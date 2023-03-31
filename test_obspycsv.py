# Copyright 2022-2023 Tom Eulenfeld, MIT license

import io
import os.path
from tempfile import gettempdir

import numpy as np
import obspy
from obspy import read_events
from obspy.core.util import NamedTemporaryFile
import obspycsv
from packaging import version
import pytest


def test_csv():
    events = read_events()
    with NamedTemporaryFile(suffix='.csv') as ft:
        events.write(ft.name, 'CSV')
        events2 = read_events(ft.name)
    assert len(events2) == len(events)
    assert events2[0].origins[0].time == events[0].origins[0].time
    with NamedTemporaryFile(suffix='.csv') as ft:
        events.write(ft.name, 'CSV', depth_in_km=True)
        events2 = read_events(ft.name)
    assert len(events2) == len(events)
    assert events2[0].origins[0].time == events[0].origins[0].time


def test_csv_reading_external_catalog():
    external = (
        'Year, Month, Day, Hour, Minute, Seconds, code, Lat, Lon, Depth, '
        'Station_count, time_residual_RMS, Magnitude, etc\n'
        '2023, 05, 06, 19, 55, 01.3, LI, 10.1942, 124.8300, 50.47, 111, '
        '0.0, 0.2, 42, 0.0, 0.0176, 0.0127, 0.02, 0.3, 2023abcde'
        )
    fields = 'year mon day hour minu sec _ lat lon dep _ _ mag _ _ _ _ _ _ id'
    incomplete_fields = 'year mon day hour minu sec _ lat lon dep'
    with NamedTemporaryFile(suffix='.csv') as ft:
        with open(ft.name, 'w') as f:
            f.write(external)
        assert not obspycsv._is_csv(ft.name)
        events = read_events(ft.name, 'CSV', skipheader=1, names=fields)
        events2 = read_events(ft.name, 'CSV', skipheader=1,
                              names=incomplete_fields)
    assert len(events) == 1
    assert str(events[0].origins[0].time) == '2023-05-06T19:55:01.300000Z'
    assert len(events[0].magnitudes) == 1
    assert len(events2) == 1
    assert str(events2[0].origins[0].time) == '2023-05-06T19:55:01.300000Z'
    assert len(events2[0].magnitudes) == 0


def test_csv_incomplete_catalog():
    csv = """time,lat,lon,dep,mag,magtype,id
        2012-04-04,42,42,nan,null,,id1
        2012-04-04,42,42,,10,Munreal,id1"""
    events = read_events()
    del events[0].magnitudes[0].magnitude_type
    events[1].magnitudes = []
    events[1].preferred_magnitude_id = None
    events[1].origins[0].depth = None
    events[2].origins = []
    events[2].preferred_origin_id = None
    with NamedTemporaryFile(suffix='.csv') as ft:
        with pytest.warns(Warning):
            events.write(ft.name, 'CSV')
        events2 = read_events(ft.name, 'CSV')
    assert len(events2) == 2
    assert events2[0].origins[0].time == events[0].origins[0].time
    assert events2[1].origins[0].depth is None
    assert events2[1].origins[0].time == events[1].origins[0].time

    with NamedTemporaryFile(suffix='.txt') as ft:
        with open(ft.name, 'w') as f:
            f.write(csv)
        assert obspycsv._is_csv(ft.name)
        events = read_events(ft.name)
    assert len(events) == 2
    assert events[0].origins[0].depth is None
    assert len(events[0].magnitudes) == 0
    assert events[1].origins[0].depth is None
    assert len(events[1].magnitudes) == 1
    assert events[1].magnitudes[0].mag == 10.0


def test_csv_custom_fmt():
    events = read_events()
    with NamedTemporaryFile(suffix='.csv') as ft:
        fname = ft.name
        events.write(fname, 'CSV', fields='{lat:.5f} {lon:.5f}')
        assert not obspycsv._is_csv(fname)
        data = np.genfromtxt(fname, names=True, delimiter=',')
        assert len(data) == 3
        assert len(data[0]) == 2


def test_csv_empty():
    assert not obspycsv._is_csv(b'')
    empty_cat = obspycsv._read_csv(b'')
    assert len(empty_cat) == 0


def test_csz(check_compression=False):
    events = read_events('/path/to/example.pha')
    tempdir = gettempdir()
    fname = os.path.join(tempdir, 'obbspycsv_testfile.csz')
    with NamedTemporaryFile(suffix='.csz') as ft:
        fname = ft.name
        def _test_write_read(events, **kw):
            events.write(fname, 'CSZ', **kw)
            assert obspycsv._is_csz(fname)
            events2 = read_events(fname, check_compression=check_compression)
            assert len(events2) == len(events)
            for ev1, ev2 in zip(events, events2):
                assert len(ev2.origins[0].arrivals) == \
                                  len(ev1.origins[0].arrivals)
                assert len(ev2.picks) == \
                                 len(ev1.picks)
        _test_write_read(events)
        _test_write_read(events, compression=False)
        try:
            import zlib
        except ImportError:
            pass
        else:
            _test_write_read(events, compression=True, compresslevel=6)
        # test with missing origin and waveformid
        events[1].origins = []
        events[0].picks[0].waveform_id = None
        with pytest.warns(Warning):
            events.write(fname, 'CSZ')
        assert obspycsv._is_csz(fname)
        events2 = read_events(fname, check_compression=check_compression)
        assert len(events2) == 1
        assert (len(events2[0].origins[0].arrivals) ==
                len(events[0].origins[0].arrivals))
        assert len(events2[0].picks) == len(events[0].picks)


def test_csz_without_picks(check_compression=False):
    events = read_events()
    with NamedTemporaryFile(suffix='.csz') as ft:
        fname = ft.name
        events.write(fname, 'CSZ')
        assert obspycsv._is_csz(fname)
        events2 = read_events(fname, check_compression=check_compression)
        assert events2[0]._format == 'CSZ'
        assert len(events2) == len(events)


@pytest.mark.skipif(version.parse(obspy.__version__) < version.parse('1.4'),
                    reason='only supported for ObsPy>=1.4')
def test_csz_without_check_compression_parameters():
    test_csz(check_compression=True)
    test_csz_without_picks(check_compression=True)


def test_load_csv():
    events = read_events()
    with NamedTemporaryFile(suffix='.csv') as ft:
        events.write(ft.name, 'CSV')
        t = obspycsv.load_csv(ft.name)
    assert t['mag'][0] == 4.4
    with NamedTemporaryFile(suffix='.csz') as ft:
        events.write(ft.name, 'CSZ')
        t = obspycsv.load_csv(ft.name)
    assert t['mag'][0] == 4.4
    t = obspycsv._events2array(events)
    assert t['mag'][0] == 4.4


def test_load_csv_incomplete_catalog():
    events = read_events()
    del events[0].magnitudes[0].magnitude_type
    events[1].magnitudes = []
    events[1].preferred_magnitude_id = None
    events[2].origins = []
    events[2].preferred_origin_id = None
    with NamedTemporaryFile(suffix='.csv') as ft:
        with pytest.warns(Warning):
            events.write(ft.name, 'CSV')
        t = obspycsv.load_csv(ft.name)
    assert len(t) == 2
    assert np.isnan(t['mag'][1])


def test_load_csv_some_cols():
    events = read_events()
    with NamedTemporaryFile(suffix='.csv') as ft:
        fields = '{lat:.6f} {lon:.6f} {mag:.2f}'
        events.write(ft.name, 'CSV', fields=fields)
        t = obspycsv.load_csv(ft.name)
        t2 = obspycsv.load_csv(ft.name, only=['mag'])
        t3 = obspycsv.load_csv(ft.name, skipheader=1, names={2: 'mag'})
    assert t['mag'][0] == 4.4
    assert t2['mag'][0] == 4.4
    assert t3['mag'][0] == 4.4
    assert 'mag' in t2.dtype.names
    assert 'lat' not in t2.dtype.names
    assert 'mag' in t3.dtype.names
    assert 'lat' not in t3.dtype.names


def test_events2array():
    events = read_events()
    t = obspycsv._events2array(events)
    assert t['mag'][0] == 4.4


def test_eventtxt():
    eventtxt = (
        '#EventID | Time | Latitude | Longitude | Depth/km | '
        'Author | Catalog | Contributor | ContributorID | '
        'MagType | Magnitude | MagAuthor | EventLocationName\n'
        '3337497|2012-04-11T08:38:37.00000|2.237600|93.014400|26.300|'
        'ISC||ISC||MW|8.60|GCMT|SUMATRA\n'
        '2413|1960-05-22T19:11:14.00000|-38.170000|-72.570000|0.000|'
        '|||||8.50||\n')
    with NamedTemporaryFile(suffix='.txt') as ft:
        with open(ft.name, 'w') as f:
            f.write(eventtxt)
        assert obspycsv._is_eventtxt(ft.name)
        events = read_events(ft.name)
        arr = obspycsv.load_eventtxt(ft.name)
    assert len(events) == 2
    assert str(events[0].origins[0].time) == \
                     '2012-04-11T08:38:37.000000Z'
    assert events[0].origins[0].creation_info.author == 'ISC'
    assert events[0].magnitudes[0].creation_info.author == 'GCMT'
    assert events[0].event_descriptions[0].text == 'SUMATRA'
    assert len(events[0].magnitudes) == 1
    assert events[1].origins[0].creation_info == None
    assert events[1].magnitudes[0].creation_info == None
    assert list(arr['mag']) == [8.6, 8.5]
    with io.StringIO() as f:
        events.write(f, 'EVENTTXT')
        assert f.getvalue() == eventtxt
