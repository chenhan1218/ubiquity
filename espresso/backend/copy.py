#!/usr/bin/python
# -*- coding: utf-8 -*-

# Last modified by A. Olmo on 4 oct 2005.

import os
import subprocess
import time
from espresso import misc
from sys import stderr

class Copy:

    def __init__(self, mountpoints):
        """Initial attributes."""

        if os.path.isdir('/rofs'):
            self.source = '/rofs'
        else:
            self.source = '/source'
        self.target = '/target'
        self.mountpoints = mountpoints
        self.unionfs = False

  def run(self, queue):
        """Run the copy stage. This is the second step from the installation
        process."""

        if self.source == '/source':
            queue.put('4 Finding the distribution to copy')
            misc.pre_log('info', 'Mounting source')
            if self.mount_source():
                misc.pre_log('info', 'Mounted source')
            else:
                misc.pre_log('error', 'Mounting source')
                return False

        queue.put('6 Preparing to copy files to disk')
        misc.pre_log('info', 'Copying distro')
        if self.copy_all(queue):
            misc.pre_log('info', 'Copied distro')
        else:
            misc.pre_log('error', 'Copying distro')
            return False

        queue.put('91 Copying installation logs')
        misc.pre_log('info', 'Copying log files')
        if self.copy_logs():
            misc.post_log('info', 'Copied log files')
        else:
            misc.pre_log('error', 'Copying log files')
            return False

        if self.source == '/source':
            queue.put('93 Unmounting original file system image')
            misc.post_log('info', 'Umounting source')
            if self.umount_source():
                misc.post_log('info', 'Umounted source')
            else:
                misc.post_log('error', 'Umounting source')
                return False


    def umount_target(self):
        """umounting selected partitions."""

        ordered_list = []
        for device, path in self.mountpoints.items():
            if path in ('swap',):
                    continue

            path = os.path.join(self.target, path[1:])
            ordered_list.append((len(path), device, path))

        ordered_list.reverse()
        for length, device, path in ordered_list:
            try:
                misc.ex('umount', '-f', os.path.join(self.target, path))
            except Exception, e:
                print e
        return True

    def copy_all(self, queue):
        """Core copy process. This is the most important step of this
        stage. It clones live filesystem into a local partition in the
        selected hard disk."""

        files = []
        total_size = 0
        oldsourcepath = ''

        misc.pre_log('info','Recollecting files to copy')
        for dirpath, dirnames, filenames in os.walk(self.source):
            sourcepath = dirpath[len(self.source)+1:]
            if oldsourcepath.split('/')[0] != sourcepath.split('/')[0]:
                if sourcepath.startswith('etc'):
                    queue.put( '7 Scanning /etc' )
                elif sourcepath.startswith('home'):
                    queue.put( '8 Scanning /home' )
                elif sourcepath.startswith('media'):
                    queue.put( '10 Scanning /media' )
                elif sourcepath.startswith('usr/doc'):
                    queue.put( '11 Scanning /usr/doc' )
                elif sourcepath.startswith('usr/local'):
                    queue.put( '13 Scanning /usr/local' )
                elif sourcepath.startswith('usr/src'):
                    queue.put( '15 Scanning /usr/src' )
                elif sourcepath.startswith('var/backups'):
                    queue.put( '16 Scanning /var/backups' )
                elif sourcepath.startswith('var/tmp'):
                    queue.put( '17 Scanning /var/tmp' )
                oldsourcepath = sourcepath


            for name in dirnames + filenames:
                relpath = os.path.join(sourcepath, name)
                fqpath = os.path.join(self.source, dirpath, name)

                if os.path.isfile(fqpath):
                    size = os.path.getsize(fqpath)
                    total_size += size
                    files.append((relpath, size))
                else:
                    files.append((relpath, None))

        misc.pre_log('info','About to start copying')

        copy = subprocess.Popen(['cpio', '-d0mp', '--quiet', self.target],
                cwd = self.source,
                stdin = subprocess.PIPE)

        copied_bytes, counter = 0, 0
        for path, size in files:
            copy.stdin.write(path + '\0')
            misc.pre_log('info', path)
            if size is not None:
                copied_bytes += size
            per = (copied_bytes * 100) / total_size
            # Adjusting the percentage
            per = (per*73/100)+17
            if counter != per and per < 34:
                # We start the counter until 33
                time_start = time.time()
                counter = per
                queue.put("%s Copying files" % per)
            elif counter != per and per >= 40:
                counter = per
                time_left = (time.time() - time_start) * 57 / (counter - 33) - (time.time() - time_start)
                minutes = time_left / 60
                seconds = time_left - int(time_left/60)*60
                queue.put("%s Copying files - %02d:%02d remaining" % (per, minutes, seconds))
            elif counter != per:
                counter = per
                queue.put("%s Copying files" % per)

        copy.stdin.close()
        copy.wait()

        return True


    def copy_logs(self):
        """copy log files into installed system."""

        log_file = '/var/log/installer/espresso'
        target_log_file = os.path.join(self.target, log_file[1:])

        if not os.path.exists(os.path.dirname(target_log_file)):
            os.makedirs(os.path.dirname(target_log_file))

        if not misc.ex('cp', '-a', log_file, target_log_file):
            misc.pre_log('error', 'No se pudieron copiar los registros de instalación')

        return True


    def mount_source(self):
        """mounting loop system from cloop or squashfs system."""

        from os import path

        self.dev = ''
        if not os.path.isdir(self.source):
            try:
                os.mkdir(self.source)
            except Exception, e:
                print e
            misc.pre_log('info', 'mkdir %s' % self.source)

        # Autodetection on unionfs systems
        for line in open('/proc/mounts'):
            if line.split()[2] == 'squashfs':
                misc.ex('mount', '--bind', line.split()[1], self.source)
                self.unionfs = True
                return True

        # Manual Detection on non unionfs systems
        files = ['/cdrom/casper/filesystem.cloop', '/cdrom/META/META.squashfs']

        for file in files:
            if path.isfile(file) and path.splitext(file)[1] == '.cloop':
                self.dev = '/dev/cloop1'
                break
            elif path.isfile(file) and path.splitext(file)[1] == '.squashfs':
                self.dev = '/dev/loop3'
                break

        if self.dev == '':
            return False

        misc.ex('losetup', self.dev, file)
        try:
            misc.ex('mount', self.dev, self.source)
        except Exception, e:
            print e
        return True


    def umount_source(self):
        """umounting loop system from cloop or squashfs system."""

        if not misc.ex('umount', self.source):
            return False
        if self.unionfs:
            return True
        if not misc.ex('losetup', '-d', self.dev) and self.dev != '':
            return False
        return True


# vim:ai:et:sts=4:tw=80:sw=4:
