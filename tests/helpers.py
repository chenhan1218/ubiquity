"""Testing helpers."""

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

import sys

import mock


if sys.version >= '3':
    def builtin_patch(name):
        return mock.patch("builtins.%s" % name)

    import io
    text_file_type = io.TextIOBase
else:
    def builtin_patch(name):
        return mock.patch("__builtin__.%s" % name)

    text_file_type = file
