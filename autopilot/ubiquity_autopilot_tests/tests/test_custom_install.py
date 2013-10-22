# Testing Default Install for the Ubiquity Installer
# Author: Dan Chapman <daniel@chapman-mail.com>
# Copyright (C) 2013
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from ubiquity_autopilot_tests.tests import UbiquityAutopilotTestCase
from testtools.matchers import Equals, NotEquals
from autopilot.matchers import Eventually
from ubiquity_autopilot_tests.emulators import gtktoplevel
from time import sleep
import platform


class CustomInstallTestCase(UbiquityAutopilotTestCase):
    """ Custom install testcase installs *buntu flavor with custom partition setup """

    def test_custom_install(self, ):
        #first check we have an emulator instance
        self.assertIsInstance(self.main_window, gtktoplevel.GtkWindow)
        self.assertThat(self.main_window.visible, Eventually(Equals(True)))
        self.main_window.run_welcome_page_tests(lang='English')
        self.go_to_next_page()
        self.preparing_page_tests()
        # lets get the flavor from the page_title
        flavor = self.main_window.get_flavor()
        self.go_to_next_page()
        sleep(10)
        self.installation_type_page_tests(custom=True)
        self.go_to_next_page()
        self.custom_partition_page_tests()
        self.go_to_next_page(wait=True)
        self.location_page_tests()
        self.go_to_next_page()
        self.keyboard_layout_page_tests()
        self.go_to_next_page()
        self.user_info_page_tests('Autopilot', 'password')

        #flavor = platform.dist()
        #flavor_name = flavor[0]
        if 'Ubuntu' in flavor:
            self.go_to_next_page()
            self.main_window.run_ubuntu_one_page_tests()
        else:
            self.go_to_progress_page()

        self.main_window.run_install_progress_page_tests()
        self.assertThat(lambda: self.app.select_single('GtkDialog', name='finished_dialog').visible,
                        Eventually(Equals(True)))
        #if we got this far the install is now fully complete. Lets check for non-fatal errors
        self.check_for_non_fatal_errors()
        #XXX: Uncomment if you want to restart after install complete
        ##we need to sleep here to wait for dialog to fully load. It appears in dbus
        ## before its actually visible. As the test has already passed this doesn't affect outcome
        #time.sleep(5)
        #
        #self.keyboard.press_and_release('Enter')
