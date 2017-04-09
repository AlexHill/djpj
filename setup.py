import os
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='DjPj',
    version='0.6.0',
    description='A template-block-based Django helper for jQuery-PJAX.',
    license='BSD',
    long_description=read('README.rst').replace('\n__ #', '\n__ https://pypi.python.org/pypi/DjPj/#'),
    url='https://github.com/alexhill/djpj',
    author='Alex Hill',
    author_email='alex@hill.net.au',

    packages=find_packages(),
    install_requires=['django>=1.4'],
    tests_require=['nose'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)


def version_exclusions():

    def vstr(v):
        return '.'.join(map(str, v))

    pythons = [(2, 6), (2, 7)] + [(3, n) for n in range(3, 7)]
    djangos = [(1, n) for n in range(4, 12)]
    exclusions = [
        lambda p, d: p <= (2, 6) and d > (1, 6),
        lambda p, d: p >= (3, 3) and d < (1, 5),
        lambda p, d: p == (3, 3) and d > (1, 8),
        lambda p, d: p >= (3, 5) and d < (1, 8),
    ]
    excluded = {
        (vstr(p), d) for p in pythons for d in djangos
        if any(e(p, d) for e in exclusions)
    }
    aliases = {
        '3.3': 'pypy3',
        '2.7': 'pypy',
    }
    excluded |= {(aliases[p], d) for p, d in excluded if p in aliases}

    return "\n".join(
        "     - python: \"%s\"\n"
        "       env: DJANGO_VERSION=%s" % (p, vstr(d))
        for p, d in sorted(excluded)
    )
