# Copyright 2013-2016 Tom Eulenfeld, MIT license
import unittest

from obspy import read_events
from obspy.core.util import NamedTemporaryFile
import obspycsv


class CSVTestCase(unittest.TestCase):

    def test_io(self):
        events = read_events()
        with NamedTemporaryFile(suffix='.csv') as ft:
            events.write(ft.name, 'CSV')
            events2 = read_events(ft.name)
        self.assertEqual(len(events2), len(events))
        self.assertEqual(events2[0].origins[0].time,
                          events[0].origins[0].time)

    def test_reading_external_catalog(self):
        external = (
            "Year, Month, Day, Hour, Minute, Seconds, code, Lat, Lon, Depth, Station_count, time_residual_RMS, Magnitude, etc\n"
            "2023, 05, 06, 19, 55, 01.3, LI, 10.1942, 124.8300, 50.47, 111, 0.0, 0.2, 42, 0.0, 0.0176, 0.0127, 0.02, 0.3, 2023abcde"
            )
        fields = 'year mon day hour minu sec _ lat lon dep _ _ mag _ _ _ _ _ _ id'.split()
        with NamedTemporaryFile(suffix='.csv') as ft:
            with open(ft.name, 'w') as f:
                f.write(external)
            self.assertFalse(obspycsv._is_csv(ft.name))
            events = read_events(ft.name, 'CSV', skipheader=1, fieldnames=fields)
        self.assertEqual(len(events), 1)
        self.assertEqual(str(events[0].origins[0].time), '2023-05-06T19:55:01.300000Z')


def suite():
    return unittest.makeSuite(CSVTestCase, 'test')


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
