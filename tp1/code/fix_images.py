import os
import glob

# Reemplaza entornos float para forzarlos
for filepath in glob.glob('chapters/*.tex'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Cambiamos !ht por H
    content = content.replace('\\begin{figure}[!ht]', '\\begin{figure}[H]')
    content = content.replace('\\begin{figure}[htbp]', '\\begin{figure}[H]')
    content = content.replace('\\begin{figure}[h]', '\\begin{figure}[H]')
    content = content.replace('\\begin{table}[!ht]', '\\begin{table}[H]')
    content = content.replace('\\begin{table}[htbp]', '\\begin{table}[H]')
    content = content.replace('\\begin{table}[h]', '\\begin{table}[H]')
    
    # Reducimos los anchos un poquito mas para evitar superposicion en columnas
    content = content.replace('width=\\columnwidth', 'width=0.9\\columnwidth')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob('figures/plot_*.tex'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Achicamos un pelin los plots para asegurar el margen en la columna
    content = content.replace('width=\\columnwidth,', 'width=0.9\\columnwidth,')
    content = content.replace('width=\\columnwidth', 'width=0.9\\columnwidth')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Imagenes ajustadas y forzadas a [H].")
