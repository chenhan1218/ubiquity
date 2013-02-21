#!/usr/bin/python3

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
        self.assertTrue(self.page._verify_email_entry("mup.frb@example.com"))
        self.assertTrue(self.page._verify_email_entry("mup@example"))
        self.assertTrue(self.page._verify_email_entry("mup\@foo.com@example"))

    def test_verify_password_entry(self):
        self.assertFalse(self.page._verify_password_entry(""))
        self.assertTrue(self.page._verify_password_entry("xxx"))


class RegisterTestCase(BaseTestPageGtk):

    def test_allow_go_forward_not_without_any_password(self):
        self.page.entry_email.set_text("foo")
        self.page.controller.allow_go_forward.assert_called_with(False)

    def test_allow_go_foward_not_without_matching_password(self):
        self.page.entry_email.set_text("foo@bar.com")
        self.page.entry_new_password.set_text("pw")
        self.page.entry_new_password2.set_text("pwd")
        self.page.controller.allow_go_forward.assert_called_with(False)

    def test_allow_go_foward(self):
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


@mock.patch.object(Gtk, 'main')
class NextButtonActionTestCase(BaseTestPageGtk):

    def test_call_register(self, mock_gtk_main):
        self.page.entry_email.set_text("foo@bar.com")
        self.page.entry_new_password.set_text("pw")
        self.page.entry_new_password2.set_text("pw")
        self.page.notebook_main.set_current_page(ubi_ubuntuone.PAGE_REGISTER)

        with mock.patch.object(self.page,
                               'register_new_sso_account') as mock_register:
            self.page.plugin_on_next_clicked()
            mock_register.assert_called_once_with("foo@bar.com", "pw",
                                                  displayname=None)

    def test_call_login(self, mock_gtk_main):
        self.page.entry_existing_email.set_text("foo")
        self.page.entry_existing_password.set_text("pass")
        self.page.notebook_main.set_current_page(ubi_ubuntuone.PAGE_LOGIN)

        with mock.patch.object(self.page, 'login_to_sso') as mock_login:
            self.page.plugin_on_next_clicked()
            mock_login.assert_called_once_with("foo", "pass", "Ubuntu One")


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
