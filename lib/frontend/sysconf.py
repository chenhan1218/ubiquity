# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'sysconf.ui'
#
# Created: Fri Aug 18 10:35:15 2006
#      by: The PyQt User Interface Compiler (pyuic) 3.16
#
# WARNING! All changes made in this file will be lost!


import sys
from qt import *
from kdecore import KCmdLineArgs, KApplication
from kdeui import *



class OEMConfKDEUI(QDialog):
    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        QDialog.__init__(self,parent,name,modal,fl)

        if not name:
            self.setName("OEMConfKDEUI")


        OEMConfKDEUILayout = QVBoxLayout(self,11,6,"OEMConfKDEUILayout")

        self.widgetStack = QWidgetStack(self,"widgetStack")

        self.step_language = QWidget(self.widgetStack,"step_language")
        step_languageLayout = QGridLayout(self.step_language,1,1,11,6,"step_languageLayout")

        self.line1 = QFrame(self.step_language,"line1")
        self.line1.setFrameShape(QFrame.HLine)
        self.line1.setFrameShadow(QFrame.Sunken)
        self.line1.setFrameShape(QFrame.HLine)

        step_languageLayout.addMultiCellWidget(self.line1,1,1,0,1)

        self.line2 = QFrame(self.step_language,"line2")
        self.line2.setFrameShape(QFrame.HLine)
        self.line2.setFrameShadow(QFrame.Sunken)
        self.line2.setFrameShape(QFrame.HLine)

        step_languageLayout.addMultiCellWidget(self.line2,3,3,0,1)

        self.titleLabel_language = QLabel(self.step_language,"titleLabel_language")

        step_languageLayout.addWidget(self.titleLabel_language,0,0)

        layout4 = QGridLayout(None,1,1,0,6,"layout4")

        self.location_combo = QComboBox(0,self.step_language,"location_combo")
        self.location_combo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed,0,0,self.location_combo.sizePolicy().hasHeightForWidth()))

        layout4.addWidget(self.location_combo,1,1)
        spacer3 = QSpacerItem(20,20,QSizePolicy.Minimum,QSizePolicy.Expanding)
        layout4.addItem(spacer3,2,1)
        spacer2 = QSpacerItem(131,111,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout4.addMultiCell(spacer2,0,1,2,2)

        self.location_label = QLabel(self.step_language,"location_label")

        layout4.addWidget(self.location_label,1,0)

        self.language_combo = QComboBox(0,self.step_language,"language_combo")
        self.language_combo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed,0,0,self.language_combo.sizePolicy().hasHeightForWidth()))
        self.language_combo.setInsertionPolicy(QComboBox.AtBottom)

        layout4.addWidget(self.language_combo,0,1)

        self.language_label = QLabel(self.step_language,"language_label")
        self.language_label.setMouseTracking(0)

        layout4.addWidget(self.language_label,0,0)

        step_languageLayout.addLayout(layout4,2,0)
        self.widgetStack.addWidget(self.step_language,0)

        self.step_keyboard = QWidget(self.widgetStack,"step_keyboard")
        step_keyboardLayout = QGridLayout(self.step_keyboard,1,1,11,6,"step_keyboardLayout")

        self.line1_2 = QFrame(self.step_keyboard,"line1_2")
        self.line1_2.setFrameShape(QFrame.HLine)
        self.line1_2.setFrameShadow(QFrame.Sunken)
        self.line1_2.setFrameShape(QFrame.HLine)

        step_keyboardLayout.addMultiCellWidget(self.line1_2,1,1,0,2)

        self.line2_2 = QFrame(self.step_keyboard,"line2_2")
        self.line2_2.setFrameShape(QFrame.HLine)
        self.line2_2.setFrameShadow(QFrame.Sunken)
        self.line2_2.setFrameShape(QFrame.HLine)

        step_keyboardLayout.addMultiCellWidget(self.line2_2,5,5,0,2)
        spacer7 = QSpacerItem(111,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        step_keyboardLayout.addItem(spacer7,3,2)

        self.titleLabel_keyboard = QLabel(self.step_keyboard,"titleLabel_keyboard")

        step_keyboardLayout.addMultiCellWidget(self.titleLabel_keyboard,0,0,0,2)
        spacer5 = QSpacerItem(21,30,QSizePolicy.Minimum,QSizePolicy.Expanding)
        step_keyboardLayout.addItem(spacer5,2,1)

        self.keyboard_label = QLabel(self.step_keyboard,"keyboard_label")

        step_keyboardLayout.addWidget(self.keyboard_label,3,0)

        self.keyboard_combo = QComboBox(0,self.step_keyboard,"keyboard_combo")
        self.keyboard_combo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed,0,0,self.keyboard_combo.sizePolicy().hasHeightForWidth()))

        step_keyboardLayout.addWidget(self.keyboard_combo,3,1)
        spacer6 = QSpacerItem(20,30,QSizePolicy.Minimum,QSizePolicy.Expanding)
        step_keyboardLayout.addItem(spacer6,4,1)
        self.widgetStack.addWidget(self.step_keyboard,1)

        self.step_timezone = QWidget(self.widgetStack,"step_timezone")
        step_timezoneLayout = QGridLayout(self.step_timezone,1,1,11,6,"step_timezoneLayout")

        self.titleLabel_timezone = QLabel(self.step_timezone,"titleLabel_timezone")

        step_timezoneLayout.addMultiCellWidget(self.titleLabel_timezone,0,0,0,2)

        self.line1_2_3 = QFrame(self.step_timezone,"line1_2_3")
        self.line1_2_3.setFrameShape(QFrame.HLine)
        self.line1_2_3.setFrameShadow(QFrame.Sunken)
        self.line1_2_3.setFrameShape(QFrame.HLine)

        step_timezoneLayout.addMultiCellWidget(self.line1_2_3,1,1,0,2)

        self.line2_2_3 = QFrame(self.step_timezone,"line2_2_3")
        self.line2_2_3.setFrameShape(QFrame.HLine)
        self.line2_2_3.setFrameShadow(QFrame.Sunken)
        self.line2_2_3.setFrameShape(QFrame.HLine)

        step_timezoneLayout.addMultiCellWidget(self.line2_2_3,5,5,0,2)

        self.timezone_label = QLabel(self.step_timezone,"timezone_label")

        step_timezoneLayout.addWidget(self.timezone_label,3,0)

        self.timezone_combo = QComboBox(0,self.step_timezone,"timezone_combo")
        self.timezone_combo.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed,0,0,self.timezone_combo.sizePolicy().hasHeightForWidth()))

        step_timezoneLayout.addWidget(self.timezone_combo,3,1)
        spacer19 = QSpacerItem(121,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        step_timezoneLayout.addItem(spacer19,3,2)
        spacer20 = QSpacerItem(20,41,QSizePolicy.Minimum,QSizePolicy.Expanding)
        step_timezoneLayout.addItem(spacer20,2,1)
        spacer21 = QSpacerItem(20,51,QSizePolicy.Minimum,QSizePolicy.Expanding)
        step_timezoneLayout.addItem(spacer21,4,1)
        self.widgetStack.addWidget(self.step_timezone,2)

        self.step_user = QWidget(self.widgetStack,"step_user")
        step_userLayout = QGridLayout(self.step_user,1,1,11,6,"step_userLayout")

        self.line1_2_3_2 = QFrame(self.step_user,"line1_2_3_2")
        self.line1_2_3_2.setFrameShape(QFrame.HLine)
        self.line1_2_3_2.setFrameShadow(QFrame.Sunken)
        self.line1_2_3_2.setFrameShape(QFrame.HLine)

        step_userLayout.addMultiCellWidget(self.line1_2_3_2,1,1,0,1)

        self.line2_2_3_2 = QFrame(self.step_user,"line2_2_3_2")
        self.line2_2_3_2.setFrameShape(QFrame.HLine)
        self.line2_2_3_2.setFrameShadow(QFrame.Sunken)
        self.line2_2_3_2.setFrameShape(QFrame.HLine)

        step_userLayout.addMultiCellWidget(self.line2_2_3_2,6,6,0,1)

        self.titleLabel_user = QLabel(self.step_user,"titleLabel_user")

        step_userLayout.addMultiCellWidget(self.titleLabel_user,0,0,0,1)

        self.user_pass_label = QLabel(self.step_user,"user_pass_label")

        step_userLayout.addWidget(self.user_pass_label,4,0)

        self.user_username_label = QLabel(self.step_user,"user_username_label")

        step_userLayout.addWidget(self.user_username_label,3,0)

        self.user_repass_label = QLabel(self.step_user,"user_repass_label")

        step_userLayout.addWidget(self.user_repass_label,5,0)

        self.user_fullname_label = QLabel(self.step_user,"user_fullname_label")

        step_userLayout.addWidget(self.user_fullname_label,2,0)

        self.user_repass_lineedit = QLineEdit(self.step_user,"user_repass_lineedit")
        self.user_repass_lineedit.setEchoMode(QLineEdit.Password)

        step_userLayout.addWidget(self.user_repass_lineedit,5,1)

        self.user_pass_lineedit = QLineEdit(self.step_user,"user_pass_lineedit")
        self.user_pass_lineedit.setEchoMode(QLineEdit.Password)

        step_userLayout.addWidget(self.user_pass_lineedit,4,1)

        self.user_username_lineedit = QLineEdit(self.step_user,"user_username_lineedit")

        step_userLayout.addWidget(self.user_username_lineedit,3,1)

        self.user_fullname_lineedit = QLineEdit(self.step_user,"user_fullname_lineedit")

        step_userLayout.addWidget(self.user_fullname_lineedit,2,1)
        self.widgetStack.addWidget(self.step_user,3)
        OEMConfKDEUILayout.addWidget(self.widgetStack)

        layout9 = QHBoxLayout(None,0,6,"layout9")

        self.step_label = QLabel(self,"step_label")
        layout9.addWidget(self.step_label)
        spacer4 = QSpacerItem(76,20,QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout9.addItem(spacer4)

        self.button_back = KPushButton(self,"button_back")
        layout9.addWidget(self.button_back)

        self.button_forward = KPushButton(self,"button_forward")
        layout9.addWidget(self.button_forward)
        OEMConfKDEUILayout.addLayout(layout9)

        self.languageChange()

        self.resize(QSize(461,253).expandedTo(self.minimumSizeHint()))
        self.clearWState(Qt.WState_Polished)

        self.setTabOrder(self.language_combo,self.location_combo)
        self.setTabOrder(self.location_combo,self.keyboard_combo)
        self.setTabOrder(self.keyboard_combo,self.timezone_combo)
        self.setTabOrder(self.timezone_combo,self.user_fullname_lineedit)
        self.setTabOrder(self.user_fullname_lineedit,self.user_username_lineedit)
        self.setTabOrder(self.user_username_lineedit,self.user_pass_lineedit)
        self.setTabOrder(self.user_pass_lineedit,self.user_repass_lineedit)
        self.setTabOrder(self.user_repass_lineedit,self.button_back)
        self.setTabOrder(self.button_back,self.button_forward)

        self.location_label.setBuddy(self.location_combo)
        self.language_label.setBuddy(self.language_combo)


    def languageChange(self):
        self.setCaption(self.__tr("System Configuration"))
        self.titleLabel_language.setText(self.__tr("<h3>Choose language and location</h3>"))
        self.location_label.setText(self.__tr("Choose your location:"))
        self.language_label.setText(self.__tr("Choose a language:"))
        self.titleLabel_keyboard.setText(self.__tr("<h3>Keyboard layout</h3>"))
        self.keyboard_label.setText(self.__tr("Your keyboard is:"))
        self.titleLabel_timezone.setText(self.__tr("<h3>Choose time zone</h3>"))
        self.timezone_label.setText(self.__tr("Select your time zone:"))
        self.titleLabel_user.setText(self.__tr("<h3>Who are you?</h3>"))
        self.user_pass_label.setText(self.__tr("Choose a password for the new user:"))
        self.user_username_label.setText(self.__tr("Username for your account:"))
        self.user_repass_label.setText(self.__tr("Re-enter password to verify:"))
        self.user_fullname_label.setText(self.__tr("Full name for the new user:"))
        self.step_label.setText(self.__tr("Step ${INDEX} of ${TOTAL}"))
        self.button_back.setText(self.__tr("&Back"))
        self.button_back.setAccel(QKeySequence(self.__tr("Alt+B")))
        self.button_forward.setText(self.__tr("&Forward"))
        self.button_forward.setAccel(QKeySequence(self.__tr("Alt+F")))


    def __tr(self,s,c = None):
        return qApp.translate("OEMConfKDEUI",s,c)

if __name__ == "__main__":
    appname     = ""
    description = ""
    version     = ""

    KCmdLineArgs.init (sys.argv, appname, description, version)
    a = KApplication ()

    QObject.connect(a,SIGNAL("lastWindowClosed()"),a,SLOT("quit()"))
    w = OEMConfKDEUI()
    a.setMainWidget(w)
    w.show()
    a.exec_loop()
