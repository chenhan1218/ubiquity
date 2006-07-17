# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import re
import locale
from oem_config.filteredcommand import FilteredCommand

_supported_locales = None

def _get_supported_locales():
    """Returns a list of all locales supported by the installation system."""
    global _supported_locales
    if _supported_locales is None:
        _supported_locales = {}
        supported = open('/usr/share/i18n/SUPPORTED')
        for line in supported:
            (locale, charset) = line.split(None, 1)
            _supported_locales[locale] = charset
        supported.close()
    return _supported_locales

class Language(FilteredCommand):
    def prepare(self):
        self.language_question = 'languagechooser/language-name'
        self.country_question = 'countrychooser/country-name'
        self.restart = False

        try:
            current_language = self.db.get('languagechooser/language-name')
        except debconf.DebconfError:
            current_language = ''
        if current_language:
            current_language = re.sub(r'.*? *- (.*)', r'\1', current_language)
        else:
            current_language = 'English'

        language_choices = self.split_choices(
            unicode(self.db.metaget('languagechooser/language-name',
                                    'choices-en.utf-8'), 'utf-8'))
        language_choices_c = self.choices_untranslated(
            'languagechooser/language-name')

        language_codes = {}
        languagelist = open('/usr/share/localechooser/languagelist')
        for line in languagelist:
            if line.startswith('#'):
                continue
            bits = line.split(';')
            if len(bits) >= 3:
                language_codes[bits[0]] = bits[2]
        languagelist.close()

        language_display_map = {}
        for i in range(len(language_choices)):
            choice = re.sub(r'.*? *- (.*)', r'\1', language_choices[i])
            choice_c = language_choices_c[i]
            if choice_c not in language_codes:
                continue
            language_display_map[choice] = (choice_c, language_codes[choice_c])

        def compare_choice(x, y):
            result = cmp(language_display_map[x][1],
                         language_display_map[y][1])
            if result != 0:
                return result
            return cmp(x, y)

        sorted_choices = sorted(language_display_map, compare_choice)
        self.frontend.set_language_choices(sorted_choices,
                                           language_display_map)
        self.frontend.set_language(current_language)

        self.update_country_list('countrychooser/country-name')

        questions = ['^languagechooser/language-name',
                     '^countrychooser/country-name$',
                     '^countrychooser/shortlist$',
                     '^localechooser/supported-locales$']
        return (['/usr/lib/oem-config/language/localechooser-wrapper'],
                questions)

    def update_country_list(self, question):
        self.frontend.set_country_choices(self.choices_display_map(question))
        try:
            self.frontend.set_country(self.db.get(question))
        except ValueError:
            pass

    def preseed_language(self):
        self.preseed(self.language_question, self.frontend.get_language())

    def preseed_country(self):
        self.preseed_as_c(self.country_question, self.frontend.get_country())

    def language_handler(self, widget, data=None):
        self.preseed_language()
        # We now need to run through most of localechooser, but stop just
        # before the end. This can be done by backing up from
        # localechooser/supported-locales, so leave a note for ourselves to
        # do so.
        self.restart = True
        self.succeeded = True
        self.exit_ui_loops()

    def ok_handler(self):
        self.preseed_language()
        self.preseed_country()
        super(Language, self).ok_handler()

    def run(self, priority, question):
        if question == 'localechooser/supported-locales':
            if self.restart:
                self.frontend.redo_step()
                self.succeeded = False
                self.done = True
                return False
            else:
                return True

        if question.startswith('languagechooser/language-name'):
            self.language_question = question
            return True
        elif question.startswith('countrychooser/'):
            self.country_question = question
        self.update_country_list(question)

        return super(Language, self).run(priority, question)

    def cleanup(self):
        di_locale = self.db.get('debian-installer/locale')
        if di_locale not in _get_supported_locales():
            di_locale = self.db.get('debian-installer/fallbacklocale')
        if di_locale == '':
            # TODO cjwatson 2006-07-17: maybe fetch
            # languagechooser/language-name and set a language based on
            # that?
            di_locale = 'en_US.UTF-8'
        if di_locale != self.frontend.locale:
            self.frontend.locale = di_locale
            os.environ['LANG'] = di_locale
            os.environ['LANGUAGE'] = di_locale
            try:
                locale.setlocale(locale.LC_ALL, '')
            except locale.Error, e:
                self.debug('locale.setlocale failed: %s (LANG=%s)',
                           e, di_locale)
