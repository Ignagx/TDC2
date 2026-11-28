#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graficador.py - TP Filtros Digitales en Bluepill (Teoria de Circuitos II, UTN-FRC)

Recibe por USB los bloques de muestras (entrada y salida del filtro) que envia la
Bluepill y los grafica en el tiempo o en frecuencia.

Uso:
  python graficador.py                       # detecta el puerto de la Bluepill
  python graficador.py --puerto COM5 --ej 1  # Ejercicio 1: filtro pasa bajos de la placa
  python graficador.py --ej 0 --fs 48000     # captura sin filtro a 48 kHz (entrada para el Ej. 2)

Teclas en la ventana:
  espacio  pausa / continua (para medir sobre un bloque quieto)
  t        alterna vista temporal / espectro (FFT)
  c        guarda el bloque actual en un archivo CSV (t, entrada, salida)
  b        agrega la medicion actual (f, |H|, fase) al barrido en frecuencia
  x        borra el ultimo punto agregado al barrido
  1 / 0    Ejercicio 1 / modo captura sin filtro

Barrido: se pone una senoidal en A0 (dentro de 0..3,3 V), se espera a que el grafico se
actualice DOS veces despues de cambiar la frecuencia del generador (el primer bloque puede
mezclar las dos frecuencias) y se aprieta b. Cada punto se guarda al instante en
barrido_<fecha>.csv y se grafica en una ventana aparte (Bode medido).
La barra inferior de matplotlib permite hacer zoom y muestra las coordenadas del cursor.

Requiere: pip install pyserial matplotlib numpy
"""
import argparse
import multiprocessing as mp
import queue
import re
import signal
import sys
import time
from datetime import datetime

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("Falta pyserial:  pip install pyserial")

for k in ('keymap.save', 'keymap.fullscreen', 'keymap.quit', 'keymap.grid', 'keymap.xscale',
          'keymap.yscale', 'keymap.pan', 'keymap.back', 'keymap.forward'):
    if k in matplotlib.rcParams:
        matplotlib.rcParams[k] = [x for x in matplotlib.rcParams[k] if x not in ('t', 'c', '1', '0', ' ')]


def buscar_puerto():
    puertos = list(serial.tools.list_ports.comports())
    for p in puertos:
        if p.vid == 0x0483:                      # STMicroelectronics
            return p.device
    if len(puertos) == 1:
        return puertos[0].device
    print("Puertos disponibles:", ", ".join(p.device for p in puertos) or "ninguno")
    sys.exit("No se encontro la Bluepill. Indicar el puerto con --puerto")


def parsear_encabezado(linea):
    info = {}
    for campo in linea.split()[1:]:
        if '=' in campo:
            k, v = campo.split('=', 1)
            info[k] = v
    return info


LINEA_DATOS = re.compile(r'entrada:(-?\d+(?:\.\d+)?)\s+salida:(-?\d+(?:\.\d+)?)$')


def proceso_lector(puerto, salida, comandos):
    """
    Corre en un PROCESO aparte: lee el puerto serie, arma los bloques y los manda por 'salida'
    como ('bloque', {'info':..., 'x': array, 'y': array} en V), ('msg', texto) o
    ('descartados', cantidad). Por 'comandos' recibe los textos a enviar a la placa (None = salir).

    Por que asi: la placa casi no tolera que la PC tarde en vaciar el puerto (si el USB se
    frena, descarta datos). Con readline() (lee de a un byte) se perdia ~1/3 de cada bloque y
    casi siempre el '#FIN', y el grafico no se actualizaba. Con un hilo dentro del programa
    tambien se perdian bloques mientras matplotlib redibujaba (comparten el interprete).
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)      # Ctrl+C lo maneja el proceso principal
    salida.cancel_join_thread()                       # no trabar la salida si quedan datos sin leer
    try:
        ser = serial.Serial(puerto, 115200, timeout=0.05)
    except serial.SerialException as e:
        salida.put(('msg', f"No se pudo abrir {puerto}: {e}"))
        return
    time.sleep(0.3)
    info, xs, ys, resto = None, [], [], b''
    descartados, pendientes, ultimo_cmd = 0, [], 0.0
    while True:
        try:
            while True:
                cmd = comandos.get_nowait()
                if cmd is None:
                    ser.close()
                    return
                pendientes.append(cmd)
        except queue.Empty:
            pass
        try:
            # los comandos se espacian 50 ms sin dejar de leer el puerto
            if pendientes and time.monotonic() - ultimo_cmd > 0.05:
                ser.write((pendientes.pop(0) + '\n').encode())
                ultimo_cmd = time.monotonic()
            resto += ser.read(max(1, ser.in_waiting))   # todo lo disponible, de una vez
        except serial.SerialException:
            salida.put(('msg', "Se perdio la conexion con la placa"))
            return
        *lineas, resto = resto.split(b'\n')
        for crudo in lineas:
            linea = crudo.decode('ascii', errors='ignore').strip()
            if not linea:
                continue
            if linea.startswith('#BLOQUE'):
                if info is not None:                  # el anterior quedo sin '#FIN'
                    descartados += 1
                    salida.put(('descartados', descartados))
                info, xs, ys = parsear_encabezado(linea), [], []
            elif linea.startswith('#FIN'):
                if info is not None and xs:
                    if len(xs) == int(info.get('N', len(xs))):
                        salida.put(('bloque', {'info': info, 'x': np.array(xs) / 1000.0,
                                               'y': np.array(ys) / 1000.0}))
                    else:                             # faltan muestras: el eje de tiempo seria falso
                        descartados += 1
                        salida.put(('descartados', descartados))
                info = None
            elif linea.startswith('#'):
                salida.put(('msg', linea))
            elif info is not None:
                m = LINEA_DATOS.match(linea)
                if m:
                    xs.append(float(m.group(1)))
                    ys.append(float(m.group(2)))


def medir(x, y, fs):
    """
    Mide el tono de la entrada por ajuste senoidal de minimos cuadrados.
    Devuelve frecuencia, amplitudes pico de entrada y salida, |H| = salida/entrada en dB,
    desfasaje salida - entrada en grados y el residuo del ajuste de la entrada (en %).
    Devuelve None si no hay un tono medible.
    """
    n = len(x)
    if n < 32:
        return None
    t = np.arange(n) / fs
    w = np.hanning(n)
    X = np.abs(np.fft.rfft((x - x.mean()) * w))
    k = int(X[1:].argmax()) + 1
    d = 0.0
    if k < len(X) - 1:                                # interpolacion parabolica del pico
        a, b, c = np.log(X[k - 1:k + 2] + 1e-20)
        if a - 2 * b + c != 0:
            d = 0.5 * (a - c) / (a - 2 * b + c)
    f0 = (k + d) * fs / n

    def ajuste(v, f):
        M = np.column_stack([np.cos(2 * np.pi * f * t), np.sin(2 * np.pi * f * t), np.ones(n)])
        coef = np.linalg.lstsq(M, v, rcond=None)[0]
        return coef, M @ coef

    def error(f):                                     # error cuadratico del ajuste de la entrada
        return np.sum((x - ajuste(x, f)[1]) ** 2)

    paso = fs / n
    if k <= 2:            # menos de ~2 periodos en el bloque: el pico de la FFT se mezcla con la continua
        f0 = min(np.linspace(0.25 * paso, 3.5 * paso, 66), key=error)
    # refinamiento de la frecuencia: la que minimiza el error del ajuste (+-1 bin y luego fino)
    for ancho in (paso, paso / 20):
        grilla = f0 + np.linspace(-ancho, ancho, 21)
        grilla = grilla[grilla > 0.2 * paso]
        f0 = min(grilla, key=error)

    (ci, si, _), ajx = ajuste(x, f0)
    (co, so, _), _ = ajuste(y, f0)
    ain, aout = np.hypot(ci, si), np.hypot(co, so)
    if ain < 5e-3:                                    # menos de 10 mVpp: no hay senal
        return None
    fase = np.degrees(np.angle(complex(co, -so)) - np.angle(complex(ci, -si)))
    fase = (fase + 180) % 360 - 180
    residuo = 100 * np.sqrt(np.mean((x - ajx) ** 2)) / (ain / np.sqrt(2))
    return {'f': f0, 'vin': ain, 'vout': aout, 'db': 20 * np.log10(aout / ain + 1e-12),
            'fase': fase, 'residuo': residuo}


def main():
    ap = argparse.ArgumentParser(description="Graficador del TP de filtros digitales")
    ap.add_argument('--puerto')
    ap.add_argument('--ej', type=int, choices=(0, 1), help="1 = Ejercicio 1, 0 = captura sin filtro")
    ap.add_argument('--fs', type=int, help="fs del modo captura [Hz], 100 a 500000")
    a = ap.parse_args()

    puerto = a.puerto or buscar_puerto()
    salida, comandos = mp.Queue(), mp.Queue()
    lector = mp.Process(target=proceso_lector, args=(puerto, salida, comandos), daemon=True)
    lector.start()

    def enviar(cmd):
        comandos.put(cmd)

    if a.fs:
        enviar(f'f{a.fs}')
    if a.ej is not None:
        enviar(f'e{a.ej}')
    enviar('?')

    estado = {'pausa': False, 'fft': False, 'bloque': None, 'medida': None, 'descartados': 0}
    barrido = []                                      # puntos en el orden en que se agregaron
    archivo_barrido = datetime.now().strftime("barrido_%Y%m%d_%H%M%S.csv")
    vb = {'fig': None}
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, layout='constrained')
    fig.canvas.manager.set_window_title(f"TP Filtros Digitales - {puerto}")
    l1, = ax1.plot([], [], color='tab:blue', lw=1)
    l2, = ax2.plot([], [], color='tab:red', lw=1)
    pie = fig.supxlabel("espacio: pausa | t: tiempo/FFT | c: guardar CSV | b: agregar punto al barrido | "
                        "x: borrar ultimo punto | 1: Ejercicio 1 | 0: captura", fontsize=8, color='gray')

    def dibujar():
        b = estado['bloque']
        if b is None:
            return
        info = b['info']
        fs = float(info.get('fs', 1))
        x, y = b['x'], b['y']
        n = len(x)
        tit = "Ejercicio 1" if info.get('ej') == '1' else "Captura sin filtro"
        tit += f"   |   fs = {fs/1e3:g} kHz   N = {n}   carga CPU = {info.get('carga')}"
        if estado['pausa']:
            tit += "   [PAUSA]"
        if estado['descartados']:
            tit += f"   (bloques incompletos descartados: {estado['descartados']})"
        m = estado['medida']
        tit += (f"\nmedia: entrada {x.mean():.4f} V   salida {y.mean():.4f} V   "
                f"(min {x.min():.3f} V, max {x.max():.3f} V)")
        if m is None:
            tit += "   -   sin tono medible en la entrada"
        else:
            tit += (f"\nf = {m['f']:.4g} Hz   entrada {2*m['vin']:.3f} Vpp   salida {2*m['vout']:.3f} Vpp"
                    f"   |H| = {m['db']:+.2f} dB   fase = {m['fase']:+.1f}°   |   barrido: {len(barrido)} puntos")
            avisos = []
            if x.min() < 0.01 or x.max() > 3.29:
                avisos.append("ENTRADA SATURADA (debe estar entre 0 y 3,3 V)")
            if m['f'] > 0.45 * fs:
                avisos.append("tono cerca de fs/2")
            if m['f'] * n / fs < 3:
                avisos.append("menos de 3 periodos en el bloque: medicion poco precisa")
            if m['residuo'] > 10:
                avisos.append(f"senal inestable/ruidosa ({m['residuo']:.0f} %)")
            if avisos:
                tit += "\n" + "  -  ".join(avisos)
        fig.suptitle(tit, fontsize=10)
        if not estado['fft']:
            t = np.arange(n) / fs * 1e3
            l1.set_data(t, x); l2.set_data(t, y)
            ax1.set_ylabel("Entrada [V]")
            ax2.set_ylabel("Salida [V]" + (" (= entrada)" if info.get('ej') == '0' else ""))
            ax2.set_xlabel("Tiempo [ms]")
            for ax in (ax1, ax2):
                ax.set_xscale('linear')
        else:
            w = np.hanning(n)
            f = np.fft.rfftfreq(n, 1 / fs)
            def esp(v):
                V = np.abs(np.fft.rfft((v - v.mean()) * w)) * 2 / w.sum()   # amplitud pico
                return 20 * np.log10(V + 1e-9)
            l1.set_data(f, esp(x)); l2.set_data(f, esp(y))
            ax1.set_ylabel("Entrada [dBV pico]")
            ax2.set_ylabel("Salida [dBV pico]")
            ax2.set_xlabel("Frecuencia [Hz]")
        for ax in (ax1, ax2):
            ax.relim(); ax.autoscale_view()
            ax.grid(True, which='both', alpha=0.4)
        if estado['fft']:
            for ax in (ax1, ax2):
                ax.set_ylim(-100, 10)
        fig.canvas.draw_idle()

    def actualizar():
        nuevo = None
        try:
            while True:
                tipo, dato = salida.get_nowait()
                if tipo == 'bloque':
                    nuevo = dato
                elif tipo == 'descartados':
                    estado['descartados'] = dato
                else:
                    print(dato)
        except queue.Empty:
            pass
        if nuevo is not None and not estado['pausa']:
            estado['bloque'] = nuevo
            estado['medida'] = medir(nuevo['x'], nuevo['y'], float(nuevo['info'].get('fs', 1)))
            if estado['medida'] is not None:
                estado['medida']['media'] = float(nuevo['x'].mean())
            dibujar()                     # se redibuja solo cuando llega un bloque nuevo

    def guardar_barrido():
        pts = sorted(barrido, key=lambda p: p['f'])
        datos = np.array([[p['f'], 2 * p['vin'], 2 * p['vout'], p['db'], p['fase'], p['media']]
                          for p in pts])
        np.savetxt(archivo_barrido, datos.reshape(-1, 6), delimiter=',', fmt='%.6g',
                   header="f [Hz],entrada [Vpp],salida [Vpp],|H| [dB],fase [grados],media entrada [V]")

    def graficar_barrido():
        if vb['fig'] is None or not plt.fignum_exists(vb['fig'].number):
            vb['fig'], (vb['m'], vb['p']) = plt.subplots(2, 1, sharex=True, figsize=(8, 6),
                                                         layout='constrained')
            vb['fig'].canvas.manager.set_window_title("Barrido en frecuencia (Bode medido)")
            vb['fig'].show()
        bm, bp = vb['m'], vb['p']
        bm.cla(); bp.cla()
        pts = sorted(barrido, key=lambda p: p['f'])
        if pts:
            f = [p['f'] for p in pts]
            db = [p['db'] for p in pts]
            bm.semilogx(f, db, 'o-', ms=4)
            bp.semilogx(f, [p['fase'] for p in pts], 'o-', ms=4, color='tab:red')
            ref = max(db) - 3
            bm.axhline(ref, color='gray', ls=':', lw=0.8)
            bm.text(f[0], ref, f" max - 3 dB = {ref:.2f} dB", fontsize=8, va='bottom', color='gray')
        bm.set_ylabel("|H| [dB]"); bp.set_ylabel("Fase [grados]"); bp.set_xlabel("f [Hz]")
        for ax in (bm, bp):
            ax.grid(True, which='both', alpha=0.4)
            ax.ticklabel_format(axis='y', useOffset=False)
        vb['fig'].suptitle(f"{len(pts)} puntos  -  {archivo_barrido}", fontsize=9)
        vb['fig'].canvas.draw_idle()

    def tecla(ev):
        if ev.key == ' ':
            estado['pausa'] = not estado['pausa']; dibujar()
        elif ev.key == 't':
            estado['fft'] = not estado['fft']
            for ax in (ax1, ax2):
                ax.set_xlim(auto=True)
                ax.set_ylim(auto=True)        # el modo FFT fija el eje y; aca se vuelve a liberar
            dibujar()
        elif ev.key == 'b':
            m = estado['medida']
            if m is None:
                print("No hay un tono medible en la entrada: no se agrego el punto")
                return
            if any(p is m for p in barrido):
                print("Ese bloque ya esta en el barrido: esperar al proximo bloque")
                return
            barrido.append(m)
            guardar_barrido()
            print(f"Punto {len(barrido)}: f = {m['f']:.4g} Hz  |H| = {m['db']:+.2f} dB  "
                  f"fase = {m['fase']:+.1f}°  (entrada {2*m['vin']:.3f} Vpp)  -> {archivo_barrido}")
            if m['residuo'] > 10:
                print("  OJO: la senal de ese bloque no es una senoidal limpia (cambio de frecuencia "
                      "en el medio, ruido o saturacion). Conviene borrarlo con x y repetir.")
            graficar_barrido(); dibujar()
        elif ev.key == 'x' and barrido:
            p = barrido.pop()
            print(f"Borrado el punto de {p['f']:.4g} Hz")
            guardar_barrido(); graficar_barrido(); dibujar()
        elif ev.key == 'c' and estado['bloque'] is not None:
            b = estado['bloque']
            fs = float(b['info'].get('fs', 1))
            nombre = datetime.now().strftime("captura_%Y%m%d_%H%M%S.csv")
            t = np.arange(len(b['x'])) / fs
            cab = " ".join(f"{k}={v}" for k, v in b['info'].items())
            np.savetxt(nombre, np.column_stack([t, b['x'], b['y']]), delimiter=',',
                       header=f"{cab}\nt [s],entrada [V],salida [V]", fmt='%.7g')
            print(f"Guardado {nombre}")
        elif ev.key in ('1', '0'):
            enviar(f'e{ev.key}')

    fig.canvas.mpl_connect('key_press_event', tecla)
    timer = fig.canvas.new_timer(interval=100)
    timer.add_callback(actualizar)
    timer.start()
    try:
        plt.show()
    except KeyboardInterrupt:                         # Ctrl+C en la terminal: salir sin traceback
        pass
    finally:
        timer.stop()
        comandos.put(None)                            # el lector cierra el puerto y termina
        lector.join(timeout=1)
        if lector.is_alive():
            lector.terminate()
    if barrido:
        print(f"Barrido guardado en {archivo_barrido} ({len(barrido)} puntos)")


if __name__ == '__main__':
    main()
