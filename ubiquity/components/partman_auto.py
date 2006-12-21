# -*- coding: UTF-8 -*-

# Copyright (C) 2006 Canonical Ltd.
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

import os
import shutil
import signal
import debconf
from ubiquity.filteredcommand import FilteredCommand
from ubiquity.parted_server import PartedServer

class PartmanAuto(FilteredCommand):
    def __init__(self, frontend=None):
        FilteredCommand.__init__(self, frontend)
        self.resize_desc = ''
        self.manual_desc = ''

    def prepare(self):
        # If an old parted_server is still running, clean it up.
        if os.path.exists('/var/run/parted_server.pid'):
            try:
                pidline = open('/var/run/parted_server.pid').readline().strip()
                pid = int(pidline)
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
            try:
                os.unlink('/var/run/parted_server.pid')
            except OSError:
                pass

        # Force autopartitioning to be re-run.
        shutil.rmtree('/var/lib/partman', ignore_errors=True)

        self.autopartition_question = None
        self.state = None
        self.extra_options = {}
        self.extra_choice = None
        self.stashed_auto_mountpoints = None

        questions = ['^partman-auto/.*automatically_partition$',
                     '^partman-auto/select_disk$',
                     '^partman-partitioning/new_size$',
                     '^partman/choose_partition$',
                     '^partman/confirm.*',
                     'type:boolean',
                     'ERROR',
                     'PROGRESS']
        return ('/bin/partman', questions, {'PARTMAN_NO_COMMIT': '1'})

    def error(self, priority, question):
        if question == 'partman-partitioning/impossible_resize':
            # Back up silently.
            return False
        self.frontend.error_dialog(self.description(question),
                                   self.extended_description(question))
        return FilteredCommand.error(self, priority, question)

    def parse_size(self, size_str):
        (num, unit) = size_str.split(' ', 1)
        if ',' in num:
            (size_int, size_frac) = num.split(',', 1)
        else:
            (size_int, size_frac) = num.split('.', 1)
        size = float(str("%s.%s" % (size_int, size_frac)))
        # partman measures sizes in decimal units
        if unit == 'B':
            pass
        elif unit == 'kB':
            size *= 1000
        elif unit == 'MB':
            size *= 1000000
        elif unit == 'GB':
            size *= 1000000000
        elif unit == 'TB':
            size *= 1000000000000
        return size

    def subst(self, question, key, value):
        if question == 'partman-partitioning/new_size':
            if key == 'MINSIZE':
                self.resize_min_size = self.parse_size(value)
            elif key == 'MAXSIZE':
                self.resize_max_size = self.parse_size(value)

    def run(self, priority, question):
        if self.stashed_auto_mountpoints is None:
            # We need to extract the automatic mountpoints calculated by
            # partman at some point while parted_server is running, so that
            # they can be used later if manual partitioning is selected.
            # This hack is only necessary because the manual partitioner is
            # NIHed rather than being based on partman.
            self.stashed_auto_mountpoints = {}
            parted = PartedServer()
            for disk in parted.disks():
                parted.select_disk(disk)
                for part in parted.partitions():
                    (p_num, p_id, p_size, p_type, p_fs, p_path, p_name) = part
                    if p_fs == 'free':
                        continue
                    if not parted.has_part_entry(p_id, 'method'):
                        continue
                    method = parted.readline_part_entry(p_id, 'method')
                    if method == 'swap':
                        continue
                    elif p_fs == 'hfs' and method == 'newworld':
                        self.stashed_auto_mountpoints[p_path] = 'newworld'
                    elif parted.has_part_entry(p_id, 'acting_filesystem'):
                        mountpoint = parted.readline_part_entry(p_id,
                                                                'mountpoint')
                        self.stashed_auto_mountpoints[p_path] = mountpoint
            self.frontend.set_auto_mountpoints(self.stashed_auto_mountpoints)

        if self.done:
            # user answered confirmation question or selected manual
            # partitioning
            return self.succeeded

        self.current_question = question

        try:
            qtype = self.db.metaget(question, 'Type')
        except debconf.DebconfError:
            qtype = ''

        if question.endswith('automatically_partition'):
            self.autopartition_question = question
            choices = self.choices(question)

            if self.state is None:
                self.resize_desc = \
                    self.description('partman-auto/text/resize_use_free')
                self.manual_desc = \
                    self.description('partman-auto/text/custom_partitioning')
                self.extra_options = {}
                if choices:
                    self.state = [0, None]
            else:
                self.state[0] += 1
            while self.state[0] < len(choices):
                self.state[1] = choices[self.state[0]]
                if self.state[1] == self.manual_desc:
                    self.state[0] += 1
                else:
                    break
            if self.state[0] < len(choices):
                # Don't preseed_as_c, because Perl debconf is buggy in that
                # it doesn't expand variables in the result of METAGET
                # choices-c. All locales have the same variables anyway so
                # it doesn't matter.
                self.preseed(question, self.state[1])
                self.succeeded = True
                return True
            else:
                self.state = None

            if self.resize_desc not in self.extra_options:
                try:
                    del choices[choices.index(self.resize_desc)]
                except ValueError:
                    pass
            self.frontend.set_autopartition_choices(
                choices, self.extra_options,
                self.resize_desc, self.manual_desc)

        elif question == 'partman-auto/select_disk':
            if self.state is not None:
                self.extra_options[self.state[1]] = self.choices(question)
                # Back up to autopartitioning question.
                self.succeeded = False
                return False
            else:
                assert self.extra_choice is not None
                self.preseed(question, self.extra_choice)
                self.succeeded = True
                return True

        elif question == 'partman-partitioning/new_size':
            if self.state is not None:
                self.extra_options[self.state[1]] = (self.resize_min_size,
                                                     self.resize_max_size)
                # Back up to autopartitioning question.
                self.succeeded = False
                return False
            else:
                assert self.extra_choice is not None
                self.preseed(question, '%d%%' % self.extra_choice)
                self.succeeded = True
                return True

        elif question.startswith('partman/confirm'):
            if question == 'partman/confirm':
                self.db.set('ubiquity/partman-made-changes', 'true')
            else:
                self.db.set('ubiquity/partman-made-changes', 'false')
            self.preseed(question, 'true')
            self.succeeded = True
            self.done = True
            return True

        elif qtype == 'boolean':
            response = self.frontend.question_dialog(
                self.description(question),
                self.extended_description(question),
                ('ubiquity/text/go_back', 'ubiquity/text/continue'))

            answer_reversed = False
            if (question == 'partman-jfs/jfs_boot' or
                question == 'partman-jfs/jfs_root'):
                answer_reversed = True
            if response is None or response == 'ubiquity/text/continue':
                answer = answer_reversed
            else:
                answer = not answer_reversed
            if answer:
                self.preseed(question, 'true')
            else:
                self.preseed(question, 'false')
            return True

        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        (autopartition_choice, self.extra_choice) = \
            self.frontend.get_autopartition_choice()
        # Don't preseed_as_c, because Perl debconf is buggy in that it
        # doesn't expand variables in the result of METAGET choices-c. All
        # locales have the same variables anyway so it doesn't matter.
        if self.autopartition_question is not None:
            self.preseed(self.autopartition_question, autopartition_choice)
        else:
            self.preseed('partman-auto/init_automatically_partition',
                         autopartition_choice)
            self.preseed('partman-auto/automatically_partition',
                         autopartition_choice)

        if autopartition_choice == self.manual_desc:
            # Back up all the way out.
            self.succeeded = False
            self.done = True
        else:
            self.succeeded = True
            # Don't exit partman yet.
        self.exit_ui_loops()

# Notes:
#
#   partman-auto/init_automatically_partition
#     Resize <partition> and use freed space
#     Erase entire disk: <disk> - <description>
#     Manually edit partition table
#
#   may show multiple disks, in which case massage into disk chooser (later)
#
#   if the resize option shows up, then run os-prober and display at the
#   top?
#
#   resize follow-up question:
#       partman-partitioning/new_size
#   progress bar:
#       partman-partitioning/progress_resizing
#
#   manual editing:
#       partman/choose_partition
#
#   final confirmation:
#       partman/confirm*
