# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2013
#
# Author: Daniel Chapman daniel@chapman-mail.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import random
import time
from autopilot.input import Pointer, Mouse, Keyboard
from ubiquity_autopilot_tests.emulators import AutopilotGtkEmulatorBase
from ubiquity_autopilot_tests.emulators import gtkcontrols, gtkaccessible
from ubiquity_autopilot_tests.emulators import EmulatorException
from ubiquity_autopilot_tests.tools.compare import expectThat

import logging
logger = logging.getLogger(__name__)


class GtkContainers(AutopilotGtkEmulatorBase):
    """ Base class for all gtkcontainers objects """
    def __init__(self, *args):
        super(GtkContainers, self).__init__(*args)
        self.pointing_device = Pointer(Mouse.create())


class StateBox(AutopilotGtkEmulatorBase):
    """ Emulator class for a statebox instance """

    def __init__(self, *args):
        super(StateBox, self).__init__(*args)
        self.pointing_device = Pointer(Mouse.create())

    def check(self, visible=True, imagestock='gtk-yes'):
        """ Checks the visibility, image and label of the statebox"""
        logger.debug('check({0}, {1})'.format(visible, imagestock))
        logger.debug("Running checks.......")
        if visible:
            expectThat(self.visible).equals(
                visible, msg="StateBox.check(): Expected {0} statebox to be visible but it wasn't".format(self.name))
            label = self.select_single('GtkLabel')
            label.check(visible)
            image = self.select_single('GtkImage')
            image.check(visible, imagestock)
        else:
            assert not visible


class GtkBox(GtkContainers):
    """ Emulator class for a GtkBox instance """
    def __init__(self, *args):
        super(GtkBox, self).__init__(*args)
        self.pointing_device = Pointer(Mouse.create())
        self.kbd = Keyboard.create()

    def get_random_language(self, ):
        """ gets a random language from the 'stepLanguage' page

        :returns: A random TreeView item from the language treeview
        :raises: EmulatorException if function is not called from the
                step language page object

        You can now use select_language_item

        """
        logger.debug("get_random_language()")
        if self.name == 'stepLanguage':
            language_item = self._get_install_language()
            if language_item is None:
                raise ValueError("Language could not be selected")
            return language_item
        raise RuntimeError("Function can only be used from a stepLanguage \
                            page object. Use .select_single('GtkBox, name='stepLanguage')")

    def select_language(self, item):
        """ Selects a language for the install

        You can either use get_random_language or if you want to set the install
        language instead of randomly selecting an item. Then select from the treeview
        using GtkTreeView.select_item and pass the returned item to select_language

        :param item: A treeview item object
        :raises: exception if function not called from stepLanguage page object"


        """
        if self.name == 'stepLanguage':
            logger.debug("select_language()")
            treeview = self.select_single('GtkTreeView')
            treeview.click()
            #for sanity lets ensure we always start at the top of the list
            logger.debug("Selecting top item of treeview list")
            self.kbd.press_and_release('Home')
            tree_items = treeview.get_all_items()
            top_item = tree_items[0]
            #If we are at the top
            if top_item.selected:
                logger.debug("top item {0} selected".format(top_item.accessible_name))
                #Now select required Language
                self.kbd.type(item.accessible_name[0:2])
                item.click()
                #check selected
                if item.selected:
                    logger.debug("Install language successfully selected! :-)")
                    return
                raise EmulatorException("Could not select Item")
            raise
        raise EmulatorException("Function can only be used from a stepLanguage \
                                page object. Use .select_single('GtkBox, name='stepLanguage')")

    def _get_install_language(self, ):
        """ Gets a random language for the install

        :returns: an object of a TreeView item for the chosen language
        """
        logger.debug("_get_install_language()")
        treeview = self.select_single('GtkTreeView')
        #lets get all items
        treeview_items = treeview.get_all_items()
        #first lets check all the items are valid unicode
        logger.debug("Checking all tree items are valid unicode")
        for item in treeview_items:
            logger.debug("Check tree item with name '%s' is unicode" % item.accessible_name)
            expectThat(item.accessible_name).is_unicode(
                msg="GtkBox._get_install_language(): Expected '{0}' tree item to be unicode but it isn't")

        #get a language which the first two chars can be ascii decoded
        test_language = self._get_decode_ascii_item(treeview_items)
        return test_language

    def _get_decode_ascii_item(self, items):
        """ decodes a list of unicode items """
        logger.debug("_get_decode_ascii_item()")
        # at the moment we can't select all locales as this would be a pain
        # to figure out all encodings for keyboard input
        lang_item = None
        l_ascii = None
        while True:
            lang_item = random.choice(items)
            l_unicode = lang_item.accessible_name
            logger.debug("Attempting to decode %s" % l_unicode)
            lan = l_unicode[0:2]
            try:
                l_ascii = lan.decode('ascii')
            except UnicodeEncodeError:
                logger.debug("%s could not be decoded" % l_unicode)
                pass
            if l_ascii:
                logger.debug("%s decoded successfully" % l_unicode)
                break
        logger.debug("Returning selected language: %s" % l_unicode)
        return lang_item

    def check_location_page(self):
        if self.name == 'stepLocation':
            location_map = self.select_single('CcTimezoneMap')
            expectThat(location_map.visible).equals(True, msg="Expected location map to be visible but it wasn't")
            location_entry = self.select_single(BuilderName='timezone_city_entry')
            expectThat(location_entry.visible).equals(True, msg="Expected location entry to be visible but it wasn't")
        else:
            raise ValueError("Function can only be called from a stepLocation page object")
    def select_location(self, location):
        """ Selects a location on the timezone map """
        if self.name == 'stepLocation':
            logger.debug("select_location({0})".format(location))

            location_map = self.select_single('CcTimezoneMap')
            self.pointing_device.move_to_object(location_map)
            #hmmmm this is tricky! and really hacky
            pos = self.pointing_device.position()
            x = pos[0]
            y = pos[1]
            x = x - 25  # px
            self.pointing_device.move(x, y)
            #TODO: Ensure we don't end up outside the maps globalRect
            while True:
                entry = self.select_single('GtkEntry')
                if entry.text != location:
                    pos = self.pointing_device.position()
                    x = pos[0]
                    y = pos[1]
                    y = y - 10  # px
                    self.pointing_device.move(x, y)
                    self.pointing_device.click()
                else:
                    expectThat(entry.text).equals(location)
                    logger.debug("Location; '{0}' selected".format(location))
                    break
        else:
            raise ValueError("Function can only be called from a stepLocation page object")

    def create_user(self, name, password):
        """ Creates a user account with password

        :param name: Username
        :param password: user password

        """
        logger.debug("create_user({0}, {1})".format(name, password))
        if self.name == 'stepUserInfo':
            self._check_user_info_page()
            self._enter_username(name)
            self._enter_password(password)
        else:
            raise

    def _check_user_info_page(self, ):
        """ Checks all the objects on the user info page """
        objects = ['hostname_label', 'username_label', 'password_label',
                   'verified_password_label', 'hostname_extra_label'
                   ]
        logger.debug("checking user info page objects ......")
        for i in objects:
            obj = self.select_single('GtkLabel', name=i)
            obj.check()

    def _enter_username(self, name):
        """ Enters the username

        :param name: username for user account
        """
        logger.debug("_enter_username({0})".format(name))
        entry = self.select_single('GtkEntry', name='fullname')
        with self.kbd.focused_type(entry) as kb:
            kb.press_and_release('Ctrl+a')
            kb.press_and_release('Delete')
            kb.type(name)
            expectThat(len(entry.text)).equals(
                len(name),
                msg="GtkBox._enter_username(): {0} != {1}, Expected {2} to be the same length as {3}".format(
                    str(len(entry.text)),
                    str(len(name)),
                    entry.text,
                    name))
        #lets get the fullname from the entry
        # as we don't know the kb layout till runtime
        fullname = entry.text
        logger.debug("Checking that name, username and hostname all contain '{0}'".format(name))
        #now check computer name contains username
        hostname_entry = self.select_single('GtkEntry', name='hostname')
        expectThat(hostname_entry.text).contains(
            fullname.lower(),
            msg="GtkBox._enter_username(): Expected the hostname entry: '{0}', to contain '{1}'".format(
                hostname_entry.text,
                fullname.lower()))
        #check username contains name
        username_entry = self.select_single('GtkEntry', name='username')
        expectThat(username_entry.text).contains(
            fullname.lower(),
            msg="GtkBox._enter_username(): Expected the username entry: '{0}', to contain '{1}'".format(
                username_entry.text,
                fullname.lower()))
        #check the GtkYes images are now visible
        logger.debug("Checking the stock 'gtk-yes' images are visible")
        images = ['fullname_ok', 'hostname_ok', 'username_ok']
        for image in images:
            img = self.select_single('GtkImage', name=image)
            expectThat(img.visible).equals(True, msg="Expected {0} image to be visible but it wasn't".format(img.name))
            expectThat(img.stock).equals('gtk-yes',
                                         msg="Expected {0} image to have a 'gtk-yes' stock image and not {1}".format(
                                             img.name, img.stock))

    def _enter_password(self, pwd, mismatch=False):
        """ enters the password

        :param pwd: password for user account
        :param mismatch: if true will cause the passwords to not match and then
                         will re-enter password to correct.
        """
        logger.debug("_enter_password({0}, mismatch={1})".format(pwd, mismatch))
        password_entry = self.select_single('GtkEntry', name='password')
        with self.kbd.focused_type(password_entry) as kb:
            kb.press_and_release('Ctrl+a')
            kb.press_and_release('Delete')
            kb.type(pwd)
            message = "GtkBox._enter_password(): expected {0} entry value '{1}' to be the same length as {2}".format(
                password_entry.name, password_entry.text, pwd
            )
            expectThat(len(password_entry.text)).equals(len(pwd), msg=message)
        verified_password_entry = self.select_single('GtkEntry', name='verified_password')
        if mismatch:
            pass  # TODO
        with self.kbd.focused_type(verified_password_entry) as kb:
            kb.press_and_release('Ctrl+a')
            kb.press_and_release('Delete')
            kb.type(pwd)
            expectThat(len(verified_password_entry.text)).equals(len(password_entry.text))
            assert verified_password_entry.text == password_entry.text, "Passwords didnt match"


class GtkScrolledWindow(GtkContainers):
    """ Emulator class for a GtkScrolledWindow instance """
    def __init__(self, *args):
        super(GtkScrolledWindow, self).__init__(*args)


class GtkAlignment(GtkContainers):
    """ Emulator class for a GtkAlignment instance """
    def __init__(self, *args):
        super(GtkAlignment, self).__init__(*args)
        self.pointing_device = Pointer(Mouse.create())
        self.kbd = Keyboard.create()

    def default_install(self, ):
        """ Tests page objects and uses the default selected option """
        visible_options = ['use_device', 'use_device_desc',
                           'use_crypto', 'use_crypto_desc', 'use_lvm', 'use_lvm_desc',
                           'custom_partitioning', 'custom_partitioning_desc']

        hidden_options = ['reuse_partition', 'reuse_partition_desc',
                          'resize_use_free', 'resize_use_free_desc',
                          'replace_partition', 'replace_partition_desc']

        self._options_tests(visible_options, hidden_options)

    def lvm_install(self, ):
        visible_options = ['use_device', 'use_device_desc',
                           'use_crypto', 'use_crypto_desc', 'use_lvm', 'use_lvm_desc',
                           'custom_partitioning', 'custom_partitioning_desc']

        hidden_options = ['reuse_partition', 'reuse_partition_desc',
                          'resize_use_free', 'resize_use_free_desc',
                          'replace_partition', 'replace_partition_desc']

        self._options_tests(visible_options, hidden_options)
        lvm_chk_button = self.select_single('GtkCheckButton', name='use_lvm')
        lvm_chk_button.click()

    def lvm_encrypt_install(self, ):
        visible_options = ['use_device', 'use_device_desc',
                           'use_crypto', 'use_crypto_desc', 'use_lvm', 'use_lvm_desc',
                           'custom_partitioning', 'custom_partitioning_desc']

        hidden_options = ['reuse_partition', 'reuse_partition_desc',
                          'resize_use_free', 'resize_use_free_desc',
                          'replace_partition', 'replace_partition_desc']

        self._options_tests(visible_options, hidden_options)
        lvm_crypto_chk_button = self.select_single('GtkCheckButton', name='use_crypto')
        lvm_crypto_chk_button.click()
        lvm_chk_button = self.select_single('GtkCheckButton', name='use_lvm')
        expectThat(lvm_chk_button.active).equals(True,
                                                 msg="Expected the {0} checkbutton to be visible but it wasn't".format(
                                                     lvm_chk_button.name
                                                 ))

    def custom_install(self, ):
        visible_options = ['use_device', 'use_device_desc',
                           'use_crypto', 'use_crypto_desc', 'use_lvm', 'use_lvm_desc',
                           'custom_partitioning', 'custom_partitioning_desc']

        hidden_options = ['reuse_partition', 'reuse_partition_desc',
                          'resize_use_free', 'resize_use_free_desc',
                          'replace_partition', 'replace_partition_desc']

        self._options_tests(visible_options, hidden_options)
        ctm_chk_button = self.select_single(BuilderName='custom_partitioning')
        self.pointing_device.click_object(ctm_chk_button)

    def _options_tests(self, visible=[], hidden=[]):

        if self.name == 'stepPartAsk':
            for option in visible:
                logger.info("selecting Visible object'{0}'".format(option))
                opt = self.select_single(BuilderName=option)
                opt.check()

            for option in hidden:
                logger.info("Selecting hidden object '{0}'".format(option))

                opt = self.select_single(BuilderName=option)
                opt.check(visible=False)
        # we would normally now select an item but we are sticking with the default for now
        else:
            raise ValueError(
                "Function can only be called from the stepPartAsk page object")

    def check_layouts(self, ):
        if self.name == 'stepKeyboardConf':
            treeviews = self.select_many('GtkTreeView')
            for treeview in treeviews:
                items = treeview.get_all_items()
                for item in items:
                    expectThat(item.accessible_name).is_unicode()
                    expectThat(item.accessible_name).not_equals(u'')

    def test_layout(self, ):
        if self.name == 'stepKeyboardConf':
            entry = self.select_single('GtkEntry')
            with self.kbd.focused_type(entry) as kb:
                kb.type(u'Testing keyboard layout')
                message = "Expected {0} (the length of the keyboard entry text) to be {1}".format(
                    len(entry.text), len(u'Testing keyboard layout')
                )
                expectThat(len(entry.text)).equals(len(u'Testing keyboard layout'), msg=message)
                expectThat(entry.text).is_unicode()
        else:
            raise ValueError(
                "Function can only be called from the stepKeyboardConf page object")

    def check_crypto_page(self, ):
        """ Checks all items on the stepPartCrypto page
        """
        if self.name == 'stepPartCrypto':
            items = ['verified_crypto_label', 'crypto_label', 'crypto_description',
                     'crypto_warning', 'crypto_extra_label', 'crypto_extra_time',
                     'crypto_description_2', 'crypto_overwrite_space']
            for i in items:
                item = self.select_single(BuilderName=i)
                item.check()
        else:
            raise ValueError(
                "Check_crypto_page() can only be called from stepPartCrypto page object"
            )

    def enter_crypto_phrase(self, cryptoPhrase):
        if self.name == 'stepPartCrypto':

            while True:
                self._enter_pass_phrase(cryptoPhrase)
                match = self._check_crypto_phrase_match()

                if match:
                    break
        else:
            raise ValueError(
                "enter_crypto_phrase() can only be called from stepPartCrypto page object"
            )

    def _enter_pass_phrase(self, phrase):

        pwd_entries = ['password', 'verified_password']
        for i in pwd_entries:
            entry = self.select_single(BuilderName=i)
            with self.kbd.focused_type(entry) as kb:
                kb.press_and_release('Ctrl+a')
                kb.press_and_release('Delete')
                expectThat(entry.text).equals(u'', msg='{0} entry text was not cleared properly'.format(entry.name))
                kb.type(phrase)

    def _check_crypto_phrase_match(self, ):
        pwd1 = self.select_single(BuilderName='password').text
        pwd2 = self.select_single(BuilderName='verified_password').text
        if pwd1 == pwd2:
            return True
        else:
            return False

    def check_custom_page(self, ):
        if self.name == 'stepPartAdvanced':
            treeview = self.select_single('GtkTreeView')
            expectThat(treeview.visible).equals(True)
            obj_list = ['partition_button_new', 'partition_button_delete', 'partition_button_edit',
                        'partition_button_edit', 'partition_button_new_label']
            for name in obj_list:
                obj = self.select_single(BuilderName=name)
                expectThat(obj.visible).equals(True, msg="{0} object was not visible".format(obj.name))
        else:
            raise ValueError(
                "Check_custom_page() can only be called from stepPartAdvanced page object"
            )

    def create_new_partition_table(self, ):
        if self.name == 'stepPartAdvanced':
            new_partition_button = self.select_single(BuilderName='partition_button_new_label')
            self.pointing_device.click_object(new_partition_button)
            time.sleep(5)
            self.kbd.press_and_release('Right')
            self.kbd.press_and_release('Enter')
            time.sleep(5)
        else:
            raise ValueError(
                "create_new_partition_table() can only be called from stepPartAdvanced page object"
            )
