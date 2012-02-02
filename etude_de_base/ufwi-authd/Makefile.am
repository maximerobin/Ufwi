if BUILD_NUAUTH_COMMAND
	
SUBDIRS = scripts ufwi-authd-cmd

EXTRA_DIST = setup.py

install-exec-local:
$(PYTHON) $(srcdir)/setup.py install --prefix $(DESTDIR)$(prefix)

clean-local:
$(PYTHON) $(srcdir)/setup.py clean; \
rm -rf $(top_builddir)/scripts/ufwi-authd-cmd/build

uninstall-local:
[ ! -f "$(DESTDIR)$(prefix)/bin/ufwi-authd-cmd" ] || rm -f "$(DESTDIR)$(prefix)/bin/ufwi-authd-cmd"
find "$(DESTDIR)$(prefix)/lib" -name "ufwi-authd-cmd-*.egg-info" -delete ||true

endif
