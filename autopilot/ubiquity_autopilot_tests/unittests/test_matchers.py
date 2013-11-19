__author__ = 'dan'

import unittest
from testtools.testcase import TestCase
from testtools.matchers import Equals


class MyTestCase(TestCase):

    def test_something(self):
        self.assertThat(True, Equals(False))

if __name__ == '__main__':
    unittest.main()
