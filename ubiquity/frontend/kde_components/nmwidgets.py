import string

if __name__ == "__main__":
    # This is done by kde_ui.py. We need to do the same for our test main(),
    # but it must be done *before* importing any PyQt4 module
    import sip
    sip.setapi('QVariant', 1)

from PyQt4 import QtCore
from PyQt4 import QtGui

from ubiquity.nm import QueuedCaller, NetworkStore, NetworkManager


ICON_SIZE = 22


class QtQueuedCaller(QueuedCaller):
    def __init__(self, *args):
        QueuedCaller.__init__(self, *args)
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.timeout)
        self.timer.timeout.connect(self.callback)

    def start(self):
        self.timer.start()


# Our wireless icons are unreadable over a white background, so...
# let's generate them.
def draw_level_pix(wanted_level):
    pix = QtGui.QPixmap(ICON_SIZE, ICON_SIZE)
    pix.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pix)
    color = QtGui.QApplication.palette().color(QtGui.QPalette.Text)
    painter.translate(0, -2)
    painter.setPen(QtGui.QPen(color, 2))
    painter.setRenderHint(QtGui.QPainter.Antialiasing)

    right = pix.width()
    bottom = pix.height()
    middle = bottom / 2 + 1

    center = QtCore.QPointF(right / 2., bottom - 1)
    for level in range(4):
        radius = 1 + level * 4
        if level <= wanted_level - 1:
            painter.setOpacity(0.8)
        else:
            painter.setOpacity(0.3)
        painter.drawEllipse(center, radius, radius)

    painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
    painter.setBrush(QtCore.Qt.black)
    painter.drawPolygon(QtGui.QPolygon(
        [center.x(), bottom,  0, middle,  0, bottom]))
    painter.drawPolygon(QtGui.QPolygon(
        [center.x(), bottom,  right, middle,  right, bottom]))
    painter.translate(0, 2)
    painter.drawRect(0, pix.height() - 2 , pix.width(), 2)
    painter.end()
    return pix


class QtNetworkStore(QtGui.QStandardItemModel, NetworkStore):
    IsSecureRole = QtCore.Qt.UserRole + 1
    StrengthRole = QtCore.Qt.UserRole + 2
    SsidRole = QtCore.Qt.UserRole + 3

    def __init__(self, parent=None):
        QtGui.QStandardItemModel.__init__(self, parent)
        self._init_icons()

    def get_device_ids(self):
        return [self.item(x).id for x in range(self.rowCount())]

    def add_device(self, devid, vendor, model):
        item = QtGui.QStandardItem("%s %s" % (vendor, model))
        item.setIcon(QtGui.QIcon.fromTheme("network-wireless"))
        item.setSelectable(False)
        # devid is a dbus.ObjectPath, so we can't store it as a QVariant using
        # setData().
        # That's why we keep it as item attribute.
        item.id = devid
        self.appendRow(item)

    def has_device(self, devid):
        return self._item_for_device(devid) is not None

    def remove_devices_not_in(self, devids):
        self._remove_rows_not_in(None, devids)

    def add_ap(self, devid, ssid, secure, strength):
        dev_item = self._item_for_device(devid)
        assert dev_item
        item = QtGui.QStandardItem(str(ssid))
        item.id = ssid
        item.setData(secure, self.IsSecureRole)
        item.setData(strength, self.StrengthRole)
        item.setData(ssid, self.SsidRole)
        self._update_item_icon(item)
        dev_item.appendRow(item)

    def has_ap(self, devid, ssid):
        return self._item_for_ap(devid, ssid) is not None

    def set_ap_strength(self, devid, ssid, strength):
        item = self._item_for_ap(devid, ssid)
        assert item
        item.setData(self.StrengthRole, strength)
        self._update_item_icon(item)

    def remove_aps_not_in(self, devid, ssids):
        dev_item = self._item_for_device(devid)
        if not dev_item:
            return
        self._remove_rows_not_in(dev_item, ssids)

    def _remove_rows_not_in(self, parent_item, ids):
        row = 0
        if parent_item is None:
            parent_item = self.invisibleRootItem()

        while row < parent_item.rowCount():
            if parent_item.child(row).id in ids:
                row += 1
            else:
                parent_item.removeRow(row)

    def _item_for_device(self, devid):
        for row in range(self.rowCount()):
            item = self.item(row)
            if item.id == devid:
                return item
        return None

    def _item_for_ap(self, devid, ssid):
        dev_item = self._item_for_device(devid)
        if not dev_item:
            return None
        for row in range(dev_item.rowCount()):
            item = dev_item.child(row)
            if item.id == ssid:
                return item
        return None

    def _update_item_icon(self, item):
        secure = item.data(QtNetworkStore.IsSecureRole).toBool()
        strength, ok = item.data(QtNetworkStore.StrengthRole).toInt()
        if strength < 30:
            icon = 0
        elif strength < 50:
            icon = 1
        elif strength < 70:
            icon = 2
        elif strength < 90:
            icon = 3
        else:
            icon = 4
        if secure:
            icon += 5
        item.setIcon(self._icons[icon])

    def _init_icons(self):
        pixes = []
        for level in range(5):
            pixes.append(draw_level_pix(level))

        secure_icon = QtGui.QIcon.fromTheme("emblem-locked")
        secure_pix = secure_icon.pixmap(ICON_SIZE / 2, ICON_SIZE / 2)
        for level in range(5):
            pix2 = QtGui.QPixmap(pixes[level])
            painter = QtGui.QPainter(pix2)
            painter.drawPixmap(ICON_SIZE - secure_pix.width(), ICON_SIZE - secure_pix.height(), secure_pix)
            painter.end()
            pixes.append(pix2)

        self._icons = [QtGui.QIcon(x) for x in pixes]


class NetworkManagerTreeView(QtGui.QTreeView):
    def __init__(self, password_entry=None, state_changed=None):
        QtGui.QTreeView.__init__(self)
        self.password_entry = password_entry
        model = QtNetworkStore(self)

        self.wifi_model = NetworkManager(model, QtQueuedCaller, state_changed)
        self.setModel(model)
        self.setHeaderHidden(True)
        self.setIconSize(QtCore.QSize(ICON_SIZE, ICON_SIZE))

    def rowsInserted(self, parent, start, end):
        QtGui.QTreeView.rowsInserted(self, parent, start, end)
        if not parent.isValid():
            return
        self.setExpanded(parent, True)

    def showEvent(self, event):
        QtGui.QTreeView.showEvent(self, event)
        for row in range(self.model().rowCount()):
            index = self.model().index(row, 0)
            self.setExpanded(index, True)

    def is_row_an_ap(self):
        index = self.currentIndex()
        if not index.isValid():
            return False
        return index.parent().isValid()
#
#    def get_state(self):
#        return self.wifi_model.get_state()
#
#    def disconnect_from_ap(self):
#        self.wifi_model.disconnect_from_ap()
#
#    def row_activated(self, unused, path, column):
#        passphrase = None
#        if self.password_entry:
#            passphrase = self.password_entry.get_text()
#        self.connect_to_selection(passphrase)
#
    def get_passphrase(self, ssid):
        try:
            cached = self.wifi_model.passphrases_cache[ssid]
        except KeyError:
            return ''
        return cached

#    def is_row_an_ap(self):
#        model, iterator = self.get_selection().get_selected()
#        if iterator is None:
#            return False
#        return model.iter_parent(iterator) is not None
#
#    def is_row_connected(self):
#        model, iterator = self.get_selection().get_selected()
#        if iterator is None:
#            return False
#        ssid = model[iterator][0]
#        parent = model.iter_parent(iterator)
#        if parent and self.wifi_model.is_connected(model[parent][0], ssid):
#            return True
#        else:
#            return False
#
#    def connect_to_selection(self, passphrase):
#        model, iterator = self.get_selection().get_selected()
#        ssid = model[iterator][0]
#        parent = model.iter_parent(iterator)
#        if parent:
#            self.wifi_model.connect_to_ap(model[parent][0], ssid, passphrase)


class NetworkManagerWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.password_entry = QtGui.QLineEdit()
        self.password_entry.returnPressed.connect(self.connect_to_ap)
        self.password_entry.textChanged.connect(self.password_entry_changed)

        self.password_label = QtGui.QLabel('&Password:')
        self.password_label.setBuddy(self.password_entry)

        self.display_password = QtGui.QCheckBox('Display password')
        self.display_password.toggled.connect(self.update_password_entry)

        hlayout = QtGui.QHBoxLayout()
        hlayout.addWidget(self.password_label)
        hlayout.addWidget(self.password_entry)
        hlayout.addWidget(self.display_password)

        self.view = NetworkManagerTreeView(self.password_entry,
                                           self.state_changed)
        self.view.selectionModel().currentChanged.connect(self._on_current_changed)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addLayout(hlayout)

        self.update_password_entry()

    def update_password_entry(self):
        if self.display_password.isChecked():
            self.password_entry.setEchoMode(QtGui.QLineEdit.Normal)
        else:
            self.password_entry.setEchoMode(QtGui.QLineEdit.Password)

    def translate(self, password_label_text, display_password_text):
        self.password_label.setText(password_label_text)
        self.display_password.setText(display_password_text)

    def get_state(self):
        return self.view.get_state()

    def is_row_an_ap(self):
        return self.view.is_row_an_ap()

    def is_row_connected(self):
        return self.view.is_row_connected()

    def select_usable_row(self):
        #self.selection.select_path('0:0')
        pass

    def state_changed(self, state):
        #self.emit('connection', state)
        pass

    def password_is_valid(self):
        passphrase = self.password_entry.text()
        if len(passphrase) >= 8 and len(passphrase) < 64:
            return True
        if len(passphrase) == 64:
            for c in passphrase:
                if not c in string.hexdigits:
                    return False
            return True
        else:
            return False

    def connect_to_ap(self, *args):
        if self.password_is_valid():
            passphrase = self.password_entry.text()
            self.view.connect_to_selection(passphrase)

    def disconnect_from_ap(self):
        self.view.disconnect_from_ap()

    def password_entry_changed(self, *args):
        #self.emit('pw_validated', self.password_is_valid())
        pass

    def _on_current_changed(self, current):
        if not self.is_row_an_ap():
            self._set_secure_widgets_enabled(False)
            return
        secure = current.data(QtNetworkStore.IsSecureRole).toBool()
        self._set_secure_widgets_enabled(secure)
        if secure:
            ssid = current.data(QtNetworkStore.SsidRole).toString()
            passphrase = self.view.get_passphrase(ssid)
            self.password_entry.setText(passphrase)

    def _set_secure_widgets_enabled(self, enabled):
        for widget in self.password_label, self.password_entry, self.display_password:
            widget.setEnabled(enabled)
        if not enabled:
            self.password_entry.setText('')
        """
        iterator = selection.get_selected()[1]
        if not iterator:
            return
        row = selection.get_tree_view().get_model()[iterator]
        secure = row[1]
        ssid = row[0]
        if secure:
            self.hbox.set_sensitive(True)
            passphrase = self.view.get_passphrase(ssid)
            self.password_entry.set_text(passphrase)
            self.emit('pw_validated', False)
        else:
            self.hbox.set_sensitive(False)
            self.password_entry.set_text('')
            self.emit('pw_validated', True)
        self.emit('selection_changed')
        """


def main():
    import sys
    from PyQt4.QtGui import QApplication

    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

    app = QApplication(sys.argv)
    QtGui.QIcon.setThemeName("oxygen")
    nm = NetworkManagerWidget()
    nm.show()
    app.exec_()


if __name__ == '__main__':
    main()
