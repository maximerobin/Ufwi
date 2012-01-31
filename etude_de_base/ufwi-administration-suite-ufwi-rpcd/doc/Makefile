
SUBDIRS = en fr

all:
	$(MAKE) recursive TARGET=all

clean:
	$(MAKE) recursive TARGET=clean

recursive:
	@for dir in $(SUBDIRS); do\
		echo "[+] $$dir ($(TARGET))";\
		make -C $$dir $(TARGET);\
	done

.PHONY: all clean recursive
