UI_FILES = $(wildcard *.ui)
UI_PY_FILES = $(UI_FILES:%.ui=%_ui.py)
PYUIC = pyuic4

all: $(UI_PY_FILES)

%_ui.py: %.ui
	$(PYUIC) -o $@ $^

	# TODO: ugly hack, because of a usefull import by
	#       Qt in the ufwi_log_ui.py file.. But we *don't*
	#       want to use a python resource file!!
	sed -i '/import ufwi_log_rc/D' $@
	sed -i '/import edenwall_rc/D' $@

clean:
	 rm -f *.pyc
	 rm -f $(UI_PY_FILES)
