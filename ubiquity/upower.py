import dbus

UPOWER = 'org.freedesktop.UPower'
UPOWER_PATH = '/org/freedesktop/UPower'
PROPS = 'org.freedesktop.DBus.Properties'

def setup_power_watch(prepare_power_source):
    bus = dbus.SystemBus()
    upower = bus.get_object(UPOWER, UPOWER_PATH)
    upower = dbus.Interface(upower, PROPS)
    def power_state_changed():
        prepare_power_source.set_state(
            upower.Get(UPOWER_PATH, 'OnBattery') == False)
    bus.add_signal_receiver(power_state_changed, 'Changed', UPOWER, UPOWER)
    power_state_changed()
