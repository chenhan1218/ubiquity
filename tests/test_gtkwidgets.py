#!/usr/bin/python

import unittest
from ubiquity import segmented_bar, timezone_map, tz
from test import test_support
from gi.repository import Gtk, GObject
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
        GObject.timeout_add(500, Gtk.main_quit)
        Gtk.main()

    def test_timezone_map(self):
        tzdb = tz.Database()
        tzmap = timezone_map.TimezoneMap(tzdb, 'pixmaps/timezone')
        self.win.add(tzmap)
        tzmap.select_city('America/New_York')
        self.win.show_all()
        self.win.connect('destroy', Gtk.main_quit)
        GObject.timeout_add(500, Gtk.main_quit)
        Gtk.main()

udevinfo = """
UDEV_LOG=3
DEVPATH=/devices/pci0000:00/0000:00:1c.1/0000:03:00.0/net/wlan0
DEVTYPE=wlan
INTERFACE=wlan0
IFINDEX=3
SUBSYSTEM=net
ID_VENDOR_FROM_DATABASE=Intel Corporation
ID_MODEL_FROM_DATABASE=PRO/Wireless 3945ABG [Golan] Network Connection
ID_BUS=pci
ID_VENDOR_ID=0x8086
ID_MODEL_ID=0x4227
ID_MM_CANDIDATE=1
"""


from ubiquity import nm
import mock
import dbus
class NetworkManagerTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('ubiquity.nm.NetworkManager.start')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.model = Gtk.TreeStore(str, object, object)
        self.manager = nm.NetworkManager(self.model)

    def test_get_vendor_and_model_null(self):
        self.assertEqual(nm.get_vendor_and_model('bogus'), ('',''))

    @mock.patch('subprocess.Popen')
    def test_get_vendor_and_model(self, mock_subprocess):
        mock_subprocess.return_value.communicate.return_value = (udevinfo, None)
        self.assertEqual(nm.get_vendor_and_model('foobar'),
                         ('Intel Corporation',
                          'PRO/Wireless 3945ABG [Golan] Network Connection'))

    def test_decode_ssid(self):
        ssid = [dbus.Byte(85), dbus.Byte(98), dbus.Byte(117), dbus.Byte(110),
                dbus.Byte(116), dbus.Byte(117), dbus.Byte(45), dbus.Byte(66),
                dbus.Byte(97), dbus.Byte(116), dbus.Byte(116), dbus.Byte(101),
                dbus.Byte(114), dbus.Byte(115), dbus.Byte(101), dbus.Byte(97)]
        self.assertEqual(nm.decode_ssid(ssid), 'Ubuntu-Battersea')

    def test_ssid_in_model(self):
        iterator = self.model.append(None, ['/foo', 'Intel', 'Wireless'])
        for ssid in ('Orange', 'Apple', 'Grape'):
            self.model.append(iterator, [ssid, True, 0])
        self.assertIsNotNone(self.manager.ssid_in_model(iterator, 'Apple', True))
        self.assertIsNone(self.manager.ssid_in_model(iterator, 'Grape', False))

    def test_prune(self):
        iterator = self.model.append(None, ['/foo', 'Intel', 'Wireless'])
        fruits = ['Orange', 'Apple', 'Grape']
        for ssid in fruits:
            self.model.append(iterator, [ssid, True, 0])
        i = self.model.iter_children(iterator)
        self.manager.prune(i, fruits)
        ret = []
        while i:
            ret.append(self.model[i][0])
            i = self.model.iter_next(i)
        # There haven't been any changes in this update.
        self.assertListEqual(fruits, ret)
        # An AP that was present no longer is.
        fruits.pop()
        i = self.model.iter_children(iterator)
        self.manager.prune(i, fruits)
        ret = []
        while i:
            ret.append(self.model[i][0])
            i = self.model.iter_next(i)
        self.assertListEqual(fruits, ret)
        
if __name__ == '__main__':
    test_support.run_unittest(WidgetTests)
