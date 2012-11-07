#!/usr/bin/python3

from test.support import run_unittest
import tempfile
import unittest

import mock
from gi.repository import Gtk

from ubiquity import plugin_manager


ubi_ubuntuone = plugin_manager.load_plugin('ubi-ubuntuone')


class TestPageGtk(unittest.TestCase):

    def setUp(self):
        mock_controller = mock.Mock()
        self.page = ubi_ubuntuone.PageGtk(mock_controller, ui=mock.Mock())

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
    
    def test_click_next(self):
        tmp_token = tempfile.NamedTemporaryFile()
        self.page.OAUTH_TOKEN_FILE = tmp_token.name
        self.page.plugin_on_next_clicked()
        self.assertEqual(self.page.notebook_main.get_current_page(),
                         ubi_ubuntuone.PAGE_SPINNER)
        with open(tmp_token.name, "r") as fp:
            self.assertEqual(fp.read(), '{"token": "none"}')


if __name__ == '__main__':
    # run tests in a sourcetree with:
    """
    UBIQUITY_GLADE=./gui/gtk \
    UBIQUITY_PLUGIN_PATH=./ubiquity/plugins/ \
    PYTHONPATH=. python3 tests/test_ubi_ubuntuone.py
    """
    run_unittest(TestPageGtk)
