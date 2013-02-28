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

from PyQt4 import QtGui
from PyQt4.QtCore import Qt

__all__ = ["Breadcrumb"]


class Breadcrumb(QtGui.QFrame):
    TODO = 0
    CURRENT = 1
    DONE = 2

    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setProperty("isBreadcrumb", True)

        self._tickLabel = QtGui.QLabel()
        fm = self._tickLabel.fontMetrics()
        self._tickLabel.setFixedWidth(fm.width(" M "))
        self._tickLabel.setAlignment(Qt.AlignTop | Qt.AlignRight)

        self._mainLabel = QtGui.QLabel()
        self._mainLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._mainLabel.setWordWrap(True)

        layout = QtGui.QHBoxLayout(self)
        layout.addWidget(self._tickLabel)
        layout.addWidget(self._mainLabel)

        self.setState(Breadcrumb.TODO)

    def setState(self, state):
        self._tickLabel.setText(_TICK_DICT[state])
        self.setStyleSheet(_CSS_DICT[state])

    def setText(self, text):
        self._mainLabel.setText(text)

    def text(self):
        return self._mainLabel.text()


_TICK_DICT = {
    Breadcrumb.TODO: "•",
    Breadcrumb.CURRENT: "‣",
    Breadcrumb.DONE: "✓",
}


_CSS_DICT = {
    Breadcrumb.TODO: "",
    Breadcrumb.CURRENT: """
    QFrame {
        border-top-width: 10px;
        border-bottom-width: 10px;
        background-image: none;
        border-image: url(/usr/share/ubiquity/qt/images/breadcrumb.png) 10px;
    }
    .QLabel {
        color: #333;
        border-width: 0px;
        border-image: none;
    }
    """,
    Breadcrumb.DONE: "",
}
