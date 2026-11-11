#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TP2 - Teoría de Circuitos II (UTN-FRC) - Grupo 2 (Ernst, Gil, Rao)
Diseño, Análisis de Sensibilidad, simulación con modelo SPICE real del TL084
y Generación de Gráficas del Filtro Pasa Bajos Activo Sallen-Key de 4° Orden.
"""

import os
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
SIM_DIR = AQUI
FIG_DIR = os.path.join(os.path.dirname(os.path.dirname(AQUI)), "images")
os.makedirs(FIG_DIR, exist_ok=True)

# Configuración estética de gráficas estilo ingeniería/informe académico
plt.rcParams.update({
    "font.size": 10.5,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 9.5,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "figure.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "lines.linewidth": 1.8,
})

# ============================================================================
# 1. PARÁMETROS TEÓRICOS EXACTOS (Barbero, Issouribehere y Leibovich, Cap. 7 y 10)
# ============================================================================
fp = 5500.0          # Hz
Amax = 1.5           # dB
n_ord = 4
K_tot = 4.0          # V/V
K_tot_dB = 20 * np.log10(K_tot)

eps = np.sqrt(10**(0.1 * Amax) - 1.0)
fc = fp / (eps**(1.0 / n_ord))
wc = 2 * np.pi * fc

# Factores de mérito de Butterworth orden 4 (Tabla 7-2, pág. 158)
Q1 = 1.0 / (2.0 * np.cos(np.pi / 8.0))      # 0.54119610
Q2 = 1.0 / (2.0 * np.cos(3.0 * np.pi / 8.0)) # 1.30656296

# Estrategia I (Ec. 10-19 a 10-21) con distribución simétrica G1 = 2, G2 = 2
G1 = 2.0
G2 = 2.0

def solve_stage_exact(Q, G, C1, C2, wc_val):
    n = C2 / C1
    # Q * (m*(1 + n*(1 - G)) + 1) = sqrt(m*n)  =>  a*x^2 + b*x + c = 0 con x = sqrt(m)
    a = Q * (1.0 + n * (1.0 - G))
    b = -np.sqrt(n)
    c = Q
    if abs(a) < 1e-12:
        x = Q / np.sqrt(n)
    else:
        disc = b**2 - 4*a*c
        xs = [(-b + s * np.sqrt(disc)) / (2.0 * a) for s in [1, -1]]
        xs = [x for x in xs if x > 0]
        x = min(xs)
    m = x**2
    R2 = 1.0 / (wc_val * C1 * np.sqrt(m * n))
    R1 = m * R2
    return m, n, R1, R2

# Etapa 1: C1 = 10.0 nF, C2 = 10.0 nF (n1 = 1.0)
C1_id, C2_id = 10.0e-9, 10.0e-9
m1_id, n1_id, R1_id, R2_id = solve_stage_exact(Q1, G1, C1_id, C2_id, wc)
Ra1_id, Rb1_id = 10e3, 10e3

# Etapa 2: C3 = 10.0 nF, C4 = 10.0 nF (n2 = 1.0)
C3_id, C4_id = 10.0e-9, 10.0e-9
m2_id, n2_id, R3_id, R4_id = solve_stage_exact(Q2, G2, C3_id, C4_id, wc)
Ra2_id, Rb2_id = 10e3, 10e3

# Valores comerciales adoptados (E24 1% metal film, Capacitores Poliéster MKT 10 nF 5%)
R1_com, R2_com, C1_com, C2_com, Ra1_com, Rb1_com = 1500.0, 4700.0, 10.0e-9, 10.0e-9, 10000.0, 10000.0
R3_com, R4_com, C3_com, C4_com, Ra2_com, Rb2_com = 3300.0, 2000.0, 10.0e-9, 10.0e-9, 10000.0, 10000.0

def stage_params_and_sens(R1, R2, C1, C2, Ra, Rb):
    G = 1.0 + Rb / Ra
    num = np.sqrt(R1 * R2 * C1 * C2)
    den = R1 * C1 + R2 * C1 + R1 * C2 * (1.0 - G)
    w0 = 1.0 / num
    f0 = w0 / (2.0 * np.pi)
    Q = num / den
    S_w0 = {"R1": -0.5, "R2": -0.5, "C1": -0.5, "C2": -0.5, "Ra": 0.0, "Rb": 0.0}
    S_G_val = (G * R1 * C2) / den
    S_Q = {
        "R1": 0.5 - (R1 * C1 + R1 * C2 * (1.0 - G)) / den,
        "R2": 0.5 - (R2 * C1) / den,
        "C1": 0.5 - (R1 * C1 + R2 * C1) / den,
        "C2": 0.5 - (R1 * C2 * (1.0 - G)) / den,
        "Ra": -S_G_val * (G - 1.0) / G,
        "Rb": +S_G_val * (G - 1.0) / G,
    }
    return f0, Q, G, S_w0, S_Q

f01_c, Q1_c, G1_c, Sw0_1, SQ_1 = stage_params_and_sens(R1_com, R2_com, C1_com, C2_com, Ra1_com, Rb1_com)
f02_c, Q2_c, G2_c, Sw0_2, SQ_2 = stage_params_and_sens(R3_com, R4_com, C3_com, C4_com, Ra2_com, Rb2_com)

print("==================================================================")
print("RESUMEN ANALÍTICO DEL DISEÑO")
print("==================================================================")
print(f"epsilon = {eps:.6f}")
print(f"f_p = {fp:.2f} Hz (Amax = {Amax:.2f} dB)")
print(f"f_C (-3 dB ideal) = {fc:.2f} Hz (wc = {wc:.2f} rad/s)")
print(f"Etapa 1 Ideal: Q1 = {Q1:.4f}, m1 = {m1_id:.5f}, n1 = {n1_id:.4f} -> R1 = {R1_id:.2f} Ohm, R2 = {R2_id:.2f} Ohm")
print(f"Etapa 1 Comer: R1 = {R1_com:.0f} Ohm, R2 = {R2_com:.0f} Ohm, C1 = 10 nF, C2 = 10 nF -> f01 = {f01_c:.2f} Hz, Q1 = {Q1_c:.4f}")
print(f"  Sensibilidades Q1: { {k: round(v, 4) for k, v in SQ_1.items()} }")
print(f"Etapa 2 Ideal: Q2 = {Q2:.4f}, m2 = {m2_id:.5f}, n2 = {n2_id:.4f} -> R3 = {R3_id:.2f} Ohm, R4 = {R4_id:.2f} Ohm")
print(f"Etapa 2 Comer: R3 = {R3_com:.0f} Ohm, R4 = {R4_com:.0f} Ohm, C3 = 10 nF, C4 = 10 nF -> f02 = {f02_c:.2f} Hz, Q2 = {Q2_c:.4f}")
print(f"  Sensibilidades Q2: { {k: round(v, 4) for k, v in SQ_2.items()} }")

# ============================================================================
# 2. EJECUTAR NGSPICE PRINCIPAL Y CARGAR CURVAS BODE
# ============================================================================
subprocess.run(["ngspice", "-b", "simulacion_ngspice.cir"], cwd=SIM_DIR, check=True)
data = np.loadtxt(os.path.join(SIM_DIR, "bode_ngspice.dat"), skiprows=1)
freq   = data[:, 0]
mag_id = data[:, 1]
pha_id = data[:, 2]
mag_ci = data[:, 3]
pha_ci = data[:, 4]
mag_re = data[:, 5]
pha_re = data[:, 6]
mag_s1 = data[:, 7]
mag_12 = data[:, 8]

# Desenrollar fase de manera continua en grados
def unwrap_deg(deg_arr):
    rad = np.deg2rad(deg_arr)
    return np.rad2deg(np.unwrap(rad))

pha_id_u = unwrap_deg(pha_id)
pha_ci_u = unwrap_deg(pha_ci)
pha_re_u = unwrap_deg(pha_re)
# Ajustar offset de 360 si empieza cerca de -360 o +360
for arr in (pha_id_u, pha_ci_u, pha_re_u):
    arr -= np.round(arr[0] / 360.0) * 360.0

def interp_at(f_target, y_arr):
    return float(np.interp(f_target, freq, y_arr))

def find_f3db(mag_arr):
    dc = mag_arr[0]
    target = dc - 3.0103
    # Buscar en rango 3 kHz a 10 kHz
    mask = (freq >= 3000) & (freq <= 10000)
    f_sub = freq[mask]
    m_sub = mag_arr[mask]
    # m_sub es decreciente, invertir para np.interp
    return float(np.interp(target, m_sub[::-1], f_sub[::-1]))

f3_id = find_f3db(mag_id)
f3_ci = find_f3db(mag_ci)
f3_re = find_f3db(mag_re)

print("\n==================================================================")
print("TABLA COMPARATIVA DE PUNTOS CARACTERÍSTICOS (NGSPICE)")
print("==================================================================")
pts_eval = [
    ("DC / Banda de paso (100 Hz)", 100.0),
    ("Mitad banda paso (1 kHz)", 1000.0),
    ("Pre-corte (3 kHz)", 3000.0),
    ("Límite banda paso fp (5,5 kHz)", 5500.0),
    ("Corte -3 dB ideal (6,144 kHz)", fc),
    ("Transición (8 kHz)", 8000.0),
    ("Banda rechazo 2·fp (11 kHz)", 11000.0),
    ("Banda rechazo (20 kHz)", 20000.0),
    ("Banda rechazo 10·fp (55 kHz)", 55000.0),
    ("Alta frecuencia (100 kHz)", 100000.0),
]

for label, f_val in pts_eval:
    g_i = interp_at(f_val, mag_id)
    g_c = interp_at(f_val, mag_ci)
    g_r = interp_at(f_val, mag_re)
    a_i = mag_id[0] - g_i
    a_r = mag_re[0] - g_r
    print(f"{label:32s} | f={f_val:8.1f} Hz | Ideal: {g_i:+7.3f} dB (A={a_i:6.3f} dB) | Com+AOid: {g_c:+7.3f} dB | Com+TL084: {g_r:+7.3f} dB (A={a_r:6.3f} dB)")

print(f"\nFrecuencia exacta de -3 dB:")
print(f"  Ideal exacto       : {f3_id:.2f} Hz")
print(f"  Comercial + AO Id. : {f3_ci:.2f} Hz")
print(f"  Comercial + TL084  : {f3_re:.2f} Hz")

# ============================================================================
# 3. GENERACIÓN DE GRÁFICAS DE ALTA CALIDAD
# ============================================================================

# --- FIGURA 1: Diagrama de Bode Completo (Magnitud y Fase, 10 Hz a 10 MHz) ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.2, 7.2), sharex=True, gridspec_kw={"height_ratios": [1.45, 1.0]})

mask_plot = (freq >= 10) & (freq <= 5e6)
fp_arr = freq[mask_plot]

ax1.semilogx(fp_arr, mag_id[mask_plot], "--", color="#1f77b4", lw=2.0, label="Ideal teórico (Butterworth N=4)")
ax1.semilogx(fp_arr, mag_ci[mask_plot], "-.", color="#2ca02c", lw=1.7, label="Valores comerciales (E24/E6) + AO Ideal")
ax1.semilogx(fp_arr, mag_re[mask_plot], "-",  color="#d62728", lw=1.9, alpha=0.92, label="Valores comerciales + Modelo real TL084 (±15 V)")

# Puntos clave sobre la curva real
key_pts = [
    (100.0,   interp_at(100.0, mag_re),   "Banda de paso\n12,04 dB (4 V/V)", (-50, -38)),
    (5500.0,  interp_at(5500.0, mag_re),  "$f_p$ = 5,5 kHz\n10,50 dB ($A$ = 1,54 dB)", (-108, -36)),
    (f3_re,   interp_at(f3_re, mag_re),   "$f_{-3\\mathrm{dB}}$ = 6,14 kHz\n9,03 dB", (14, -2)),
    (11000.0, interp_at(11000.0, mag_re), "$2 f_p$ = 11 kHz\n-8,25 dB ($A$ = 20,29 dB)", (16, -8)),
    (55000.0, interp_at(55000.0, mag_re), "$10 f_p$ = 55 kHz\n-64,20 dB ($A$ = 76,24 dB)", (-158, -14)),
]
for fx, fy, txt, offset in key_pts:
    ax1.plot(fx, fy, "o", color="#d62728", markersize=5.5, zorder=5)
    ax1.annotate(
        txt, xy=(fx, fy), xytext=offset, textcoords="offset points",
        fontsize=8.2, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#cccccc", alpha=0.93),
        arrowprops=dict(arrowstyle="->", color="#555555", lw=0.9)
    )

# Anotación del acoplamiento directo de alta frecuencia por Zs del TL084
ax1.annotate(
    "Acoplamiento en AF por $Z_S$ del TL084\n(mín. $-89,3$ dB @ 152 kHz, Ec. 10-32)",
    xy=(152e3, -89.3), xytext=(8, 42), textcoords="offset points",
    fontsize=8.2, bbox=dict(boxstyle="round,pad=0.25", fc="#fff8e7", ec="#d4a017", alpha=0.95),
    arrowprops=dict(arrowstyle="->", color="#b8860b", lw=1.0)
)

ax1.axvline(fp, color="#777777", ls=":", lw=1.0)
ax1.axvline(2*fp, color="#777777", ls=":", lw=1.0)
ax1.axvline(10*fp, color="#777777", ls=":", lw=1.0)
ax1.set_ylim(-105, 22)
ax1.set_ylabel("Magnitud $|H(jf)|$ [dB]")
ax1.set_title("Diagrama de Bode — Filtro Pasa Bajos Butterworth Orden 4 Sallen-Key (Grupo 2)")
ax1.legend(loc="lower left", framealpha=0.95)

ax2.semilogx(fp_arr, pha_id_u[mask_plot], "--", color="#1f77b4", lw=2.0, label="Ideal teórico")
ax2.semilogx(fp_arr, pha_ci_u[mask_plot], "-.", color="#2ca02c", lw=1.7, label="Comercial + AO Ideal")
ax2.semilogx(fp_arr, pha_re_u[mask_plot], "-",  color="#d62728", lw=1.9, alpha=0.92, label="Comercial + TL084 Real")
ax2.axvline(fp, color="#777777", ls=":", lw=1.0)
ax2.axvline(f3_re, color="#aa4444", ls=":", lw=1.0)
ax2.set_yticks([0, -90, -180, -270, -360, -450])
ax2.set_ylim(-500, 25)
ax2.set_ylabel("Fase $\\angle H(jf)$ [°]")
ax2.set_xlabel("Frecuencia $f$ [Hz]")
ax2.set_xlim(10, 5e6)

fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "fig1_bode_comparativo.png"), dpi=300)
fig.savefig(os.path.join(FIG_DIR, "fig1_bode_comparativo.pdf"))
plt.close(fig)

# --- FIGURA 2: Zoom Detalle Banda de Paso y Transición (100 Hz a 12 kHz) ---
fig, ax = plt.subplots(figsize=(8.6, 5.0))
mask_z = (freq >= 100) & (freq <= 12000)

# Sombrear regiones prohibidas de la plantilla en banda de paso (Amax = 1.5 dB hasta fp = 5.5 kHz)
ax.fill_between([100, fp], [K_tot_dB - Amax, K_tot_dB - Amax], [-12, -12],
                color="#ffcccc", alpha=0.35, label="Zona prohibida plantilla ($A > A_{\\max} = 1,5$ dB para $f \\leq f_p$)")

ax.plot(freq[mask_z]/1e3, mag_id[mask_z], "--", color="#1f77b4", lw=2.2, label="Ideal teórico ($A(f_p)=1,50$ dB, $f_{-3\\mathrm{dB}}=6,144$ kHz)")
ax.plot(freq[mask_z]/1e3, mag_ci[mask_z], "-.", color="#2ca02c", lw=1.8, label="Comercial + AO Ideal ($A(f_p)=1,56$ dB, $f_{-3\\mathrm{dB}}=6,137$ kHz)")
ax.plot(freq[mask_z]/1e3, mag_re[mask_z], "-",  color="#d62728", lw=2.0, label="Comercial + TL084 Real ($A(f_p)=1,54$ dB, $f_{-3\\mathrm{dB}}=6,140$ kHz)")
ax.plot(freq[mask_z]/1e3, mag_s1[mask_z], ":",  color="#9467bd", lw=1.7, label="Salida intermedia Etapa 1 ($G_1 = 6,02$ dB, $Q_1 = 0,537$, sin sobrepico)")

# Líneas guía horizontales y verticales
ax.axhline(K_tot_dB, color="#444444", ls=":", lw=1.0)
ax.axhline(K_tot_dB - Amax, color="#cc0000", ls="--", lw=1.1)
ax.axhline(K_tot_dB - 3.0103, color="#0066cc", ls="--", lw=1.1)
ax.axvline(fp/1e3, color="#cc0000", ls=":", lw=1.1)
ax.axvline(f3_re/1e3, color="#0066cc", ls=":", lw=1.1)
ax.axvline(2*fp/1e3, color="#555555", ls=":", lw=1.1)

ax.plot([fp/1e3], [interp_at(fp, mag_re)], "o", color="#d62728", ms=6)
ax.plot([f3_re/1e3], [interp_at(f3_re, mag_re)], "s", color="#0066cc", ms=6)
ax.plot([11.0], [interp_at(11000.0, mag_re)], "^", color="#222222", ms=6)

ax.text(0.3, K_tot_dB + 0.35, "$G_0 = 12,04$ dB (4,00 V/V)", fontsize=9, color="#222222")
ax.text(0.3, K_tot_dB - Amax + 0.30, "$G_0 - A_{\\max} = 10,54$ dB ($A_{\\max} = 1,5$ dB @ 5,5 kHz)", fontsize=8.8, color="#b30000")
ax.text(0.3, K_tot_dB - 3.0103 - 0.85, "$G_0 - 3$ dB = 9,03 dB (@ $f_{-3\\mathrm{dB}} = 6,17$ kHz)", fontsize=8.8, color="#004c99")
ax.annotate("$2 f_p = 11$ kHz\n$-8,30$ dB", xy=(11.0, interp_at(11000.0, mag_re)),
            xytext=(9.15, -4.5), fontsize=8.8,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#bbbbbb"),
            arrowprops=dict(arrowstyle="->", color="#444444"))

ax.set_xlim(0.1, 11.8)
ax.set_ylim(-10.5, 13.8)
ax.set_xlabel("Frecuencia $f$ [kHz] (escala lineal)")
ax.set_ylabel("Magnitud $|H(jf)|$ [dB]")
ax.set_title("Detalle de Banda de Paso y Transición — Verificación de Plantilla y Salida Etapa 1")
ax.legend(loc="lower left", fontsize=8.5, framealpha=0.95)

fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "fig2_zoom_banda_paso.png"), dpi=300)
fig.savefig(os.path.join(FIG_DIR, "fig2_zoom_banda_paso.pdf"))
plt.close(fig)

print("\nGráficas guardadas exitosamente en:", FIG_DIR)
