## Copyright 2022 Tom Eulenfeld, MIT license
"""
CSV and CSZ read/write support for ObsPy earthquake catalogs

You have to use the field names
time or year, mon, day, hour, minu, sec
lat, lon, dep, mag, magtype, id
(see global FIELDS variable)
"""
import csv
from contextlib import contextmanager
import io
import math
from string import Formatter

from obspy import UTCDateTime as UTC
from obspy.core.event import (
    Catalog, Event, Origin, Magnitude, Pick, WaveformStreamID, Arrival,
    ResourceIdentifier)


__version__ = '0.3.0'

DEFAULT = {'magtype': None}
FIELDS = '{time!s:.25} {lat:.6f} {lon:.6f} {dep:.3f} {mag:.2f} {magtype} {id}'.split()
PFIELDS = '{seedid} {phase} {time:.5f} {weight:.3f}'.split()


def _is_csv(fname, **kwargs):
    try:
        read_csv(fname)
    except:
        return False
    return True


def _is_csz(fname, **kwargs):
    try:
        import zipfile
        with zipfile.ZipFile(fname) as zipf:
            assert 'events.csv' in zipf.namelist()
    except:
        return False
    return True


def _evid(event):
    return str(event.resource_id).split('/')[-1]


def _origin(event):
    return event.preferred_origin() or event.origins[0]


@contextmanager
def _open(filein, *args, **kwargs):
    "Accept both files or file names"""
    if isinstance(filein, str):  # filename
        with open(filein, *args, **kwargs) as f:
            yield f
    else:  # file-like object
        yield filein


def read_csz(fname, default=None, check_compression=None):
    """
    Read a CSZ file and return ObsPy Catalog with picks

    :param default: dictionary with default values, at the moment only
         magtype is supported,
         i.e. to set magtypes use `default={'magtype': 'Ml'}`
    """
    import zipfile
    with zipfile.ZipFile(fname) as zipf:
        with io.TextIOWrapper(zipf.open('events.csv'), encoding='utf-8') as f:
            events = read_csv(f, default=default)
        for event in events:
            evid = _evid(event)
            fname = f'picks_{evid}.csv'
            if fname not in zipf.namelist():
                continue
            with io.TextIOWrapper(zipf.open(fname), encoding='utf-8') as f:
                _read_picks(event, f)
    return events


def write_csz(events, fname, **kwargs):
    """
    Write ObsPy catalog to CSZ file

    :param events: catalog or list of events
    :param fname: file name
    :param **kwargs: compression and compression level can be specified see
    https://docs.python.org/library/zipfile.html#zipfile.ZipFile
    ```
    events.write('CSZ', compression=True, compresslevel=9)
    ```
    """
    import zipfile
    if kwargs.get('compression') is True:  # allow True as value for compression
        kwargs['compression'] = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(fname, mode='w', **kwargs) as zipf:
        with io.StringIO() as f:
            write_csv(events, f)
            zipf.writestr('events.csv', f.getvalue())
        for event in events:
            if len(event.picks) == 0:
                continue
            evid = str(event.resource_id).split('/')[-1]
            try:
                _origin(event)
            except:
                continue
            with io.StringIO() as f:
                _write_picks(event, f)
                zipf.writestr(f'picks_{evid}.csv', f.getvalue())


def _read_picks(event, fname):
    otime = _origin(event).time
    picks = []
    arrivals = []
    with _open(fname) as f:
        reader = csv.DictReader(f)
        for row in reader:
            phase = row['phase']
            wid = WaveformStreamID(seed_string=row['seedid'])
            pick = Pick(waveform_id=wid, phase_hint=phase,
                        time=otime + float(row['time']))
            arrival = Arrival(phase=phase, pick_id=pick.resource_id,
                              time_weight=float(row['weight']))
            picks.append(pick)
            arrivals.append(arrival)
    event.picks = picks
    event.origins[0].arrivals = arrivals


def _write_picks(event, fname, delimiter=','):
    fmtstr = delimiter.join(PFIELDS)
    fieldnames = [
        fn for _, fn, _, _ in Formatter().parse(fmtstr) if fn is not None]
    origin = _origin(event)
    weights = {str(arrival.pick_id): arrival.time_weight
               for arrival in origin.arrivals if arrival.time_weight}
    phases = {str(arrival.pick_id): arrival.phase
               for arrival in origin.arrivals if arrival.phase}
    with _open(fname, 'w') as f:
        f.write(delimiter.join(fieldnames) + '\n')
        for pick in event.picks:
            pick_id = str(pick.resource_id)
            d = {'time': pick.time - origin.time,
                 'seedid': pick.waveform_id.id,
                 'phase': phases.get(pick_id, pick.phase_hint),
                 'weight': weights.get(pick_id, 1.)}
            f.write(fmtstr.format(**d) + '\n')


def read_csv(fname, skipheader=0, depth_in_km=True, default=None,
             check_compression=None, **kwargs):
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
    with _open(fname) as f:
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
            try:
                # add zero to eliminate negative zeros in magnitudes
                mag = float(row['mag'])+0
                if math.isnan(mag):
                    raise
            except:
                magnitudes = []
            else:
                try:
                    magtype = row['magtype']
                except:
                    magtype = DEFAULT.get('magtype')
                else:
                    if magtype.lower() in ('none', 'null', 'nan'):
                        magtype = None
                magnitudes = [Magnitude(mag=mag, magnitude_type=magtype)]
            id_ = ResourceIdentifier(row['id'].strip()) if 'id' in row else None
            event = Event(magnitudes=magnitudes, origins=[origin], resource_id=id_)
            events.append(event)
    return Catalog(events=events)


def write_csv(events, fname, depth_in_km=True, delimiter=','):
    """
    Write ObsPy catalog to CSV file

    :param events: catalog or list of events
    :param fname: file name
    :param depth_in_km: write depth in units of kilometer (default: True) or meter
    :param delimiter: defaults to `','`
    """
    fmtstr = delimiter.join(FIELDS)
    fieldnames = [
        fn for _, fn, _, _ in Formatter().parse(fmtstr) if fn is not None]
    with _open(fname, 'w') as f:
        f.write(delimiter.join(fieldnames) + '\n')
        for event in events:
            evid = str(event.resource_id).split('/')[-1]
            try:
                origin = _origin(event)
            except:
                from warnings import warn
                warn(f'No origin found -> do not write event {evid}')
                continue
            try:
                magnitude = event.preferred_magnitude() or event.magnitudes[0]
            except:
                from warnings import warn
                warn(f'No magnitude found for event {evid}')
                mag = float('nan')
                magtype = None
            else:
                mag = magnitude.mag
                magtype = magnitude.magnitude_type
            d = {'time': origin.time,
                 'lat': origin.latitude,
                 'lon': origin.longitude,
                 'dep': origin.depth / (1000 if depth_in_km else 1),
                 'mag': mag,
                 'magtype': magtype,
                 'id': evid}
            f.write(fmtstr.format(**d) + '\n')
