MATERIA := $(notdir $(abspath $(CURDIR)/..))
TP := $(notdir $(CURDIR))
OUTPUT_NAME := $(MATERIA)_$(TP)

SRC := main.tex

all:
	latexmk -pdf $(SRC) -shell-escape
	cp main.pdf $(OUTPUT_NAME).pdf

clean:
	latexmk -CA $(SRC)
	rm -f main.pdf
	rm -f *-figure*.*
