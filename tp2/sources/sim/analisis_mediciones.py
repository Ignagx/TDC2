"""
TP2 Teoria de Circuitos II - Grupo 2
Analisis de las mediciones de laboratorio de los filtros pasa bajos y pasa altos (placa 2, TL084).

Datos: sources/Mediciones Filtros_261111_211301.pdf (lecturas de osciloscopio, Vin = 1 Vpp senoidal).
Compara los puntos medidos con la respuesta teorica Butterworth y con la simulacion de LTspice
(valores comerciales + macromodelo TL084) y genera:
  - images/fig9_pb_medido_vs_simulado.{pdf,png}
  - images/fig10_pa_medido_vs_simulado.{pdf,png}
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

AQUI = Path(__file__).resolve().parent
IMAGENES = AQUI.parent.parent / "images"
VIN = 1.0             # Vpp en todos los puntos
PISO = 0.030          # Vpp, piso de medicion observado (lecturas de 25-30 mVpp donde se esperaba < 2 mVpp)


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


def butter4(f, f0, k, pasa_altos):
    s = 1j * f / f0
    if pasa_altos:
        s = 1 / s
    q1, q2 = 1 / (2 * np.cos(np.pi / 8)), 1 / (2 * np.cos(3 * np.pi / 8))
    return k / ((s ** 2 + s / q1 + 1) * (s ** 2 + s / q2 + 1))


def db(x):
    return 20 * np.log10(np.abs(x))


def interp_log(fx, f, y):
    return np.interp(np.log10(fx), np.log10(f), y)


def cruce_lin(f1, h1, f2, h2, nivel):
    """Interpolacion lineal en log f entre dos puntos medidos."""
    t = (nivel - h1) / (h2 - h1)
    return 10 ** (np.log10(f1) + t * (np.log10(f2) - np.log10(f1)))


FILTROS = {
    "pb": dict(
        titulo="Filtro pasa bajos — medición vs. simulación",
        raw="Filtro_PasaBajos_Solo_TL084.raw",
        fp=5.5e3, amax=1.5, k=4.0, pasa_altos=False,
        f=np.array([100, 1e3, 3e3, 5.5e3, 6174, 8e3, 11e3, 20e3, 55e3]),
        vout=np.array([4.0, 4.1, 4.2, 3.5, 2.9, 1.3, 0.385, 0.050, 0.030]),
        xlim=(30, 2e5), ylim=(-75, 20), fig="fig9_pb_medido_vs_simulado",
    ),
    "pa": dict(
        titulo="Filtro pasa altos — medición vs. simulación",
        raw="Filtro_PasaAltos_Orden4_Grupo2.raw",
        fp=33e3, amax=2.25, k=3.5 ** 2, pasa_altos=True,
        f=np.array([3.3e3, 10e3, 16.5e3, 25e3, 31.44e3, 33e3, 48.7e3, 200e3, 761e3, 1.5e6]),
        vout=np.array([0.025, 0.135, 0.845, 4.27, 8.2, 8.93, 10.7, 10.325, 8.1, 3.74]),
        xlim=(1e3, 5e6), ylim=(-70, 30), fig="fig10_pa_medido_vs_simulado",
    ),
}

for clave, d in FILTROS.items():
    eps = np.sqrt(10 ** (d["amax"] / 10) - 1)
    f0 = d["fp"] * eps ** (1 / 4) if d["pasa_altos"] else d["fp"] / eps ** (1 / 4)
    sim = leer_raw(d["raw"])
    fs, hs = sim["frequency"].real, db(sim["v(vout)"])
    f, hm = d["f"], db(d["vout"] / VIN)
    hsim = interp_log(f, fs, hs)
    hteo = db(butter4(f, f0, d["k"], d["pasa_altos"]))
    piso = d["vout"] <= 1.7 * PISO   # puntos dominados (o muy afectados) por el piso de medicion

    print(f"\n=== {clave.upper()} (f0 = {f0:.1f} Hz, K = {db(d['k']):.2f} dB) ===")
    print(f"{'f [Hz]':>10} {'Vout [Vpp]':>11} {'|H|med':>8} {'|H|sim':>8} {'|H|teo':>8} {'med-sim':>8}")
    for i in range(len(f)):
        print(f"{f[i]:10.0f} {d['vout'][i]:11.4g} {hm[i]:8.2f} {hsim[i]:8.2f} {hteo[i]:8.2f} {hm[i]-hsim[i]:+8.2f}"
              + ("   <- piso" if piso[i] else ""))
    gref = hm.max()
    print(f"G max medida = {gref:.2f} dB ({10**(gref/20):.3f} V/V) en {f[np.argmax(hm)]:.0f} Hz")
    i_fp = int(np.argmin(abs(f - d["fp"])))
    print(f"A(fp) vs G max medida = {gref - hm[i_fp]:.2f} dB | vs K nominal = {db(d['k']) - hm[i_fp]:.2f} dB")
    # frecuencia de -3 dB respecto de la ganancia de referencia medida, por interpolacion entre puntos
    ref = hm[0] if not d["pasa_altos"] else gref
    nivel = ref - 3.0103
    for i in range(len(f) - 1):
        if (hm[i] - nivel) * (hm[i + 1] - nivel) < 0:
            print(f"cruce de {nivel:.2f} dB entre {f[i]:.0f} y {f[i+1]:.0f} Hz -> "
                  f"f ~ {cruce_lin(f[i], hm[i], f[i+1], hm[i+1], nivel):.0f} Hz")
    print(f"|H|sim en 1,5 MHz = {interp_log(1.5e6, fs, hs):.2f} dB")

    # ------------------------------------------------------------------ figura
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True,
                                   gridspec_kw=dict(height_ratios=[3, 1.3]))
    ft = np.logspace(np.log10(d["xlim"][0]), np.log10(d["xlim"][1]), 2000)
    ax1.semilogx(ft, db(butter4(ft, f0, d["k"], d["pasa_altos"])), color="k", lw=1.6, ls="--",
                 label="Teórica Butterworth")
    ax1.semilogx(fs, hs, color="tab:red", lw=1.8, label="Simulada (comerciales + TL084)")
    ax1.semilogx(f[~piso], hm[~piso], "o", color="tab:blue", ms=8, mec="white", mew=1.2, zorder=5,
                 label=r"Medida ($V_{in} = 1\ \mathrm{V_{pp}}$)")
    ax1.semilogx(f[piso], hm[piso], "o", ms=8, mfc="white", mec="tab:blue", mew=1.6, zorder=5,
                 label="Medida limitada por el piso de medición")
    ax1.axhspan(d["ylim"][0], db(PISO), color="gray", alpha=0.12, lw=0)
    ax1.text(d["xlim"][0] * 1.3, db(PISO) - 5, f"piso de medición ≈ {PISO*1e3:.0f} mVpp ({db(PISO):.0f} dB)",
             color="dimgray", fontsize=9)
    ax1.axvline(d["fp"], color="gray", ls=":", lw=1)
    ax1.text(d["fp"] * 1.06, d["ylim"][1] - 6, r"$f_p$", color="gray")
    ax1.set_ylim(*d["ylim"])
    ax1.set_ylabel("Módulo [dB]")
    ax1.grid(True, which="both", alpha=0.3)
    ax1.legend(loc="lower center" if d["pasa_altos"] else "lower left", fontsize=9)
    ax1.set_title(d["titulo"])

    dev = hm - hsim
    ax2.axhline(0, color="tab:red", lw=1)
    ax2.vlines(f, 0, dev, color="tab:blue", lw=1.5)
    ax2.semilogx(f[~piso], dev[~piso], "o", color="tab:blue", ms=7, mec="white", mew=1)
    ax2.semilogx(f[piso], dev[piso], "o", ms=7, mfc="white", mec="tab:blue", mew=1.5)
    # puntos cercanos en frecuencia: las etiquetas alternan entre dos alturas para no superponerse
    nivel_etq = 0
    for i in np.where(~piso)[0]:
        nivel_etq = (nivel_etq + 1) % 2 if i > 0 and f[i] / f[i - 1] < 1.6 else 0
        dy = (7 + 11 * nivel_etq) if dev[i] >= 0 else (-13 - 11 * nivel_etq)
        ax2.annotate(f"{dev[i]:+.2f}", (f[i], dev[i]), textcoords="offset points",
                     xytext=(0, dy), ha="center", fontsize=8)
    ax2.set_ylim(-2.5, 2.5)
    ax2.set_ylabel("Medido − simulado [dB]", fontsize=9)
    ax2.set_xlabel("Frecuencia [Hz]")
    ax2.grid(True, which="both", alpha=0.3)
    ax2.set_xlim(*d["xlim"])
    # los puntos dominados por el piso quedan fuera de escala: se indican con una flecha
    for i in np.where(piso & (abs(dev) > 2.5))[0]:
        ax2.annotate(f"{dev[i]:+.0f} dB", (f[i], 2.3), ha="center", fontsize=8, color="dimgray",
                     xytext=(0, -2), textcoords="offset points", va="top",
                     bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(IMAGENES / f"{d['fig']}.{ext}", dpi=200)
    plt.close(fig)
