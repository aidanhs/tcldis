# Flags to improve security
CFLAGS_SEC = \
	-fstack-protector \
	--param=ssp-buffer-size=4 \
	-Wformat \
	-Werror=format-security \
	-D_FORTIFY_SOURCE=2\
	-Wl,-z,relro,-z,now
# Protect against my own poor programming
CFLAGS_SAFE = -fno-strict-overflow
# Tell me when I'm doing something wrong
CFLAGS_WARN = \
	-Wall -Wextra \
	-Wstrict-aliasing -Wstrict-overflow -Wstrict-prototypes
# Not interested in these warnings
CFLAGS_NOWARN = -Wno-unused-parameter
# Speed things up
CFLAGS_FAST = -O2

CFLAGS = \
	$(CFLAGS_SEC) $(CFLAGS_SAFE) \
	$(CFLAGS_WARN) $(CFLAGS_NOWARN) \
	$(CFLAGS_FAST)

# TODO:
#  - check python-config works
#  - check stubs are supported (TCL_SUPPORTS_STUBS)

TCLCONFIG?=/usr/lib/tclConfig.sh
TCL_LIB     = $(shell . $(TCLCONFIG); echo $$TCL_LIB_SPEC)
TCL_INCLUDE = $(shell . $(TCLCONFIG); echo $$TCL_INCLUDE_SPEC)
PY_LIB      = $(shell python-config --libs)
PY_INCLUDE  = $(shell python-config --includes)
PY_LIBFILE  = $(shell python -c 'import distutils.sysconfig; print distutils.sysconfig.get_config_var("LDLIBRARY")')
CFLAGS += -DPY_LIBFILE='"$(PY_LIBFILE)"'

default: _tcldis.so

_tcldis.so: _tcldis.o
	gcc -shared -fPIC $(CFLAGS) $< -o $@ -Wl,--export-dynamic $(TCL_LIB) $(PY_LIB)

_tcldis.o: src/tcldis.c
	test -f $(TCLCONFIG)
	gcc -fPIC $(CFLAGS) $(PY_INCLUDE) $(TCL_INCLUDE) -c $< -o $@

clean:
	rm -f *.so *.o

.PHONY: clean default
