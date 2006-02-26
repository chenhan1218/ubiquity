#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import time
import debconf
from espresso import misc
from sys import stderr

class Copy:

    def __init__(self):
        """Initial attributes."""

        if os.path.isdir('/rofs'):
            self.source = '/rofs'
        else:
            self.source = '/source'
        self.target = '/target'
        self.unionfs = False
        self.db = debconf.Debconf()

    def run(self):
        """Run the copy stage. This is the second step from the installation
        process."""

        self.db.progress('START', 0, 100, 'espresso/copy/title')
        self.db.progress('INFO', 'espresso/copy/mounting_source')
        if self.source == '/source':
            if not self.mount_source():
                return False

        if not self.copy_all():
            return False

        self.db.progress('SET', 98)
        self.db.progress('INFO', 'espresso/copy/log_files')
        if not self.copy_logs():
            return False

        self.db.progress('SET', 99)
        self.db.progress('INFO', 'espresso/copy/cleanup')
        if self.source == '/source':
            if not self.umount_source():
                return False

        self.db.progress('SET', 100)
        self.db.progress('STOP')


    def copy_all(self):
        """Core copy process. This is the most important step of this
        stage. It clones live filesystem into a local partition in the
        selected hard disk."""

        files = []
        total_size = 0
        oldsourcepath = ''

        self.db.progress('SET', 1)
        self.db.progress('INFO', 'espresso/copy/scanning')

        # Obviously doing os.walk() twice is inefficient, but I'd rather not
        # suck the list into espresso's memory, and I'm guessing that the
        # kernel's dentry cache will avoid most of the slowness anyway.
        walklen = 0
        for entry in os.walk(self.source):
            walklen += 1
        walkpos = 0
        walkprogress = 0

        for dirpath, dirnames, filenames in os.walk(self.source):
            walkpos += 1
            if int(float(walkpos) / walklen * 9) != walkprogress:
                walkprogress = int(float(walkpos) / walklen * 9)
                self.db.progress('SET', 1 + walkprogress)

            sourcepath = dirpath[len(self.source) + 1:]

            for name in dirnames + filenames:
                relpath = os.path.join(sourcepath, name)
                fqpath = os.path.join(self.source, dirpath, name)

                if os.path.isfile(fqpath):
                    size = os.path.getsize(fqpath)
                    total_size += size
                    files.append((relpath, size))
                else:
                    files.append((relpath, None))

        self.db.progress('SET', 10)
        self.db.progress('INFO', 'espresso/copy/copying')

        copy = subprocess.Popen(['cpio', '-d0mp', '--quiet', self.target],
                cwd = self.source,
                stdin = subprocess.PIPE)

        # Progress bar handling:
        # We sample progress every half-second (assuming time.time() gives
        # us sufficiently good granularity) and use the average of progress
        # over the last minute or so to decide how much time remains. We
        # don't bother displaying any progress for the first ten seconds in
        # order to allow things to settle down, and we only update the "time
        # remaining" indicator at most every two seconds after that.

        copy_progress = 0
        copied_bytes, counter = 0, 0
        time_start = time.time()
        times = [(time_start, copied_bytes)]
        long_enough = False
        time_last_update = time_start

        for path, size in files:
            copy.stdin.write(path + '\0')
            if size is not None:
                copied_bytes += size

            if int((copied_bytes * 88) / total_size) != copy_progress:
                copy_progress = int((copied_bytes * 88) / total_size)
                self.db.progress('SET', 10 + copy_progress)

            time_now = time.time()
            if (time_now - times[-1][0]) >= 0.5:
                times.append((time_now, copied_bytes))
                if not long_enough and time_now - times[0][0] >= 10:
                    long_enough = True
                if long_enough and time_now - time_last_update >= 2:
                    time_last_update = time_now
                    while (time_now - times[0][0] > 60 and
                           time_now - times[1][0] >= 60):
                        times.pop(0)
                    speed = ((times[-1][1] - times[0][1]) /
                             (times[-1][0] - times[0][0]))
                    time_remaining = int(total_size / speed)
                    time_str = "%d:%02d" % divmod(time_remaining, 60)
                    self.db.subst('espresso/copy/copying_time',
                                  'TIME', time_str)
                    self.db.progress('INFO', 'espresso/copy/copying_time')

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


if __name__ == '__main__':
    Copy().run()

# vim:ai:et:sts=4:tw=80:sw=4:
