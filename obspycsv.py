## Copyright 2022 Tom Eulenfeld, MIT license
"""
CSV and CSZ read/write support for ObsPy earthquake catalogs

You can use the following field names to read an external CSV file
time or year, mon, day, hour, minu, sec
lat, lon, dep, mag, magtype, id
(see also global FIELDS variable and help of read_csv)

Note: This plugin can be easily extended to write and read more event information.
If you are interested, please send a PR to the github repository.
  1. Add 'extended' or similar key to FIELDS dict, e.g. as a start use
      'extended': (
          '{time!s:.25} {lat:.6f} {lat_err:.6f} {lon:.6f} {lon_err:.6f} '
          '{dep:.3f} {dep_err:.3f} {mag:.2f} {mag_err:.2f} {magtype} {id}'
          )
     You can also test by just passing the string to `fields` option.
  2. Implement writing functionality in write_csv by adding the new properties
     to the dict d. Missing values have to be handled.
  3. Implement reading functionality for the new properties in read_csv.
  4. Write some tests testing all new properties. Check that an event with
     all new properties defined or missing can be written and read again.
Similar can be done for the picks using PFIELDS, _write_picks, _read_picks
"""

import csv
from contextlib import contextmanager
import io
import math
from string import Formatter
import zipfile

import numpy as np
from obspy import UTCDateTime as UTC
from obspy.core.event import (
    Catalog, Event, Origin, Magnitude, Pick, WaveformStreamID, Arrival,
    ResourceIdentifier)


__version__ = '0.7.0'

# for reading
DEFAULT = {'magtype': ''}
# for writing
FIELDS = {
    'basic': '{time!s:.25} {lat:.6f} {lon:.6f} {dep:.3f} {mag:.2f} {magtype} {id}'
    }
PFIELDS = {
    'basic': '{seedid} {phase} {time:.5f} {weight:.3f}'
    }
CSZ_COMMENT = f'CSZ format v{__version__} obspy_no_uncompress'.encode('utf-8')
# for load_csv
DTYPE = {
    'time': 'datetime64[ms]',
    'lat': float,
    'lon': float,
    'dep': float,
    'mag': float,
    'magtype': 'U10',
    'id': 'U50'
    }

#EventID | Time | Latitude | Longitude | Depth/km | Author | Catalog | Contributor | ContributorID | MagType | Magnitude | MagAuthor | EventLocationName
NAMES_EVENTTXT = 'id time lat lon dep _ _ _ _ magtype mag _ _'


def _is_csv(fname, **kwargs):
    try:
        return read_csv(fname, format_check=True)
    except:
        return False


def _is_eventtxt(fname, **kwargs):
    try:
        return read_eventtxt(fname, format_check=True)
    except:
        return False


def _is_csz(fname, **kwargs):
    try:
        assert zipfile.is_zipfile(fname)
        with zipfile.ZipFile(fname) as zipf:
            assert (zipf.comment.startswith(b'CSZ') and
                    zipf.comment.endswith(b'obspy_no_uncompress'))
        return True
    except:
        return False


def _evid(event):
    return str(event.resource_id).split('/')[-1]


def _origin(event):
    return event.preferred_origin() or event.origins[0]


@contextmanager
def _open(filein, *args, **kwargs):
    """Accept both files or file names"""
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
    :param check_compression: Has to be set to False, when using
        ObsPy's read_events() function, otherwise ObsPy will automatically
        unpack the zip file and reading it with obspycsv will not work.
        The option is not used by read_csz.
    """
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


def write_csz(events, fname, fields='basic', fields_picks='basic', **kwargs):
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
    if kwargs.get('compression') is True:  # allow True as value for compression
        kwargs['compression'] = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(fname, mode='w', **kwargs) as zipf:
        zipf.comment = CSZ_COMMENT
        with io.StringIO() as f:
            write_csv(events, f, fields=fields)
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
                _write_picks(event, f, fields_picks=fields_picks)
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


def _write_picks(event, fname, fields_picks='basic', delimiter=','):
    fields = PFIELDS.get(fields_picks, fields_picks)
    if ' ' in fields:
        fields = fields.split()
    fmtstr = delimiter.join(fields)
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


def _names_sequence(names):
    if isinstance(names, dict):
        names = [names.get(i, '_') for i in range(max(names.keys())+1)]
    elif ' ' in names:
        names = names.split()
    return names


def read_eventtxt(fname, default=None, format_check=False):
    return read_csv(fname,
                    skipheader=1, names=NAMES_EVENTTXT, delimiter='|',
                    default=default, format_check=format_check)


def read_csv(fname, skipheader=0, depth_in_km=True, default=None, names=None,
             check_compression=None, format_check=False,
             **kwargs):
    """
    Read a CSV file and return ObsPy Catalog

    :param skipheader: skip first rows of file
    :param depth_in_kim: depth is given in kilometer (default: True) or
        meter (False)
    :param default: dictionary with default values, at the moment only
         magtype is supported,
         i.e. to set magtypes use `default={'magtype': 'Ml'}`
    :param names: determined automatically from header line of file,
        otherwise can be specified as string, sequence or dict
    :param check_compression: not used by read_csv
    :param format_check: Read only the first event
    :param **kargs: all other kwargs are passed to csv.DictReader,
        important additional arguments are fieldnames, dialect, delimiter, etc

    You can read csv files created by this module or external csv files.
    Example reading an external csv file:

        from obspy import read_events
        names = 'year mon day hour minu sec _ lat lon dep _ _ mag _ _ _ _ _ _ id'
        catalog = read_events('external.csv', 'CSV', skipheader=1, names=names)
    """
    if default is None:
        default= DEFAULT
    events = []
    with _open(fname) as f:
        for _ in range(skipheader):
            f.readline()
        if names is not None:
            kwargs.setdefault('fieldnames', _names_sequence(names))
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
                    if magtype.lower() in ('', 'none', 'null', 'nan'):
                        raise
                except:
                    magtype = default.get('magtype')
                magnitudes = [Magnitude(mag=mag, magnitude_type=magtype)]
            id_ = ResourceIdentifier(row['id'].strip()) if 'id' in row else None
            event = Event(magnitudes=magnitudes, origins=[origin], resource_id=id_)
            events.append(event)
            if format_check:
                return True
    if format_check:
        # empty file will return an empty catalog, but it is not detected as CSV file
        return False
    return Catalog(events=events)


def write_csv_default(events, fname, fields='basic'):
    """
    Write ObsPy catalog to CSV file

    :param events: catalog or list of events
    :param fname: file name
    """
    return write_csv(events, fname, fields=fields)


def write_csv(events, fname, fields='basic', depth_in_km=True, delimiter=','):
    """
    Write ObsPy catalog to CSV file

    :param events: catalog or list of events
    :param fname: file name
    :param depth_in_km: write depth in units of kilometer (default: True) or meter
    :param delimiter: defaults to `','`
    """
    fields = FIELDS.get(fields, fields)
    if ' ' in fields:
        fields = fields.split()
    fmtstr = delimiter.join(fields)
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
                magtype = ''
            else:
                mag = magnitude.mag
                magtype = magnitude.magnitude_type or ''
            d = {'time': origin.time,
                 'lat': origin.latitude,
                 'lon': origin.longitude,
                 'dep': origin.depth / (1000 if depth_in_km else 1),
                 'mag': mag,
                 'magtype': magtype,
                 'id': evid}
            f.write(fmtstr.format(**d).replace('nan', '') + '\n')


def load_csv(fname, skipheader=0, only=None, names=None, **kw):
    """
    Load CSV or CSZ file into numpy array

    :param only: sequence, read only columns speified by name
    :param skipheader, names: see `read_csv`
    :param **kw: Other kwargs are passed to `np.loadtxt`

    """
    if isinstance(fname, str) and zipfile.is_zipfile(fname):
        with zipfile.ZipFile(fname) as zipf:
            with io.TextIOWrapper(
                    zipf.open('events.csv'), encoding='utf-8') as f:
                return load_csv(f)
    with _open(fname) as f:
        for _ in range(skipheader):
            f.readline()
        if names is None:
            names = f.readline().strip().split(',')
        names = _names_sequence(names)
        dtype = [(n, DTYPE[n]) for n in names if n in DTYPE and
                        (only is None or n in only)]
        usecols = [i for i, n in enumerate(names) if n in DTYPE and
                        (only is None or n in only)]
        kw.setdefault('usecols', usecols)
        kw.setdefault('dtype', dtype)
        kw.setdefault('delimiter', ',')
        return np.genfromtxt(f, **kw)


def events2array(events, **kw):
    """
    Convert ObsPy catalog to numpy array

    All kwargs are passed to `load_csv`, e.g. use `only=('lat', 'lon', 'mag')`
    to get an array with lat, lon, mag parameters.
    """
    with io.StringIO() as f:
        write_csv(events, f)
        f.seek(0)
        return load_csv(f, **kw)
