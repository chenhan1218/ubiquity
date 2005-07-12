# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import popen2
import debconf

class DebconfCommunicator(debconf.Debconf, object):
    def __init__(self, owner, title=None):
        self.dccomm = popen2.Popen3(['debconf-communicate', '-fnoninteractive',
                                     owner])
        super(DebconfCommunicator, self).__init__(title=title,
                                                  read=self.dccomm.fromchild,
                                                  write=self.dccomm.tochild)

    def shutdown(self):
        if self.dccomm is not None:
            self.dccomm.tochild.close()
            self.dccomm.wait()
            self.dccomm = None

    def __del__(self):
        self.shutdown()
