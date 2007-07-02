# -*- coding: utf-8 -*-
#
# «gtk_ui» - GTK user interface
#
# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006, 2007 Canonical Ltd.
#
# Authors:
#
# - Javier Carranza <javier.carranza#interactors._coop>
# - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
# - Antonio Olmo Titos <aolmo#emergya._info>
# - Gumer Coronel Pérez <gcoronel#emergya._info>
# - Colin Watson <cjwatson@ubuntu.com>
# - Evan Dandrea <evand@ubuntu.com>
# - Mario Limonciello <superm1@ubuntu.com>
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
import datetime
import subprocess
import math
import traceback
import syslog
import atexit
import signal
import xml.sax.saxutils
import gettext

import pygtk
pygtk.require('2.0')
import pango
import gobject
import gtk.glade

try:
    from debconf import DebconfCommunicator
except ImportError:
    from ubiquity.debconfcommunicator import DebconfCommunicator

from ubiquity import filteredcommand, i18n, validation
from ubiquity.misc import *
from ubiquity.components import console_setup, language, timezone, usersetup, \
                                partman, partman_commit, \
                                summary, install, migrationassistant
import ubiquity.emap
import ubiquity.tz
import ubiquity.progressposition
from ubiquity.frontend.base import BaseFrontend

# Define global path
PATH = '/usr/share/ubiquity'

# Define glade path
GLADEDIR = os.path.join(PATH, 'glade')

# Define locale path
LOCALEDIR = "/usr/share/locale"

BREADCRUMB_STEPS = {
    "stepLanguage": 1,
    "stepLocation": 2,
    "stepKeyboardConf": 3,
    "stepPartAuto": 4,
    "stepPartAdvanced": 4,
    "stepMigrationAssistant": 5,
    "stepUserInfo": 6,
    "stepReady": 7
}
BREADCRUMB_MAX_STEP = 7

# Define what pages of the UI we want to load.  Note that most of these pages
# are required for the install to complete successfully.
SUBPAGES = [
    "stepWelcome",
    "stepLanguage",
    "stepLocation",
    "stepKeyboardConf",
    "stepPartAuto",
    "stepPartAdvanced",
    "stepMigrationAssistant",
    "stepUserInfo",
    "stepReady"
]

class Wizard(BaseFrontend):

    def __init__(self, distro):
        def add_subpage(self, steps, name):
            """Inserts a subpage into the notebook.  This assumes the file
            shares the same base name as the page you are looking for."""
            gladefile = GLADEDIR + '/' + name + '.glade'
            gladexml = gtk.glade.XML(gladefile, name)
            widget = gladexml.get_widget(name)
            steps.append_page(widget)
            add_widgets(self, gladexml)
            gladexml.signal_autoconnect(self)

        def add_widgets(self, glade):
            """Makes all widgets callable by the toplevel."""
            for widget in glade.get_widget_prefix(""):
                setattr(self, widget.get_name(), widget)
                # We generally want labels to be selectable so that people can
                # easily report problems in them
                # (https://launchpad.net/bugs/41618), but GTK+ likes to put
                # selectable labels in the focus chain, and I can't seem to turn
                # this off in glade and have it stick. Accordingly, make sure
                # labels are unfocusable here.
                if isinstance(widget, gtk.Label):
                    widget.set_property('can-focus', False)

        BaseFrontend.__init__(self, distro)

        self.previous_excepthook = sys.excepthook
        sys.excepthook = self.excepthook

        # declare attributes
        self.gconf_previous = {}
        self.thunar_previous = {}
        self.language_questions = ('live_installer', 'oem_config_title',
                                   'welcome_heading_label', 'welcome_text_label',
                                   'release_notes_label', 'release_notes_url',
                                   'step_label',
                                   'cancel', 'back', 'next',
                                   'warning_dialog', 'warning_dialog_label',
                                   'cancelbutton', 'exitbutton')
        self.current_page = None
        self.allowed_change_step = True
        self.allowed_go_forward = True
        self.progress_position = ubiquity.progressposition.ProgressPosition()
        self.progress_cancelled = False
        self.autopartition_extras = {}
        self.resize_min_size = None
        self.resize_max_size = None
        self.new_size_scale = None
        self.username_combo = None
        self.username_edited = False
        self.hostname_edited = False
        self.previous_partitioning_page = None
        self.installing = False
        self.installing_no_return = False
        self.returncode = 0

        self.laptop = execute("laptop-detect")

        # set default language
        dbfilter = language.Language(self, DebconfCommunicator('ubiquity',
                                                               cloexec=True))
        dbfilter.cleanup()
        dbfilter.db.shutdown()

        gobject.timeout_add(30000, self.poke_screensaver)

        # To get a "busy mouse":
        self.watch = gtk.gdk.Cursor(gtk.gdk.WATCH)

        # set custom language
        self.set_locales()

        # load the main interface
        self.glade = gtk.glade.XML('%s/ubiquity.glade' % GLADEDIR)
        add_widgets(self,self.glade)

        steps = self.glade.get_widget("steps")
        for page in SUBPAGES:
            add_subpage(self, steps, page)

        self.translate_widgets()

        self.customize_installer()


    def excepthook(self, exctype, excvalue, exctb):
        """Crash handler."""

        if (issubclass(exctype, KeyboardInterrupt) or
            issubclass(exctype, SystemExit)):
            return

        tbtext = ''.join(traceback.format_exception(exctype, excvalue, exctb))
        syslog.syslog(syslog.LOG_ERR,
                      "Exception in GTK frontend (invoking crash handler):")
        for line in tbtext.split('\n'):
            syslog.syslog(syslog.LOG_ERR, line)
        print >>sys.stderr, ("Exception in GTK frontend"
                             " (invoking crash handler):")
        print >>sys.stderr, tbtext

        self.post_mortem(exctype, excvalue, exctb)

        if os.path.exists('/usr/share/apport/apport-gtk'):
            self.previous_excepthook(exctype, excvalue, exctb)
        else:
            self.crash_detail_label.set_text(tbtext)
            self.crash_dialog.run()
            self.crash_dialog.hide()

            sys.exit(1)


    def thunar_set_volmanrc (self, fields):
        previous = {}
        if 'SUDO_USER' in os.environ:
            thunar_dir = os.path.expanduser('~%s/.config/Thunar' %
                                            os.environ['SUDO_USER'])
        else:
            thunar_dir = os.path.expanduser('~/.config/Thunar')
        if os.path.isdir(thunar_dir):
            import ConfigParser
            thunar_volmanrc = '%s/volmanrc' % thunar_dir
            parser = ConfigParser.RawConfigParser()
            parser.optionxform = str # case-sensitive
            parser.read(thunar_volmanrc)
            if not parser.has_section('Configuration'):
                parser.add_section('Configuration')
            for key, value in fields.iteritems():
                if parser.has_option('Configuration', key):
                    previous[key] = parser.get('Configuration', key)
                else:
                    previous[key] = 'TRUE'
                parser.set('Configuration', key, value)
            try:
                thunar_volmanrc_new = open('%s.new' % thunar_volmanrc, 'w')
                parser.write(thunar_volmanrc_new)
                thunar_volmanrc_new.close()
                os.rename('%s.new' % thunar_volmanrc, thunar_volmanrc)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                pass
        return previous

    # Disable gnome-volume-manager automounting to avoid problems during
    # partitioning.
    def disable_volume_manager(self):
        gvm_automount_drives = '/desktop/gnome/volume_manager/automount_drives'
        gvm_automount_media = '/desktop/gnome/volume_manager/automount_media'
        volumes_visible = '/apps/nautilus/desktop/volumes_visible'
        if 'SUDO_USER' in os.environ:
            gconf_dir = ('xml:readwrite:%s' %
                         os.path.expanduser('~%s/.gconf' %
                                            os.environ['SUDO_USER']))
        else:
            gconf_dir = 'xml:readwrite:%s' % os.path.expanduser('~/.gconf')
        self.gconf_previous = {}
        for gconf_key in (gvm_automount_drives, gvm_automount_media,
            volumes_visible):
            subp = subprocess.Popen(['gconftool-2', '--config-source',
                                     gconf_dir, '--get', gconf_key],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    preexec_fn=drop_privileges)
            self.gconf_previous[gconf_key] = subp.communicate()[0].rstrip('\n')
            if self.gconf_previous[gconf_key] != 'false':
                subprocess.call(['gconftool-2', '--set', gconf_key,
                                 '--type', 'bool', 'false'],
                                preexec_fn=drop_privileges)

        self.thunar_previous = self.thunar_set_volmanrc(
            {'AutomountDrives': 'FALSE', 'AutomountMedia': 'FALSE'})

        atexit.register(self.enable_volume_manager)

    def enable_volume_manager(self):
        gvm_automount_drives = '/desktop/gnome/volume_manager/automount_drives'
        gvm_automount_media = '/desktop/gnome/volume_manager/automount_media'
        volumes_visible = '/apps/nautilus/desktop/volumes_visible'
        for gconf_key in (gvm_automount_drives, gvm_automount_media,
            volumes_visible):
            if self.gconf_previous[gconf_key] == '':
                subprocess.call(['gconftool-2', '--unset', gconf_key],
                                preexec_fn=drop_privileges)
            elif self.gconf_previous[gconf_key] != 'false':
                subprocess.call(['gconftool-2', '--set', gconf_key,
                                 '--type', 'bool',
                                 self.gconf_previous[gconf_key]],
                                preexec_fn=drop_privileges)

        if self.thunar_previous:
            self.thunar_set_volmanrc(self.thunar_previous)


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
            first_step = self.stepWelcome
        else:
            first_step = self.stepLanguage
        self.set_current_page(self.steps.page_num(first_step))
        if got_intro:
            # intro_label was the only focusable widget, but got can-focus
            # removed, so we end up with no input focus and thus pressing
            # Enter doesn't activate the default widget. Work around this.
            self.next.grab_focus()

        if not 'UBIQUITY_MIGRATION_ASSISTANT' in os.environ:
            self.steps.remove_page(self.steps.page_num(self.stepMigrationAssistant))
            for step in BREADCRUMB_STEPS:
                if (BREADCRUMB_STEPS[step] >
                    BREADCRUMB_STEPS["stepMigrationAssistant"]):
                    BREADCRUMB_STEPS[step] -= 1
            BREADCRUMB_MAX_STEP -= 1

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
                self.dbfilter = summary.Summary(self)
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


    def customize_installer(self):
        """Initial UI setup."""

        gtk.window_set_default_icon_from_file('/usr/share/pixmaps/'
                                              'ubiquity.png')

        PIXMAPSDIR = os.path.join(PATH, 'pixmaps', self.distro)

        # set pixmaps
        if ( gtk.gdk.get_default_root_window().get_screen().get_width() > 1024 ):
            logo = os.path.join(PIXMAPSDIR, "logo_1280.jpg")
            photo = os.path.join(PIXMAPSDIR, "photo_1280.jpg")
        else:
            logo = os.path.join(PIXMAPSDIR, "logo_1024.jpg")
            photo = os.path.join(PIXMAPSDIR, "photo_1024.jpg")
        if not os.path.exists(logo):
            logo = None
        if not os.path.exists(photo):
            photo = None

        self.logo_image.set_from_file(logo)
        self.photo.set_from_file(photo)

        if self.oem_config:
            self.live_installer.set_title(self.get_string('oem_config_title'))
            self.fullname.set_text('OEM Configuration (temporary user)')
            self.fullname.set_editable(False)
            self.username.set_text('oem')
            self.username.set_editable(False)
            # The UserSetup component takes care of preseeding passwd/user-uid.
            execute('apt-install', 'oem-config-gtk')

        self.live_installer.show()
        self.allow_change_step(False)

        try:
            release_notes = open('/cdrom/.disk/release_notes_url')
            self.release_notes_url.set_uri(
                release_notes.read().rstrip('\n'))
            release_notes.close()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.release_notes_vbox.hide()

        self.tzmap = TimezoneMap(self)
        self.tzmap.tzmap.show()

        if 'UBIQUITY_DEBUG' in os.environ:
            self.password_debug_warning_label.show()

        # set initial bottom bar status
        self.back.hide()


    def poke_screensaver(self):
        """Attempt to make sure that the screensaver doesn't kick in."""
        if os.path.exists('/usr/bin/gnome-screensaver-command'):
            command = ["gnome-screensaver-command", "--poke"]
        elif os.path.exists('/usr/bin/xscreensaver-command'):
            command = ["xscreensaver-command", "--deactivate"]
        else:
            return

        env = ['LC_ALL=C']
        for key, value in os.environ.iteritems():
            if key != 'LC_ALL':
                env.append('%s=%s' % (key, value))
        gobject.spawn_async(command, envp=env,
                            flags=(gobject.SPAWN_SEARCH_PATH |
                                   gobject.SPAWN_STDOUT_TO_DEV_NULL |
                                   gobject.SPAWN_STDERR_TO_DEV_NULL),
                            child_setup=drop_privileges)
        return True


    def set_locales(self):
        """internationalization config. Use only once."""

        domain = self.distro + '-installer'
        gettext.bindtextdomain(domain, LOCALEDIR)
        gtk.glade.bindtextdomain(domain, LOCALEDIR )
        gtk.glade.textdomain(domain)
        gettext.textdomain(domain)
        gettext.install(domain, LOCALEDIR, unicode=1)


    def translate_widgets(self):
        if self.locale is None:
            languages = []
        else:
            languages = [self.locale]
        core_names = ['ubiquity/text/%s' % q for q in self.language_questions]
        for stock_item in ('cancel', 'close', 'go-back', 'go-forward',
                           'ok', 'quit'):
            core_names.append('ubiquity/imported/%s' % stock_item)
        i18n.get_translations(languages=languages, core_names=core_names)

        for widget in self.glade.get_widget_prefix(""):
            self.translate_widget(widget, self.locale)

    def translate_widget(self, widget, lang):
        if isinstance(widget, gtk.Button) and widget.get_use_stock():
            widget.set_label(widget.get_label())

        text = self.get_string(widget.get_name(), lang)
        if text is None:
            return
        name = widget.get_name()

        if isinstance(widget, gtk.Label):
            if name == 'step_label':
                global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
                curstep = '?'
                if self.current_page is not None:
                    current_name = self.step_name(self.current_page)
                    if current_name in BREADCRUMB_STEPS:
                        curstep = str(BREADCRUMB_STEPS[current_name])
                text = text.replace('${INDEX}', curstep)
                text = text.replace('${TOTAL}', str(BREADCRUMB_MAX_STEP))
            widget.set_text(text)

            # Ideally, these attributes would be in the glade file somehow ...
            textlen = len(text.encode("UTF-8"))
            if 'heading_label' in name:
                attrs = pango.AttrList()
                attrs.insert(pango.AttrScale(pango.SCALE_LARGE, 0, textlen))
                attrs.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, textlen))
                widget.set_attributes(attrs)
            elif 'extra_label' in name:
                attrs = pango.AttrList()
                attrs.insert(pango.AttrStyle(pango.STYLE_ITALIC, 0, textlen))
                widget.set_attributes(attrs)
            elif ('group_label' in name or 'warning_label' in name or
                  name in ('drives_label', 'partition_method_label')):
                attrs = pango.AttrList()
                attrs.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, textlen))
                widget.set_attributes(attrs)

        elif isinstance(widget, gtk.Button):
            # TODO evand 2007-06-26: LP #122141 causes a crash unless we keep a
            # reference to the button image.
            tempref = widget.get_image()

            question = i18n.map_widget_name(widget.get_name())
            if question.startswith('ubiquity/imported/'):
                if '|' in text:
                    widget.set_label(text.split('|', 1)[1])
                else:
                    widget.set_label(text)
                stock_id = question[18:]
                widget.set_use_stock(False)
                widget.set_image(gtk.image_new_from_stock(
                    'gtk-%s' % stock_id, gtk.ICON_SIZE_BUTTON))
            else:
                widget.set_label(text)

        elif isinstance(widget, gtk.Window):
            widget.set_title(text)


    def allow_change_step(self, allowed):
        if allowed:
            cursor = None
        else:
            cursor = self.watch
        self.live_installer.window.set_cursor(cursor)
        self.back.set_sensitive(allowed)
        self.next.set_sensitive(allowed and self.allowed_go_forward)
        self.allowed_change_step = allowed

    def allow_go_forward(self, allowed):
        self.next.set_sensitive(allowed and self.allowed_change_step)
        self.allowed_go_forward = allowed


    def dbfilter_handle_status(self):
        """If a dbfilter crashed, ask the user if they want to continue anyway.

        Returns True to continue, or False to try again."""

        if not self.dbfilter_status or self.current_page is None:
            return True

        syslog.syslog('dbfilter_handle_status: %s' % str(self.dbfilter_status))

        # TODO cjwatson 2007-04-04: i18n
        text = ('%s failed with exit code %s. Further information may be '
                'found in /var/log/syslog. Do you want to try running this '
                'step again before continuing? If you do not, your '
                'installation may fail entirely or may be broken.' %
                (self.dbfilter_status[0], self.dbfilter_status[1]))
        dialog = gtk.Dialog('%s crashed' % self.dbfilter_status[0],
                            self.live_installer, gtk.DIALOG_MODAL,
                            (gtk.STOCK_QUIT, gtk.RESPONSE_CLOSE,
                             'Continue anyway', 1,
                             'Try again', 2))
        self.dbfilter_status = None
        label = gtk.Label(text)
        label.set_line_wrap(True)
        label.set_selectable(True)
        dialog.vbox.add(label)
        dialog.show_all()
        response = dialog.run()
        dialog.hide()
        syslog.syslog('dbfilter_handle_status: response %d' % response)
        if response == 1:
            return True
        elif response == gtk.RESPONSE_CLOSE:
            self.quit()
        else:
            step = self.step_name(self.steps.get_current_page())
            if step.startswith("stepPart"):
                self.set_current_page(self.steps.page_num(self.stepPartAuto))
            return False


    def show_intro(self):
        """Show some introductory text, if available."""

        intro = os.path.join(PATH, 'intro.txt')

        if os.path.isfile(intro):
            intro_file = open(intro)
            self.intro_label.set_markup(intro_file.read().rstrip('\n'))
            intro_file.close()
            return True
        else:
            return False


    def step_name(self, step_index):
        return self.steps.get_nth_page(step_index).get_name()


    def set_current_page(self, current):
        if self.steps.get_current_page() == current:
            # self.steps.set_current_page() will do nothing. Update state
            # ourselves.
            self.on_steps_switch_page(
                self.steps, self.steps.get_nth_page(current), current)
        else:
            self.steps.set_current_page(current)

    # Methods

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

        dbfilter = install.Install(self)
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

        self.finished_dialog.run()


    def reboot(self, *args):
        """reboot the system after installing process."""

        self.returncode = 10
        self.quit()


    def do_reboot(self):
        """Callback for main program to actually reboot the machine."""

        if (os.path.exists("/usr/bin/gdm-signal") and
            os.path.exists("/usr/bin/gnome-session-save")):
            execute("gdm-signal", "--reboot")
            if 'SUDO_UID' in os.environ:
                user = '#%d' % int(os.environ['SUDO_UID'])
            else:
                user = 'ubuntu'
            execute("sudo", "-u", user, "-H",
                    "gnome-session-save", "--kill", "--silent")
        else:
            execute("reboot")


    def quit(self):
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        if gtk.main_level() > 0:
            gtk.main_quit()


    # Callbacks
    def on_cancel_clicked(self, widget):
        self.warning_dialog.show()
        response = self.warning_dialog.run()
        self.warning_dialog.hide()
        if response == gtk.RESPONSE_CLOSE:
            self.current_page = None
            self.quit()
            return False
        else:
            return True # stop processing


    def on_live_installer_delete_event(self, widget, event):
        return self.on_cancel_clicked(widget)


    def info_loop(self, widget):
        """check if all entries from Identification screen are filled. Callback
        defined in glade file."""

        if (widget is not None and widget.get_name() == 'fullname' and
            not self.username_edited):
            self.username.handler_block(self.username_changed_id)
            new_username = widget.get_text().split(' ')[0]
            new_username = new_username.encode('ascii', 'ascii_transliterate')
            new_username = new_username.lower()
            self.username.set_text(new_username)
            self.username.handler_unblock(self.username_changed_id)
        elif (widget is not None and widget.get_name() == 'username' and
              not self.hostname_edited):
            if self.laptop:
                hostname_suffix = '-laptop'
            else:
                hostname_suffix = '-desktop'
            self.hostname.handler_block(self.hostname_changed_id)
            self.hostname.set_text(widget.get_text() + hostname_suffix)
            self.hostname.handler_unblock(self.hostname_changed_id)

        complete = True
        for name in ('username', 'password', 'verified_password', 'hostname'):
            if getattr(self, name).get_text() == '':
                complete = False
        self.allow_go_forward(complete)

    def on_username_changed(self, widget):
        self.username_edited = (widget.get_text() != '')

    def on_hostname_changed(self, widget):
        self.hostname_edited = (widget.get_text() != '')

    def on_next_clicked(self, widget):
        """Callback to control the installation process between steps."""

        if not self.allowed_change_step or not self.allowed_go_forward:
            return

        self.allow_change_step(False)

        step = self.step_name(self.steps.get_current_page())

        if step == "stepUserInfo":
            self.username_error_box.hide()
            self.password_error_box.hide()
            self.hostname_error_box.hide()

        if step == "stepMigrationAssistant":
            for u in self.ma_new_users.iterkeys():
                self.ma_new_users[u]['password-error'] = ''
                self.ma_new_users[u]['loginname-error'] = ''
            self.ma_seed_userinfo()
            # To get a watch cursor and non-sensitive next button before the
            # next page.
            while gtk.events_pending():
                gtk.main_iteration(False)

        if self.dbfilter is not None:
            self.dbfilter.ok_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        elif gtk.main_level() > 0:
            gtk.main_quit()

    def on_keyboardlayoutview_row_activated(self, treeview, path, view_column):
        self.next.activate()

    def on_keyboard_layout_selected(self, start_editing, *args):
        if isinstance(self.dbfilter, console_setup.ConsoleSetup):
            layout = self.get_keyboard()
            if layout is not None:
                self.current_layout = layout
                self.dbfilter.change_layout(layout)

    def on_keyboardvariantview_row_activated(self, treeview, path,
                                             view_column):
        self.next.activate()

    def on_keyboard_variant_selected(self, start_editing, *args):
        if isinstance(self.dbfilter, console_setup.ConsoleSetup):
            layout = self.get_keyboard()
            variant = self.get_keyboard_variant()
            if layout is not None and variant is not None:
                self.dbfilter.apply_keyboard(layout, variant)

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
        # Ready to install
        elif step == "stepReady":
            self.live_installer.hide()
            self.current_page = None
            self.installing = True
            self.progress_loop()
            return

        step = self.step_name(self.steps.get_current_page())
        syslog.syslog('Step_after = %s' % step)

        if step == "stepReady":
            self.next.set_label("Install")

    def process_identification (self):
        """Processing identification step tasks."""

        error_msg = []
        error = 0

        # Validation stuff

        # checking hostname entry
        hostname = self.hostname.get_property('text')
        for result in validation.check_hostname(hostname):
            if result == validation.HOSTNAME_LENGTH:
                error_msg.append("The hostname must be between 2 and 63 characters long.")
            elif result == validation.HOSTNAME_BADCHAR:
                error_msg.append("The hostname may only contain letters, digits, hyphens, and dots.")
            elif result == validation.HOSTNAME_BADHYPHEN:
                error_msg.append("The hostname may not start or end with a hyphen.")

        # showing warning message is error is set
        if len(error_msg) != 0:
            self.hostname_error_reason.set_text("\n".join(error_msg))
            self.hostname_error_box.show()
        else:
            self.steps.next_page()


    def process_autopartitioning(self):
        """Processing automatic partitioning step tasks."""

        while gtk.events_pending ():
            gtk.main_iteration ()

        # For safety, if we somehow ended up improperly initialised
        # then go to manual partitioning.
        choice = self.get_autopartition_choice()[0]
        if self.manual_choice is None or choice == self.manual_choice:
            self.steps.next_page()
        else:
            if not 'UBIQUITY_MIGRATION_ASSISTANT' in os.environ:
                self.info_loop(None)
                self.set_current_page(self.steps.page_num(self.stepUserInfo))
            else:
                self.set_current_page(self.steps.page_num(self.stepMigrationAssistant))


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
            self.set_current_page(self.steps.page_num(self.stepKeyboardConf))
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


    def selected_language (self, selection):
        (model, iterator) = selection.get_selected()
        if iterator is not None:
            value = unicode(model.get_value(iterator, 0))
            return self.language_choice_map[value][1]
        else:
            return ''


    def link_button_browser (self, button, uri):
        selection = self.language_treeview.get_selection()
        lang = self.selected_language(selection)
        lang = lang.split('.')[0] # strip encoding
        uri = uri.replace('${LANG}', lang)
        subprocess.Popen(['sensible-browser', uri], close_fds=True)


    def on_language_treeview_row_activated (self, treeview, path, view_column):
        self.next.activate()

    def on_language_treeview_selection_changed (self, selection):
        lang = self.selected_language(selection)
        if lang:
            # strip encoding; we use UTF-8 internally no matter what
            lang = lang.split('.')[0].lower()
            for widget in self.language_questions:
                self.translate_widget(getattr(self, widget), lang)


    def on_new_size_scale_format_value (self, widget, value):
        # TODO cjwatson 2006-01-09: get minsize/maxsize through to here
        if self.resize_max_size is not None:
            size = value * self.resize_max_size / 100
            return '%d%% (%s)' % (value, format_size(size))
        else:
            return '%d%%' % value


    def on_steps_switch_page (self, foo, bar, current):
        self.current_page = current
        self.translate_widget(self.step_label, self.locale)
        syslog.syslog('switched to page %s' % self.step_name(current))


    def on_autopartition_toggled (self, widget):
        """Update autopartitioning screen when a button is selected."""

        choice = unicode(widget.get_label(), 'utf-8', 'replace')
        if choice is not None and choice in self.autopartition_extras:
            element = self.autopartition_extras[choice]
            if widget.get_active():
                element.set_sensitive(True)
            else:
                element.set_sensitive(False)


    # Callbacks provided to components.

    def watch_debconf_fd (self, from_debconf, process_input):
        gobject.io_add_watch(from_debconf,
                             gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
                             self.watch_debconf_fd_helper, process_input)


    def watch_debconf_fd_helper (self, source, cb_condition, callback):
        debconf_condition = 0
        if (cb_condition & gobject.IO_IN) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_IN
        if (cb_condition & gobject.IO_ERR) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        if (cb_condition & gobject.IO_HUP) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_HUP

        return callback(source, debconf_condition)


    def debconf_progress_start (self, progress_min, progress_max, progress_title):
        if self.progress_cancelled:
            return False
        if self.current_page is not None:
            self.debconf_progress_window.set_transient_for(self.live_installer)
        else:
            self.debconf_progress_window.set_transient_for(None)
        if progress_title is None:
            progress_title = ""
        if self.progress_position.depth() == 0:
            self.debconf_progress_window.set_title(progress_title)

        self.progress_position.start(progress_min, progress_max,
                                     progress_title)
        self.progress_title.set_markup(
            '<big><b>' +
            xml.sax.saxutils.escape(self.progress_position.title()) +
            '</b></big>')
        self.debconf_progress_set(0)
        self.progress_info.set_text('')
        self.debconf_progress_window.show()
        return True

    def debconf_progress_set (self, progress_val):
        if self.progress_cancelled:
            return False
        self.progress_position.set(progress_val)
        fraction = self.progress_position.fraction()
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text('%s%%' % int(fraction * 100))
        return True

    def debconf_progress_step (self, progress_inc):
        if self.progress_cancelled:
            return False
        self.progress_position.step(progress_inc)
        fraction = self.progress_position.fraction()
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text('%s%%' % int(fraction * 100))
        return True

    def debconf_progress_info (self, progress_info):
        if self.progress_cancelled:
            return False
        self.progress_info.set_markup(
            '<i>' + xml.sax.saxutils.escape(progress_info) + '</i>')
        return True

    def debconf_progress_stop (self):
        if self.progress_cancelled:
            self.progress_cancelled = False
            return False
        self.progress_position.stop()
        if self.progress_position.depth() == 0:
            self.debconf_progress_window.hide()
        else:
            self.progress_title.set_markup(
                '<big><b>' +
                xml.sax.saxutils.escape(self.progress_position.title()) +
                '</b></big>')
        return True

    def debconf_progress_region (self, region_start, region_end):
        self.progress_position.set_region(region_start, region_end)

    def debconf_progress_cancellable (self, cancellable):
        if cancellable:
            self.progress_cancel_button.show()
        else:
            self.progress_cancel_button.hide()
            self.progress_cancelled = False

    def on_progress_cancel_button_clicked (self, button):
        self.progress_cancelled = True


    def debconffilter_done (self, dbfilter):
        if BaseFrontend.debconffilter_done(self, dbfilter):
            if isinstance(dbfilter, summary.Summary):
                # The Summary component is just there to gather information,
                # and won't call run_main_loop() for itself.
                self.allow_change_step(True)
            elif gtk.main_level() > 0:
                gtk.main_quit()
            return True
        else:
            return False


    def set_language_choices (self, choices, choice_map):
        BaseFrontend.set_language_choices(self, choices, choice_map)
        if len(self.language_treeview.get_columns()) < 1:
            column = gtk.TreeViewColumn(None, gtk.CellRendererText(), text=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.language_treeview.append_column(column)
            selection = self.language_treeview.get_selection()
            selection.connect('changed',
                              self.on_language_treeview_selection_changed)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.language_treeview.set_model(list_store)
        for choice in choices:
            list_store.append([choice])


    def set_language (self, language):
        model = self.language_treeview.get_model()
        iterator = model.iter_children(None)
        while iterator is not None:
            if unicode(model.get_value(iterator, 0)) == language:
                path = model.get_path(iterator)
                self.language_treeview.get_selection().select_path(path)
                self.language_treeview.scroll_to_cell(
                    path, use_align=True, row_align=0.5)
                break
            iterator = model.iter_next(iterator)


    def get_language (self):
        selection = self.language_treeview.get_selection()
        (model, iterator) = selection.get_selected()
        if iterator is None:
            return 'C'
        else:
            value = unicode(model.get_value(iterator, 0))
            return self.language_choice_map[value][0]


    def set_timezone (self, timezone):
        self.tzmap.set_tz_from_name(timezone)


    def get_timezone (self):
        return self.tzmap.get_selected_tz_name()


    def set_keyboard_choices(self, choices):
        layouts = gtk.ListStore(gobject.TYPE_STRING)
        self.keyboardlayoutview.set_model(layouts)
        for v in sorted(choices):
            layouts.append([v])

        if len(self.keyboardlayoutview.get_columns()) < 1:
            column = gtk.TreeViewColumn("Layout", gtk.CellRendererText(), text=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.keyboardlayoutview.append_column(column)
            selection = self.keyboardlayoutview.get_selection()
            selection.connect('changed',
                              self.on_keyboard_layout_selected)

        if self.current_layout is not None:
            self.set_keyboard(self.current_layout)

    def set_keyboard (self, layout):
        BaseFrontend.set_keyboard(self, layout)
        model = self.keyboardlayoutview.get_model()
        if model is None:
            return
        iterator = model.iter_children(None)
        while iterator is not None:
            if unicode(model.get_value(iterator, 0)) == layout:
                path = model.get_path(iterator)
                self.keyboardlayoutview.get_selection().select_path(path)
                self.keyboardlayoutview.scroll_to_cell(
                    path, use_align=True, row_align=0.5)
                break
            iterator = model.iter_next(iterator)

    def get_keyboard (self):
        selection = self.keyboardlayoutview.get_selection()
        (model, iterator) = selection.get_selected()
        if iterator is None:
            return None
        else:
            return unicode(model.get_value(iterator, 0))

    def set_keyboard_variant_choices(self, choices):
        variants = gtk.ListStore(gobject.TYPE_STRING)
        self.keyboardvariantview.set_model(variants)
        for v in sorted(choices):
            variants.append([v])

        if len(self.keyboardvariantview.get_columns()) < 1:
            column = gtk.TreeViewColumn("Variant", gtk.CellRendererText(), text=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.keyboardvariantview.append_column(column)
            selection = self.keyboardvariantview.get_selection()
            selection.connect('changed',
                              self.on_keyboard_variant_selected)

    def set_keyboard_variant (self, variant):
        model = self.keyboardvariantview.get_model()
        if model is None:
            return
        iterator = model.iter_children(None)
        while iterator is not None:
            if unicode(model.get_value(iterator, 0)) == variant:
                path = model.get_path(iterator)
                self.keyboardvariantview.get_selection().select_path(path)
                self.keyboardvariantview.scroll_to_cell(
                    path, use_align=True, row_align=0.5)
                break
            iterator = model.iter_next(iterator)

    def get_keyboard_variant (self):
        selection = self.keyboardvariantview.get_selection()
        (model, iterator) = selection.get_selected()
        if iterator is None:
            return None
        else:
            return unicode(model.get_value(iterator, 0))


    def set_autopartition_choices (self, choices, extra_options,
                                   resize_choice, manual_choice):
        BaseFrontend.set_autopartition_choices(self, choices, extra_options,
                                               resize_choice, manual_choice)

        for child in self.autopartition_vbox.get_children():
            self.autopartition_vbox.remove(child)

        firstbutton = None
        for choice in choices:
            button = gtk.RadioButton(firstbutton, choice, False)
            if firstbutton is None:
                firstbutton = button
            self.autopartition_vbox.add(button)

            if choice in extra_options:
                alignment = gtk.Alignment(xscale=1, yscale=1)
                alignment.set_padding(0, 0, 12, 0)
                if choice == resize_choice:
                    hbox = gtk.HBox(spacing=6)
                    alignment.add(hbox)
                    new_size_label = gtk.Label("New partition size:")
                    new_size_label.set_name('new_size_label')
                    self.translate_widget(new_size_label, self.locale)
                    new_size_label.set_selectable(True)
                    new_size_label.set_property('can-focus', False)
                    hbox.pack_start(new_size_label, expand=False, fill=False)
                    self.new_size_scale = gtk.HScale(
                        gtk.Adjustment(0, 0, 100, 1, 10, 0))
                    self.new_size_scale.set_draw_value(True)
                    self.new_size_scale.set_value_pos(gtk.POS_TOP)
                    self.new_size_scale.set_digits(0)
                    self.new_size_scale.set_update_policy(
                        gtk.UPDATE_CONTINUOUS)
                    self.new_size_scale.connect(
                        'format_value', self.on_new_size_scale_format_value)
                    self.resize_min_size, self.resize_max_size = \
                        extra_options[choice]
                    if (self.resize_min_size is not None and
                        self.resize_max_size is not None):
                        min_percent = int(math.ceil(
                            100 * self.resize_min_size / self.resize_max_size))
                        self.new_size_scale.set_range(min_percent, 100)
                        self.new_size_scale.set_value(
                            int((min_percent + 100) / 2))
                    hbox.pack_start(self.new_size_scale, expand=True, fill=True)
                elif choice != manual_choice:
                    vbox = gtk.VBox(spacing=6)
                    alignment.add(vbox)
                    extra_firstbutton = None
                    for extra in extra_options[choice]:
                        extra_button = gtk.RadioButton(
                            extra_firstbutton, extra, False)
                        if extra_firstbutton is None:
                            extra_firstbutton = extra_button
                        vbox.add(extra_button)
                self.autopartition_vbox.pack_start(alignment,
                                                   expand=False, fill=False)
                self.autopartition_extras[choice] = alignment

                self.on_autopartition_toggled(button)
                button.connect('toggled', self.on_autopartition_toggled)
        if firstbutton is not None:
            firstbutton.set_active(True)

        self.autopartition_vbox.show_all()

        # make sure we're on the autopartitioning page
        self.set_current_page(self.steps.page_num(self.stepPartAuto))


    def get_autopartition_choice (self):
        for button in self.autopartition_vbox.get_children():
            if isinstance(button, gtk.Button):
                if button.get_active():
                    choice = unicode(button.get_label(), 'utf-8', 'replace')
                    break
        else:
            raise AssertionError, "no active autopartitioning choice"

        if choice == self.resize_choice:
            # resize_choice should have been hidden otherwise
            assert self.new_size_scale is not None
            return choice, self.new_size_scale.get_value()
        elif (choice != self.manual_choice and
              choice in self.autopartition_extras):
            vbox = self.autopartition_extras[choice].child
            for button in vbox.get_children():
                if isinstance(button, gtk.Button):
                    if button.get_active():
                        return choice, unicode(button.get_label(),
                                               'utf-8', 'replace')
            else:
                return choice, None
        else:
            return choice, None


    def partman_column_name (self, column, cell, model, iterator):
        partition = model[iterator][1]
        if 'id' not in partition:
            # whole disk
            cell.set_property('text', partition['device'])
        elif partition['parted']['fs'] != 'free':
            cell.set_property('text', '  %s' % partition['parted']['path'])
        elif partition['parted']['type'] == 'unusable':
            unusable = self.get_string('partman/text/unusable')
            cell.set_property('text', '  %s' % unusable)
        else:
            # TODO cjwatson 2006-10-30 i18n; partman uses "FREE SPACE" which
            # feels a bit too SHOUTY for this interface.
            cell.set_property('text', '  free space')

    def partman_column_type (self, column, cell, model, iterator):
        partition = model[iterator][1]
        if 'id' not in partition or 'method' not in partition:
            cell.set_property('text', '')
        elif ('filesystem' in partition and
              partition['method'] in ('format', 'keep')):
            cell.set_property('text', partition['acting_filesystem'])
        else:
            cell.set_property('text', partition['method'])

    def partman_column_mountpoint (self, column, cell, model, iterator):
        partition = model[iterator][1]
        if isinstance(self.dbfilter, partman.Partman):
            mountpoint = self.dbfilter.get_current_mountpoint(partition)
            if mountpoint is None:
                mountpoint = ''
        else:
            mountpoint = ''
        cell.set_property('text', mountpoint)

    def partman_column_format (self, column, cell, model, iterator):
        partition = model[iterator][1]
        if 'id' not in partition:
            cell.set_property('visible', False)
            cell.set_property('active', False)
            cell.set_property('activatable', False)
        elif 'method' in partition:
            cell.set_property('visible', True)
            cell.set_property('active', partition['method'] == 'format')
            cell.set_property('activatable', 'can_activate_format' in partition)
        else:
            cell.set_property('visible', True)
            cell.set_property('active', False)
            cell.set_property('activatable', False)

    def partman_column_format_toggled (self, cell, path, user_data):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return
        model = user_data
        devpart = model[path][0]
        partition = model[path][1]
        if 'id' not in partition or 'method' not in partition:
            return
        self.allow_change_step(False)
        self.dbfilter.edit_partition(devpart, format='dummy')

    def partman_column_size (self, column, cell, model, iterator):
        partition = model[iterator][1]
        if 'id' not in partition:
            cell.set_property('text', '')
        else:
            # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
            # partman expects.
            size_mb = int(partition['parted']['size']) / 1000000
            cell.set_property('text', '%d MB' % size_mb)

    def partman_column_used (self, column, cell, model, iterator):
        partition = model[iterator][1]
        if 'id' not in partition or partition['parted']['fs'] == 'free':
            cell.set_property('text', '')
        elif 'resize_min_size' not in partition:
            # TODO cjwatson 2007-03-26: i18n
            cell.set_property('text', 'unknown')
        else:
            # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
            # partman expects.
            size_mb = int(partition['resize_min_size']) / 1000000
            cell.set_property('text', '%d MB' % size_mb)

    def partman_popup (self, widget, event):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return

        model, iterator = widget.get_selection().get_selected()
        if iterator is None:
            devpart = None
            partition = None
        else:
            devpart = model[iterator][0]
            partition = model[iterator][1]

        partition_list_menu = gtk.Menu()
        for action in self.dbfilter.get_actions(devpart, partition):
            if action == 'new_label':
                # TODO cjwatson 2006-12-21: i18n;
                # partman-partitioning/text/label text is quite long?
                new_label_item = gtk.MenuItem('New partition table')
                new_label_item.connect(
                    'activate', self.on_partition_list_new_label_activate,
                    devpart, partition)
                partition_list_menu.append(new_label_item)
            elif action == 'new':
                # TODO cjwatson 2006-10-31: i18n
                new_item = gtk.MenuItem('New partition')
                new_item.connect(
                    'activate', self.on_partition_list_new_activate,
                    devpart, partition)
                partition_list_menu.append(new_item)
            elif action == 'edit':
                # TODO cjwatson 2006-10-31: i18n
                edit_item = gtk.MenuItem('Edit partition')
                edit_item.connect(
                    'activate', self.on_partition_list_edit_activate,
                    devpart, partition)
                partition_list_menu.append(edit_item)
            elif action == 'delete':
                # TODO cjwatson 2006-10-31: i18n
                delete_item = gtk.MenuItem('Delete partition')
                delete_item.connect(
                    'activate', self.on_partition_list_delete_activate,
                    devpart, partition)
                partition_list_menu.append(delete_item)
        if partition_list_menu.get_children():
            partition_list_menu.append(gtk.SeparatorMenuItem())
        undo_item = gtk.MenuItem(
            self.get_string('partman/text/undo_everything'))
        undo_item.connect('activate', self.on_partition_list_undo_activate)
        partition_list_menu.append(undo_item)
        partition_list_menu.show_all()

        if event:
            button = event.button
            time = event.get_time()
        else:
            button = 0
            time = 0
        partition_list_menu.popup(None, None, None, button, time)

    def partman_create_dialog (self, devpart, partition):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return

        self.partition_create_dialog.show_all()

        # TODO cjwatson 2006-11-01: Because partman doesn't use a question
        # group for these, we have to figure out in advance whether each
        # question is going to be asked.

        if partition['parted']['type'] == 'pri/log':
            # Is there already an extended partition?
            model = self.partition_list_treeview.get_model()
            for otherpart in [row[1] for row in model]:
                if (otherpart['dev'] == partition['dev'] and
                    'id' in otherpart and
                    otherpart['parted']['type'] == 'logical'):
                    self.partition_create_type_logical.set_active(True)
                    break
            else:
                self.partition_create_type_primary.set_active(True)
        else:
            self.partition_create_type_label.hide()
            self.partition_create_type_primary.hide()
            self.partition_create_type_logical.hide()

        # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
        # partman expects.
        max_size_mb = int(partition['parted']['size']) / 1000000
        self.partition_create_size_spinbutton.set_adjustment(
            gtk.Adjustment(value=max_size_mb, upper=max_size_mb,
                           step_incr=1, page_incr=100, page_size=100))
        self.partition_create_size_spinbutton.set_value(max_size_mb)

        self.partition_create_use_combo.clear()
        renderer = gtk.CellRendererText()
        self.partition_create_use_combo.pack_start(renderer)
        self.partition_create_use_combo.add_attribute(renderer, 'text', 1)
        list_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        for method, name in partman.Partman.create_use_as():
            list_store.append([method, name])
        self.partition_create_use_combo.set_model(list_store)
        if list_store.get_iter_first():
            self.partition_create_use_combo.set_active(0)

        # TODO cjwatson 2006-11-01: set up mount point combo
        self.partition_create_mount_combo.child.set_text('')

        response = self.partition_create_dialog.run()
        self.partition_create_dialog.hide()

        if (response == gtk.RESPONSE_OK and
            isinstance(self.dbfilter, partman.Partman)):
            if partition['parted']['type'] == 'primary':
                prilog = partman.PARTITION_TYPE_PRIMARY
            elif partition['parted']['type'] == 'logical':
                prilog = partman.PARTITION_TYPE_LOGICAL
            elif partition['parted']['type'] == 'pri/log':
                if self.partition_create_type_primary.get_active():
                    prilog = partman.PARTITION_TYPE_PRIMARY
                else:
                    prilog = partman.PARTITION_TYPE_LOGICAL

            if self.partition_create_place_beginning.get_active():
                place = partman.PARTITION_PLACE_BEGINNING
            else:
                place = partman.PARTITION_PLACE_END

            method_iter = self.partition_create_use_combo.get_active_iter()
            if method_iter is None:
                method = None
            else:
                model = self.partition_create_use_combo.get_model()
                method = model.get_value(method_iter, 1)

            mountpoint = self.partition_create_mount_combo.child.get_text()

            self.allow_change_step(False)
            self.dbfilter.create_partition(
                devpart,
                str(self.partition_create_size_spinbutton.get_value()),
                prilog, place, method, mountpoint)

    def on_partition_create_use_combo_changed (self, combobox):
        model = combobox.get_model()
        iterator = combobox.get_active_iter()
        # If the selected method isn't a filesystem, then selecting a mount
        # point makes no sense.
        if iterator is None or model[iterator][0] != 'filesystem':
            self.partition_create_mount_combo.child.set_text('')
            self.partition_create_mount_combo.set_sensitive(False)
        else:
            self.partition_create_mount_combo.set_sensitive(True)

    def partman_edit_dialog (self, devpart, partition):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return

        self.partition_edit_dialog.show_all()

        current_size = None
        if ('can_resize' not in partition or not partition['can_resize'] or
            'resize_min_size' not in partition or
            'resize_max_size' not in partition):
            self.partition_edit_size_label.hide()
            self.partition_edit_size_spinbutton.hide()
        else:
            # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
            # partman expects.
            min_size_mb = int(partition['resize_min_size']) / 1000000
            cur_size_mb = int(partition['parted']['size']) / 1000000
            max_size_mb = int(partition['resize_max_size']) / 1000000
            # Bad things happen if the current size is out of bounds.
            min_size_mb = min(min_size_mb, cur_size_mb)
            max_size_mb = max(cur_size_mb, max_size_mb)
            self.partition_edit_size_spinbutton.set_adjustment(
                gtk.Adjustment(value=cur_size_mb, lower=min_size_mb,
                               upper=max_size_mb,
                               step_incr=1, page_incr=100, page_size=100))
            self.partition_edit_size_spinbutton.set_value(cur_size_mb)
            current_size = str(self.partition_edit_size_spinbutton.get_value())

        self.partition_edit_use_combo.clear()
        renderer = gtk.CellRendererText()
        self.partition_edit_use_combo.pack_start(renderer)
        self.partition_edit_use_combo.add_attribute(renderer, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        for script, arg, option in partition['method_choices']:
            list_store.append([arg])
        self.partition_edit_use_combo.set_model(list_store)
        current_method = self.dbfilter.get_current_method(partition)
        if current_method:
            iterator = list_store.get_iter_first()
            while iterator:
                if list_store[iterator][0] == current_method:
                    self.partition_edit_use_combo.set_active_iter(iterator)
                    break
                iterator = list_store.iter_next(iterator)

        # TODO cjwatson 2006-11-02: mountpoint_choices won't be available
        # unless the method is already one that can be mounted, so we may
        # need to calculate this dynamically based on the method instead of
        # relying on cached information from partman
        list_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        if 'mountpoint_choices' in partition:
            for mp, choice_c, choice in partition['mountpoint_choices']:
                list_store.append([mp, choice])
        self.partition_edit_mount_combo.set_model(list_store)
        if self.partition_edit_mount_combo.get_text_column() == -1:
            self.partition_edit_mount_combo.set_text_column(0)
        current_mountpoint = self.dbfilter.get_current_mountpoint(partition)
        if current_mountpoint is not None:
            self.partition_edit_mount_combo.child.set_text(current_mountpoint)
            iterator = list_store.get_iter_first()
            while iterator:
                if list_store[iterator][0] == current_mountpoint:
                    self.partition_edit_mount_combo.set_active_iter(iterator)
                    break
                iterator = list_store.iter_next(iterator)

        response = self.partition_edit_dialog.run()
        self.partition_edit_dialog.hide()

        if (response == gtk.RESPONSE_OK and
            isinstance(self.dbfilter, partman.Partman)):
            size = None
            if current_size is not None:
                size = str(self.partition_edit_size_spinbutton.get_value())

            method_iter = self.partition_edit_use_combo.get_active_iter()
            if method_iter is None:
                method = None
            else:
                model = self.partition_edit_use_combo.get_model()
                method = model.get_value(method_iter, 0)

            mountpoint = self.partition_edit_mount_combo.child.get_text()

            if (current_size is not None and size is not None and
                current_size == size):
                size = None
            if method == current_method:
                method = None
            if mountpoint == current_mountpoint:
                mountpoint = None

            if (size is not None or method is not None or
                mountpoint is not None):
                self.allow_change_step(False)
                self.dbfilter.edit_partition(devpart, size, method, mountpoint)

    def on_partition_edit_use_combo_changed (self, combobox):
        model = combobox.get_model()
        iterator = combobox.get_active_iter()
        # If the selected method isn't a filesystem, then selecting a mount
        # point makes no sense. TODO cjwatson 2007-01-31: Unfortunately we
        # have to hardcode the list of known filesystems here.
        known_filesystems = ('ext3', 'ext2', 'reiserfs', 'jfs', 'xfs',
                             'fat16', 'fat32', 'ntfs')
        if iterator is None or model[iterator][0] not in known_filesystems:
            self.partition_edit_mount_combo.child.set_text('')
            self.partition_edit_mount_combo.set_sensitive(False)
        else:
            self.partition_edit_mount_combo.set_sensitive(True)

    def on_partition_list_treeview_button_press_event (self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            path_at_pos = widget.get_path_at_pos(int(event.x), int(event.y))
            if path_at_pos is not None:
                selection = widget.get_selection()
                selection.unselect_all()
                selection.select_path(path_at_pos[0])

            self.partman_popup(widget, event)
            return True

    def on_partition_list_treeview_popup_menu (self, widget):
        self.partman_popup(widget, None)
        return True

    def on_partition_list_treeview_selection_changed (self, selection):
        if not isinstance(self.dbfilter, partman.Partman):
            return

        for child in self.partition_list_buttonbox.get_children():
            self.partition_list_buttonbox.remove(child)

        model, iterator = selection.get_selected()
        if iterator is None:
            devpart = None
            partition = None
        else:
            devpart = model[iterator][0]
            partition = model[iterator][1]

        for action in self.dbfilter.get_actions(devpart, partition):
            if action == 'new_label':
                # TODO cjwatson 2007-02-19: i18n;
                # partman-partitioning/text/label is too long unless we can
                # figure out how to make the row of buttons auto-wrap
                new_label_button = gtk.Button('New partition table')
                new_label_button.connect(
                    'clicked', self.on_partition_list_new_label_activate,
                    devpart, partition)
                self.partition_list_buttonbox.pack_start(new_label_button,
                                                         False, False)
            elif action == 'new':
                # TODO cjwatson 2007-02-19: i18n
                new_button = gtk.Button('New partition')
                new_button.connect(
                    'clicked', self.on_partition_list_new_activate,
                    devpart, partition)
                self.partition_list_buttonbox.pack_start(new_button,
                                                         False, False)
            elif action == 'edit':
                # TODO cjwatson 2007-02-19: i18n
                edit_button = gtk.Button('Edit partition')
                edit_button.connect(
                    'clicked', self.on_partition_list_edit_activate,
                    devpart, partition)
                self.partition_list_buttonbox.pack_start(edit_button,
                                                         False, False)
            elif action == 'delete':
                # TODO cjwatson 2007-02-19: i18n
                delete_button = gtk.Button('Delete partition')
                delete_button.connect(
                    'clicked', self.on_partition_list_delete_activate,
                    devpart, partition)
                self.partition_list_buttonbox.pack_start(delete_button,
                                                         False, False)
        undo_button = gtk.Button(
            self.get_string('partman/text/undo_everything'))
        undo_button.connect('clicked', self.on_partition_list_undo_activate)
        self.partition_list_buttonbox.pack_start(undo_button, False, False)
        self.partition_list_buttonbox.show_all()

    def on_partition_list_treeview_row_activated (self, treeview,
                                                  path, view_column):
        if not self.allowed_change_step:
            return
        model = treeview.get_model()
        try:
            devpart = model[path][0]
            partition = model[path][1]
        except (IndexError, KeyError):
            return

        if 'id' not in partition:
            # Are there already partitions on this disk? If so, don't allow
            # activating the row to offer to create a new partition table,
            # to avoid mishaps.
            for otherpart in [row[1] for row in model]:
                if otherpart['dev'] == partition['dev'] and 'id' in otherpart:
                    break
            else:
                if not isinstance(self.dbfilter, partman.Partman):
                    return
                self.allow_change_step(False)
                self.dbfilter.create_label(devpart)
        elif partition['parted']['fs'] == 'free':
            if 'can_new' in partition and partition['can_new']:
                self.partman_create_dialog(devpart, partition)
        else:
            self.partman_edit_dialog(devpart, partition)

    def on_partition_list_new_label_activate (self, widget,
                                              devpart, partition):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return
        self.allow_change_step(False)
        self.dbfilter.create_label(devpart)

    def on_partition_list_new_activate (self, widget, devpart, partition):
        self.partman_create_dialog(devpart, partition)

    def on_partition_list_edit_activate (self, widget, devpart, partition):
        self.partman_edit_dialog(devpart, partition)

    def on_partition_list_delete_activate (self, widget, devpart, partition):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return
        self.allow_change_step(False)
        self.dbfilter.delete_partition(devpart)

    def on_partition_list_undo_activate (self, widget):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return
        self.allow_change_step(False)
        self.dbfilter.undo()

    def update_partman (self, disk_cache, partition_cache, cache_order):
        partition_tree_model = self.partition_list_treeview.get_model()
        if partition_tree_model is None:
            partition_tree_model = gtk.ListStore(gobject.TYPE_STRING,
                                                 gobject.TYPE_PYOBJECT)
            for item in cache_order:
                if item in disk_cache:
                    partition_tree_model.append([item, disk_cache[item]])
                else:
                    partition_tree_model.append([item, partition_cache[item]])

            # TODO cjwatson 2006-08-05: i18n
            cell_name = gtk.CellRendererText()
            column_name = gtk.TreeViewColumn("Device", cell_name)
            column_name.set_cell_data_func(cell_name, self.partman_column_name)
            column_name.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.partition_list_treeview.append_column(column_name)

            cell_type = gtk.CellRendererText()
            column_type = gtk.TreeViewColumn("Type", cell_type)
            column_type.set_cell_data_func(cell_type, self.partman_column_type)
            column_type.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.partition_list_treeview.append_column(column_type)

            cell_mountpoint = gtk.CellRendererText()
            column_mountpoint = gtk.TreeViewColumn("Mount point", cell_mountpoint)
            column_mountpoint.set_cell_data_func(
                cell_mountpoint, self.partman_column_mountpoint)
            column_mountpoint.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.partition_list_treeview.append_column(column_mountpoint)

            cell_format = gtk.CellRendererToggle()
            column_format = gtk.TreeViewColumn("Format?", cell_format)
            column_format.set_cell_data_func(
                cell_format, self.partman_column_format)
            column_format.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            cell_format.connect("toggled", self.partman_column_format_toggled,
                                partition_tree_model)
            self.partition_list_treeview.append_column(column_format)

            cell_size = gtk.CellRendererText()
            column_size = gtk.TreeViewColumn("Size", cell_size)
            column_size.set_cell_data_func(cell_size, self.partman_column_size)
            column_size.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.partition_list_treeview.append_column(column_size)

            cell_used = gtk.CellRendererText()
            column_used = gtk.TreeViewColumn("Used", cell_used)
            column_used.set_cell_data_func(cell_used, self.partman_column_used)
            column_used.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.partition_list_treeview.append_column(column_used)

            self.partition_list_treeview.set_model(partition_tree_model)

            selection = self.partition_list_treeview.get_selection()
            selection.connect(
                'changed', self.on_partition_list_treeview_selection_changed)
        else:
            # TODO cjwatson 2006-08-31: inefficient, but will do for now
            partition_tree_model.clear()
            for item in cache_order:
                if item in disk_cache:
                    partition_tree_model.append([item, disk_cache[item]])
                else:
                    partition_tree_model.append([item, partition_cache[item]])

        # make sure we're on the advanced partitioning page
        self.set_current_page(self.steps.page_num(self.stepPartAdvanced))


    def ma_info_loop(self, widget):
        """migration-assistant version of info_loop. For now it just autofills
        the username.  Callback defined in glade file."""
        edited = False
        m, i = self.matreeview.get_selection().get_selected()
        if not m.iter_children(i):
            i = m.iter_parent(i)
        for k in m.get_value(i, 1).iterkeys():
            val = m.get_value(i, 1)[k]
            if k == 'newuser' and val != '' and self.ma_loginname.child.get_text() != '':
                edited = True

        if (widget is not None and widget.get_name() == 'ma_fullname' and
            not edited):
            new_username = widget.get_text().split(' ')[0]
            new_username = new_username.encode('ascii', 'ascii_transliterate')
            new_username = new_username.lower()
            self.ma_loginname.child.set_text(new_username)

    def ma_configure_usersetup(self):

        def selection_changed(sender):
            if sender.get_active() >= 0:
                user = self.ma_new_users[sender.child.get_text()]
                self.fullname.set_text(user['fullname'])
                self.password.set_text(user['password'])
                self.verified_password.set_text(user['confirm'])

        def focus_out(sender, event):
            user = self.username.get_text()
            if user in self.ma_new_users.keys():
                u = self.ma_new_users[user]
                self.fullname.set_text(u['fullname'])
                self.password.set_text(u['password'])
                self.verified_password.set_text(u['confirm'])
                # This prevents auto filling based on the full name from
                # clobbering m-a usernames.
                self.username_edited = True

        # If the user pressed back.
        if self.username_combo:
            return

        # Reconfigure username as a combobox without having to modify
        # existing code.
        self.username.destroy()
        self.username_combo = gtk.combo_box_entry_new_text()
        model = self.username_combo.get_model()
        for k in self.ma_new_users.iterkeys():
            if k != '-':
                model.append([k])

        self.username = self.username_combo.child
        self.username.set_width_chars(20)
        self.username.set_name('username')
        self.username_combo.connect('changed', selection_changed)
        self.username.connect('changed', self.info_loop)
        self.username.connect('focus-out-event', focus_out)
        self.username_changed_id = self.username.connect(
            'changed', self.on_username_changed)
        self.username_hbox.pack_start(self.username_combo, False, False, 0)
        self.username_hbox.reorder_child(self.username_combo, 0)
        self.username_combo.show_all()

    def ma_user_error(self, error, user):
        # Note that 'user' is the original user.
        model = self.matreeview.get_model()
        iterator = model.get_iter(0)
        while iterator:
            val = model.get_value(iterator, 1)
            if user == val['user']:
                newuser = val['newuser']
                self.ma_new_users[newuser]['loginname-error'] = error

                # selection_changed only gets emitted if the selection actually
                # changes.  So we only change the selection if we need to,
                # otherwise we just call update_selection directly.
                selection = self.matreeview.get_selection()
                if selection.iter_is_selected(iterator):
                    self.ma_update_selection()
                else:
                    selection.select_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    def ma_password_error(self, error, user):
        # Note that 'user' is the user we're importing to.
        model = self.matreeview.get_model()
        iterator = model.get_iter(0)
        while iterator:
            val = model.get_value(iterator, 1)
            if user == val['newuser']:
                self.ma_new_users[user]['password-error'] = error

                selection = self.matreeview.get_selection()
                if selection.iter_is_selected(iterator):
                    self.ma_update_selection()
                else:
                    selection.select_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    def ma_get_choices(self):
        return (self.ma_choices, self.ma_new_users)

    def ma_cb_toggle(self, cell, path, model=None):
        iterator = model.get_iter(path)
        checked = not cell.get_active()
        model.set_value(iterator, 0, checked)

        # We're on a user checkbox.
        if model.iter_children(iterator):
            if checked:
                self.ma_userinfo.set_sensitive(True)
            else:
                self.ma_userinfo.set_sensitive(False)

            if not cell.get_active():
                model.get_value(iterator, 1)['selected'] = True
            else:
                model.get_value(iterator, 1)['selected'] = False
            parent = iterator
            iterator = model.iter_children(iterator)
            items = []
            while iterator:
                model.set_value(iterator, 0, checked)
                if checked:
                    items.append(model.get_value(iterator, 1))
                iterator = model.iter_next(iterator)
            model.get_value(parent, 1)['items'] = items

        # We're on an item checkbox.
        else:
            parent = model.iter_parent(iterator)
            if not model.get_value(parent, 0):
                model.set_value(parent, 0, True)
                model.get_value(parent, 1)['selected'] = True

            item = model.get_value(iterator, 1)
            items = model.get_value(parent, 1)['items']
            if checked:
                items.append(item)
            else:
                items.remove(item)

    def ma_seed_userinfo(self):
        sel = self.ma_previous_selection
        if not sel:
            return

        m = sel[0]
        i = sel[1]
        if not m.iter_children(i):
            i = m.iter_parent(i)
        newuser = self.ma_loginname.child.get_text()
        if m.get_value(i, 0):
            if not newuser:
                # Use - as a key for a null username.
                newuser = '-'
            try:
                val = self.ma_new_users[newuser]
            except KeyError:
                self.ma_new_users[newuser] = {}
                val = self.ma_new_users[newuser]
                val['loginname-error'] = ''
                val['password-error'] = ''

            m.get_value(i, 1)['newuser'] = newuser

            # Clear out any unused new users.
            keys = self.ma_new_users.keys()
            for k in keys:
                it = m.get_iter(0)
                found = False
                while it:
                    u = m.get_value(it, 1)['newuser']
                    if k == u:
                        found = True
                        break
                    it = m.iter_next(it)
                if not found:
                    self.ma_new_users.pop(k)

            self.ma_loginname.set_model(gtk.ListStore(str))
            for u in self.ma_new_users.iterkeys():
                if u and u != '-':
                    self.ma_loginname.append_text(u)
            val['fullname'] = self.ma_fullname.get_text()
            val['password'] = self.ma_password.get_text()
            val['confirm'] = self.ma_confirm.get_text()
            # We don't have to clear the username error because changing the
            # username creates a new user.
            if val['password'] and (val['password'] == val['confirm']):
                val['password-error'] = ''
            else:
                val['password-error'] = self.ma_password_error_reason.get_text()

    def ma_update_selection(self):
        model, iterator = self.matreeview.get_selection().get_selected()
        if not model.iter_children(iterator):
            iterator = model.iter_parent(iterator)

        self.ma_loginname_error_box.hide()
        self.ma_password_error_box.hide()

        newuser = model.get_value(iterator, 1)['newuser']
        try:
            val = self.ma_new_users[newuser]
            if newuser == '-':
                self.ma_loginname.child.set_text('')
            else:
                self.ma_loginname.child.set_text(newuser)

            self.ma_fullname.set_text(val['fullname'])
            self.ma_password.set_text(val['password'])
            self.ma_confirm.set_text(val['confirm'])

            error = val['loginname-error']
            if error:
                self.ma_loginname_error_reason.set_text(error)
                self.ma_loginname_error_box.show()
            error = val['password-error']
            if error:
                self.ma_password_error_reason.set_text(error)
                self.ma_password_error_box.show()

        except KeyError:
            self.ma_fullname.set_text('')
            self.ma_loginname.child.set_text('')
            self.ma_password.set_text('')
            self.ma_confirm.set_text('')

    def ma_selection_changed(self, selection):
        if self.ma_previous_selection:
            self.ma_seed_userinfo()

        model, iterator = selection.get_selected()
        if not iterator:
            return
        if model.iter_parent(iterator):
            iterator = model.iter_parent(iterator)

        if model.get_value(iterator, 0):
            self.ma_userinfo.set_sensitive(True)
        else:
            self.ma_userinfo.set_sensitive(False)

        self.ma_previous_selection = selection.get_selected()
        self.ma_update_selection()

    def ma_combo_changed(self, sender):
        if sender.get_active() >= 0:
            user = self.ma_loginname.child.get_text()
            val = self.ma_new_users[user]
            self.ma_fullname.set_text(val['fullname'])
            self.ma_password.set_text(val['password'])
            self.ma_confirm.set_text(val['confirm'])


    def ma_set_choices(self, choices):

        def cell_data_func(column, cell, model, iterator):
            val = model.get_value(iterator, 1)
            if model.iter_children(iterator):
                # Windows XP...
                text = '%s  <small><i>%s (%s)</i></small>' % \
                       (val['user'], val['os'], val['part'])
                newuser = val['newuser']
                if newuser and model.get_value(iterator, 0):
                    newuser = self.ma_new_users[newuser]
                    if newuser['password-error'] or newuser['loginname-error']:
                        text = '<span foreground="red">%s  <small><i>%s' \
                               ' (%s)</i></small></span>' % \
                               (val['user'], val['os'], val['part'])
            else:
                # Gaim, Yahoo, etc
                text = model.get_value(iterator, 1)

            cell.set_property("markup", text)
        # The user probably hit the back button.
        if self.matreeview.get_model():
            return

        self.ma_choices = choices
        # For the new users.
        self.ma_new_users = {}
        # For the previous selected item.
        self.ma_previous_selection = None

        # TODO evand 2007-01-11 I'm on the fence as to whether or not skipping
        # the page would be better than showing the user this error.
        if not choices:
            msg = 'There were no users or operating systems suitable for ' \
                  'importing from.'
            liststore = gtk.ListStore(str)
            liststore.append([msg])
            self.matreeview.set_model(liststore)
            column = gtk.TreeViewColumn('item', gtk.CellRendererText(), text=0)
            self.matreeview.append_column(column)
            self.matreeview.show_all()
        else:
            treestore = gtk.TreeStore(bool, object)
            for choice in choices:
                piter = treestore.append(None, [False, choice])
                for item in choice['items']:
                    treestore.append(piter, [False, item])
                choice['items'] = []

            self.matreeview.set_model(treestore)

            renderer = gtk.CellRendererToggle()
            renderer.connect('toggled', self.ma_cb_toggle, treestore)
            column = gtk.TreeViewColumn('boolean', renderer, active=0)
            column.set_clickable(True)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.matreeview.append_column(column)

            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn('item', renderer)
            column.set_cell_data_func(renderer, cell_data_func)
            self.matreeview.append_column(column)

            self.matreeview.set_search_column(1)

            self.matreeview.get_selection().connect('changed',
                                                    self.ma_selection_changed)
            self.matreeview.show_all()

            self.ma_loginname.set_model(gtk.ListStore(str))
            self.ma_loginname.set_text_column(0)
            self.ma_loginname.connect('changed', self.ma_combo_changed)


    def set_fullname(self, value):
        self.fullname.set_text(value)

    def get_fullname(self):
        return self.fullname.get_text()

    def set_username(self, value):
        self.username.set_text(value)

    def get_username(self):
        return self.username.get_text()

    def get_password(self):
        return self.password.get_text()

    def get_verified_password(self):
        return self.verified_password.get_text()

    def username_error(self, msg):
        self.username_error_reason.set_text(msg)
        self.username_error_box.show()

    def password_error(self, msg):
        self.password_error_reason.set_text(msg)
        self.password_error_box.show()

    def get_hostname (self):
        return self.hostname.get_text()


    def set_summary_text (self, text):
        for child in self.ready_text.get_children():
            self.ready_text.remove(child)

        ready_buffer = gtk.TextBuffer()
        ready_buffer.set_text(text)
        self.ready_text.set_buffer(ready_buffer)

    def on_advanced_button_clicked (self, button):
        display = False
        summary_device = self.get_summary_device()
        if summary_device is not None:
            display = True
            self.bootloader_vbox.show()
            self.grub_device_entry.set_text(summary_device)
        else:
            self.bootloader_vbox.hide()
        if self.popcon is not None:
            display = True
            self.popcon_vbox.show()
            self.popcon_checkbutton.set_active(self.popcon)
        else:
            self.popcon_vbox.hide()
        if not display:
            return

        response = self.advanced_dialog.run()
        self.advanced_dialog.hide()
        if response == gtk.RESPONSE_OK:
            self.set_summary_device(self.grub_device_entry.get_text())
            self.set_popcon(self.popcon_checkbutton.get_active())
        return True


    def return_to_partitioning (self):
        """If the install progress bar is up but still at the partitioning
        stage, then errors can safely return us to partitioning.
        """

        if self.installing and not self.installing_no_return:
            # Go back to the partitioner and try again.
            self.live_installer.show()
            self.set_current_page(self.previous_partitioning_page)
            self.next.set_label("gtk-go-forward")
            self.translate_widget(self.next, self.locale)
            self.backup = True
            self.installing = False

    def error_dialog (self, title, msg, fatal=True):
        # TODO: cancel button as well if capb backup
        self.allow_change_step(True)
        if self.current_page is not None:
            transient = self.live_installer
        else:
            transient = self.debconf_progress_window
        if not msg:
            msg = title
        dialog = gtk.MessageDialog(transient, gtk.DIALOG_MODAL,
                                   gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        dialog.set_title(title)
        dialog.run()
        dialog.hide()
        if fatal:
            self.return_to_partitioning()

    def question_dialog (self, title, msg, options, use_templates=True):
        self.allow_change_step(True)
        if self.current_page is not None:
            transient = self.live_installer
        else:
            transient = self.debconf_progress_window
        if not msg:
            msg = title
        buttons = []
        for option in options:
            if use_templates:
                text = self.get_string(option)
            else:
                text = option
            if text is None:
                text = option
            # Work around PyGTK bug; each button text must actually be a
            # subtype of str, which unicode isn't.
            text = str(text)
            buttons.extend((text, len(buttons) / 2 + 1))
        dialog = gtk.Dialog(title, transient, gtk.DIALOG_MODAL, tuple(buttons))
        vbox = gtk.VBox()
        vbox.set_border_width(5)
        label = gtk.Label(msg)
        label.set_line_wrap(True)
        label.set_selectable(True)
        vbox.pack_start(label)
        vbox.show_all()
        dialog.vbox.pack_start(vbox)
        response = dialog.run()
        dialog.hide()
        if response < 0:
            # something other than a button press, probably destroyed
            return None
        else:
            return options[response - 1]


    def refresh (self):
        while gtk.events_pending():
            gtk.main_iteration()


    # Run the UI's main loop until it returns control to us.
    def run_main_loop (self):
        self.allow_change_step(True)
        gtk.main()


    # Return control to the next level up.
    def quit_main_loop (self):
        if gtk.main_level() > 0:
            gtk.main_quit()


# Much of this timezone map widget is a rough translation of
# gnome-system-tools/src/time/tz-map.c. Thanks to Hans Petter Jansson
# <hpj@ximian.com> for that.

NORMAL_RGBA = 0xc070a0ffL
HOVER_RGBA = 0xffff60ffL
SELECTED_1_RGBA = 0xff60e0ffL
SELECTED_2_RGBA = 0x000000ffL

class TimezoneMap(object):
    def __init__(self, frontend):
        self.frontend = frontend
        self.tzdb = ubiquity.tz.Database()
        self.tzmap = ubiquity.emap.EMap()
        self.update_timeout = None
        self.point_selected = None
        self.point_hover = None
        self.location_selected = None

        self.tzmap.set_smooth_zoom(False)
        zoom_in_file = os.path.join(PATH, 'pixmaps', 'zoom-in.png')
        if os.path.exists(zoom_in_file):
            display = self.frontend.live_installer.get_display()
            pixbuf = gtk.gdk.pixbuf_new_from_file(zoom_in_file)
            self.cursor_zoom_in = gtk.gdk.Cursor(display, pixbuf, 10, 10)
        else:
            self.cursor_zoom_in = None

        self.tzmap.add_events(gtk.gdk.LEAVE_NOTIFY_MASK |
                              gtk.gdk.VISIBILITY_NOTIFY_MASK)

        self.frontend.timezone_map_window.add(self.tzmap)

        timezone_city_combo = self.frontend.timezone_city_combo

        renderer = gtk.CellRendererText()
        timezone_city_combo.pack_start(renderer, True)
        timezone_city_combo.add_attribute(renderer, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        timezone_city_combo.set_model(list_store)

        prev_continent = ''
        for location in self.tzdb.locations:
            self.tzmap.add_point("", location.longitude, location.latitude,
                                 NORMAL_RGBA)
            zone_bits = location.zone.split('/')
            if len(zone_bits) == 1:
                continue
            continent = zone_bits[0]
            if continent != prev_continent:
                list_store.append(['', None])
                list_store.append(["--- %s ---" % continent, None])
                prev_continent = continent
            human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
            list_store.append([human_zone, location.zone])

        self.tzmap.connect("map-event", self.mapped)
        self.tzmap.connect("unmap-event", self.unmapped)
        self.tzmap.connect("motion-notify-event", self.motion)
        self.tzmap.connect("button-press-event", self.button_pressed)
        self.tzmap.connect("leave-notify-event", self.out_map)

        timezone_city_combo.connect("changed", self.city_changed)

    def set_city_text(self, name):
        model = self.frontend.timezone_city_combo.get_model()
        iterator = model.get_iter_first()
        while iterator is not None:
            location = model.get_value(iterator, 1)
            if location == name:
                self.frontend.timezone_city_combo.set_active_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    def set_zone_text(self, location):
        offset = location.utc_offset
        if offset >= datetime.timedelta(0):
            minuteoffset = int(offset.seconds / 60)
        else:
            minuteoffset = int(offset.seconds / 60 - 1440)
        if location.zone_letters == 'GMT':
            text = location.zone_letters
        else:
            text = "%s (GMT%+d:%02d)" % (location.zone_letters,
                                         minuteoffset / 60, minuteoffset % 60)
        self.frontend.timezone_zone_text.set_text(text)
        translations = gettext.translation('iso_3166',
                                           languages=[self.frontend.locale],
                                           fallback=True)
        self.frontend.timezone_country_text.set_text(
            translations.ugettext(location.human_country))
        self.update_current_time()

    def update_current_time(self):
        if self.location_selected is not None:
            try:
                now = datetime.datetime.now(self.location_selected.info)
                self.frontend.timezone_time_text.set_text(now.strftime('%X'))
            except ValueError:
                # Some versions of Python have problems with clocks set
                # before the epoch (http://python.org/sf/1646728).
                self.frontend.timezone_time_text.set_text('<clock error>')

    def set_tz_from_name(self, name):
        (longitude, latitude) = (0.0, 0.0)

        for location in self.tzdb.locations:
            if location.zone == name:
                (longitude, latitude) = (location.longitude, location.latitude)
                break
        else:
            return

        if self.point_selected is not None:
            self.tzmap.point_set_color_rgba(self.point_selected, NORMAL_RGBA)

        self.point_selected = self.tzmap.get_closest_point(longitude, latitude,
                                                           False)

        self.location_selected = location
        self.set_city_text(self.location_selected.zone)
        self.set_zone_text(self.location_selected)
        self.frontend.allow_go_forward(True)

    def city_changed(self, widget):
        iterator = widget.get_active_iter()
        if iterator is not None:
            model = widget.get_model()
            location = model.get_value(iterator, 1)
            if location is not None:
                self.set_tz_from_name(location)

    def get_selected_tz_name(self):
        if self.location_selected is not None:
            return self.location_selected.zone
        else:
            return None

    def location_from_point(self, point):
        if point is None:
            return None

        (longitude, latitude) = point.get_location()

        best_location = None
        best_distance = None
        for location in self.tzdb.locations:
            if (abs(location.longitude - longitude) <= 1.0 and
                abs(location.latitude - latitude) <= 1.0):
                distance = ((location.longitude - longitude) ** 2 +
                            (location.latitude - latitude) ** 2) ** 0.5
                if best_distance is None or distance < best_distance:
                    best_location = location
                    best_distance = distance

        return best_location

    def timeout(self):
        self.update_current_time()

        if self.point_selected is None:
            return True

        if self.point_selected.get_color_rgba() == SELECTED_1_RGBA:
            self.tzmap.point_set_color_rgba(self.point_selected,
                                            SELECTED_2_RGBA)
        else:
            self.tzmap.point_set_color_rgba(self.point_selected,
                                            SELECTED_1_RGBA)

        return True

    def mapped(self, widget, event):
        if self.update_timeout is None:
            self.update_timeout = gobject.timeout_add(100, self.timeout)

    def unmapped(self, widget, event):
        if self.update_timeout is not None:
            gobject.source_remove(self.update_timeout)
            self.update_timeout = None

    def motion(self, widget, event):
        if self.tzmap.get_magnification() <= 1.0:
            if self.cursor_zoom_in is not None:
                self.frontend.live_installer.window.set_cursor(
                    self.cursor_zoom_in)
        else:
            self.frontend.live_installer.window.set_cursor(None)

            (longitude, latitude) = self.tzmap.window_to_world(event.x,
                                                               event.y)

            if (self.point_hover is not None and
                self.point_hover != self.point_selected):
                self.tzmap.point_set_color_rgba(self.point_hover, NORMAL_RGBA)

            self.point_hover = self.tzmap.get_closest_point(longitude,
                                                            latitude, True)

            if self.point_hover != self.point_selected:
                self.tzmap.point_set_color_rgba(self.point_hover, HOVER_RGBA)

        return True

    def out_map(self, widget, event):
        if event.mode != gtk.gdk.CROSSING_NORMAL:
            return False

        if (self.point_hover is not None and
            self.point_hover != self.point_selected):
            self.tzmap.point_set_color_rgba(self.point_hover, NORMAL_RGBA)

        self.point_hover = None

        self.frontend.live_installer.window.set_cursor(None)

        return True

    def button_pressed(self, widget, event):
        (longitude, latitude) = self.tzmap.window_to_world(event.x, event.y)

        if event.button != 1:
            self.tzmap.zoom_out()
            if self.cursor_zoom_in is not None:
                self.frontend.live_installer.window.set_cursor(
                    self.cursor_zoom_in)
        elif self.tzmap.get_magnification() <= 1.0:
            self.tzmap.zoom_to_location(longitude, latitude)
            if self.cursor_zoom_in is not None:
                self.frontend.live_installer.window.set_cursor(None)
        else:
            if self.point_selected is not None:
                self.tzmap.point_set_color_rgba(self.point_selected,
                                                NORMAL_RGBA)
            self.point_selected = self.point_hover

            new_location_selected = \
                self.location_from_point(self.point_selected)
            if new_location_selected is not None:
                old_city = self.get_selected_tz_name()
                if old_city is None or old_city != new_location_selected.zone:
                    self.set_city_text(new_location_selected.zone)
                    self.set_zone_text(new_location_selected)
            self.location_selected = new_location_selected
            self.frontend.allow_go_forward(self.location_selected is not None)

        return True

# vim:ai:et:sts=4:tw=80:sw=4:
