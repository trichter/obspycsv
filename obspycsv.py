## Copyright 2022 Tom Eulenfeld, MIT license
"""
CSV or CSZ read/write support for ObsPy earthquake catalogs

You have to use the field names
time or year, mon, day, hour, minu, sec
lat, lon, dep, mag, magtype, id
(see global FIELDS variable)
"""
import csv
from contextlib import contextmanager
import io
import os.path
from string import Formatter

from obspy import UTCDateTime as UTC
from obspy.core.event import (
    Catalog, Event, Origin, Magnitude, Pick, WaveformStreamID, Arrival,
    ResourceIdentifier)


__version__ = '0.3.0'
DEFAULT = {'magtype': 'None'}
FIELDS = '{time!s:.22} {lat:.4f} {lon:.4f} {dep:.3f} {mag:.1f} {magtype} {id}'.split()
PFIELDS = '{seedid} {phase} {time:.5f} {weight:.3f}'.split()



def _is_csv(fname, **kwargs):
    try:
        read_csv(fname)
    except:
        return False
    return True


def _is_csz(fname, **kwargs):
    return os.path.exists(fname + 'ip')


def _evid(event):
    return str(event.resource_id).split('/')[-1]


@contextmanager
def _open(filein, *args, **kwargs):
    "Accept bot files or file names"""
    if isinstance(filein, str):  # filename
        with open(filein, *args, **kwargs) as f:
            yield f
    else:  # file-like object
        yield filein


def read_csz(fname, default=None):
    """
    Read a CSZ file and return ObsPy Catalog with picks

    :param default: dictionary with default values, at the moment only
         magtype is supported,
         i.e. to set magtypes use `default={'magtype': 'Ml'}`
    """
    import zipfile
    fname2 = fname + 'ip'
    if os.path.exists(fname2):
        fname = fname2
    with open(fname, 'rb') as fw:
        with zipfile.ZipFile(fw) as zipf:
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


def write_csz(events, fname, compress=False):
    """
    Write ObsPy catalog to CSZ file

    :param events: catalog or list of events
    :param fname: file name
    """
    import zipfile
    import io

    compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(fname + 'ip', mode='w', compression=compression) as zipf:
        with io.StringIO() as f:
            write_csv(events, f)
            zipf.writestr('events.csv', f.getvalue())
        for event in events:
            if len(event.picks) == 0:
                continue
            evid = str(event.resource_id).split('/')[-1]
            with io.StringIO() as f:
                _write_picks(event, f)
                zipf.writestr(f'picks_{evid}.csv', f.getvalue())
    with open(fname, 'w') as f:
        f.write('CSZ file\nThis dummy file is necessary, because ObsPy '
                'otherwise will automatically uncompress the cszip file.\n')


def _read_picks(event, fname):
    otime = event.origins[0].time
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
    origin = event.origins[0]
    weights = {str(arrival.pick_id): arrival.time_weight
               for arrival in origin.arrivals if arrival.time_weight}
    phases = {str(arrival.pick_id): arrival.phase
               for arrival in origin.arrivals if arrival.time_weight}
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
            try:
                ori = event.preferred_origin() or event.origins[0]
                mag = event.preferred_magnitude() or event.magnitudes[0]
            except:
                from warnings import warn
                eventstr = str(event).splitlines()[0]
                warn(f'Cannot write event, because no origin or no magnitude was found: {eventstr}')
                continue
            evid = str(event.resource_id).split('/')[-1]
            d = {'time': ori.time,
                 'lat': ori.latitude,
                 'lon': ori.longitude,
                 'dep': ori.depth / (1000 if depth_in_km else 1),
                 'mag': mag.mag,
                 'magtype': mag.magnitude_type,
                 'id': evid}
            f.write(fmtstr.format(**d) + '\n')
