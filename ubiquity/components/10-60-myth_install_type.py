# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2006, 2007, 2009 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.
# Copyright (C) 2007 Mario Limonciello
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

from ubiquity.plugin import Plugin
import os

NAME = 'myth-installtype'
AFTER = 'usersetup'

class PageGtk:
    def __init__(self, *args, **kwargs):
        pass
    def get_ui(self):
        if os.environ['UBIQUITY_FRONTEND'] == 'mythbuntu_ui':
            return {'widgets': 'mythbuntu_stepCustomInstallType'}
        else:
            return None

class Page(Plugin):
#we are seeding one of the possible install types

    def prepare(self):
        self.questions = ['install_type']
        questions = []
        for question in self.questions:
            answer = self.db.get('mythbuntu/' + question)
            if answer != '':
                self.frontend.set_installtype(answer)
            questions.append('^mythbuntu/' + question)
        return (['/usr/share/ubiquity/ask-mythbuntu','type'], questions)

    def ok_handler(self):
        self.preseed('mythbuntu/' + self.questions[0],self.frontend.get_installtype())
        Plugin.ok_handler(self)
