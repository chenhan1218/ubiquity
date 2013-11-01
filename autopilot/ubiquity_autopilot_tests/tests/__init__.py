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
import random

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
from ubiquity_autopilot_tests.emulators.partconfig import (
    Config1,
    Config2,
    Config3,
    Config4,
    Config5,
    Config6
)
custom_configs = [Config1, Config2, Config3, Config4, Config5, Config6]

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
        self.pointing_device.click_object(nxt_button)

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
        self.pointing_device.click_object(nxt_button)

    def welcome_page_tests(self, lang=None):
        """ Runs the tests for the Welcome Page
        :param lang: The treeview label value (e.g 'English') of the required language.
                     If None will pick a random language from the tree.
                     ..NOTE: You should only specify a language if the test relies
                           upon a specific language. It is better to write the unittests
                           to work for any language.
        """
        self._update_current_step('stepLanguage')
        self._check_navigation_buttons()
        self._run_welcome_page_tests(lang)
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
        self._run_preparing_page_tests(updates,
                                       thirdParty,
                                       networkConnection,
                                       sufficientSpace,
                                       powerSource)
        self._check_page_titles()
        self._check_navigation_buttons()

    def installation_type_page_tests(self, default=False, lvm=False,
                                     lvmEncrypt=False, custom=False):
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
        self._run_installation_type_page_tests(_default=default,
                                               _lvm=lvm,
                                               _lvmEncrypt=lvmEncrypt,
                                               _custom=custom)
        self._check_page_titles()
        self._check_navigation_buttons()

    def lvm_crypto_page_tests(self, crypto_password):
        """ Runs the tests for the LVM encryption password page

        :param crypto_password: *String*, password to be used for the encryption

        """
        self._update_current_step('stepPartCrypto')
        self._check_navigation_buttons()
        self._update_page_titles()
        self._run_step_part_crypto_page_tests(crypto_password)
        self._check_page_titles()
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
        self._run_custom_partition_page_tests(part_config)
        self._check_page_titles()
        self._check_navigation_buttons()

    def location_page_tests(self, ):
        self._update_current_step('stepLocation')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        self._run_location_page_tests()
        self._check_page_titles()
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def keyboard_layout_page_tests(self, ):
        self._update_current_step('stepKeyboardConf')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        self._run_keyboard_layout_page_tests()
        self._check_page_titles()
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def user_info_page_tests(self, username, pwd, encrypted=False, autologin=False):
        self._update_current_step('stepUserInfo')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)
        self._update_page_titles()
        self._run_user_info_page_tests(username, pwd,
                                                  encrypted, autologin)
        self._check_page_titles()
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=False)

    def ubuntu_one_page_tests(self, ):
        #self._update_current_step('stepUserInfo')
        self._check_navigation_buttons(continue_button=True, back_button=True,
                                       quit_button=False, skip_button=True)
        self._update_page_titles()
        self._run_ubuntu_one_page_tests()

    def progress_page_tests(self, ):
        self._check_navigation_buttons(continue_button=False, back_button=False,
                                       quit_button=False, skip_button=False)
        self._run_install_progress_page_tests()

    def _run_welcome_page_tests(self, lang=None):

        #first check pageTitle visible and correct if label given
        logger.debug("run_welcome_page_tests()")
        #selecting an install language
        logger.debug("Selecting stepLanguage page object")
        welcome_page = self.main_window.select_single('GtkBox',
                                                      name='stepLanguage')
        if lang:
            treeview = welcome_page.select_single('GtkTreeView')
            item = treeview.select_item(lang)
            language = item
        else:
            language = welcome_page.get_random_language()
        welcome_page.select_language(language)
        ##Test release notes label is visible
        logger.debug("Checking the release_notes_label")
        release_notes_label = welcome_page.select_single('GtkLabel',
                                                         BuilderName='release_notes_label')
        self.expectThat(release_notes_label.visible, Equals(True))
        self.expectThat(release_notes_label.label, NotEquals(u''))
        self.expectIsInstance(release_notes_label.label, unicode)
        self.pointing_device.move_to_object(release_notes_label)

    def _run_preparing_page_tests(self, updates=False, thirdParty=False,
                                  networkConnection=True, sufficientSpace=True,
                                  powerSource=False):

        logger.debug("run_preparing_page_tests()")
        logger.debug("selecting stepPrepare page")
        preparing_page = self.main_window.select_single('GtkAlignment',
                                                        BuilderName='stepPrepare')
        objList = ['prepare_best_results', 'prepare_foss_disclaimer',
                   'prepare_download_updates', 'prepare_nonfree_software']
        for obj in objList:
            logging.debug("Running checks on {0} object".format(obj))
            obj = preparing_page.select_single(BuilderName=obj)
            obj.check()

        #check network connection statebox
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

    def _run_installation_type_page_tests(self, _default=False, _lvm=False,
                                          _lvmEncrypt=False, _custom=False):
        logger.debug(
            "run_installation_type_page_tests({0}, {1}, {2}, {3})".format(_default,
                                                                          _lvm,
                                                                          _lvmEncrypt,
                                                                          _custom))
        logger.debug("Selecting stepPartAsk page.....")
        install_type_page = self.main_window.select_single('GtkAlignment',
                                                           BuilderName='stepPartAsk')
        #check heading is visible
        heading = install_type_page.select_single('GtkLabel', BuilderName='part_ask_heading')
        heading.check()

        if _default:
            logger.debug("Default installation selected")
            install_type_page.default_install()

        if _lvm:
            logger.debug("LVM installation selected")
            install_type_page.lvm_install()

        if _lvmEncrypt:
            logger.debug("LVM with Encrypted installation selected")
            install_type_page.lvm_encrypt_install()

        if _custom:
            logger.debug("Custom installation selected")
            install_type_page.custom_install()

    def _run_step_part_crypto_page_tests(self, cryptoPhrase):

        logger.debug("run_step_part_crypto_page_tests({0})".format(cryptoPhrase))
        logger.debug('Selecting stepPartCrypto page object')
        crypto_page = self.main_window.select_single('GtkAlignment', BuilderName='stepPartCrypto')

        self._check_crypto_page()
        crypto_page.enter_crypto_phrase(cryptoPhrase)
        pwd_entries = ['password', 'verified_password']
        for i in pwd_entries:
            entry = crypto_page.select_single(BuilderName=i)
            self.expectThat(entry.text, Equals(cryptoPhrase))

    def _run_custom_partition_page_tests(self, partition_config=None):

        logger.debug("run_custom_partition_page_tests()")
        logger.debug("Selecting the stepPartAdvanced page object")
        custom_page = self.main_window.select_single('GtkAlignment',
                                                     BuilderName='stepPartAdvanced')
        self._check_custom_page()
        logger.debug("Sleeping while we wait for all UI elements to fully load")
        time.sleep(5)  # need to give time for all UI elements to load
        custom_page.create_new_partition_table()
        #lets create the partitions from here
        if partition_config:
            logger.debug("Setting the given partition config")
            config = partition_config
        else:
            logger.debug("Selecting a random partition config")
            config = random.choice(custom_configs)

        for elem in config:
            custom_page.add_new_partition()

            partition_dialog = self.main_window.get_dialog('GtkDialog',
                                                           BuilderName='partition_dialog')
            self.assertThat(partition_dialog.visible, Eventually(Equals(True)))
            partition_dialog.set_partition_size(elem['PartitionSize'])
            partition_dialog.set_partition_location(elem['Position'])
            partition_dialog.set_partition_type(elem['PartitionType'])
            partition_dialog.set_file_system_type(elem['FileSystemType'])
            partition_dialog.set_mount_point(elem['MountPoint'])
            ok_button = partition_dialog.select_single('GtkButton',
                                                       BuilderName='partition_dialog_okbutton')
            ok_button.click()
            self.assertThat(partition_dialog.visible, Eventually(Equals(False)))
            self._check_partition_created(elem)

    def _run_location_page_tests(self, ):
        """ Runs the test for the Location page

        Due to not being able to introspect the timezone map we only have a
        choice of 4 locations which get selected at random.

        """
        logger.debug('run_location_page_tests()')

        logger.debug("Selecting stepLocation page object")
        location_page = self.main_window.select_single('GtkBox', BuilderName='stepLocation')
        self._check_location_page()
        location = ['London', 'Paris', 'Madrid', 'Algiers']
        location_page.select_location(random.choice(location))

    def _run_keyboard_layout_page_tests(self, ):
        """ Runs the unittests for the keyboard layout page """
        logger.debug("run_keyboard_layout_page_tests()")

        logger.debug("Selecting the stepKeyboardCOnf page object")
        keyboard_page = self.main_window.select_single('GtkAlignment', BuilderName='stepKeyboardConf')

        keyboard_page.check_layouts()
        keyboard_page.test_layout()
        #TODO: detect layout
        #keyboard_page.detect_layout()

    def _run_user_info_page_tests(self, user_name, password,
                                 encrypt=False, auto_login=False):
        """ Runs unittests for the User Info Page

        :param user_name:*String*, name of user

        :param password: *String*, password for user

        :param encrypt: *Bool* if true encypts the home directory

        :param auto_login: *Bool* if true sets the user account to login
                           automagically

        """
        logger.debug(
            "run_user_info_page_tests({0}, {1}, {2}, {3})".format(
                user_name, password, encrypt, auto_login
            )
        )

        logger.debug("Selecting stepUserInfo page")
        user_info_page = self.main_window.select_single('GtkBox', BuilderName='stepUserInfo')
        self._check_user_info_page()
        user_info_page.create_user(user_name, password)

        if encrypt:
            user_info_page.encrypt_home_dir()
        if auto_login:
            user_info_page.set_auto_login()

    def _run_ubuntu_one_page_tests(self, ):
        """ Runs the unittests for the U1 sign in"""
        logger.debug("run_ubuntu_one_page_tests()")
        skip_button = self.main_window.select_single('GtkButton', name='skip')
        skip_button.click()

    def _run_install_progress_page_tests(self, ):
        ''' Runs the test for the installation progress page

            This method tracks the current progress of the install
            by using the fraction property of the progress bar
            to assertain the percentage complete.

        '''
        logger.debug("run_install_progress_page_tests()")
        #We cant assert page title here as its an external html page
        #Maybe try assert WebKitWebView is visible
        webkitwindow = self.main_window.select_single('GtkScrolledWindow',
                                                      name='webkit_scrolled_window')
        self.expectThat(webkitwindow.visible, Equals(True),
                        "Expected the slideshow to be visible, but it wasn't")

        #Can we track the progress percentage?
        self.install_progress = self.main_window.select_single('GtkProgressBar',
                                                               name='install_progress')

        #Copying files progress bar
        self._track_install_progress_bar()

        self.install_progress.fraction.wait_for(0.0, timeout=120)
        #And now the install progress bar
        self._track_install_progress_bar()

    def _track_install_progress_bar(self):
        """Gets the value of the fraction property of the progress bar

            so we can see when the progress bar is complete

        """
        logger.debug("_track_install_progress_bar()")
        progress = 0.0
        complete = 1.0
        logger.debug('Percentage complete "{0:.0f}%"'.format(progress * 100))
        while progress < complete:
            #keep updating fraction value
            progress = self.install_progress.fraction
            # lets sleep for a second on each loop until we get near the end of the progress bar
            if progress < 0.7:
                time.sleep(1)

            logger.debug('Percentage complete "{0:.0f}%"'.format(progress * 100))
            #check for install errors while waiting
            try:
                crash_dialog = self.main_window.get_dialog('GtkDialog', BuilderName='crash_dialog')
                logger.debug("Checking crash dialog hasn't appeared....")
                if crash_dialog.visibe:
                    logger.error("Crash Dialog appeared")
                    assert not crash_dialog.visible, "Crash Dialog appeared! Something went wrong!!!"
                    progress = 1.0
            except Exception:
                pass
            # Lets try and grab the grub failed message box on the fly
            try:
                logger.debug("Checking failed grub install dialog hasn't appeared.......")
                grub_dialog = self.main_window.get_dialog('GtkMessageDialog')
                if grub_dialog.visible:
                    logger.error("The Grub installation failed dialog appeared :-(")
                    assert grub_dialog.visible != 1, "The Grub installation failed"
                    progress = 1.0
            except Exception:
                pass

    def _check_partition_created(self, conf):
        """ Checks that the partition was created properly """
        time.sleep(5)
        # TODO: This needs fixing
        custom_page = self.main_window.select_single('GtkAlignment',
                                                     BuilderName='stepPartAdvanced')
        tree_view = custom_page.select_single('GtkTreeView')
        items = tree_view.get_all_items()
        print 'partition_tree_items'
        print '--------------------------------------------------------------'
        for item in items:
            if item.accessible_name == u'':
                print 'empty item ------------'
            else:
                print item.accessible_name
        print '-----------------------------------------------------------------'

        #root = self.get_root_instance()
        #item = root.select_single('GtkTextCellAccessible',
        #                          accessible_name=mountPoint)
        #item.visible.wait_for(True)
        #assert item is not None

    def _check_crypto_page(self, ):
        """ Checks all items on the stepPartCrypto page
        """
        items = ['verified_crypto_label', 'crypto_label', 'crypto_description',
                 'crypto_warning', 'crypto_extra_label', 'crypto_extra_time',
                 'crypto_description_2', 'crypto_overwrite_space']
        for i in items:
            #TODO: change to crypto.select_single
            item = self.main_window.select_single(BuilderName=i)
            item.check()

    def _check_custom_page(self, ):
        custom_page = self.main_window.select_single('GtkAlignment',
                                                     BuilderName='stepPartAdvanced')
        treeview = custom_page.select_single('GtkTreeView')
        self.expectThat(treeview.visible, Equals(True))
        obj_list = ['partition_button_new', 'partition_button_delete', 'partition_button_edit',
                    'partition_button_edit', 'partition_button_new_label']
        for name in obj_list:
            obj = custom_page.select_single(BuilderName=name)
            self.expectThat(obj.visible, Equals(True), "{0} object was not visible".format(obj.name))

    def _check_location_page(self):
        #TODO: change to location_page.select_single
        location_map = self.main_window.select_single('CcTimezoneMap')
        self.expectThat(location_map.visible, Equals(True),
                        "Expected location map to be visible but it wasn't")
        location_entry = self.main_window.select_single(BuilderName='timezone_city_entry')
        self.expectThat(location_entry.visible, Equals(True),
                        "Expected location entry to be visible but it wasn't")

    def _check_user_info_page(self, ):
        """ Checks all the objects on the user info page """
        objects = ['hostname_label', 'username_label', 'password_label',
                   'verified_password_label', 'hostname_extra_label'
                   ]
        logger.debug("checking user info page objects ......")
        for i in objects:
            #TODO: change to user_info_page.select_single
            obj = self.main_window.select_single('GtkLabel', name=i)
            obj.check()

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
        # only the next button not being visible should fail the test
        self.assertThat(con_button.visible, Equals(continue_button))

        bk_button = self.main_window.select_single('GtkButton', name='back')
        self.expectThat(bk_button.visible, Equals(back_button))

        qt_button = self.main_window.select_single('GtkButton', name='quit')
        self.expectThat(qt_button.visible, Equals(quit_button))

        skp_button = self.main_window.select_single('GtkButton', name='skip')
        self.expectThat(skp_button.visible, Equals(skip_button))

    def _check_page_titles(self, ):
        current_page_title = self.main_window.select_single('GtkLabel',
                                                            BuilderName='page_title')
        message_one = "Expected %s page title '%s' to not equal \
        the previous %s page title '%s' but it does" % \
                  (self.current_step, self.current_page_title, self.step_before, self.previous_page_title)

        self.expectThat(self.previous_page_title, NotEquals(self.current_page_title), message_one)
        # THis second one catches the known bug for the stepPartAdvanced page title switching back to the prev page title
        message_two = "Expected %s page title '%s' to not equal the previous %s page title '%s' but it does" % \
                      (self.current_step, current_page_title.label, self.step_before, self.previous_page_title)
        self.expectThat(self.previous_page_title,
                        NotEquals(current_page_title.label), message=message_two)
        self.expectThat(current_page_title.visible, Equals(True))

    def _check_preparing_statebox(self, stateboxName, visible=True, imagestock='gtk-yes'):
        """ Checks the preparing page statebox's """
        logger.debug("Running checks on {0} StateBox".format(stateboxName))
        preparing_page = self.main_window.select_single('GtkAlignment',
                                                        BuilderName='stepPrepare')
        state_box = preparing_page.select_single('StateBox',
                                                 BuilderName=stateboxName)
        state_box.check(visible, imagestock)

    def _update_current_step(self, name):
        logger.debug("Updating current step to %s" % name)
        self.step_before = self.current_step
        self.current_step = name

    def _update_page_titles(self, ):
        self.previous_page_title = self.current_page_title
        self.current_page_title = self.main_window.select_single('GtkLabel',
                                                                 BuilderName='page_title').label

    def get_distribution(self, ):
        """Returns the name of the running distribution."""
        proc = subprocess.Popen(
            ['lsb_release', '-is'], stdout=subprocess.PIPE,
            universal_newlines=True)
        distro = proc.communicate()[0].strip()
        return str(distro)
