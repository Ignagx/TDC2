import os
import re

input_file = 'sources/circuito3_phase_and_magnitude.txt'
output_file = 'sources/circuito3_cleaned.txt'

with open(input_file, 'r', encoding='latin-1') as f:
    lines = f.readlines()

out_lines = ['Freq(Hz)\tMag_Ideal(dB)\tPhase_Ideal(deg)\tMag_Real(dB)\tPhase_Real(deg)\n']

for line in lines[1:]:
    line = line.strip()
    if not line: continue
    # Extract the columns split by tabs or spaces
    parts = re.split(r'\s+', line)
    if len(parts) >= 3:
        freq = parts[0]
        # Clean parens and units
        ideal = parts[1].replace('(', '').replace(')', '').replace('dB', '').replace('°', '')
        real = parts[2].replace('(', '').replace(')', '').replace('dB', '').replace('°', '')
        
        mag_i, ph_i = ideal.split(',')
        mag_r, ph_r = real.split(',')
        
        out_lines.append(f"{freq}\t{mag_i}\t{ph_i}\t{mag_r}\t{ph_r}\n")

with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)
print(f"Cleaned data saved to {output_file}")
