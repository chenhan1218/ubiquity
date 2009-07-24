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
import re
import locale

from ubiquity.plugin import Plugin
from ubiquity import i18n

NAME = 'language'
AFTER = None

class PageBase:
    def set_language_choices(self, choices, choice_map):
        """Called with language choices and a map to localised names."""
        self.language_choice_map = dict(choice_map)

    def set_language(self, language):
        """Set the current selected language."""
        pass

    def get_language(self):
        """Get the current selected language."""
        return 'C'

try:
    import gtk, gobject
    class PageGtk(PageBase):
        def __init__(self, controller, *args, **kwargs):
            self.controller = controller
            self.controller.is_language_page = True
            if 'UBIQUITY_OEM_USER_CONFIG' in os.environ:
                ui_file = 'stepLanguageOnly.ui'
                self.only = True
            else:
                ui_file = 'stepLanguage.ui'
                self.only = False
            try:
                builder = gtk.Builder()
                builder.add_from_file('/usr/share/ubiquity/gtk/%s' % ui_file)
                self.page = builder.get_object('page')
                self.iconview = builder.get_object('language_iconview')
                self.treeview = builder.get_object('language_treeview')

                release_notes_vbox = builder.get_object('release_notes_vbox')
                if release_notes_vbox:
                    try:
                        release_notes_url = builder.get_object('release_notes_url')
                        release_notes = open('/cdrom/.disk/release_notes_url')
                        release_notes_url.set_uri(
                            release_notes.read().rstrip('\n'))
                        release_notes.close()
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except:
                        release_notes_vbox.hide()
            except:
                self.page = None

        def get_ui(self):
            return self.page

        def set_language_choices(self, choices, choice_map):
            PageBase.set_language_choices(self, choices, choice_map)
            list_store = gtk.ListStore(gobject.TYPE_STRING)
            for choice in choices:
                list_store.append([choice])
            # Support both iconview and treeview
            if self.only:
                self.iconview.set_model(list_store)
                self.iconview.set_text_column(0)
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
except:
    pass

class PageKde:
    def get_ui(self):
        return 'stepLanguage'

class PageDebconf:
    def get_ui(self):
        return 'stepLanguage'

class Page(Plugin):
    def prepare(self, unfiltered=False):
        self.language_question = None
        self.initial_language = None
        self.db.fset('localechooser/languagelist', 'seen', 'false')
        try:
            os.unlink('/var/lib/localechooser/preseeded')
            os.unlink('/var/lib/localechooser/langlevel')
        except OSError:
            pass
        questions = ['localechooser/languagelist']
        environ = {'PATH': '/usr/lib/ubiquity/localechooser:' + os.environ['PATH']}
        if 'UBIQUITY_FRONTEND' in os.environ and os.environ['UBIQUITY_FRONTEND'] == "debconf_ui":
          environ['TERM_FRAMEBUFFER'] = '1'
        else:
          environ['OVERRIDE_SHOW_ALL_LANGUAGES'] = '1'
        return (['/usr/lib/ubiquity/localechooser/localechooser'], questions,
                environ)

    def run(self, priority, question):
        if question == 'localechooser/languagelist':
            self.language_question = question
            if self.initial_language is None:
                self.initial_language = self.db.get(question)
            current_language_index = self.value_index(question)
            current_language = "English"

            import gzip
            languagelist = gzip.open('/usr/lib/ubiquity/localechooser/languagelist.data.gz')
            language_display_map = {}
            i = 0
            for line in languagelist:
                line = unicode(line, 'utf-8')
                if line == '' or line == '\n':
                    continue
                code, name, trans = line.strip(u'\n').split(u':')[1:]
                if code in ('dz', 'km'):
                    i += 1
                    continue
                language_display_map[trans] = (name, code)
                if i == current_language_index:
                    current_language = trans
                i += 1
            languagelist.close()

            def compare_choice(x, y):
                result = cmp(language_display_map[x][1],
                             language_display_map[y][1])
                if result != 0:
                    return result
                return cmp(x, y)

            sorted_choices = sorted(language_display_map, compare_choice)
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
        Plugin.ok_handler(self)

    def cleanup(self):
        Plugin.cleanup(self)
        # Done after sub-cleanup because now the debconf lock is clear for a reset/reget
        i18n.reset_locale()
        self.ui.controller.translate(just_me=False, reget=True)
