# Copyright 2013-2017 Tom Eulenfeld, MIT license
import os.path
import re

from setuptools import setup


def find_version(*paths):
    fname = os.path.join(os.path.dirname(__file__), *paths)
    with open(fname) as fp:
        code = fp.read()
    match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", code, re.M)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")

version = find_version('obspycsv.py')

with open('README.md') as f:
    README = f.read()
DESCRIPTION = README.split('\n')[2]

ENTRY_POINTS = {
    'obspy.plugin.event': ['CSV = obspycsv',
                           'CSZ = obspycsv',
                           'EVENTTXT = obspycsv'],
    'obspy.plugin.event.CSV': [
        'isFormat = obspycsv:_is_csv',
        'readFormat = obspycsv:read_csv',
        'writeFormat = obspycsv:write_csv_default'],
    'obspy.plugin.event.CSZ': [
        'isFormat = obspycsv:_is_csz',
        'readFormat = obspycsv:read_csz',
        'writeFormat = obspycsv:write_csz'],
    'obspy.plugin.event.EVENTTXT': [
        'isFormat = obspycsv:_is_eventtxt',
        'readFormat = obspycsv:read_eventtxt']
    }

CLASSIFIERS = [
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'Topic :: Scientific/Engineering :: Physics'
    ]

setup(name='obspycsv',
      version=version,
      description=DESCRIPTION,
      url='https://github.com/trichter/obspycsv',
      author='Tom Eulenfeld',
      license='MIT',
      py_modules=['obspycsv'],
      install_requires=['obspy', 'setuptools'],
      entry_points=ENTRY_POINTS,
      zip_safe=False,
      include_package_data=True,
      classifiers=CLASSIFIERS
      )
