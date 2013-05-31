from autopilot.testcase import AutopilotTestCase
from autopilot.introspection import get_autopilot_proxy_object_for_process

class WelcomeTests(AutopilotTestCase):

    def launch_application(self):
        '''
        Hmm... launch ubiquity

        :returns: The application proxy object.
        '''
        from collections import namedtuple
        Pr = namedtumpe('Process', ['pid'])
        my_process = Pr(os.environ['UBIQUITY_PID'])
        return get_autopilot_proxy_object_for_process(my_process)
        
    def test_something(self):
        '''An example test case that will always pass.'''
        self.assertTrue(True)
