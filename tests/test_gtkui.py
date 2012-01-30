#!/usr/bin/python
# -*- coding: utf-8; -*-

import os
os.environ['UBIQUITY_PLUGIN_PATH'] = 'ubiquity/plugins'
os.environ['UBIQUITY_GLADE'] = 'gui/gtk'

import unittest
import mock

class TestFrontend(unittest.TestCase):
    def setUp(self):
        for obj in ('ubiquity.misc.drop_privileges',
                    'ubiquity.misc.regain_privileges',
                    'ubiquity.misc.execute',
                    'ubiquity.frontend.base.drop_privileges',
                    'ubiquity.frontend.gtk_ui.Wizard.customize_installer',
                    'ubiquity.nm.wireless_hardware_present',
                    'ubiquity.nm.NetworkManager.start',
                    'ubiquity.nm.NetworkManager.get_state',
                    'ubiquity.misc.add_connection_watch',
                    'ubiquity.misc.has_connection',
                    'ubiquity.upower.setup_power_watch',
                    'dbus.mainloop.glib.DBusGMainLoop',
                    'gi.repository.UbiquityWebcam.Webcam.available'):
            patcher = mock.patch(obj)
            patcher.start()
            self.addCleanup(patcher.stop)
            if obj in ('ubiquity.misc.wireless_hardware_present',
                       'ubiquity.misc.has_connection'):
                patcher.return_value = False
            elif obj == 'gi.repository.UbiquityWebcam.Webcam.available':
                patcher.return_value = True

    def test_question_dialog(self):
        from ubiquity.frontend import gtk_ui
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

    def test_pages_fit_on_a_netbook(self):
        from gi.repository import Gtk, GObject
        from ubiquity.frontend import gtk_ui
        ui = gtk_ui.Wizard('test-ubiquity')
        ui.translate_pages()
        for page in ui.pages:
            ui.set_page(page.module.NAME)
            GObject.timeout_add(250, Gtk.main_quit)
            Gtk.main()
            alloc = ui.live_installer.get_allocation()
            self.assertLessEqual(alloc.width, 640)
            self.assertLessEqual(alloc.height, 500)

    def test_interface_translated(self):
        import subprocess
        from ubiquity.frontend import gtk_ui
        from gi.repository import Gtk
        ui = gtk_ui.Wizard('test-ubiquity')
        missing_translations = []
        with mock.patch_object(ui, 'translate_widget') as translate_widget:
            def side_effect(widget, lang=None, prefix=None):
                label  = isinstance(widget, Gtk.Label)
                button = isinstance(widget, Gtk.Button)
                # We have some checkbuttons without labels.
                button = button and widget.get_label()
                # Stock buttons.
                button = button and not widget.get_use_stock()
                window = isinstance(widget, Gtk.Window)
                if not (label or button or window):
                    return
                name = widget.get_name()
                if not ui.get_string(name, lang, prefix):
                    missing_translations.append(name)
            translate_widget.side_effect = side_effect
            ui.translate_widgets()
            whitelist = [
                # These are calculated and set as the partitioning options are
                # being calculated.
                'reuse_partition_desc', 'reuse_partition_title',
                'replace_partition_desc', 'replace_partition_title',
                'resize_use_free_desc', 'resize_use_free_title',
                'use_device_desc', 'use_device_title', 'part_ask_heading',
                # Pulled straight from debconf when the installation medium is
                # already mounted.
                'part_advanced_warning_message',
                # These are calculated and set inside info_loop in the user
                # setup page.
                'password_strength', 'hostname_error_label',
                'password_error_label', 'username_error_label',
                # Pulled straight from debconf into the UI on progress.
                'install_progress_text',
                # Contains just the traceback.
                'crash_detail_label',
                # Pages define a debconf template to look up and use as the
                # title. If it is not set or not found, the title is hidden.
                'page_title',
                ]
            deb_host_arch = subprocess.Popen(
                ['dpkg-architecture', '-qDEB_HOST_ARCH'],
                stdout=subprocess.PIPE).communicate()[0].strip()
            if deb_host_arch not in ('amd64', 'i386'):
                # grub-installer not available, but this template won't be
                # displayed anyway.
                whitelist.append('grub_device_label')
            missing_translations = set(missing_translations) - set(whitelist)
            missing_translations = list(missing_translations)
            if missing_translations:
                missing_translations = ', '.join(missing_translations)
                raise Exception('Missing translation for:\n%s'
                                % missing_translations)
