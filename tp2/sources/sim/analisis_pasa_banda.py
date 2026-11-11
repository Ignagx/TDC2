"""
TP2 Teoria de Circuitos II - Grupo 2
Filtro pasa banda Butterworth de orden 2 (Sallen-Key topologia I)

Lee los resultados de LTspice (.raw binarios) y genera las figuras del informe:
  - PasaBanda_Ideal_vs_Comercial.raw   -> valores calculados y comerciales, AO ideal
  - Filtro_PasaBanda_Orden2_Grupo2.raw -> valores comerciales + TL084

Antes de ejecutar, correr ambas simulaciones (LTspice -b <archivo>). Ejecutar desde sources/sim/.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from diseno_pasa_banda import AM, AMAX, BW, EPS, F0, QP, bordes

AQUI = Path(__file__).resolve().parent
IMAGENES = AQUI.parent.parent / "images"

G0 = 20 * np.log10(AM)
W0 = 2 * np.pi * F0
FP1, FP2 = bordes(F0, BW)
FC1, FC2 = bordes(F0, BW / EPS)


def leer_raw(nombre):
    """Lector minimo de archivos .raw binarios de LTspice (AC complejo o transitorio real)."""
    b = (AQUI / nombre).read_bytes()
    clave = "Binary:\n".encode("utf-16le")
    i = b.find(clave)
    lineas = b[:i].decode("utf-16le").splitlines()

    def campo(k):
        return next(l for l in lineas if l.startswith(k)).split(":", 1)[1].strip()

    nv, npt = int(campo("No. Variables")), int(campo("No. Points"))
    iv = lineas.index("Variables:")
    nombres = [l.split("\t")[2].lower() for l in lineas[iv + 1: iv + 1 + nv]]
    datos = b[i + len(clave):]
    if "complex" in campo("Flags"):
        d = np.frombuffer(datos, dtype="<c16", count=nv * npt).reshape(npt, nv)
        return {n: d[:, k] for k, n in enumerate(nombres)}
    # transitorio: tiempo en float64, el resto en float32
    tipo = np.dtype([("t", "<f8")] + [(f"v{k}", "<f4") for k in range(1, nv)])
    d = np.frombuffer(datos, dtype=tipo, count=npt)
    offset = float(campo("Offset")) if any(l.startswith("Offset") for l in lineas) else 0.0
    salida = {nombres[0]: np.abs(d["t"]) + offset}   # LTspice guarda el tiempo relativo al Offset
    salida.update({n: d[f"v{k}"].astype(float) for k, n in enumerate(nombres) if k > 0})
    return salida


def cruce(f, mag_db, nivel, subiendo=True):
    """Frecuencia (interpolada en log f) donde mag_db cruza 'nivel' (primer cruce ascendente o ultimo descendente)."""
    s = np.sign(mag_db - nivel)
    if subiendo:
        k = np.where(np.diff(s) > 0)[0][0]
        return 10 ** np.interp(nivel, mag_db[k: k + 2], np.log10(f[k: k + 2]))
    k = np.where(np.diff(s) < 0)[0][-1]
    return 10 ** np.interp(nivel, mag_db[k: k + 2][::-1], np.log10(f[k: k + 2])[::-1])


def h_teorica(f):
    """Pasa banda Butterworth de orden 2: H(s) = K (w0/Qp) s / (s^2 + (w0/Qp) s + w0^2)."""
    s = 2j * np.pi * f
    return AM * (W0 / QP) * s / (s ** 2 + (W0 / QP) * s + W0 ** 2)


def caracterizar(f, h):
    """Frecuencias y ganancias caracteristicas de una respuesta pasa banda."""
    m = 20 * np.log10(abs(h))
    gmax = m.max()
    fc1, fc2 = cruce(f, m, gmax - 3.0103), cruce(f, m, gmax - 3.0103, False)
    fp1, fp2 = cruce(f, m, gmax - AMAX), cruce(f, m, gmax - AMAX, False)
    f0 = np.sqrt(fc1 * fc2)

    def en(fx):
        return np.interp(np.log10(fx), np.log10(f), m)

    fase_f0 = np.interp(np.log10(f0), np.log10(f), np.angle(h, deg=True))
    return dict(Gmax=gmax, fmax=f[np.argmax(m)], fc1=fc1, fc2=fc2, f0=f0, Q=f0 / (fc2 - fc1), fp1=fp1, fp2=fp2,
                BW=fp2 - fp1, BW3=fc2 - fc1, A_banda=gmax - min(en(FP1), en(FP2)), H_f0=en(F0), fase_f0=fase_f0,
                H_2f0=en(2 * F0), H_f0_2=en(F0 / 2), H_10f0=en(10 * F0), H_f0_10=en(F0 / 10))


ideal = leer_raw("PasaBanda_Ideal_vs_Comercial.raw")
nominal = leer_raw("Filtro_PasaBanda_Orden2_Grupo2.raw")
f = ideal["frequency"].real
curvas = {
    "Teórica Butterworth": (f, h_teorica(f)),
    "Valores calculados (AO ideal)": (f, ideal["v(vout_calc)"]),
    "Valores comerciales (AO ideal)": (f, ideal["v(vout_com)"]),
    "Valores comerciales + TL084": (nominal["frequency"].real, nominal["v(vout)"]),
}
estilos = {
    "Teórica Butterworth": dict(color="k", lw=2.2, ls="-"),
    "Valores calculados (AO ideal)": dict(color="tab:blue", lw=1.4, ls="--"),
    "Valores comerciales (AO ideal)": dict(color="tab:green", lw=1.4, ls="-."),
    "Valores comerciales + TL084": dict(color="tab:red", lw=1.6, ls="-"),
}

# ---------------------------------------------------------------- resultados numericos
print(f"Especificacion: f0 = {F0:.0f} Hz  fp1 = {FP1:.2f}  fp2 = {FP2:.2f}  BW = {BW:.0f} Hz  Qp = {QP:.4f}"
      f"  K = {AM} V/V ({G0:.3f} dB)  fc1 = {FC1:.2f}  fc2 = {FC2:.2f}")
res = {}
for nombre, (ff, h) in curvas.items():
    r = res[nombre] = caracterizar(ff, h)
    print(f"{nombre:36s} Gmax = {r['Gmax']:7.3f} dB ({10 ** (r['Gmax'] / 20):.3f} V/V) @ {r['fmax']:8.1f} Hz |"
          f" f0 = {r['f0']:8.1f} ({r['f0'] / F0 - 1:+.2%}) | Q = {r['Q']:.4f} ({r['Q'] / QP - 1:+.2%}) |"
          f" fp1 = {r['fp1']:8.1f}  fp2 = {r['fp2']:8.1f}  BW = {r['BW']:7.1f} ({r['BW'] / BW - 1:+.2%}) |"
          f" fc1 = {r['fc1']:8.1f}  fc2 = {r['fc2']:8.1f} | A en banda esp. = {r['A_banda']:.3f} dB |"
          f" |H(f0)| = {r['H_f0']:.3f} dB  fase(f0) = {r['fase_f0']:+.1f} | |H(f0/2)| = {r['H_f0_2']:.2f}"
          f"  |H(2f0)| = {r['H_2f0']:.2f}  |H(f0/10)| = {r['H_f0_10']:.2f}  |H(10f0)| = {r['H_10f0']:.2f}")

# ---------------------------------------------------------------- figura 1: Bode completo
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.2), sharex=True)
for nombre, (ff, h) in curvas.items():
    ax1.semilogx(ff, 20 * np.log10(abs(h)), label=nombre, **estilos[nombre])
    ax2.semilogx(ff, np.angle(h, deg=True), label=nombre, **estilos[nombre])
for x, txt in ((FC1, r"$f_{c1}$"), (F0, r"$f_0$"), (FC2, r"$f_{c2}$")):
    ax1.axvline(x, color="gray", ls=":", lw=1)
    ax1.text(x * 1.03, -24, txt, color="gray")
ax1.axhline(G0 - 3.0103, color="gray", ls=":", lw=1)
ax1.set_ylim(-27, 24)
ax1.set_ylabel("Módulo [dB]")
ax1.grid(True, which="both", alpha=0.35)
ax2.legend(loc="lower left", fontsize=8.5, ncol=2)
ax1.set_title("Filtro pasa banda Butterworth de orden 2 — respuesta en frecuencia")
ax2.set_ylabel("Fase [°]")
ax2.set_xlabel("Frecuencia [Hz]")
ax2.set_yticks(np.arange(-180, 181, 45))
ax2.grid(True, which="both", alpha=0.35)
ax2.set_xlim(1e3, 1e6)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig7_pbd_bode_comparativo.{ext}", dpi=200)

# ---------------------------------------------------------------- figura 2: zoom banda de paso
fig, ax = plt.subplots(figsize=(9, 5.0))
for nombre, (ff, h) in curvas.items():
    ax.semilogx(ff, 20 * np.log10(abs(h)), label=nombre, **estilos[nombre])
ax.axhline(G0, color="gray", ls=":", lw=1)
ax.axhline(G0 - AMAX, color="tab:orange", ls=":", lw=1.2)
ax.axhline(G0 - 3.0103, color="gray", ls=":", lw=1)
ax.axvspan(FP1, FP2, color="tab:orange", alpha=0.12, lw=0)
for x in (FP1, FP2):
    ax.axvline(x, color="tab:orange", ls=":", lw=1.2)
ax.axvline(F0, color="gray", ls=":", lw=1)
ax.text(2.02e4, G0 + 0.1, rf"$K$ = {G0:.2f} dB", color="gray", fontsize=9)
ax.text(2.02e4, G0 - AMAX - 0.35, rf"$K - A_{{max}}$ = {G0 - AMAX:.2f} dB", color="tab:orange", fontsize=9)
ax.text(2.02e4, G0 - 3.0103 + 0.1, rf"$K - 3$ dB = {G0 - 3.01:.2f} dB", color="gray", fontsize=9)
ax.text(FP1 * 0.995, 19.42, r"$f_{p1}$", color="tab:orange", fontsize=9, ha="right")
ax.text(FP2 * 1.005, 19.42, r"$f_{p2}$", color="tab:orange", fontsize=9)
ax.set_xlim(2e4, 4e4)
ax.set_ylim(11.5, 19.6)
ax.set_xticks([2e4, 2.5e4, 3e4, 3.5e4, 4e4])
ax.set_xticklabels(["20k", "25k", "30k", "35k", "40k"])
ax.set_xlabel("Frecuencia [Hz]")
ax.set_ylabel("Módulo [dB]")
ax.set_title("Detalle de la banda de paso (banda especificada sombreada)")
ax.grid(True, which="both", alpha=0.35)
ax.legend(loc="lower center", fontsize=8.5, ncol=2)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig8_pbd_zoom_banda_paso.{ext}", dpi=200)
