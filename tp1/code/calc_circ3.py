#!/usr/bin/env python3
import math

# Ideal values
R1_id = 20e3
R2_id = 400e3
C1_id = 1.25e-6
C2_id = 15.625e-9

# Real values
R1_re = 100e3
R2_re = 400e3  # 390k + 10k
C1_re = 1.2e-6
C2_re = 15e-9

def analyze(R1, R2, C1, C2, name=""):
    print(f"=== {name} ===")
    wc1 = 1.0 / (R1 * C1)
    wc2 = 1.0 / (R2 * C2)
    print(f"wc1: {wc1:.4f} rad/s (fc1: {wc1/(2*math.pi):.4f} Hz)")
    print(f"wc2: {wc2:.4f} rad/s (fc2: {wc2/(2*math.pi):.4f} Hz)")
    
    # H(s) = - (s * R2 * C1) / [ (s*R1*C1 + 1)*(s*R2*C2 + 1) ]
    # H(s) = - num_s * s / (den_s2 * s^2 + den_s1 * s + 1)
    num_s = R2 * C1
    den_s2 = R1 * R2 * C1 * C2
    den_s1 = R1 * C1 + R2 * C2
    
    print(f"H(s) coefficients: num = {-num_s} s, den = {den_s2} s^2 + {den_s1} s + 1")
    
    # Divide by den_s2 to get standard form s^2 + a s + b
    num_s_std = num_s / den_s2
    den_s1_std = den_s1 / den_s2
    den_const_std = 1.0 / den_s2
    print(f"Standard form H(s) = -{num_s_std:.4f} s / (s^2 + {den_s1_std:.4f} s + {den_const_std:.4f})")
    
    # Roots of s^2 + den_s1_std s + den_const_std
    # s = (-a +/- sqrt(a^2 - 4b)) / 2
    a = den_s1_std
    b = den_const_std
    disc = a**2 - 4*b
    if disc >= 0:
        s1 = (-a + math.sqrt(disc)) / 2
        s2 = (-a - math.sqrt(disc)) / 2
        print(f"Poles: {s1:.4f}, {s2:.4f}")
    else:
        real = -a / 2
        imag = math.sqrt(-disc) / 2
        print(f"Poles: {real:.4f} +/- {imag:.4f}j")

analyze(R1_id, R2_id, C1_id, C2_id, "IDEAL")
analyze(R1_re, R2_re, C1_re, C2_re, "REAL")
