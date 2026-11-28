#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
generar_ej2.py - Datos y numeros del Ejercicio 2 para el informe.

Usa las funciones de ../ej2_filtro_digital.py (el mismo calculo que hace el script) y escribe
en datos/:
  ej2_bode.dat, ej2_bode_zoom.dat    |H| y fase de H(s) del TP2, H(z) (predistorsion en fo)
                                     y H(z) corregida (bordes predistorsionados)
  ej2_pz.dat                         polos y ceros de ambas H(z)
  ej2_tiempo.dat                     respuesta al impulso y al escalon (corregida)
  ej2_espectro.dat                   espectro de la senal de prueba a la entrada y a la salida
  ej2_tabla_bits.tex                 filas de la tabla de cuantizacion
  resultados_ej2.tex                 macros \ejXxx con los numeros citados en el texto

Uso (desde informe/):  python generar_ej2.py
"""
import contextlib
import io
import math
import os
import sys

import numpy as np
from scipy import signal

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, 'datos')
sys.path.insert(0, os.path.dirname(AQUI))
import ej2_filtro_digital as e  # noqa: E402

FS = e.FS_HZ


def num(x, dec):
    if round(x, dec) == 0:
        x = 0.0
    return f"{x:.{dec}f}".replace('.', ',')


def callado(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


def db(h):
    return 20 * np.log10(np.abs(h) + 1e-15)


def cumple(sos, fp1, fp2):
    """Estable, bordes >= G - Amax y maximo <= G + Amax (en dB)."""
    gdb = 20 * math.log10(e.G)
    r = max(abs(np.roots(s[3:])).max() for s in sos)
    _, h12 = signal.sosfreqz(sos, worN=[fp1, fp2], fs=FS)
    fw = np.linspace(1, FS / 2 * 0.999, 100000)
    _, hw = signal.sosfreqz(sos, worN=fw, fs=FS)
    d12, dmax = db(h12), db(hw).max()
    return r, d12, dmax, (r < 1 and d12.min() >= gdb - e.AMAX_DB and dmax <= gdb + e.AMAX_DB)


def main():
    fp1, fp2 = e.bordes()
    gdb = 20 * math.log10(e.G)
    sos_fo = callado(e.armar_hz, FS)
    sec_b = e.secciones_bordes(FS)
    sos_b = callado(e.armar_hz, FS, sec_b)
    (n_b, d_b), = sec_b
    w0b = math.sqrt(d_b[2])
    qb = w0b / d_b[1]

    # ---- Bode ----
    f = np.logspace(3, math.log10(FS / 2 * 0.9999), 700)
    hs = e.respuesta_s(f)
    _, hz = signal.sosfreqz(sos_fo, worN=f, fs=FS)
    _, hb = signal.sosfreqz(sos_b, worN=f, fs=FS)
    np.savetxt(os.path.join(DATOS, 'ej2_bode.dat'),
               np.column_stack([f / 1e3, db(hs), db(hz), db(hb), np.degrees(np.angle(hs)),
                                np.degrees(np.angle(hz)), np.degrees(np.angle(hb))]),
               header='f hs hz hb fs fz fb', comments='', fmt='%.6g')
    fz = np.linspace(25e3, 31e3, 600)
    hs_z = e.respuesta_s(fz)
    _, hz_z = signal.sosfreqz(sos_fo, worN=fz, fs=FS)
    _, hb_z = signal.sosfreqz(sos_b, worN=fz, fs=FS)
    np.savetxt(os.path.join(DATOS, 'ej2_bode_zoom.dat'),
               np.column_stack([fz / 1e3, db(hs_z), db(hz_z), db(hb_z)]),
               header='f hs hz hb', comments='', fmt='%.6g')

    # ---- polos y ceros ----
    p_fo, p_b = np.roots(sos_fo[0][3:]), np.roots(sos_b[0][3:])
    z_b = np.roots(sos_b[0][:3])
    filas = [(p.real, p.imag, 0) for p in p_fo] + [(p.real, p.imag, 1) for p in p_b] + \
            [(z.real, z.imag, 2) for z in z_b]
    np.savetxt(os.path.join(DATOS, 'ej2_pz.dat'), np.array(filas), header='re im tipo',
               comments='', fmt='%.6g')
    r_fo, r_b = abs(p_fo[0]), abs(p_b[0])
    ang_b = np.degrees(abs(np.angle(p_b[0])))
    # relacion |p| - Q para la bilineal con predistorsion en f0: r^2 = (1 - x)/(1 + x),
    # x = sin(2 pi f0/fs) / (2 Q)
    x_fo = math.sin(2 * math.pi * e.FO_HZ / FS) / (2 * e.Q_TP2)
    r_formula = math.sqrt((1 - x_fo) / (1 + x_fo))

    # ---- respuesta temporal (filtro corregido) ----
    n = np.arange(80)
    imp = signal.sosfilt(sos_b, (n == 0).astype(float))
    esc = signal.sosfilt(sos_b, np.ones(len(n)))
    np.savetxt(os.path.join(DATOS, 'ej2_tiempo.dat'), np.column_stack([n, n / FS * 1e6, imp, esc]),
               header='n tus imp esc', comments='', fmt='%.6g')
    env = np.abs(imp)
    n1 = int(np.argmax(r_b ** n < 0.01))           # envolvente r^n cae al 1 %

    # ---- senal de prueba (la del script) ----
    t, x, tonos = e.senal_prueba(FS, 4096)
    y = signal.sosfilt(sos_b, x)
    fx, ex = e.espectro(x, FS)
    _, ey = e.espectro(y, FS)
    sel = fx <= 100e3
    paso = 2                                         # se reduce el archivo (sin perder los picos)
    np.savetxt(os.path.join(DATOS, 'ej2_espectro.dat'),
               np.column_stack([fx[sel][::paso] / 1e3, ex[sel][::paso], ey[sel][::paso]]),
               header='f ex ey', comments='', fmt='%.5g')
    tonos_res = []
    for ft in tonos:
        k = np.argmin(abs(fx - ft))
        k = k - 2 + int(np.argmax(ex[k - 2:k + 3]))
        medido = ey[k] - ex[k]
        _, ht = signal.sosfreqz(sos_b, worN=[ft], fs=FS)
        tonos_res.append((ft, ex[k], ey[k], medido, db(ht)[0]))

    # ---- cuantizacion ----
    filas_bits = []
    resumen_bits = {}
    for bits in (None, 16, 14, 12, 11, 10, 8, 6, 4):
        fila = [r'$\infty$' if bits is None else str(bits)]
        for nombre, sos in (('fo', sos_fo), ('b', sos_b)):
            s = sos if bits is None else e.cuantizar(sos, bits)[0]
            r, d12, dmax, ok = cumple(s, fp1, fp2)
            resumen_bits[(nombre, bits)] = ok
            fila += [f"\\num{{{num(r, 3)}}}", f"\\num{{{num(d12.min() - gdb, 3)}}}",
                     f"\\num{{{num(dmax - gdb, 3)}}}", 'Sí' if ok else 'No']
        filas_bits.append(' & '.join(fila) + r' \\')
    with open(os.path.join(DATOS, 'ej2_tabla_bits.tex'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(filas_bits) + '\n\\bottomrule\n')
    min_bits = min(b for (nom, b), ok in resumen_bits.items()
                   if nom == 'b' and b is not None and ok and
                   all(resumen_bits[('b', bb)] for bb in (16, 14, 12, 11, 10, 8, 6, 4) if bb >= b))

    # ---- numeros para el texto ----
    _, h12_fo = signal.sosfreqz(sos_fo, worN=[fp1, fp2], fs=FS)
    _, h12_b = signal.sosfreqz(sos_b, worN=[fp1, fp2], fs=FS)
    _, hmax_b = signal.sosfreqz(sos_b, worN=[e.FO_HZ], fs=FS)
    hs12 = e.respuesta_s(np.array([fp1, fp2]))
    th = math.pi * e.FO_HZ / FS
    factor = 2 * th / math.sin(2 * th)               # angostamiento de la banda en fo
    f3 = lambda sos: (lambda fw, dd: fw[np.where(np.diff(np.sign(dd - (dd.max() - 3))))[0]])(
        np.linspace(1e3, FS / 2 * 0.999, 400000),
        db(signal.sosfreqz(sos, worN=np.linspace(1e3, FS / 2 * 0.999, 400000), fs=FS)[1]))
    c3_s = (lambda fw: fw[np.where(np.diff(np.sign(db(e.respuesta_s(fw)) - (gdb - 3))))[0]])(
        np.linspace(1e3, FS / 2 * 0.999, 400000))
    c3_fo, c3_b = f3(sos_fo), f3(sos_b)
    _, h90 = signal.sosfreqz(sos_b, worN=[90e3], fs=FS)
    hs90 = e.respuesta_s(np.array([90e3]))
    m = {
        'Fs': num(FS / 1e3, 0), 'Fpuno': num(fp1, 0), 'Fpdos': num(fp2, 0), 'Eps': num(e.EPSILON, 5),
        'Q': num(e.Q_TP2, 4), 'Gdb': num(gdb, 2), 'Spec': num(gdb - e.AMAX_DB, 2),
        'Kbil': f"{2 * math.pi * e.FO_HZ / math.tan(th):.5e}",
        'Bfo': num(sos_fo[0][0], 5), 'Afo': num(sos_fo[0][4], 5), 'Adfo': num(sos_fo[0][5], 5),
        'Bb': num(sos_b[0][0], 5), 'Ab': num(sos_b[0][4], 5), 'Adb': num(sos_b[0][5], 5),
        'FoB': num(w0b / (2 * math.pi), 0), 'QB': num(qb, 4),
        'DbFoUno': num(db(h12_fo)[0] - gdb, 3), 'DbFoDos': num(db(h12_fo)[1] - gdb, 3),
        'DbBUno': num(db(h12_b)[0] - gdb, 3), 'DbBDos': num(db(h12_b)[1] - gdb, 3),
        'DbSUno': num(db(hs12)[0] - gdb, 3), 'DbSDos': num(db(hs12)[1] - gdb, 3),
        'DbCentroB': num(db(hmax_b)[0], 2),
        'Factor': num((factor - 1) * 100, 1),
        'TresSuno': num(c3_s[0] / 1e3, 2), 'TresSdos': num(c3_s[1] / 1e3, 2),
        'TresFouno': num(c3_fo[0] / 1e3, 2), 'TresFodos': num(c3_fo[1] / 1e3, 2),
        'TresBuno': num(c3_b[0] / 1e3, 2), 'TresBdos': num(c3_b[1] / 1e3, 2),
        'DbNoventaZ': num(db(h90)[0], 1), 'DbNoventaS': num(db(hs90)[0], 1),
        'RFo': num(r_fo, 4), 'RB': num(r_b, 4), 'RFormula': num(r_formula, 4), 'AngB': num(ang_b, 2),
        'Nuno': str(n1), 'TUno': num(n1 / FS * 1e6, 0), 'Hcero': num(imp[0], 3),
        'MinBits': str(min_bits), 'Ciclos': num(72e6 / FS, 0), 'FsMaxPlaca': num(72e6 / 932 / 1e3, 0),
    }
    for i, (ft, ein, eout, med, teo) in enumerate(tonos_res):
        s = ['Uno', 'Dos', 'Tres'][i]
        m[f'Tono{s}'] = num(ft / 1e3, 0)
        m[f'Tono{s}Med'] = num(med, 2)
        m[f'Tono{s}Teo'] = num(teo, 2)
    with open(os.path.join(DATOS, 'resultados_ej2.tex'), 'w', encoding='utf-8') as fh:
        fh.write("% Generado por generar_ej2.py: no editar a mano\n")
        for k, v in m.items():
            fh.write(f"\\newcommand{{\\ej{k}}}{{{v}}}\n")
    for k, v in m.items():
        print(f"{k:12s} {v}")
    print(open(os.path.join(DATOS, 'ej2_tabla_bits.tex')).read())


if __name__ == '__main__':
    main()
