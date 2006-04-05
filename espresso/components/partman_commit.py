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

from espresso.filteredcommand import FilteredCommand
from espresso.parted_server import PartedServer
from espresso.components.partman import Partman

class PartmanCommit(Partman):
    def prepare(self):
        # Make sure autopartitioning doesn't get run. We rely on the manual
        # partitioning control path.
        questions = ['^partman/choose_partition$',
                     '^partman/confirm.*',
                     'ERROR',
                     'PROGRESS']
        return ('/bin/partman', questions)

    def run(self, priority, question):
        if question == 'partman/choose_partition':
            if self.done:
                # user said no to confirmation question
                return False

            partitions = {}
            parted = PartedServer()
            for disk in parted.disks():
                parted.select_disk(disk)
                for part in parted.partitions():
                    (p_num, p_id, p_size, p_type, p_fs, p_path, p_name) = part
                    partitions[p_path] = (disk, p_id)

            mountpoints = self.frontend.get_mountpoints()
            for device, (path, format, fstype) in mountpoints.items():
                if device in partitions:
                    (disk, p_id) = partitions[device]
                    parted.select_disk(disk)
                    if path == 'swap':
                        parted.write_part_entry(p_id, 'method', 'swap\n')
                        if format:
                            parted.write_part_entry(p_id, 'format', '')
                        else:
                            parted.remove_part_entry(p_id, 'format')
                        parted.remove_part_entry(p_id, 'use_filesystem')
                    else:
                        detected = parted.has_part_entry(
                            p_id, 'detected_filesystem')
                        if fstype is None:
                            if detected:
                                fstype = parted.readline_part_entry(
                                    p_id, 'detected_filesystem')
                            else:
                                fstype = 'ext3'

                        if format or not detected:
                            parted.write_part_entry(p_id, 'method', 'format\n')
                            parted.write_part_entry(p_id, 'format', '')
                            parted.write_part_entry(p_id, 'filesystem', fstype)
                            parted.remove_part_entry(p_id, 'options')
                            parted.mkdir_part_entry(p_id, 'options')
                        else:
                            parted.write_part_entry(p_id, 'method', 'keep\n')
                            parted.remove_part_entry(p_id, 'format')
                            parted.write_part_entry(
                                p_id, 'detected_filesystem', fstype)
                        parted.write_part_entry(p_id, 'use_filesystem', '')
                        parted.write_part_entry(p_id, 'mountpoint', path)
                    parted.update_partition(p_id)

            # Don't preseed_as_c, because Perl debconf is buggy in that it
            # doesn't expand variables in the result of METAGET choices-c.
            # All locales have the same variables anyway so it doesn't
            # matter.
            self.preseed('partman/choose_partition',
                         self.description('partman/text/end_the_partitioning'))
            self.current_question = question
            return True

        elif question.startswith('partman/confirm'):
            self.current_question = question
            if self.frontend.confirm_partitioning_dialog(
                    self.description(question), self.confirmation_message()):
                self.preseed(question, 'true')
            else:
                self.preseed(question, 'false')
            self.done = True
            return True

        else:
            return super(Partman, self).run(priority, question)

    # Partman's ok_handler isn't appropriate here.
    def ok_handler(self):
        return super(Partman, self).ok_handler()
