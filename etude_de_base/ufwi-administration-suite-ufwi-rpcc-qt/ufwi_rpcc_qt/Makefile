
UI_FILES = $(wildcard *.ui)
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)

PYUIC = pyuic4
RCC = rcc

all: $(UI_PY_FILES)

%_ui.py: %.ui
	$(PYUIC) -o $@ $^
	sed -i '/import ufwi_rpcc_qt_rc/D' $@

lrelease: $(QM_FILES)

clean:
	rm -f $(UI_PY_FILES) *.pyc

help:
	@echo "The following targets are valid for this Makefile:"
	@echo "... all      : compile ui and translation files"
	@echo "... clean    : remove generated files"

.PHONY: all clean

