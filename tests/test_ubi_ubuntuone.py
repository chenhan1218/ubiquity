#!/usr/bin/python3

import tempfile
import unittest

import mock
from gi.repository import Gtk, GObject, GLib

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
        self.page.linkbutton_have_account.clicked()
        self.assertEqual(
            self.page.notebook_main.get_current_page(),
            ubi_ubuntuone.PAGE_LOGIN)
        self.page.linkbutton_need_account.clicked()
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

        TOKEN = "{'token': 'nonex'}"

        def mock_done(self, callback, errback, data):
            callback(self.TOKEN, data)
            Gtk.main_quit()
        def register(self, email, passw, callback, errback, data):
            GObject.idle_add(self.mock_done, callback, errback, data)
        def login(self, email, passw, callback, errback, data):
            GObject.idle_add(self.mock_done, callback, errback, data)

    def test_click_next(self):
        self.page.ubuntu_sso = self.MockUbuntuSSO()
        with mock.patch.object(
            self.page, "_create_keyring_and_store_u1_token") as m_create:
            self.page.plugin_on_next_clicked()
            self.assertEqual(self.page.notebook_main.get_current_page(),
                             ubi_ubuntuone.PAGE_SPINNER)
            m_create.assert_called_with(self.page.ubuntu_sso.TOKEN)


class RegisterTestCase(BaseTestPageGtk):

    def test_register_allow_go_forward_not_yet(self):
        self.page.entry_email.set_text("foo")
        self.page.controller.allow_go_forward.assert_called_with(False)

    def test_register_allow_go_foward(self):
        self.page.entry_email.set_text("foo@bar.com")
        self.page.entry_new_password.set_text("pw")
        self.page.entry_new_password2.set_text("pw")
        self.page.controller.allow_go_forward.assert_called_with(True)


class LoginTestCase(BaseTestPageGtk):

    def test_login_allow_go_forward_not_yet(self):
        self.page.entry_existing_email.set_text("foo")
        self.page.entry_existing_password.set_text("pass")
        self.page.controller.allow_go_forward.assert_called_with(False)

    def test_login_allow_go_foward(self):
        self.page.linkbutton_have_account.clicked()
        self.page.entry_existing_email.set_text("foo@bar.com")
        self.page.entry_existing_password.set_text("pass")
        self.page.controller.allow_go_forward.assert_called_with(True)


class UbuntuSSOHelperTestCase(unittest.TestCase):
    
    def setUp(self):
        self.callback = mock.Mock()
        self.callback.side_effect = lambda *args: self.loop.quit()
        self.errback = mock.Mock()
        self.errback.side_effect = lambda *args: self.loop.quit()
        self.loop = GLib.MainLoop(GLib.main_context_default())
        self.sso_helper = ubi_ubuntuone.UbuntuSSO()

    def test_spawning_error(self):
        self.sso_helper.login("foo@example.com", "nopass",
                              self.callback, self.errback)
        self.loop.run()
        self.assertTrue(self.errback.called)
        self.assertFalse(self.callback.called)

    def test_spawning_success(self):
        self.sso_helper.BINARY = "/bin/echo"
        self.sso_helper.login("foo@example.com", "nopass",
                              self.callback, self.errback, data="data")
        self.loop.run()
        self.assertFalse(self.errback.called)
        self.assertTrue(self.callback.called)
        # ensure stdout is captured and data is also send
        self.callback.assert_called_with("--login foo@example.com\n", "data")


if __name__ == '__main__':
    # run tests in a sourcetree with:
    """
    UBIQUITY_GLADE=./gui/gtk \
    UBIQUITY_PLUGIN_PATH=./ubiquity/plugins/ \
    PYTHONPATH=. python3 tests/test_ubi_ubuntuone.py
    """
    #from test.support import run_unittest
    # run_unittest()
    unittest.main()
