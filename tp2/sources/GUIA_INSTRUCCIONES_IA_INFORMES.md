# Guía de instrucciones para IA (informes técnicos)

Este documento define las reglas obligatorias para que una IA genere informes de laboratorio para las diferentes materias con formato consistente, basándose en los estándares establecidos en los trabajos previos.

## Reglas obligatorias

1. **Clase LaTeX obligatoria**
   - Debe usarse `informeutn.cls`.
   - El archivo principal debe iniciar con:
     - `\documentclass[]{informeutn}` (o `\documentclass[chaptersright]{informeutn}` si se desea que los capítulos inicien en página impar/derecha).
   - No se permite reemplazar esta clase por `article`, `report`, u otras.

2. **Compilación obligatoria con latexmk**
   - El flujo de compilación debe usar `latexmk` y `make` como herramientas principales.
   - Todos los trabajos prácticos deben tener el siguiente `Makefile` en su raíz:
     ```makefile
     MATERIA := $(notdir $(abspath $(CURDIR)/..))
     TP := $(notdir $(CURDIR))
     OUTPUT_NAME := $(MATERIA)_$(TP)

     SRC := main.tex

     all:
     	latexmk -pdf -jobname=$(OUTPUT_NAME) $(SRC)

     clean:
     	latexmk -CA -jobname=$(OUTPUT_NAME) $(SRC)
     ```

3. **Estructura modular (main + capítulos por archivo)**
   - El archivo raíz debe llamarse `main.tex`.
   - Los capítulos deben estar en una carpeta `chapters/`.
   - El archivo principal debe incluirlos con `\input{chapters/X-nombre.tex}`.
   - **Orden del Documento:**
     ```latex
     \begin{document}
       \maketitle
       \tableofcontents
       \setcounter{page}{1}
       \thispagestyle{plain}
       
       \input{...} % Capítulos
       
       % Bibliografía (si aplica)
       \nocite{*}
       \printbibliography[heading=bibnumbered, title={Fuentes}]
       
       \input{...} % Anexos (si aplica)
     \end{document}
     ```
    - El numero (X) del archivo es el orden en el que será incluido en el informe, arrancando con
        1-integrantes (si aplica) o 1-introduccion.

4. **Metadatos y Carátula**
   - Es obligatorio definir: `\materia`, `\titulo`, `\comision`, `\autores`, `\fecha`.
   - `\subtitulo` es opcional pero recomendado para detallar el tema del TP.
   - En `\autores`, incluir nombre completo, legajo (opcional según materia).
   - En `\fecha`, es aceptable usar `\today` o una fecha fija.

5. **Organización de Directorios**
   - `chapters/`: Archivos `.tex` de los capítulos.
   - `images/`: Diagramas, capturas de pantalla y gráficos vectoriales.
   - `pictures/`: Fotos de laboratorio.
   - `figures/`: Archivos `.tex` con plots, diagramas (tikz o circuitikz) y cualquier otra fuente de graficos. Cada
       archivo tiene una figura individual que se incluye en el archivo del capitulo que corresponde. No deben tener el
       entorno `figure`, `minipage` o similar, este debe estar en el archivo del capitulo.
   - `sources/` Archivos con consignas y fuentes de datos (ej.: proyectos ltspice, kicad, etc.)
   - `common/`: (Ubicada en la raíz del repositorio) Para recursos compartidos como anexos comunes.

6. **Figuras, Tablas y Ecuaciones**
   - **Flotantes:** Siempre usar el especificador `[!ht]`.
   - **Alineación:** Siempre usar `\centering`.
   - **Circuitos:** Preferir `circuitikz` dentro de un entorno `tikzpicture`.
   - **Tablas:** Si son muy anchas, usar `\resizebox{\textwidth}{!}{\begin{tabular}{...}}`. Usar bordes (`|l|c|`) según el estilo predominante.
   - **Referencias Cruzadas:** Usar el formato `\ref{type:name}`.
     - `fig:` para figuras.
     - `tab:` para tablas.
     - `eq:` para ecuaciones.
     - `crkt:` para esquemáticos/circuitos.
     - `list:` para listados de código.
   - **Subfiguras:** Usar el paquete `subcaption` con alineamiento `[t]`.

7. **Gestión de Código y Simulaciones**
   - Usar el paquete `listings`.
   - Definir/usar el estilo `ltspice` para listados de netlists o parámetros de simulación:
     ```latex
     \lstdefinestyle{ltspice}{
       backgroundcolor=\color{gray!10},
       basicstyle=\ttfamily\small,
       keywordstyle=\color{blue},
       frame=single,
       breaklines=true,
       captionpos=b
     }
     ```
   - Usar `\lstinputlisting` para archivos de código externos.

8. **Bibliografía**
   - Usar `biblatex` con backend `bibtex` (o `biber` si se especifica) y estilo `alphabetic`.
   - Archivo de recursos: `fuentes.bib`.
   - Configuración típica en el preámbulo:
     ```latex
     \usepackage[backend=bibtex, style=alphabetic, sorting=ynt]{biblatex}
     \addbibresource{fuentes.bib}
     ```

9. **Unidades y Formato de Texto**
   - **Unidades:** Usar la biblioteca siunitx para agregar unidades del sistema internacional con sus prefijos correspondientes. NO escribir unidades como texto simple si existe el comando. Cuando se quiera poner un comando de unidad, debe estar en un entorno `$ $` si es con numero. Si es solo la unidad, se puede omitir el entorno matematico.
   - **Matemática:** Usar entornos `equation` para fórmulas numeradas y `gather*` o `align*` para desarrollos.
   - **Énfasis:** No utilizar negrita (`\textbf`) para resaltar palabras clave o términos técnicos dentro de los párrafos.

10. **Requisitos de Contenido Mínimo**
    - **Capítulo de Integrantes:** (Opcional según materia) Tabla de roles y fechas.
    - **Capítulo de Introducción:** Objetivos y breve descripción del TP.
    - **Capítulo de Conclusiones:** Análisis de resultados y cumplimiento de objetivos.
    - **Anexos:** Hojas de datos (datasheets), cálculos extensos o código fuente completo.

## Criterio operativo para la IA

- **Consistencia Visual:** Mantener el espaciado y estilo de tablas de los informes previos.
- **Precisión Técnica:** Las referencias a figuras y tablas deben ser exactas.
- **Modularidad:** No escribir todo en un solo archivo; separar por lógica de capítulos.
- **Validación:** No re-incluir paquetes en el preámbulo que ya estén presentes en la clase base (e.g., `circuitikz`, `pgfplots`).
- **Escritura:** Maximo 120 caracteres por linea. Evitar el uso de `\textbf` en párrafos.

