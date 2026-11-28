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
  1 / 0    Ejercicio 1 / modo captura sin filtro
La barra inferior de matplotlib permite hacer zoom y muestra las coordenadas del cursor.

Requiere: pip install pyserial matplotlib numpy
"""
import argparse
import queue
import sys
import threading
import time
from datetime import datetime

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

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


class Lector(threading.Thread):
    """Lee el puerto serie y arma bloques {'info':..., 'x': array, 'y': array} (en V)."""

    def __init__(self, ser, cola):
        super().__init__(daemon=True)
        self.ser, self.cola = ser, cola
        self.mensajes = queue.Queue()

    def run(self):
        info, xs, ys = None, [], []
        while True:
            try:
                linea = self.ser.readline().decode('ascii', errors='ignore').strip()
            except serial.SerialException:
                self.mensajes.put("Se perdio la conexion con la placa")
                return
            if not linea:
                continue
            if linea.startswith('#BLOQUE'):
                info, xs, ys = parsear_encabezado(linea), [], []
            elif linea.startswith('#FIN'):
                if info is not None and xs:
                    self.cola.put({'info': info, 'x': np.array(xs) / 1000.0, 'y': np.array(ys) / 1000.0})
                info = None
            elif linea.startswith('#'):
                self.mensajes.put(linea)
            elif info is not None and linea.startswith('entrada:'):
                try:
                    a, b = linea.split()
                    xs.append(float(a.split(':')[1]))
                    ys.append(float(b.split(':')[1]))
                except ValueError:
                    pass


def main():
    ap = argparse.ArgumentParser(description="Graficador del TP de filtros digitales")
    ap.add_argument('--puerto')
    ap.add_argument('--ej', type=int, choices=(0, 1), help="1 = Ejercicio 1, 0 = captura sin filtro")
    ap.add_argument('--fs', type=int, help="fs del modo captura [Hz], 100 a 500000")
    a = ap.parse_args()

    puerto = a.puerto or buscar_puerto()
    ser = serial.Serial(puerto, 115200, timeout=0.5)
    time.sleep(0.3)

    def enviar(cmd):
        ser.write((cmd + '\n').encode())
        time.sleep(0.05)

    if a.fs:
        enviar(f'f{a.fs}')
    if a.ej is not None:
        enviar(f'e{a.ej}')
    enviar('?')

    cola = queue.Queue()
    lector = Lector(ser, cola)
    lector.start()

    estado = {'pausa': False, 'fft': False, 'bloque': None}
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    fig.canvas.manager.set_window_title(f"TP Filtros Digitales - {puerto}")
    l1, = ax1.plot([], [], color='tab:blue', lw=1)
    l2, = ax2.plot([], [], color='tab:red', lw=1)
    pie = fig.text(0.01, 0.005, "espacio: pausa | t: tiempo/FFT | c: guardar CSV | 1: Ejercicio 1 | 0: captura",
                   fontsize=8, color='gray')

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

    def actualizar(_):
        while not lector.mensajes.empty():
            print(lector.mensajes.get())
        nuevo = None
        while not cola.empty():
            nuevo = cola.get()
        if nuevo is not None and not estado['pausa']:
            estado['bloque'] = nuevo
            dibujar()
        return l1, l2

    def tecla(ev):
        if ev.key == ' ':
            estado['pausa'] = not estado['pausa']; dibujar()
        elif ev.key == 't':
            estado['fft'] = not estado['fft']
            for ax in (ax1, ax2):
                ax.set_xlim(auto=True)
            dibujar()
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
    anim = FuncAnimation(fig, actualizar, interval=100, cache_frame_data=False)
    plt.tight_layout(rect=(0, 0.02, 1, 0.96))
    plt.show()
    ser.close()
    return anim


if __name__ == '__main__':
    main()
