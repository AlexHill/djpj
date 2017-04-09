import sys

PY2 = sys.version_info[0] == 2

if PY2:
    import Queue as queue
else:
    import queue
