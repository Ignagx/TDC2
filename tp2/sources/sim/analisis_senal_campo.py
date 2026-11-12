"""
TP2 Teoria de Circuitos II - Grupo 2
Filtro de senal de campo: Sallen-Key pasa bajos Butterworth de orden 2 con ganancia unitaria (fc = 10 Hz)

Lee los resultados de LTspice (.raw binarios) y genera las figuras del informe:
  - Campo_Ideal_vs_Comercial.raw  -> valores calculados / comerciales con AO ideal
  - Filtro_Senal_Campo_Vctrl{1..5}.raw y .op.raw -> circuito completo de la placa (LM324 y BC547B), un
    archivo por cada valor de Vctrl
Figuras:
  - images/fig_campo_bode_comparativo.{pdf,png}
  - images/fig_campo_zoom_banda_paso.{pdf,png}
  - images/fig_campo_medido_vs_simulado.{pdf,png}

Antes de ejecutar, correr las simulaciones (LTspice -b <archivo>). En modo batch, el .step de
Filtro_Senal_Campo_Grupo2.asc no converge en el punto de operacion a partir del segundo paso, por lo que se
corre una vez por cada valor: se genera el netlist (LTspice -netlist), se quita la linea .step, se cambia
.param Vctrl=3 por el valor buscado y se guarda como Filtro_Senal_Campo_Vctrl<n>.net.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

AQUI = Path(__file__).resolve().parent
IMAGENES = AQUI.parent.parent / "images"

# ---------------------------------------------------------------- especificaciones
FC = 10.0            # Hz, frecuencia de corte de diseno (-3 dB)
Q = 1 / np.sqrt(2)   # Butterworth de orden 2
FRED = 50.0          # Hz, frecuencia de red
VCTRL = [1, 2, 3, 4, 5]   # V, valores del .step (4 a 20 mA)

# ---------------------------------------------------------------- mediciones (placa de Valentino)
MEDIDO = {"fc": (10.83, -3.0), "red": (50.0, -27.8)}


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


def leer_op(nombre):
    """Lector de un .op.raw de LTspice: la primera variable es double y el resto float32."""
    b = (AQUI / nombre).read_bytes()
    clave = "Binary:\n".encode("utf-16le")
    i = b.find(clave)
    lineas = b[:i].decode("utf-16le").splitlines()
    nv = int(next(l for l in lineas if l.startswith("No. Variables")).split(":")[1])
    iv = lineas.index("Variables:")
    nombres = [l.split("\t")[2].lower() for l in lineas[iv + 1: iv + 1 + nv]]
    datos = b[i + len(clave):]
    valores = np.concatenate([np.frombuffer(datos[:8], "<f8"), np.frombuffer(datos[8: 8 + 4 * (nv - 1)], "<f4")])
    return dict(zip(nombres, valores.astype(float)))


def cruce_bajada(f, mag_db, nivel):
    """Primera frecuencia (interpolada en log f) donde mag_db cae por debajo de 'nivel'."""
    k = np.where(np.diff(np.sign(mag_db - nivel)) < 0)[0][0]
    x = np.log10(f[k: k + 2])
    return 10 ** np.interp(nivel, mag_db[k: k + 2][::-1], x[::-1])


def h_teorica(f):
    """Butterworth pasa bajos de orden 2 con ganancia unitaria (f0 = fc)."""
    s = 1j * f / FC
    return 1 / (s ** 2 + s / Q + 1)


def fase_grados(h):
    """Fase desenrollada; a baja frecuencia un pasa bajos tiende a 0 grados."""
    fase = np.unwrap(np.angle(h)) * 180 / np.pi
    return fase - 360 * np.round(fase[0] / 360)


ideal = leer_raw("Campo_Ideal_vs_Comercial.raw")
placa = [leer_raw(f"Filtro_Senal_Campo_Vctrl{v}.raw") for v in VCTRL]

f = ideal["frequency"].real
fp = placa[2]["frequency"].real            # Vctrl = 3 V (punto medio, 12 mA)
# la placa entrega V(salida2) con la ganancia de continua de la fuente de prueba y del amplificador de
# instrumentacion; se normaliza para comparar sólo la forma de la respuesta
h_placa = [p["v(salida2)"] / abs(p["v(salida2)"][0]) for p in placa]
curvas = {
    "Teórica Butterworth": (f, h_teorica(f)),
    "Valores calculados (AO ideal)": (f, ideal["v(vout_calc)"]),
    "Valores comerciales (AO ideal)": (f, ideal["v(vout_com)"]),
    "Circuito completo (LM324, $V_{ctrl}$ = 3 V)": (fp, h_placa[2]),
}
estilos = {
    "Teórica Butterworth": dict(color="k", lw=2.2, ls="-"),
    "Valores calculados (AO ideal)": dict(color="tab:blue", lw=1.4, ls="--"),
    "Valores comerciales (AO ideal)": dict(color="tab:green", lw=1.4, ls="-."),
    "Circuito completo (LM324, $V_{ctrl}$ = 3 V)": dict(color="tab:red", lw=1.6, ls="-"),
}

# ---------------------------------------------------------------- resultados numericos
for nombre, (ff, h) in curvas.items():
    m = 20 * np.log10(abs(h))
    fc = cruce_bajada(ff, m, -3.0103)
    def en(fx): return np.interp(np.log10(fx), np.log10(ff), m)
    fase_fc = np.interp(np.log10(fc), np.log10(ff), fase_grados(h))
    print(f"{nombre:45s} fc = {fc:6.3f} Hz | Gmax = {m.max():7.4f} dB | |H|(50) = {en(50):7.2f} dB"
          f" | |H|(100) = {en(100):7.2f} dB | |H|(1k) = {en(1e3):7.2f} dB | fase(fc) = {fase_fc:6.1f} deg")
for v, p in zip(VCTRL, placa):
    h = p["v(salida2)"]
    g0 = abs(h[0])
    m = 20 * np.log10(abs(h) / g0)
    ff = p["frequency"].real
    print(f"Vctrl = {v} V: G0 = {g0:.4f} V/V | fc = {cruce_bajada(ff, m, -3.0103):6.3f} Hz"
          f" | |H|(50) = {np.interp(np.log10(50), np.log10(ff), m):6.2f} dB")

# punto de operacion: Iin en Rs (R15), Ic en Rcarga (R12, desde 24 V) e Ie en Rshunt_out (R13)
for v in VCTRL:
    op = leer_op(f"Filtro_Senal_Campo_Vctrl{v}.op.raw")
    iin = op["v(lazo-)"] / 250
    ic = (24 - op["v(n014)"]) / 250
    ie = op["v(n017)"] / 250
    print(f"Vctrl = {v} V: Iin = {iin * 1e3:7.4f} mA | Ic = {ic * 1e3:7.4f} mA | Ie = {ie * 1e3:7.4f} mA"
          f" | (Ic - Iin)/Iin = {100 * (ic / iin - 1):6.3f} % | Ic/Ie = {ic / ie:.5f}")

# ---------------------------------------------------------------- figura 1: Bode completo
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7.2), sharex=True)
for nombre, (ff, h) in curvas.items():
    ax1.semilogx(ff, 20 * np.log10(abs(h)), label=nombre, **estilos[nombre])
    ax2.semilogx(ff, fase_grados(h), label=nombre, **estilos[nombre])
ax1.axvline(FC, color="gray", ls=":", lw=1)
ax1.axvline(FRED, color="gray", ls=":", lw=1)
ax1.text(FC * 1.06, -75, r"$f_c$", color="gray")
ax1.text(FRED * 1.06, -75, "50 Hz", color="gray")
ax1.axhline(-3.0103, color="gray", ls=":", lw=1)
ax1.set_ylim(-85, 5)
ax1.set_ylabel("Módulo [dB]")
ax1.grid(True, which="both", alpha=0.35)
ax1.legend(loc="lower left", fontsize=9)
ax1.set_title("Filtro de señal de campo (Sallen-Key de orden 2) — respuesta en frecuencia")
ax2.set_ylabel("Fase [°]")
ax2.set_xlabel("Frecuencia [Hz]")
ax2.set_yticks(np.arange(-180, 1, 45))
ax2.grid(True, which="both", alpha=0.35)
ax2.set_xlim(0.1, 1e3)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig_campo_bode_comparativo.{ext}", dpi=200)

# ---------------------------------------------------------------- figura 2: zoom, cinco puntos de trabajo
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.semilogx(f, 20 * np.log10(abs(h_teorica(f))), label="Teórica Butterworth", **estilos["Teórica Butterworth"])
ax.semilogx(f, 20 * np.log10(abs(ideal["v(vout_com)"])), label="Valores comerciales (AO ideal)",
            **estilos["Valores comerciales (AO ideal)"])
colores = plt.cm.autumn(np.linspace(0, 0.8, len(VCTRL)))
for v, p, h, c in zip(VCTRL, placa, h_placa, colores):
    ax.semilogx(p["frequency"].real, 20 * np.log10(abs(h)), color=c, lw=1.1,
                label=f"Circuito completo, $V_{{ctrl}}$ = {v} V ({4 * v} mA)")
ax.axhline(-3.0103, color="gray", ls=":", lw=1)
ax.axvline(FC, color="gray", ls=":", lw=1)
ax.text(1.05, -2.8, "−3 dB", color="gray", fontsize=9)
ax.set_xlim(1, 30)
ax.set_ylim(-12, 1)
ax.set_xlabel("Frecuencia [Hz]")
ax.set_ylabel("Módulo [dB]")
ax.grid(True, which="both", alpha=0.35)
ax.legend(loc="lower left", fontsize=8.5)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig_campo_zoom_banda_paso.{ext}", dpi=200)

# ---------------------------------------------------------------- figura 3: medido vs simulado
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.semilogx(f, 20 * np.log10(abs(h_teorica(f))), label="Teórica Butterworth", **estilos["Teórica Butterworth"])
ax.semilogx(fp, 20 * np.log10(abs(h_placa[2])), label="Simulación LTspice (circuito completo)",
            **estilos["Circuito completo (LM324, $V_{ctrl}$ = 3 V)"])
fm, am = zip(*MEDIDO.values())
ax.semilogx(fm, am, "o", color="tab:blue", ms=7, label="Medido")
for x, y in MEDIDO.values():
    ax.annotate(f"{x:g} Hz; {y:g} dB".replace(".", ","), (x, y), textcoords="offset points", xytext=(8, 6), fontsize=9)
ax.axhline(-3.0103, color="gray", ls=":", lw=1)
ax.set_xlim(1, 200)
ax.set_ylim(-50, 5)
ax.set_xlabel("Frecuencia [Hz]")
ax.set_ylabel("Módulo [dB]")
ax.grid(True, which="both", alpha=0.35)
ax.legend(loc="lower left", fontsize=9)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(IMAGENES / f"fig_campo_medido_vs_simulado.{ext}", dpi=200)
