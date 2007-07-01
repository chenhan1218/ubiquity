# -*- coding: utf-8 -*-
#
# «mythbuntu-ui» - Mythbuntu user interface
#
# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006, 2007 Canonical Ltd.
# Copyright (C) 2007, Mario Limonciello, for Mythbuntu
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
##################################################################################

import os
import subprocess
import gtk.glade
import MySQLdb
import syslog
import signal
try:
    from debconf import DebconfCommunicator
except ImportError:
    from ubiquity.debconfcommunicator import DebconfCommunicator

from ubiquity.misc import *

from ubiquity import misc
from ubiquity.components import console_setup, language, timezone, usersetup, \
                                partman, partman_commit, \
                                mythbuntu, mythbuntu_install, mythbuntu_summary

import ubiquity.frontend.gtk_ui
import ubiquity.components.mythbuntu_install
import ubiquity.components.mythbuntu_summary
ubiquity.frontend.gtkui.install = ubiquity.components.mythbuntu_install
ubiquity.frontend.gtkui.summary = ubiquity.components.mythbuntu_summary


BREADCRUMB_STEPS = {
    "stepLanguage": 1,
    "stepLocation": 2,
    "stepKeyboardConf": 3,
    "mythbuntu_stepInstallType": 4,
    "mythbuntu_stepCustomInstallType": 5,
    "mythbuntu_stepPlugins": 6,
    "mythbuntu_stepThemes": 7,
    "mythbuntu_stepServices": 8,
    "mythbuntu_stepPasswords": 9,
    "mythbuntu_stepDrivers": 10,
    "stepPartAuto": 11,
    "stepPartAdvanced": 11,
    "stepUserInfo": 12,
    "stepReady": 13, 
    "mythbuntu_stepBackendSetup": 14
}
BREADCRUMB_MAX_STEP = 14

# Define what pages of the UI we want to load.  Note that most of these pages
# are required for the install to complete successfully.
SUBPAGES = [
    "stepWelcome",
    "stepLanguage",
    "stepLocation",
    "stepKeyboardConf",
    "mythbuntu_stepInstallType",
    "mythbuntu_stepCustomInstallType",
    "mythbuntu_stepPlugins",
    "mythbuntu_stepThemes",
    "mythbuntu_stepServices",
    "mythbuntu_stepPasswords",
    "mythbuntu_stepDrivers",
    "stepPartAuto",
    "stepPartAdvanced",
    "stepUserInfo",
    "stepReady",
    "mythbuntu_stepBackendSetup"
]

ubiquity.frontend.gtkui.BREADCRUMB_STEPS = BREADCRUMB_STEPS;
ubiquity.frontend.gtkui.BREADCRUMB_MAX_STEP = BREADCRUMB_MAX_STEP;
ubiquity.frontend.gtkui.SUBPAGES = SUBPAGES;

class Wizard(ubiquity.frontend.gtkui.Wizard):

#Overriden Methods    
    def __init__(self, distro):
        del os.environ['UBIQUITY_MIGRATION_ASSISTANT'];
        ubiquity.frontend.gtkui.Wizard.__init__(self,distro)
        
    def run(self):
        """run the interface."""

        if os.getuid() != 0:
            title = ('This installer must be run with administrative '
                     'privileges, and cannot continue without them.')
            dialog = gtk.MessageDialog(self.live_installer, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                                       title)
            dialog.run()
            sys.exit(1)

        self.disable_volume_manager()

        # show interface
        got_intro = self.show_intro()
        self.allow_change_step(True)

        # Declare SignalHandler
        self.glade.signal_autoconnect(self)

        # Some signals need to be connected by hand so that we have the
        # handler ids.
        self.username_changed_id = self.username.connect(
            'changed', self.on_username_changed)
        self.hostname_changed_id = self.hostname.connect(
            'changed', self.on_hostname_changed)

        # Start the interface
        if got_intro:
            global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
            for step in BREADCRUMB_STEPS:
                BREADCRUMB_STEPS[step] += 1
            BREADCRUMB_STEPS["stepWelcome"] = 1
            BREADCRUMB_MAX_STEP += 1
            ubiquity.frontend.gtkui.BREADCRUMB_STEPS = BREADCRUMB_STEPS;
            ubiquity.frontend.gtkui.BREADCRUMB_MAX_STEP = BREADCRUMB_MAX_STEP;
            first_step = self.stepWelcome
        else:
            first_step = self.stepLanguage
        self.set_current_page(self.steps.page_num(first_step))
        if got_intro:
            # intro_label was the only focusable widget, but got can-focus
            # removed, so we end up with no input focus and thus pressing
            # Enter doesn't activate the default widget. Work around this.
            self.next.grab_focus()
        
        while self.current_page is not None:
            if not self.installing:
                # Make sure any started progress bars are stopped.
                while self.progress_position.depth() != 0:
                    self.debconf_progress_stop()

            self.backup = False
            current_name = self.step_name(self.current_page)
            old_dbfilter = self.dbfilter
            if current_name == "stepLanguage":
                self.dbfilter = language.Language(self)
                gtk.link_button_set_uri_hook(self.link_button_browser)
            elif current_name == "stepMigrationAssistant":
                self.dbfilter = migrationassistant.MigrationAssistant(self)
            elif current_name == "stepLocation":
                self.dbfilter = timezone.Timezone(self)
            elif current_name == "stepKeyboardConf":
                self.dbfilter = console_setup.ConsoleSetup(self)
            elif current_name == "mythbuntu_stepDrivers":
                self.dbfilter = mythbuntu.MythbuntuSetup(self)
            elif current_name == "stepUserInfo":
                self.dbfilter = usersetup.UserSetup(self)
            elif current_name == "stepPartAuto":
                self.dbfilter = partman.Partman(self)
            elif current_name == "stepPartAdvanced":
                if isinstance(self.dbfilter, partman.Partman):
                    pre_log('info', 'reusing running partman')
                else:
                    self.dbfilter = partman.Partman(self)
            elif current_name == "stepReady":
                self.dbfilter = mythbuntu_summary.Summary(self)
            else:
                self.dbfilter = None

            if self.dbfilter is not None and self.dbfilter != old_dbfilter:
                self.allow_change_step(False)
                self.dbfilter.start(auto_process=True)
            else:
                # Non-debconf steps don't have a mechanism for turning this
                # back on, so we do it here. process_step should block until
                # the next step has started up; this will block the UI, but
                # that's probably unavoidable for now. (This is currently
                # believed to be unused; we only used this for gparted,
                # which had its own UI loop.)
                self.allow_change_step(True)
            gtk.main()

            if self.backup or self.dbfilter_handle_status():
                if self.installing:
                    self.progress_loop()
                elif self.current_page is not None and not self.backup:
                    self.process_step()

            while gtk.events_pending():
                gtk.main_iteration()

        return self.returncode

    def process_step(self):
        """Process and validate the results of this step."""

        # setting actual step
        step_num = self.steps.get_current_page()
        step = self.step_name(step_num)
        syslog.syslog('Step_before = %s' % step)

        if step.startswith("stepPart"):
            self.previous_partitioning_page = step_num

        # Welcome
        if step == "stepWelcome":
            self.steps.next_page()
        # Language
        elif step == "stepLanguage":
            self.translate_widgets()
            self.steps.next_page()
            self.back.show()
            self.allow_go_forward(self.get_timezone() is not None)
        # Location
        elif step == "stepLocation":
            self.steps.next_page()
        # Keyboard
        elif step == "stepKeyboardConf":
            self.steps.next_page()
        #Install Type
        elif step == "mythbuntu_stepInstallType":
            self.steps.next_page()
        #Adv Install Type
        elif step == "mythbuntu_stepCustomInstallType":
            self.steps.next_page()
        #Frontend/Backend Plugins
        elif step == "mythbuntu_stepPlugins":
            self.steps.next_page()
        #Themes
        elif step == "mythbuntu_stepThemes":
            self.steps.next_page()
        #Backend Info
        elif step == "mythbuntu_stepPasswords":
            self.steps.next_page()
        elif step == "mythbuntu_stepServices":
            self.steps.next_page()
        #Proprietary Video Drivers
        elif step == "mythbuntu_stepDrivers":
            self.steps.next_page()
        # Automatic partitioning
        elif step == "stepPartAuto":
            self.process_autopartitioning()
        # Advanced partitioning
        elif step == "stepPartAdvanced":
            if not 'UBIQUITY_MIGRATION_ASSISTANT' in os.environ:
                self.info_loop(None)
                self.set_current_page(self.steps.page_num(self.stepUserInfo))
            else:
                self.set_current_page(self.steps.page_num(self.stepMigrationAssistant))
        # Migration Assistant
        elif step == "stepMigrationAssistant":
            self.steps.next_page()
            self.ma_configure_usersetup()
            self.info_loop(None)
        # Identification
        elif step == "stepUserInfo":
            self.process_identification()
            self.next.set_label("Install")
        # Ready to install
        elif step == "stepReady":
            self.live_installer.hide()
            self.current_page = None
            self.installing = True
            self.progress_loop()
            if self.get_installtype() == "Frontend":
                self.finished_dialog.run()
                return
            else:
                self.live_installer.show()
                self.installing = False
                self.steps.next_page()
                self.back.hide()
                self.cancel.hide()
                self.next.set_label("Finish")
        #Post Install Steps
        elif step == "mythbuntu_stepBackendSetup":
            self.live_installer.hide()
            self.current_page = None
            self.finished_dialog.run()
            return
        step = self.step_name(self.steps.get_current_page())
        syslog.syslog('Step_after = %s' % step)

    def on_back_clicked(self, widget):
        """Callback to set previous screen."""

        if not self.allowed_change_step:
            return

        self.allow_change_step(False)

        self.backup = True

        # Enabling next button
        self.allow_go_forward(True)
        # Setting actual step
        step = self.step_name(self.steps.get_current_page())

        changed_page = False

        if step == "stepLocation":
            self.back.hide()
        elif step == "stepPartAuto":
            self.set_current_page(self.steps.page_num(self.mythbuntu_stepDrivers))
            changed_page = True
        elif step == "stepPartAdvanced":
            self.set_current_page(self.steps.page_num(self.stepPartAuto))
            changed_page = True
        elif step == "stepMigrationAssistant":
            self.set_current_page(self.previous_partitioning_page)
            changed_page = True
        elif step == "stepUserInfo":
            if 'UBIQUITY_MIGRATION_ASSISTANT' not in os.environ:
                self.set_current_page(self.previous_partitioning_page)
                changed_page = True
        elif step == "stepReady":
            self.next.set_label("gtk-go-forward")
            self.translate_widget(self.next, self.locale)
            self.steps.prev_page()
            changed_page = True

        if not changed_page:
            self.steps.prev_page()

        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        elif gtk.main_level() > 0:
            gtk.main_quit()

    def progress_loop(self):
        """prepare, copy and config the system in the core install process."""

        syslog.syslog('progress_loop()')

        self.current_page = None

        self.debconf_progress_start(
            0, 100, self.get_string('ubiquity/install/title'))
        self.debconf_progress_region(0, 15)

        dbfilter = partman_commit.PartmanCommit(self)
        if dbfilter.run_command(auto_process=True) != 0:
            while self.progress_position.depth() != 0:
                self.debconf_progress_stop()
            self.debconf_progress_window.hide()
            self.return_to_partitioning()
            return

        # No return to partitioning from now on
        self.installing_no_return = True

        self.debconf_progress_region(15, 100)

        dbfilter = mythbuntu_install.Install(self)
        ret = dbfilter.run_command(auto_process=True)
        if ret != 0:
            self.installing = False
            if ret == 3:
                # error already handled by Install
                sys.exit(ret)
            elif (os.WIFSIGNALED(ret) and
                  os.WTERMSIG(ret) in (signal.SIGINT, signal.SIGKILL,
                                       signal.SIGTERM)):
                sys.exit(ret)
            elif os.path.exists('/var/lib/ubiquity/install.trace'):
                tbfile = open('/var/lib/ubiquity/install.trace')
                realtb = tbfile.read()
                tbfile.close()
                raise RuntimeError, ("Install failed with exit code %s\n%s" %
                                     (ret, realtb))
            else:
                raise RuntimeError, ("Install failed with exit code %s; see "
                                     "/var/log/syslog" % ret)

        while self.progress_position.depth() != 0:
            self.debconf_progress_stop()

        # just to make sure
        self.debconf_progress_window.hide()

        self.installing = False


#Added Methods
    def allow_go_backward(self, allowed):
        self.back.set_sensitive(allowed and self.allowed_change_step)
        self.allowed_go_backward = allowed

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
        elif (widget is not None and widget.get_name() == 'mythweb_password'):
            password = widget.get_text().split(' ')[0]
            if len(password) >= 1:
                self.mythweb_error_image.hide()
            else:
                self.mythweb_error_image.show()
                
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
            mythweb_flag = self.mythweb_error_image.flags() & gtk.VISIBLE
            result = not (mythweb_flag | mysql_root_flag)
            self.allow_go_forward(result)
            self.allow_go_backward(result)            
        
    
    def do_mythtv_setup(self,widget):
        """Spawn MythTV-Setup binary."""
        execute("/usr/lib/ubiquity/mythbuntu/mythbuntu-setup")
        
    def do_connection_test(self,widget):
        """Tests to make sure that the backend is accessible"""
        host = self.mysql_server.get_text()
        database = self.mysql_database.get_text()
        user = self.mysql_user.get_text()
        password = self.mysql_password.get_text()
        try:
            db = MySQLdb.connect(host=host, user=user, passwd=password,
db=database)
            cursor = db.cursor()
            cursor.execute("SELECT NULL")
            result = cursor.fetchone()
            cursor.close()
            db.close()
            result = "Successful"
        except:
            result = "Failure"
        self.connection_results_label.show()
        self.connection_results.set_text(result)
        

    def toggle_installtype (self,widget):
        """Called whenever standard or full are toggled"""
        if self.standardinstall.get_active() :
            #Make sure that we have everything turned on in case they came back to this page
            #and changed their mind
            #Note: This will recursively handle changing the values on the pages
            self.master_be_fe.set_active(True)
            #For a standard install, remove any customization pages
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepCustomInstallType)).hide()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepPlugins)).hide()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepThemes)).hide()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepPasswords)).hide()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepServices)).hide()
            self.enablessh.set_active(True)
            self.enablevnc.set_active(False)
            self.enablenfs.set_active(False)
            self.enablesamba.set_active(True)
            self.enablemysql.set_active(False)
            
        else:
            # For a custom install, reinsert our missing pages
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepCustomInstallType)).show()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepPlugins)).show()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepThemes)).show()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepPasswords)).show()
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepServices)).show()
            self.master_backend_expander.hide()
            self.mythweb_expander.show()
            self.mysql_server_expander.show()
    
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
                self.tuner0.set_active(0)
                self.tuner1.set_active(0)
                self.tuner2.set_active(0)
                self.tuner3.set_active(0)
                self.tuner4.set_active(0)
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
                self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepPasswords)).show()
            else:
                self.master_backend_expander.hide()
                self.mythweb_expander.hide()
                self.mysql_server_expander.hide()
                self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepPasswords)).hide()
        
        def set_all_themes(self,enable):
            """Enables all themes for defaults"""
            self.communitythemes.set_active(enable)
            self.officialthemes.set_active(enable)

        def set_all_fe_plugins(self,enable):
            """ Enables all frontend plugins for defaults"""
            self.mytharchive.set_active(enable)
            self.mythbrowser.set_active(enable)
            self.mythcontrols.set_active(enable)
            self.mythdvd.set_active(enable)
            self.mythflix.set_active(enable)
            self.mythgallery.set_active(enable)
            self.mythgame.set_active(enable)
            self.mythmusic.set_active(enable)
            self.mythnews.set_active(enable)
            self.mythphone.set_active(enable)
            self.mythvideo.set_active(enable)
            self.mythweather.set_active(enable)
        
        def set_all_be_plugins(self,enable):
            """ Enables all backend plugins for defaults"""
            self.mythweb.set_active(enable)
        
        if self.master_be_fe.get_active() :
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
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepThemes)).show()
            set_fe_drivers(self,True)
            set_be_drivers(self,True)
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepBackendSetup)).show()
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
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepThemes)).show()
            set_fe_drivers(self,True)
            set_be_drivers(self,True)
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepBackendSetup)).show()
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
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepThemes)).hide()
            set_fe_drivers(self,False)
            set_be_drivers(self,True)
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepBackendSetup)).show()
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
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepThemes)).hide()
            set_fe_drivers(self,False)
            set_be_drivers(self,True)
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepBackendSetup)).show()
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
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepThemes)).show()
            set_fe_drivers(self,True)
            set_be_drivers(self,False)
            self.steps.get_nth_page(self.steps.page_num(self.mythbuntu_stepBackendSetup)).hide()
    
    def mythweb_toggled(self,widget):
        """Called when the checkbox to install Mythweb is toggled"""
        if (self.mythweb.get_active()):
            self.mythweb_expander.show()
        else:
            self.mythweb_expander.hide()
    
    def enablevnc_toggled(self,widget):
        """Called when the checkbox to turn on VNC is toggled"""
        if (self.enablevnc.get_active()):
            self.vnc_pass_hbox.show()
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.vnc_error_image.show()            
        else:
            self.vnc_pass_hbox.hide()
            self.vnc_password.set_text("")
            self.allow_go_forward(True)
            self.allow_go_backward(True)
            self.vnc_error_image.hide()
    
    def uselivemysqlinfo_toggled(self,widget):
        """Called when the checkbox to copy live mysql information is pressed"""
        if (self.uselivemysqlinfo.get_active()):
            self.master_backend_table.hide()
        else:
            self.master_backend_table.show()        
    
    def usemythwebpassword_toggled(self,widget):
        """Called when the checkbox to set a mythweb password is pressed"""
        if (self.usemythwebpassword.get_active()):
            self.mythweb_hbox.show()
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.mythweb_error_image.show()            
        else:
            self.mythweb_hbox.hide()
            self.mythweb_password.set_text("")
            self.mythweb_error_image.hide()
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
            if (not self.usemythwebpassword.get_active() or not self.mythweb_error_image.flags() & gtk.VISIBLE):
                self.allow_go_forward(True)
                self.allow_go_backward(True)
                
                      
    
    def toggle_number_tuners (self,widget):
        """Called whenever a number of tuners is changed"""
        num = self.number_tuners.get_value()
        if num > 0:
            if num > 1:
                if num > 2:
                    if num > 3:
                        if num > 4:
                            self.tuner0.show()
                            self.tuner1.show()
                            self.tuner2.show()
                            self.tuner3.show()
                            self.tuner4.show()                    
                        else:
                            self.tuner0.show()
                            self.tuner1.show()
                            self.tuner2.show()
                            self.tuner3.show()
                            self.tuner4.hide()
                            self.tuner4.set_active(0)                    
                    else:
                        self.tuner0.show()
                        self.tuner1.show()
                        self.tuner2.show()
                        self.tuner3.hide()
                        self.tuner3.set_active(0)
                        self.tuner4.hide()
                        self.tuner4.set_active(0)                    
                else:
                    self.tuner0.show()
                    self.tuner1.show()
                    self.tuner2.hide()
                    self.tuner2.set_active(0)
                    self.tuner3.hide()
                    self.tuner3.set_active(0)
                    self.tuner4.hide()
                    self.tuner4.set_active(0)                                    
            else:
                self.tuner0.show()
                self.tuner1.hide()
                self.tuner1.set_active(0)
                self.tuner2.hide()
                self.tuner2.set_active(0)
                self.tuner3.hide()
                self.tuner3.set_active(0)
                self.tuner4.hide()
                self.tuner4.set_active(0)                    
        else:
            self.tuner0.hide()
            self.tuner0.set_active(0)
            self.tuner1.hide()
            self.tuner1.set_active(0)
            self.tuner2.hide()
            self.tuner2.set_active(0)
            self.tuner3.hide()
            self.tuner3.set_active(0)
            self.tuner4.hide()
            self.tuner4.set_active(0)    
    
    def toggle_tuners (self,widget):
        """Checks to make sure no tuner widgets have same value"""
        def return_tuner_val(self,num):
            if num == 0:
                return self.tuner0.get_active()
            elif num == 1:
                return self.tuner1.get_active()
            elif num == 2:
                return self.tuner2.get_active()
            elif num == 3:
                return self.tuner3.get_active()
            elif num == 4:
                return self.tuner4.get_active()
            
        def set_tuner_val(self,num_tuner,val):
            if num_tuner == 0:
                return self.tuner0.set_active(val)
            elif num_tuner == 1:
                return self.tuner1.set_active(val)
            elif num_tuner == 2:
                return self.tuner2.set_active(val)
            elif num_tuner == 3:
                return self.tuner3.set_active(val)
            elif num_tuner == 4:
                return self.tuner4.set_active(val)
                
        number_tuners = self.number_tuners.get_value_as_int()
        enable_warning=False
        for i in range(number_tuners):
            for j in range(i+1,number_tuners):
                #Check for duplicates
                if (return_tuner_val(self,i) != 0 and return_tuner_val(self,i) !=19 and return_tuner_val(self,i) !=20 and return_tuner_val(self,i) == return_tuner_val(self,j)):
                    set_tuner_val(self,j,0)
            #Check for the unknown Analogue or Digital Option
            if (return_tuner_val(self,i) == 19 or return_tuner_val(self,i) == 20):
                enable_warning=True
        if enable_warning == True:
            self.tunernotice.show()
        else:
            self.tunernotice.hide()
                

    def toggle_proprietary (self,widget):
        """Called whenever the proprietary driver option is toggled"""
        if (self.proprietarydrivers.get_active()):
            self.tvouttype.show()
            self.tvout_label.show()
            self.tvoutstandard.show()
            self.tvwarning.show()
            self.tvouttype.set_active(0)
            self.tvoutstandard.set_active(0)
            self.auto_detect.show()
            self.auto_detect_driver.show()
            # run restricted-manager --check to poll the restricted devices
            # we don't care about the results of this
            subprocess.Popen(["/usr/bin/restricted-manager", "--check"], stdout=subprocess.PIPE).communicate()[0]          
            # now actually get the list of restricted modules
            drivers = subprocess.Popen(["/usr/bin/restricted-manager", "--list"], stdout=subprocess.PIPE).communicate()[0]                    
            for driver in drivers.split():
                if driver == "nvidia":
                    self.auto_detect_driver.set_text("nvidia")
                elif driver == "fglrx":
                    self.auto_detect_driver.set_text("fglrx")
            if self.auto_detect_driver.get_text() != "nvidia" and self.auto_detect_driver.get_text() != "fglrx":
                self.auto_detect_driver.set_text("None")
        else:
            self.tvouttype.hide()
            self.tvout_label.hide()
            self.tvoutstandard.hide()
            self.tvwarning.hide()
            self.auto_detect.hide()
            self.auto_detect_driver.hide()
            self.auto_detect_driver.set_text("None")
        
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
        
    def get_mytharchive(self):
        """Returns the status of the mytharchive plugin"""
        if self.mytharchive.get_active():
            return "yes"
        else:
            return "no"

    def get_mythbrowser(self):
        """Returns the status of the mythbrowser plugin"""
        if self.mythbrowser.get_active():
            return "yes"
        else:
            return "no"

    def get_mythcontrols(self):
        """Returns the status of the mythcontrols plugin"""
        if self.mythcontrols.get_active():
            return "yes"
        else:
            return "no"

    def get_mythdvd(self):
        """Returns the status of the mythdvd plugin"""
        if self.mythdvd.get_active():
            return "yes"
        else:
            return "no"

    def get_mythflix(self):
        """Returns the status of the mythflix plugin"""
        if self.mythflix.get_active():
            return "yes"
        else:
            return "no"

    def get_mythgallery(self):
        """Returns the status of the mythgallery plugin"""
        if self.mythgallery.get_active():
            return "yes"
        else:
            return "no"

    def get_mythgame(self):
        """Returns the status of the mythgame plugin"""
        if self.mythgame.get_active():
            return "yes"
        else:
            return "no"

    def get_mythmusic(self):
        """Returns the status of the mythmusic plugin"""
        if self.mythmusic.get_active():
            return "yes"
        else:
            return "no"

    def get_mythnews(self):
        """Returns the status of the mythnews plugin"""
        if self.mythnews.get_active():
            return "yes"
        else:
            return "no"

    def get_mythphone(self):
        """Returns the status of the mythphone plugin"""
        if self.mythphone.get_active():
            return "yes"
        else:
            return "no"

    def get_mythvideo(self):
        """Returns the status of the mythvideo plugin"""
        if self.mythvideo.get_active():
            return "yes"
        else:
            return "no"

    def get_mythweather(self):
        """Returns the status of the mythweather plugin"""
        if self.mythweather.get_active():
            return "yes"
        else:
            return "no"

    def get_mythweb(self):
        """Returns the status of the mythweb plugin"""
        if self.mythweb.get_active():
            return "yes"
        else:
            return "no"
            
    def get_officialthemes(self):
        """Returns the status of the official themes"""
        if self.officialthemes.get_active():
            return "yes"
        else:
            return "no"

    def get_communitythemes(self):
        """Returns the status of the community themes"""
        if self.communitythemes.get_active():
            return "yes"
        else:
            return "no"
    def get_proprietary(self):
        """Returns the status of the proprietary graphics drivers"""
        if (self.proprietarydrivers.get_active()):
            return self.auto_detect_driver.get_text()
        else:
            return "None"

    def get_tvout(self):
        """Returns the status of the TV Out type"""
        if (self.proprietarydrivers.get_active()):
            return self.tvouttype.get_active_text()
        else:
            return "TV Out Disabled"

    def get_tvstandard(self):
        """Returns the status of the TV Standard type"""
        if (self.proprietarydrivers.get_active()):
            return self.tvoutstandard.get_active_text()           
        else:
            return "TV Out Disabled"
            
    def get_uselivemysqlinfo(self):
        if (self.uselivemysqlinfo.get_active()):
            return "yes"
        else:
            return "no"

    def get_mysqluser(self):
        return self.mysql_user.get_text()
        
    def get_mysqlpass(self):
        return self.mysql_password.get_text()
        
    def get_mysqldatabase(self):
        return self.mysql_database.get_text()
        
    def get_mysqlserver(self):
        return self.mysql_server.get_text()

    def get_secure_mysql(self):
        if self.usemysqlrootpassword.get_active():
            return "yes"
        else:
            return "no"

    def get_mysql_root_password(self):
        return self.mysql_root_password.get_text()           
        
    def get_secure_mythweb(self):
        if self.usemythwebpassword.get_active():
            return "yes"
        else:
            return "no"

    def get_mythweb_password(self):
        return self.mythweb_password.get_text()   

    def get_vnc(self):
        if self.enablevnc.get_active():
            return "yes"
        else:
            return "no"

    def get_vnc_password(self):
        return self.vnc_password.get_text()           
            
    def get_ssh(self):
        if self.enablessh.get_active():
            return "yes"
        else:
            return "no"

    def get_samba(self):
        if self.enablesamba.get_active():
            return "yes"
        else:
            return "no"
            
    def get_nfs(self):
        if self.enablenfs.get_active():
            return "yes"
        else:
            return "no"                        

    def get_mysql_port(self):
        if self.enablemysql.get_active():
            return "yes"
        else:
            return "no"   
