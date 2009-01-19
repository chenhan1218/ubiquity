# -*- coding: utf-8 -*-
#
# «mythbuntu-ui» - Mythbuntu user interface
#
# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006, 2007, 2008 Canonical Ltd.
# Copyright (C) 2007-2009, Mario Limonciello, for Mythbuntu
# Copyright (C) 2007, Jared Greenwald, for Mythbuntu
#
# Authors:
#
# - Original gtk-ui.py that this is based upon:
#   - Javier Carranza <javier.carranza#interactors._coop>
#   - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
#   - Antonio Olmo Titos <aolmo#emergya._info>
#   - Gumer Coronel Pérez <gcoronel#emergya._info>
#   - Colin Watson <cjwatson@ubuntu.com>
#   - Evan Dandrea <evand@ubuntu.com>
#   - Mario Limonciello <superm1@ubuntu.com>
#
# - This Document:
#   - Mario Limonciello <superm1@mythbuntu.org>
#   - Jared Greenwald <greenwaldjared@gmail.com>
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or at your option)
# any later version.
#
# Ubiquity is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with Ubiquity; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import os
import re
import string
import subprocess
import syslog
import signal
import inspect

import gtk

#Mythbuntu common functionality
from mythbuntu_common.lirc import LircHandler
from mythbuntu_common.mysql import MySQLHandler
from mythbuntu_common.dictionaries import *

#Mythbuntu ubiquity imports
from ubiquity.components import mythbuntu, mythbuntu_install

#Ubiquity imports
from ubiquity.misc import *
import ubiquity.frontend.gtk_ui as ParentFrontend
ParentFrontend.install = mythbuntu_install
ParentFrontend.summary = mythbuntu_install

MYTHPAGES = [
    "mythbuntu_stepInstallType",
    "mythbuntu_stepCustomInstallType",
    "mythbuntu_stepPlugins",
    "tab_themes",
    "mythbuntu_stepServices",
    "mythbuntu_stepPasswords",
    "tab_remote_control",
    "mythbuntu_stepDrivers",
    "mythbuntu_stepBackendSetup"
]

class Wizard(ParentFrontend.Wizard):

#Overriden Methods
    def __init__(self, distro):
        #Remove migration assistant
        del os.environ['UBIQUITY_MIGRATION_ASSISTANT']
        place=ParentFrontend.BREADCRUMB_STEPS["stepReady"]

        #Max steps
        ParentFrontend.BREADCRUMB_MAX_STEP = place + len(MYTHPAGES)

        #update location of summary page
        ParentFrontend.BREADCRUMB_STEPS["stepReady"]=place+len(MYTHPAGES)-1

        #Add in final page
        final_page=MYTHPAGES.pop()
        ParentFrontend.BREADCRUMB_STEPS[final_page]=place+len(MYTHPAGES)+1
        ParentFrontend.SUBPAGES.append(final_page)

        #Add in individual mythpages pages
        for string in MYTHPAGES:
            ParentFrontend.BREADCRUMB_STEPS[string]=place
            ParentFrontend.SUBPAGES.insert(len(ParentFrontend.SUBPAGES)-2,string)
            place+=1

        ParentFrontend.Wizard.__init__(self,distro)

    def allow_change_step(self,allow):
        """Normally used to determine if we can progress pages.  We have to override
           this function to determine whether this is a skippable page."""

        #This skipping condition only happens when called with False
        if not allow:
            #do stuff only if we are getting called from a function
            #called run.  No not too ambiguous, right?
            if inspect.stack()[1][3] == 'run':
                new_name = self.dbfilter.__class__.__name__
                advanced=self.get_advanced()
                type = self.get_installtype()
                if (not advanced and \
                                     (new_name == 'MythbuntuInstallType' or \
                                      new_name == 'MythbuntuPlugins' or \
                                      new_name == 'MythbuntuThemes' or \
                                      new_name == 'MythbuntuServices' or \
                                      new_name == 'MythbuntuPasswords')) or \
                   ('Frontend' not in type and \
                                     (new_name == 'MythbuntuThemes' or \
                                      new_name == 'MythbuntuRemote')):
                    self.dbfilter.start(auto_process=True)
                    if not self.backup:
                        self.dbfilter.ok_handler()
                    else:
                        self.dbfilter.cancel_handler()
                    self.dbfilter = mythbuntu.MythbuntuPageSkipper(self)
                    self.dbfilter_status=None

        #Finally do something releated to step changing
        ParentFrontend.Wizard.allow_change_step(self,allow)

    def customize_installer(self):
        """Initial UI setup."""
        #Prepopulate some dynamic pages
        self.populate_lirc()
        self.populate_video()
        self.populate_mysql()
        self.backup=False

        #Default to auto login, but don't make it mandatory
        #This requires disabling encrypted FS
        self.set_auto_login(True)
        self.login_encrypt.set_sensitive(False)

        #Remove their summary page.  ours is better
        self.pages.pop()

        #Insert all of our pages
        for page in [mythbuntu.MythbuntuAdvancedType,
            mythbuntu.MythbuntuInstallType, mythbuntu.MythbuntuPlugins,
            mythbuntu.MythbuntuThemes, mythbuntu.MythbuntuServices,
            mythbuntu.MythbuntuPasswords, mythbuntu.MythbuntuRemote,
            mythbuntu.MythbuntuDrivers, mythbuntu_install.Summary]:
            self.pages.append(page)

        ParentFrontend.Wizard.customize_installer(self)

    def run_success_cmd(self):
        """Runs mythbuntu post post install GUI step"""
        if not 'UBIQUITY_AUTOMATIC' in os.environ and self.get_installtype() != "Frontend":
            self.live_installer.show()
            self.installing = False
            self.steps.next_page()
            self.back.hide()
            self.quit.hide()
            self.next.set_label("Finish")
            gtk.main()
            self.live_installer.hide()
        ParentFrontend.Wizard.run_success_cmd(self)

    def set_page(self, n):
        if n == 'MythbuntuAdvancedType':
            cur = self.mythbuntu_stepInstallType
        elif n == 'MythbuntuRemote':
            cur = self.tab_remote_control
        elif n == 'MythbuntuDrivers':
            cur = self.mythbuntu_stepDrivers
        elif n == 'MythbuntuInstallType':
            cur = self.mythbuntu_stepCustomInstallType
        elif n == 'MythbuntuPlugins':
            cur = self.mythbuntu_stepPlugins
        elif n == 'MythbuntuThemes':
            cur = self.tab_themes
        elif n == 'MythbuntuPasswords':
            cur = self.mythbuntu_stepPasswords
            if "Master" not in self.get_installtype():
                self.allow_go_forward(False)
        elif n == 'MythbuntuServices':
            cur = self.mythbuntu_stepServices
        else:
            ParentFrontend.Wizard.set_page(self,n)
            return
        self.run_automation_error_cmd()
        self.backup = False
        self.live_installer.show()
        self.set_current_page(self.steps.page_num(cur))

####################
#Helper Functions  #
####################
#Called for initialization and calculation on a page

    def populate_lirc(self):
            """Fills the lirc pages with the appropriate data"""
            self.remote_count = 0
            self.transmitter_count = 0
            self.lirc=LircHandler()
            for item in self.lirc.get_possible_devices("remote"):
                if "Custom" not in item and "Blaster" not in item:
                    self.remote_list.append_text(item)
                    self.remote_count = self.remote_count + 1
            for item in self.lirc.get_possible_devices("transmitter"):
                if "Custom" not in item:
                    self.transmitter_list.append_text(item)
                    self.transmitter_count = self.transmitter_count + 1
            self.remote_list.set_active(0)
            self.transmitter_list.set_active(0)

    def populate_video(self):
        """Finds the currently active video driver"""
        dictionary=get_graphics_dictionary()
        for driver in dictionary:
            self.video_driver.append_text(driver)
        self.video_driver.append_text("Open Source Driver")
        self.video_driver.set_active(len(dictionary))
        self.tvoutstandard.set_active(0)
        self.tvouttype.set_active(0)

    def populate_mysql(self):
        """Puts a new random mysql password into the UI for each run
           This ensures that passwords don't ever get cached"""
        self.mysql=MySQLHandler()
        new_pass_caller = subprocess.Popen(['pwgen','-s','8'],stdout=subprocess.PIPE)
        self.mysql_password.set_text(string.split(new_pass_caller.communicate()[0])[0])

    def mythbuntu_password(self,widget):
        """Checks that certain passwords meet requirements"""
        #For the services page, the only password we have is the VNC
        if (widget is not None and widget.get_name() == 'vnc_password'):
            password= widget.get_text().split(' ')[0]
            if len(password) >= 6:
                self.allow_go_forward(True)
                self.allow_go_backward(True)
                self.vnc_error_image.hide()
            else:
                self.allow_go_forward(False)
                self.allow_go_backward(False)
                self.vnc_error_image.show()
        elif (widget is not None and widget.get_name() == 'mythweb_username'):
            username = widget.get_text().split(' ')[0]
            if len(username) >= 1:
                self.mythweb_user_error_image.hide()
            else:
                self.mythweb_user_error_image.show()
        elif (widget is not None and widget.get_name() == 'mythweb_password'):
            password = widget.get_text().split(' ')[0]
            if len(password) >= 1:
                self.mythweb_pass_error_image.hide()
            else:
                self.mythweb_pass_error_image.show()

        elif (widget is not None and widget.get_name() == 'mysql_root_password'):
            password = widget.get_text().split(' ')[0]
            if len(password) >= 1:
                self.mysql_root_error_image.hide()
            else:
                self.mysql_root_error_image.show()

        #The password check page is much more complex. Pieces have to be
        #done in a sequential order
        if (self.usemysqlrootpassword.get_active() or self.usemythwebpassword.get_active()):
            mysql_root_flag = self.mysql_root_error_image.flags() & gtk.VISIBLE
            mythweb_user_flag = self.mythweb_user_error_image.flags() & gtk.VISIBLE
            mythweb_pass_flag = self.mythweb_pass_error_image.flags() & gtk.VISIBLE
            result = not (mythweb_user_flag | mythweb_pass_flag | mysql_root_flag)
            self.allow_go_forward(result)
            self.allow_go_backward(result)

    def do_mythtv_setup(self,widget):
        """Spawn MythTV-Setup binary."""
        self.live_installer.hide()
        self.refresh()
        execute_root("/usr/share/ubiquity/mythbuntu-setup")
        self.live_installer.show()

    def do_connection_test(self,widget):
        """Tests to make sure that the backend is accessible"""
        config={}
        config["user"]=self.mysql_user.get_text()
        config["password"]=self.mysql_password.get_text()
        config["server"]=self.mysql_server.get_text()
        config["database"]=self.mysql_database.get_text()
        self.mysql.update_config(config)
        result=self.mysql.do_connection_test()
        if result == "Successful":
            self.allow_go_forward(True)
        else:
            self.allow_go_forward(False)
        self.connection_results_label.show()
        self.connection_results.set_text(result)

#####################
#Preseeding Functions#
#####################
#Used to preset the status of an element in the GUI

    def set_advanced(self,enable):
        """Preseeds whether this is an advanced install"""
        enable = create_bool(enable)
        self.custominstall.set_active(enable)

    def set_installtype(self,type):
        """Preseeds the type of custom install"""
        if type == "Set Top Box":
            self.stb.set_active(True)
        elif type == "Frontend":
            self.fe.set_active(True)
        elif type == "Slave Backend":
            self.slave_be.set_active(True)
        elif type == "Master Backend":
            self.master_be.set_active(True)
        elif type == "Slave Backend/Frontend":
            self.slave_be_fe.set_active(True)
        else:
            self.master_be_fe.set_active(True)

    def set_themes(self,names):
        """Preseeds the themes that will be removed"""
        lists = [get_official_theme_dictionary(self),get_community_theme_dictionary(self)]
        self._preseed_list(lists,names,False)

    def set_plugin(self,name,value):
        """Preseeds the status of a plugin"""
        lists = [get_frontend_plugin_dictionary(self),get_backend_plugin_dictionary(self)]
        self._preseed_list(lists,name,value)

    def set_service(self,name,value):
        """Preseeds the status of a service"""
        lists = [get_services_dictionary(self),{"x11vnc_password":self.vnc_password}]
        self._preseed_list(lists,name,value)

    def set_driver(self,name,value):
        """Preseeds the status of a driver"""
        lists = [{'video_driver': self.video_driver,
                  'tvout': self.tvouttype,
                  'tvstandard': self.tvoutstandard,
                  'hdhomerun': self.hdhomerun}]
        self._preseed_list(lists,name,value)

    def set_password(self,name,value):
        """Preseeds a password"""
        lists = [{'mysql_admin_password':self.mysql_root_password,
                  'mysql_mythtv_user':self.mysql_user,
                  'mysql_mythtv_password':self.mysql_password,
                  'mysql_mythtv_dbname':self.mysql_database,
                  'mysql_host':self.mysql_server},
                 {'enable':self.usemythwebpassword,
                  'username':self.mythweb_username,
                  'password':self.mythweb_password}]
        self._preseed_list(lists,name,value)

    def set_lirc(self,question,answer):
        """Preseeds a lirc configuration item"""
        if question == "remote_modules":
            self.remote_modules.set_text(answer)
        elif question == "remote_device":
            self.remote_device.set_text(answer)
        elif question == "remote_driver":
            self.remote_driver.set_text(answer)
        elif question == "remote_lircd_conf":
            print "TODO"
        elif question == "remote":
            for i in range(0,self.remote_count):
                self.remote_list.set_active(i)
                found=False
                if self.remote_list.get_active_text() == answer:
                    found = True
                    break
                if not found:
                    self.remote_list.set_active(0)
        if question == "transmitter_modules":
            self.transmitter_modules.set_text(answer)
        elif question == "transmitter_device":
            self.transmitter_modules.set_text(answer)
        elif question == "transmitter_driver":
            self.transmitter_driver.set_text(answer)
        elif question == "transmitter_lircd_conf":
            print "TODO"
        elif question == "transmitter":
            for i in range(0,self.transmitter_count):
                self.transmitter_list.set_active(i)
                found=False
                if self.transmitter_list.get_active_text() == answer:
                    found = True
                    break
                if not found:
                    self.transmitter_list.set_active(0)

    def _preseed_list(self,lists,names,value):
        """Helper function for preseeding dictionary based lists"""
        new_value = create_bool(value)
        for list in lists:
            for item in list:
                for name in string.split(names):
                    if item == name:
                        #be careful what type of item we are deealing with
                        if type(list[item]) == gtk.CheckButton:
                            list[item].set_active(new_value)
                        elif type(list[item]) == gtk.Entry:
                            list[item].set_text(new_value)
                        elif type(list[item]) == gtk.ComboBox:
                            for iteration in range(len(list[item]),0):
                                list[item].set_active(iteration)
                                if list[item].get_active_text() == new_value:
                                    break
                        else:
                            list[item].set_active_text(new_value)

##################
#Status Reading  #
##################
#Functions for reading the status of Frontend elements

    def get_advanced(self):
        """Returns if this is an advanced install"""
        return self.custominstall.get_active()

    def get_installtype(self):
        """Returns the current custom installation type"""
        if self.master_be_fe.get_active():
            return "Master Backend/Frontend"
        elif self.slave_be_fe.get_active():
            return "Slave Backend/Frontend"
        elif self.master_be.get_active():
            return "Master Backend"
        elif self.slave_be.get_active():
            return "Slave Backend"
        elif self.fe.get_active():
            return "Frontend"
        elif self.stb.get_active():
            return "Set Top Box"

    def _build_static_list(self,lists):
        """Creates a flat list"""
        total_list= {}
        for list in lists:
            for item in list:
                if type(list[item]) == str:
                    total_list[item]=list[item]
                elif type(list[item]) == gtk.CheckButton:
                    total_list[item]=list[item].get_active()
                elif type(list[item]) == gtk.Entry:
                    total_list[item]=list[item].get_text()
                else:
                    total_list[item]=list[item].get_active_text()
        return total_list

    def get_plugins(self):
        """Returns the status of all the plugins"""
        return self._build_static_list([get_frontend_plugin_dictionary(self),get_backend_plugin_dictionary(self)])

    def get_themes(self,type):
        """Returns the status of the theme dictionaries"""
        if type == 'officialthemes':
            return self._build_static_list([get_official_theme_dictionary(self)])
        else:
            return self._build_static_list([get_community_theme_dictionary(self)])

    def get_services(self):
        """Returns the status of all installable services"""
        return self._build_static_list([get_services_dictionary(self),{'x11vnc_password':self.vnc_password}])

    def get_drivers(self):
        video_drivers=get_graphics_dictionary()
        active_video_driver=self.video_driver.get_active_text()
        for item in video_drivers:
            if (active_video_driver == item):
                active_video_driver=video_drivers[item]
                break
        return self._build_static_list([{'video_driver': active_video_driver,
                                         'tvout': self.tvouttype,
                                         'tvstandard': self.tvoutstandard,
                                         'hdhomerun': self.hdhomerun}])

    def get_mythtv_passwords(self):
        return self._build_static_list([{'mysql_admin_password':self.mysql_root_password,
                                         'mysql_mythtv_user':self.mysql_user,
                                         'mysql_mythtv_password':self.mysql_password,
                                         'mysql_mythtv_dbname':self.mysql_database,
                                         'mysql_host':self.mysql_server}])

    def get_mythweb_passwords(self):
        return self._build_static_list([{'enable':self.usemythwebpassword,
                                         'username':self.mythweb_username,
                                         'password':self.mythweb_password}])

    def get_lirc(self,type):
        item = {"modules":"","device":"","driver":"","lircd_conf":""}
        if type == "remote":
            item["remote"]=self.remote_list.get_active_text()
            if item["remote"] == "Custom":
                item["modules"]=self.remote_modules.get_text()
                item["device"]=self.remote_device.get_text()
                item["driver"]=self.remote_driver.get_text()
                item["lircd_conf"]=self.browse_remote_lircd_conf.get_filename()
        elif type == "transmitter":
            item["transmitter"]=self.transmitter_list.get_active_text()
            if item["transmitter"] == "Custom":
                item["modules"]=self.transmitter_modules.get_text()
                item["device"]=self.transmitter_device.get_text()
                item["driver"]=self.transmitter_driver.get_text()
                item["lircd_conf"]=self.browse_transmitter_lircd_conf.get_filename()
        return item

##################
#Toggle functions#
##################
#Called when a widget changes and other GUI elements need to react

    def toggle_meta(self,widget):
        """Called whenever a request to enable / disable meta pages"""
        if widget is not None:
            list = []
            name = widget.get_name()
            if (name == 'officialthemes'):
                list = get_official_theme_dictionary(self)
            elif (name == 'communitythemes'):
                list = get_community_theme_dictionary(self)
            elif (name == 'frontendplugins'):
                list = get_frontend_plugin_dictionary(self)
            elif (name == 'backendplugins'):
                list = get_backend_plugin_dictionary(self)

            toggle = widget.get_active()
            for item in list:
                if list[item].flags() & gtk.SENSITIVE:
                    list[item].set_active(toggle)

    def toggle_enablevnc(self,widget):
        """Called when the checkbox to turn on VNC is toggled"""
        if (self.enablevnc.get_active()):
            self.vnc_pass_hbox.set_sensitive(True)
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.vnc_error_image.show()
        else:
            self.vnc_pass_hbox.set_sensitive(False)
            self.vnc_password.set_text("")
            self.allow_go_forward(True)
            self.allow_go_backward(True)
            self.vnc_error_image.hide()

    def toggle_tv_out (self,widget):
        """Called when the tv-out type is toggled"""
        if (self.tvouttype.get_active() == 0):
            self.tvoutstandard.set_active(0)
        elif ((self.tvouttype.get_active() == 1 or self.tvouttype.get_active() == 2) and (self.tvoutstandard.get_active() == 0 or self.tvoutstandard.get_active() >= 11 )):
            self.tvoutstandard.set_active(10)
        elif self.tvouttype.get_active() == 3:
            self.tvoutstandard.set_active(11)

    def toggle_tv_standard(self,widget):
        """Called when the tv standard is toggled"""
        if (self.tvoutstandard.get_active() >= 11):
            self.tvouttype.set_active(3)
        elif (self.tvoutstandard.get_active() < 11 and self.tvoutstandard.get_active() > 0 and self.tvouttype.get_active() == 0):
            self.tvouttype.set_active(1)
        elif (self.tvoutstandard.get_active() < 11 and self.tvouttype.get_active() ==3):
            self.tvouttype.set_active(1)
        elif (self.tvoutstandard.get_active() == 0):
            self.tvouttype.set_active(0)

    def video_changed (self,widget):
        """Called whenever the modify video driver option is toggled or its kids"""
        drivers=get_graphics_dictionary()
        if (widget is not None and widget.get_name() == 'modifyvideodriver'):
            if (widget.get_active()):
                self.videodrivers_hbox.set_sensitive(True)
            else:
                self.tvout_vbox.set_sensitive(False)
                self.videodrivers_hbox.set_sensitive(False)
                self.video_driver.set_active(len(drivers))
                self.tvoutstandard.set_active(0)
                self.tvouttype.set_active(0)
        elif (widget is not None and widget.get_name() == 'video_driver'):
            type = widget.get_active()
            if (type < len(drivers)):
                self.tvout_vbox.set_sensitive(True)
            else:
                self.tvout_vbox.set_sensitive(False)
                self.tvoutstandard.set_active(0)
                self.tvouttype.set_active(0)

    def toggle_customtype (self,widget):
        """Called whenever a custom type is toggled"""

        def set_fe_drivers(self,enable):
            """Toggle Visible Frontend Applicable Drivers"""
            if enable:
                self.frontend_driver_list.show()
            else:
                self.frontend_driver_list.hide()

        def set_be_drivers(self,enable):
            """Toggles Visible Backend Applicable Drivers"""
            if enable:
                self.backend_driver_list.show()
            else:
                self.backend_driver_list.hide()

        def set_all_services(self,enable):
            """Toggles visibility on all possible services"""
            if enable:
                self.ssh_option_hbox.show()
                self.samba_option_hbox.show()
                self.nfs_option_hbox.show()
                self.mysql_option_hbox.show()
            else:
                self.ssh_option_hbox.hide()
                self.samba_option_hbox.hide()
                self.nfs_option_hbox.hide()
                self.mysql_option_hbox.hide()

        def set_all_passwords(self,enable):
            """Toggles visibility on all password selection boxes"""
            if enable:
                self.master_backend_expander.show()
                self.mythweb_expander.show()
                self.mysql_server_expander.show()
            else:
                self.master_backend_expander.hide()
                self.mythweb_expander.hide()
                self.mysql_server_expander.hide()

        def set_all_themes(self,enable):
            """Enables all themes for defaults"""
            self.communitythemes.set_active(enable)
            self.officialthemes.set_active(enable)

        def set_all_fe_plugins(self,enable):
            """ Enables all frontend plugins for defaults"""
            list = get_frontend_plugin_dictionary(self)
            for item in list:
                list[item].set_active(enable)

        def set_all_be_plugins(self,enable):
            """ Enables all backend plugins for defaults"""
            list = get_backend_plugin_dictionary(self)
            for item in list:
                list[item].set_active(enable)

        if self.master_be_fe.get_active():
            set_all_themes(self,True)
            set_all_fe_plugins(self,True)
            set_all_be_plugins(self,True)
            set_all_passwords(self,True)
            set_all_services(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.show()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Frontend / Backend Plugins")
            self.master_backend_expander.hide()
            set_fe_drivers(self,True)
            set_be_drivers(self,True)
        elif self.slave_be_fe.get_active():
            set_all_themes(self,True)
            set_all_fe_plugins(self,True)
            set_all_be_plugins(self,True)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.show()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Frontend / Backend Plugins")
            self.mysql_server_expander.hide()
            self.mysql_option_hbox.hide()
            set_fe_drivers(self,True)
            set_be_drivers(self,True)
        elif self.master_be.get_active():
            set_all_themes(self,False)
            set_all_fe_plugins(self,False)
            set_all_be_plugins(self,True)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.hide()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Backend Plugins")
            self.master_backend_expander.hide()
            set_fe_drivers(self,False)
            set_be_drivers(self,True)
        elif self.slave_be.get_active():
            set_all_themes(self,False)
            set_all_fe_plugins(self,False)
            set_all_be_plugins(self,True)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.hide()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Backend Plugins")
            self.mysql_server_expander.hide()
            self.mysql_option_hbox.hide()
            set_fe_drivers(self,False)
            set_be_drivers(self,True)
        else:
            set_all_themes(self,True)
            set_all_fe_plugins(self,True)
            set_all_be_plugins(self,False)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(False)
            self.enablenfs.set_active(False)
            self.enablemysql.set_active(False)
            self.frontend_plugin_list.show()
            self.backend_plugin_list.hide()
            self.febe_heading_label.set_label("Choose Frontend Plugins")
            self.mythweb_expander.hide()
            self.mysql_server_expander.hide()
            self.mysql_option_hbox.hide()
            self.nfs_option_hbox.hide()
            self.samba_option_hbox.hide()
            set_fe_drivers(self,True)
            set_be_drivers(self,False)

    def toggle_ir(self,widget):
        """Called whenever a request to enable/disable remote is called"""
        if widget is not None:
            #turn on/off IR remote
            if widget.get_name() == 'remotecontrol':
                self.remote_hbox.set_sensitive(widget.get_active())
                self.generate_lircrc_checkbox.set_sensitive(widget.get_active())
                if widget.get_active() and self.remote_list.get_active() == 0:
                        self.remote_list.set_active(1)
                else:
                    self.remote_list.set_active(0)
            #turn on/off IR transmitter
            elif widget.get_name() == "transmittercontrol":
                self.transmitter_hbox.set_sensitive(widget.get_active())
                if widget.get_active():
                    if self.transmitter_list.get_active() == 0:
                        self.transmitter_list.set_active(1)
                else:
                    self.transmitter_list.set_active(0)
            #if our selected remote itself changed
            elif widget.get_name() == 'remote_list':
                self.generate_lircrc_checkbox.set_active(True)
                if self.remote_list.get_active() == 0:
                    custom = False
                    self.remotecontrol.set_active(False)
                    self.generate_lircrc_checkbox.set_active(False)
                elif self.remote_list.get_active_text() == "Custom":
                    custom = True
                else:
                    custom = False
                    self.remote_driver.set_text("")
                    self.remote_modules.set_text("")
                    self.remote_device.set_text("")
                self.remote_driver_hbox.set_sensitive(custom)
                self.remote_modules_hbox.set_sensitive(custom)
                self.remote_device_hbox.set_sensitive(custom)
                self.remote_configuration_hbox.set_sensitive(custom)
                self.browse_remote_lircd_conf.set_filename("/usr/share/lirc/remotes")
            #if our selected transmitter itself changed
            elif widget.get_name() == 'transmitter_list':
                if self.transmitter_list.get_active() == 0:
                    custom = False
                    self.transmittercontrol.set_active(False)
                elif self.transmitter_list.get_active_text() == "Custom":
                    custom = True
                else:
                    custom = False
                    self.transmitter_driver.set_text("")
                    self.transmitter_modules.set_text("")
                    self.transmitter_device.set_text("")
                self.transmitter_driver_hbox.set_sensitive(custom)
                self.transmitter_modules_hbox.set_sensitive(custom)
                self.transmitter_device_hbox.set_sensitive(custom)
                self.transmitter_configuration_hbox.set_sensitive(custom)
                self.browse_transmitter_lircd_conf.set_filename("/usr/share/lirc/transmitters")

    def mythweb_toggled(self,widget):
        """Called when the checkbox to install Mythweb is toggled"""
        if (self.mythweb_checkbox.get_active()):
            self.mythweb_expander.show()
        else:
            self.mythweb_expander.hide()

    def usemythwebpassword_toggled(self,widget):
        """Called when the checkbox to set a mythweb password is pressed"""
        if (self.usemythwebpassword.get_active()):
            self.mythweb_table.show()
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.mythweb_user_error_image.show()
            self.mythweb_pass_error_image.show()
        else:
            self.mythweb_table.hide()
            self.mythweb_password.set_text("")
            self.mythweb_username.set_text("")
            self.mythweb_user_error_image.hide()
            self.mythweb_pass_error_image.hide()
            if (not self.usemysqlrootpassword.get_active() or not self.mysql_root_error_image.flags() & gtk.VISIBLE):
                self.allow_go_forward(True)
                self.allow_go_backward(True)

    def usemysqlrootpassword_toggled(self,widget):
        """Called when the checkbox to set a MySQL root password is pressed"""
        if (self.usemysqlrootpassword.get_active()):
            self.mysql_server_hbox.show()
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.mysql_root_error_image.show()
        else:
            self.mysql_server_hbox.hide()
            self.mysql_root_password.set_text("")
            self.mysql_root_error_image.hide()
            if (not self.usemythwebpassword.get_active() or ((not self.mythweb_pass_error_image.flags() & gtk.VISIBLE) and (not self.mythweb_user_error_image.flags() & gtk.VISIBLE))):
                self.allow_go_forward(True)
                self.allow_go_backward(True)

    def toggle_installtype (self,widget):
        """Called whenever standard or full are toggled"""
        if self.standardinstall.get_active() :
            #Make sure that we have everything turned on in case they came back to this page
            #and changed their mind
            #Note: This will recursively handle changing the values on the pages
            self.master_be_fe.set_active(True)
            self.enablessh.set_active(True)
            self.enablevnc.set_active(False)
            self.enablenfs.set_active(False)
            self.enablesamba.set_active(True)
            self.enablemysql.set_active(False)

        else:
            self.master_backend_expander.hide()
            self.mythweb_expander.show()
            self.mysql_server_expander.show()
