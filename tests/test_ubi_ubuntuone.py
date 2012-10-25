#!/usr/bin/python3

from test.support import run_unittest
import unittest

import mock

from ubiquity import plugin_manager


ubi_ubuntuone = plugin_manager.load_plugin('ubi-ubuntuone')


class TestPageGtk(unittest.TestCase):

    def setUp(self):
        mock_controller = mock.Mock()
        self.page = ubi_ubuntuone.PageGtk(mock_controller, ui=mock.Mock())

    def test_ui_visible(self):
        self.page.plugin_get_current_page()
        self.assertTrue(self.page.entry_email.get_property("visible"))

    def test_have_ui(self):
        self.page.plugin_get_current_page()
        self.assertNotEqual(self.page.entry_email, None)


if __name__ == '__main__':
    # run tests in a sourcetree with:
    #   UBIQUITY_GLADE=./gui/gtk \
    #   UBIQUITY_PLUGIN_PATH=./ubiquity/plugins/ \
    #   PYTHONPATH=. python3 tests/test_ubi_ubuntuone.py
    run_unittest(TestPageGtk)

