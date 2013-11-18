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

from __future__ import print_function

import os
import logging
import random
import time

from testtools.matchers import Equals, NotEquals

from autopilot.matchers import Eventually
from autopilot.introspection import get_proxy_object_for_existing_process
from autopilot.input import (
    Mouse,
    Keyboard,
    Pointer
)
from ubiquity_autopilot_tests.emulators import gtktoplevel
from ubiquity_autopilot_tests.emulators.gtktoplevel import GtkWindow
from ubiquity_autopilot_tests.emulators import AutopilotGtkEmulatorBase
from ubiquity_autopilot_tests.testcase import UbiquityTestCase
from ubiquity_autopilot_tests.configs import eng_label_values
from ubiquity_autopilot_tests.configs.partconfig import (
    Config1,
    Config2,
    Config3,
    Config4,
    Config5,
    Config6
)

custom_configs = [Config1, Config2, Config3, Config4, Config5, Config6]
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
        self.english_install = False
        self.eng_config = {}

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
            self.expectIsInstance(item.accessible_name, str,
                                  "[Page:'stepLanguage'] Expected '%s' tree view item to be unicode but it wasn't"
                                  % item.accessible_name)
            self.expectThat(item.accessible_name, NotEquals(u''),
                            "[Page:'stepLanguage'] Tree item found that doesn't contain any text")

        if lang:
            item = treeview.select_item(lang)
            language = item
        else:
            language = welcome_page.get_random_language()
        if language == 'English':
            self.english_install = True
        welcome_page.select_language(language)

        self.assertThat(language.selected, Equals(True))
        ##Test release notes label is visible
        logger.debug("Checking the release_notes_label")
        release_notes_label = welcome_page.select_single('GtkLabel',
                                                         BuilderName='release_notes_label')
        self.expectThat(release_notes_label.visible, Equals(True),
                        "[Page:'{0}'] Release notes label was not visible".format(self.current_step))
        self.expectThat(release_notes_label.label, NotEquals(u''),
                        "[Page:'{0}'] Release notes label did not contain any text".format(self.current_step))
        self.expectIsInstance(release_notes_label.label, str,
                              "[Page:'{0}'] Expected release notes label to be unicode but it wasn't")
        self.pointing_device.move_to_object(release_notes_label)
        self._update_page_titles()
        if self.english_install:
            #if english install check english values
            self.eng_config = eng_label_values.stepLanguage
            self.expectThat(release_notes_label.label, Equals(self.eng_config['release_notes_label']))
            self.expectThat(self.current_page_title, Equals(self.eng_config['page_title']))
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
        for i in objList:
            logging.debug("Running checks on {0} object".format(i))
            obj = preparing_page.select_single(BuilderName=i)
            self.expectThat(obj.visible, Equals(True),
                            "[Page:'{0}'] Expected {1} object to be visible but it wasn't".format(
                                self.current_step, obj.name
                            ))
            self.expectThat(obj.label, NotEquals(u''),
                            "[Page:'{0}'] Expected {1} objects label value to contain text but it didn't".format(
                                self.current_step, obj.name
                            ))
            self.expectIsInstance(obj.label, str,
                                  "[Page:'{0}'] Expected {1} objects label value to be unicode but it wasn't".format(
                                  self.current_step, obj.name
                                  ))
            if self.english_install:
                #if english install check english values
                self.eng_config = eng_label_values.stepPrepare
                self.expectThat(obj.label, Equals(self.eng_config[i]))


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
        if self.english_install:
            self.expectThat(self.current_page_title, Equals(self.eng_config['page_title']))
        self._check_navigation_buttons()

    def installation_type_page_tests(self, default=False, lvm=False, lvmEncrypt=False, custom=False):
        """ Runs the tests for the installation type page

        :param default: Boolean if True will use the default selected option for the
                        installation

        :param lvm: Boolean if True will use the LVM option for the
                    installation

        :param lvmEncrypt: Boolean if True will use the LVM with encryption option for the
                           installation

        :param custom: Boolean if True will use the 'Something else' option for the
                       installation

        """
        self._update_current_step('stepPartAsk')
        self._check_navigation_buttons()
        self._update_page_titles()

        option_name = None
        if default:
            from ubiquity_autopilot_tests.configs import default_install

            config = default_install
        if lvm:
            from ubiquity_autopilot_tests.configs import lvm_install

            config = lvm_install
            option_name = 'use_lvm'
        if lvmEncrypt:
            from ubiquity_autopilot_tests.configs import encrypt_lvm_install

            config = encrypt_lvm_install
            option_name = 'use_crypto'
        if custom:
            from ubiquity_autopilot_tests.configs import custom_install

            config = custom_install
            option_name = 'custom_partitioning'
        self._options_tests(config.visible_options, config.hidden_options)
        install_type_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartAsk')
        if option_name:
            obj = install_type_page.select_single(BuilderName=option_name)
            self.pointing_device.click_object(obj)

        self._check_page_titles()
        if self.english_install:
            self.expectThat(self.current_page_title, Equals(self.eng_config['page_title']))

        self._check_navigation_buttons()

    def lvm_crypto_page_tests(self, crypto_password):
        """ Runs the tests for the LVM encryption password page

        :param crypto_password: *String*, password to be used for the encryption

        """
        self._update_current_step('stepPartCrypto')
        self._check_navigation_buttons()
        self._update_page_titles()

        logger.debug("run_step_part_crypto_page_tests({0})".format(crypto_password))
        logger.debug('Selecting stepPartCrypto page object')
        crypto_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartCrypto')

        items = ['verified_crypto_label', 'crypto_label', 'crypto_description',
                 'crypto_warning', 'crypto_extra_label', 'crypto_extra_time',
                 'crypto_description_2', 'crypto_overwrite_space']
        for i in items:
            item = crypto_page.select_single(BuilderName=i)
            self.expectThat(item.visible, Equals(True),
                            "[Page:'{0}'] Expected {1} object to be visible but it wasn't".format(
                                self.current_step, item.name
                            ))
            self.expectThat(item.label, NotEquals(u''),
                            "[Page:'{0}'] Expected {1} objects label value to contain text but it didn't".format(
                                self.current_step, item.name
                            ))
            self.expectIsInstance(item.label, str,
                                  "[Page:'{0}'] Expected {1} objects label value to be unicode but it wasn't".format(
                                  self.current_step, item.name
                                  ))
            if self.english_install:
                #if english install check english values
                self.eng_config = eng_label_values.stepPartCrypto
                self.expectThat(item.label, Equals(self.eng_config[i]))

        crypto_page.enter_crypto_phrase(crypto_password)
        self._check_page_titles()
        if self.english_install:
            self.expectThat(self.current_page_title, Equals(self.eng_config['page_title']))

        self._check_navigation_buttons()

    def custom_partition_page_tests(self, part_config=None):
        """ Runs the tests for the custom partition page

        The custom partition configurations are in partconfig.py. This function
        selects a random Config for each test run from partconfig.py.

        When adding a new config, import it and add it to the custom_configs list

        :param part_config:
        """
        self._update_current_step('stepPartAdvanced')
        self._check_navigation_buttons()
        self._update_page_titles()
        logger.debug("run_custom_partition_page_tests()")
        logger.debug("Selecting the stepPartAdvanced page object")
        custom_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartAdvanced')
        treeview = custom_page.select_single('GtkTreeView')
        self.expectThat(treeview.visible, Equals(True),
                        "[Page:'{0}'] Partition tree view was not visible")
        obj_list = ['partition_button_new', 'partition_button_delete', 'partition_button_edit',
                    'partition_button_edit', 'partition_button_new_label']
        for name in obj_list:
            obj = custom_page.select_single(BuilderName=name)
            self.expectThat(obj.visible, Equals(True),
                            "[Page:'{0}'] {1} object was not visible".format(self.current_step, obj.name))
        logger.debug("Sleeping while we wait for all UI elements to fully load")
        time.sleep(5)  # need to give time for all UI elements to load
        custom_page.create_new_partition_table()
        #lets create the partitions from here
        if part_config:
            logger.debug("Setting the given partition config")
            config = part_config
        else:
            logger.debug("Selecting a random partition config")
            config = random.choice(custom_configs)
        for elem in config:
            self._add_new_partition()

            partition_dialog = self.main_window.get_dialog('GtkDialog', BuilderName='partition_dialog')
            self.assertThat(partition_dialog.visible, Eventually(Equals(True)),
                            "Partition dialog not visible")
            partition_dialog.set_partition_size(elem['PartitionSize'])
            partition_dialog.set_partition_location(elem['Position'])
            partition_dialog.set_partition_type(elem['PartitionType'])
            partition_dialog.set_file_system_type(elem['FileSystemType'])
            partition_dialog.set_mount_point(elem['MountPoint'])
            ok_button = partition_dialog.select_single('GtkButton',
                                                       BuilderName='partition_dialog_okbutton')
            self.pointing_device.click_object(ok_button)
            self.assertThat(partition_dialog.visible, Eventually(Equals(False)),
                            "Partition dialog did not close")
            self._check_partition_created(elem['MountPoint'])
        self._check_page_titles()
        self._check_navigation_buttons()

    def location_page_tests(self, ):
        """ Runs the test for the Location page

        Due to not being able to introspect the timezone map we only have a
        choice of 4 locations which get selected at random.

        """
        logger.debug('run_location_page_tests()')
        self._update_current_step('stepLocation')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()

        logger.debug("Selecting stepLocation page object")
        location_page = self.main_window.select_single('GtkBox', BuilderName='stepLocation')
        location_map = location_page.select_single('CcTimezoneMap')
        self.assertThat(location_map.visible, Equals(True),
                        "Expected location map to be visible but it wasn't")
        location_entry = location_page.select_single(BuilderName='timezone_city_entry')
        self.assertThat(location_entry.visible, Equals(True),
                        "Expected location entry to be visible but it wasn't")

        location = ['London', 'Paris', 'Madrid', 'Algiers']
        location_page.select_location(random.choice(location))
        self._check_page_titles()
        if self.english_install:
            self.eng_config = eng_label_values.stepLocation
            self.expectThat(self.current_page_title, Equals(self.eng_config['page_title']))

        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def keyboard_layout_page_tests(self, ):
        self._update_current_step('stepKeyboardConf')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        logger.debug("run_keyboard_layout_page_tests()")

        logger.debug("Selecting the stepKeyboardCOnf page object")
        keyboard_page = self.main_window.select_single('GtkAlignment', BuilderName='stepKeyboardConf')
        treeviews = keyboard_page.select_many('GtkTreeView')
        #lets check all the keyboard tree items for the selected language
        # TODO: we should probably test at some point try changing the keyboard
        #       layout to a different language/locale/layout and see if ubiquity breaks
        for treeview in treeviews:
            items = treeview.get_all_items()
            for item in items:
                self.expectIsInstance(item.accessible_name, str,
                                      "[Page:'%r'] Expected %r item to be unicode but it wasn't" % (
                                          self.current_step, item.accessible_name
                                      ))
                self.expectThat(item.accessible_name, NotEquals(u''),
                                "[Page:'{0}'] Tree view item found which didn't contain text, but it should!!")

        #now lets test typing with the keyboard layout
        entry = keyboard_page.select_single('GtkEntry')
        with self.keyboard.focused_type(entry) as kb:
            kb.type(u'Testing keyboard layout')
            #TODO: only test the entry value if we are using english install
            #message = "Expected {0} (the length of the keyboard entry text) to be {1}".format(
            #    len(entry.text), len(u'Testing keyboard layout')
            #)
            #self.expectThat(len(entry.text), Equals(len(u'Testing keyboard layout')))
            self.expectThat(entry.text, NotEquals(u''),
                            "[Page:'{0}'] Expected Entry to contain text after typing but it didn't".format(
                                self.current_step
                            ))
            self.expectIsInstance(entry.text, str,
                                  "[Page:'{0}'] Expected Entry text to be unicode but it wasnt".format(
                                      self.current_step
                                  ))
        #TODO: Test detecting keyboard layout
        self._check_page_titles()
        if self.english_install:
            self.eng_config = eng_label_values.stepKeyboardConf
            self.expectThat(self.current_page_title, Equals(self.eng_config['page_title']))

        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def user_info_page_tests(self, username, pwd,
                             encrypted=False, autologin=False):
        """ Runs tests for the User Info Page

        :param username:*String*, name of user

        :param pwd: *String*, password for user

        :param encrypted: *Bool* if true encypts the home directory

        :param autologin: *Bool* if true sets the user account to login
                           automagically

        """
        self._update_current_step('stepUserInfo')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        logger.debug("Selecting stepUserInfo page")
        user_info_page = self.main_window.select_single('GtkBox', BuilderName='stepUserInfo')

        objects = ['hostname_label', 'username_label', 'password_label',
                   'verified_password_label', 'hostname_extra_label'
                   ]
        logger.debug("checking user info page objects ......")
        for i in objects:
            obj = user_info_page.select_single('GtkLabel', name=i)
            self.expectThat(obj.visible, Equals(True),
                            "[Page:'{0}'] Expected {1} object to be visible but it wasn't".format(
                                self.current_step, obj.name
                            ))
            self.expectThat(obj.label, NotEquals(u''),
                            "[Page:'{0}'] Expected {1} objects label value to contain text but it didn't".format(
                                self.current_step, obj.name
                            ))
            self.expectIsInstance(obj.label, str,
                                  "[Page:'{0}'] Expected {1} objects label value to be unicode but it wasn't".format(
                                  self.current_step, obj.name
                                  ))
            if self.english_install:
                #if english install check english values
                self.eng_config = eng_label_values.stepUserInfo
                self.expectThat(obj.label, Equals(self.eng_config[i]))

        user_info_page.create_user(username, pwd)
        #TODO: get these working
        if encrypted:
            user_info_page.encrypt_home_dir()
        if autologin:
            user_info_page.set_auto_login()

        self._check_page_titles()
        if self.english_install:
            self.expectThat(self.current_page_title, Equals(self.eng_config['page_title']))

        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def ubuntu_one_page_tests(self, ):
        #self._update_current_step('stepUserInfo')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=True)
        logger.debug("run_ubuntu_one_page_tests()")
        skip_button = self.main_window.select_single('GtkButton', name='skip')
        self.pointing_device.click_object(skip_button)
        #TODO: add checks to the U1 page

    def progress_page_tests(self, ):
        #TODO: move here from emulator and use process manager to check window stack doesn't change
        # during the progress stage and if a dialog becomes top of stack we get
        # window title to work outwhich one. Currently polling on dbus for two specific dialogs is really horrible
        # for the logs and test design so need to find a cleaner way.
        pass

    def _add_new_partition(self, ):
        """ adds a new partition """
        logger.debug("_add_new_partition()")
        custom_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartAdvanced')
        tree_view = custom_page.select_single('GtkTreeView')
        item = tree_view.select_item(u'  free space')
        self.pointing_device.click_object(item)
        self.assertThat(item.selected, Equals(True),
                        "[Page:'{0}'] Free Space tree item not selected".format(
                            self.current_step
                        ))
        add_button = custom_page.select_single('GtkToolButton', BuilderName='partition_button_new')
        self.pointing_device.click_object(add_button)
        time.sleep(2)
        logger.debug('_add_new_partition complete')

    def _check_partition_created(self, mountPoint):
        """ Checks that the partition was created properly """
        time.sleep(5)
        # TODO: This needs fixing
        custom_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartAdvanced')
        tree_view = custom_page.select_single('GtkTreeView')
        items = tree_view.get_all_items()
        print('partition_tree_items')
        print('--------------------------------------------------------------')
        for item in items:
            if item.accessible_name == u'':
                print('empty item ------------')
            else:
                print(item.accessible_name)
        print('-----------------------------------------------------------------')

        #root = self.get_root_instance()
        #item = root.select_single('GtkTextCellAccessible',
        #                          accessible_name=mountPoint)
        #item.visible.wait_for(True)
        #assert item is not None

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
        message_one = "Expected %s page title '%s' to not equal \
        the previous %s page title '%s' but it does" % \
                      (self.current_step, self.current_page_title, self.step_before, self.previous_page_title)

        self.expectThat(self.previous_page_title, NotEquals(self.current_page_title), message=message_one)
        # THis second one catches the known bug for the stepPartAdvanced page title switching back to the prev page title
        message_two = "Expected %s page title '%s' to not equal the previous %s page title '%s' but it does" % \
                      (self.current_step, current_page_title.label, self.step_before, self.previous_page_title)
        #This only runs if the current page title changes from its initial value when page loaded
        if current_page_title.label != self.current_page_title:
            self.expectThat(self.previous_page_title,
                            NotEquals(current_page_title.label), message=message_two)
            self.expectThat(current_page_title.visible, Equals(True),
                            "[Page:'{0}'] Expect page title to be visible but it wasn't".format(
                                self.current_step
                            ))

    def _check_preparing_statebox(self, stateboxName, visible=True, imagestock='gtk-yes'):
        """ Checks the preparing page statebox's """
        logger.debug("Running checks on {0} StateBox".format(stateboxName))
        preparing_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPrepare')
        state_box = preparing_page.select_single('StateBox', BuilderName=stateboxName)
        logger.debug('check({0}, {1})'.format(visible, imagestock))
        logger.debug("Running checks.......")
        if visible:
            self.expectThat(state_box.visible, Equals(visible),
                            "StateBox.check(): Expected {0} statebox to be visible but it wasn't".format(
                                state_box.name))
            label = state_box.select_single('GtkLabel')
            self.expectThat(label.label, NotEquals(u''),
                            "[Page:'{0}'] Expected {1} Statebox's label to contain text but it didn't".format(
                                self.current_step, stateboxName
                            ))
            self.expectThat(label.visible, Equals(visible),
                            "[Page:'{0}'] Expected {1} Statebox label's visible property to be {2} ".format(
                                self.current_step, stateboxName, str(visible)
                            ))
            self.expectIsInstance(label.label, str,
                                  "[Page:'{0}'] Expected {1} Statebox's label to be unicode but it wasn't".format(
                                  self.current_step, stateboxName
                                  ))
            image = state_box.select_single('GtkImage')
            self.expectThat(image.stock, Equals(imagestock))
            self.expectThat(image.visible, Equals(visible))

        else:
            self.expectThat(state_box.visible, Equals(False),
                            "[Page:'{0}'] Expected {1} statebox to not be visible but it was".format(
                                self.current_step, stateboxName
                            ))

    def _options_tests(self, visible=[], hidden=[]):

        install_type_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartAsk')

        for option in visible:
            logger.info("selecting Visible object'{0}'".format(option))
            opt = install_type_page.select_single(BuilderName=option)
            self.expectThat(opt.visible, Equals(True),
                            "[Page:'{0}'] Expected {1} object to be visible but it wasn't".format(
                                self.current_step, opt.name
                            ))
            self.expectThat(opt.label, NotEquals(u''),
                            "[Page:'{0}'] Expected {1} objects label value to contain text but it didn't".format(
                                self.current_step, opt.name
                            ))
            self.expectIsInstance(opt.label, str,
                                  "[Page:'{0}'] Expected {1} objects label value to be unicode but it wasn't".format(
                                  self.current_step, opt.name
                                  ))
            if self.english_install:
                #if english install check english values
                self.eng_config = eng_label_values.stepPartAsk
                self.expectThat(opt.label, Equals(self.eng_config[option]))


        for option in hidden:
            logger.info("Selecting hidden object '{0}'".format(option))

            opt = install_type_page.select_single(BuilderName=option)
            self.expectThat(opt.visible, Equals(False),
                            "[Page:'{0}'] Expected {1} object to be not visible but it was".format(
                                self.current_step, opt.name
                            ))
            self.expectThat(opt.label, NotEquals(u''),
                            "[Page:'{0}'] Expected {1} objects label value to contain text but it didn't".format(
                                self.current_step, opt.name
                            ))
            self.expectIsInstance(opt.label, str,
                                  "[Page:'{0}'] Expected {1} objects label value to be unicode but it wasn't".format(
                                  self.current_step, opt.name
                                  ))

    def _select_install_type(self, install_type):
        pass

    def get_distribution(self, ):
        """Returns the name of the running distribution."""
        logger.debug("Detecting flavor")
        with open('/cdrom/.disk/info') as f:
            for line in f:
                distro = line[:max(line.find(' '), 0) or None]
                if distro:
                    logger.debug("{0} flavor detected".format(distro))
                    return str(distro)
                raise SystemError("Could not get distro name")
