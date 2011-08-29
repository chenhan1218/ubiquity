# -*- coding: utf8; -*-
#!/usr/bin/python

import unittest
import mock
import sys, os
import debconf

os.environ['UBIQUITY_GLADE'] = 'gui/gtk'

class TimezoneTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, 'ubiquity/plugins')
        self.ubi_timezone = __import__('ubi-timezone')
        sys.path.pop()
        db = debconf.DebconfCommunicator('ubi-test', cloexec=True)
        self.addCleanup(db.shutdown)
        controller = mock.Mock()
        controller.dbfilter = self.ubi_timezone.Page(None, db=db)
        self.gtk = self.ubi_timezone.PageGtk(controller)

    @mock.patch('json.loads')
    @mock.patch('urllib2.build_opener')
    def test_city_entry(self, opener_mock, json_mock):
        json_mock.return_value = []
        self.gtk.set_timezone('America/New_York')
        self.gtk.city_entry.set_text('Eastern')
        self.gtk.changed(self.gtk.city_entry)
        m = self.gtk.city_entry.get_completion().get_model()
        results = []
        expected = (('Eastern', 'United States'), ('Eastern', 'Canada'))
        for x in m:
            results.append((x[0], x[2]))
        self.assertEqual(len(results), 2)
        self.assertEqual(set(results), set(expected))
        # unicode, LP: #831533
        self.gtk.city_entry.set_text(u'♥')
        self.gtk.changed(self.gtk.city_entry)
