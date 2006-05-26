# -*- coding: utf-8 -*-

# «settings» - ajustes globales
# 
# Copyright (C) 2005 Junta de Andalucía
# 
# Author:
# 
# - Antonio Olmo Titos <aolmo#emergya._info>
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

""" U{pylint<http://logilab.org/projects/pylint>} mark: -5.00! (wrong
    encoding) """

# Global settings.
# Created by Antonio Olmo <aolmo#emergya._info> on 7 oct 2005.

DEBUGGING_STATUS = True

MINIMAL_PARTITION_SCHEME = {'swap':  205,
                            'root': 2048,
                            'home':  512}

LARGER_PARTITION_SCHEME = {'swap':  1024,
                           'root': 20480,
                           'home': 30720}

# WARNING: next variable controls whether partitioning will be actually
#          performed, or not. Enable it at your own risk!
ACTUAL_PARTITIONING = True
