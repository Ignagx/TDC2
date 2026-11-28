#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
generar_datos.py - Datos y numeros del Ejercicio 1 para el informe.

Lee las mediciones hechas con graficador.py (ver CONFIGURACION) y escribe en datos/:
  bode_medido.dat, bode_modelo.dat   barrido medido y curvas de H(z), Sallen-Key del TP2
  tp2_medido.dat                     los dos puntos medidos del Sallen-Key en el TP2
  escalon.dat                        flanco de subida medido y respuesta simulada de H(z)
  tabla_barrido.tex, tabla_estatica.tex, tabla_aliasing.tex   filas de las tablas
  resultados.tex                     macros \resXxx con los numeros citados en el texto
Si falta una medicion, sus macros quedan en "??" y el informe compila igual.

Uso (desde informe/):  python generar_datos.py
"""
import math
import os
import sys

import numpy as np
from scipy import optimize, signal

AQUI = os.path.dirname(os.path.abspath(__file__))
TP = os.path.dirname(AQUI)
DATOS = os.path.join(AQUI, 'datos')
sys.path.insert(0, TP)
from graficador import medir  # noqa: E402  (el mismo ajuste senoidal del graficador)

# =============================================================================
# CONFIGURACION: archivos de cada medicion (en la carpeta del TP)
# =============================================================================
BARRIDO = 'barrido_20261127_204457.csv'      # barrido de 1 a 100 Hz (punto 3)
OFFSET_BARRIDO_V = 0.72                      # continua de ese barrido (medida en las capturas)
ESTATICA = {4: 'captura_20261127_221322.csv',     # generador digital, continua
            8: 'captura_20261127_221357.csv',
            12: 'captura_20261127_221544.csv',
            16: 'captura_20261127_221635.csv',
            20: 'captura_20261127_221759.csv'}
ESCALON = ['captura_20261127_222053.csv']    # onda cuadrada de 0,5 Hz, 0,65 a 3,04 V
ALIASING = {950: 'captura_20261127_215448.csv',   # (215535 es la misma, repetida)
            990: 'captura_20261127_215601.csv',
            1010: 'captura_20261127_215625.csv'}
SOSPECHOSOS = (9.0, 12.0)                    # puntos del barrido que se excluyen del ajuste

FS = 1000.0
FC_NOM, Q_NOM = 10.0, 1 / math.sqrt(2)
# Sallen-Key del TP2 (Etapa 2 del modulo de 4-20 mA), valores comerciales
R1, R2, C1, C2 = 8.2e3, 15e3, 2.2e-6, 1e-6
TP2_FC_MED, TP2_DB50_MED = 10.83, -27.8      # medidos en el TP2
V_POR_MA = 0.15                              # 0,6 V = 4 mA, 3,0 V = 20 mA


def num(x, dec):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return '??'
    if round(x, dec) == 0:
        x = 0.0
    return f"{x:.{dec}f}".replace('.', ',')


def hz_bilineal(f0, q, k, fs=FS):
    """H(z) de K w0^2/(s^2 + w0/Q s + w0^2) por bilineal con predistorsion en f0."""
    w0 = 2 * math.pi * f0
    kb = w0 / math.tan(math.pi * f0 / fs)
    return signal.bilinear([k * w0 ** 2], [1.0, w0 / q, w0 ** 2], fs=kb / 2)


def resp(ba, f):
    return signal.freqz(*ba, worN=np.atleast_1d(f), fs=FS)[1]


def resp_s(f, f0, q, k=1.0):
    w0 = 2 * math.pi * f0
    return signal.freqs([k * w0 ** 2], [1.0, w0 / q, w0 ** 2], worN=2 * np.pi * np.atleast_1d(f))[1]


def leer(nombre):
    d = np.loadtxt(os.path.join(TP, nombre), delimiter=',', comments='#')
    return d[:, 0], d[:, 1], d[:, 2]


def analizar_escalon(x, y):
    """
    Mide sobrepico, tiempo de pico y de establecimiento (2 %) en un flanco de la onda cuadrada.
    Usa el primer flanco de subida con al menos 50 muestras antes y 400 despues; si no hay,
    uno de bajada (para un sistema lineal da los mismos parametros).
    """
    medio = (x.min() + x.max()) / 2
    for signo in (1, -1):
        xs, ys = signo * x, signo * y
        flancos = np.where((xs[:-1] < signo * medio) & (xs[1:] >= signo * medio))[0] + 1
        for n0 in flancos:
            if n0 < 50 or n0 + 400 > len(x):
                continue
            fin = min(n0 + 900, len(x))
            y0 = ys[max(0, n0 - 150):n0].mean()
            yf = ys[n0 + 300:fin].mean()
            tramo = ys[n0:n0 + 300]
            npico = int(np.argmax(tramo))
            mp = (tramo[npico] - yf) / (yf - y0)
            fuera = np.where(np.abs(ys[n0:fin] - yf) > 0.02 * abs(yf - y0))[0]
            nts = int(fuera[-1]) + 1 if len(fuera) else 0
            return {'n0': n0, 'signo': signo, 'y0': signo * y0, 'yf': signo * yf, 'mp': mp,
                    'tp': npico / FS, 'ts': nts / FS,
                    'x0': x[max(0, n0 - 150):n0].mean(), 'xf': x[n0 + 300:fin].mean()}
    return None


def main():
    m = {}

    # ---------------- 3. barrido ----------------
    d = np.loadtxt(os.path.join(TP, BARRIDO), delimiter=',', comments='#')
    f, vin, vout, dbm, fase = d.T[:5]
    offset = float(np.median(d[:, 5])) if d.shape[1] > 5 else OFFSET_BARRIDO_V
    orden = np.argsort(f)
    f, vin, vout, dbm, fase = f[orden], vin[orden], vout[orden], dbm[orden], fase[orden]
    hm = 10 ** (dbm / 20) * np.exp(1j * np.radians(fase))
    sosp = np.array([any(abs(fi - s) < 0.1 for s in SOSPECHOSOS) for fi in f])
    buenos = ~sosp

    def residuos(p):
        e = np.log(hm[buenos] / resp(hz_bilineal(*p), f[buenos]))
        return np.concatenate([e.real, e.imag])
    r = optimize.least_squares(residuos, [FC_NOM, Q_NOM, 1.0])
    cov = np.sum(r.fun ** 2) / (2 * buenos.sum() - 3) * np.linalg.inv(r.jac.T @ r.jac)
    (fc_f, q_f, k_f), (sfc, sq, sk) = r.x, np.sqrt(np.diag(cov))

    def cruce(y, nivel):
        for j in range(len(y) - 1):
            if (y[j] - nivel) * (y[j + 1] - nivel) <= 0:
                return 10 ** np.interp(nivel, [y[j + 1], y[j]], np.log10([f[j + 1], f[j]]))
    f3 = cruce(dbm, dbm[0] - 3)
    j50 = np.argmin(abs(f - 50))
    j100 = np.argmin(abs(f - 100))
    pend = (dbm[j100] - dbm[j50]) / np.log10(f[j100] / f[j50])

    # ---------------- 2. escalon ----------------
    esc = None
    for nombre in ESCALON:
        t, x, y = leer(nombre)
        esc = analizar_escalon(x, y)
        if esc:
            esc['x'], esc['y'] = x, y
            break
    if esc:
        lmp = math.log(esc['mp'])
        zeta = -lmp / math.sqrt(math.pi ** 2 + lmp ** 2)
        wn = math.pi / (esc['tp'] * math.sqrt(1 - zeta ** 2))
        fn, q_e = wn / (2 * math.pi), 1 / (2 * zeta)
    else:
        zeta = wn = fn = q_e = None

    # H(s) identificada: la del escalon si hay, si no la del barrido
    fc_id, q_id = (fn, q_e) if esc else (fc_f, q_f)
    ba = hz_bilineal(fc_id, q_id, 1.0)
    ba_nom = hz_bilineal(FC_NOM, Q_NOM, 1.0)
    h = resp(ba_nom, f)
    edb = dbm - 20 * np.log10(abs(h))
    efa = fase - np.degrees(np.angle(h))

    # respuesta al escalon esperada de H(z) nominal
    n = np.arange(700)
    y_sim = signal.lfilter(*ba_nom, np.ones(len(n)))
    mp_sim = y_sim.max() - 1
    tp_sim = np.argmax(y_sim) / FS
    ts_sim = (np.where(abs(y_sim - 1) > 0.02)[0][-1] + 1) / FS
    if esc:
        n0, amp = esc['n0'], esc['yf'] - esc['y0']
        sel = slice(n0 - 50, n0 + 400)
        tt = (np.arange(len(esc['y']))[sel] - n0) / FS * 1e3
        sim = np.concatenate([np.zeros(50), y_sim[:400]]) * amp + esc['y0']
        np.savetxt(os.path.join(DATOS, 'escalon.dat'),
                   np.column_stack([tt, esc['x'][sel], esc['y'][sel], sim]),
                   header='t x y sim', comments='', fmt='%.6g')
    else:                         # sin medicion: solo la respuesta esperada de 0,6 V a 3,0 V
        tt = np.arange(-50, 400)
        sim = np.concatenate([np.zeros(50), y_sim[:400]]) * 2.4 + 0.6
        nan = np.full(len(tt), np.nan)
        np.savetxt(os.path.join(DATOS, 'escalon.dat'), np.column_stack([tt, nan, nan, sim]),
                   header='t x y sim', comments='', fmt='%.6g')

    # ---------------- tablas y curvas del barrido ----------------
    filas = []
    for i in range(len(f)):
        dt = -fase[i] / (360 * f[i]) * 1e3
        marca = '$^{*}$' if sosp[i] else ''
        celdas = [num(dbm[i], 2), num(fase[i], 1), num(dt, 1), num(edb[i], 2), num(efa[i], 1)]
        filas.append(f"\\num{{{num(f[i], 2)}}}{marca} & " + " & ".join(f"\\num{{{c}}}" for c in celdas)
                     + " \\\\")
    with open(os.path.join(DATOS, 'tabla_barrido.tex'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(filas) + '\n\\bottomrule\n')
    for nombre, mask in (('medido_ok.dat', buenos), ('medido_sosp.dat', sosp)):
        np.savetxt(os.path.join(DATOS, nombre),
                   np.column_stack([f[mask], dbm[mask], fase[mask], edb[mask], efa[mask]]),
                   header='f db fase edb efa', comments='', fmt='%.6g')
    w0sk = 1 / math.sqrt(R1 * R2 * C1 * C2)
    f0sk, qsk = w0sk / (2 * math.pi), math.sqrt(R1 * R2 * C1 * C2) / (C2 * (R1 + R2))
    fg = np.logspace(np.log10(0.5), np.log10(499), 600)
    hz_g, hsk = resp(ba, fg), resp_s(fg, f0sk, qsk)
    np.savetxt(os.path.join(DATOS, 'bode_modelo.dat'),
               np.column_stack([fg, 20 * np.log10(abs(hz_g)), np.degrees(np.unwrap(np.angle(hz_g))),
                                20 * np.log10(abs(hsk)), np.degrees(np.unwrap(np.angle(hsk)))]),
               header='f db fase dbsk fasesk', comments='', fmt='%.6g')
    np.savetxt(os.path.join(DATOS, 'tp2_medido.dat'), np.array([[TP2_FC_MED, -3.0], [50.0, TP2_DB50_MED]]),
               header='f db', comments='', fmt='%.6g')
    hsk50, hz50 = resp_s(50.0, f0sk, qsk)[0], resp(ba_nom, 50.0)[0]
    hsk500, hz500 = resp_s(500.0 - 1e-6, f0sk, qsk)[0], None
    # frecuencia de -3 dB del Sallen-Key con valores comerciales
    fsk3 = optimize.brentq(lambda x: 20 * np.log10(abs(resp_s(x, f0sk, qsk)[0])) + 3, 1, 50)

    # ---------------- 1. estatica ----------------
    filas_e, vins, vouts = [], [], []
    for ma in (4, 8, 12, 16, 20):
        if ma in ESTATICA:
            _, x, y = leer(ESTATICA[ma])
            vi, vo = x.mean(), y.mean()
            vins.append(vi); vouts.append(vo)
            err = (vo - vi) / V_POR_MA
            filas_e.append(f"\\num{{{num(4 + (vi - 0.6) / V_POR_MA, 3)}}} & \\num{{{num(vi, 4)}}} & "
                           f"\\num{{{num(vo, 4)}}} & \\num{{{num(4 + (vo - 0.6) / V_POR_MA, 3)}}} & "
                           f"\\num{{{num(err * 1e3, 1)}}} \\\\")
        else:
            filas_e.append(f"{ma} & ?? & ?? & ?? & ?? \\\\")
    with open(os.path.join(DATOS, 'tabla_estatica.tex'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(filas_e) + '\n\\bottomrule\n')
    if len(vins) >= 2:
        pend_e, ord_e = np.polyfit(vins, vouts, 1)
        err_max = max(abs(np.array(vouts) - np.array(vins))) / V_POR_MA * 1e3
    else:
        pend_e = ord_e = err_max = None

    # ---------------- 6. aliasing ----------------
    filas_a = []
    for fg_al in (950, 990, 1010):
        falias = abs(fg_al - FS * round(fg_al / FS))
        teo = 20 * np.log10(abs(resp(ba_nom, falias)[0]))
        if fg_al in ALIASING:
            _, x, y = leer(ALIASING[fg_al])
            mm = medir(x, y, FS)
            teo = 20 * np.log10(abs(resp(ba_nom, mm['f'])[0]))   # en la frecuencia de alias medida
            filas_a.append(f"{fg_al} & \\num{{{num(falias, 0)}}} & \\num{{{num(mm['f'], 2)}}} & "
                           f"\\num{{{num(mm['db'], 2)}}} & \\num{{{num(teo, 2)}}} \\\\")
        else:
            filas_a.append(f"{fg_al} & \\num{{{num(falias, 0)}}} & ?? & ?? & \\num{{{num(teo, 2)}}} \\\\")
    with open(os.path.join(DATOS, 'tabla_aliasing.tex'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(filas_a) + '\n\\bottomrule\n')

    # ---------------- macros ----------------
    m.update({
        'NPuntos': str(len(f)), 'NBuenos': str(int(buenos.sum())),
        'VinPP': num(np.median(vin), 2), 'OffsetBarrido': num(offset, 2),
        'FTres': num(f3, 2), 'DbCincuenta': num(dbm[j50], 2), 'Pend': num(pend, 1),
        'FcFit': num(fc_f, 4), 'SFcFit': num(sfc, 4), 'QFit': num(q_f, 4), 'SQFit': num(sq, 4),
        'KFit': num(k_f, 4), 'SKFit': num(sk, 4),
        'MaxEdb': num(np.max(abs(edb[buenos])), 3), 'MaxEfa': num(np.max(abs(efa[buenos])), 2),
        'DtDiez': num(-fase[np.argmin(abs(f - 10))] / (360 * f[np.argmin(abs(f - 10))]) * 1e3, 1),
        'Mp': num(esc['mp'] * 100 if esc else None, 2), 'Tp': num(esc['tp'] * 1e3 if esc else None, 0),
        'Ts': num(esc['ts'] * 1e3 if esc else None, 0),
        'Zeta': num(zeta, 3), 'Wn': num(wn, 1), 'Fn': num(fn, 2), 'QEsc': num(q_e, 3),
        'MpSim': num(mp_sim * 100, 2), 'TpSim': num(tp_sim * 1e3, 0), 'TsSim': num(ts_sim * 1e3, 0),
        'EscBajo': num(esc['x0'] if esc else None, 2), 'EscAlto': num(esc['xf'] if esc else None, 2),
        'FcId': num(fc_id, 2), 'QId': num(q_id, 3),
        'Bcero': f"{ba[0][0]:.4e}", 'Buno': f"{ba[0][1]:.4e}", 'Bdos': f"{ba[0][2]:.4e}",
        'Auno': num(ba[1][1], 5), 'Ados': num(ba[1][2], 5),
        'FoSK': num(f0sk, 2), 'QSK': num(qsk, 3), 'FtresSK': num(fsk3, 2),
        'DbCincuentaSK': num(20 * np.log10(abs(hsk50)), 1), 'DbCincuentaZ': num(20 * np.log10(abs(hz50)), 2),
        'TPdosFc': num(TP2_FC_MED, 2), 'TPdosDb': num(TP2_DB50_MED, 1),
        'GanDC': num(pend_e, 4), 'OrdDC': num(ord_e * 1e3 if ord_e is not None else None, 1),
        'ErrMax': num(err_max, 1),
    })
    with open(os.path.join(DATOS, 'resultados.tex'), 'w', encoding='utf-8') as fh:
        fh.write("% Generado por generar_datos.py: no editar a mano\n")
        for k, v in m.items():
            fh.write(f"\\newcommand{{\\res{k}}}{{{v}}}\n")
    for k, v in m.items():
        print(f"{k:14s} {v}")


if __name__ == '__main__':
    main()
