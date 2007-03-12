# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Form2.ui'
#
# Created: Tue Mar 13 02:09:22 2007
#      by: PyQt4 UI code generator 4.1
#
# WARNING! All changes made in this file will be lost!

import sys
from PyQt4 import QtCore, QtGui

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        #Form.resize(QtCore.QSize(QtCore.QRect(0,0,861,600).size()).expandedTo(Form.minimumSizeHint()))

        Form.setWindowState(QtCore.Qt.WindowFullScreen)
        #Why does setstylesheet hog memory in feisty?
        #Form.setStyleSheet("background-image: url(/usr/lib/oem-config/oem_config/frontend/1.png)")

        #why do widgets look ugly?
        pixmap = QtGui.QPixmap()
        loaded = pixmap.load("/usr/share/wallpapers/kubuntu-wallpaper.png")
        palette = Form.palette()
        palette.setBrush(Form.backgroundRole(),QtGui.QBrush(pixmap))
        Form.setPalette(palette)

        self.gridlayout = QtGui.QGridLayout(Form)
        self.gridlayout.setMargin(9)
        self.gridlayout.setSpacing(6)
        self.gridlayout.setObjectName("gridlayout")

        self.stackedWidget = QtGui.QStackedWidget(Form)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(7),QtGui.QSizePolicy.Policy(7))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.stackedWidget.sizePolicy().hasHeightForWidth())
        self.stackedWidget.setSizePolicy(sizePolicy)
        self.stackedWidget.setMinimumSize(QtCore.QSize(500,381))
        self.stackedWidget.setObjectName("stackedWidget")

        self.step_language = QtGui.QWidget()
        self.step_language.setObjectName("step_language")

        self.gridlayout1 = QtGui.QGridLayout(self.step_language)
        self.gridlayout1.setMargin(9)
        self.gridlayout1.setSpacing(6)
        self.gridlayout1.setObjectName("gridlayout1")

        spacerItem = QtGui.QSpacerItem(191,91,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout1.addItem(spacerItem,3,1,1,1)

        spacerItem1 = QtGui.QSpacerItem(191,71,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout1.addItem(spacerItem1,0,1,1,1)

        self.language_list = QtGui.QListWidget(self.step_language)
        self.language_list.setMaximumSize(QtCore.QSize(260,350))
        self.language_list.setObjectName("language_list")
        self.gridlayout1.addWidget(self.language_list,2,1,1,1)

        self.language_label = QtGui.QLabel(self.step_language)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.language_label.sizePolicy().hasHeightForWidth())
        self.language_label.setSizePolicy(sizePolicy)
        self.language_label.setObjectName("language_label")
        self.gridlayout1.addWidget(self.language_label,1,1,1,1)

        spacerItem2 = QtGui.QSpacerItem(231,421,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout1.addItem(spacerItem2,0,2,4,1)

        spacerItem3 = QtGui.QSpacerItem(181,421,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout1.addItem(spacerItem3,0,0,4,1)
        self.stackedWidget.addWidget(self.step_language)

        self.step_timezone = QtGui.QWidget()
        self.step_timezone.setObjectName("step_timezone")

        self.gridlayout2 = QtGui.QGridLayout(self.step_timezone)
        self.gridlayout2.setMargin(9)
        self.gridlayout2.setSpacing(6)
        self.gridlayout2.setObjectName("gridlayout2")

        self.location_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location_label.sizePolicy().hasHeightForWidth())
        self.location_label.setSizePolicy(sizePolicy)
        self.location_label.setObjectName("location_label")
        self.gridlayout2.addWidget(self.location_label,1,1,1,1)

        self.map_frame = QtGui.QFrame(self.step_timezone)
        self.map_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.map_frame.setFrameShadow(QtGui.QFrame.Raised)
        self.map_frame.setObjectName("map_frame")
        self.gridlayout2.addWidget(self.map_frame,2,1,1,1)

        spacerItem4 = QtGui.QSpacerItem(60,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.gridlayout2.addItem(spacerItem4,2,2,1,1)

        spacerItem5 = QtGui.QSpacerItem(100,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.gridlayout2.addItem(spacerItem5,2,0,1,1)

        self.gridlayout3 = QtGui.QGridLayout()
        self.gridlayout3.setMargin(0)
        self.gridlayout3.setSpacing(6)
        self.gridlayout3.setObjectName("gridlayout3")

        self.city_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.city_label.sizePolicy().hasHeightForWidth())
        self.city_label.setSizePolicy(sizePolicy)
        self.city_label.setObjectName("city_label")
        self.gridlayout3.addWidget(self.city_label,0,0,1,1)

        self.city_combo = QtGui.QComboBox(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(7),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.city_combo.sizePolicy().hasHeightForWidth())
        self.city_combo.setSizePolicy(sizePolicy)
        self.city_combo.setObjectName("city_combo")
        self.gridlayout3.addWidget(self.city_combo,0,1,1,1)

        self.region_selected_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.region_selected_label.sizePolicy().hasHeightForWidth())
        self.region_selected_label.setSizePolicy(sizePolicy)
        self.region_selected_label.setObjectName("region_selected_label")
        self.gridlayout3.addWidget(self.region_selected_label,0,4,1,1)

        self.tz_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tz_label.sizePolicy().hasHeightForWidth())
        self.tz_label.setSizePolicy(sizePolicy)
        self.tz_label.setObjectName("tz_label")
        self.gridlayout3.addWidget(self.tz_label,1,0,1,1)

        self.tz_selected_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tz_selected_label.sizePolicy().hasHeightForWidth())
        self.tz_selected_label.setSizePolicy(sizePolicy)
        self.tz_selected_label.setObjectName("tz_selected_label")
        self.gridlayout3.addWidget(self.tz_selected_label,1,1,1,1)

        self.region_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.region_label.sizePolicy().hasHeightForWidth())
        self.region_label.setSizePolicy(sizePolicy)
        self.region_label.setObjectName("region_label")
        self.gridlayout3.addWidget(self.region_label,0,3,1,1)

        spacerItem6 = QtGui.QSpacerItem(111,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout3.addItem(spacerItem6,1,2,1,1)

        self.time_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.time_label.sizePolicy().hasHeightForWidth())
        self.time_label.setSizePolicy(sizePolicy)
        self.time_label.setObjectName("time_label")
        self.gridlayout3.addWidget(self.time_label,1,3,1,1)

        self.time_current_label = QtGui.QLabel(self.step_timezone)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.time_current_label.sizePolicy().hasHeightForWidth())
        self.time_current_label.setSizePolicy(sizePolicy)
        self.time_current_label.setObjectName("time_current_label")
        self.gridlayout3.addWidget(self.time_current_label,1,4,1,1)

        spacerItem7 = QtGui.QSpacerItem(31,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout3.addItem(spacerItem7,1,5,1,2)

        spacerItem8 = QtGui.QSpacerItem(111,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout3.addItem(spacerItem8,0,5,1,1)
        self.gridlayout2.addLayout(self.gridlayout3,3,1,1,1)

        spacerItem9 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout2.addItem(spacerItem9,4,1,1,1)

        spacerItem10 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout2.addItem(spacerItem10,0,1,1,1)
        self.stackedWidget.addWidget(self.step_timezone)

        self.step_keyboard = QtGui.QWidget()
        self.step_keyboard.setObjectName("step_keyboard")

        self.gridlayout4 = QtGui.QGridLayout(self.step_keyboard)
        self.gridlayout4.setMargin(9)
        self.gridlayout4.setSpacing(6)
        self.gridlayout4.setObjectName("gridlayout4")

        self.gridlayout5 = QtGui.QGridLayout()
        self.gridlayout5.setMargin(0)
        self.gridlayout5.setSpacing(6)
        self.gridlayout5.setObjectName("gridlayout5")

        self.keyboard_test_ledit = QtGui.QLineEdit(self.step_keyboard)
        self.keyboard_test_ledit.setObjectName("keyboard_test_ledit")
        self.gridlayout5.addWidget(self.keyboard_test_ledit,1,1,1,1)

        self.keyboard_test_label = QtGui.QLabel(self.step_keyboard)
        self.keyboard_test_label.setObjectName("keyboard_test_label")
        self.gridlayout5.addWidget(self.keyboard_test_label,0,1,1,1)

        spacerItem11 = QtGui.QSpacerItem(20,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout5.addItem(spacerItem11,1,0,1,1)

        spacerItem12 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout5.addItem(spacerItem12,1,2,1,1)
        self.gridlayout4.addLayout(self.gridlayout5,3,1,1,1)

        spacerItem13 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout4.addItem(spacerItem13,2,1,1,1)

        spacerItem14 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout4.addItem(spacerItem14,4,1,1,2)

        spacerItem15 = QtGui.QSpacerItem(20,50,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout4.addItem(spacerItem15,0,1,1,2)

        spacerItem16 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout4.addItem(spacerItem16,1,0,1,1)

        spacerItem17 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout4.addItem(spacerItem17,1,2,1,1)

        self.gridlayout6 = QtGui.QGridLayout()
        self.gridlayout6.setMargin(0)
        self.gridlayout6.setSpacing(6)
        self.gridlayout6.setObjectName("gridlayout6")

        self.keyboard_list_2 = QtGui.QListWidget(self.step_keyboard)
        self.keyboard_list_2.setObjectName("keyboard_list_2")
        self.gridlayout6.addWidget(self.keyboard_list_2,1,3,1,1)

        spacerItem18 = QtGui.QSpacerItem(20,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.gridlayout6.addItem(spacerItem18,1,2,1,1)

        self.keyboard_list_1 = QtGui.QListWidget(self.step_keyboard)
        self.keyboard_list_1.setObjectName("keyboard_list_1")
        self.gridlayout6.addWidget(self.keyboard_list_1,1,1,1,1)

        self.keyboard_label = QtGui.QLabel(self.step_keyboard)
        self.keyboard_label.setObjectName("keyboard_label")
        self.gridlayout6.addWidget(self.keyboard_label,0,1,1,3)

        spacerItem19 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout6.addItem(spacerItem19,1,0,1,1)
        self.gridlayout4.addLayout(self.gridlayout6,1,1,1,1)
        self.stackedWidget.addWidget(self.step_keyboard)

        self.step_user = QtGui.QWidget()
        self.step_user.setObjectName("step_user")

        self.hboxlayout = QtGui.QHBoxLayout(self.step_user)
        self.hboxlayout.setMargin(9)
        self.hboxlayout.setSpacing(6)
        self.hboxlayout.setObjectName("hboxlayout")

        spacerItem20 = QtGui.QSpacerItem(100,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem20)

        self.vboxlayout = QtGui.QVBoxLayout()
        self.vboxlayout.setMargin(0)
        self.vboxlayout.setSpacing(6)
        self.vboxlayout.setObjectName("vboxlayout")

        spacerItem21 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem21)

        self.gridlayout7 = QtGui.QGridLayout()
        self.gridlayout7.setMargin(0)
        self.gridlayout7.setSpacing(6)
        self.gridlayout7.setObjectName("gridlayout7")

        spacerItem22 = QtGui.QSpacerItem(20,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.gridlayout7.addItem(spacerItem22,1,0,1,1)

        self.name_error_reason = QtGui.QLabel(self.step_user)
        self.name_error_reason.setObjectName("name_error_reason")
        self.gridlayout7.addWidget(self.name_error_reason,1,3,1,1)

        self.name_ledit = QtGui.QLineEdit(self.step_user)
        self.name_ledit.setObjectName("name_ledit")
        self.gridlayout7.addWidget(self.name_ledit,1,1,1,1)

        self.name_error_image = QtGui.QLabel(self.step_user)
        self.name_error_image.setObjectName("name_error_image")
        self.gridlayout7.addWidget(self.name_error_image,1,2,1,1)

        spacerItem23 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout7.addItem(spacerItem23,1,4,1,1)

        self.name_label = QtGui.QLabel(self.step_user)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.name_label.sizePolicy().hasHeightForWidth())
        self.name_label.setSizePolicy(sizePolicy)
        self.name_label.setObjectName("name_label")
        self.gridlayout7.addWidget(self.name_label,0,1,1,4)
        self.vboxlayout.addLayout(self.gridlayout7)

        spacerItem24 = QtGui.QSpacerItem(20,20,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem24)

        self.gridlayout8 = QtGui.QGridLayout()
        self.gridlayout8.setMargin(0)
        self.gridlayout8.setSpacing(6)
        self.gridlayout8.setObjectName("gridlayout8")

        self.uname_extra_label = QtGui.QLabel(self.step_user)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(1),QtGui.QSizePolicy.Policy(1))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.uname_extra_label.sizePolicy().hasHeightForWidth())
        self.uname_extra_label.setSizePolicy(sizePolicy)
        self.uname_extra_label.setScaledContents(True)
        self.uname_extra_label.setWordWrap(True)
        self.uname_extra_label.setObjectName("uname_extra_label")
        self.gridlayout8.addWidget(self.uname_extra_label,2,1,1,4)

        self.uname_ledit = QtGui.QLineEdit(self.step_user)
        self.uname_ledit.setObjectName("uname_ledit")
        self.gridlayout8.addWidget(self.uname_ledit,1,1,1,1)

        spacerItem25 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout8.addItem(spacerItem25,1,4,1,1)

        spacerItem26 = QtGui.QSpacerItem(20,31,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.gridlayout8.addItem(spacerItem26,1,0,1,1)

        self.uname_error_reason = QtGui.QLabel(self.step_user)
        self.uname_error_reason.setObjectName("uname_error_reason")
        self.gridlayout8.addWidget(self.uname_error_reason,1,3,1,1)

        self.uname_error_image = QtGui.QLabel(self.step_user)
        self.uname_error_image.setObjectName("uname_error_image")
        self.gridlayout8.addWidget(self.uname_error_image,1,2,1,1)

        self.uname_label = QtGui.QLabel(self.step_user)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.uname_label.sizePolicy().hasHeightForWidth())
        self.uname_label.setSizePolicy(sizePolicy)
        self.uname_label.setObjectName("uname_label")
        self.gridlayout8.addWidget(self.uname_label,0,1,1,4)
        self.vboxlayout.addLayout(self.gridlayout8)

        spacerItem27 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem27)

        self.gridlayout9 = QtGui.QGridLayout()
        self.gridlayout9.setMargin(0)
        self.gridlayout9.setSpacing(6)
        self.gridlayout9.setObjectName("gridlayout9")

        spacerItem28 = QtGui.QSpacerItem(20,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.gridlayout9.addItem(spacerItem28,1,0,1,1)

        spacerItem29 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout9.addItem(spacerItem29,1,5,1,1)

        self.password_error_reason = QtGui.QLabel(self.step_user)
        self.password_error_reason.setObjectName("password_error_reason")
        self.gridlayout9.addWidget(self.password_error_reason,1,4,1,1)

        self.pass_label = QtGui.QLabel(self.step_user)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pass_label.sizePolicy().hasHeightForWidth())
        self.pass_label.setSizePolicy(sizePolicy)
        self.pass_label.setObjectName("pass_label")
        self.gridlayout9.addWidget(self.pass_label,0,1,1,5)

        self.pass_ledit_1 = QtGui.QLineEdit(self.step_user)
        self.pass_ledit_1.setEchoMode(QtGui.QLineEdit.Password)
        self.pass_ledit_1.setObjectName("pass_ledit_1")
        self.gridlayout9.addWidget(self.pass_ledit_1,1,1,1,1)

        self.pass_ledit_2 = QtGui.QLineEdit(self.step_user)
        self.pass_ledit_2.setEchoMode(QtGui.QLineEdit.Password)
        self.pass_ledit_2.setObjectName("pass_ledit_2")
        self.gridlayout9.addWidget(self.pass_ledit_2,1,2,1,1)

        self.password_error_label = QtGui.QLabel(self.step_user)
        self.password_error_label.setObjectName("password_error_label")
        self.gridlayout9.addWidget(self.password_error_label,1,3,1,1)

        self.pass_extra_label = QtGui.QLabel(self.step_user)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pass_extra_label.sizePolicy().hasHeightForWidth())
        self.pass_extra_label.setSizePolicy(sizePolicy)
        self.pass_extra_label.setWordWrap(False)
        self.pass_extra_label.setObjectName("pass_extra_label")
        self.gridlayout9.addWidget(self.pass_extra_label,2,1,1,5)
        self.vboxlayout.addLayout(self.gridlayout9)

        spacerItem30 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem30)

        self.gridlayout10 = QtGui.QGridLayout()
        self.gridlayout10.setMargin(0)
        self.gridlayout10.setSpacing(6)
        self.gridlayout10.setObjectName("gridlayout10")

        self.hname_error_label = QtGui.QLabel(self.step_user)
        self.hname_error_label.setObjectName("hname_error_label")
        self.gridlayout10.addWidget(self.hname_error_label,1,2,1,1)

        spacerItem31 = QtGui.QSpacerItem(21,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.gridlayout10.addItem(spacerItem31,1,0,1,1)

        self.hname_extra_label = QtGui.QLabel(self.step_user)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.hname_extra_label.sizePolicy().hasHeightForWidth())
        self.hname_extra_label.setSizePolicy(sizePolicy)
        self.hname_extra_label.setScaledContents(True)
        self.hname_extra_label.setWordWrap(True)
        self.hname_extra_label.setObjectName("hname_extra_label")
        self.gridlayout10.addWidget(self.hname_extra_label,2,1,1,4)

        self.hname_ledit = QtGui.QLineEdit(self.step_user)
        self.hname_ledit.setObjectName("hname_ledit")
        self.gridlayout10.addWidget(self.hname_ledit,1,1,1,1)

        self.vboxlayout1 = QtGui.QVBoxLayout()
        self.vboxlayout1.setMargin(0)
        self.vboxlayout1.setSpacing(6)
        self.vboxlayout1.setObjectName("vboxlayout1")

        spacerItem32 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.vboxlayout1.addItem(spacerItem32)
        self.gridlayout10.addLayout(self.vboxlayout1,1,4,1,1)

        self.hname_error_reason = QtGui.QLabel(self.step_user)
        self.hname_error_reason.setObjectName("hname_error_reason")
        self.gridlayout10.addWidget(self.hname_error_reason,1,3,1,1)

        self.hname_label = QtGui.QLabel(self.step_user)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.hname_label.sizePolicy().hasHeightForWidth())
        self.hname_label.setSizePolicy(sizePolicy)
        self.hname_label.setObjectName("hname_label")
        self.gridlayout10.addWidget(self.hname_label,0,1,1,4)
        self.vboxlayout.addLayout(self.gridlayout10)

        spacerItem33 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem33)
        self.hboxlayout.addLayout(self.vboxlayout)

        spacerItem34 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Fixed,QtGui.QSizePolicy.Minimum)
        self.hboxlayout.addItem(spacerItem34)
        self.stackedWidget.addWidget(self.step_user)
        self.gridlayout.addWidget(self.stackedWidget,1,1,3,1)

        spacerItem35 = QtGui.QSpacerItem(131,71,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Maximum)
        self.gridlayout.addItem(spacerItem35,3,0,1,1)

        spacerItem36 = QtGui.QSpacerItem(131,51,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Maximum)
        self.gridlayout.addItem(spacerItem36,1,0,1,1)

        self.hboxlayout1 = QtGui.QHBoxLayout()
        self.hboxlayout1.setMargin(0)
        self.hboxlayout1.setSpacing(6)
        self.hboxlayout1.setObjectName("hboxlayout1")

        self.button_help = QtGui.QPushButton(Form)
        self.button_help.setObjectName("button_help")
        self.hboxlayout1.addWidget(self.button_help)

        spacerItem37 = QtGui.QSpacerItem(561,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.hboxlayout1.addItem(spacerItem37)

        self.button_back = QtGui.QPushButton(Form)
        self.button_back.setObjectName("button_back")
        self.hboxlayout1.addWidget(self.button_back)

        self.button_next = QtGui.QPushButton(Form)
        self.button_next.setObjectName("button_next")
        self.hboxlayout1.addWidget(self.button_next)
        self.gridlayout.addLayout(self.hboxlayout1,4,0,1,2)

        self.gridlayout11 = QtGui.QGridLayout()
        self.gridlayout11.setMargin(0)
        self.gridlayout11.setSpacing(6)
        self.gridlayout11.setObjectName("gridlayout11")

        self.welcome_label = QtGui.QLabel(Form)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.welcome_label.sizePolicy().hasHeightForWidth())
        self.welcome_label.setSizePolicy(sizePolicy)
        self.welcome_label.setObjectName("welcome_label")
        self.gridlayout11.addWidget(self.welcome_label,0,0,1,1)

        self.welcome2_label = QtGui.QLabel(Form)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Policy(5),QtGui.QSizePolicy.Policy(0))
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.welcome2_label.sizePolicy().hasHeightForWidth())
        self.welcome2_label.setSizePolicy(sizePolicy)
        self.welcome2_label.setObjectName("welcome2_label")
        self.gridlayout11.addWidget(self.welcome2_label,1,0,1,1)

        spacerItem38 = QtGui.QSpacerItem(646,21,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout11.addItem(spacerItem38,1,1,1,2)

        spacerItem39 = QtGui.QSpacerItem(713,50,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout11.addItem(spacerItem39,0,1,1,2)
        self.gridlayout.addLayout(self.gridlayout11,0,0,1,2)

        self.gridlayout12 = QtGui.QGridLayout()
        self.gridlayout12.setMargin(0)
        self.gridlayout12.setSpacing(6)
        self.gridlayout12.setObjectName("gridlayout12")

        self.step_icon_key = QtGui.QLabel(Form)
        self.step_icon_key.setPixmap(QtGui.QPixmap("../../../usr/share/icons/default.kde/32x32/apps/keyboard_layout.png"))
        self.step_icon_key.setObjectName("step_icon_key")
        self.gridlayout12.addWidget(self.step_icon_key,4,0,1,1)

        spacerItem40 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout12.addItem(spacerItem40,5,0,1,2)

        self.step_icon_loc = QtGui.QLabel(Form)
        self.step_icon_loc.setPixmap(QtGui.QPixmap("../../../usr/share/icons/default.kde/32x32/apps/clock.png"))
        self.step_icon_loc.setObjectName("step_icon_loc")
        self.gridlayout12.addWidget(self.step_icon_loc,2,0,1,1)

        spacerItem41 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout12.addItem(spacerItem41,3,0,1,2)

        spacerItem42 = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Fixed)
        self.gridlayout12.addItem(spacerItem42,1,0,1,2)

        self.step_name_key = QtGui.QLabel(Form)
        self.step_name_key.setObjectName("step_name_key")
        self.gridlayout12.addWidget(self.step_name_key,4,1,1,1)

        self.step_name_lang = QtGui.QLabel(Form)
        self.step_name_lang.setObjectName("step_name_lang")
        self.gridlayout12.addWidget(self.step_name_lang,0,1,1,1)

        self.step_icon_lang = QtGui.QLabel(Form)
        self.step_icon_lang.setPixmap(QtGui.QPixmap("../../../usr/share/icons/default.kde/32x32/apps/locale.png"))
        self.step_icon_lang.setObjectName("step_icon_lang")
        self.gridlayout12.addWidget(self.step_icon_lang,0,0,1,1)

        self.step_name_loc = QtGui.QLabel(Form)
        self.step_name_loc.setObjectName("step_name_loc")
        self.gridlayout12.addWidget(self.step_name_loc,2,1,1,1)

        self.step_icon_user = QtGui.QLabel(Form)
        self.step_icon_user.setPixmap(QtGui.QPixmap("../../../usr/share/icons/default.kde/32x32/apps/userconfig.png"))
        self.step_icon_user.setObjectName("step_icon_user")
        self.gridlayout12.addWidget(self.step_icon_user,6,0,1,1)

        self.step_name_user = QtGui.QLabel(Form)
        self.step_name_user.setObjectName("step_name_user")
        self.gridlayout12.addWidget(self.step_name_user,6,1,1,1)
        self.gridlayout.addLayout(self.gridlayout12,2,0,1,1)

        self.retranslateUi(Form)
        self.stackedWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Form)
        Form.setTabOrder(self.button_back,self.language_list)
        Form.setTabOrder(self.language_list,self.city_combo)
        Form.setTabOrder(self.city_combo,self.keyboard_list_1)
        Form.setTabOrder(self.keyboard_list_1,self.keyboard_list_2)
        Form.setTabOrder(self.keyboard_list_2,self.keyboard_test_ledit)
        Form.setTabOrder(self.keyboard_test_ledit,self.name_ledit)
        Form.setTabOrder(self.name_ledit,self.uname_ledit)
        Form.setTabOrder(self.uname_ledit,self.pass_ledit_1)
        Form.setTabOrder(self.pass_ledit_1,self.pass_ledit_2)
        Form.setTabOrder(self.pass_ledit_2,self.hname_ledit)
        Form.setTabOrder(self.hname_ledit,self.button_next)
        Form.setTabOrder(self.button_next,self.button_help)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "System Configuration", None, QtGui.QApplication.UnicodeUTF8))
        self.language_label.setText(QtGui.QApplication.translate("Form", "Select a Language:", None, QtGui.QApplication.UnicodeUTF8))
        self.location_label.setText(QtGui.QApplication.translate("Form", "Select a city in your country and time zone.", None, QtGui.QApplication.UnicodeUTF8))
        self.city_label.setText(QtGui.QApplication.translate("Form", "Selected city:", None, QtGui.QApplication.UnicodeUTF8))
        self.tz_label.setText(QtGui.QApplication.translate("Form", "Time zone:", None, QtGui.QApplication.UnicodeUTF8))
        self.region_label.setText(QtGui.QApplication.translate("Form", "Selected region:", None, QtGui.QApplication.UnicodeUTF8))
        self.time_label.setText(QtGui.QApplication.translate("Form", "Current time:", None, QtGui.QApplication.UnicodeUTF8))
        self.keyboard_test_label.setText(QtGui.QApplication.translate("Form", "You can type into this box to test your new keyboard layout.", None, QtGui.QApplication.UnicodeUTF8))
        self.keyboard_label.setText(QtGui.QApplication.translate("Form", "Which layout is most similar to your keyboard?", None, QtGui.QApplication.UnicodeUTF8))
        self.name_label.setText(QtGui.QApplication.translate("Form", "What is your name?", None, QtGui.QApplication.UnicodeUTF8))
        self.uname_extra_label.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-style:italic;\">If more than one person will use this computer, you can set up multiple accounts after installation.</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.uname_label.setText(QtGui.QApplication.translate("Form", "What name do you want to use to log in?", None, QtGui.QApplication.UnicodeUTF8))
        self.pass_label.setText(QtGui.QApplication.translate("Form", "Choose a password to keep your account safe.", None, QtGui.QApplication.UnicodeUTF8))
        self.pass_extra_label.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-style:italic;\">Enter the same password twice, so that it can be checked for typing errors.</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.hname_extra_label.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-style:italic;\">This name will be used if you make the computer visible to others on a network.</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.hname_label.setText(QtGui.QApplication.translate("Form", "What is the name of this computer?", None, QtGui.QApplication.UnicodeUTF8))
        self.button_help.setText(QtGui.QApplication.translate("Form", "&Help", None, QtGui.QApplication.UnicodeUTF8))
        self.button_back.setText(QtGui.QApplication.translate("Form", "< &Go Back", None, QtGui.QApplication.UnicodeUTF8))
        self.button_next.setText(QtGui.QApplication.translate("Form", "&Continue >", None, QtGui.QApplication.UnicodeUTF8))
        self.welcome_label.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:20pt; font-style:italic;\">Welcome!</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.welcome2_label.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:11pt;\">Let\'s Configure your system...</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.step_name_key.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt;\">Keyboard Setup</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.step_name_lang.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt;\">Language</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.step_name_loc.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt;\">Location</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.step_name_user.setText(QtGui.QApplication.translate("Form", "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
        "p, li { white-space: pre-wrap; }\n"
        "</style></head><body style=\" font-family:\'Sans Serif\'; font-size:9pt; font-weight:400; font-style:normal; text-decoration:none;\">\n"
        "<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt;\">User Setup</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))

