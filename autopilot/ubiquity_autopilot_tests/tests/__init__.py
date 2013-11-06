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
from testtools.content import text_content

from autopilot.matchers import Eventually
from autopilot.introspection import get_proxy_object_for_existing_process
from autopilot.input import Mouse, Keyboard, Pointer

from ubiquity_autopilot_tests.emulators import AutopilotGtkEmulatorBase
from ubiquity_autopilot_tests.emulators import gtktoplevel
from ubiquity_autopilot_tests.tools import compare
from ubiquity_autopilot_tests.tools.compare import expectThat
from ubiquity_autopilot_tests.emulators.gtktoplevel import GtkWindow
from ubiquity_autopilot_tests.testcase import UbiquityTestCase

logger = logging.getLogger(__name__)


class UbiquityAutopilotTestCase(UbiquityTestCase):

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
        """ Runs the tests for the Welcome Page
        :param lang: The treeview label value (e.g 'English') of the required language.
                     If None will pick a random language from the tree.
                     ..NOTE: You should only specify a language if the test relies
                           upon a specific language. It is better to write the tests
                           to work for any language.
        """
        self._update_current_step('stepLanguage')
        self._check_navigation_buttons()
        #first check pageTitle visible and correct if label given
        logger.debug("run_welcome_page_tests()")
        #selecting an install language
        logger.debug("Selecting stepLanguage page object")
        welcome_page = self.main_window.select_single('GtkBox', name='stepLanguage')
        treeview = welcome_page.select_single('GtkTreeView')
        #lets get all items
        treeview_items = treeview.get_all_items()
        #first lets check all the items are non-empty unicode strings
        logger.debug("Checking all tree items are valid unicode")
        for item in treeview_items:
            logger.debug("Check tree item with name '%s' is unicode" % item.accessible_name)
            self.expectIsInstance(item.accessible_name, unicode)
            self.expectThat(item.accessible_name, NotEquals(u''))

        if lang:
            item = treeview.select_item(lang)
            language = item
        else:
            language = welcome_page.get_random_language()

        welcome_page.select_language(language)
        self.assertThat(language.selected, Equals(True))
        ##Test release notes label is visible
        logger.debug("Checking the release_notes_label")
        release_notes_label = welcome_page.select_single('GtkLabel',
                                                         BuilderName='release_notes_label')
        self.expectThat(release_notes_label.visible, Equals(True))
        self.expectThat(release_notes_label.label, NotEquals(u''))
        self.expectIsInstance(release_notes_label.label, unicode)
        self.pointing_device.move_to_object(release_notes_label)
        self._update_page_titles()
        self._check_page_titles()
        self._check_navigation_buttons()

    def preparing_page_tests(self, updates=False, thirdParty=False,
                             networkConnection=True, sufficientSpace=True,
                             powerSource=False):
        """ Runs the tests for the 'Preparing to install' page

        :param updates: Boolean, if True selects install updates during install

        :param thirdParty: Boolean, if True selects install third-party software

        :param networkConnection: Boolean if True checks the network state box is
                                  visible and objects are correct, If false will
                                  still check the objects are correct but the
                                  state box is not visible

        :param sufficientSpace: Boolean if True checks the network state box is
                                  visible and objects are correct, If false will
                                  still check the objects are correct but the
                                  state box is not visible

        :param powerSource: Boolean if True checks the network state box is
                                  visible and objects are correct, If false will
                                  still check the objects are correct but the
                                  state box is not visible
        """
        self._update_current_step('stepPrepare')
        self._check_navigation_buttons()
        self._update_page_titles()

        logger.debug("run_preparing_page_tests()")
        logger.debug("selecting stepPrepare page")
        preparing_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPrepare')

        objList = ['prepare_best_results', 'prepare_foss_disclaimer',
                   'prepare_download_updates', 'prepare_nonfree_software']
        for obj in objList:
            logging.debug("Running checks on {0} object".format(obj))
            obj = preparing_page.select_single(BuilderName=obj)
            self.expectThat(obj.visible, Equals(True))
            self.expectThat(obj.label, NotEquals(u''))
            self.expectIsInstance(obj.label, unicode)

        if updates:
            logger.debug("Selecting install updates")
            update_checkbutton = preparing_page.select_single('GtkCheckButton',
                                                              BuilderName='prepare_download_updates')
            self.pointing_device.click_object(update_checkbutton)

        if thirdParty:
            logger.debug("Selecting install thirdparty software")
            thrdprty_checkbutton = preparing_page.select_single('GtkCheckButton',
                                                                BuilderName='prepare_nonfree_software')
            self.pointing_device.click_object(thrdprty_checkbutton)

        self._check_preparing_statebox('prepare_network_connection',
                                       visible=networkConnection)
        #and sufficient space
        self._check_preparing_statebox('prepare_sufficient_space',
                                       visible=sufficientSpace)
        # and power source
        self._check_preparing_statebox('prepare_power_source',
                                       visible=powerSource)

        self._check_page_titles()
        self._check_navigation_buttons()

    def installation_type_page_tests(self, default=False, lvm=False,
                                     lvmEncrypt=False, custom=False):
        self._update_current_step('stepPartAsk')
        self._check_navigation_buttons()
        self._update_page_titles()
        from ubiquity_autopilot_tests import configs
        option_name = None
        if default:
            config = configs.default_install
        if lvm:
            config = configs.lvm_install
            option_name = 'use_lvm'
        if lvmEncrypt:
            config = configs.encrypt_lvm_install
            option_name = 'use_crypto'
        if custom:
            config = configs.custom_install
            option_name = 'custom_partitioning'
        self._options_tests(config.visible_options, config.hidden_options)
        install_type_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartAsk')
        if option_name:
            obj = install_type_page.select_single(BuilderName=option_name)
            self.pointing_device.click_object(obj)

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

        expectThat(self.previous_page_title).not_equals(self.current_page_title, message)
        # THis second one catches the known bug for the stepPartAdvanced page title switching back to the prev page title
        message_two = "Expected %s page title '%s' to not equal the previous %s page title '%s' but it does" % \
                      (self.current_step, current_page_title.label, self.step_before, self.previous_page_title)
        self.expectThat(self.previous_page_title,
                        NotEquals(current_page_title.label), message=message_two)
        self.expectThat(current_page_title.visible, Equals(True))

    def _check_preparing_statebox(self, stateboxName, visible=True, imagestock='gtk-yes'):
        """ Checks the preparing page statebox's """
        logger.debug("Running checks on {0} StateBox".format(stateboxName))
        preparing_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPrepare')
        state_box = preparing_page.select_single('StateBox', BuilderName=stateboxName)
        state_box.check(visible, imagestock)
        logger.debug('check({0}, {1})'.format(visible, imagestock))
        logger.debug("Running checks.......")
        if visible:
            self.expectThat(state_box.visible, Equals(visible),
                            "StateBox.check(): Expected {0} statebox to be visible but it wasn't".format(self.name))
            label = state_box.select_single('GtkLabel')
            self.expectThat(label.label, NotEquals(u''))
            self.expectThat(label.visible, Equals(visible))
            self.expectIsInstance(label.label, unicode)
            image = state_box.select_single('GtkImage')
            self.expectThat(image.stock, Equals(imagestock))
            self.expectThat(image.visible, Equals(visible))

        else:
            self.expectThat(state_box.visible, Equals(False))

    def _options_tests(self, visible=[], hidden=[]):

        install_type_page = self.select_single('GtkAlignment',
                                               BuilderName='stepPartAsk')

        for option in visible:
            logger.info("selecting Visible object'{0}'".format(option))
            opt = install_type_page.select_single(BuilderName=option)
            self.expectThat(opt.visible, Equals(True))
            self.expectThat(opt.label, NotEquals(u''))
            self.expectIsInstance(opt.label, unicode)

        for option in hidden:
            logger.info("Selecting hidden object '{0}'".format(option))

            opt = install_type_page.select_single(BuilderName=option)
            self.expectThat(opt.visible, Equals(False))
            self.expectThat(opt.label, NotEquals(u''))
            self.expectIsInstance(opt.label, unicode)

    def _select_install_type(self, install_type):
        pass

    def get_distribution(self, ):
        """Returns the name of the running distribution."""
        proc = subprocess.Popen(
            ['lsb_release', '-is'], stdout=subprocess.PIPE,
            universal_newlines=True)
        distro = proc.communicate()[0].strip()
        return str(distro)
