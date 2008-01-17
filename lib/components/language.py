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
from oem_config import i18n
from oem_config import im_switch

class Language(FilteredCommand):
    def prepare(self):
        self.language_question = None
        self.db.fset('languagechooser/language-name', 'seen', 'false')
        self.db.set('localechooser/alreadyrun', 'false')
        questions = ['^languagechooser/language-name',
                     '^countrychooser/(shortlist|country-name)$']
        return (['/usr/lib/oem-config/language/localechooser-wrapper'],
                questions)

    def run(self, priority, question):
        if question.startswith('languagechooser/language-name'):
            self.language_question = question

            # Get index of untranslated value; we'll map this to the
            # translated value later.
            current_language_index = self.value_index(question)
            current_language = "English"

            language_choices = self.split_choices(
                unicode(self.db.metaget(question, 'choices-en.utf-8'),
                        'utf-8', 'replace'))
            language_choices_c = self.choices_untranslated(question)

            language_codes = {}
            languagelist = open('/usr/share/localechooser/languagelist')
            for line in languagelist:
                if line.startswith('#'):
                    continue
                bits = line.split(';')
                if len(bits) >= 3:
                    if bits[2] in ('dz', 'km'):
                        # Exclude these languages for now, as we don't ship
                        # fonts for them and we don't have sufficient
                        # translations anyway.
                        continue
                    elif bits[2] in ('pt', 'zh'):
                        # Special handling for subdivided languages.
                        code = '%s_%s' % (bits[2], bits[3])
                    else:
                        code = bits[2]
                    language_codes[bits[0]] = code
            languagelist.close()

            language_display_map = {}
            for i in range(len(language_choices)):
                choice = re.sub(r'.*? *- (.*)', r'\1', language_choices[i])
                choice_c = language_choices_c[i]
                if choice_c not in language_codes:
                    continue
                language_display_map[choice] = (choice_c,
                                                language_codes[choice_c])
                if i == current_language_index:
                    current_language = choice

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

        elif question.startswith('countrychooser/'):
            if 'DEBCONF_USE_CDEBCONF' not in os.environ:
                # Normally this default is handled by Default-$LL, but since
                # we can't change debconf's language on the fly (unlike
                # cdebconf), we have to fake it.
                self.db.set(question, self.db.get('debian-installer/country'))
            return True

        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        if self.language_question is not None:
            self.preseed(self.language_question, self.frontend.get_language())
        FilteredCommand.ok_handler(self)

    def cleanup(self):
        di_locale = self.db.get('debian-installer/locale')
        if di_locale not in i18n.get_supported_locales():
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
            im_switch.start_im()
