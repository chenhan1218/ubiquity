# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2013 Canonical Ltd.
#
# Author:
#   Aurélien Gâteau <agateau@kde.org>
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

from PyQt4 import QtCore, QtGui

__all__ = ["Breadcrumb"]


class Breadcrumb(QtGui.QLabel):
    TODO = 0
    CURRENT = 1
    DONE = 2

    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)
        self.setWordWrap(True)
        self.setState(Breadcrumb.TODO)

    def setState(self, state):
        self.setStyleSheet(_CSS_DICT[state])


_CSS_DICT = {
    Breadcrumb.TODO: "color: #666666",
    Breadcrumb.CURRENT: """
        color: #0088aa;
        border-width: 6px;
        border-image: url(/usr/share/ubiquity/qt/images/label_border.png) 6px;
        """,
    Breadcrumb.DONE: "color: #b3b3b3",
}
