# obspycsv

CSV and CSZ read/write support, EVENTTXT read support for ObsPy earthquake catalogs

[![build status](https://github.com/trichter/obspycsv/workflows/tests/badge.svg)](https://github.com/trichter/obspycsv/actions)
[![coverage](https://codecov.io/gh/trichter/obspycsv/branch/master/graph/badge.svg)](https://codecov.io/gh/trichter/obspycsv)
[![version](https://img.shields.io/pypi/v/obspycsv.svg)](https://pypi.python.org/pypi/obspycsv)
[![pyversions](https://img.shields.io/pypi/pyversions/obspycsv.svg)](https://python.org)
[![zenodo](https://zenodo.org/badge/DOI/10.5281/zenodo.7225902.svg)](https://doi.org/10.5281/zenodo.7225902)

## Installation

Install ObsPy. After that install obspycsv using pip by:

    pip install obspycsv


## Usage EVENTTXT

```
>>> read_events('https://service.iris.edu/fdsnws/event/1/query?minmagnitude=8.5&format=text')
7 Event(s) in Catalog:
2012-04-11T08:38:37.000000Z |  +2.238,  +93.014 | 8.6  MW
2011-03-11T05:46:23.000000Z | +38.296, +142.498 | 9.1  MW
2010-02-27T06:34:13.000000Z | -36.148,  -72.933 | 8.8  MW
2007-09-12T11:10:26.000000Z |  -4.464, +101.396 | 8.5  MW
2005-03-28T16:09:35.000000Z |  +2.096,  +97.113 | 8.6  MW
2004-12-26T00:58:52.000000Z |  +3.413,  +95.901 | 9.0  MW
1960-05-22T19:11:14.000000Z | -38.170,  -72.570 | 8.5
```

## Usage CSV

CSV format can be used to store a catalog with basic origin properties. Picks cannot be stored.

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
2012-04-04T14:21:42.30000,41.818000,79.689000,1.000,4.40,mb,20120404_0000041
2012-04-04T14:18:37.00000,39.342000,41.044000,14.400,4.30,ML,20120404_0000038
2012-04-04T14:08:46.00000,38.017000,37.736000,7.000,3.00,ML,20120404_0000039
```

It is possible to load arbitrary csv files. Define the field names in the code or use the first line in the file to define the field names.
The following field names have to be used to read the origin time: `time` (UTC time string) or `year, mon, day, hour, minu, sec`.
The following additional field names have to be used: `lat, lon, dep, mag, magtype, id`. `magtype`, `mag` and `id` are optional.
For external csv files, the format `'CSV'` has to be explicitly specified.

```
>>> cat external.csv
Year, Month, Day, Hour, Minute, Seconds, code, Lat, Lon, Depth, Station_count, time_residual_RMS, Magnitude, etc
2023, 05, 06, 19, 55, 01.3, LI, 10.1942, 124.8300, 50.47, 111, 0.0, 0.2, 42, 0.0, 0.0176, 0.0127, 0.02, 0.3, 2023abcde
>>> names = 'year mon day hour minu sec _ lat lon dep _ _ mag _ _ _ _ _ _ id'.split()
events = read_events('external.csv', 'CSV', skipheader=1, names=names)
1 Event(s) in Catalog:
2023-05-06T19:55:01.300000Z | +10.194, +124.830 | 0.2  None
```

## Usage CSZ

CSZ format can be used to store a catalog with picks in a set of csv files zipped into a single file.
It works similar to NumPy's npz format.
Compression may be used with `compression` and `compresslevel` parameters
(see [zipfile doc](https://docs.python.org/library/zipfile.html#zipfile.ZipFile)).

```
>>> events = read_events('/path/to/example.pha')
>>> print(events)
2 Event(s) in Catalog:
2025-05-14T14:35:35.510000Z | +40.225,  +10.450 | 3.5  None
2025-05-14T15:43:05.280000Z | +40.223,  +10.450 | 1.8  None
>>> print(len(events[0].picks))
2
>>> events.write('catalog.csz', 'CSZ')
>>> events2 = read_events('catalog.csz')  # add check_compression=False for ObsPy version < 1.4
>>> print(events2)
2 Event(s) in Catalog:
2025-05-14T14:35:35.510000Z | +40.225,  +10.450 | 3.5  None
2025-05-14T15:43:05.280000Z | +40.223,  +10.450 | 1.8  None
>>> print(len(events2[0].picks))
2
```

## Load CSV/CSZ file into numpy array

For plotting, e.t.c, it is useful to represent the event paramters with a numpy
array.
The `load_csv` function can be used to load a CSV or CSZ file as numpy array.

```py
>>> from obspycsv import load_csv
>>> t = load_csv('catalog.csz')
>>> print(t)
[('2012-04-04T14:21:42.300', 41.818, 79.689,  1. , 4.4, 'mb', '20120404_0000041')
 ('2012-04-04T14:18:37.000', 39.342, 41.044, 14.4, 4.3, 'ML', '20120404_0000038')
 ('2012-04-04T14:08:46.000', 38.017, 37.736,  7. , 3. , 'ML', '20120404_0000039')]
 >>> print(t['mag')
 [4.4 4.3 3. ]
```

## Convert ObsPy catalog into numpy array

The `events2array` function  can be used to convert an ObsPy catalog to numpy array.
Code example creating event plots:

```py
import matplotlib.pyplot as plt
from obspy import read_events
from obspycsv import events2array

events = read_events()
t = events2array(events)
plt.subplot(121)
plt.scatter(t['lon'], t['lat'], 4*t['mag']**2)
plt.subplot(122)
plt.scatter(t['time'], t['mag'], 4*t['mag']**2)
plt.show()
```

## Miscellaneous

Plese submit an issue if you want to see support for other properties.
Questions can be asked in the ObsPy forum.
