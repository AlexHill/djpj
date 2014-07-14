import sys

PY2 = sys.version_info[0] == 2

if PY2:
    import Queue as queue
    string_types = basestring,
else:
    import queue
    string_types = str,