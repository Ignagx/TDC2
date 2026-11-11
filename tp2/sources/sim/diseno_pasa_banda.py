"""
TP2 Teoria de Circuitos II - Grupo 2
Filtro pasa banda Butterworth de orden 2 - celda Sallen-Key pasa banda (Topologia I, Barbero et al. 10.5.3)

Calculo de diseno: especificaciones -> Qp, w0 -> componentes ideales -> valores comerciales -> recalculo.
Todos los numeros del capitulo salen de este script.

Topologia I:  ue --R1-- uf ; uf --C1-- masa ; uf --C2-- u+ ; u+ --R2-- masa ; uf --Rf-- us ; us = G u+
              G = 1 + Rb/Ra

  H(s) = (G/(R1 C1)) s / [ s^2 + s( (1-G)/(Rf C1) + 1/(R1 C1) + 1/(R2 C1) + 1/(R2 C2) ) + (R1+Rf)/(R1 R2 Rf C1 C2) ]
"""
import numpy as np

# ---------------------------------------------------------------- especificaciones (Grupo 2)
AMAX = 0.1           # dB, atenuacion maxima en la banda de paso
F0 = 28e3            # Hz, frecuencia central
BW = 1.7e3           # Hz, ancho de banda de paso fp2 - fp1 (medido a Amax)
AM = 9.0             # V/V, ganancia en el centro de la banda

W0 = 2 * np.pi * F0
EPS = np.sqrt(10 ** (AMAX / 10) - 1)
QP = EPS * F0 / BW
BW3 = BW / EPS


def bordes(f0, bw):
    """Bordes geometricamente simetricos de una banda de ancho bw centrada en f0."""
    f1 = -bw / 2 + np.sqrt((bw / 2) ** 2 + f0 ** 2)
    return f1, f1 + bw


def parametros(R1, R2, Rf, C1, C2, G):
    """w0, Qp, ganancia central K y coeficientes del denominador de la celda."""
    b0 = (R1 + Rf) / (R1 * R2 * Rf * C1 * C2)
    b1 = (1 - G) / (Rf * C1) + 1 / (R1 * C1) + 1 / (R2 * C1) + 1 / (R2 * C2)
    a1 = G / (R1 * C1)
    w0 = np.sqrt(b0)
    return dict(w0=w0, f0=w0 / 2 / np.pi, Q=w0 / b1, K=a1 / b1, a1=a1, b1=b1, b0=b0,
                Gosc=1 + Rf / R1 + Rf / R2 + Rf * C1 / (R2 * C2))


def H(f, p):
    s = 2j * np.pi * f
    return p["a1"] * s / (s ** 2 + p["b1"] * s + p["b0"])


def f_corte(p, nivel_db):
    """Frecuencias donde |H| cae 'nivel_db' respecto de K (forma cerrada para 2do orden)."""
    eps = np.sqrt(10 ** (nivel_db / 10) - 1)
    return bordes(p["f0"], eps * p["f0"] / p["Q"])


# valores comerciales adoptados (ver seccion 5 del calculo)
COM = dict(R1=2.2e3, R2=13e3, Rf=2.2e3, C1=1.5e-9, C2=1.5e-9, Ra=5.6e3, Rb=6.2e3)


def resumen(nombre, p):
    fp1, fp2 = f_corte(p, AMAX)
    fc1, fc2 = f_corte(p, 3.0103)
    print(f"   [{nombre}] f0 = {p['f0']:.3f} Hz  Q = {p['Q']:.5f}  K = {p['K']:.5f} V/V ({20 * np.log10(p['K']):.3f} dB)"
          f"  Gosc = {p['Gosc']:.4f}")
    print(f"   [{nombre}] a1 = {p['a1']:.5e}  b1 = {p['b1']:.5e}  b0 = {p['b0']:.5e}")
    print(f"   [{nombre}] fp1 = {fp1:.2f}  fp2 = {fp2:.2f}  BW = {fp2 - fp1:.2f} Hz | "
          f"fc1 = {fc1:.2f}  fc2 = {fc2:.2f}  BW3 = {fc2 - fc1:.2f} Hz")


if __name__ == "__main__":
    print("=" * 100)
    print("1) ESPECIFICACIONES Y PARAMETROS DE LA APROXIMACION")
    fp1, fp2 = bordes(F0, BW)
    fc1, fc2 = bordes(F0, BW3)
    print(f"eps = {EPS:.5f}   Qp = eps*f0/BW = {QP:.4f}   BW(-3dB) = BW/eps = {BW3:.2f} Hz")
    print(f"w0 = {W0:.2f} rad/s   w0/Qp = {W0 / QP:.2f} rad/s   w0^2 = {W0 ** 2:.5e}")
    print(f"fp1 = {fp1:.2f} Hz  fp2 = {fp2:.2f} Hz  (fp1*fp2 = {fp1 * fp2:.4e}, f0^2 = {F0 ** 2:.4e})")
    print(f"fc1 = {fc1:.2f} Hz  fc2 = {fc2:.2f} Hz")
    print(f"K = {AM} V/V = {20 * np.log10(AM):.3f} dB ;  K*w0/Qp = {AM * W0 / QP:.5e}")
    print(f"Polos: s = {-W0 / (2 * QP):.2f} +/- j{W0 * np.sqrt(1 - 1 / (4 * QP ** 2)):.2f}")

    print("=" * 100)
    print("2) PARAMETRIZACION R1 = Rf = R, R2 = m R, C1 = C2 = C ; eleccion de m para K = 9")
    # K = G Qp/u - con u = sqrt(2/m), G = 2 + u^2 - u/Qp  ->  K = Qp(2+u^2)/u - 1
    # -> u^2 - (K+1)/Qp u + 2 = 0
    c = (AM + 1) / QP
    raices = np.roots([1, -c, 2])
    print(f"u^2 - {c:.4f} u + 2 = 0  -> u = {raices}")
    for u in sorted(raices):
        m = 2 / u ** 2
        G = 2 + u ** 2 - u / QP
        print(f"   u = {u:.5f}  m = {m:.4f}  G = {G:.4f}  K = G Qp / u = {G * QP / u:.4f}")
    u = min(raices)
    M = 2 / u ** 2
    GID = 2 + u ** 2 - u / QP
    print(f"Se adopta m = {M:.4f}, G = {GID:.5f}  (Rb/Ra = {GID - 1:.5f})")
    print(f"Ganancia de oscilacion Gosc = 2 + 2/m = {2 + 2 / M:.4f}  -> margen {(2 + 2 / M) / GID - 1:.2%}")
    print(f"Sensibilidad S_G^Q = G Qp sqrt(m/2) = {GID * QP * np.sqrt(M / 2):.3f}")
    print(f"S_(Rb/Ra)^Q = S_G^Q (G-1)/G = {GID * QP * np.sqrt(M / 2) * (GID - 1) / GID:.3f}")

    print("=" * 100)
    print("3) BARRIDO DE C (serie E6) -> R")
    for c in [1e-9, 1.5e-9, 2.2e-9, 3.3e-9, 4.7e-9]:
        R = u / (W0 * c)
        print(f"   C = {c * 1e9:4.1f} nF  ->  R1 = Rf = {R:8.2f} ohm   R2 = {M * R:9.2f} ohm")

    C = 1.5e-9
    R = u / (W0 * C)
    RA_ID = 5.6e3
    ideal = dict(R1=R, R2=M * R, Rf=R, C1=C, C2=C, G=GID)
    RB_ID = (GID - 1) * RA_ID
    p = parametros(**ideal)
    print("=" * 100)
    print("4) DISENO IDEAL (C = 1,5 nF, Ra = 5,6 k)")
    for k, v in ideal.items():
        print(f"   {k} = {v:.6g}")
    print(f"   Ra = {RA_ID:.2f}  Rb = {RB_ID:.2f}")
    resumen("ideal", p)

    print("=" * 100)
    print("5) VALORES COMERCIALES (E24 1 %, capacitores E6 5 %)")
    print(f"   R1 = Rf: {R:.2f} -> {COM['R1']:.0f} ({COM['R1'] / R - 1:+.2%})"
          f"   R2: {M * R:.2f} -> {COM['R2']:.0f} ({COM['R2'] / (M * R) - 1:+.2%})")
    mS = COM["R2"] / COM["R1"]
    w0S = np.sqrt(2 / mS) / (COM["R1"] * C)
    # paso b2 del libro: G requerido para el Qp especificado con los pasivos ya normalizados
    Greq = 2 + 2 / mS - np.sqrt(2 / mS) / QP
    print(f"   mS = R2/R1 = {mS:.4f}   f0S = {w0S / 2 / np.pi:.2f} Hz ({w0S / W0 - 1:+.3%})")
    print(f"   G requerido (10-68) = 2 + 2/mS - sqrt(2/mS)/Qp = {Greq:.5f}  ->  Rb = (G-1) Ra = "
          f"{(Greq - 1) * COM['Ra']:.2f} ohm con Ra = {COM['Ra']:.0f}")
    GS = 1 + COM["Rb"] / COM["Ra"]
    print(f"   Rb adoptado = {COM['Rb']:.0f}  ->  GS = {GS:.5f} (error {GS / Greq - 1:+.3%})")
    pc = parametros(COM["R1"], COM["R2"], COM["Rf"], COM["C1"], COM["C2"], GS)
    resumen("comercial", pc)
    print("   desvios respecto del ideal:")
    for k in ("f0", "Q", "K"):
        print(f"     {k}: {pc[k]:.5g} vs {p[k]:.5g}  ({pc[k] / p[k] - 1:+.3%})")
    bw_c = np.diff(f_corte(pc, AMAX))[0]
    bw3_c = np.diff(f_corte(pc, 3.0103))[0]
    print(f"     BW(0,1 dB): {bw_c:.2f} Hz ({bw_c / BW - 1:+.3%})   BW(-3 dB): {bw3_c:.2f} Hz ({bw3_c / BW3 - 1:+.3%})")
    print(f"     K = {pc['K']:.4f} V/V = {20 * np.log10(pc['K']):.3f} dB "
          f"({20 * np.log10(pc['K'] / AM):+.3f} dB respecto de 9 V/V)")
