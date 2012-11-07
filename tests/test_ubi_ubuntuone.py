#!/usr/bin/python3

from test.support import run_unittest
import tempfile
import unittest

import mock
from gi.repository import Gtk, GObject

from ubiquity import plugin_manager


ubi_ubuntuone = plugin_manager.load_plugin('ubi-ubuntuone')


class BaseTestPageGtk(unittest.TestCase):
    
    def setUp(self):
        mock_controller = mock.Mock()
        self.page = ubi_ubuntuone.PageGtk(mock_controller, ui=mock.Mock())
    
class TestPageGtk(BaseTestPageGtk):

    def test_ui_visible(self):
        self.page.plugin_get_current_page()
        self.assertTrue(self.page.entry_email.get_property("visible"))

    def test_init_ui(self):
        self.page.plugin_get_current_page()
        self.assertEqual(
            self.page.notebook_main.get_current_page(), 
            ubi_ubuntuone.PAGE_REGISTER)
    
    def test_switch_pages(self):
        self.page.plugin_get_current_page()
        self.page.button_have_account.clicked()
        self.assertEqual(
            self.page.notebook_main.get_current_page(),
            ubi_ubuntuone.PAGE_LOGIN)
        self.page.button_need_account.clicked()
        self.assertEqual(
            self.page.notebook_main.get_current_page(),
            ubi_ubuntuone.PAGE_REGISTER)
    
    def test_verify_email_entry(self):
        self.assertFalse(self.page._verify_email_entry("meep"))
        self.assertTrue(self.page._verify_email_entry("mup@example.com"))
    
    def test_verify_password_entry(self):
        self.assertFalse(self.page._verify_password_entry(""))
        self.assertTrue(self.page._verify_password_entry("xxx"))


class MockSSOTestCase(BaseTestPageGtk):

    class MockUbuntuSSO():
        def mock_done(self, callback, errback):
            callback({'token': 'nonex'})
            Gtk.main_quit()
        def register(self, email, passw, callback, errback):
            GObject.idle_add(self.mock_done, callback, errback)
        def login(self, email, passw, callback, errback):
            GObject.idle_add(self.mock_done, callback, errback)

    def test_click_next(self):
        self.page.ubuntu_sso = self.MockUbuntuSSO()
        tmp_token = tempfile.NamedTemporaryFile()
        self.page.OAUTH_TOKEN_FILE = tmp_token.name
        self.page.plugin_on_next_clicked()
        self.assertEqual(self.page.notebook_main.get_current_page(),
                         ubi_ubuntuone.PAGE_SPINNER)
        with open(tmp_token.name, "r") as fp:
            self.assertEqual(fp.read(), '{"token": "nonex"}')


class RegisterTestCase(BaseTestPageGtk):

    def test_register_allow_go_forward_not_yet(self):
        self.page.entry_email.set_text("foo")
        self.page.controller.allow_go_forward.assert_called_with(False)

    def test_register_allow_go_foward(self):
        self.page.entry_email.set_text("foo@bar.com")
        self.page.controller.allow_go_forward.assert_called_with(True)


class LoginTestCase(BaseTestPageGtk):

    def test_login_allow_go_forward_not_yet(self):
        self.page.entry_existing_email.set_text("foo")
        self.page.entry_existing_password.set_text("pass")
        self.page.controller.allow_go_forward.assert_called_with(False)

    def test_login_allow_go_foward(self):
        self.page.button_have_account.clicked()
        self.page.entry_existing_email.set_text("foo@bar.com")
        self.page.entry_existing_password.set_text("pass")
        self.page.controller.allow_go_forward.assert_called_with(True)


if __name__ == '__main__':
    # run tests in a sourcetree with:
    """
    UBIQUITY_GLADE=./gui/gtk \
    UBIQUITY_PLUGIN_PATH=./ubiquity/plugins/ \
    PYTHONPATH=. python3 tests/test_ubi_ubuntuone.py
    """
    unittest.main()
