import string

from PyQt4 import QtCore
from PyQt4 import QtGui

from ubiquity.nm import QueuedCaller, NetworkManager

from TreeModelAdapter import TreeModelAdapter

class QtQueuedCaller(QueuedCaller):
    def __init__(self, *args):
        QueuedCaller.__init__(self, *args)
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.timeout)
        self.timer.timeout.connect(self.callback)

    def start(self):
        self.timer.start()


class NetworkManagerTreeView(QtGui.QTreeView):
    def __init__(self, password_entry=None, state_changed=None):
        QtGui.QTreeView.__init__(self)
        self.password_entry = password_entry
        self.configure_icons()
        model = QtGui.QStandardItemModel(self)
        adapter = TreeModelAdapter(model)

#        model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.wifi_model = NetworkManager(adapter, QtQueuedCaller, state_changed)
        self.setModel(model)
#
#        ssid_column = Gtk.TreeViewColumn('')
#        cell_pixbuf = Gtk.CellRendererPixbuf()
#        cell_text = Gtk.CellRendererText()
#        ssid_column.pack_start(cell_pixbuf, False)
#        ssid_column.pack_start(cell_text, True)
#        ssid_column.set_cell_data_func(cell_text, self.data_func)
#        ssid_column.set_cell_data_func(cell_pixbuf, self.pixbuf_func)
#        self.connect('row-activated', self.row_activated)
#
#        self.append_column(ssid_column)
#        self.set_headers_visible(False)
#        self.setup_row_expansion_handling(model)
#
#    def setup_row_expansion_handling(self, model):
#        """
#        If the user collapses a row, save that state. If all the APs go away
#        and then return, such as when the user toggles the wifi kill switch,
#        the UI should keep the row collapsed if it already was, or expand it.
#        """
#        self.expand_all()
#        self.rows_changed_id = None
#
#        def queue_rows_changed(*args):
#            if self.rows_changed_id:
#                GLib.source_remove(self.rows_changed_id)
#            self.rows_changed_id = GLib.idle_add(self.rows_changed)
#
#        model.connect('row-inserted', queue_rows_changed)
#        model.connect('row-deleted', queue_rows_changed)
#
#        self.user_collapsed = {}
#
#        def collapsed(self, iterator, path, collapse):
#            udi = model[iterator][0]
#            self.user_collapsed[udi] = collapse
#
#        self.connect('row-collapsed', collapsed, True)
#        self.connect('row-expanded', collapsed, False)
#
#    def rows_changed(self, *args):
#        model = self.get_model()
#        i = model.get_iter_first()
#        while i:
#            udi = model[i][0]
#            try:
#                if not self.user_collapsed[udi]:
#                    path = model.get_path(i)
#                    self.expand_row(path, False)
#            except KeyError:
#                path = model.get_path(i)
#                self.expand_row(path, False)
#            i = model.iter_next(i)
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
    def configure_icons(self):
        pass
#        it = Gtk.IconTheme()
#        default = Gtk.IconTheme.get_default()
#        default = default.load_icon(Gtk.STOCK_MISSING_IMAGE, 22, 0)
#        it.set_custom_theme('ubuntu-mono-light')
#        self.icons = []
#        for n in ['nm-signal-00',
#                  'nm-signal-25',
#                  'nm-signal-50',
#                  'nm-signal-75',
#                  'nm-signal-100',
#                  'nm-signal-00-secure',
#                  'nm-signal-25-secure',
#                  'nm-signal-50-secure',
#                  'nm-signal-75-secure',
#                  'nm-signal-100-secure']:
#            ico = it.lookup_icon(n, 22, 0)
#            if ico:
#                ico = ico.load_icon()
#            else:
#                ico = default
#            self.icons.append(ico)
#
#    def pixbuf_func(self, column, cell, model, iterator, data):
#        if not model.iter_parent(iterator):
#            cell.set_property('pixbuf', None)
#            return
#        strength = model[iterator][2]
#        if strength < 30:
#            icon = 0
#        elif strength < 50:
#            icon = 1
#        elif strength < 70:
#            icon = 2
#        elif strength < 90:
#            icon = 3
#        else:
#            icon = 4
#        if model[iterator][1]:
#            icon += 5
#        cell.set_property('pixbuf', self.icons[icon])
#
#    def data_func(self, column, cell, model, iterator, data):
#        ssid = model[iterator][0]
#
#        if not model.iter_parent(iterator):
#            txt = '%s %s' % (model[iterator][1], model[iterator][2])
#            cell.set_property('text', txt)
#        else:
#            cell.set_property('text', ssid)
#
#    def get_passphrase(self, ssid):
#        try:
#            cached = self.wifi_model.passphrases_cache[ssid]
#        except KeyError:
#            return ''
#        return cached
#
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
        #self.view.selectionModel().currentChanged.connect(self.changed)

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

    def changed(self, selection):
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
        pass


if __name__ == '__main__':
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication(sys.argv)
    nm = NetworkManagerWidget()
    nm.show()
    app.exec_()
