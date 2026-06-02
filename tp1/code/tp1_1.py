#!/usr/bin/env python3

import sympy as sp
from sympy import symbols, Eq, I
from sympy.plotting import plot_implicit
from sympy.physics.control.lti import TransferFunction
from sympy.physics.control.control_plots import pole_zero_plot
from sympy.physics.control.control_plots import bode_plot
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

Yr1, Yr2, Yc1, Yc2, s = sp.symbols('Yr1 Yr2 Yc1 Yc2 s')
A = (Yr1*Yr2)/(Yc1*Yc2*s**2+Yc1*Yr1*s+Yc1*Yr2*s+Yc2*Yr2*s+Yr1*Yr2)
H = sp.simplify(A)
TF= TransferFunction(H.as_numer_denom()[0], H.as_numer_denom()[1], s)
TF1=TF.xreplace({Yc2: 0.000000000033, Yr1: 0.00001, Yc1: 0.000000000091, Yr2: 0.00000549})
pole_zero_plot(TF1)
bode_plot(TF1,initial_exp=np.log10(0.0628), final_exp=np.log10(62831853.07))
numerador = TF1.num
denominador = TF1.den

num_coeffs = [float(c) for c in sp.Poly(numerador, s).all_coeffs()]
den_coeffs = [float(c) for c in sp.Poly(denominador, s).all_coeffs()]

sys = signal.TransferFunction(num_coeffs, den_coeffs)

w, h = signal.freqresp(sys)

fig, ax = plt.subplots()
ax.plot(h.real, h.imag)
ax.set_xlabel('Parte real')
ax.set_ylabel('Parte imaginaria')
ax.grid(True)

plt.show()
