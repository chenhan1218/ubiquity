#! /usr/bin/python
# -*- coding: utf-8; -*-

from __future__ import unicode_literals

import mock
import os
import unittest

import six

from ubiquity import filteredcommand


class FilteredCommandTests(unittest.TestCase):
    def setUp(self):
        os.environ['UBIQUITY_DEBUG_CORE'] = '1'
        patcher = mock.patch('sys.stderr')
        patched_stderr = patcher.start()
        self.addCleanup(patcher.stop)
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
