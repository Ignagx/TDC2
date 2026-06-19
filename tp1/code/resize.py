import re

def set_size(filename, width, height):
    with open(filename, 'r') as f:
        content = f.read()
    content = re.sub(r'width\s*=\s*[0-9\.]+\\\\(columnwidth|textwidth)', lambda m: f'width={width}', content)
    content = re.sub(r'width\s*=\s*[0-9\.]+cm', lambda m: f'width={width}', content)
    content = re.sub(r'height\s*=\s*[0-9\.]+\\\\(columnwidth|textwidth)', lambda m: f'height={height}', content)
    content = re.sub(r'height\s*=\s*[0-9\.]+cm', lambda m: f'height={height}', content)
    with open(filename, 'w') as f:
        f.write(content)

set_size('figures/plot_poles_circuito_3.tex', r'0.75\columnwidth', '4cm')
set_size('figures/plot_polar_circuito_3.tex', '5cm', '5cm')
set_size('figures/plot_asymptotic_gain_circuito_3.tex', r'0.85\columnwidth', '4.2cm')
set_size('figures/plot_asymptotic_phase_circuito_3.tex', r'0.85\columnwidth', '4.2cm')
