# -*- coding: utf-8 -*-

# «validation» - miscellaneous validation of user-entered data
#
# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006 Canonical Ltd.
#
# Authors:
#
# - Antonio Olmo Titos <aolmo#emergya._info>
# - Javier Carranza <javier.carranza#interactors._coop>
# - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
# - Colin Watson <cjwatson@ubuntu.com>
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or at your option)
# any later version.
#
# Ubiquity is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with Ubiquity; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# Validation library.
# Created by Antonio Olmo <aolmo#emergya._info> on 26 jul 2005.

HOSTNAME_LENGTH = 1
HOSTNAME_BADCHAR = 2
HOSTNAME_BADHYPHEN = 3

def check_hostname(name):

    """ Check the correctness of a proposed host name.

        @return empty list (valid) or list of:
            - C{HOSTNAME_LENGTH} wrong length.
            - C{HOSTNAME_BADCHAR} contains invalid characters.
            - C{HOSTNAME_BADHYPHEN} starts or ends with a hyphen."""

    import re
    result = set()

    if len (name) < 2 or len (name) > 63:
        result.add(HOSTNAME_LENGTH)

    regex = re.compile(r'^[a-zA-Z0-9.-]+$')
    if not regex.search(name):
        result.add(HOSTNAME_BADCHAR)
    if name.startswith('-') or name.endswith('-'):
        result.add(HOSTNAME_BADHYPHEN)

    return sorted(result)
