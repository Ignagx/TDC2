import os
import glob

def downgrade_headers(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Process from smallest to largest to avoid double replacements
    content = content.replace('\\subsection{', '\\subsubsection{')
    content = content.replace('\\section{', '\\subsection{')
    content = content.replace('\\chapter{', '\\section{')
    
    # Also fix any width issues with graphics
    content = content.replace('width=0.8\\textwidth', 'width=\\columnwidth')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('chapters/*.tex'):
    downgrade_headers(filepath)

# Also fix the PGFPlots width so they don't overlap in two-column format
for filepath in glob.glob('figures/plot_*.tex'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('width=12cm,', 'width=\\columnwidth,')
    content = content.replace('width=12cm', 'width=\\columnwidth')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Headers downgraded and widths adjusted.")
