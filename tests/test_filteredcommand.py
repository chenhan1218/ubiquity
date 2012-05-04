#! /usr/bin/python
# -*- coding: utf-8; -*-

from __future__ import unicode_literals

import mock
import os
import sys
import unittest

import six

from ubiquity import filteredcommand


class FilteredCommandTests(unittest.TestCase):
    def setUp(self):
        os.environ['UBIQUITY_DEBUG_CORE'] = '1'
        # On Python 2, we need to patch sys.stderr.write to force a failure
        # if something attempts to write a non-ASCII-only unicode object to
        # stderr, because that may fail.
        # The situation with Python 3 is more pleasant, although no less
        # fiddly to test.  sys.stderr is an io.TextIOWrapper object in the
        # default locale encoding and with errors="backslashreplace"; so we
        # can mock up one of these with the worst-case locale encoding of
        # ASCII.
        if sys.version < '3':
            patcher = mock.patch('sys.stderr')
        else:
            import io
            new_stderr = io.TextIOWrapper(
                io.BytesIO(), encoding='ASCII', errors='backslashreplace')
            patcher = mock.patch('sys.stderr', new_stderr)
        patched_stderr = patcher.start()
        self.addCleanup(patcher.stop)
        if sys.version < '3':
            patched_stderr.write = self.write_side_effect

    def tearDown(self):
        del os.environ['UBIQUITY_DEBUG_CORE']

    def write_side_effect(self, *args, **kwargs):
        for arg in args:
            if isinstance(arg, six.text_type):
                arg.encode('ascii')

    def test_debug_unicode(self):
        variant = "Arménien"
        filteredcommand.UntrustedBase.debug("Unknown keyboard variant %s",
            variant)

    def test_debug_bytes(self):
        variant = b"English"
        filteredcommand.UntrustedBase.debug("Unknown keyboard variant %s",
            variant)
