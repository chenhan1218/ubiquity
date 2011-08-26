# -*- coding: utf-8; -*-
#!/usr/bin/python

import os
os.environ['UBIQUITY_PLUGIN_PATH'] = 'ubiquity/plugins'
os.environ['UBIQUITY_GLADE'] = 'gui/gtk'

import unittest
from ubiquity.frontend import gtk_ui
import mock

from gi.repository import Gtk
class TestFrontend(unittest.TestCase):
    @mock.patch('ubiquity.misc.drop_privileges')
    @mock.patch('ubiquity.misc.regain_privileges')
    @mock.patch('ubiquity.misc.execute')
    @mock.patch('ubiquity.frontend.gtk_ui.Wizard.customize_installer')
    def test_question_dialog(self, *args):
        ui = gtk_ui.Wizard('test-ubiquity')
        with mock.patch('gi.repository.Gtk.Dialog.run') as run:
            run.return_value = 0
            ret = ui.question_dialog(title=u'♥', msg=u'♥',
                                     options=(u'♥', u'£'))
            self.assertEqual(ret, u'£')
            run.return_value = 1
            ret = ui.question_dialog(title=u'♥', msg=u'♥',
                                     options=(u'♥', u'£'))
            self.assertEqual(ret, u'♥')
