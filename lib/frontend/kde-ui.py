import sys, os, datetime, gettext, syslog
from sysconf import Ui_SysConf
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from debconf import DebconfCommunicator
from oem_config import filteredcommand
from oem_config.components import console_setup, language, timezone, user, \
                                  language_apply, timezone_apply, \
                                  console_setup_apply
import oem_config.tz

UIDIR = '/usr/lib/oem-config/oem_config/frontend'

WIDGET_STACK_STEPS = {
    "step_language": 0,
    "step_timezone": 1,
    "step_keyboard": 2,
    "step_user": 3
}

WIDGET_STACK_MAX_STEPS = 3

class OEMConfUI(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        uic.loadUi("%s/SysConf.ui" % UIDIR, self)
        self.setWindowState(Qt.WindowFullScreen)

    def setFrontend(self, fe):
        self.frontend = fe

    def resizeEvent(self, event):
        pixmapUnscaled = QPixmap()
        loaded = pixmapUnscaled.load("/usr/share/wallpapers/kubuntu-wallpaper.png")
        pixmap = pixmapUnscaled.scaled(QSize(self.width(), self.height()), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        palette = self.palette()
        palette.setBrush(self.backgroundRole(),QBrush(pixmap))
        self.setPalette(palette)

class Frontend:
    def __init__(self):
        self.debconf_callbacks = {}
        self.locale = None
        self.current_step = None
        self.dbfilter = None
        # Set default language.
        dbfilter = language.Language(self, DebconfCommunicator('oem-config',
                                                               cloexec=True))
        dbfilter.cleanup()
        dbfilter.db.shutdown()
        self.allowed_change_step = True
        self.allowed_go_forward = True
        self.mainLoopRunning = False
        self.apply_changes = False
        self.app = QApplication([])
        self.userinterface = OEMConfUI()
        self.userinterface.setFrontend(self)
        self.userinterface.show()
        self.customize_installer()
        self.current_layout = None
        self.map_vbox = QVBoxLayout(self.userinterface.map_frame)
        self.map_vbox.setMargin(0)
        self.tzmap = TimezoneMap(self)
        self.tzmap.tzmap.show()

    def run(self):
        global WIDGET_STACK_STEPS, WIDGET_STACK_MAX_STEPS

        self.userinterface.setCursor(QCursor(Qt.ArrowCursor))

        #Signals and Slots
        self.app.connect(self.userinterface.button_next,SIGNAL("clicked()"),self.on_next_clicked)
        self.app.connect(self.userinterface.button_back,SIGNAL("clicked()"),self.on_back_clicked)
        self.app.connect(self.userinterface.keyboard_list_1, SIGNAL("itemSelectionChanged()"), self.on_keyboard_layout_selected)
        self.app.connect(self.userinterface.keyboard_list_2, SIGNAL("itemSelectionChanged()"), self.on_keyboard_variant_selected)
        self.app.connect(self.userinterface.city_combo, SIGNAL("activated(int)"), self.tzmap.city_combo_changed)

        first_step = "step_language"
        self.userinterface.stackedWidget.setCurrentWidget(self.userinterface.step_language)
        self.current_step = self.get_current_step()
        self.set_current_page()
        while self.current_step is not None:
            self.backup = False
            self.current_step = self.get_current_step()
            if self.current_step == 'step_language':
                self.dbfilter = language.Language(self)
            elif self.current_step == 'step_keyboard':
                self.dbfilter = console_setup.ConsoleSetup(self)
            elif self.current_step == 'step_timezone':
                self.dbfilter = timezone.Timezone(self)
            elif self.current_step == 'step_user':
                self.dbfilter = user.User(self)
            else:
                raise ValueError, "step %s not recognised" % current_name
            self.allow_change_step(False)
            self.dbfilter.start(auto_process=True)
            self.app.exec_()
            self.app.processEvents()
            curr = str(self.get_current_step())

            if self.backup:
                pass
            elif self.current_step == 'step_user':
                self.allow_change_step(False)
                self.current_step = None
                self.apply_changes = True
            else:
                self.userinterface.stackedWidget.setCurrentIndex(WIDGET_STACK_STEPS[curr]+1)
                self.set_current_page()
            self.app.processEvents()
        if self.apply_changes:
            dbfilter = language_apply.LanguageApply(self)
            dbfilter.run_command(auto_process=True)

            dbfilter = timezone_apply.TimezoneApply(self)
            dbfilter.run_command(auto_process=True)

            dbfilter = console_setup_apply.ConsoleSetupApply(self)
            dbfilter.run_command(auto_process=True)


    def customize_installer(self):
        global WIDGET_STACK_MAX_STEPS
        self.step_icon_size = QSize(32,32)
        self.step_icons = [self.userinterface.step_icon_lang, self.userinterface.step_icon_loc, \
                           self.userinterface.step_icon_key, self.userinterface.step_icon_user]
        self.step_labels = [self.userinterface.step_name_lang, self.userinterface.step_name_loc, \
                            self.userinterface.step_name_key, self.userinterface.step_name_user]
        self.step_icons_path_prefix = "../../../usr/share/icons/default.kde/32x32/apps/"
        self.step_icons_path = ["locale.png","clock.png","keyboard_layout.png","userconfig.png"]
        self.step_labels_text = [self.userinterface.step_name_lang.text(),self.userinterface.step_name_loc.text(), \
                                self.userinterface.step_name_key.text(), self.userinterface.step_name_user.text()]
        for icon in range(WIDGET_STACK_MAX_STEPS+1):
            self.step_icons[icon].setPixmap(QPixmap(str(self.step_icons_path_prefix+self.step_icons_path[icon])))

    def on_keyboard_layout_selected(self):
        if isinstance(self.dbfilter, console_setup.ConsoleSetup):
            layout = self.get_keyboard()
            if layout is not None:
                self.current_layout = layout
                self.dbfilter.change_layout(layout)

    def on_keyboard_variant_selected(self):
        if isinstance(self.dbfilter, console_setup.ConsoleSetup):
            layout = self.get_keyboard()
            variant = self.get_keyboard_variant()
            if layout is not None and variant is not None:
                self.dbfilter.apply_keyboard(layout, variant)

    def set_language_choices(self, choices, choice_map):
        self.userinterface.language_list.clear()
        self.language_choice_map = dict(choice_map)
        self.lang_store = QStringList()
        for choice in choices:
            self.lang_store.append(QString(choice))
        self.userinterface.language_list.addItems(self.lang_store)


    def set_language(self, language):
        index = self.lang_store.indexOf(QRegExp("^"+language+"$"))
        if index != -1:
            self.userinterface.language_list.setCurrentRow(index)

    def get_language(self):
        value = unicode(self.userinterface.language_list.currentItem().text())
        return self.language_choice_map[value][0]

    def set_timezone (self, timezone):
        self.tzmap.set_tz_from_name(timezone)

    def get_timezone (self):
        return self.tzmap.get_selected_tz_name()

    def set_keyboard_choices(self, choices):
        self.userinterface.keyboard_list_1.clear()
        self.key_store_1 = QStringList()
        for choice in sorted(choices):
            self.key_store_1.append(QString(choice))
        self.userinterface.keyboard_list_1.addItems(self.key_store_1)

    def set_keyboard(self, keyboard):
        index = self.key_store_1.indexOf(QRegExp("^"+keyboard+"$"))
        if index != -1:
            self.userinterface.keyboard_list_1.setCurrentRow(index)

    def get_keyboard(self):
        return unicode(self.userinterface.keyboard_list_1.currentItem().text())

    def set_keyboard_variant_choices(self, choices):
        self.userinterface.keyboard_list_2.clear()
        self.key_store_2 = QStringList()
        for choice in sorted(choices):
            self.key_store_2.append(QString(choice))
        self.userinterface.keyboard_list_2.addItems(self.key_store_2)

    def set_keyboard_variant(self, variant):
        index = self.key_store_2.indexOf(QRegExp("^"+variant+"$"))
        if index != -1:
            self.userinterface.keyboard_list_2.setCurrentRow(index)

    def get_keyboard_variant(self):
        return unicode(self.userinterface.keyboard_list_2.currentItem().text())

    def set_timezone (self, timezone):
        self.tzmap.set_tz_from_name(timezone)

    def get_timezone (self):
        return self.tzmap.get_selected_tz_name()

    def set_fullname(self, value):
        self.userinterface.name_ledit.setText(value)

    def get_fullname(self):
        return unicode(self.userinterface.name_ledit.text())

    def set_username(self, value):
        self.userinterface.uname_ledit.setText(value)

    def get_username(self):
        return unicode(self.userinterface.uname_ledit.text())

    def get_password(self):
        return unicode(self.userinterface.pass_ledit_1.text())

    def get_verified_password(self):
        return unicode(self.userinterface.pass_ledit_2.text())

    def watch_debconf_fd (self, from_debconf, process_input):
        self.debconf_fd_counter = 0
        self.socketNotifierRead = QSocketNotifier(from_debconf, QSocketNotifier.Read, self.app)
        self.app.connect(self.socketNotifierRead, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_read)

        self.socketNotifierWrite = QSocketNotifier(from_debconf, QSocketNotifier.Write, self.app)
        self.app.connect(self.socketNotifierWrite, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_write)

        self.socketNotifierException = QSocketNotifier(from_debconf, QSocketNotifier.Exception, self.app)
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

    def debconffilter_done (self, dbfilter):
        ##FIXME in Qt 4 without this disconnect it calls watch_debconf_fd_helper_read once more causing
        ## a crash after the keyboard stage.  No idea why.
        self.app.disconnect(self.socketNotifierRead, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_read)
        # TODO cjwatson 2006-02-10: handle dbfilter.status
        self.app.disconnect(self.socketNotifierWrite, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_write)
        self.app.disconnect(self.socketNotifierException, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_exception)
        if dbfilter is None:
            name = 'None'
        else:
            name = dbfilter.__class__.__name__
        if self.dbfilter is None:
            currentname = 'None'
        else:
            currentname = self.dbfilter.__class__.__name__
        syslog.syslog(syslog.LOG_DEBUG,
                      "debconffilter_done: %s (current: %s)" %
                      (name, currentname))
        if dbfilter == self.dbfilter:
            self.dbfilter = None
            #if isinstance(dbfilter, summary.Summary):
                ## The Summary component is just there to gather information,
                # and won't call run_main_loop() for itself.
                #self.allow_change_step(True)
            self.app.exit()

    def run_main_loop (self):
        if not self.apply_changes:
            self.allow_change_step(True)
        #self.app.exec_()   ##FIXME Qt 4 won't allow nested main loops, here it just returns directly
        self.mainLoopRunning = True
        while self.mainLoopRunning:    # nasty, but works OK
            self.app.processEvents()

    def quit_main_loop (self):
        self.mainLoopRunning = False

    def on_back_clicked(self):
        curr = str(self.get_current_step())
        self.backup = True
        if self.dbfilter is not None:
            self.userinterface.stackedWidget.setCurrentIndex(WIDGET_STACK_STEPS[curr]-1)
            self.allow_change_step(False)
            self.dbfilter.cancel_handler()
            self.set_current_page()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits

    def on_next_clicked(self):
        if self.dbfilter is not None:
            self.allow_change_step(False)
            self.dbfilter.ok_handler()

    def redo_step(self):
        """Redo the current step. Used by the language component to rerun
        itself when the language changes."""
        self.backup = True

    def set_current_page(self):
        global WIDGET_STACK_STEPS, WIDGET_STACK_MAX_STEP
        current_name = self.get_current_step()
        if current_name == 'step_language':
            self.userinterface.button_back.hide()
        else:
            self.userinterface.button_back.show()
        if current_name == 'step_user':
            self.userinterface.button_next.setText(QApplication.translate("SysConf", "&Finish!", None, QApplication.UnicodeUTF8))
        else:
            self.userinterface.button_next.setText(QApplication.translate("SysConf", "&Continue >", None, QApplication.UnicodeUTF8))
        for icon in self.step_icons:
            pixmap = QIcon(icon.pixmap()).pixmap(self.step_icon_size, QIcon.Disabled)
            icon.setPixmap(pixmap)
        for step in range(WIDGET_STACK_MAX_STEPS+1):
            self.step_labels_text[step].replace("p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt; font-weight:800; font-style:italic;\">","<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt; color:gray;\">")
            self.step_labels[step].setText(self.step_labels_text[step])
        current_icon = self.step_icons[WIDGET_STACK_STEPS[str(current_name)]]
        current_pixmap = QPixmap(str(self.step_icons_path_prefix+self.step_icons_path[WIDGET_STACK_STEPS[str(current_name)]]))
        current_icon.setPixmap(current_pixmap)
        current_label_text = self.step_labels_text[WIDGET_STACK_STEPS[str(current_name)]]
        current_label_text.replace("<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt; color:gray;\">","<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  <span style=\" font-size:13pt; font-weight:800; font-style:italic;\">")
        self.step_labels[WIDGET_STACK_STEPS[str(current_name)]].setText(current_label_text)
    def allow_change_step(self, allowed):
        if allowed:
            cursor = QCursor(Qt.ArrowCursor)
        else:
            cursor = QCursor(Qt.WaitCursor)
        self.userinterface.setCursor(cursor)

    def allow_go_forward(self, allowed):
        self.userinterface.button_next.setEnabled(allowed and self.allowed_change_step)
        self.allowed_go_forward = allowed

    def get_current_step(self):
        return self.userinterface.stackedWidget.currentWidget().objectName()

class TimezoneMap(object):
    def __init__(self, frontend):
        self.frontend = frontend
        self.tzdb = oem_config.tz.Database()
        #self.tzmap = ubiquity.emap.EMap()
        self.tzmap = MapWidget(self.frontend.userinterface.map_frame)
        self.frontend.map_vbox.addWidget(self.tzmap)
        self.tzmap.show()
        self.update_timeout = None
        self.point_selected = None
        self.point_hover = None
        self.location_selected = None

        timezone_city_combo = self.frontend.userinterface.city_combo
        self.timezone_city_index = {}  #map human readable city name to Europe/London style zone
        self.city_index = []  # map cities to indexes for the combo box

        prev_continent = ''
        for location in self.tzdb.locations:
            #self.tzmap.add_point("", location.longitude, location.latitude,
            #                     NORMAL_RGBA)
            zone_bits = location.zone.split('/')
            if len(zone_bits) == 1:
                continue
            continent = zone_bits[0]
            if continent != prev_continent:
                timezone_city_combo.addItem('')
                self.city_index.append('')
                timezone_city_combo.addItem("--- %s ---" % continent)
                self.city_index.append("--- %s ---" % continent)
                prev_continent = continent
            human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
            timezone_city_combo.addItem(human_zone)
            self.timezone_city_index[human_zone] = location.zone
            self.city_index.append(human_zone)
            self.tzmap.cities[human_zone] = [location.latitude, location.longitude]

        self.frontend.app.connect(self.tzmap, SIGNAL("cityChanged"), self.cityChanged)
        self.mapped()

    def set_city_text(self, name):
        """ Gets a long name, Europe/London """
        timezone_city_combo = self.frontend.userinterface.city_combo
        count = timezone_city_combo.count()
        found = False
        i = 0
        zone_bits = name.split('/')
        human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
        while not found and i < count:
            if str(timezone_city_combo.itemText(i)) == human_zone:
                timezone_city_combo.setCurrentIndex(i)
                found = True
            i += 1

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
        self.frontend.userinterface.tz_selected_label.setText(text)
        translations = gettext.translation('iso_3166',
                                           languages=[self.frontend.locale],
                                           fallback=True)
        self.frontend.userinterface.region_selected_label.setText(translations.ugettext(location.human_country))
        self.update_current_time()

    def update_current_time(self):
        if self.location_selected is not None:
            now = datetime.datetime.now(self.location_selected.info)
            self.frontend.userinterface.time_current_label.setText(unicode(now.strftime('%X'), "utf-8"))

    def set_tz_from_name(self, name):
        """ Gets a long name, Europe/London """

        (longitude, latitude) = (0.0, 0.0)

        for location in self.tzdb.locations:
            if location.zone == name:
                (longitude, latitude) = (location.longitude, location.latitude)
                break
        else:
            return

        self.location_selected = location
        self.set_city_text(self.location_selected.zone)
        self.set_zone_text(self.location_selected)
        self.frontend.allow_go_forward(True)

        if name == None or name == "":
            return

    def get_tz_from_name(self, name):
        if len(name) != 0:
            return self.timezone_city_index[name]
        else:
            return None

    def city_combo_changed(self, index):
        city = str(self.frontend.userinterface.city_combo.currentText())
        try:
            zone = self.timezone_city_index[city]
        except KeyError:
            return
        self.set_tz_from_name(zone)

    def get_selected_tz_name(self):
        name = str(self.frontend.userinterface.city_combo.currentText())
        return self.get_tz_from_name(name)

    def timeout(self):
        self.update_current_time()
        return True

    def mapped(self):
        if self.update_timeout is None:
            self.update_timeout = QTimer()
            self.frontend.app.connect(self.update_timeout, SIGNAL("timeout()"), self.timeout)
            self.update_timeout.start(100)

    def cityChanged(self):
        self.frontend.userinterface.city_combo.setCurrentIndex(self.city_index.index(self.tzmap.city))
        self.city_combo_changed(self.frontend.userinterface.city_combo.currentIndex())
        self.frontend.allow_go_forward(True)

class CityIndicator(QLabel):
    def __init__(self, parent, name="cityindicator"):
        QLabel.__init__(self, parent)
        self.setMouseTracking(True)
        self.setMargin(1)
        self.setIndent(0)
        self.setAutoFillBackground(True)
        self.setLineWidth(1)
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setPalette(QToolTip.palette())
        self.setText("CityIndicator")

    def mouseMoveEvent(self, mouseEvent):
        mouseEvent.ignore()

    def setText(self, text):
        """ implement auto resize """
        QLabel.setText(self, text)
        self.adjustSize()

class MapWidget(QWidget):
    def __init__(self, parent, name="mapwidget"):
        QWidget.__init__(self, parent)
        self.setObjectName(name)
        self.setAutoFillBackground(True)
        self.imagePath = "/usr/share/oem-config/pixmaps/world_map-960.png"
        image = QImage(self.imagePath);
        pixmapUnscaled = QPixmap(self.imagePath);
        pixmap = pixmapUnscaled.scaled( QSize(self.width(), self.height()) )
        palette = QPalette()
        palette.setBrush(self.backgroundRole(), QBrush(pixmap))
        self.setPalette(palette)
        self.cities = {}
        self.cities['Edinburgh'] = [self.coordinate(False, 55, 50, 0), self.coordinate(True, 3, 15, 0)]
        self.timer = QTimer(self)
        self.connect(self.timer, SIGNAL("timeout()"), self.updateCityIndicator)
        self.setMouseTracking(True)

        self.cityIndicator = CityIndicator(self)
        self.cityIndicator.setText("")
        self.cityIndicator.hide()

    def paintEvent(self, paintEvent):
        ##FIXME this is slow, need to buffer the output.
        painter = QPainter(self)
        for city in self.cities:
            self.drawCity(self.cities[city][0], self.cities[city][1], painter)

    def drawCity(self, lat, long, painter):
        point = self.getPosition(lat, long, self.width(), self.height())
        painter.setPen(QPen(QColor(250,100,100), 1))
        painter.drawPoint(point.x(), point.y()-1)
        painter.drawPoint(point.x()-1, point.y())
        painter.drawPoint(point.x(), point.y())
        painter.drawPoint(point.x()+1, point.y())
        painter.drawPoint(point.x(), point.y()+1)
        painter.setPen(QPen(QColor(0,0,0), 1))
        painter.drawPoint(point.x(), point.y()-2)
        painter.drawPoint(point.x()-1, point.y()-1)
        painter.drawPoint(point.x()+1, point.y()-1)
        painter.drawPoint(point.x()-2, point.y())
        painter.drawPoint(point.x()+2, point.y())
        painter.drawPoint(point.x()-1, point.y()+1)
        painter.drawPoint(point.x()+1, point.y()+1)
        painter.drawPoint(point.x(), point.y()+2)

    def getPosition(self, la, lo, w, h):
        x = (w * (180.0 + lo) / 360.0)
        y = (h * (90.0 - la) / 180.0)

        return QPoint(int(x),int(y))

    def coordinate(self, neg, d, m, s):
        if neg:
            return - (d + m/60.0 + s/3600.0)
        else :
            return d + m/60.0 + s/3600.0

    def getNearestCity(self, w, h, x, y):
        result = None
        dist = 1.0e10
        for city in self.cities:
            pos = self.getPosition(self.cities[city][0], self.cities[city][1], self.width(), self.height())

            d = (pos.x()-x)*(pos.x()-x) + (pos.y()-y)*(pos.y()-y)
            if d < dist:
                dist = d
                self.where = pos
                result = city
        return result

    def mouseMoveEvent(self, mouseEvent):
        self.x = mouseEvent.pos().x()
        self.y = mouseEvent.pos().y()
        if not self.timer.isActive():
            self.timer.setSingleShot(True)
            self.timer.start(25)

    def updateCityIndicator(self):
        city = self.getNearestCity(self.width(), self.height(), self.x, self.y)
        if city is None:
            return
        self.cityIndicator.setText(city)
        movePoint = self.getPosition(self.cities[city][0], self.cities[city][1], self.width(), self.height())
        self.cityIndicator.move(movePoint.x(), movePoint.y() - self.cityIndicator.height())
        self.cityIndicator.show()

    def mouseReleaseEvent(self, mouseEvent):
        pos = mouseEvent.pos()

        city = self.getNearestCity(self.width(), self.height(), pos.x(), pos.y());
        if city is None:
            return
        elif city == "Edinburgh":
            self.city = "London"
        else:
            self.city = city
        self.emit(SIGNAL("cityChanged"), ())

    def resizeEvent(self, resizeEvent):
        image = QImage(self.imagePath);
        pixmapUnscaled = QPixmap(self.imagePath);
        pixmap = pixmapUnscaled.scaled( QSize(self.width(), self.height()), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        palette = QPalette()
        palette.setBrush(self.backgroundRole(), QBrush(pixmap))
        self.setPalette(palette)