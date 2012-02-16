#!/usr/bin/python
# -*- coding: utf8; -*-

import unittest

from gi.repository import UbiquityMockResolver
import mock

from ubiquity import gtkwidgets, plugin_manager


class UserSetupTests(unittest.TestCase):
    def setUp(self):
        for obj in ('ubiquity.misc.execute',
                    'ubiquity.misc.execute_root',
                    'ubiquity.misc.dmimodel'):
            patcher = mock.patch(obj)
            patcher.start()
            self.addCleanup(patcher.stop)
        ubi_usersetup = plugin_manager.load_plugin('ubi-usersetup')
        controller = mock.Mock()
        self.ubi_usersetup = ubi_usersetup
        self.gtk = self.ubi_usersetup.PageGtk(controller)

    def test_hostname_check(self):
        self.gtk.resolver = UbiquityMockResolver.MockResolver(
            hostname='myhostname')
        self.gtk.hostname_ok.show()
        self.gtk.hostname.set_text('ahostnamethatdoesntexistonthenetwork')
        self.gtk.hostname_error = mock.Mock()
        self.gtk.hostname_timeout(self.gtk.hostname)
        gtkwidgets.refresh()
        self.assertEqual(self.gtk.hostname_error.call_count, 0)

    def test_hostname_check_exists(self):
        error_msg = 'That name already exists on the network.'
        self.gtk.resolver = UbiquityMockResolver.MockResolver(
            hostname='myhostname')
        self.gtk.hostname_ok.show()
        self.gtk.hostname.set_text('myhostname')
        self.gtk.hostname_error = mock.Mock()
        self.gtk.hostname_timeout(self.gtk.hostname)
        gtkwidgets.refresh()
        self.assertTrue(self.gtk.hostname_error.call_count > 0)
        self.gtk.hostname_error.assert_called_with(error_msg)

    def test_check_hostname(self):
        self.assertEqual(self.ubi_usersetup.check_hostname('a' * 64),
            "Must be between 1 and 63 characters long.")
        self.assertEqual(self.ubi_usersetup.check_hostname('abc123$'),
            "May only contain letters, digits, hyphens, and dots.")
        self.assertEqual(self.ubi_usersetup.check_hostname('-abc123'),
            "May not start or end with a hyphen.")
        self.assertEqual(self.ubi_usersetup.check_hostname('abc123-'),
            "May not start or end with a hyphen.")
        self.assertEqual(self.ubi_usersetup.check_hostname('.abc123'),
            'May not start or end with a dot, or contain the sequence "..".')
        self.assertEqual(self.ubi_usersetup.check_hostname('abc123.'),
            'May not start or end with a dot, or contain the sequence "..".')
        self.assertEqual(self.ubi_usersetup.check_hostname('abc..123'),
            'May not start or end with a dot, or contain the sequence "..".')
        self.assertEqual(self.ubi_usersetup.check_hostname(
            '-abc..123$' + 'a' * 64),
            ('Must be between 1 and 63 characters long.\n'
            'May only contain letters, digits, hyphens, and dots.\n'
            'May not start or end with a hyphen.\n'
            'May not start or end with a dot, or contain the sequence "..".'))
        self.assertEqual(self.ubi_usersetup.check_hostname('abc123'), '')

    def test_check_username(self):
        self.assertEqual(self.ubi_usersetup.check_username('Evan'),
            "Must start with a lower-case letter.")
        self.assertEqual(self.ubi_usersetup.check_username('evan$'),
            ("May only contain lower-case letters, "
             "digits, hyphens, and underscores."))
        self.assertEqual(self.ubi_usersetup.check_username('evan'), '')

    def test_unicode(self):
        # i18n needs to be imported to register ascii_transliterate
        from ubiquity import i18n
        heart = u'♥'
        self.gtk.set_fullname(heart)
        self.gtk.set_username(heart)
        self.gtk.set_hostname(heart)
        # Shortcut initialization
        self.gtk.fullname.set_name('fullname')
        self.gtk.username.set_name('username')
        self.gtk.username_edited = False
        self.gtk.hostname_edited = False
        self.gtk.info_loop(self.gtk.fullname)
        self.gtk.info_loop(self.gtk.username)


    def test_on_authentication_toggled(self):
        self.gtk.login_encrypt.set_active(True)
        self.gtk.login_auto.set_active(True)
        self.gtk.on_authentication_toggled(self.gtk.login_auto)
        self.assertFalse(self.gtk.login_encrypt.get_active())

        self.gtk.login_auto.set_active(True)
        self.gtk.login_encrypt.set_active(True)
        self.gtk.on_authentication_toggled(self.gtk.login_encrypt)
        self.assertTrue(self.gtk.login_pass.get_active())
