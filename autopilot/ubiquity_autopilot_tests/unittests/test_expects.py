__author__ = 'dan'
import unittest
from ubiquity_autopilot_tests.testcase import UbiquityTestCase
from testtools.matchers import (
    Equals,
    NotEquals,
)

class ExpectTestCase(UbiquityTestCase):


    def test_fail_expect_equal(self):
        self.expectEqual(5, 4)
        self.assertThat(len(self.non_fatal_errors), Equals(1))

    def test_expect_equal(self):
        self.expectEqual(5, 5)
        self.assertThat(len(self.non_fatal_errors), Equals(0))

if __name__ == '__main__':
    unittest.main()
