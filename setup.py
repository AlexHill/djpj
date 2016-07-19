import os
try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='DjPj',
    version='0.5.0',
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
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
