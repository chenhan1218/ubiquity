#!/usr/bin/python

import unittest
from ubiquity import gtkwidgets, segmented_bar, timezone_map, tz
from test import test_support
from gi.repository import Gtk
import sys

class WidgetTests(unittest.TestCase):
    def setUp(self):
        self.err = None
        def excepthook(exctype, value, tb):
            Gtk.main_quit()
            self.err = exctype, tb
        sys.excepthook = excepthook
        self.win = Gtk.Window()

    def tearDown(self):
        self.win.hide()
        if self.err:
            raise self.err[0], None, self.err[1]

    def test_segmented_bar(self):
        sb = segmented_bar.SegmentedBar()
        self.win.add(sb)
        sb.add_segment_rgb('Test One', 30 * 1000 * 1000 * 1000, 'ff00ff')
        sb.add_segment_rgb('Test Two', 30 * 1000 * 1000 * 1000, '0000ff')
        for segment in sb.segments:
            self.assertEqual(segment.subtitle, '30.0 GB')
        self.assertEqual(sb.segments[0].title, 'Test One')
        self.assertEqual(sb.segments[1].title, 'Test Two')
        sb.remove_all()
        self.assertEqual(sb.segments, [])
        self.win.show_all()
        # TODO delete me
        #self.win.connect('destroy', Gtk.main_quit)
        #Gtk.main()

    def test_timezone_map(self):
        tzdb = tz.Database()
        tzmap = timezone_map.TimezoneMap(tzdb, 'pixmaps/timezone')
        self.win.add(tzmap)
        self.win.show_all()
        Gtk.main()
        
        
if __name__ == '__main__':
    test_support.run_unittest(WidgetTests)
