RST_FILES = $(wildcard *.rst)
HTML_FILES = $(RST_FILES:.rst=.html)

all: $(HTML_FILES)

doxygen:
	/usr/bin/doxygen -u

%.html: %.rst
	rst2html --stylesheet-path=style.css $< $@

clean:
	rm -f $(HTML_FILES) ufwi_log.tex

.PHONY: all clean
