# -*- coding: utf-8 -*-

# «validation» - validación de los datos de entrada del usuario
# 
# Copyright (C) 2005 Junta de Andalucía
# 
# Autor/es (Author/s):
# 
# - Antonio Olmo Titos <aolmo#emergya._info>
# - Javier Carranza <javier.carranza#interactors._coop>
# - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
# 
# Este fichero es parte del instalador en directo de Guadalinex 2005.
# 
# El instalador en directo de Guadalinex 2005 es software libre. Puede
# redistribuirlo y/o modificarlo bajo los términos de la Licencia Pública
# General de GNU según es publicada por la Free Software Foundation, bien de la
# versión 2 de dicha Licencia o bien (según su elección) de cualquier versión
# posterior. 
# 
# El instalador en directo de Guadalinex 2005 se distribuye con la esperanza de
# que sea útil, pero SIN NINGUNA GARANTÍA, incluso sin la garantía MERCANTIL
# implícita o sin garantizar la CONVENIENCIA PARA UN PROPÓSITO PARTICULAR. Véase
# la Licencia Pública General de GNU para más detalles.
# 
# Debería haber recibido una copia de la Licencia Pública General junto con el
# instalador en directo de Guadalinex 2005. Si no ha sido así, escriba a la Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
# USA.
# 
# -------------------------------------------------------------------------
# 
# This file is part of Guadalinex 2005 live installer.
# 
# Guadalinex 2005 live installer is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License, or
# at your option) any later version.
# 
# Guadalinex 2005 live installer is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# Guadalinex 2005 live installer; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

""" U{pylint<http://logilab.org/projects/pylint>} mark: 6.67 """

# Validation library.
# Created by Antonio Olmo <aolmo#emergya._info> on 26 jul 2005.

from string            import whitespace, uppercase
from espresso.settings import *

HOSTNAME_LENGTH = 1
HOSTNAME_WHITESPACE = 2
HOSTNAME_BADCHAR = 3

def check_hostname(name):

    """ Check the correctness of a proposed host name.

        @return empty list (valid) or list of:
            - C{HOSTNAME_LENGTH} wrong length.
            - C{HOSTNAME_WHITESPACE} contains white spaces.
            - C{HOSTNAME_BADCHAR} contains invalid characters."""

    import re
    result = set()

    if len (set(name).intersection(set(whitespace))) > 0:
        result.add(HOSTNAME_WHITESPACE)
    if len (name) < 3 or len (name) > 18:
        result.add(HOSTNAME_LENGTH)

    regex = re.compile(r'^[a-zA-Z0-9]+$')
    if not regex.search(name):
        result.add(HOSTNAME_BADCHAR)

    return sorted(result)

MOUNTPOINT_NOROOT = 1
MOUNTPOINT_DUPPATH = 2
MOUNTPOINT_BADSIZE = 3
MOUNTPOINT_BADCHAR = 4

def check_mountpoint(mountpoints, size):

    """ Check the correctness of a proposed set of mountpoints.

        @return empty list (valid) or list of:
            - C{MOUNTPOINT_NOROOT} Doesn't exist root path.
            - C{MOUNTPOINT_DUPPATH} Path duplicated.
            - C{MOUNTPOINT_BADSIZE} Size incorrect.
            - C{MOUNTPOINT_BADCHAR} Contains invalid characters."""

    import re
    result = set()
    root = 0

    for mountpoint, format in mountpoints.itervalues():
        if mountpoint == 'swap':
            root_minimum_KB = MINIMAL_PARTITION_SCHEME['root'] * 1024
            break
    else:
        root_minimum_KB = (MINIMAL_PARTITION_SCHEME['root'] +
                           MINIMAL_PARTITION_SCHEME['swap']) * 1024

    seen_mountpoints = set()
    for device, (path, format) in mountpoints.items():
        if path == '/':
            root = 1

            if float(size[device.split('/')[2]]) < root_minimum_KB:
                result.add(MOUNTPOINT_BADSIZE)

        if path in seen_mountpoints:
            result.add(MOUNTPOINT_DUPPATH)
        else:
            seen_mountpoints.add(path)
        regex = re.compile(r'^[a-zA-Z0-9/\-\_\+]+$')
        if not regex.search(path):
            result.add(MOUNTPOINT_BADCHAR)

    if root != 1:
        result.add(MOUNTPOINT_NOROOT)

    return sorted(result)
