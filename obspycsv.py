## Copyright 2022 Tom Eulenfeld, MIT license
"""
Simple CSV read/write support for ObsPy earthquake catalogs

You have to use the field names
time or year, mon, day, hour, minu, sec
lat, lon, dep, mag, magtype, id
(see global FIELDS variable)
"""

import csv
from string import Formatter

from obspy import UTCDateTime as UTC
from obspy.core.event import Catalog, Event, Magnitude, Origin, ResourceIdentifier


__version__ = '0.2.0'
DEFAULT = {'magtype': 'None'}
FIELDS = '{time!s:.22} {lat:.4f} {lon:.4f} {dep:.3f} {mag:.1f} {magtype} {id}'.split()


def _is_csv(fname, **kwargs):
    try:
        read_csv(fname)
    except:
        return False
    return True


def read_csv(fname, skipheader=0, depth_in_km=True, default=None,
             **kwargs):
    """
    Read a CSV file and return ObsPy Catalog

    :param skipheader: skip first rows of file
    :param depth_in_kim: depth is given in kilometer (default: True) or
        meter (False)
    :param default: dictionary with default values, at the moment only
         magtype is supported,
         i.e. to set magtypes use `default={'magtype': 'Ml'}`
    :param **kargs: all other kwargs are passed to csv.DictReader,
        important additional arguments are fieldnames, dialect, delimiter, etc

    You can read csv files created by this module or external csv files.
    Example reading an external csv file:

        from obspy import read_events
        fields = 'year mon day hour minu sec _ lat lon dep _ _ mag _ _ _ _ _ _ id'.split()
        catalog = read_events('external.csv', 'CSV', skipheader=1, fieldnames=fields)
    """
    if default is None:
        default= DEFAULT
    events = []
    with open(fname) as f:
        for _ in range(skipheader):
            next(f)
        reader = csv.DictReader(f, **kwargs)
        for row in reader:
            if 'time' in row:
                time = UTC(row['time'])
            else:
                time = UTC('{year}-{mon}-{day} {hour}:{minu}:{sec}'.format(**row))
            dep = float(row['dep']) * (1000 if depth_in_km else 1)
            origin = Origin(time=time, latitude=row['lat'], longitude=row['lon'], depth=dep)
            magtype = row.get('magtype', DEFAULT.get('magtype'))
            if magtype == 'None':
                magtype = None
            # add zero to eliminate negative zeros in magnitudes
            mag = float(row['mag'])+0
            magnitude = Magnitude(mag=mag, magnitude_type=magtype)
            id_ = ResourceIdentifier(row['id'].strip()) if 'id' in row else None
            event = Event(magnitudes=[magnitude], origins=[origin], resource_id=id_)
            events.append(event)
    return Catalog(events=events)


def write_csv(events, fname, depth_in_km=True, delimiter=',', fields=FIELDS):
    """
    Write ObsPy catalog to CSV file

    :param events: catalog or list of events
    :param fname: file name
    :param depth_in_km: write depth in units of kilometer (default: True) or meter
    :param delimiter: defaults to `','`
    :param fields: List of field names and the corresponding formatting, see
       default in global `FIELDS` variable
    """
    fmtstr = delimiter.join(fields)
    fieldnames = [
        fn for _, fn, _, _ in Formatter().parse(fmtstr) if fn is not None]
    with open(fname, 'w') as f:
        f.write(delimiter.join(fieldnames) + '\n')
        for event in events:
            try:
                ori = event.preferred_origin() or event.origins[0]
                mag = event.preferred_magnitude() or event.magnitudes[0]
            except:
                from warnings import warn
                eventstr = str(event).splitlines()[0]
                warn(f'Cannot write event, because no origin or no magnitude was found: {eventstr}')
                continue
            id_ = str(event.resource_id).split('/')[-1]
            d = {'time': ori.time,
                 'lat': ori.latitude,
                 'lon': ori.longitude,
                 'dep': ori.depth / (1000 if depth_in_km else 1),
                 'mag': mag.mag,
                 'magtype': mag.magnitude_type,
                 'id': id_}
            f.write(fmtstr.format(**d) + '\n')
