# Copyright 2022 Tom Eulenfeld, MIT license
import os.path
from tempfile import gettempdir
import unittest

import numpy as np
import obspy
from obspy import read_events
from obspy.core.util import NamedTemporaryFile
import obspycsv
from packaging import version


class CSVCSZTestCase(unittest.TestCase):

    def test_csv(self):
        events = read_events()
        with NamedTemporaryFile(suffix='.csv') as ft:
            events.write(ft.name, 'CSV')
            events2 = read_events(ft.name)
        self.assertEqual(len(events2), len(events))
        self.assertEqual(events2[0].origins[0].time,
                          events[0].origins[0].time)

    def test_csv_reading_external_catalog(self):
        external = (
            'Year, Month, Day, Hour, Minute, Seconds, code, Lat, Lon, Depth, Station_count, time_residual_RMS, Magnitude, etc\n'
            '2023, 05, 06, 19, 55, 01.3, LI, 10.1942, 124.8300, 50.47, 111, 0.0, 0.2, 42, 0.0, 0.0176, 0.0127, 0.02, 0.3, 2023abcde'
            )
        fields = 'year mon day hour minu sec _ lat lon dep _ _ mag _ _ _ _ _ _ id'.split()
        incomplete_fields = 'year mon day hour minu sec _ lat lon dep'.split()
        with NamedTemporaryFile(suffix='.csv') as ft:
            with open(ft.name, 'w') as f:
                f.write(external)
            self.assertFalse(obspycsv._is_csv(ft.name))
            events = read_events(ft.name, 'CSV', skipheader=1, fieldnames=fields)
            events2 = read_events(ft.name, 'CSV', skipheader=1, fieldnames=incomplete_fields)
        self.assertEqual(len(events), 1)
        self.assertEqual(str(events[0].origins[0].time), '2023-05-06T19:55:01.300000Z')
        self.assertEqual(len(events[0].magnitudes), 1)
        self.assertEqual(len(events2), 1)
        self.assertEqual(str(events2[0].origins[0].time), '2023-05-06T19:55:01.300000Z')
        self.assertEqual(len(events2[0].magnitudes), 0)

    def test_csv_incomplete_catalog(self):
        events = read_events()
        del events[0].magnitudes[0].magnitude_type
        events[1].magnitudes = []
        events[1].preferred_magnitude_id = None
        events[2].origins = []
        events[2].preferred_origin_id = None
        with NamedTemporaryFile(suffix='.csv') as ft:
            with self.assertWarns(Warning):
                events.write(ft.name, 'CSV')
            events2 = read_events(ft.name, 'CSV')
        self.assertEqual(len(events2), 2)
        self.assertEqual(events2[0].origins[0].time,
                          events[0].origins[0].time)
        self.assertEqual(events2[1].origins[0].time,
                          events[1].origins[0].time)

    def test_csv_custom_fmt(self):
        events = read_events()
        with NamedTemporaryFile(suffix='.csv') as ft:
            fname = ft.name
            events.write(fname, 'CSV', fields='{lat:.5f} {lon:.5f}')
            self.assertFalse(obspycsv._is_csv(fname))
            data = np.genfromtxt(fname, names=True, delimiter=',')
            self.assertEqual(len(data), 3)
            self.assertEqual(len(data[0]), 2)

    def test_csv_empty(self):
        self.assertFalse(obspycsv._is_csv(b''))
        empty_cat = obspycsv.read_csv(b'')
        self.assertEqual(len(empty_cat), 0)

    def test_csz(self, check_compression=False):
        events = read_events('/path/to/example.pha')
        tempdir = gettempdir()
        fname = os.path.join(tempdir, 'obbspycsv_testfile.csz')
        with NamedTemporaryFile(suffix='.csz') as ft:
            fname = ft.name
            def _test_write_read(events, **kw):
                events.write(fname, 'CSZ', **kw)
                self.assertTrue(obspycsv._is_csz(fname))
                events2 = read_events(fname, check_compression=check_compression)
                self.assertEqual(len(events2), len(events))
                for ev1, ev2 in zip(events, events2):
                    self.assertEqual(len(ev2.origins[0].arrivals),
                                      len(ev1.origins[0].arrivals))
                    self.assertEqual(len(ev2.picks),
                                     len(ev1.picks))
            _test_write_read(events)
            _test_write_read(events, compression=False)
            try:
                import zlib
            except ImportError:
                pass
            else:
                _test_write_read(events, compression=True, compresslevel=6)
            # test with missing origin
            events[1].origins = []
            with self.assertWarns(Warning):
                events.write(fname, 'CSZ')
            self.assertTrue(obspycsv._is_csz(fname))
            events2 = read_events(fname, check_compression=check_compression)
            self.assertEqual(len(events2), 1)
            self.assertEqual(len(events2[0].origins[0].arrivals),
                             len(events[0].origins[0].arrivals))
            self.assertEqual(len(events2[0].picks),
                             len(events[0].picks))

    def test_csz_without_picks(self, check_compression=False):
        events = read_events()
        with NamedTemporaryFile(suffix='.csz') as ft:
            fname = ft.name
            events.write(fname, 'CSZ')
            self.assertTrue(obspycsv._is_csz(fname))
            events2 = read_events(fname, check_compression=check_compression)
            self.assertEqual(events2[0]._format, 'CSZ')
            self.assertEqual(len(events2), len(events))

    @unittest.skipIf(version.parse(obspy.__version__) < version.parse('1.4'),
                     'only supported for ObsPy>=1.4')
    def test_csz_without_check_compression_parameters(self):
        self.test_csz(check_compression=True)
        self.test_csz_without_picks(check_compression=True)

    def test_load_csv(self):
        events = read_events()
        with NamedTemporaryFile(suffix='.csv') as ft:
            events.write(ft.name, 'CSV')
            t = obspycsv.load_csv(ft.name)
        self.assertEqual(t['mag'][0], 4.4)
        with NamedTemporaryFile(suffix='.csz') as ft:
            events.write(ft.name, 'CSZ')
            t = obspycsv.load_csv(ft.name)
        self.assertEqual(t['mag'][0], 4.4)
        t = obspycsv.events2array(events)
        self.assertEqual(t['mag'][0], 4.4)

    def test_load_csv_incomplete_catalog(self):
        events = read_events()
        del events[0].magnitudes[0].magnitude_type
        events[1].magnitudes = []
        events[1].preferred_magnitude_id = None
        events[2].origins = []
        events[2].preferred_origin_id = None
        with NamedTemporaryFile(suffix='.csv') as ft:
            with self.assertWarns(Warning):
                events.write(ft.name, 'CSV')
            t = obspycsv.load_csv(ft.name)
        self.assertEqual(len(t), 2)
        self.assertTrue(np.isnan(t['mag'][1]))

    def test_load_csv_some_cols(self):
        events = read_events()
        with NamedTemporaryFile(suffix='.csv') as ft:
            fields = '{lat:.6f} {lon:.6f} {mag:.2f}'
            events.write(ft.name, 'CSV', fields=fields)
            t = obspycsv.load_csv(ft.name)
        self.assertEqual(t['mag'][0], 4.4)

    def test_events2array(self):
        events = read_events()
        t = obspycsv.events2array(events)
        self.assertEqual(t['mag'][0], 4.4)


def suite():
    return unittest.makeSuite(CSVCSZTestCase, 'test')


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
