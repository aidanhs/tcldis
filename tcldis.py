from __future__ import print_function

def _tcldis_init():
    import sys
    import _tcldis
    mod = sys.modules[__name__]
    for key, value in _tcldis.__dict__.iteritems():
        if not callable(value):
            continue
        mod.__dict__[key] = value

_tcldis_init()
