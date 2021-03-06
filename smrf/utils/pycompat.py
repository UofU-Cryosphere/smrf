# flake8: noqa
import sys

PY3 = sys.version_info[0] >= 3

if PY3:  # pragma: no cover
    basestring = str
    unicode_type = str
    bytes_type = bytes

    def iteritems(d):
        return iter(d.items())

    def itervalues(d):
        return iter(d.values())

    pyrange = range
    pyzip = zip
    import builtins
    from configparser import SafeConfigParser
    from functools import reduce as pyreduce
else:  # pragma: no cover
    # Python 2
    basestring = basestring
    unicode_type = unicode
    bytes_type = str

    def iteritems(d):
        return d.iteritems()

    def itervalues(d):
        return d.itervalues()

    pyrange = xrange
    from itertools import imap as pymap
    from itertools import izip as pyzip
    pyreduce = reduce
    import __builtin__ as builtins
    from ConfigParser import SafeConfigParser


try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
