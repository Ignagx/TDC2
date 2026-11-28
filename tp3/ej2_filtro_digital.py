#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ej2_filtro_digital.py - TP Filtros Digitales - Ejercicio 2 (Teoria de Circuitos II, UTN-FRC)

Diseno del filtro digital IIR equivalente al filtro del TP2 que NO se implemento
en forma fisica, y obtencion de su salida por simulacion.

QUE TIENE QUE COMPLETAR EL GRUPO (secciones 1, 2 y 3):
  1. Datos del filtro asignado y la frecuencia de muestreo elegida.
  2. La H(s) analogica disenada en el TP2, como producto de secciones de 2do orden.
  3. La funcion bilineal_prewarp(): transformacion bilineal con predistorsion.

QUE HACE EL SCRIPT (no hace falta modificarlo):
  - Arma H(z) aplicando su bilineal_prewarp() a cada seccion y la verifica.
  - Informa estabilidad, ganancia maxima y atenuacion en los bordes vs. la especificacion.
  - Grafica: Bode de H(s) y H(z), polos y ceros en el plano z, respuesta al impulso y
    al escalon, y la salida del filtro para una senal de prueba (tiempo y espectro).
  - Opcional: filtra una senal real capturada con la Bluepill (graficador.py, tecla c)
    y analiza el efecto de cuantizar los coeficientes.

Uso:
  python ej2_filtro_digital.py
  python ej2_filtro_digital.py --csv captura_20261120_101500.csv   # entrada = senal capturada
  python ej2_filtro_digital.py --bits 16                            # coeficientes en punto fijo
Requiere: pip install numpy scipy matplotlib
"""
import argparse
import math
import sys

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# =============================================================================
# 1. DATOS DEL FILTRO (completar con la asignacion del grupo)
# =============================================================================
GRUPO = 2
FILTRO = 'pba'           # 'pb' = pasa bajos, 'pa' = pasa altos, 'pba' = pasa banda
APROXIMACION = 'Butterworth'   # 'Butterworth' o 'Chebyshev' (informativo)
AMAX_DB = 0.1            # atenuacion maxima en la banda de paso [dB]
G = 9.0                  # ganancia maxima de la banda de paso [V/V]
FP_HZ = 1000.0           # pasa bajos / pasa altos: borde de la banda de paso [Hz] (no se usa)
FO_HZ = 28000.0          # pasa banda: frecuencia central [Hz]
BW_HZ = 1700.0           # pasa banda: ancho de banda fp2 - fp1 [Hz]

# fs = 200 kHz: la banda llega a fp2 = 28,9 kHz y el tono de rechazo de la senal de prueba
# esta en 2 fo = 56 kHz, ambos muy por debajo de fs/2 = 100 kHz (unas 7 muestras por periodo
# en fo). Es una frecuencia que el ADC del STM32 alcanza (hasta 1 Msps) y que el graficador
# puede capturar (--ej 0 --fs 200000), aunque filtrar en tiempo real a esa velocidad exige
# hacer cada muestra en menos de 360 ciclos de 72 MHz (aritmetica de punto fijo).
FS_HZ = 200000.0


# =============================================================================
# 2. H(s) DEL TP2 (completar)
#    Producto de secciones de 2do orden, con los f0, Q y K de cada etapa calculados
#    en el TP2. Ejemplos:
#       SECCIONES_S = [seccion_pb(K=2.0, f0=1200, Q=0.54), seccion_pb(K=3.5, f0=1100, Q=1.31)]
#       SECCIONES_S = [seccion_pba(K=..., f0=..., Q=...), seccion_pba(K=..., f0=..., Q=...)]
#    Tambien se puede escribir cada seccion a mano como (num, den) en potencias
#    decrecientes de s, por ejemplo ([0, 0, w0**2], [1, w0/Q, w0**2]).
# =============================================================================
def seccion_pb(K, f0, Q):
    """Pasa bajos de 2do orden: K w0^2 / (s^2 + (w0/Q) s + w0^2)."""
    w0 = 2 * math.pi * f0
    return [0.0, 0.0, K * w0 ** 2], [1.0, w0 / Q, w0 ** 2]


def seccion_pa(K, f0, Q):
    """Pasa altos de 2do orden: K s^2 / (s^2 + (w0/Q) s + w0^2)."""
    w0 = 2 * math.pi * f0
    return [K, 0.0, 0.0], [1.0, w0 / Q, w0 ** 2]


def seccion_pba(K, f0, Q):
    """Pasa banda de 2do orden: K (w0/Q) s / (s^2 + (w0/Q) s + w0^2)  (ganancia K en f0)."""
    w0 = 2 * math.pi * f0
    return [0.0, K * w0 / Q, 0.0], [1.0, w0 / Q, w0 ** 2]


# TP2, capitulo 5: pasa banda Butterworth de orden 2 obtenido de un prototipo pasa bajos de
# orden 1 con epsilon = sqrt(10^(Amax/10) - 1). Una sola celda Sallen-Key con
# Qp = epsilon fo / BW = 2,5137 y ganancia K = 9 en fo.
EPSILON = math.sqrt(10 ** (AMAX_DB / 10) - 1)
Q_TP2 = EPSILON * FO_HZ / BW_HZ
SECCIONES_S = [seccion_pba(K=G, f0=FO_HZ, Q=Q_TP2)]


# =============================================================================
# 3. DISENO DIGITAL (completar)
# =============================================================================
F_PREWARP_HZ = FP_HZ if FILTRO != 'pba' else FO_HZ   # frecuencia donde se predistorsiona


def bilineal_prewarp(num_s, den_s, fs, f0):
    """
    Transforma UNA seccion de 2do orden H(s) = (b2 s^2 + b1 s + b0) / (a2 s^2 + a1 s + a0)
    en H(z) = (B0 + B1 z^-1 + B2 z^-2) / (1 + A1 z^-1 + A2 z^-2) reemplazando

        s = K (1 - z^-1) / (1 + z^-1),   con   K = 2*pi*f0 / tan(pi*f0/fs)

    (la eleccion de K hace que H(z) coincida exactamente con H(s) en f = f0).
    num_s = [b2, b1, b0], den_s = [a2, a1, a0].
    Debe devolver (b, a) = ([B0, B1, B2], [1, A1, A2]).
    """
    K = 2 * math.pi * f0 / math.tan(math.pi * f0 / fs)

    # Multiplicando numerador y denominador por (1 + z^-1)^2:
    #   c2 K^2 (1 - z^-1)^2 + c1 K (1 - z^-1)(1 + z^-1) + c0 (1 + z^-1)^2
    #   = (c2 K^2 + c1 K + c0) + 2 (c0 - c2 K^2) z^-1 + (c2 K^2 - c1 K + c0) z^-2
    def coeficientes(c2, c1, c0):
        return [c2 * K ** 2 + c1 * K + c0,
                2 * (c0 - c2 * K ** 2),
                c2 * K ** 2 - c1 * K + c0]

    B = coeficientes(*num_s)
    A = coeficientes(*den_s)
    return [x / A[0] for x in B], [x / A[0] for x in A]


def secciones_bordes(fs):
    """
    Correccion propuesta (analisis, punto 1; se usa con --bordes).
    Con la predistorsion solo en fo, la bilineal angosta la banda: los bordes fp1 y fp2 quedan
    con algo mas de Amax de atenuacion. Aca se redisena el pasa banda analogico para que sus
    bordes caigan en Omega = K tan(pi fp/fs), con el mismo K de bilineal_prewarp(): al
    transformarlo, los bordes digitales quedan exactamente en fp1 y fp2.
    Los bordes se disenan con AMAX_DISENO_DB = 0,09 dB, 0,01 dB menos que la especificacion,
    como margen para la cuantizacion de los coeficientes.
    """
    fp1 = (-BW_HZ + math.sqrt(BW_HZ ** 2 + 4 * FO_HZ ** 2)) / 2
    fp2 = fp1 + BW_HZ
    K = 2 * math.pi * F_PREWARP_HZ / math.tan(math.pi * F_PREWARP_HZ / fs)
    w1, w2 = K * math.tan(math.pi * fp1 / fs), K * math.tan(math.pi * fp2 / fs)
    w0 = math.sqrt(w1 * w2)
    eps = math.sqrt(10 ** (AMAX_DISENO_DB / 10) - 1)
    return [seccion_pba(K=G, f0=w0 / (2 * math.pi), Q=eps * w0 / (w2 - w1))]


AMAX_DISENO_DB = 0.09


# =============================================================================
#                 A PARTIR DE ACA NO HACE FALTA MODIFICAR NADA
# =============================================================================
def armar_hz(fs, secciones=None):
    secciones = secciones or SECCIONES_S
    if not secciones:
        sys.exit("Completar SECCIONES_S (seccion 2) con la H(s) del TP2.")
    sos = []
    K = 2 * math.pi * F_PREWARP_HZ / math.tan(math.pi * F_PREWARP_HZ / fs)
    for i, (n, d) in enumerate(secciones):
        b, a = bilineal_prewarp(list(n), list(d), fs, F_PREWARP_HZ)
        b, a = np.asarray(b, float), np.asarray(a, float)
        # verificacion contra scipy (bilineal con constante 2*fs' = K)
        bz, az = signal.bilinear(n, d, fs=K / 2)
        ok = len(bz) == 3 and np.allclose(b / a[0], bz / az[0], rtol=1e-6, atol=1e-9) and \
            np.allclose(a / a[0], az / az[0], rtol=1e-6, atol=1e-9)
        print(f"  Seccion {i+1}: b = {np.array2string(b / a[0], precision=8)}  "
              f"a = {np.array2string(a / a[0], precision=8)}  -> {'OK' if ok else 'NO COINCIDE con scipy'}")
        sos.append(np.concatenate([b / a[0], a / a[0]]))
    return np.array(sos)


def respuesta_s(f):
    h = np.ones_like(f, dtype=complex)
    for n, d in SECCIONES_S:
        _, hs = signal.freqs(n, d, 2 * np.pi * f)
        h *= hs
    return h


def bordes():
    if FILTRO == 'pba':
        fp1 = (-BW_HZ + math.sqrt(BW_HZ ** 2 + 4 * FO_HZ ** 2)) / 2
        return [fp1, fp1 + BW_HZ]
    return [FP_HZ]


def cuantizar(sos, bits):
    """Coeficientes en punto fijo de 'bits' bits con la cantidad de bits enteros necesaria."""
    ent = int(math.ceil(math.log2(np.max(np.abs(sos)) + 1e-12))) + 1
    q = bits - ent
    return np.round(sos * 2 ** q) / 2 ** q, q


def informe(sos, fs):
    print(f"\nGrupo {GRUPO} - filtro '{FILTRO}' {APROXIMACION} - fs = {fs/1e3:g} kHz")
    polos = np.concatenate([np.roots(s[3:]) for s in sos])
    print("  |polos| =", ", ".join(f"{abs(p):.5f}" for p in polos),
          "->", "ESTABLE" if np.all(np.abs(polos) < 1) else "INESTABLE")
    f = np.linspace(fs / 1e5, fs / 2 * 0.9999, 50000)
    _, h = signal.sosfreqz(sos, worN=f, fs=fs)
    db = 20 * np.log10(np.abs(h) + 1e-15)
    gdb = 20 * math.log10(G)
    print(f"  Ganancia maxima: {db.max():.2f} dB en {f[db.argmax()]/1e3:.3f} kHz (especificado {gdb:.2f} dB)")
    for fb in bordes():
        v = db[np.argmin(abs(f - fb))]
        print(f"  |H| en {fb/1e3:.3f} kHz: {v:.2f} dB (especificado >= {gdb - AMAX_DB:.2f} dB)")
    cruces = f[np.where(np.diff(np.sign(db - (db.max() - 3))))[0]]
    print("  Frecuencias a -3 dB del maximo:", ", ".join(f"{c/1e3:.3f} kHz" for c in cruces))


def senal_prueba(fs, n):
    """Suma de tres tonos (banda de paso, borde y banda de rechazo) + ruido."""
    t = np.arange(n) / fs
    if FILTRO == 'pb':
        tonos = [FP_HZ / 4, FP_HZ, min(4 * FP_HZ, 0.45 * fs)]
    elif FILTRO == 'pa':
        tonos = [FP_HZ / 4, FP_HZ, min(4 * FP_HZ, 0.45 * fs)]
    else:
        tonos = [FO_HZ / 2, FO_HZ, min(2 * FO_HZ, 0.45 * fs)]
    x = sum(0.3 * np.sin(2 * np.pi * ft * t) for ft in tonos)
    x += 0.02 * np.random.default_rng(1).standard_normal(n)
    return t, x, tonos


def leer_csv(nombre):
    with open(nombre, encoding='utf-8') as fh:
        cab = fh.readline()
    info = dict(c.split('=', 1) for c in cab.lstrip('# ').split() if '=' in c)
    datos = np.loadtxt(nombre, delimiter=',', comments='#')
    fs = float(info.get('fs', 0)) or 1.0 / (datos[1, 0] - datos[0, 0])
    x = datos[:, 1] - datos[:, 1].mean()       # se quita la continua (offset del generador)
    return datos[:, 0], x, fs


def espectro(v, fs):
    w = np.hanning(len(v))
    V = np.abs(np.fft.rfft((v - v.mean()) * w)) * 2 / w.sum()
    return np.fft.rfftfreq(len(v), 1 / fs), 20 * np.log10(V + 1e-9)


def main():
    ap = argparse.ArgumentParser(description="Ejercicio 2: filtro digital IIR")
    ap.add_argument('--csv', help="senal de entrada capturada con graficador.py (tecla c)")
    ap.add_argument('--bits', type=int, help="cuantizar los coeficientes a N bits (ej. 16)")
    ap.add_argument('--bordes', action='store_true',
                    help="correccion: predistorsionar los bordes de banda (ver secciones_bordes)")
    ap.add_argument('--guardar', metavar='PREFIJO',
                    help="guardar las figuras como PREFIJO_bode.pdf, etc., en lugar de mostrarlas")
    a = ap.parse_args()

    fs = FS_HZ
    if a.csv:
        t, x, fs_csv = leer_csv(a.csv)
        if abs(fs_csv - fs) > 1e-6 * fs:
            print(f"AVISO: la captura tiene fs = {fs_csv:g} Hz y el diseno fs = {fs:g} Hz. "
                  f"Se redisena H(z) con fs = {fs_csv:g} Hz.")
            fs = fs_csv
        tonos = []
    print("Transformacion bilineal con prewarping en "
          f"{F_PREWARP_HZ/1e3:g} kHz:")
    if a.bordes:
        print("Correccion: H(s) redisenada con los bordes de banda predistorsionados")
    sos = armar_hz(fs, secciones_bordes(fs) if a.bordes else None)
    informe(sos, fs)
    if not a.csv:
        t, x, tonos = senal_prueba(fs, 4096)

    sos_q = None
    if a.bits:
        sos_q, q = cuantizar(sos, a.bits)
        print(f"\nCoeficientes cuantizados a {a.bits} bits (Q{a.bits - q}.{q}):")
        informe(sos_q, fs)

    y = signal.sosfilt(sos, x)
    np.savetxt('salida_filtro.csv', np.column_stack([t, x, y]), delimiter=',', fmt='%.7g',
               header=f"fs={fs:g}\nt [s],entrada [V],salida [V]")
    print("\nSalida guardada en salida_filtro.csv")

    # ---- Figura 1: Bode ----
    fmin = max(fs / 1e5, min(bordes()) / 100)
    f = np.logspace(math.log10(fmin), math.log10(fs / 2 * 0.9999), 3000)
    _, hz = signal.sosfreqz(sos, worN=f, fs=fs)
    hs = respuesta_s(f)
    fig1, (m, ph) = plt.subplots(2, 1, sharex=True, figsize=(10, 7))
    m.semilogx(f, 20 * np.log10(np.abs(hs) + 1e-15), label='H(s) analogico (TP2)')
    m.semilogx(f, 20 * np.log10(np.abs(hz) + 1e-15), '--', label=f'H(z), fs = {fs/1e3:g} kHz')
    if sos_q is not None:
        _, hq = signal.sosfreqz(sos_q, worN=f, fs=fs)
        m.semilogx(f, 20 * np.log10(np.abs(hq) + 1e-15), ':', label=f'H(z) con {a.bits} bits')
    gdb = 20 * math.log10(G)
    for fb in bordes():
        m.axvline(fb, color='gray', lw=0.8)
    m.axhline(gdb - AMAX_DB, color='gray', ls=':', lw=0.8)
    m.axvline(fs / 2, color='k', lw=1); m.text(fs / 2, gdb - 75, ' fs/2', fontsize=8)
    m.set_ylim(gdb - 80, gdb + 6); m.set_ylabel('|H| [dB]'); m.legend(fontsize=8)
    ph.semilogx(f, np.degrees(np.unwrap(np.angle(hs))), label='H(s)')
    ph.semilogx(f, np.degrees(np.unwrap(np.angle(hz))), '--', label='H(z)')
    ph.set_ylabel('Fase [grados]'); ph.set_xlabel('f [Hz]'); ph.legend(fontsize=8)
    for ax in (m, ph):
        ax.grid(True, which='both', alpha=0.4)
    fig1.suptitle(f"Grupo {GRUPO} - respuesta en frecuencia" + (" (bordes predistorsionados)" if a.bordes else ""))

    # ---- Figura 2: polos y ceros ----
    fig2, ax = plt.subplots(figsize=(6, 6))
    ax.add_patch(plt.Circle((0, 0), 1, fill=False, color='gray'))
    z = np.concatenate([np.roots(s[:3]) if s[0] != 0 else np.roots(s[1:3]) for s in sos])
    p = np.concatenate([np.roots(s[3:]) for s in sos])
    ax.plot(z.real, z.imag, 'o', mfc='none', ms=9, label='ceros')
    ax.plot(p.real, p.imag, 'x', ms=9, label='polos')
    ax.set_aspect('equal'); ax.grid(True, alpha=0.4); ax.legend()
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3); ax.set_title('Plano z')

    # ---- Figura 3: impulso y escalon ----
    n = np.arange(int(min(4000, max(200, 20 * fs / min(bordes())))))
    imp = signal.sosfilt(sos, (n == 0).astype(float))
    esc = signal.sosfilt(sos, np.ones(len(n)))
    fig3, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
    a1.plot(n, imp, '.-', ms=3); a1.set_ylabel('h[n]')
    a2.plot(n, esc, '.-', ms=3); a2.set_ylabel('respuesta al escalon'); a2.set_xlabel('n')
    for ax in (a1, a2):
        ax.grid(True, alpha=0.4)
    fig3.suptitle('Respuesta al impulso y al escalon')

    # ---- Figura 4: senal de prueba ----
    fig4, ((t1, f1), (t2, f2)) = plt.subplots(2, 2, figsize=(12, 7))
    t1.plot(t * 1e3, x, lw=0.8); t1.set_ylabel('Entrada [V]')
    t2.plot(t * 1e3, y, lw=0.8, color='tab:red'); t2.set_ylabel('Salida [V]'); t2.set_xlabel('t [ms]')
    if tonos:                                   # se muestran unos 20 periodos del tono mas lento
        t1.set_xlim(0, min(t[-1], 20 / min(tonos)) * 1e3); t2.set_xlim(t1.get_xlim())
    fx, Ex = espectro(x, fs); fy, Ey = espectro(y, fs)
    f1.plot(fx, Ex, lw=0.8); f2.plot(fy, Ey, lw=0.8, color='tab:red')
    f2.set_xlabel('f [Hz]')
    for ax in (f1, f2):
        ax.set_ylabel('dBV pico'); ax.set_ylim(-100, 20)
        for ft in tonos:
            ax.axvline(ft, color='gray', lw=0.6, ls=':')
    for ax in (t1, t2, f1, f2):
        ax.grid(True, alpha=0.4)
    fig4.suptitle('Senal de prueba' if not a.csv else f'Senal capturada: {a.csv}')
    plt.tight_layout()
    if a.guardar:
        for fig, nombre in ((fig1, 'bode'), (fig2, 'polos_ceros'), (fig3, 'impulso_escalon'),
                            (fig4, 'senal_prueba')):
            fig.savefig(f"{a.guardar}_{nombre}.pdf", bbox_inches='tight')
        print(f"Figuras guardadas como {a.guardar}_*.pdf")
    else:
        plt.show()


if __name__ == '__main__':
    main()
