MATERIA := TDC2
TP := TP1
CURSO := 4R2
GRUPO := Grupo2
OUTPUT_NAME := $(MATERIA)_$(TP)_$(CURSO)_$(GRUPO)

SRC := main.tex

all:
	latexmk -pdf $(SRC) -shell-escape
	cp main.pdf $(OUTPUT_NAME).pdf

clean:
	latexmk -CA $(SRC)
	rm -f main.pdf
	rm -f *-figure*.*
