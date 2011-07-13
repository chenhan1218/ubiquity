import subprocess
import dbus
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
from gi.repository import Gtk, GObject

NM = 'org.freedesktop.NetworkManager'
NM_DEVICE = 'org.freedesktop.NetworkManager.Device'
NM_DEVICE_WIFI = 'org.freedesktop.NetworkManager.Device.Wireless'
NM_AP = 'org.freedesktop.NetworkManager.AccessPoint'
NM_SETTINGS = 'org.freedesktop.NetworkManager.Settings'
NM_SETTINGS_CONN = 'org.freedesktop.NetworkManager.Settings.Connection'
DEVICE_TYPE_WIFI = 2


# TODO: DBus exceptions.  Catch 'em all.

def decode_ssid(characters):
    ssid = ''.join([str(char) for char in characters])
    return ssid.encode('utf-8')

def get_prop(obj, iface, prop):
    return obj.Get(iface, prop, dbus_interface=dbus.PROPERTIES_IFACE)

def get_vendor_and_model(udi):
    vendor = ''
    model = ''
    cmd = ['udevadm', 'info', '--path=%s' % udi, '--query=property']
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
    if not out[1]:
        for prop in out[0].split('\n'):
            if prop.startswith('ID_VENDOR_FROM_DATABASE'):
                vendor = prop.split('ID_VENDOR_FROM_DATABASE=')[1]
            elif prop.startswith('ID_MODEL_FROM_DATABASE'):
                model = prop.split('ID_MODEL_FROM_DATABASE=')[1]
    return (vendor, model)

class NetworkManagerCache:
    def __init__(self, model):
        self.bus = dbus.SystemBus()
        self.manager = self.bus.get_object(NM, '/org/freedesktop/NetworkManager')
        self.model = model
        self.bus.add_signal_receiver(self.ap_added, 'AccessPointAdded',
                                     NM_DEVICE_WIFI, NM)
        self.bus.add_signal_receiver(self.ap_removed, 'AccessPointRemoved',
                                     NM_DEVICE_WIFI, NM)
        self.build_cache()
        self.build_passphrase_cache()

    # TODO device added, removed, call build_cache in the former?

    def connect_to_ap(self, device, ap, passphrase=None):
        obj = dbus.Dictionary(signature='sa{sv}')
        if passphrase:
            obj['802-11-wireless-security'] = { 'psk' : passphrase }
        self.manager.AddAndActivateConnection(
            obj,
            dbus.ObjectPath(device),
            dbus.ObjectPath(ap))

    def ap_added(self, ap):
        print 'ap_added', ap
        iterator = self.model.get_iter_first()
        while iterator:
            device_path = self.model[iterator][0]
            device_obj = self.bus.get_object(NM, device_path)
            if get_prop(device_obj, NM_DEVICE, 'DeviceType') == DEVICE_TYPE_WIFI:
                ap_list = device_obj.GetAccessPoints(dbus_interface=NM_DEVICE_WIFI)
                for ap_path in ap_list:
                    if ap_path == ap:
                        ap_obj = self.bus.get_object(NM, ap_path)
                        ssid = decode_ssid(get_prop(ap_obj, NM_AP, 'Ssid'))
                        strength = get_prop(ap_obj, NM_AP, 'Strength')
                        security = get_prop(ap_obj, NM_AP, 'WpaFlags') != 0
                        self.cache[ap_path] = {'ssid'     : ssid,
                                               'strength' : strength,
                                               'security' : security}
                        self.model.append(iterator, [ap_path])
            iterator = self.model.iter_next(iterator)

    def ap_removed(self, ap):
        ap = str(ap)
        try:
            self.cache.pop(ap)
        except KeyError:
            print 'cache miss?', ap
            return
        def search_and_destroy(model, path, iterator, ap):
            if model[iterator][0] == ap:
                model.remove(iterator)
                return True
        self.model.foreach(search_and_destroy, ap)

    def build_passphrase_cache(self):
        self.passphrases_cache = {}
        settings_obj = self.bus.get_object(NM,
            '/org/freedesktop/NetworkManager/Settings')
        for con in settings_obj.ListConnections(dbus_interface=NM_SETTINGS):
            connection_obj = self.bus.get_object(NM, con)
            props = connection_obj.GetSettings(dbus_interface=NM_SETTINGS_CONN)
            if '802-11-wireless-security' in props:
                # TODO either infinite timeout or find some UI way of handling
                # retrying on timeout.
                sec = connection_obj.GetSecrets('802-11-wireless-security',
                                            dbus_interface=NM_SETTINGS_CONN)
                sec = sec['802-11-wireless-security'].values()[0]
                ssid = decode_ssid(props['802-11-wireless']['ssid'])
                self.passphrases_cache[ssid] = sec

    def build_cache(self):
        self.cache = {}
        for device_path in self.manager.GetDevices():
            print 'device', device_path
            device_obj = self.bus.get_object(NM, device_path)
            if get_prop(device_obj, NM_DEVICE, 'DeviceType') != DEVICE_TYPE_WIFI:
                continue
            self.cache[device_path] = {}
            cached = self.cache[device_path]
            udi = get_prop(device_obj, NM_DEVICE, 'Udi')
            cached['vendor'], cached['model'] = get_vendor_and_model(udi)
            iterator = self.model.append(None, [device_path])

            ap_list = device_obj.GetAccessPoints(dbus_interface=NM_DEVICE_WIFI)
            for ap_path in ap_list:
                ap_obj = self.bus.get_object(NM, ap_path)
                ssid = decode_ssid(get_prop(ap_obj, NM_AP, 'Ssid'))
                strength = get_prop(ap_obj, NM_AP, 'Strength')
                security = get_prop(ap_obj, NM_AP, 'WpaFlags') != 0
                self.cache[ap_path] = {'ssid'     : ssid,
                                       'strength' : strength,
                                       'security' : security}
                # TODO: there's multiple APs for a single ssid, obviously.
                # Find out how nm-applet handles this.
                print 'ap_path', ap_path, ssid
                self.model.append(iterator, [ap_path])

class NetworkManagerTreeView(Gtk.TreeView):
    __gtype_name__ = 'NetworkManagerTreeView'
    def __init__(self, password_entry=None):
        Gtk.TreeView.__init__(self)
        self.password_entry = password_entry
        self.configure_icons()
        model = Gtk.TreeStore(str)
        # TODO eventually this will subclass GenericTreeModel.
        self.wifi_model = NetworkManagerCache(model)
        self.set_model(model)

        ssid_column = Gtk.TreeViewColumn('')
        cell_pixbuf = Gtk.CellRendererPixbuf()
        cell_text = Gtk.CellRendererText()
        ssid_column.pack_start(cell_pixbuf, False)
        ssid_column.pack_start(cell_text, True)
        ssid_column.set_cell_data_func(cell_text, self.data_func)
        ssid_column.set_cell_data_func(cell_pixbuf, self.pixbuf_func)
        self.connect('row-activated', self.row_activated)

        self.append_column(ssid_column)
        self.set_headers_visible(False)
        self.expand_all()
        # TODO pre-select existing connection.

    def row_activated(self, unused, path, column):
        passphrase = None
        if self.password_entry:
            passphrase = self.password_entry.get_text()
        self.connect_to_selection(passphrase)

    def configure_icons(self):
        it = Gtk.IconTheme()
        default = Gtk.IconTheme.get_default()
        default = default.load_icon(Gtk.STOCK_MISSING_IMAGE, 22, 0)
        it.set_custom_theme('ubuntu-mono-light')
        self.icons = []
        for n in ['nm-signal-00',
                  'nm-signal-25',
                  'nm-signal-50',
                  'nm-signal-75',
                  'nm-signal-100',
                  'nm-signal-00-secure',
                  'nm-signal-25-secure',
                  'nm-signal-50-secure',
                  'nm-signal-75-secure',
                  'nm-signal-100-secure']:
            ico = it.lookup_icon(n, 22, 0)
            if ico:
                ico = ico.load_icon()
            else:
                ico = default
            self.icons.append(ico)

    def pixbuf_func(self, column, cell, model, iterator, data):
        path = model[iterator][0]
        try:
            cached = self.wifi_model.cache[path]
        except KeyError:
            return
        if not cached.has_key('strength'):
            cell.set_property('pixbuf', None)
            return
        strength = cached['strength']
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
        if cached.has_key('security'):
            icon *= 2
        cell.set_property('pixbuf', self.icons[icon])

    def data_func(self, column, cell, model, iterator, data):
        path = model[iterator][0]
        try:
            cached = self.wifi_model.cache[path]
        except KeyError:
            return
        if cached.has_key('vendor'):
            txt = '%s %s' % (cached['vendor'], cached['model'])
            cell.set_property('text', txt)
        else:
            cell.set_property('text', cached['ssid'])

    def is_secure(self, path):
        try:
            cached = self.wifi_model.cache[path]
        except KeyError:
            return
        return cached.has_key('security') and cached['security']

    def get_passphrase(self, path):
        try:
            cached = self.wifi_model.passphrases_cache[path]
        except KeyError:
            return ''
        return cached

    def get_ssid(self, path):
        try:
            return self.wifi_model.cache[path]['ssid']
        except KeyError:
            return ''

    def connect_to_selection(self, passphrase):
        model, iterator = self.get_selection().get_selected()
        path = model[iterator][0]
        try:
            cached = self.wifi_model.cache[path]
        except KeyError:
            return
        if cached.has_key('vendor'):
            return
        parent = model.iter_parent(iterator)
        if parent:
            self.wifi_model.connect_to_ap(model[parent][0], path, passphrase)
            

GObject.type_register(NetworkManagerTreeView)

class NetworkManagerWidget(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.set_spacing(12)
        self.password_entry = Gtk.Entry()
        self.view = NetworkManagerTreeView(self.password_entry)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        scrolled_window.add(self.view)
        self.add(scrolled_window)
        self.hbox = Gtk.HBox(spacing=6)
        self.pack_start(self.hbox, False, True, 0)
        password_label = Gtk.Label('Password:')
        self.password_entry.set_visibility(False)
        self.password_entry.connect('activate', self.connect)
        self.display_password = Gtk.CheckButton('Display password')
        self.display_password.connect('toggled', self.display_password_toggled)
        self.hbox.pack_start(password_label, False, True, 0)
        self.hbox.pack_start(self.password_entry, True, True, 0)
        self.hbox.pack_start(self.display_password, False, True, 0)
        selection = self.view.get_selection()
        selection.connect('changed', self.changed)
        selection.select_path(0)
    
    def connect(self, *args):
        passphrase = self.password_entry.get_text()
        self.view.connect_to_selection(passphrase)

    def display_password_toggled(self, *args):
        self.password_entry.set_visibility(self.display_password.get_active())

    def changed(self, selection):
        iterator = selection.get_selected()[1]
        if not iterator:
            return
        path = selection.get_tree_view().get_model()[iterator][0]
        if self.view.is_secure(path):
            self.hbox.set_sensitive(True)
            passphrase = self.view.get_passphrase(self.view.get_ssid(path))
            self.password_entry.set_text(passphrase)
        else:
            self.hbox.set_sensitive(False)
            self.password_entry.set_text('')

GObject.type_register(NetworkManagerWidget)

if __name__ == '__main__':
    window = Gtk.Window()
    window.connect('destroy', Gtk.main_quit)
    window.set_size_request(300, 300)
    window.set_border_width(12)
    nm = NetworkManagerWidget()
    window.add(nm)
    window.show_all()
    Gtk.main()

