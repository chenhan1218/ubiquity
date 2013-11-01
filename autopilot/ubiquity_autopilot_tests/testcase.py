__author__ = 'dan'
from autopilot.testcase import AutopilotTestCase
from testtools.testcase import MismatchError
from testtools.matchers import (
    Not,
    Equals,
    Annotate,
    Is,
    IsInstance
    )
import unittest
from testtools.content import text_content
import traceback
from ubiquity_autopilot_tests.tools import compare
from ubiquity_autopilot_tests.tools._exc import NonFatalErrors


class UbiquityTestCase(AutopilotTestCase):

    def setUp(self):
        super(UbiquityTestCase, self).setUp()
        self.non_fatal_errors = []

    def tearDown(self):
        emulator_errors = compare.non_fatal_errors
        if len(emulator_errors) > 0:
            for error in emulator_errors:
                self.non_fatal_errors.append(error)
        self.assertNonFatalErrors()
        super(UbiquityTestCase, self).tearDown()
        unittest.TestCase.tearDown(self)

    def assertNonFatalErrors(self, ):
        error_list = self.non_fatal_errors
        if len(error_list) > 0:
            num = 1
            for error in error_list:
                output = """
=======================================================================
The Installation Succeeded, but with Non-Fatal Errors.
_______________________________________________________________________
%s
_______________________________________________________________________
""" % error
                self.addDetail("Non-Fatal error {0}: ".format(num), text_content(output))
                num += 1
            raise NonFatalErrors("The test completed, but with {0} non fatal errors".format(len(error_list)))
        return

    def expectEqual(self, expected, observed, message=''):
        """Assert that 'expected' is equal to 'observed'.

        :param expected: The expected value.
        :param observed: The observed value.
        :param message: An optional message to include in the error.
        """
        matcher = Equals(expected)
        try:
            self._expectThat(observed, matcher, message)
        except MismatchError:

            stck = traceback.format_exc(limit=5)
            self.non_fatal_errors.append(stck)

    def expectIsNotNone(self, observed, message=''):
        """Assert that 'observed' is not equal to None.

        :param observed: The observed value.
        :param message: An optional message describing the error.
        """
        matcher = Not(Is(None))
        try:
            self._expectThat(observed, matcher, message)
        except MismatchError:
            stck = traceback.format_exc(limit=5)
            self.non_fatal_errors.append(stck)

    def expectIsInstance(self, obj, klass, msg=None):
        if isinstance(klass, tuple):
            matcher = IsInstance(*klass)
        else:
            matcher = IsInstance(klass)
        try:
            self._expectThat(obj, matcher, msg)
        except MismatchError:
            stck = traceback.format_exc(limit=5)
            self.non_fatal_errors.append(stck)

    def expectThat(self, matchee, matcher, message='', verbose=False):
        try:
            self._expectThat(matchee, matcher, message, verbose)
        except MismatchError:
            stck = traceback.format_exc(limit=5)
            self.non_fatal_errors.append(stck)

    def _expectThat(self, matchee, matcher, message='', verbose=False):

        matcher = Annotate.if_message(message, matcher)
        mismatch = matcher.match(matchee)
        if not mismatch:
            return
        existing_details = self.getDetails()
        for (name, content) in mismatch.get_details().items():
            full_name = name
            suffix = 1
            while full_name in existing_details:
                full_name = "%s-%d" % (name, suffix)
                suffix += 1
                self.addDetail(full_name, content)

        raise MismatchError(matchee, matcher, mismatch, verbose)
