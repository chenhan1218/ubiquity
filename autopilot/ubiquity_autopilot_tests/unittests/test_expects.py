__author__ = 'dan'
import unittest
from testtools.testcase import TestCase


class ExpectTestCase(TestCase):
    def test_something(self):
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
