# obspycsv

Simple CSV read/write support for ObsPy earthquake catalogs

[![build status](https://github.com/trichter/obspycsv/workflows/tests/badge.svg)](https://github.com/trichter/obspycsv/actions)
[![coverage](https://codecov.io/gh/trichter/obspycsv/branch/master/graph/badge.svg)](https://codecov.io/gh/trichter/obspycsv)
[![version](https://img.shields.io/pypi/v/obspycsv.svg)](https://pypi.python.org/pypi/obspycsv)
[![pyversions](https://img.shields.io/pypi/pyversions/obspycsv.svg)](https://python.org)
[![zenodo](https://zenodo.org/badge/DOI/10.5281/zenodo.7225902.svg)](https://doi.org/10.5281/zenodo.7225902)

Writes and reads the most basic properties of ObsPy earthquake catalogs to/from CSV files.

## Installation

Install obspy. After that install obspycsv using pip by:

    pip install obspycsv


## Usage

Basic example using ObsPy's `read_events()`

```
>>> from obspy import read_events
>>> events = read_events()  # load example events
>>> print(events)
3 Event(s) in Catalog:
2012-04-04T14:21:42.300000Z | +41.818,  +79.689 | 4.4  mb | manual
2012-04-04T14:18:37.000000Z | +39.342,  +41.044 | 4.3  ML | manual
2012-04-04T14:08:46.000000Z | +38.017,  +37.736 | 3.0  ML | manual
>>> events.write('catalog.csv', 'CSV')  # declare 'CSV' as format
>>> print(read('catalog.csv'))
3 Event(s) in Catalog:
2012-04-04T14:21:42.300000Z | +41.818,  +79.689 | 4.4  mb
2012-04-04T14:18:37.000000Z | +39.342,  +41.044 | 4.3  ML
2012-04-04T14:08:46.000000Z | +38.017,  +37.736 | 3.0  ML
>>> cat catalog.csv
time,lat,lon,dep,mag,magtype,id
2012-04-04T14:21:42.30,41.8180,79.6890,1.000,4.4,mb,20120404_0000041
2012-04-04T14:18:37.00,39.3420,41.0440,14.400,4.3,ML,20120404_0000038
2012-04-04T14:08:46.00,38.0170,37.7360,7.000,3.0,ML,20120404_0000039
```

It is not possible to write picks, only basic origin and magnitude properties.
It is possible, however, to load arbritary csv files. Define the field names in the code or use the first line in the file to define the field names.
The following field names have to be used to read the origin time `time` (UTC time string) or `year, mon, day, hour, minu, sec`.
The following additional field names have to be used: `lat, lon, dep, mag, magtype, id`. `magtype` and `mag` are optional.
For external csv files, the format `'CSV'` has to be explicietly specified.

```
>>> cat external.csv
Year, Month, Day, Hour, Minute, Seconds, code, Lat, Lon, Depth, Station_count, time_residual_RMS, Magnitude, etc
2023, 05, 06, 19, 55, 01.3, LI, 10.1942, 124.8300, 50.47, 111, 0.0, 0.2, 42, 0.0, 0.0176, 0.0127, 0.02, 0.3, 2023abcde
>>> fields = 'year mon day hour minu sec _ lat lon dep _ _ mag _ _ _ _ _ _ id'.split()
events = read_events('external.csv', 'CSV', skipheader=1, fieldnames=fields)
1 Event(s) in Catalog:
2023-05-06T19:55:01.300000Z | +10.194, +124.830 | 0.2  None
```
