# TP3: Filtros digitales

Enunciado: `TP3_TeoriaII_2026.pdf`. Informe: `informe/TDC2_TP3.pdf` (4 páginas, plantilla IEEE).

## Scripts
- `graficador.py`: graficador de la cátedra corregido. El original (`graficador_original.py`) perdía cerca de un tercio de cada bloque porque leía el puerto de a un byte. Ahora lee en bloques desde un proceso aparte y además mide ganancia y fase en vivo. Con la tecla `b` registra puntos de un barrido en `barrido_<fecha>.csv`. Uso: `python graficador.py --ej 1`.
- `ej2_filtro_digital.py`: Ejercicio 2 completo (pasa banda del Grupo 2, fs = 200 kHz). Opciones agregadas: `--bordes` aplica la corrección con predistorsión de los bordes de banda, y `--guardar PREFIJO` guarda los gráficos en PDF.

## Mediciones del Ejercicio 1 (Blue Pill, fs = 1 kHz)
| Archivo | Medición |
|---|---|
| `barrido_20261127_204457.csv` | Punto 3: barrido de 1 a 100 Hz (1,13 Vpp sobre 0,72 V) |
| `captura_20261127_221322.csv` … `221759.csv` | Punto 1: estática, 0,6 / 1,2 / 1,8 / 2,4 / 3,0 V |
| `captura_20261127_222053.csv` | Punto 2: escalón (cuadrada de 0,5 Hz, 0,65 a 3,04 V) |
| `captura_20261127_215448.csv`, `215601.csv`, `215625.csv` | Punto 6: aliasing a 950, 990 y 1010 Hz |
| `captura_20261127_215535.csv` | Repetición de la de 950 Hz (no se usa) |
| `captura_20261127_205503.csv`, `205505.csv`, `210721.csv` | Bloques de prueba a 100 Hz y 1 Hz (no se usan) |
| `captura_20261127_220241.csv`, `220353.csv` | Primer intento de la estática, con el generador analógico (no se usan) |

## Regenerar el informe
Desde `informe/`:
```
python generar_datos.py     # Ejercicio 1: lee los CSV y escribe datos/
python generar_ej2.py       # Ejercicio 2: usa ../ej2_filtro_digital.py
pdflatex TDC2_TP3.tex       # dos veces, para las referencias
```
Qué archivo corresponde a cada medición se configura al principio de `generar_datos.py`.
