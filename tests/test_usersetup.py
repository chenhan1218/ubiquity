
#!/usr/bin/python

import unittest
import mock
from test import test_support
from gi.repository import Gtk, GObject
import sys, os

os.environ['UBIQUITY_GLADE'] = 'gui/gtk'

class UserSetupTests(unittest.TestCase):
    def setUp(self):
        for obj in ('ubiquity.misc.execute',
                    'ubiquity.misc.execute_root',
                    'ubiquity.misc.dmimodel'):
            patcher = mock.patch(obj)
            patcher.start()
            self.addCleanup(patcher.stop)
        sys.path.insert(0, 'ubiquity/plugins')
        ubi_usersetup = __import__('ubi-usersetup')
        sys.path.pop()
        controller = mock.Mock()
        self.gtk = ubi_usersetup.PageGtk(controller)

    def test_hostname_check(self):
        self.gtk.hostname_ok.show()
        self.gtk.hostname.set_text('ahostnamethatdoesntexistonthenetwork')
        self.gtk.hostname_error = mock.Mock()
        self.gtk.hostname_timeout(self.gtk.hostname)
        GObject.timeout_add(1, Gtk.main_quit)
        Gtk.main()
        self.assertEqual(self.gtk.hostname_error.call_count, 0)

    def test_hostname_check_exists(self):
        import socket
        error_msg = 'That name already exists on the network.'
        self.gtk.hostname_ok.show()
        self.gtk.hostname.set_text(socket.gethostname())
        self.gtk.hostname_error = mock.Mock()
        self.gtk.hostname_timeout(self.gtk.hostname)
        GObject.timeout_add(1, Gtk.main_quit)
        Gtk.main()
        self.assertTrue(self.gtk.hostname_error.call_count > 0)
        self.gtk.hostname_error.assert_called_with(error_msg)
