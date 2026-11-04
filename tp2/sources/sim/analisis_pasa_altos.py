"""
TP2 Teoria de Circuitos II - Grupo 2
Filtro pasa altos Butterworth de orden 4 (Sallen-Key, 2 celdas con G = 3,5 V/V)

Lee los resultados de LTspice (.raw binarios) y genera las figuras del informe:
  - PasaAltos_Ideal_vs_Comercial.raw  -> valores calculados / comerciales con AO ideal
  - Filtro_PasaAltos_Orden4_Grupo2.raw -> valores comerciales con macromodelo TL084

Antes de ejecutar, correr ambas simulaciones (LTspice -b <archivo>).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

AQUI = Path(__file__).resolve().parent
IMAGENES = AQUI.parent.parent / "images"

# ---------------------------------------------------------------- especificaciones
AMAX = 2.25          # dB
FP = 33e3            # Hz
N = 4
K = 3.5 ** 2         # ganancia total adoptada (12,25 V/V)
EPS = np.sqrt(10 ** (AMAX / 10) - 1)
F0 = FP * EPS ** (1 / N)


def leer_raw(nombre):
    """Lector minimo de archivos .raw binarios de LTspice (analisis AC, complejos)."""
    b = (AQUI / nombre).read_bytes()
    clave = "Binary:\n".encode("utf-16le")
    i = b.find(clave)
    lineas = b[:i].decode("utf-16le").splitlines()

    def campo(k):
        return next(l for l in lineas if l.startswith(k)).split(":", 1)[1].strip()

    nv, npt = int(campo("No. Variables")), int(campo("No. Points"))
    iv = lineas.index("Variables:")
    nombres = [l.split("\t")[2].lower() for l in lineas[iv + 1: iv + 1 + nv]]
    datos = np.frombuffer(b[i + len(clave):], dtype="<c16", count=nv * npt).reshape(npt, nv)
    return {n: datos[:, k] for k, n in enumerate(nombres)}


def cruce(f, mag_db, nivel, desde=0, subiendo=True):
    """Frecuencia (interpolada en log f) donde mag_db cruza 'nivel'."""
    s = np.sign(mag_db - nivel)
    idx = np.where(np.diff(s) > 0)[0] if subiendo else np.where(np.diff(s) < 0)[0]
    idx = idx[f[idx] >= desde]
    k = idx[0]
    x = np.log10(f[k: k + 2])
    return 10 ** np.interp(nivel, mag_db[k: k + 2], x) if subiendo else \
        10 ** np.interp(nivel, mag_db[k: k + 2][::-1], x[::-1])


def h_teorica(f):
    """Butterworth pasa altos ideal de orden 4 desnormalizado a f0."""
    s = 1j * f / F0
    q1, q2 = 1 / (2 * np.cos(np.pi / 8)), 1 / (2 * np.cos(3 * np.pi / 8))
    return K * s ** 4 / ((s ** 2 + s / q1 + 1) * (s ** 2 + s / q2 + 1))


ideal = leer_raw("PasaAltos_Ideal_vs_Comercial.raw")
real = leer_raw("Filtro_PasaAltos_Orden4_Grupo2.raw")

f = ideal["frequency"].real
fr = real["frequency"].real
curvas = {
    "Teórica Butterworth": (f, h_teorica(f)),
    "Valores calculados (AO ideal)": (f, ideal["v(vout_calc)"]),
    "Valores comerciales (AO ideal)": (f, ideal["v(vout_com)"]),
    "Valores comerciales + TL084": (fr, real["v(vout)"]),
}
estilos = {
    "Teórica Butterworth": dict(color="k", lw=2.2, ls="-"),
    "Valores calculados (AO ideal)": dict(color="tab:blue", lw=1.4, ls="--"),
    "Valores comerciales (AO ideal)": dict(color="tab:green", lw=1.4, ls="-."),
    "Valores comerciales + TL084": dict(color="tab:red", lw=1.6, ls="-"),
}

# ---------------------------------------------------------------- resultados numericos
G0 = 20 * np.log10(K)
print(f"eps = {EPS:.4f}   f0 = {F0:.2f} Hz   K = {K} V/V ({G0:.2f} dB)")
for nombre, (ff, h) in curvas.items():
    m = 20 * np.log10(abs(h))
    gmax, fgmax = m.max(), ff[np.argmax(m)]
    fc = cruce(ff, m, G0 - 3.0103)
    def en(fx): return np.interp(np.log10(fx), np.log10(ff), m)
    linea = (f"{nombre:32s} fc(-3dB vs K) = {fc/1e3:7.3f} kHz | Gmax = {gmax:6.2f} dB @ {fgmax/1e3:7.1f} kHz"
             f" | A(fp) = {G0 - en(FP):5.2f} dB | |H|(fp/2) = {en(FP/2):6.2f} dB | |H|(fp/10) = {en(FP/10):7.2f} dB"
             f" | |H|(200k) = {en(200e3):6.2f} dB")
    if "TL084" in nombre:
        fc_rel = cruce(ff, m, gmax - 3.0103)
        fsup = cruce(ff, m, gmax - 3.0103, desde=fgmax, subiendo=False)
        fase_fc = np.interp(np.log10(fc), np.log10(ff), np.angle(h, deg=True))
        linea += (f"\n{'':32s} fc(-3dB vs Gmax) = {fc_rel/1e3:7.3f} kHz | f_sup(-3dB vs Gmax) = {fsup/1e3:7.1f} kHz"
                  f" | fase en fc = {fase_fc:6.1f} deg")
    print(linea)


# ---------------------------------------------------------------- figura 1: Bode completo
def fase_grados(h):
    """Fase desenrollada; a baja frecuencia un pasa altos de orden 4 tiende a +360 grados."""
    fase = np.unwrap(np.angle(h)) * 180 / np.pi
    return fase - 360 * np.round((fase[0] - 360) / 360)


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.2), sharex=True)
for nombre, (ff, h) in curvas.items():
    ax1.semilogx(ff, 20 * np.log10(abs(h)), label=nombre, **estilos[nombre])
    ax2.semilogx(ff, fase_grados(h), label=nombre, **estilos[nombre])
ax1.axvline(FP, color="gray", ls=":", lw=1)
ax1.axvline(F0, color="gray", ls=":", lw=1)
ax1.text(FP * 1.05, -75, r"$f_p$", color="gray")
ax1.text(F0 / 1.35, -75, r"$f_0$", color="gray")
ax1.axhline(G0 - 3.0103, color="gray", ls=":", lw=1)
ax1.set_ylim(-90, 30)
ax1.set_ylabel("Módulo [dB]")
ax1.grid(True, which="both", alpha=0.35)
ax1.legend(loc="lower right", fontsize=9)
ax1.set_title("Filtro pasa altos Butterworth de orden 4 — respuesta en frecuencia")
ax2.set_ylabel("Fase [°]")
ax2.set_xlabel("Frecuencia [Hz]")
ax2.set_yticks(np.arange(-270, 361, 90))
ax2.grid(True, which="both", alpha=0.35)
ax2.set_xlim(1e3, 1e7)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig5_pa_bode_comparativo.{ext}", dpi=200)

# ---------------------------------------------------------------- figura 2: zoom banda de paso
fig, ax = plt.subplots(figsize=(9, 4.6))
for nombre, (ff, h) in curvas.items():
    ax.semilogx(ff, 20 * np.log10(abs(h)), label=nombre, **estilos[nombre])
ax.axhline(G0, color="gray", ls=":", lw=1)
ax.axhline(G0 - AMAX, color="tab:orange", ls=":", lw=1.2)
ax.axhline(G0 - 3.0103, color="gray", ls=":", lw=1)
ax.axvline(FP, color="tab:orange", ls=":", lw=1.2)
ax.axvline(F0, color="gray", ls=":", lw=1)
ax.text(1.2e4, G0 + 0.15, rf"$K$ = {G0:.2f} dB", color="gray", fontsize=9)
ax.text(1.2e4, G0 - AMAX + 0.15, rf"$K - A_{{max}}$ = {G0 - AMAX:.2f} dB", color="tab:orange", fontsize=9)
ax.text(1.2e4, G0 - 3.0103 + 0.15, rf"$K - 3$ dB = {G0 - 3.01:.2f} dB", color="gray", fontsize=9)
ax.set_xlim(1e4, 3e6)
ax.set_ylim(12, 23)
ax.set_xlabel("Frecuencia [Hz]")
ax.set_ylabel("Módulo [dB]")
ax.grid(True, which="both", alpha=0.35)
ax.legend(loc="lower center", fontsize=9)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig6_pa_zoom_banda_paso.{ext}", dpi=200)
