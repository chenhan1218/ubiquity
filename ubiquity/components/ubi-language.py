# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-

# Copyright (C) 2006, 2007, 2008 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import debconf

from ubiquity.plugin import *
from ubiquity import i18n
from ubiquity import misc
from ubiquity import auto_update
from ubiquity import osextras

NAME = 'language'
AFTER = None
WEIGHT = 10

_release_notes_url_path = '/cdrom/.disk/release_notes_url'

class PageBase(PluginUI):
    def set_language_choices(self, unused_choices, choice_map):
        """Called with language choices and a map to localised names."""
        self.language_choice_map = dict(choice_map)

    def set_language(self, language):
        """Set the current selected language."""
        pass

    def get_language(self):
        """Get the current selected language."""
        return 'C'

    def set_oem_id(self, text):
        pass

    def get_oem_id(self):
        return ''

class PageGtk(PageBase):
    plugin_is_language = True

    def __init__(self, controller, *args, **kwargs):
        self.controller = controller
        if self.controller.oem_user_config:
            ui_file = 'stepLanguageOnly.ui'
            self.only = True
        else:
            ui_file = 'stepLanguage.ui'
            self.only = False
        try:
            import gtk
            builder = gtk.Builder()
            builder.add_from_file('/usr/share/ubiquity/gtk/%s' % ui_file)
            builder.connect_signals(self)
            self.controller.add_builder(builder)
            self.page = builder.get_object('stepLanguage')
            self.iconview = builder.get_object('language_iconview')
            self.treeview = builder.get_object('language_treeview')
            self.oem_id_entry = builder.get_object('oem_id_entry')

            if self.controller.oem_config:
                builder.get_object('oem_id_vbox').show()

            if self.controller.oem_config or auto_update.already_updated():
                update_this_installer = builder.get_object(
                    'update_this_installer')
                if update_this_installer:
                    update_this_installer.hide()

            release_notes_vbox = builder.get_object('release_notes_vbox')
            if release_notes_vbox:
                try:
                    release_notes_url = builder.get_object('release_notes_url')
                    release_notes = open(_release_notes_url_path)
                    release_notes_url.set_uri(
                        release_notes.read().rstrip('\n'))
                    release_notes.close()
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    release_notes_vbox.hide()
        except Exception, e:
            self.debug('Could not create language page: %s', e)
            self.page = None
        self.plugin_widgets = self.page

    def set_language_choices(self, choices, choice_map):
        import gtk, gobject
        PageBase.set_language_choices(self, choices, choice_map)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        for choice in choices:
            list_store.append([choice])
        # Support both iconview and treeview
        if self.only:
            self.iconview.set_model(list_store)
            self.iconview.set_text_column(0)
            lang_per_column = self.iconview.get_allocation().height / 40
            columns = int(round(len(choices) / float(lang_per_column)))
            self.iconview.set_columns(columns)
        else:
            if len(self.treeview.get_columns()) < 1:
                column = gtk.TreeViewColumn(None, gtk.CellRendererText(), text=0)
                column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
                self.treeview.append_column(column)
                selection = self.treeview.get_selection()
                selection.connect('changed',
                                    self.on_language_selection_changed)
            self.treeview.set_model(list_store)

    def set_language(self, language):
        # Support both iconview and treeview
        if self.only:
            model = self.iconview.get_model()
            iterator = model.iter_children(None)
            while iterator is not None:
                if unicode(model.get_value(iterator, 0)) == language:
                    path = model.get_path(iterator)
                    self.iconview.select_path(path)
                    self.iconview.scroll_to_path(path, True, 0.5, 0.5)
                    break
                iterator = model.iter_next(iterator)
        else:
            model = self.treeview.get_model()
            iterator = model.iter_children(None)
            while iterator is not None:
                if unicode(model.get_value(iterator, 0)) == language:
                    path = model.get_path(iterator)
                    self.treeview.get_selection().select_path(path)
                    self.treeview.scroll_to_cell(
                        path, use_align=True, row_align=0.5)
                    break
                iterator = model.iter_next(iterator)

    def get_language(self):
        # Support both iconview and treeview
        if self.only:
            model = self.iconview.get_model()
            items = self.iconview.get_selected_items()
            if not items:
                return 'C'
            iterator = model.get_iter(items[0])
        else:
            selection = self.treeview.get_selection()
            (model, iterator) = selection.get_selected()
        if iterator is None:
            return 'C'
        else:
            value = unicode(model.get_value(iterator, 0))
            return self.language_choice_map[value][1]

    def on_language_activated(self, *args, **kwargs):
        self.controller.go_forward()

    def on_language_selection_changed(self, *args, **kwargs):
        lang = self.get_language()
        if lang:
            # strip encoding; we use UTF-8 internally no matter what
            lang = lang.split('.')[0].lower()
            self.controller.translate(lang)
            import gtk
            ltr = i18n.get_string('default-ltr', lang, 'ubiquity/imported')
            if ltr == 'default:RTL':
                gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)
            else:
                gtk.widget_set_default_direction(gtk.TEXT_DIR_LTR)

    def set_oem_id(self, text):
        return self.oem_id_entry.set_text(text)

    def get_oem_id(self):
        return self.oem_id_entry.get_text()

    def on_update_this_installer(self, widget):
        if not auto_update.update(self.controller._wizard):
            # no updates, so don't check again
            widget.set_sensitive(False)

class PageKde(PageBase):
    plugin_breadcrumb = 'ubiquity/text/breadcrumb_language'
    plugin_is_language = True

    def __init__(self, controller, *args, **kwargs):
        self.controller = controller
        try:
            from PyQt4 import uic
            from PyQt4.QtGui import QLabel, QWidget
            self.page = uic.loadUi('/usr/share/ubiquity/qt/stepLanguage.ui')
            self.combobox = self.page.language_combobox
            self.combobox.currentIndexChanged[str].connect(self.on_language_selection_changed)
            
            if not self.controller.oem_config:
                self.page.oem_id_label.hide()
                self.page.oem_id_entry.hide()

            if self.page.findChildren(QWidget,'update_this_installer'):
                if self.controller.oem_config or auto_update.already_updated():
                    self.page.update_this_installer.hide()
                else:
                    self.page.update_this_installer.clicked.connect(
                        self.on_update_this_installer)

            class linkLabel(QLabel):
                def __init__(self, wizard, parent):
                    QLabel.__init__(self, parent)
                    self.wizard = wizard

                def mouseReleaseEvent(self, event):
                    self.wizard.openReleaseNotes()

                def setText(self, text):
                    QLabel.setText(self, text)
                    self.resize(self.sizeHint())

            self.release_notes_url = linkLabel(self, self.page.release_notes_frame)
            self.release_notes_url.setObjectName("release_notes_url")
            self.release_notes_url.show()

            self.release_notes_url_template = None
            try:
                release_notes = open(_release_notes_url_path)
                self.release_notes_url_template = release_notes.read().rstrip('\n')
                release_notes.close()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.page.release_notes_label.hide()
                self.page.release_notes_frame.hide()
                
        except Exception, e:
            self.debug('Could not create language page: %s', e)
            self.page = None
        self.plugin_widgets = self.page

    def openReleaseNotes(self):
        lang = self.selected_language()
        if lang:
            lang = lang.split('.')[0].lower()
            url = self.release_notes_url_template.replace('${LANG}', lang)
            self.openURL(url)

    def openURL(self, url):
        #need to run this else kdesu can't run Konqueror
        misc.execute('su', '-c', 'xhost +localhost', 'ubuntu')
        misc.execute('su', '-c', 'kfmclient openURL '+url, 'ubuntu')

    def set_language_choices(self, choices, choice_map):
        from PyQt4.QtCore import QString
        PageBase.set_language_choices(self, choices, choice_map)
        self.combobox.clear()
        for choice in choices:
            self.combobox.addItem(QString(unicode(choice)))

    def set_language(self, language):
        from PyQt4.QtCore import QString
        index = self.combobox.findText(QString(unicode(language)))
        if index < 0:
            self.combobox.addItem("C")
        else:
            self.combobox.setCurrentIndex(index)

    def get_language(self):
        lang = self.selected_language()
        return lang if lang else 'C'

    def selected_language(self):
        lang = self.combobox.currentText()
        if lang.isNull():
            return None
        else:
            return self.language_choice_map[unicode(lang)][1]

    def on_language_selection_changed(self):
        lang = self.selected_language()
        if lang:
            # strip encoding; we use UTF-8 internally no matter what
            lang = lang.split('.')[0].lower()

            self.controller.translate(lang)

            if self.release_notes_url_template is not None:
                url = self.release_notes_url_template.replace('${LANG}', lang)
                text = i18n.get_string('release_notes_url', lang)
                self.release_notes_url.setText('<a href="%s">%s</a>' % (url, text))

    def set_oem_id(self, text):
        return self.page.oem_id_entry.setText(text)

    def get_oem_id(self):
        return unicode(self.page.oem_id_entry.text())

    def on_update_this_installer(self):
        if not auto_update.update(self.controller._wizard):
            # no updates, so don't check again
            self.page.update_this_installer.setEnabled(False)

class PageDebconf(PageBase):
    plugin_title = 'ubiquity/text/language_heading_label'

    def __init__(self, controller, *args, **kwargs):
        self.controller = controller

class PageNoninteractive(PageBase):
    def __init__(self, controller, *args, **kwargs):
        self.controller = controller

    def set_language(self, language):
        """Set the current selected language."""
        # Use the language code, not the translated name
        self.language = self.language_choice_map[language][1]

    def get_language(self):
        """Get the current selected language."""
        return self.language

class Page(Plugin):
    def prepare(self, unfiltered=False):
        self.language_question = None
        self.initial_language = None
        self.db.fset('localechooser/languagelist', 'seen', 'false')
        with misc.raised_privileges():
            osextras.unlink_force('/var/lib/localechooser/preseeded')
            osextras.unlink_force('/var/lib/localechooser/langlevel')
        if self.ui.controller.oem_config:
            try:
                self.ui.set_oem_id(self.db.get('oem-config/id'))
            except debconf.DebconfError:
                pass

        localechooser_script = '/usr/lib/ubiquity/localechooser/localechooser'
        if ('UBIQUITY_FRONTEND' in os.environ and
            os.environ['UBIQUITY_FRONTEND'] == 'debconf_ui'):
            localechooser_script += '-debconf'

        questions = ['localechooser/languagelist']
        environ = {'PATH': '/usr/lib/ubiquity/localechooser:' + os.environ['PATH']}
        if 'UBIQUITY_FRONTEND' in os.environ and os.environ['UBIQUITY_FRONTEND'] == "debconf_ui":
          environ['TERM_FRAMEBUFFER'] = '1'
        else:
          environ['OVERRIDE_SHOW_ALL_LANGUAGES'] = '1'
        return (localechooser_script, questions, environ)

    def run(self, priority, question):
        if question == 'localechooser/languagelist':
            self.language_question = question
            if self.initial_language is None:
                self.initial_language = self.db.get(question)
            current_language_index = self.value_index(question)
            only_installable = misc.create_bool(self.db.get('ubiquity/only-show-installable-languages'))

            current_language, sorted_choices, language_display_map = \
                i18n.get_languages(current_language_index, only_installable)

            self.ui.set_language_choices(sorted_choices,
                                         language_display_map)
            self.ui.set_language(current_language)
        return Plugin.run(self, priority, question)

    def cancel_handler(self):
        self.ui.controller.translate(just_me=False) # undo effects of UI translation
        Plugin.cancel_handler(self)

    def ok_handler(self):
        if self.language_question is not None:
            new_language = self.ui.get_language()
            self.preseed(self.language_question, new_language)
            if (self.initial_language is None or
                self.initial_language != new_language):
                self.db.reset('debian-installer/country')
        if self.ui.controller.oem_config:
            self.preseed('oem-config/id', self.ui.get_oem_id())
        Plugin.ok_handler(self)

    def cleanup(self):
        Plugin.cleanup(self)
        i18n.reset_locale(self.frontend)
        self.frontend.stop_debconf()
        self.ui.controller.translate(just_me=False, reget=True)

class Install(InstallPlugin):
    def prepare(self, unfiltered=False):
        if 'UBIQUITY_OEM_USER_CONFIG' in os.environ:
            return (['/usr/lib/ubiquity/localechooser-apply'], [])
        else:
            return (['sh', '-c',
                     '/usr/lib/ubiquity/localechooser/post-base-installer ' +
                     '&& /usr/lib/ubiquity/localechooser/finish-install'], [])

    def install(self, target, progress, *args, **kwargs):
        progress.info('ubiquity/install/locales')
        rv = InstallPlugin.install(self, target, progress, *args, **kwargs)
        if not rv:
            # fontconfig configuration needs to be adjusted based on the
            # selected locale (from language-selector-common.postinst). Ignore
            # errors.
            misc.execute('chroot', target, 'fontconfig-voodoo', '--auto', '--force', '--quiet')
        return rv
