#!/usr/bin/python3

import http.client
import json
import unittest

from mock import call, DEFAULT, Mock, patch, PropertyMock, sentinel
from gi.repository import Gtk

from ubiquity import plugin_manager


ubi_ubuntuone = plugin_manager.load_plugin('ubi-ubuntuone')


class BaseTestPageGtk(unittest.TestCase):

    def setUp(self):
        mock_controller = Mock()
        self.page = ubi_ubuntuone.PageGtk(mock_controller, ui=Mock())


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


@patch.object(Gtk, 'main')
class NextButtonActionTestCase(BaseTestPageGtk):

    def test_call_register(self, mock_gtk_main):
        self.page.entry_email.set_text("foo@bar.com")
        self.page.entry_new_password.set_text("pw")
        self.page.entry_new_password2.set_text("pw")
        self.page.notebook_main.set_current_page(ubi_ubuntuone.PAGE_REGISTER)

        with patch.object(self.page,
                          'register_new_sso_account') as mock_register:
            self.page.plugin_on_next_clicked()
            mock_register.assert_called_once_with("foo@bar.com", "pw",
                                                  displayname=None)

    def test_call_login(self, mock_gtk_main):
        self.page.entry_existing_email.set_text("foo")
        self.page.entry_existing_password.set_text("pass")
        self.page.notebook_main.set_current_page(ubi_ubuntuone.PAGE_LOGIN)

        with patch.object(self.page, 'login_to_sso') as mock_login:
            self.page.plugin_on_next_clicked()
            mock_login.assert_called_once_with("foo", "pass", "Ubuntu One")


@patch('syslog.syslog')
@patch.object(Gtk, 'main')
class SSOAPITestCase(BaseTestPageGtk):

    def _call_handle_soup_message_done(self, status,
                                       response_body, from_page):
        mock_session = Mock()
        mock_msg = Mock()
        cfgstr = ('response_body.flatten.return_value'
                  '.get_data.return_value.decode.return_value')
        cfg = {cfgstr: response_body}
        mock_msg.configure_mock(**cfg)
        mock_status_code = PropertyMock(return_value=status)
        type(mock_msg).status_code = mock_status_code

        self.page._handle_soup_message_done(mock_session, mock_msg, from_page)
        self.assertEqual(self.page.notebook_main.get_current_page(),
                         from_page)

    def test_handle_done_OK(self, mock_gtk_main, mock_syslog):
        expected_body = "TESTBODY"
        self._call_handle_soup_message_done(http.client.OK,
                                            expected_body,
                                            ubi_ubuntuone.PAGE_REGISTER)
        self.assertEqual(self.page.oauth_token,
                         expected_body)

    def test_handle_done_CREATED(self, mock_gtk_main, mock_syslog):
        expected_body = "TESTBODY"
        self._call_handle_soup_message_done(http.client.CREATED,
                                            expected_body,
                                            ubi_ubuntuone.PAGE_REGISTER)
        self.assertEqual(self.page.oauth_token,
                         expected_body)

    def test_handle_done_error(self, mock_gtk_main, mock_syslog):
        expected_body = json.dumps({"message": "tstmsg"})
        # GONE or anything other than OK/CREATED:
        self._call_handle_soup_message_done(http.client.GONE,
                                            expected_body,
                                            ubi_ubuntuone.PAGE_REGISTER)
        self.assertEqual(self.page.oauth_token, None)
        self.assertEqual(self.page.label_global_error.get_text(),
                         "tstmsg")

    @patch('json.dumps')
    def test_login_to_sso(self, mock_json_dumps, mock_gtk_main, mock_syslog):
        email = 'email'
        password = 'pass'
        token_name = 'tok'
        service_url = 'url/'
        json_ct = 'application/json'
        expected_dict = dict(email=email,
                             password=password,
                             token_name=token_name)
        # NOTE: in order to avoid failing tests when dict key ordering
        # changes, we pass the actual dict by mocking json.dumps. This
        # way we can compare the dicts instead of their
        # serializations.
        mock_json_dumps.return_value = expected_dict
        with patch.multiple(self.page, soup=DEFAULT, session=DEFAULT) as mocks:
            typeobj = type(mocks['soup'].MemoryUse)
            typeobj.COPY = PropertyMock(return_value=sentinel.COPY)
            self.page.login_to_sso(email, password, token_name, service_url)
            expected = [call.Message.new("POST", 'url/tokens'),
                        call.Message.new().set_request(json_ct,
                                                       sentinel.COPY,
                                                       expected_dict,
                                                       len(expected_dict)),
                        call.Message.new().request_headers.append('Accept',
                                                                  json_ct)]
            self.assertEqual(mocks['soup'].mock_calls,
                             expected)

    @patch('json.dumps')
    def test_register_new_sso_account(self, mock_json_dumps, mock_gtk_main,
                                      mock_syslog):
        email = 'email'
        password = 'pass'
        service_url = 'url/'
        displayname = 'mr tester'
        json_ct = 'application/json'
        expected_dict = dict(email=email,
                             displayname=displayname,
                             password=password)

        # See test_login_to_sso for comment about patching json.dumps():
        mock_json_dumps.return_value = expected_dict
        with patch.multiple(self.page, soup=DEFAULT, session=DEFAULT) as mocks:
            typeobj = type(mocks['soup'].MemoryUse)
            typeobj.COPY = PropertyMock(return_value=sentinel.COPY)
            self.page.register_new_sso_account(email, password,
                                               displayname, service_url)
            expected = [call.Message.new("POST", 'url/accounts'),
                        call.Message.new().set_request(json_ct,
                                                       sentinel.COPY,
                                                       expected_dict,
                                                       len(expected_dict)),
                        call.Message.new().request_headers.append('Accept',
                                                                  json_ct)]
            self.assertEqual(mocks['soup'].mock_calls,
                             expected)


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
