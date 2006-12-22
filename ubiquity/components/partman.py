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

from ubiquity.filteredcommand import FilteredCommand
from ubiquity import parted_server
from ubiquity.components.partman_auto import PartmanAuto

# For now, we inherit from PartmanAuto to avoid code duplication. Once all
# frontends are converted to the all-in-one Partman, or once the complexity
# involved in this inheritance gets too great, the necessary parts of
# PartmanAuto should be moved here.

PARTITION_TYPE_PRIMARY = 0
PARTITION_TYPE_LOGICAL = 1

PARTITION_PLACE_BEGINNING = 0
PARTITION_PLACE_END = 1

class PartmanOptionError(LookupError):
    pass

class Partman(PartmanAuto):
    def prepare(self):
        prep = PartmanAuto.prepare(self)

        # We don't need this weirdness for the all-in-one Partman.
        self.stashed_auto_mountpoints = {}

        self.update_partitions = None
        self.building_cache = True
        self.__state = [['', None, None]]
        self.disk_cache = {}
        self.partition_cache = {}
        self.cache_order = []
        self.creating_partition = None
        self.editing_partition = None
        self.deleting_partition = None
        self.finish_partitioning = False

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

    def find_script(self, menu_options, want_script, want_arg=None):
        scripts = []
        for (script, arg, option) in menu_options:
            if ((want_script is None or script[2:] == want_script) and
                (want_arg is None or arg == want_arg)):
                scripts.append((script, arg, option))
        return scripts

    def must_find_one_script(self, question, menu_options,
                             want_script, want_arg=None):
        for (script, arg, option) in menu_options:
            if ((want_script is None or script[2:] == want_script) and
                (want_arg is None or arg == want_arg)):
                return (script, arg, option)
        else:
            raise PartmanOptionError, ("%s should have %s (%s) option" %
                                       (question, want_script, want_arg))

    def preseed_script(self, question, menu_options,
                       want_script, want_arg=None):
        (script, arg, option) = self.must_find_one_script(
            question, menu_options, want_script, want_arg)
        self.preseed(question, option)

    @classmethod
    def split_devpart(self, devpart):
        dev, part_id = devpart.split('//', 1)
        if dev.startswith(parted_server.devices + '/'):
            dev = dev[len(parted_server.devices) + 1:]
            return dev, part_id
        else:
            return None, None

    @classmethod
    def subdirectories(self, directory):
        for name in sorted(os.listdir(directory)):
            if os.path.isdir(os.path.join(directory, name)):
                yield name[2:]

    @classmethod
    def scripts(self, directory):
        for name in sorted(os.listdir(directory)):
            if os.access(os.path.join(directory, name), os.X_OK):
                yield name[2:]

    @classmethod
    def create_use_as(self):
        """Yields the possible methods that a new partition may use."""

        # TODO cjwatson 2006-11-01: This is a particular pain; we can't find
        # out the real list of possible uses from partman until after the
        # partition has been created, so we have to partially hardcode this.
        # TODO cjwatson 2006-11-01: Get human-readable names.

        for method in self.subdirectories('/lib/partman/choose_method'):
            if method == 'filesystem':
                for fs in self.scripts('/lib/partman/valid_filesystems'):
                    if fs == 'ntfs':
                        continue
                    yield fs
            else:
                yield method

    def get_current_method(self, partition):
        if 'method' in partition:
            if partition['method'] in ('format', 'keep'):
                if 'filesystem' in partition:
                    return partition['filesystem']
                else:
                    return None
            else:
                return partition['method']
        else:
            return 'dont_use'

    def set(self, question, value):
        if question == 'ubiquity/partman-rebuild-cache':
            if not self.building_cache:
                self.debug('Partman: Partition %s updated', value)
                if self.update_partitions is None:
                    self.update_partitions = []
                if value not in self.update_partitions:
                    self.update_partitions.append(value)
            self.debug('Partman: update_partitions = %s',
                       self.update_partitions)

    def run(self, priority, question):
        self.current_question = question
        options = self.snoop()
        menu_options = self.snoop_menu(options)
        self.debug('Partman: state = %s', self.__state)

        if question == 'partman/choose_partition':
            if not self.building_cache and self.update_partitions:
                # Rebuild our cache of just these partitions.
                self.__state = [['', None, None]]
                self.building_cache = True

            if self.building_cache:
                state = self.__state[-1]
                if state[0] == question:
                    # advance to next partition
                    self.frontend.debconf_progress_step(1)
                    self.frontend.refresh()
                    self.debug('Partman: update_partitions = %s',
                               self.update_partitions)
                    state[1] = None
                    while self.update_partitions:
                        state[1] = self.update_partitions[0]
                        del self.update_partitions[0]
                        if state[1] not in self.partition_cache:
                            self.debug('Partman: %s not found in cache',
                                       partition)
                            state[1] = None
                            self.frontend.debconf_progress_step(1)
                            self.frontend.refresh()
                        else:
                            break

                    if state[1] is not None:
                        # Move on to the next partition.
                        partition = self.partition_cache[state[1]]
                        self.debug('Partman: Building cache (%s)',
                                   partition['parted']['path'])
                        self.preseed(question, partition['display'],
                                     escape=True)
                        return True
                    else:
                        # Finished building the cache.
                        self.debug('Partman: Finished building cache')
                        self.__state.pop()
                        self.update_partitions = None
                        self.building_cache = False
                        self.frontend.debconf_progress_stop()
                        self.frontend.refresh()
                        self.frontend.update_partman(
                            self.disk_cache, self.partition_cache,
                            self.cache_order)
                else:
                    self.debug('Partman: Building cache')
                    parted = parted_server.PartedServer()
                    matches = self.find_script(menu_options, 'partition_tree')

                    # If we're only updating our cache for certain
                    # partitions, then self.update_partitions will be a list
                    # of the partitions to update; otherwise, we build the
                    # cache from scratch.
                    rebuild_all = self.update_partitions is None

                    if rebuild_all:
                        self.disk_cache = {}
                        self.partition_cache = {}
                    self.cache_order = []

                    # Clear out the partitions we're updating to make sure
                    # stale keys are removed.
                    if self.update_partitions is not None:
                        for devpart in self.update_partitions:
                            if devpart in self.partition_cache:
                                del self.partition_cache[devpart]

                    # Initialise any items we haven't heard of yet.
                    for script, arg, option in matches:
                        dev, part_id = self.split_devpart(arg)
                        if not dev:
                            continue
                        parted.select_disk(dev)
                        self.cache_order.append(arg)
                        if part_id:
                            if rebuild_all or arg not in self.partition_cache:
                                self.partition_cache[arg] = {
                                    'dev': dev,
                                    'id': part_id
                                }
                        else:
                            if rebuild_all or arg not in self.disk_cache:
                                device = parted.readline_device_entry('device')
                                self.disk_cache[arg] = {
                                    'dev': dev,
                                    'device': device
                                }

                    if self.update_partitions is None:
                        self.update_partitions = self.partition_cache.keys()
                    else:
                        self.update_partitions = [devpart
                            for devpart in self.update_partitions
                            if devpart in self.partition_cache]

                    # Update the display names of all disks and partitions.
                    for script, arg, option in matches:
                        dev, part_id = self.split_devpart(arg)
                        if not dev:
                            continue
                        parted.select_disk(dev)
                        if part_id:
                            self.partition_cache[arg]['display'] = option
                        else:
                            self.disk_cache[arg]['display'] = option

                    # Get basic information from parted_server for each
                    # partition being updated.
                    for devpart in self.update_partitions:
                        dev, part_id = self.split_devpart(devpart)
                        if not dev:
                            continue
                        parted.select_disk(dev)
                        info = parted.partition_info(part_id)
                        self.partition_cache[devpart]['parted'] = {
                            'num': info[0],
                            'id': info[1],
                            'size': info[2],
                            'type': info[3],
                            'fs': info[4],
                            'path': info[5],
                            'name': info[6]
                        }

                    self.frontend.debconf_progress_start(
                        0, len(self.update_partitions),
                        self.description('partman/progress/init/parted'))
                    self.frontend.refresh()
                    self.debug('Partman: update_partitions = %s',
                               self.update_partitions)

                    # Selecting a disk will ask to create a new disklabel,
                    # so don't bother with that.

                    devpart = None
                    if self.partition_cache:
                        while self.update_partitions:
                            devpart = self.update_partitions[0]
                            del self.update_partitions[0]
                            if devpart not in self.partition_cache:
                                self.debug('Partman: %s not found in cache',
                                           partition)
                                devpart = None
                                self.frontend.debconf_progress_step(1)
                                self.frontend.refresh()
                            else:
                                break
                    if devpart is not None:
                        partition = self.partition_cache[devpart]
                        self.debug('Partman: Building cache (%s)',
                                   partition['parted']['path'])
                        self.__state.append([question, devpart, None])
                        self.preseed(question, partition['display'],
                                     escape=True)
                        return True
                    else:
                        self.debug('Partman: Finished building cache '
                                   '(no partitions to update)')
                        self.update_partitions = None
                        self.building_cache = False
                        self.frontend.debconf_progress_stop()
                        self.frontend.refresh()
                        self.frontend.update_partman(
                            self.disk_cache, self.partition_cache,
                            self.cache_order)
            elif self.creating_partition:
                devpart = self.creating_partition['devpart']
                if devpart in self.partition_cache:
                    self.frontend.update_partman(
                        self.disk_cache, self.partition_cache,
                        self.cache_order)
            elif self.editing_partition:
                devpart = self.editing_partition['devpart']
                if devpart in self.partition_cache:
                    self.frontend.update_partman(
                        self.disk_cache, self.partition_cache,
                        self.cache_order)
            elif self.deleting_partition:
                raise AssertionError, "Deleting partition didn't rebuild cache?"

            if self.debug_enabled():
                import pprint
                self.debug('disk_cache:')
                printer = pprint.PrettyPrinter()
                for line in printer.pformat(self.disk_cache).split('\n'):
                    self.debug('%s', line)
                self.debug('disk_cache end')
                self.debug('partition_cache:')
                printer = pprint.PrettyPrinter()
                for line in printer.pformat(self.partition_cache).split('\n'):
                    self.debug('%s', line)
                self.debug('partition_cache end')

            self.__state = [['', None, None]]
            self.creating_partition = None
            self.editing_partition = None
            self.deleting_partition = None
            self.finish_partitioning = False

            FilteredCommand.run(self, priority, question)

            if self.finish_partitioning or self.done:
                if self.succeeded:
                    self.preseed_script(question, menu_options, 'finish')
                return self.succeeded

            elif self.creating_partition:
                devpart = self.creating_partition['devpart']
                if devpart in self.partition_cache:
                    partition = self.partition_cache[devpart]
                    self.__state.append([question, devpart, None])
                    self.preseed(question, partition['display'], escape=True)
                return True

            elif self.editing_partition:
                devpart = self.editing_partition['devpart']
                if devpart in self.partition_cache:
                    partition = self.partition_cache[devpart]
                    self.__state.append([question, devpart, None])
                    self.preseed(question, partition['display'], escape=True)
                return True

            elif self.deleting_partition:
                devpart = self.deleting_partition['devpart']
                if devpart in self.partition_cache:
                    partition = self.partition_cache[devpart]
                    # No need to use self.__state to keep track of this.
                    self.preseed(question, partition['display'], escape=True)
                return True

            else:
                raise AssertionError, ("Returned to %s with nothing to do" %
                                       question)

        elif question == 'partman/free_space':
            if self.building_cache:
                state = self.__state[-1]
                assert state[0] == 'partman/choose_partition'
                partition = self.partition_cache[state[1]]
                can_new = False
                if self.find_script(menu_options, 'new'):
                    can_new = True
                partition['can_new'] = can_new
                # Back up to the previous menu.
                return False
            elif self.creating_partition:
                self.preseed_script(question, menu_options, 'new')
                return True
            else:
                raise AssertionError, "Arrived at %s unexpectedly" % question

        elif question == 'partman-partitioning/new_partition_size':
            # TODO cjwatson 2006-08-03: handle error
            # (partman-partitioning/bad_new_partition_size)
            if self.creating_partition:
                self.preseed(question, self.creating_partition['size'])
                return True
            else:
                raise AssertionError, "Arrived at %s unexpectedly" % question

        elif question == 'partman-partitioning/new_partition_type':
            if self.creating_partition:
                if self.creating_partition['type'] == PARTITION_TYPE_PRIMARY:
                    self.preseed(question, 'Primary')
                else:
                    self.preseed(question, 'Logical')
                return True
            else:
                raise AssertionError, "Arrived at %s unexpectedly" % question

        elif question == 'partman-partitioning/new_partition_place':
            if self.creating_partition:
                if (self.creating_partition['place'] ==
                    PARTITION_PLACE_BEGINNING):
                    self.preseed(question, 'Beginning')
                else:
                    self.preseed(question, 'End')
                return True
            else:
                raise AssertionError, "Arrived at %s unexpectedly" % question

        elif question == 'partman/active_partition':
            if self.building_cache:
                state = self.__state[-1]
                partition = self.partition_cache[state[1]]

                if state[0] == question:
                    state[2] += 1
                    if state[2] < len(partition['active_partition_visit']):
                        # Move on to the next item.
                        visit = partition['active_partition_visit']
                        self.preseed(question, visit[state[2]][2], escape=True)
                        return True
                    else:
                        # Finished building the cache for this submenu; go
                        # back to the previous one.
                        del partition['active_partition_visit']
                        self.__state.pop()
                        return False

                assert state[0] == 'partman/choose_partition'
                parted = parted_server.PartedServer()

                parted.select_disk(partition['dev'])
                for entry in ('method',
                              'filesystem', 'detected_filesystem',
                              'acting_filesystem',
                              'existing', 'formatable',
                              'mountpoint'):
                    if parted.has_part_entry(partition['id'], entry):
                        partition[entry] = \
                            parted.readline_part_entry(partition['id'], entry)

                visit = []
                for (script, arg, option) in menu_options:
                    if arg in ('method', 'mountpoint'):
                        visit.append((script, arg, option))
                    elif arg == 'format':
                        partition['can_activate_format'] = True
                    elif arg == 'resize':
                        partition['can_resize'] = True
                if visit:
                    partition['active_partition_visit'] = visit
                    self.__state.append([question, state[1], 0])
                    self.preseed(question, visit[0][2], escape=True)
                    return True
                else:
                    # Back up to the previous menu.
                    return False

            elif self.creating_partition or self.editing_partition:
                if self.creating_partition:
                    request = self.creating_partition
                else:
                    request = self.editing_partition

                state = self.__state[-1]
                partition = self.partition_cache[state[1]]

                if state[0] == question:
                    state[2] += 1
                    if state[2] < len(partition['active_partition_visit']):
                        # Move on to the next item.
                        visit = partition['active_partition_visit']
                        self.preseed(question, visit[state[2]][2], escape=True)
                        return True
                    else:
                        # Finish editing this partition.
                        del partition['active_partition_visit']
                        self.__state.pop()
                        self.preseed_script(question, menu_options, 'finish')
                        return True

                visit = []
                for item in ('method', 'mountpoint', 'format'):
                    if item not in request or request[item] is None:
                        continue
                    scripts = self.find_script(menu_options, None, item)
                    if scripts:
                        visit.append(scripts[0])
                if visit:
                    partition['active_partition_visit'] = visit
                    self.__state.append([question, state[1], 0])
                    self.preseed(question, visit[0][2], escape=True)
                    return True
                else:
                    # Finish editing this partition.
                    del partition['active_partition_visit']
                    self.__state.pop()
                    self.preseed_script(question, menu_options, 'finish')
                    return True

            elif self.deleting_partition:
                self.preseed_script(question, menu_options, 'delete')
                self.deleting_partition = None
                return True

            else:
                raise AssertionError, "Arrived at %s unexpectedly" % question

        elif question == 'partman-target/choose_method':
            if self.building_cache:
                state = self.__state[-1]
                assert state[0] == 'partman/active_partition'
                partition = self.partition_cache[state[1]]
                partition['method_choices'] = []
                for (script, arg, option) in menu_options:
                    partition['method_choices'].append((script, arg, option))
                # Back up to the previous menu.
                return False
            elif self.creating_partition or self.editing_partition:
                if self.creating_partition:
                    request = self.creating_partition
                else:
                    request = self.editing_partition

                self.preseed_script(question, menu_options,
                                    None, request['method'])
                return True
            else:
                raise AssertionError, "Arrived at %s unexpectedly" % question

        elif question in ('partman-basicfilesystems/mountpoint',
                          'partman-basicfilesystems/fat_mountpoint'):
            if self.building_cache:
                state = self.__state[-1]
                assert state[0] == 'partman/active_partition'
                partition = self.partition_cache[state[1]]
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
            if self.creating_partition or self.editing_partition:
                if self.creating_partition:
                    request = self.creating_partition
                else:
                    request = self.editing_partition

                self.preseed(question, request['mountpoint'])
                return True
            else:
                raise AssertionError, "Arrived at %s unexpectedly" % question

        return PartmanAuto.run(self, priority, question)

    def ok_handler(self):
        if self.current_question.endswith('automatically_partition'):
            PartmanAuto.ok_handler(self)
            if self.frontend.get_autopartition_choice()[0] == self.manual_desc:
                # In the all-in-one Partman, we keep on going in this case.
                self.succeeded = True
                self.done = False
        else:
            self.succeeded = True
            self.finish_partitioning = True
            self.exit_ui_loops()

    # TODO cjwatson 2006-11-01: Do we still need this?
    def rebuild_cache(self):
        assert self.current_question == 'partman/choose_partition'
        self.building_cache = True

    def create_partition(self, devpart, size, prilog, place,
                         method=None, mountpoint=None):
        assert self.current_question == 'partman/choose_partition'
        self.creating_partition = {
            'devpart': devpart,
            'size': size,
            'type': prilog,
            'place': place,
            'method': method,
            'mountpoint': mountpoint
        }
        self.exit_ui_loops()

    def edit_partition(self, devpart,
                       method=None, mountpoint=None, format=None):
        assert self.current_question == 'partman/choose_partition'
        self.editing_partition = {
            'devpart': devpart,
            'method': method,
            'mountpoint': mountpoint,
            'format': format
        }
        self.exit_ui_loops()

    def delete_partition(self, devpart):
        assert self.current_question == 'partman/choose_partition'
        self.deleting_partition = {
            'devpart': devpart
        }
        self.exit_ui_loops()
