__author__ = 'dan'
__all__ = [
    'Expect'

]
from testtools.matchers import Matcher, Equals, Mismatch
from ubiquity_autopilot_tests.tests import non_fatal_errors
import traceback


class Expect(Matcher):
    """ Match non-fatal errors
    """
    def __init__(self, matcher, msg=''):
        super(Expect, self).__init__()
        self.message = msg
        match_fun = getattr(matcher, 'match', None)
        if match_fun is None or not callable(match_fun):
            raise TypeError(
                "Expect must be called with a testtools matcher argument.")
        self.matcher = matcher

    def match(self, value):
        try:
            mismatch = self.matcher.match(value)
            if mismatch:
                fail_msg = mismatch.describe()
                raise NonFatalErrors("{0!r:s} {1!r:s}".format(fail_msg, self.message))
        except NonFatalErrors:
            global non_fatal_errors
            stck = traceback.format_exc(limit=5)
            non_fatal_errors.append(stck)

            pass
        return None

    def __str__(self):
        return "Expect " + str(self.matcher)

class LessThanOrEqual(Matcher):
    pass

class GreaterThanOrEqual(Matcher):
    pass

class NonFatalErrors(AssertionError):
    """Exception class for raising non fatal errors
    """