# Copyright (C) 2012 Canonical Ltd.
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

"""Parse the output of kbdnames-maker."""

import gzip
import io


_default_filename = "/usr/lib/ubiquity/console-setup/kbdnames.gz"


class KeyboardNames:
    def __init__(self, filename=_default_filename):
        self._current_lang = None
        self._filename = filename
        self._clear()

    def _clear(self):
        self._layout = {}
        self._layout_rev = {}
        self._variant = {}
        self._variant_rev = {}

    def _load_file(self, lang, kbdnames):
        # TODO cjwatson 2012-07-19: Work around
        # http://bugs.python.org/issue10791 in Python 3.2.  When we can rely
        # on 3.3, this should be:
        #   for line in kbdnames:
        #       line = line.rstrip("\n")
        for line in kbdnames.read().splitlines():
            got_lang, element, name, value = line.split("*", 3)
            if got_lang != lang:
                continue

            if element == "layout":
                self._layout[name] = value
                self._layout_rev[value] = name
            elif element == "variant":
                variantname, variantdesc = value.split("*", 1)
                if name not in self._variant:
                    self._variant[name] = {}
                self._variant[name][variantname] = variantdesc
                if name not in self._variant_rev:
                    self._variant_rev[name] = {}
                self._variant_rev[name][variantdesc] = variantname

    def _load(self, lang):
        if lang == self._current_lang:
            return

        # Saving memory is more important than parsing time in the
        # relatively rare case of changing languages, so we only keep data
        # around for a single language.
        self._clear()

        raw = gzip.open(self._filename)
        try:
            with io.TextIOWrapper(raw) as kbdnames:
                self._load_file(lang, kbdnames)
        finally:
            raw.close()
        self._current_lang = lang

    def has_language(self, lang):
        self._load(lang)
        return bool(self._layout)

    def has_layout(self, lang, name):
        self._load(lang)
        return name in self._layout

    def layout(self, lang, name):
        self._load(lang)
        return self._layout[name]

    def layout_reverse(self, lang, value):
        self._load(lang)
        return self._layout_rev[value]

    def has_variants(self, lang, layout):
        self._load(lang)
        return layout in self._variant

    def has_variant(self, lang, layout, name):
        self._load(lang)
        return layout in self._variant and name in self._variant[layout]

    def variant(self, lang, layout, name):
        self._load(lang)
        return self._variant[layout][name]

    def variant_reverse(self, lang, layout, value):
        self._load(lang)
        return self._variant_rev[layout][value]


_keyboard_names = None


def _get_keyboard_names():
    """Return a singleton KeyboardNames instance."""
    global _keyboard_names
    if _keyboard_names is None:
        _keyboard_names = KeyboardNames()
    return _keyboard_names


def has_language(lang):
    kn = _get_keyboard_names()
    return kn.has_language(lang)


def has_layout(lang, name):
    kn = _get_keyboard_names()
    return kn.has_layout(lang, name)


def layout(lang, name):
    kn = _get_keyboard_names()
    return kn.layout(lang, name)


def layout_reverse(lang, value):
    kn = _get_keyboard_names()
    return kn.layout_reverse(lang, value)


def has_variants(lang, layout):
    kn = _get_keyboard_names()
    return kn.has_variants(lang, layout)


def has_variant(lang, layout, name):
    kn = _get_keyboard_names()
    return kn.has_variant(lang, layout, name)


def variant(lang, layout, name):
    kn = _get_keyboard_names()
    return kn.variant(lang, layout, name)


def variant_reverse(lang, layout, value):
    kn = _get_keyboard_names()
    return kn.variant_reverse(lang, layout, value)
