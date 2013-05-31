import os
from collections import namedtuple
from autopilot.testcase import AutopilotTestCase
from autopilot.introspection import get_autopilot_proxy_object_for_process
from testtools.matchers import Equals

class WelcomeTests(AutopilotTestCase):

    def setUp(self):
        super(WelcomeTests, self).setUp()
        self.app = self.launch_application()
    
    def launch_application(self):
        '''
        Hmm... launch ubiquity

        :returns: The application proxy object.
        '''

        Pr = namedtuple('Process', ['pid'])
        my_process = Pr(int(os.environ['UBIQUITY_PID']))
        return get_autopilot_proxy_object_for_process(my_process)
        
    def test_window_title(self):
        '''
        Check that title is "Install"
        '''
        main_window = self.app.select_single(
            'GtkWindow', name='live_installer')
        self.assertThat(main_window.title, Equals("Install"))
