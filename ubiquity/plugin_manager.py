# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2009 Canonical Ltd.
# Written by Michael Terry <michael.terry@canonical.com>.
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Ubiquity is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubiquity.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import fnmatch

PLUGIN_PATH = '/usr/lib/ubiquity/plugins.d'

def load_plugins():
    modules = []
    modfiles = filter(lambda x: fnmatch.fnmatch(x,'*.py'), os.listdir(PLUGIN_PATH))
    sys.path.insert(0, PLUGIN_PATH)
    for modfile in modfiles:
        modname = os.path.splitext(modfile)[0]
        try:
            modules.append(__import__(modname))
        except Exception, e:
            print >> sys.stderr, 'Could not import plugin %s: %s' % (modname, e)
    del sys.path[0]
    return modules

def get_mod_list(mod, name):
    if hasattr(mod, name):
        mod_list = getattr(mod, name)
        if type(mod_list).__name__ != 'list':
            mod_list = [mod_list]
        return mod_list
    else:
        return []

def get_mod_string(mod, name):
    if hasattr(mod, name):
        mod_string = getattr(mod, name)
        return mod_string
    else:
        return ''

def get_mod_index(modlist, name):
    index = 0
    for mod in modlist:
        modname = get_mod_string(mod, 'NAME')
        if modname == name:
            return index
        index += 1
    return None

def order_plugins(mods, order):
    hidden_list = []
    for mod in mods:
        name = get_mod_string(mod, 'NAME')
        if not name:
            continue
        after = get_mod_list(mod, 'AFTER')
        before = get_mod_list(mod, 'BEFORE')
        hidden = get_mod_list(mod, 'HIDDEN')
        if not after and not before and hidden:
            hidden_list.extend(hidden)
        index = None
        for modname in after:
            if not modname:
                index = 0
                break
            else:
                index = get_mod_index(order, modname)
                if index is not None:
                    index += 1
                    break
        if index is None:
            for modname in before:
                if not modname:
                    index = len(order)
                    break
                else:
                    index = get_mod_index(order, modname)
                    if index is not None:
                        break
        if index is not None:
            order.insert(index, mod)
            hidden_list.extend(hidden)
    for hidden in hidden_list:
        index = get_mod_index(order, hidden)
        if index is not None:
            del order[index]
    return order
