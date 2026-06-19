import os
import re

input_file = 'sources/circuito3_phase_and_magnitude.txt'
output_file = 'sources/circuito3_cleaned.txt'

with open(input_file, 'r', encoding='latin-1') as f:
    lines = f.readlines()

out_lines = ['Freq(Hz)\tMag_Ideal(dB)\tPhase_Ideal(deg)\tMag_Real(dB)\tPhase_Real(deg)\n']

last_ph_i = None
last_ph_r = None
offset_i = 0
offset_r = 0

for line in lines[1:]:
    line = line.strip()
    if not line: continue
    parts = re.split(r'\s+', line)
    if len(parts) >= 3:
        freq = parts[0]
        ideal = parts[1].replace('(', '').replace(')', '').replace('dB', '').replace('°', '')
        real = parts[2].replace('(', '').replace(')', '').replace('dB', '').replace('°', '')
        
        mag_i_str, ph_i_str = ideal.split(',')
        mag_r_str, ph_r_str = real.split(',')
        
        mag_i = float(mag_i_str)
        ph_i = float(ph_i_str)
        mag_r = float(mag_r_str)
        ph_r = float(ph_r_str)
        
        # Unwrap phase ideal
        if last_ph_i is not None:
            if ph_i - last_ph_i > 180:
                offset_i -= 360
            elif ph_i - last_ph_i < -180:
                offset_i += 360
        
        # Unwrap phase real
        if last_ph_r is not None:
            if ph_r - last_ph_r > 180:
                offset_r -= 360
            elif ph_r - last_ph_r < -180:
                offset_r += 360
        
        last_ph_i = ph_i
        last_ph_r = ph_r
        
        ph_i += offset_i
        ph_r += offset_r
        
        out_lines.append(f"{freq}\t{mag_i}\t{ph_i}\t{mag_r}\t{ph_r}\n")

with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)
print(f"Cleaned and unwrapped data saved to {output_file}")
