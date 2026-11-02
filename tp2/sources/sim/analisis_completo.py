#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TP2 - Teoría de Circuitos II (UTN-FRC) - Grupo 2 (Ernst, Gil, Rao)
Diseño, Análisis de Sensibilidad, Monte Carlo (con modelo SPICE real del TL084)
y Generación de Gráficas del Filtro Pasa Bajos Activo Sallen-Key de 4° Orden.
"""

import os
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_DIR = os.path.join(BASE_DIR, "simulaciones")
FIG_DIR = os.path.join(BASE_DIR, "figuras")
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
    disc = b**2 - 4*a*c
    # Tomamos la raíz que minimiza sensibilidad / da valores moderados de m (< 1 para n > 1)
    xs = [(-b + s * np.sqrt(disc)) / (2.0 * a) for s in [1, -1]]
    xs = [x for x in xs if x > 0]
    x = min(xs)
    m = x**2
    R2 = 1.0 / (wc_val * C1 * np.sqrt(m * n))
    R1 = m * R2
    return m, n, R1, R2

# Etapa 1: C1 = 2.2 nF, C2 = 3.3 nF (n1 = 1.5, Tabla D-IV Apéndice D)
C1_id, C2_id = 2.2e-9, 3.3e-9
m1_id, n1_id, R1_id, R2_id = solve_stage_exact(Q1, G1, C1_id, C2_id, wc)
Ra1_id, Rb1_id = 10e3, 10e3

# Etapa 2: C3 = 3.3 nF, C4 = 10.0 nF (n2 = 3.0303, Tabla D-IV Apéndice D)
C3_id, C4_id = 3.3e-9, 10.0e-9
m2_id, n2_id, R3_id, R4_id = solve_stage_exact(Q2, G2, C3_id, C4_id, wc)
Ra2_id, Rb2_id = 10e3, 10e3

# Valores comerciales adoptados (Resistencias E24 1% metal film, Capacitores Poliéster MKT E6)
R1_com, R2_com, C1_com, C2_com, Ra1_com, Rb1_com = 3900.0, 24000.0, 2.2e-9, 3.3e-9, 10000.0, 10000.0
R3_com, R4_com, C3_com, C4_com, Ra2_com, Rb2_com = 2000.0, 10000.0, 3.3e-9, 10.0e-9, 10000.0, 10000.0

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
print(f"Etapa 1 Comer: R1 = {R1_com:.0f} Ohm, R2 = {R2_com:.0f} Ohm, C1 = 2.2 nF, C2 = 3.3 nF -> f01 = {f01_c:.2f} Hz, Q1 = {Q1_c:.4f}")
print(f"  Sensibilidades Q1: { {k: round(v, 4) for k, v in SQ_1.items()} }")
print(f"Etapa 2 Ideal: Q2 = {Q2:.4f}, m2 = {m2_id:.5f}, n2 = {n2_id:.4f} -> R3 = {R3_id:.2f} Ohm, R4 = {R4_id:.2f} Ohm")
print(f"Etapa 2 Comer: R3 = {R3_com:.0f} Ohm, R4 = {R4_com:.0f} Ohm, C3 = 3.3 nF, C4 = 10 nF -> f02 = {f02_c:.2f} Hz, Q2 = {Q2_c:.4f}")
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
# 3. SIMULACIÓN DE MONTE CARLO EN NGSPICE CON MODELO REAL DEL TL084
# ============================================================================
def run_ngspice_montecarlo(N_runs=200, r_tol=0.01, c_tol=0.05, seed=2026):
    rng = np.random.default_rng(seed)
    lines = [
        "* Monte Carlo SPICE con modelo real TL084",
        '.include "TL084.lib"',
        "VCC vcc 0 DC 15",
        "VEE vee 0 DC -15",
        "VIN in 0 DC 0 AC 1",
    ]
    out_vecs = []
    for k in range(N_runs):
        r1 = R1_com * rng.uniform(1 - r_tol, 1 + r_tol)
        r2 = R2_com * rng.uniform(1 - r_tol, 1 + r_tol)
        c1 = C1_com * rng.uniform(1 - c_tol, 1 + c_tol)
        c2 = C2_com * rng.uniform(1 - c_tol, 1 + c_tol)
        ra1 = Ra1_com * rng.uniform(1 - r_tol, 1 + r_tol)
        rb1 = Rb1_com * rng.uniform(1 - r_tol, 1 + r_tol)

        r3 = R3_com * rng.uniform(1 - r_tol, 1 + r_tol)
        r4 = R4_com * rng.uniform(1 - r_tol, 1 + r_tol)
        c3 = C3_com * rng.uniform(1 - c_tol, 1 + c_tol)
        c4 = C4_com * rng.uniform(1 - c_tol, 1 + c_tol)
        ra2 = Ra2_com * rng.uniform(1 - r_tol, 1 + r_tol)
        rb2 = Rb2_com * rng.uniform(1 - r_tol, 1 + r_tol)

        lines += [
            f"R1_{k} in n1_{k} {r1:.4f}",
            f"R2_{k} n1_{k} n2_{k} {r2:.4f}",
            f"C1_{k} n2_{k} 0 {c1:.6e}",
            f"C2_{k} o1_{k} n1_{k} {c2:.6e}",
            f"RA1_{k} iv1_{k} 0 {ra1:.4f}",
            f"RB1_{k} o1_{k} iv1_{k} {rb1:.4f}",
            f"XU1_{k} n2_{k} iv1_{k} vcc vee o1_{k} TL084",
            f"R3_{k} o1_{k} n3_{k} {r3:.4f}",
            f"R4_{k} n3_{k} n4_{k} {r4:.4f}",
            f"C3_{k} n4_{k} 0 {c3:.6e}",
            f"C4_{k} out_{k} n3_{k} {c4:.6e}",
            f"RA2_{k} iv2_{k} 0 {ra2:.4f}",
            f"RB2_{k} out_{k} iv2_{k} {rb2:.4f}",
            f"XU2_{k} n4_{k} iv2_{k} vcc vee out_{k} TL084",
        ]
        out_vecs.append(f"vdb(out_{k})")

    dat_name = f"mc_c{int(c_tol*100)}.dat"
    cir_name = f"mc_c{int(c_tol*100)}.cir"
    lines += [
        ".control",
        "set wr_vecnames",
        "set wr_singlescale",
        "ac dec 250 100 100k",
        f"wrdata {dat_name} " + " ".join(out_vecs),
        "quit",
        ".endc",
        ".END",
    ]
    cir_path = os.path.join(SIM_DIR, cir_name)
    with open(cir_path, "w") as f:
        f.write("\n".join(lines))
    subprocess.run(["ngspice", "-b", cir_name], cwd=SIM_DIR, check=True, stdout=subprocess.DEVNULL)
    mc_data = np.loadtxt(os.path.join(SIM_DIR, dat_name), skiprows=1)
    return mc_data[:, 0], mc_data[:, 1:]

print("\nCorriendo Monte Carlo en ngspice con modelo real del TL084 (N=200 para C=5% y C=10%)...")
f_mc5, mags_mc5   = run_ngspice_montecarlo(N_runs=200, r_tol=0.01, c_tol=0.05, seed=101)
f_mc10, mags_mc10 = run_ngspice_montecarlo(N_runs=200, r_tol=0.01, c_tol=0.10, seed=202)

# También 10.000 corridas estadísticas exactas para intervalos de confianza precisos
def fast_mc_stats(N=10000, r_tol=0.01, c_tol=0.05, seed=42):
    rng = np.random.default_rng(seed)
    freqs_fine = np.linspace(4200.0, 7800.0, 901)
    s = 1j * 2 * np.pi * freqs_fine[None, :]

    def sample_H(R1, R2, C1, C2, Ra, Rb):
        r1 = R1 * rng.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        r2 = R2 * rng.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        c1 = C1 * rng.uniform(1 - c_tol, 1 + c_tol, (N, 1))
        c2 = C2 * rng.uniform(1 - c_tol, 1 + c_tol, (N, 1))
        ra = Ra * rng.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        rb = Rb * rng.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        G = 1.0 + rb / ra
        H = G / (r1*r2*c1*c2*(s**2) + (r1*c1 + r2*c1 + r1*c2*(1.0 - G))*s + 1.0)
        return H, G[:, 0]

    H1, g1 = sample_H(R1_com, R2_com, C1_com, C2_com, Ra1_com, Rb1_com)
    H2, g2 = sample_H(R3_com, R4_com, C3_com, C4_com, Ra2_com, Rb2_com)
    Kdc = g1 * g2
    Kdc_db = 20 * np.log10(Kdc)
    mag_db = 20 * np.log10(np.abs(H1 * H2))
    att_db = Kdc_db[:, None] - mag_db
    idx_fp = np.argmin(np.abs(freqs_fine - fp))
    att_fp = att_db[:, idx_fp]
    gain_fp = mag_db[:, idx_fp]
    idx_3db = np.argmin(np.abs(att_db - 3.0103), axis=1)
    f3db = freqs_fine[idx_3db]

    # También evaluar en 2fp y 10fp
    s_stop = 1j * 2 * np.pi * np.array([[2*fp, 10*fp]])
    # Reusar las mismas muestras para 2fp y 10fp con una segunda pasada determinista
    rng2 = np.random.default_rng(seed)
    def sample_H_pts(R1, R2, C1, C2, Ra, Rb):
        r1 = R1 * rng2.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        r2 = R2 * rng2.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        c1 = C1 * rng2.uniform(1 - c_tol, 1 + c_tol, (N, 1))
        c2 = C2 * rng2.uniform(1 - c_tol, 1 + c_tol, (N, 1))
        ra = Ra * rng2.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        rb = Rb * rng2.uniform(1 - r_tol, 1 + r_tol, (N, 1))
        G = 1.0 + rb / ra
        return G / (r1*r2*c1*c2*(s_stop**2) + (r1*c1 + r2*c1 + r1*c2*(1.0 - G))*s_stop + 1.0)
    Hs1 = sample_H_pts(R1_com, R2_com, C1_com, C2_com, Ra1_com, Rb1_com)
    Hs2 = sample_H_pts(R3_com, R4_com, C3_com, C4_com, Ra2_com, Rb2_com)
    mag_stop = 20 * np.log10(np.abs(Hs1 * Hs2))
    att_2fp = Kdc_db - mag_stop[:, 0]
    att_10fp = Kdc_db - mag_stop[:, 1]
    return {
        "Kdc_db": Kdc_db, "Kdc": Kdc,
        "att_fp": att_fp, "gain_fp": gain_fp,
        "f3db": f3db, "att_2fp": att_2fp, "att_10fp": att_10fp,
    }

stats_5  = fast_mc_stats(10000, 0.01, 0.05, seed=777)
stats_10 = fast_mc_stats(10000, 0.01, 0.10, seed=888)

for label, st in [("R ±1%, C ±5% (Poliéster estándar J)", stats_5),
                  ("R ±1%, C ±10% (Poliéster clase K)", stats_10)]:
    print(f"\n--- Estadísticas Monte Carlo (N=10.000) [{label}] ---")
    for kname, unit in [("Kdc_db", "dB"), ("att_fp", "dB"), ("f3db", "Hz"), ("att_2fp", "dB"), ("att_10fp", "dB")]:
        arr = st[kname]
        print(f"  {kname:8s}: media={np.mean(arr):8.2f} {unit}, std={np.std(arr):6.2f} {unit}, "
              f"P2.5-P97.5=[{np.percentile(arr, 2.5):7.2f}, {np.percentile(arr, 97.5):7.2f}], "
              f"min-max=[{np.min(arr):7.2f}, {np.max(arr):7.2f}]")

# Peor caso de frecuencia de corte (todos los R y C en su extremo superior vs inferior)
def eval_cascade_mag_db(f_arr, mult_R, mult_C, mult_G1=1.0, mult_G2=1.0):
    s = 1j * 2 * np.pi * f_arr
    def H_s(R1, R2, C1, C2, G):
        return G / (R1*R2*C1*C2*(s**2) + (R1*C1 + R2*C1 + R1*C2*(1.0 - G))*s + 1.0)
    H1 = H_s(R1_com*mult_R, R2_com*mult_R, C1_com*mult_C, C2_com*mult_C, 1.0 + mult_G1)
    H2 = H_s(R3_com*mult_R, R4_com*mult_R, C3_com*mult_C, C4_com*mult_C, 1.0 + mult_G2)
    return 20 * np.log10(np.abs(H1 * H2))

# ============================================================================
# 4. GENERACIÓN DE GRÁFICAS DE ALTA CALIDAD
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
ax.text(0.3, K_tot_dB - 3.0103 - 0.85, "$G_0 - 3$ dB = 9,03 dB (@ $f_{-3\\mathrm{dB}} = 6,14$ kHz)", fontsize=8.8, color="#004c99")
ax.annotate("$2 f_p = 11$ kHz\n$-8,25$ dB", xy=(11.0, interp_at(11000.0, mag_re)),
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

# --- FIGURA 3: Análisis de Tolerancias (Monte Carlo con TL084 Real + Histogramas) ---
fig = plt.figure(figsize=(10.0, 7.4))
gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0], hspace=0.34, wspace=0.26)

ax_mc = fig.add_subplot(gs[0, :])
ax_hf = fig.add_subplot(gs[1, 0])
ax_ha = fig.add_subplot(gs[1, 1])

mask_mc = (f_mc5 >= 1000) & (f_mc5 <= 15000)
f_sub = f_mc5[mask_mc] / 1e3

# Graficar nube de 120 corridas C=10% en gris suave y 120 corridas C=5% en celeste/naranja
for k in range(min(120, mags_mc10.shape[1])):
    lbl = "Monte Carlo SPICE TL084 ($R\\,\\pm 1\\%,\\; C\\,\\pm 10\\%$)" if k == 0 else None
    ax_mc.plot(f_sub, mags_mc10[mask_mc, k], color="#cccccc", lw=0.6, alpha=0.45, label=lbl)

for k in range(min(120, mags_mc5.shape[1])):
    lbl = "Monte Carlo SPICE TL084 ($R\\,\\pm 1\\%,\\; C\\,\\pm 5\\%$)" if k == 0 else None
    ax_mc.plot(f_sub, mags_mc5[mask_mc, k], color="#6baed6", lw=0.65, alpha=0.45, label=lbl)

# Curvas de peor caso (corrimiento extremo de f_c para R ±1%, C ±5%)
f_wc_grid = f_mc5[mask_mc]
wc_low5  = eval_cascade_mag_db(f_wc_grid, 1.01, 1.05, 1.01/0.99 - 1 + 1, 1.01/0.99 - 1 + 1)
# Corregir argumento mult_G: Rb/Ra max = 1.01/0.99, min = 0.99/1.01
wc_fmin5 = eval_cascade_mag_db(f_wc_grid, 1.01, 1.05, 0.99/1.01, 0.99/1.01)
wc_fmax5 = eval_cascade_mag_db(f_wc_grid, 0.99, 0.95, 1.01/0.99, 1.01/0.99)
ax_mc.plot(f_sub, wc_fmin5, "--", color="#08519c", lw=1.5, label="Extremos $f_c$ ($R\\,\\pm 1\\%,\\; C\\,\\pm 5\\%$)")
ax_mc.plot(f_sub, wc_fmax5, "--", color="#08519c", lw=1.5)

mask_nom_mc = (freq >= 1000) & (freq <= 15000)
ax_mc.plot(freq[mask_nom_mc]/1e3, mag_re[mask_nom_mc], "-", color="#d62728", lw=2.2, label="Nominal Comercial + TL084")
ax_mc.axvline(fp/1e3, color="#cc0000", ls=":", lw=1.1)
ax_mc.axvline(f3_re/1e3, color="#222222", ls=":", lw=1.1)
ax_mc.axhline(K_tot_dB - 3.0103, color="#555555", ls=":", lw=1.0)

ax_mc.set_xlim(1.0, 15.0)
ax_mc.set_ylim(-22, 15.5)
ax_mc.set_xlabel("Frecuencia $f$ [kHz] (escala lineal)")
ax_mc.set_ylabel("Magnitud $|H(jf)|$ [dB]")
ax_mc.set_title("Análisis de Tolerancias — 200 Simulaciones Monte Carlo SPICE (Modelo Real TL084)")
ax_mc.legend(loc="lower left", fontsize=8.6, ncol=2, framealpha=0.95)

# Histograma f_-3dB
ax_hf.hist(stats_10["f3db"], bins=40, density=True, color="#bdbdbd", alpha=0.65, edgecolor="#888888", label="$R\\,\\pm 1\\%,\\; C\\,\\pm 10\\%$")
ax_hf.hist(stats_5["f3db"],  bins=40, density=True, color="#4292c6", alpha=0.75, edgecolor="#08519c", label="$R\\,\\pm 1\\%,\\; C\\,\\pm 5\\%$")
ax_hf.axvline(f3_re, color="#d62728", lw=2.0, label=f"Nominal: {f3_re:.0f} Hz")
ax_hf.set_xlabel("Frecuencia de corte $f_{-3\\mathrm{dB}}$ [Hz]")
ax_hf.set_ylabel("Densidad de probabilidad")
ax_hf.set_title(f"Dispersión de $f_{{-3\\mathrm{{dB}}}}$ ($\\sigma_{{5\\%}}={np.std(stats_5['f3db']):.0f}$ Hz, $\\sigma_{{10\\%}}={np.std(stats_10['f3db']):.0f}$ Hz)")
ax_hf.legend(fontsize=8.2)

# Histograma Atenuación en fp (5.5 kHz)
ax_ha.hist(stats_10["att_fp"], bins=40, density=True, color="#bdbdbd", alpha=0.65, edgecolor="#888888", label="$R\\,\\pm 1\\%,\\; C\\,\\pm 10\\%$")
ax_ha.hist(stats_5["att_fp"],  bins=40, density=True, color="#ef6548", alpha=0.75, edgecolor="#99000d", label="$R\\,\\pm 1\\%,\\; C\\,\\pm 5\\%$")
ax_ha.axvline(1.541, color="#222222", lw=2.0, label="Nominal: 1,54 dB")
ax_ha.axvline(1.500, color="#1f77b4", ls="--", lw=1.5, label="Ideal: 1,50 dB")
ax_ha.set_xlabel("Atenuación en $f_p = 5,5$ kHz, $A(f_p)$ [dB]")
ax_ha.set_ylabel("Densidad de probabilidad")
ax_ha.set_title(f"Dispersión de $A(f_p)$ ($\\sigma_{{5\\%}}={np.std(stats_5['att_fp']):.2f}$ dB, $\\sigma_{{10\\%}}={np.std(stats_10['att_fp']):.2f}$ dB)")
ax_ha.legend(fontsize=8.2)

fig.savefig(os.path.join(FIG_DIR, "fig3_tolerancias_montecarlo.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(FIG_DIR, "fig3_tolerancias_montecarlo.pdf"), bbox_inches="tight")
plt.close(fig)

print("\nGráficas guardadas exitosamente en:", FIG_DIR)
