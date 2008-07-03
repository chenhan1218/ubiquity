# -*- coding: UTF-8 -*-

# Copyright (C) 2006 Canonical Ltd.
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
import syslog

from ubiquity.filteredcommand import FilteredCommand
from ubiquity import i18n
from ubiquity import misc

class Language(FilteredCommand):
    def prepare(self):
        self.language_question = None
        self.codes = None
        self.names = None
        #self.db.fset('languagechooser/language-name', 'seen', 'false')
        #self.db.fset('localechooser/languagelist', 'seen', 'false')
        self.db.set('localechooser/alreadyrun', 'false')
        questions = ['^languagechooser/language-name',
                     '^countrychooser/(shortlist|country-name)$',
                     'localechooser/languagelist', 'localechooser/continentlist']
        return (['/usr/lib/ubiquity/localechooser/localechooser'], questions,
                {'PATH': '/usr/lib/ubiquity/localechooser:' + os.environ['PATH'],
                 'OVERRIDE_SHOW_ALL_LANGUAGES': '1'})

    #def subst(self, question, key, value):
    #    syslog.syslog('subst %s %s' % (question, key))
    #    if key == 'CODES':
    #        self.codes = value
    #    elif key == 'NAMES_BOTH':
    #        self.names = value

    def run(self, priority, question):
        syslog.syslog('question: %s' % question)
        if question == 'localechooser/languagelist':
            self.language_question = question
            current_language_index = 17 #self.value_index(question)
            current_language = "English"

            # language_display_map = {u'Galego': (u'Galician', 'gl'), ...}
            import gzip
            languagelist = gzip.open('/usr/lib/ubiquity/localechooser/languagelist.data.gz')
            language_display_map = {}
            i = 0
            for line in languagelist:
                # TODO: necessary?
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
            syslog.syslog('sorted_choices: %s' % sorted_choices)
            self.frontend.set_language_choices(sorted_choices,
                                               language_display_map)
            syslog.syslog('language_display_map: %s' % language_display_map)
            self.frontend.set_language(current_language)

        #if question == 'localechooser/languagelist':
        #    syslog.syslog('codes: %s' % self.codes)
        #    syslog.syslog('names: %s' % self.names)
        #    language_display_map = {}
        #    for code, name in zip(self.codes.split(', '), self.names.split(u', ')):
        #        # FIXME evand 2008-06-16: This will break horribly once perl
        #        # debconf supports directives.
        #        n = name.split(u'${!TAB}-${!TAB}')
        #        language_display_map[n[1]] = (n[0], code)
        #    syslog.syslog('language_display_map: %s' % language_display_map)
        #    
        #    def compare_choice(x, y):
        #        result = cmp(language_display_map[x][1],
        #                     language_display_map[y][1])
        #        if result != 0:
        #            return result
        #        return cmp(x, y)

        #    sorted_choices = sorted(language_display_map, compare_choice)
        #    syslog.syslog('sorted_choices: %s' % sorted_choices)
        #    self.frontend.set_language_choices(sorted_choices,
        #                                       language_display_map)
        #    current_language = "English"
        #    self.frontend.set_language(current_language)

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
            languagelist = open('/usr/lib/ubiquity/localechooser/languagelist')
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
        elif question == 'localechooser/continentlist':
            pass

        elif question.startswith('countrychooser/'):
            if 'DEBCONF_USE_CDEBCONF' not in os.environ:
                # Normally this default is handled by Default-$LL, but since
                # we can't change debconf's language on the fly (unlike
                # cdebconf), we have to fake it.
                country = self.db.get('debian-installer/country')
                if question.endswith('shortlist'):
                    self.db.set(question, country)
                elif question.endswith('country-name') and country:
                    fp = open('/usr/share/iso-codes/iso_3166.tab')
                    try:
                        for line in fp:
                            if line.startswith(country):
                                line = line.rstrip('\n')
                                self.db.set(question, line.split('\t')[1])
                                break
                    finally:
                        fp.close()
            return True

        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        #self.preseed('debconf/language', 'UTF-8')
        #self.preseed('debian-installer/language', 'pt_BR_US:UTF-8')
        #self.preseed('debian-installer/locale', 'BR')
        if self.language_question is not None:
            self.preseed(self.language_question, 'fr')
            #self.preseed('debconf/language', 'UTF-8')
            #self.preseed('debian-installer/language', 'fr_FR')
            #self.preseed('debian-installer/country', 'FR')
            #self.preseed('debian-installer/locale', 'fr')
            #self.preseed(self.language_question, self.frontend.get_language())
        FilteredCommand.ok_handler(self)

    def cleanup(self):
        di_locale = self.db.get('debian-installer/locale')
        if di_locale not in i18n.get_supported_locales():
            di_locale = self.db.get('debian-installer/fallbacklocale')
        if di_locale != self.frontend.locale:
            self.frontend.locale = di_locale
            os.environ['LANG'] = di_locale
            os.environ['LANGUAGE'] = di_locale
            try:
                locale.setlocale(locale.LC_ALL, '')
            except locale.Error, e:
                self.debug('locale.setlocale failed: %s (LANG=%s)',
                           e, di_locale)
            misc.execute_root('fontconfig-voodoo',
                              '--auto', '--force', '--quiet')
