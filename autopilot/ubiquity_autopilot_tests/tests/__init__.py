# Testing Ubiquity Installer
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
import os
import logging
import subprocess
import time
from testtools.matchers import Equals, NotEquals
from autopilot.matchers import Eventually
from autopilot.testcase import AutopilotTestCase
from autopilot.introspection import get_proxy_object_for_existing_process
from ubiquity_autopilot_tests.emulators import AutopilotGtkEmulatorBase
from ubiquity_autopilot_tests.emulators import gtktoplevel
from ubiquity_autopilot_tests.tools.compare import expectThat, non_fatal_errors
from ubiquity_autopilot_tests.emulators.gtktoplevel import GtkWindow
from autopilot.input import Mouse, Keyboard, Pointer
from testtools.content import text_content

logger = logging.getLogger(__name__)


class UbiquityAutopilotTestCase(AutopilotTestCase):
    def setUp(self):
        super(UbiquityAutopilotTestCase, self).setUp()
        self.app = self.launch_application()

        self.pointing_device = Pointer(Mouse.create())
        self.kbd = Keyboard.create()
        self.current_page_title = ''
        self.previous_page_title = ''
        self.current_step = ''
        self.step_before = ''

    def launch_application(self):
        '''
        Hmm... launch ubiquity


        :returns: The application proxy object.
        '''
        my_process = int(os.environ['UBIQUITY_PID'])
        my_dbus = str(os.environ['DBUS_SESSION_BUS_ADDRESS'])
        return get_proxy_object_for_existing_process(pid=my_process,
                                                     dbus_bus=my_dbus,
                                                     emulator_base=AutopilotGtkEmulatorBase)

    @property
    def main_window(self, ):
        return self.app.select_single('GtkWindow', name='live_installer')

    def go_to_next_page(self, wait=False):
        """ Goes to the next page of Ubiquity installer

        Will timeout after 2 mins waiting for next page to appear.

        Params:
            wait: If set to true will wait for the buttons sensitive property
                  to be true. Will timeout after 20mins.
                NOTE: this should only be used when clicking 'Install Now'
                the default 2 mins is sufficient for every other page switch

        """
        logger.debug('go_to_next_page(wait={0})'.format(wait))
        nxt_button = self.main_window.select_single('GtkButton', name='next')
        nxt_button.click()

        if wait:
            #This sleep just bridges a weird error when the next button, sometimes
            # flickers its sensitive property back to 1 once clicked and then
            # goes back to 0
            time.sleep(2)
            # now take back over from the sleep and wait for sensitive to become 1
            logger.debug("Waiting for 'next' Button to become sensitive again.....")
            self.assertThat(nxt_button.sensitive, Eventually(Equals(True), timeout=1200))

        page_title = self.main_window.select_single('GtkLabel', name='page_title')
        self.assertThat(page_title.label,
                        Eventually(NotEquals(self.current_page_title),
                                   timeout=120))

    def go_to_progress_page(self, ):
        """ This simply clicks next and goes to the progress page

        NOTE: THis shouldn't be used for any other page switches as it does no checks.
        
        """
        nxt_button = self.main_window.select_single('GtkButton', name='next')
        nxt_button.click()

    def welcome_page_tests(self, lang=None):
        self._update_current_step('stepLanguage')
        self._check_navigation_buttons()
        self.main_window.run_welcome_page_tests(lang)
        self._update_page_titles()
        self._check_page_titles()
        self._check_navigation_buttons()

    def preparing_page_tests(self, updates=False, thirdParty=False,
                             networkConnection=True, sufficientSpace=True,
                             powerSource=False):
        self._update_current_step('stepPrepare')
        self._check_navigation_buttons()
        self._update_page_titles()
        self.main_window.run_preparing_page_tests(updates, thirdParty,
                                                  networkConnection,
                                                  sufficientSpace,
                                                  powerSource)
        self._check_page_titles()
        self._check_navigation_buttons()

    def installation_type_page_tests(self, default=False, lvm=False,
                                     lvmEncrypt=False, custom=False):
        self._update_current_step('stepPartAsk')
        self._check_navigation_buttons()
        self._update_page_titles()
        self.main_window.run_installation_type_page_tests(_default=default,
                                                          _lvm=lvm,
                                                          _lvmEncrypt=lvmEncrypt,
                                                          _custom=custom)
        self._check_page_titles()
        self._check_navigation_buttons()

    def lvm_crypto_page_tests(self, crypto_password):
        self._update_current_step('stepPartCrypto')
        self._check_navigation_buttons()
        self._update_page_titles()
        self.main_window.run_step_part_crypto_page_tests(crypto_password)
        self._check_page_titles()
        self._check_navigation_buttons()

    def custom_partition_page_tests(self, part_config=None):
        self._update_current_step('stepPartAdvanced')
        self._check_navigation_buttons()
        self._update_page_titles()
        self.main_window.run_custom_partition_page_tests(part_config)
        self._check_page_titles()
        self._check_navigation_buttons()

    def location_page_tests(self, ):
        self._update_current_step('stepLocation')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        self.main_window.run_location_page_tests()
        self._check_page_titles()
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def keyboard_layout_page_tests(self, ):
        self._update_current_step('stepKeyboardConf')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        self.main_window.run_keyboard_layout_page_tests()
        self._check_page_titles()
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def user_info_page_tests(self, username, pwd,
                             encrypted=False, autologin=False):
        self._update_current_step('stepUserInfo')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        self.main_window.run_user_info_page_tests(username, pwd,
                                                  encrypted, autologin)
        self._check_page_titles()
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def ubuntu_one_page_tests(self, ):
        #self._update_current_step('stepUserInfo')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=True)
        self._update_page_titles()
        self.main_window.run_ubuntu_one_page_tests()

    def progress_page_tests(self, ):
        pass

    def _check_navigation_buttons(self, continue_button=True, back_button=True,
                                  quit_button=True, skip_button=False):
        """ Function that checks the navigation buttons through out the install

        :param continue_button: Boolean value of buttons expected visibility
        :param back_button: Boolean value of buttons expected visibility
        :param quit_button: Boolean value of buttons expected visibility
        :param skip_button: Boolean value of buttons expected visibility

        """
        logger.debug("check_window_constants({0}, {1}, {2}, {3})".format(
            continue_button, back_button, quit_button, skip_button))

        con_button = self.main_window.select_single('GtkButton', name='next')
        self.assertThat(con_button.visible, Equals(continue_button))

        bk_button = self.main_window.select_single('GtkButton', name='back')
        self.assertThat(bk_button.visible, Equals(back_button))

        qt_button = self.main_window.select_single('GtkButton', name='quit')
        self.assertThat(qt_button.visible, Equals(quit_button))

        skp_button = self.main_window.select_single('GtkButton', name='skip')
        self.assertThat(skp_button.visible, Equals(skip_button))

    def _update_current_step(self, name):
        logger.debug("Updating current step to %s" % name)
        self.step_before = self.current_step
        self.current_step = name

    def _update_page_titles(self, ):
        self.previous_page_title = self.current_page_title
        self.current_page_title = self.main_window.select_single('GtkLabel',
                                                                 BuilderName='page_title').label

    def _check_page_titles(self, ):
        current_page_title = self.main_window.select_single('GtkLabel',
                                                            BuilderName='page_title')
        message = "Expected %s page title '%s' to not equal \
        the previous %s page title '%s' but it does" % \
                  (self.current_step, self.current_page_title, self.step_before, self.previous_page_title)

        expectThat(self.previous_page_title).not_equals(self.current_page_title, msg=message)
        # THis second one catches the known bug for the stepPartAvanced page title switching back to the prev page title
        message_two = "Expected %s page title '%s' to not equal the previous %s page title '%s' but it does" % \
                      (self.current_step, current_page_title.label, self.step_before, self.previous_page_title)
        expectThat(self.previous_page_title).not_equals(current_page_title.label, msg=message_two)
        expectThat(current_page_title.visible).equals(True)

    def check_for_non_fatal_errors(self, ):
        """ Checks for any non fatal failures during the install

            This should be the very last function call in the test,
            the install should have successfully completed. Which we can then check for non
            critical problems
        """
        global non_fatal_errors
        try:
            self.assertThat(len(non_fatal_errors), Equals(0),
                            "There were {0} Non-Fatal Errors".format(len(non_fatal_errors)))
        except AssertionError:
            logger.debug("There were {0} Non-Fatal Errors".format(len(non_fatal_errors)))
            i = 1
            for elem in non_fatal_errors:
                out = """
                ============================================================\n
Fail: The Installation Succeeded, but with Non-Fatal Errors.
------------------------------------------------------------
%s""" % elem
                self.addDetail('NON_FATAL_ERROR %s:' % str(i), text_content(out))
                i += 1
            raise

    def get_distribution(self, ):
        """Returns the name of the running distribution."""
        proc = subprocess.Popen(
            ['lsb_release', '-is'], stdout=subprocess.PIPE,
            universal_newlines=True)
        distro = proc.communicate()[0].strip()
        return str(distro)
