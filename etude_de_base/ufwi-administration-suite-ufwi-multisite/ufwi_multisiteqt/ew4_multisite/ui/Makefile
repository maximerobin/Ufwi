UI_FILES = $(wildcard *.ui)
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)

PYUIC = pyuic4
RCC = rcc

all: $(UI_PY_FILES)

%_ui.py: %.ui
	$(PYUIC) -o $@ $^
	sed -i '/import multisite_rc/D;/setSortingEnabled/D' $@
