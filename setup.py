import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'django-pjax-blocks',
    version = '0.2',
    description = 'A template-block-based Django helper for jQuery-PJAX.',
    license = 'BSD',
    long_description = read('README.rst'),
    url = 'https://github.com/alexhill/django-pjax-blocks',

    author = 'Alex Hill',
    author_email = 'alex@hill.net.au',

    py_modules =  ['djpjax'],
    install_requires = ['django>=1.3'],

    classifiers = (
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python',
    ),
)
