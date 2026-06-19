import sys

filepath = 'chapters/4-circuito_3.tex'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(filepath, 'w', encoding='utf-8') as f:
    for i, line in enumerate(lines):
        # We need to comment lines 112 to 168 (which are indexes 111 to 167 but wait!
        # The line index before was 112 <= i <= 168 when uncommenting
        if 112 <= i <= 168:
            if not line.startswith('%'):
                f.write('% ' + line)
            else:
                f.write(line)
        else:
            f.write(line)
