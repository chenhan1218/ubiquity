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

import re
import subprocess
import codecs
import os
import locale
import sys
from ubiquity import misc, im_switch

_supported_locales = None

def get_supported_locales():
    """Returns a list of all locales supported by the installation system."""
    global _supported_locales
    if _supported_locales is None:
        _supported_locales = {}
        supported = open('/usr/share/i18n/SUPPORTED')
        for line in supported:
            (slocale, charset) = line.split(None, 1)
            _supported_locales[slocale] = charset
        supported.close()
    return _supported_locales


# if 'just_country' is True, only the country is changing
def reset_locale(frontend, just_country=False):
    di_locale = frontend.db.get('debian-installer/locale')
    if di_locale not in get_supported_locales():
        di_locale = frontend.db.get('debian-installer/fallbacklocale')
    if not di_locale:
        # TODO cjwatson 2006-07-17: maybe fetch
        # languagechooser/language-name and set a language based on
        # that?
        di_locale = 'en_US.UTF-8'
    if 'LANG' not in os.environ or di_locale != os.environ['LANG']:
        os.environ['LANG'] = di_locale
        os.environ['LANGUAGE'] = di_locale
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error, e:
            print >>sys.stderr, 'locale.setlocale failed: %s (LANG=%s)' % \
                                (e, di_locale)
        if not just_country:
            misc.execute_root('fontconfig-voodoo',
                                '--auto', '--force', '--quiet')
        im_switch.start_im()
    return di_locale

_strip_context_re = None

def strip_context(unused_question, string):
    # po-debconf context
    global _strip_context_re
    if _strip_context_re is None:
        _strip_context_re = re.compile(r'\[\s[^\[\]]*\]$')
    string = _strip_context_re.sub('', string)

    return string


_translations = None

def get_translations(languages=None, core_names=[], extra_prefixes=[]):
    """Returns a dictionary {name: {language: description}} of translatable
    strings.

    If languages is set to a list, then only languages in that list will be
    translated. If core_names is also set to a list, then any names in that
    list will still be translated into all languages. If either is set, then
    the dictionary returned will be built from scratch; otherwise, the last
    cached version will be returned."""

    global _translations
    if _translations is None or languages is not None or core_names or extra_prefixes:
        if languages is None:
            use_langs = None
        else:
            use_langs = set('c')
            for lang in languages:
                ll_cc = lang.lower().split('.')[0]
                ll = ll_cc.split('_')[0]
                use_langs.add(ll_cc)
                use_langs.add(ll)

        prefixes = 'ubiquity|partman/text/undo_everything|partman/text/unusable|partman-basicfilesystems/bad_mountpoint|partman-basicfilesystems/text/specify_mountpoint|partman-basicmethods/text/format|partman-newworld/no_newworld|partman-partitioning|partman-target/no_root|partman-target/text/method|grub-installer/bootdev|popularity-contest/participate'
        prefixes = reduce(lambda x, y: x+'|'+y, extra_prefixes, prefixes)

        _translations = {}
        devnull = open('/dev/null', 'w')
        db = subprocess.Popen(
            ['debconf-copydb', 'templatedb', 'pipe',
             '--config=Name:pipe', '--config=Driver:Pipe',
             '--config=InFd:none',
             '--pattern=^(%s)' % prefixes],
            stdout=subprocess.PIPE, stderr=devnull,
            # necessary?
            preexec_fn=misc.regain_privileges)
        question = None
        descriptions = {}
        fieldsplitter = re.compile(r':\s*')

        for line in db.stdout:
            line = line.rstrip('\n')
            if ':' not in line:
                if question is not None:
                    _translations[question] = descriptions
                    descriptions = {}
                    question = None
                continue

            (name, value) = fieldsplitter.split(line, 1)
            if value == '':
                continue
            name = name.lower()
            if name == 'name':
                question = value
            elif name.startswith('description'):
                namebits = name.split('-', 1)
                if len(namebits) == 1:
                    lang = 'c'
                else:
                    lang = namebits[1].lower()
                    # TODO: recode from specified encoding
                    lang = lang.split('.')[0]
                if (use_langs is None or lang in use_langs or
                    question in core_names):
                    value = strip_context(question, value)
                    descriptions[lang] = value.replace('\\n', '\n')
            elif name.startswith('extended_description'):
                namebits = name.split('-', 1)
                if len(namebits) == 1:
                    lang = 'c'
                else:
                    lang = namebits[1].lower()
                    # TODO: recode from specified encoding
                    lang = lang.split('.')[0]
                if (use_langs is None or lang in use_langs or
                    question in core_names):
                    value = strip_context(question, value)
                    if lang not in descriptions:
                        descriptions[lang] = value.replace('\\n', '\n')
                    # TODO cjwatson 2006-09-04: a bit of a hack to get the
                    # description and extended description separately ...
                    if question in ('grub-installer/bootdev',
                                    'partman-newworld/no_newworld',
                                    'ubiquity/text/error_updating_installer'):
                        descriptions["extended:%s" % lang] = \
                            value.replace('\\n', '\n')

        db.wait()
        devnull.close()

    return _translations

string_questions = {
    'new_size_label': 'partman-partitioning/new_size',
    'partition_create_heading_label': 'partman-partitioning/text/new',
    'partition_create_type_label': 'partman-partitioning/new_partition_type',
    'partition_create_mount_label': 'partman-basicfilesystems/text/specify_mountpoint',
    'partition_create_use_label': 'partman-target/text/method',
    'partition_create_place_label': 'partman-partitioning/new_partition_place',
    'partition_edit_use_label': 'partman-target/text/method',
    'partition_edit_format_label': 'partman-basicmethods/text/format',
    'partition_edit_mount_label': 'partman-basicfilesystems/text/specify_mountpoint',
    'grub_device_dialog': 'grub-installer/bootdev',
    'grub_device_label': 'grub-installer/bootdev',
    # TODO: it would be nice to have a neater way to handle stock buttons
    'quit': 'ubiquity/imported/quit',
    'back': 'ubiquity/imported/go-back',
    'next': 'ubiquity/imported/go-forward',
    'cancelbutton': 'ubiquity/imported/cancel',
    'exitbutton': 'ubiquity/imported/quit',
    'closebutton1': 'ubiquity/imported/close',
    'cancelbutton1': 'ubiquity/imported/cancel',
    'okbutton1': 'ubiquity/imported/ok',
}

string_extended = set('grub_device_label')

def map_widget_name(prefix, name):
    """Map a widget name to its translatable template."""
    if prefix is None:
        prefix = 'ubiquity/text'
    if '/' in name:
        question = name
    elif name in string_questions:
        question = string_questions[name]
    else:
        question = '%s/%s' % (prefix, name)
    return question

def get_string(name, lang, prefix=None):
    """Get the translation of a single string."""
    question = map_widget_name(prefix, name)
    translations = get_translations()
    if question not in translations:
        return None

    if lang is None:
        lang = 'c'
    else:
        lang = lang.lower()
    if name in string_extended:
        lang = 'extended:%s' % lang

    if lang in translations[question]:
        text = translations[question][lang]
    else:
        ll_cc = lang.split('.')[0]
        ll = ll_cc.split('_')[0]
        if ll_cc in translations[question]:
            text = translations[question][ll_cc]
        elif ll in translations[question]:
            text = translations[question][ll]
        elif lang.startswith('extended:'):
            text = translations[question]['extended:c']
        else:
            text = translations[question]['c']

    return unicode(text, 'utf-8', 'replace')


# Based on code by Walter Dörwald:
# http://mail.python.org/pipermail/python-list/2007-January/424460.html
def ascii_transliterate(exc):
    if not isinstance(exc, UnicodeEncodeError):
        raise TypeError("don't know how to handle %r" % exc)
    import unicodedata
    s = unicodedata.normalize('NFD', exc.object[exc.start])[:1]
    if ord(s) in range(128):
        return s, exc.start + 1
    else:
        return u'', exc.start + 1

codecs.register_error('ascii_transliterate', ascii_transliterate)


# Returns a tuple of (current language, sorted choices, display map).
def get_languages(current_language_index=-1, only_installable=False):
    import gzip
    import PyICU

    current_language = "English"

    if only_installable:
        from apt.cache import Cache
        #workaround for an issue where euid != uid and the
        #apt cache has not yet been loaded causing a SystemError
        #when libapt-pkg tries to load the Cache the first time.
        with misc.raised_privileges():
            cache = Cache()

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

        if only_installable:
            if code == 'C':
                i += 1
                continue
            pkg_name = 'language-pack-%s' % code
            #special case these
            if pkg_name.endswith('_CN'):
                pkg_name = 'language-pack-zh-hans'
            elif pkg_name.endswith('_TW'):
                pkg_name = 'language-pack-zh-hant'
            elif pkg_name.endswith('_NO'):
                pkg_name = pkg_name.split('_NO')[0]
            elif pkg_name.endswith('_BR'):
                pkg_name = pkg_name.split('_BR')[0]
            try:
                pkg = cache[pkg_name]
                if not (pkg.installed or pkg.candidate):
                    i += 1
                    continue
            except KeyError:
                i += 1
                continue

        language_display_map[trans] = (name, code)
        if i == current_language_index:
            current_language = trans
        i += 1
    languagelist.close()

    if only_installable:
        del cache

    try:
        # Note that we always collate with the 'C' locale.  This is far
        # from ideal.  But proper collation always requires a specific
        # language for its collation rules (languages frequently have
        # custom sorting).  This at least gives us common sorting rules,
        # like stripping accents.
        collator = PyICU.Collator.createInstance(PyICU.Locale('C'))
    except:
        collator = None

    def compare_choice(x):
        if language_display_map[x][1] == 'C':
            return None # place C first
        if collator:
            try:
                return collator.getCollationKey(x).getByteArray()
            except:
                pass
        # Else sort by unicode code point, which isn't ideal either,
        # but also has the virtue of sorting like-glyphs together
        return x

    sorted_choices = sorted(language_display_map, key=compare_choice)

    return current_language, sorted_choices, language_display_map

def default_locales():
    languagelist = open('/usr/lib/ubiquity/localechooser/languagelist')
    defaults = {}
    for line in languagelist:
        line = unicode(line, 'utf-8')
        if line == '' or line == '\n':
            continue
        bits = line.strip(u'\n').split(u';')
        code = bits[0]
        locale = bits[4]
        defaults[code] = locale
    languagelist.close()
    return defaults

# vim:ai:et:sts=4:tw=80:sw=4:
