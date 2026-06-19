import sys

filepath = 'chapters/4-circuito_3.tex'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(filepath, 'w', encoding='utf-8') as f:
    for i, line in enumerate(lines):
        # The commented block starts around line 113 to 169
        if 112 <= i <= 168:
            if line.startswith('% '):
                f.write(line[2:])
            elif line.startswith('%'):
                f.write(line[1:])
            else:
                f.write(line)
        else:
            f.write(line)
