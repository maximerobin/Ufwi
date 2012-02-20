all:
	$(MAKE) -C ufwi_log
	$(MAKE) -C ufwi_logqt

lrelease:
	$(MAKE) -C ufwi_log lrelease
	$(MAKE) -C ufwi_logqt lrelease

clean:
	find . -name '*.pyc' -delete
	rm -rf build
	$(MAKE) -C ufwi_log clean
	$(MAKE) -C ufwi_logqt clean
	$(MAKE) -C doc clean

todo:
	@grep -Rn "\(TODO\|FIXME\|XXX\)" ufwi_log
