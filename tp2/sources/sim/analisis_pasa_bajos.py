"""
TP2 Teoria de Circuitos II - Grupo 2
Filtro pasa bajos Butterworth de orden 4 (Sallen-Key, 2 celdas con G = 2 V/V)

Lee los resultados de LTspice (.raw binarios) y genera las figuras del informe:
  - PasaBajos_Ideal_vs_Comercial.raw -> valores calculados / comerciales con AO ideal
  - Filtro_PasaBajos_Solo_TL084.raw   -> valores comerciales con macromodelo TL084

Antes de ejecutar, correr ambas simulaciones (LTspice -b <archivo>).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

AQUI = Path(__file__).resolve().parent
IMAGENES = AQUI.parent.parent / "images"

# ---------------------------------------------------------------- especificaciones
AMAX = 1.5           # dB
FP = 5.5e3           # Hz
N = 4
K = 2.0 ** 2         # ganancia total (4 V/V)
EPS = np.sqrt(10 ** (AMAX / 10) - 1)
F0 = FP / EPS ** (1 / N)


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


def cruce_bajada(f, mag_db, nivel):
    """Primera frecuencia (interpolada en log f) donde mag_db cae por debajo de 'nivel'."""
    k = np.where(np.diff(np.sign(mag_db - nivel)) < 0)[0][0]
    x = np.log10(f[k: k + 2])
    return 10 ** np.interp(nivel, mag_db[k: k + 2][::-1], x[::-1])


def h_teorica(f):
    """Butterworth pasa bajos ideal de orden 4 desnormalizado a f0."""
    s = 1j * f / F0
    q1, q2 = 1 / (2 * np.cos(np.pi / 8)), 1 / (2 * np.cos(3 * np.pi / 8))
    return K / ((s ** 2 + s / q1 + 1) * (s ** 2 + s / q2 + 1))


ideal = leer_raw("PasaBajos_Ideal_vs_Comercial.raw")
real = leer_raw("Filtro_PasaBajos_Solo_TL084.raw")

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
    fc = cruce_bajada(ff, m, G0 - 3.0103)
    def en(fx): return np.interp(np.log10(fx), np.log10(ff), m)
    fase_fc = np.interp(np.log10(fc), np.log10(ff), np.unwrap(np.angle(h)) * 180 / np.pi)
    print(f"{nombre:32s} fc(-3dB vs K) = {fc:8.1f} Hz | Gmax = {gmax:6.3f} dB @ {fgmax/1e3:6.2f} kHz"
          f" | A(fp) = {G0 - en(FP):5.3f} dB | |H|(2fp) = {en(2*FP):6.2f} dB | |H|(10fp) = {en(10*FP):7.2f} dB"
          f" | |H|(1M) = {en(1e6):7.2f} dB | fase(fc) = {fase_fc:6.1f} deg")


# ---------------------------------------------------------------- figura 1: Bode completo
def fase_grados(h):
    """Fase desenrollada; a baja frecuencia un pasa bajos tiende a 0 grados."""
    fase = np.unwrap(np.angle(h)) * 180 / np.pi
    return fase - 360 * np.round(fase[0] / 360)


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.2), sharex=True)
for nombre, (ff, h) in curvas.items():
    ax1.semilogx(ff, 20 * np.log10(abs(h)), label=nombre, **estilos[nombre])
    ax2.semilogx(ff, fase_grados(h), label=nombre, **estilos[nombre])
ax1.axvline(FP, color="gray", ls=":", lw=1)
ax1.axvline(F0, color="gray", ls=":", lw=1)
ax1.text(FP / 1.45, -95, r"$f_p$", color="gray")
ax1.text(F0 * 1.06, -95, r"$f_0$", color="gray")
ax1.axhline(G0 - 3.0103, color="gray", ls=":", lw=1)
ax1.set_ylim(-110, 25)
ax1.set_ylabel("Módulo [dB]")
ax1.grid(True, which="both", alpha=0.35)
ax1.legend(loc="lower left", fontsize=9)
ax1.set_title("Filtro pasa bajos Butterworth de orden 4 — respuesta en frecuencia")
ax2.set_ylabel("Fase [°]")
ax2.set_xlabel("Frecuencia [Hz]")
ax2.set_yticks(np.arange(-900, 1, 180))
ax2.grid(True, which="both", alpha=0.35)
ax2.set_xlim(10, 1e7)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig1_pb_bode_comparativo.{ext}", dpi=200)

# ---------------------------------------------------------------- figura 2: zoom banda de paso
fig, ax = plt.subplots(figsize=(9, 4.6))
for nombre, (ff, h) in curvas.items():
    ax.semilogx(ff, 20 * np.log10(abs(h)), label=nombre, **estilos[nombre])
ax.axhline(G0, color="gray", ls=":", lw=1)
ax.axhline(G0 - AMAX, color="tab:orange", ls=":", lw=1.2)
ax.axhline(G0 - 3.0103, color="gray", ls=":", lw=1)
ax.axvline(FP, color="tab:orange", ls=":", lw=1.2)
ax.axvline(F0, color="gray", ls=":", lw=1)
ax.text(1050, G0 + 0.15, rf"$K$ = {G0:.2f} dB", color="gray", fontsize=9)
ax.text(1050, G0 - AMAX + 0.15, rf"$K - A_{{max}}$ = {G0 - AMAX:.2f} dB", color="tab:orange", fontsize=9)
ax.text(1050, G0 - 3.0103 + 0.15, rf"$K - 3$ dB = {G0 - 3.01:.2f} dB", color="gray", fontsize=9)
ax.set_xlim(1e3, 1.2e4)
ax.set_ylim(5, 12.8)
ax.set_xlabel("Frecuencia [Hz]")
ax.set_ylabel("Módulo [dB]")
ax.grid(True, which="both", alpha=0.35)
ax.legend(loc="lower left", fontsize=9)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig2_pb_zoom_banda_paso.{ext}", dpi=200)
