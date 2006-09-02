import sys
from qt import *
from kdeui import *
from kdecore import *

from debconf import DebconfCommunicator
from oem_config import filteredcommand
from oem_config.components import language, keyboard, timezone, user

#Import the UI Dialog
from sysconf import OEMConfKDEUI

BREADCRUMB_STEPS = {
    "step_language": 1,
    "step_keyboard": 2,
    "step_timezone": 3,
    "step_user": 4
}
BREADCRUMB_MAX_STEP = 4

WIDGET_STACK_STEPS = {
    "step_language": 0,
    "step_keyboard": 1,
    "step_timezone": 2,
    "step_user": 3
}
WIDGET_STACK_MAX_STEPS = 3

class OEMConfUI(OEMConfKDEUI):
	
	def setFrontend(self,fe):
		self.frontend = fe


class Frontend:
    def __init__(self):
	
	
	about=KAboutData("kubuntu-oem-config","OEM Installer","1.0","OEM Installer for Kubuntu",KAboutData.License_GPL,"(c) 2006 Canonical Ltd", "http://wiki.kubuntu.org/KubuntuUbiquity", "the.abattoir@gmail.com")
        about.addAuthor("Anirudh Ramesh", None,"the.abattoir@gmail.com")
        KCmdLineArgs.init(["./installer"],about)
	
	self.app=KApplication()
	
	#Create an instance of the sysconf widget and run it.
	self.userinterface = OEMConfUI(None, "OEM-Config")
        self.userinterface.setFrontend(self)
        self.app.setMainWidget(self.userinterface)
        self.userinterface.show()
	
	self.debconf_callbacks = {}    # array to keep callback functions needed by debconf file descriptors
	
	#lists needed to set default values through set_language(), set_country(), set_keyboard() and set_timezone()
	self.lang_list = []
	self.loc_list = []
	self.key_list = []
	self.tz_list = []
	
	# To get a "busy mouse":
        self.userinterface.setCursor(QCursor(Qt.WaitCursor))
	
	self.locale = None
	self.current_step = None
	# Set default language.
        self.dbfilter = language.Language(self, DebconfCommunicator('oem-config',cloexec=True))
        self.dbfilter.cleanup()
        self.dbfilter.db.shutdown()

    def run(self):
	    global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP, WIDGET_STACK_STEPS, WIDGET_STACK_MAX_STEPS
	    
	    self.userinterface.setCursor(QCursor(Qt.ArrowCursor))
	    
	    #Signals and Slots
	    self.app.connect(self.userinterface.button_forward, SIGNAL("clicked()"), self.on_forward_clicked)
	    self.app.connect(self.userinterface.button_back, SIGNAL("clicked()"), self.on_back_clicked)
	    
	    first_step = "step_language"
	    self.userinterface.widgetStack.raiseWidget(self.userinterface.step_language)
	    self.userinterface.widgetStack.visibleWidget()
	    self.current_step = self.get_current_step()
	    self.set_current_page()
	    #Disable "Back" button for the first step
	    self.userinterface.button_back.setEnabled(0)
	    
	    while self.current_step is not None:
		    self.backup = False
		    self.current_step = self.get_current_step()
		    print self.current_step
		    if self.current_step == 'step_language':
			    self.dbfiler = language.Language(self)
	            elif self.current_step == 'step_keyboard':
			    self.dbfilter = keyboard.Keyboard(self)
		    elif self.current_step == 'step_timezone':
			    self.dbfilter = timezone.Timezone(self)
	            elif self.current_step == 'step_user':
			    self.dbfilter = user.User(self)
		    else:
			    raise ValueError, "step %s not recognised" % self.current_step
		    
		    self.dbfilter.start(auto_process=True)
	            self.app.exec_loop()
		    #self.app.processEvents(1)
		    curr = self.get_current_step()
		    if self.backup:
			    pass
		    elif self.current_step == 'step_user':
			self.userinterface.hide()
			self.current_step = None
	            elif WIDGET_STACK_STEPS[curr] < WIDGET_STACK_MAX_STEPS :
                        self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS[curr]+1)
                        self.set_current_page()
			if (WIDGET_STACK_STEPS[curr]+1) == WIDGET_STACK_MAX_STEPS:
				self.userinterface.button_forward.setText("&Finish!") #check tr
				
    def get_current_step(self):
	    return self.userinterface.widgetStack.visibleWidget().name()
    
    def set_language_choices(self,choices,choice_map):
	    self.language_choice_map = dict(choice_map)
	    self.userinterface.language_combo.clear()
	    for choice in choices:
		    self.lang_list.append(choice)
		    self.userinterface.language_combo.insertItem(choice)
	    
    def set_language(self, language):
	    index = 0
	    while index < len(self.lang_list):
		    if unicode(self.lang_list[index]) == language:
			    self.userinterface.language_combo.setCurrentItem(index)
			    break
	            index = index + 1
    
    def set_country_choices(self, choice_map):
	    print "Set country choices entered"
	    self.country_choice_map = dict(choice_map)
	    choices = choice_map.keys()
	    choices.sort()
	    self.userinterface.location_combo.clear()
	    for choice in choices:
		    self.loc_list.append(choice)
		    self.userinterface.location_combo.insertItem(choice)

    def set_country(self, country):
	    print "Set country entered"
	    print country
	    index = 0
	    while index < len(self.loc_list):
		    if unicode(self.country_choice_map[self.loc_list[index]]) == country:
			    self.userinterface.location_combo.setCurrentItem(index)
			    print country
			    break
                    index = index + 1

    def get_language(self):
	    return unicode(self.userinterface.language_combo.currentText())
	    pass
	
    def on_language_combo_changed(self, widget):
        if isinstance(self.dbfilter, language.Language):
            self.dbfilter.language_changed()
	
    def get_country(self):
	    return unicode(self.userinterface.location_combo.currentText())
	    pass
    
    def set_keyboard_choices(self, choice_map):
	    self.keyboard_choice_map = dict(choice_map)
	    choices=choice_map.keys()
	    choices.sort()
	    self.userinterface.keyboard_combo.clear()
	    for choice in choices:
		    self.key_list.append(choice)
		    self.userinterface.keyboard_combo.insertItem(choice)
    
    def set_keyboard(self,keyboard):
	    index = 0
	    while index < len(self.key_list):
		    if unicode(self.key_list[index]) == keyboard:
			    self.userinterface.keyboard_combo.setCurrentItem(index)
			    break
                    index = index +1

    def get_keyboard(self):
	    return unicode(self.userinterface.keyboard_combo.currentText())
	    pass
    
    def set_timezone_choices(self, choice_map):
	    self.timezone_choice_map = dict(choice_map)
	    choices = choice_map.keys()
	    choices.sort()
	    for choice in choices:
		    self.tz_list.append(choice)
		    self.userinterface.timezone_combo.insertItem(choice)
    
    def set_timezone(self, timezone):
	    index = 0
	    while index < len(self.tz_list):
		    if unicode(self.tz_list[index]) == keyboard:
			    self.userinterface.timezone_combo.setCurrentItem(index)
			    break
		    index = index + 1 
    
    def get_timezone(self):
	    return unicode(self.userinterface.timezone_combo.currentText())
    
    def set_fullname(self, value):
        self.userinterface.user_fullname_lineedit.setText(value)

    def get_fullname(self):
        return unicode(self.userinterface.user_fullname_lineedit.text())

    def set_username(self, value):
        self.userinterface.user_username_lineedit.setText(value)

    def get_username(self):
        return unicode(self.userinterface.user_username_lineedit.text())

    def get_password(self):
        return unicode(self.userinterface.user_pass_lineedit.text())

    def get_verified_password(self):
        return unicode(self.userinterface.user_pass_lineedit.text())
    
    def watch_debconf_fd (self, from_debconf, process_input):
	self.debconf_fd_counter = 0
        self.socketNotifierRead = QSocketNotifier(from_debconf, QSocketNotifier.Read, self.app, "read-for-" + str(from_debconf))
        self.app.connect(self.socketNotifierRead, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_read)
        
        self.socketNotifierWrite = QSocketNotifier(from_debconf, QSocketNotifier.Write, self.app, "read-for-" + str(from_debconf))
        self.app.connect(self.socketNotifierWrite, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_write)

        self.socketNotifierException = QSocketNotifier(from_debconf, QSocketNotifier.Exception, self.app, "read-for-" + str(from_debconf))
        self.app.connect(self.socketNotifierException, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_exception)
        
        self.debconf_callbacks[from_debconf] = process_input
        self.current_debconf_fd = from_debconf

    def watch_debconf_fd_helper_read (self, source):
        self.debconf_fd_counter += 1
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_IN
        self.debconf_callbacks[source](source, debconf_condition)

    def watch_debconf_fd_helper_write(self, source):
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_OUT
        self.debconf_callbacks[source](source, debconf_condition)

    def watch_debconf_fd_helper_exception(self, source):
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        self.debconf_callbacks[source](source, debconf_condition)
    
    #def watch_debconf_fd_helper (self, source, cb_condition, callback):
	    #pass
    
    def debconffilter_done (self, dbfilter):
	if dbfilter == self.dbfilter:
            self.dbfilter = None
            self.app.exit()
    
    def on_forward_clicked(self):
	    global WIDGET_STACK_MAX_STEPS, WIDGET_STACK_STEPS
	    self.userinterface.setCursor(QCursor(Qt.WaitCursor))
	    curr = self.get_current_step()
	    if WIDGET_STACK_STEPS[curr] == 0:
		    self.userinterface.button_back.setEnabled(1)
	    #if WIDGET_STACK_STEPS[curr] < WIDGET_STACK_MAX_STEPS :
		    #self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS[curr]+1)
		    #if (WIDGET_STACK_STEPS[curr]+1) == WIDGET_STACK_MAX_STEPS:
			    #self.userinterface.button_forward.setText("&Finish!") #check tr
	    self.set_current_page()
	    if self.dbfilter is not None:
		    self.dbfilter.ok_handler()
	    else:
		    self.app.exit()
	    
    
    def on_back_clicked(self):
	    global WIDGET_STACK_STEPS, WIDGET_STACK_MAX_STEPS
	    self.backup = True
	    curr = self.get_current_step()
	    if self.userinterface.button_forward.text() == "&Finish!":
		    self.userinterface.button_forward.setText("&Forward")#check tr
	    if WIDGET_STACK_STEPS[curr] == 1:
		    self.userinterface.button_back.setEnabled(0)
	    if WIDGET_STACK_STEPS[curr] > 0 :
		    self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS[curr]-1)
	    self.set_current_page()
	    if self.dbfilter is not None:
		    self.dbfilter.cancel_handler()
    def run_main_loop (self):
	    self.userinterface.setCursor(QCursor(Qt.ArrowCursor))
	    self.app.exec_loop()
	
    def quit_main_loop (self):
	    self.app.exit()
	
    def redo_step(self):
	    self.backup = True
    
    def set_current_page(self):
	    global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
	    #self.current_page = current
	    current_name = self.get_current_step()
	    label_text = "Step ${INDEX} of ${TOTAL}"
	    curstep = "<i>?</i>"
	    if current_name in BREADCRUMB_STEPS:
		    curstep = str(BREADCRUMB_STEPS[current_name])
	    label_text = label_text.replace("${INDEX}", curstep)
	    label_text = label_text.replace("${TOTAL}", str(BREADCRUMB_MAX_STEP))
	    self.userinterface.step_label.setText(label_text)