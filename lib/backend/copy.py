#!/usr/bin/python

    def mount_target(self, mountpoints):
        if not os.path.isdir(self.target):
            os.mkdir(self.target)
        self.ex('mount', mountpoints['/'], self.target)

        for path, device in mountpoints.items():
            if path in ('/', 'swap'):
                continue
            path = os.path.join(self.target, path[1:])
            os.mkdir(path)
            self.ex('mount', device, path)

    def copy_all(self):
        files = []
        total_size = 0
        
        for dirpath, dirnames, filenames in os.walk(self.source):
            sourcepath = dirpath[len(self.source)+1:]

            for name in dirnames + filenames:
                relpath = os.path.join(sourcepath, name)
                fqpath = os.path.join(self.source, dirpath, name)

                if os.path.isfile(fqpath):
		    size = os.path.getsize(fqpath)
		    total_size += size	
                    files.append((relpath, size))
                else:
                    files.append((relpath, None))

        copy = subprocess.Popen(['cpio', '-d0mp', self.target],
                                cwd=self.source,
                                stdin=subprocess.PIPE)

        copied_bytes = 0
        for path, size in files:
            copy.stdin.write(path + '\0')
            if size is not None:
                copied_bytes += size
            per = (copied_bytes * 100) / total_size
            self.wizard.set_progress(per)

        copy.stdin.close()
        copy.wait()
        

    def mount_source(self):
	from os import path
	files = ['/cdrom/casper/filesystem.cloop', '/cdrom/META/META.squashfs']
	for f in files:
		if path.isfile(f) and path.splitext(f)[1] == '.cloop':
			file = f
			self.dev = '/dev/cloop1'
		elif path.isfile(f) and path.splitext(f)[1] == '.squashfs':
			file = f
			self.dev = '/dev/loop3'
		else:
                    return -1			

        self.ex('losetup', self.dev, file)
        os.mkdir(self.source)
        self.ex('mount', self.dev, self.source)
	return 0

    def unmount_source(self):
        self.ex('umount', self.source)
        self.ex('losetup', '-d', self.dev)


# vim:ai:et:sts=2:tw=80:sw=2:
