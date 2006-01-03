#! /usr/bin/python
# -*- coding: UTF-8 -*-

import os
try:
    from debconf import DebconfCommunicator
except ImportError:
    from espresso.debconfcommunicator import DebconfCommunicator
from espresso.debconffilter import DebconfFilter

class FilteredCommand(object):
    def __init__(self):
        self.package = 'espresso'

    def debug(self, fmt, *args):
        if 'ESPRESSO_DEBUG' in os.environ:
            message = fmt % args
            print >>sys.stderr, '%s: %s' % (self.package, message)

    def run_command(self, command, widgets={}):
        db = DebconfCommunicator(self.package)
        dbfilter = DebconfFilter(db, widgets)

        # TODO: Set as unseen all questions that we're going to ask.

        ret = dbfilter.run(command)

        if ret != 0:
            # TODO: error message if (ret / 256) != 10
            self.debug("%s exited with code %d", command, ret)

        db.shutdown()

        return ret

if __name__ == '__main__':
    import sys
    fc = FilteredCommand()
    fc.run(sys.argv[1])
