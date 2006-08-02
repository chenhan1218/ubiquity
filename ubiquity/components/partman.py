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

from ubiquity.filteredcommand import FilteredCommand
from ubiquity import parted_server
from ubiquity.components.partman_auto import PartmanAuto

# For now, we inherit from PartmanAuto to avoid code duplication. Once all
# frontends are converted to the all-in-one Partman, or once the complexity
# involved in this inheritance gets too great, the necessary parts of
# PartmanAuto should be moved here.

class Partman(PartmanAuto):
    def prepare(self):
        prep = super(Partman, self).prepare()

        # We don't need this weirdness for the all-in-one Partman.
        self.stashed_auto_mountpoints = {}

        self.building_cache = True
        self.build_cache_state = [['', '']]
        self.disk_cache = []
        self.partition_cache = []

        questions = list(prep[1])
        questions.extend(['^partman/free_space$',
                          '^partman/active_partition$',
                          '^partman-partitioning/new_partition_(size|type|place)$',
                          '^partman-target/choose_method$',
                          '^partman-basicfilesystems/(fat_mountpoint|mountpoint|mountpoint_manual)$'])
        prep = list(prep)
        prep[1] = questions
        return prep

    def snoop(self):
        """Read the partman snoop file hack, returning a list of tuples
        mapping from keys to displayed options. (We use a list of tuples
        because this preserves ordering and is reasonably fast to convert to
        a dictionary.)"""

        try:
            snoop = open('/var/lib/partman/snoop')
            options = []
            for line in snoop:
                line = unicode(line.rstrip('\n'), 'utf-8', 'replace')
                fields = line.split('\t', 1)
                if len(fields) == 2:
                    (key, option) = fields
                    options.append((key, option))
                    continue
            snoop.close()
            return options
        except IOError:
            return {}

    def snoop_menu(self, options):
        """Parse the raw snoop data into script, argument, and displayed
        name, as used by ask_user."""

        menu_options = []
        for (key, option) in options:
            keybits = key.split('__________', 1)
            if len(keybits) == 2:
                (script, arg) = keybits
                menu_options.append((script, arg, option))
        return menu_options

    def run(self, priority, question):
        self.current_question = question
        options = self.snoop()
        menu_options = self.snoop_menu(options)

        if question == 'partman/choose_partition':
            if self.building_cache:
                state = self.build_cache_state[-1]
                if state[0] == question:
                    state[1] += 1
                    if state[1] < len(self.partition_cache):
                        # Move on to the next partition.
                        partition = self.partition_cache[state[1]][1]
                        self.preseed(question, partition['display'],
                                     escape=True)
                        return True
                    else:
                        # Finished building the cache.
                        self.build_cache_state.pop()
                        self.building_cache = False
                else:
                    self.disk_cache = []
                    self.partition_cache = []
                    parted = parted_server.PartedServer()

                    for (script, arg, option) in menu_options:
                        if script[2:] == 'partition_tree':
                            (dev, part_id) = arg.split('//', 1)
                            if dev.startswith(parted_server.devices + '/'):
                                dev = dev[len(parted_server.devices) + 1:]
                            else:
                                continue
                            parted.select_disk(dev)
                            if part_id:
                                self.partition_cache.append((arg, {
                                    'dev': dev,
                                    'id': part_id,
                                    'display': option,
                                    'parted': parted.partition_info(part_id)
                                }))
                            else:
                                self.disk_cache.append((arg, {
                                    'dev': dev,
                                    'display': option,
                                    'device': parted.readline_device_entry('device')
                                }))

                    # Selecting a disk will ask to create a new disklabel,
                    # so don't bother with that.

                    if self.partition_cache:
                        self.build_cache_state.append([question, 0])
                        self.preseed(question,
                                     self.partition_cache[0][1]['display'],
                                     escape=True)
                        return True
                    else:
                        self.building_cache = False

            self.debug('partition_cache: %s', str(self.partition_cache))
            import sys
            sys.exit(1)

            # TODO cjwatson 2006-07-27: wait for user input

        elif question == 'partman/free_space':
            if self.building_cache:
                state = self.build_cache_state[-1]
                assert state[0] == 'partman/choose_partition'
                partition = self.partition_cache[state[1]][1]
                can_new = False
                for (script, arg, option) in menu_options:
                    if script[2:] == 'new':
                        can_new = True
                        break
                partition['can_new'] = can_new
                # Back up to the previous menu.
                return False
            else:
                # TODO cjwatson 2006-08-02: presumably we're being told to
                # create a partition here; do so
                pass

        elif question == 'partman/active_partition':
            if self.building_cache:
                state = self.build_cache_state[-1]
                partition = self.partition_cache[state[1]][1]

                if state[0] == question:
                    state[1] += 1
                    if state[1] < len(partition['active_partition_visit']):
                        # Move on to the next item.
                        self.preseed(question, visit[state[1]][2], escape=True)
                        return True
                    else:
                        # Finished building the cache for this submenu; go
                        # back to the previous one.
                        del partition['active_partition_visit']
                        self.build_cache_state.pop()
                        return False

                assert state[0] == 'partman/choose_partition'
                parted = parted_server.PartedServer()

                parted.select_disk(partition['dev'])
                for entry in ('method', 'detected_filesystem',
                              'acting_filesystem'):
                    if parted.has_part_entry(partition['id'], entry):
                        partition[entry] = \
                            parted.readline_part_entry(partition['id'], entry)

                visit = []
                for (script, arg, option) in menu_options:
                    if arg in ('method', 'mountpoint'):
                        visit.append((script, arg, option))
                if visit:
                    partition['active_partition_visit'] = visit
                    self.build_cache_state.append([question, 0])
                    self.preseed(question, visit[0][2], escape=True)
                    return True
                else:
                    # Back up to the previous menu.
                    return False

            else:
                # TODO cjwatson 2006-08-02: presumably we're planning to do
                # something in a submenu, so do that
                pass

        elif question == 'partman-partitioning/new_partition_size':
            # TODO cjwatson 2006-08-02: fill in user-requested size
            pass

        elif question == 'partman-partitioning/new_partition_type':
            # TODO cjwatson 2006-08-02: fill in user-requested type
            pass

        elif question == 'partman-partitioning/new_partition_place':
            # TODO cjwatson 2006-08-02: fill in user-requested place
            pass

        elif question == 'partman-target/choose_method':
            if self.building_cache:
                state = self.build_cache_state[-1]
                assert state[0] == 'partman/active_partition'
                partition = self.partition_cache[state[1]][1]
                partition['method_choices'] = []
                for (script, arg, option) in menu_options:
                    partition['method_choices'].append((script, arg, option))
                # Back up to the previous menu.
                return False
            else:
                # TODO cjwatson 2006-08-02: fill in user-requested method
                pass

        elif question in ('partman-basicfilesystems/mountpoint',
                          'partman-basicfilesystems/fat_mountpoint'):
            # TODO cjwatson 2006-08-02: if building cache, get choices
            # (excluding "Enter manually" and "Do not mount it" at least),
            # fill into cache, back up; otherwise, fill in user-requested
            # mountpoint
            if self.building_cache:
                state = self.build_cache_state[-1]
                assert state[0] == 'partman/active_partition'
                partition = self.partition_cache[state[1]][1]
                partition['mountpoint_choices'] = []
                choices_c = self.choices_untranslated(question)
                choices = self.choices(question)
                assert len(choices_c) == len(choices)
                for i in range(len(choices_c)):
                    if choices_c[i].startswith('/'):
                        partition['mountpoint_choices'].append((
                            choices_c[i].split(' ')[0],
                            choices_c[i], choices[i]))
                # Back up to the previous menu.
                return False
            else:
                self.preseed(question, 'Enter manually')
                return True

        elif question == 'partman-basicfilesystems/mountpoint_manual':
            # TODO cjwatson 2006-08-02: fill in user-requested mountpoint
            pass

        return super(Partman, self).run(priority, question)

    def ok_handler(self):
        super(Partman, self).ok_handler()
        if (self.current_question.endswith('automatically_partition') or
            self.current_question == 'partman-partitioning/new_size'):
            if self.frontend.get_autopartition_choice() == self.manual_desc:
                # In the all-in-one Partman, we keep on going in this case.
                self.succeeded = True
                self.done = False

    def rebuild_cache(self):
        assert self.current_question == 'partman/choose_partition'
        self.building_cache = True
