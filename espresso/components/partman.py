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
import signal
import textwrap
from espresso.filteredcommand import FilteredCommand
from espresso.parted_server import PartedServer

class Partman(FilteredCommand):
    def __init__(self, frontend=None):
        super(Partman, self).__init__(frontend)
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
        if os.path.exists('/var/lib/partman/initial_auto'):
            os.unlink('/var/lib/partman/initial_auto')

        self.resize_min_percent = 0
        self.manual_partitioning = False

        questions = ['^partman-auto/disk$',
                     '^partman-auto/.*automatically_partition$',
                     '^partman-partitioning/new_size$',
                     '^partman/choose_partition$',
                     '^partman/confirm.*',
                     'ERROR',
                     'PROGRESS']
        return ('/bin/partman', questions)

    def error(self, priority, question):
        self.frontend.error_dialog(self.description(question))
        return super(Partman, self).error(priority, question)

    def subst(self, question, key, value):
        if question == 'partman-partitioning/new_size':
            if key == 'PERCENT':
                self.frontend.set_autopartition_resize_min_percent(
                    int(value.rstrip('%')))

    # partman relies on multi-line SUBSTs to construct the confirmation
    # message, which have no way to work in debconf (and, as far as I can
    # tell, only work in cdebconf by dumb luck). Furthermore, debconf
    # truncates multi-line METAGET returns to the first line, so we can't
    # get hold of the extended description anyway. This could politely be
    # described as a total mess.
    #
    # Thus, we have to construct a confirmation message ourselves.
    def confirmation_message(self):
        # TODO: untranslatable
        message = textwrap.dedent("""\
        If you continue, the changes listed below will be written to the disks. Otherwise, you will be able to make further changes manually.

        WARNING: This will destroy all data on any partitions you have removed as well as on the partitions that are going to be formatted.

        """)

        items = []
        parted = PartedServer()
        for disk in parted.disks():
            parted.select_disk(disk)
            for part in parted.partitions():
                (p_num, p_id, p_size, p_type, p_fs, p_path, p_name) = part
                if p_fs == 'free':
                    continue

                if not parted.has_part_entry(p_id, 'method'):
                    continue
                if not parted.has_part_entry(p_id, 'format'):
                    continue
                if not parted.has_part_entry(p_id, 'visual_filesystem'):
                    continue
                # If no filesystem (e.g. swap), then we will format it if
                # either (a) it is unformatted or (b) it was formatted
                # before the method was specified.
                if (not parted.has_part_entry(p_id, 'filesystem')):
                    if not parted.has_part_entry(p_id, 'formatted'):
                        pass
                    else:
                        formatted_mtime = os.path.getmtime(
                            parted.part_entry(p_id, 'formatted'))
                        method_mtime = os.path.getmtime(
                            parted.part_entry(p_id, 'method'))
                        if formatted_mtime >= method_mtime:
                            continue
                # If the partition was already formatted, then we will
                # reformat it if it was formatted before the method or
                # filesystem was specified.
                if (parted.has_part_entry(p_id, 'filesystem') and
                    parted.has_part_entry(p_id, 'formatted')):
                    formatted_mtime = os.path.getmtime(
                        parted.part_entry(p_id, 'formatted'))
                    method_mtime = os.path.getmtime(
                        parted.part_entry(p_id, 'method'))
                    filesystem_mtime = os.path.getmtime(
                        parted.part_entry(p_id, 'filesystem'))
                    if (formatted_mtime >= method_mtime and
                        formatted_mtime >= filesystem_mtime):
                        continue
                filesystem = parted.readline_part_entry(
                    p_id, 'visual_filesystem')
                self.db.subst('partman/text/confirm_item', 'TYPE', filesystem)
                self.db.subst('partman/text/confirm_item', 'PARTITION', p_num)
                # TODO: humandev
                device = parted.readline_device_entry('device')
                self.db.subst('partman/text/confirm_item', 'DEVICE', device)
                items.append(self.description('partman/text/confirm_item'))

        # TODO: need to show which partition tables have changed as well

        if len(items) > 0:
            message += self.description('partman/text/confirm_item_header')
            for item in items:
                message += '\n   ' + item

        return message

    def run(self, priority, question):
        if self.done:
            # user answered confirmation question or selected manual
            # partitioning
            if self.manual_partitioning:
                return False
            else:
                return self.succeeded

        self.current_question = question

        if question == 'partman-auto/disk':
            self.manual_desc = \
                self.description('partman-auto/text/custom_partitioning')
            if not self.frontend.set_disk_choices(self.choices(question),
                                                  self.manual_desc):
                # disk selector not implemented; just use first disk
                return True

        elif question.endswith('automatically_partition'):
            self.resize_desc = \
                self.description('partman-auto/text/resize_use_free')
            self.manual_desc = \
                self.description('partman-auto/text/custom_partitioning')
            self.frontend.set_autopartition_choices(
                self.choices(question), self.resize_desc, self.manual_desc)

        elif question == 'partman-partitioning/new_size':
            # We have to wait for partman to ask this rather than preseeding
            # it in advance, since partman sets it before asking it.
            percent = self.frontend.get_autopartition_resize_percent()
            self.preseed('partman-partitioning/new_size', '%d%%' % percent)

        elif question.startswith('partman/confirm'):
            if self.frontend.confirm_partitioning_dialog(
                    self.description(question), self.confirmation_message()):
                self.preseed(question, 'true')
                self.succeeded = True
            else:
                self.preseed(question, 'false')
                self.succeeded = False
            self.done = True
            return True

        # We have some odd control flow here, so make sure we always return
        # True until the user leaves the autopartitioning screen.
        super(Partman, self).run(priority, question)
        if self.manual_partitioning:
            return False
        else:
            return True

    def ok_handler(self):
        if self.current_question == 'partman-auto/disk':
            disk_choice = self.frontend.get_disk_choice()
            # Don't preseed_as_c, because Perl debconf is buggy in that it
            # doesn't expand variables in the result of METAGET choices-c.
            # All locales have the same variables anyway so it doesn't
            # matter.
            if disk_choice is not None:
                self.preseed(self.current_question, disk_choice)
                if disk_choice == self.manual_desc:
                    self.manual_partitioning = True
                else:
                    # don't exit partman yet
                    self.exit_ui_loops()
                    return

        elif self.current_question.endswith('automatically_partition'):
            autopartition_choice = self.frontend.get_autopartition_choice()
            # Don't preseed_as_c, because Perl debconf is buggy in that it
            # doesn't expand variables in the result of METAGET choices-c.
            # All locales have the same variables anyway so it doesn't
            # matter.
            self.preseed(self.current_question, autopartition_choice)
            if autopartition_choice == self.manual_desc:
                self.manual_partitioning = True
            else:
                # don't exit partman yet
                self.exit_ui_loops()
                return

        super(Partman, self).ok_handler()

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
