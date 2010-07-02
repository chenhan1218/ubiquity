#!/usr/bin/python

import gtk
import gobject
import cairo
import pango

def format_size(size):
    """Format a partition size."""
    if size < 1000:
        unit = 'B'
        factor = 1
    elif size < 1000 * 1000:
        unit = 'kB'
        factor = 1000
    elif size < 1000 * 1000 * 1000:
        unit = 'MB'
        factor = 1000 * 1000
    elif size < 1000 * 1000 * 1000 * 1000:
        unit = 'GB'
        factor = 1000 * 1000 * 1000
    else:
        unit = 'TB'
        factor = 1000 * 1000 * 1000 * 1000
    return '%.1f %s' % (float(size) / factor, unit)

def draw_round_rect(c, r, x, y, w, h):
    c.move_to(x+r,y)
    c.line_to(x+w-r,y);   c.curve_to(x+w,y,x+w,y,x+w,y+r)
    c.line_to(x+w,y+h-r); c.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h)
    c.line_to(x+r,y+h);   c.curve_to(x,y+h,x,y+h,x,y+h-r)
    c.line_to(x,y+r);     c.curve_to(x,y,x,y,x+r,y)
    c.close_path()

def gtk_to_cairo_color(c):
    color = gtk.gdk.color_parse(c)
    s = 1.0/65535.0
    r = color.red * s
    g = color.green * s
    b = color.blue * s
    return r, g, b

class StylizedFrame(gtk.Bin):
    __gtype_name__ = 'StylizedFrame'
    __gproperties__ = {
        'radius'  : (gobject.TYPE_INT,
                    'Radius',
                    'The radius of the rounded corners.',
                    0, 32767, 10, gobject.PARAM_READWRITE),
        'width'   : (gobject.TYPE_INT,
                    'Width',
                    'The width of the outline.',
                    0, 32767, 1, gobject.PARAM_READWRITE),
        'padding' : (gobject.TYPE_INT,
                    'Padding',
                    'The padding between the bin and the outline.',
                    0, 32767, 2, gobject.PARAM_READWRITE)
    }
    
    def do_get_property(self, prop):
        return getattr(self, prop.name)

    def do_set_property(self, prop, value):
        setattr(self, prop.name, value)

    def __init__(self):
        gtk.Bin.__init__(self)
        self.child = None
        self.radius = 10
        self.width = 1
        self.padding = 2

    #def do_realize(self):
    #    self.set_flags(gtk.REALIZED)

    #    self.window = gtk.gdk.Window(
    #        self.get_parent_window(),
    #        width=self.allocation.width,
    #        height=self.allocation.height,
    #        window_type=gtk.gdk.WINDOW_CHILD,
    #        wclass=gtk.gdk.INPUT_OUTPUT,
    #        event_mask=self.get_events() | gtk.gdk.EXPOSURE_MASK)

    #    self.window.set_user_data(self)
    #    self.style.attach(self.window)
    #    self.style.set_background(self.window, gtk.STATE_NORMAL)
    #    self.window.move_resize(*self.allocation)
    #    gtk.Bin.do_realize(self)

    def do_size_request(self, req):
        w, h = 1, 1
        if self.child:
            w, h = self.child.size_request()
        req.width = w + (self.width * 2) + (self.padding * 2)
        req.height = h + (self.width * 2) + (self.padding * 2)

    def do_size_allocate(self, alloc):
        self.allocation = alloc
        self.child.size_allocate(alloc)

    def do_forall(self, include_internals, callback, user_data):
        if self.child:
            callback (self.child, user_data)

    def paint_background(self, c):
        c.set_source_rgb(*gtk_to_cairo_color('#fbfbfb'))
        draw_round_rect(c, self.radius, self.allocation.x + self.width,
                        self.allocation.y + self.width,
                        self.allocation.width - (self.width * 2),
                        self.allocation.height - (self.width * 2))
        c.fill_preserve()

    def do_expose_event(self, event):
        x, y, w, h = self.allocation
        c = self.window.cairo_create()
        c.rectangle(x, y, w, h)
        c.clip()
        # Background
        self.paint_background(c)
        # Edge
        c.set_source_rgb(*gtk_to_cairo_color('#c7c7c6'))
        c.set_line_width(self.width)
        c.stroke()
        gtk.Bin.do_expose_event(self, event)

gobject.type_register(StylizedFrame)

# c3032
class ResizeWidget(gtk.HPaned):
    __gtype_name__ = 'ResizeWidget'
    __gproperties__ = {
        'part_size'  : (gobject.TYPE_INT,
                    'Partition size',
                    'The size of the partition being resized',
                    1, 32767, 100, gobject.PARAM_READWRITE),
        'min_size'   : (gobject.TYPE_INT,
                    'Minimum size',
                    'The minimum size that the existing partition can be '\
                    'resized to',
                    0, 32767, 0, gobject.PARAM_READWRITE),
        'max_size' : (gobject.TYPE_INT,
                    'Maximum size',
                    'The maximum size that the existing partition can be ' \
                    'resized to',
                    1, 32767, 100, gobject.PARAM_READWRITE)
    }
    
    def do_get_property(self, prop):
        return getattr(self, prop.name.replace('-', '_'))

    def do_set_property(self, prop, value):
        setattr(self, prop.name.replce('-', '_'), value)

    # TODO: Should this be automatically composed of an existing_part and
    # new_part, given that it cannot function without them.  This could then be
    # exposed in Glade, so both widgets could be named, and then the ubiquity
    # code would simply have to call set_* functions.  Or, if that doesn't work
    # (because you don't want to be able to delete them), add a get_children()
    # function.  Yes.
    def __init__(self, part_size=100, min_size=0, max_size=100, existing_part=None, new_part=None):
        gtk.HPaned.__init__(self)
        assert min_size <= max_size <= part_size
        assert part_size > 0
        # The size (b) of the existing partition.
        self.part_size = part_size
        # The minimum size (b) that the existing partition can be resized to.
        self.min_size = min_size
        # The maximum size (b) that the existing partition can be resized to.
        self.max_size = max_size

        # FIXME: Why do we still need these event boxes to get proper bounds
        # for the linear gradient?
        self.existing_part = existing_part or PartitionBox()
        eb = gtk.EventBox()
        eb.add(self.existing_part)
        self.pack1(eb, shrink=False)
        self.new_part = new_part or PartitionBox()
        eb = gtk.EventBox()
        eb.add(self.new_part)
        self.pack2(eb, shrink=False)

    def do_realize(self):
        # TEST: Make sure the value of the minimum size and maximum size equal
        # the value of the widget when pushed to the min/max.
        total = (self.new_part.get_allocation().width +
                 self.existing_part.get_allocation().width)
        tmp = float(self.min_size) / self.part_size
        pixels = int(tmp * total)
        self.existing_part.set_size_request(pixels, -1)

        tmp = ((float(self.part_size) - self.max_size) / self.part_size)
        pixels = int(tmp * total)
        self.new_part.set_size_request(pixels, -1)

        gtk.HPaned.do_realize(self)

    def do_expose_event(self, event):
        s1 = self.existing_part.get_allocation().width
        s2 = self.new_part.get_allocation().width
        total = s1 + s2

        percent = (float(s1) / float(total))
        self.existing_part.set_size(percent * self.part_size)
        
        percent = (float(s2) / float(total))
        self.new_part.set_size(percent * self.part_size)
        gtk.HPaned.do_expose_event(self, event)

    def get_size(self):
        '''Returns the size of the old partition, clipped to the minimum and
           maximum sizes.'''
        s1 = self.existing_part.get_allocation().width
        s2 = self.new_part.get_allocation().width
        totalwidth = s1 + s2
        size = int(float(s1) * self.part_size / float(totalwidth))
        if size < self.min_size:
            return self.min_size
        elif size > self.max_size:
            return self.max_size
        else:
            return size


gobject.type_register(ResizeWidget)

class PartitionBox(StylizedFrame):
    __gtype_name__ = 'PartitionBox'
    __gproperties__ = {
        'title'  : (gobject.TYPE_STRING,
                    'Title',
                    None,
                    'Title', gobject.PARAM_READWRITE),
    }
    
    def do_get_property(self, prop):
        if prop.name == 'title':
            return self.ostitle.get_text()
        return getattr(self, prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'title':
            self.ostitle.set_text(value)
            return
        setattr(self, prop.name, value)

    # TODO: A keyword argument default of a widget seems silly.  Use a string.
    def __init__(self, title='', extra='', icon=gtk.Image()):
        # 10 px above the topmost element
        # 6 px between the icon and the title
        # 4 px between the title and the extra heading
        # 5 px between the extra heading and the size
        # 12 px below the bottom-most element
        StylizedFrame.__init__(self)
        vbox = gtk.VBox()
        self.logo = icon
        align = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
        align.set_padding(10, 0, 0, 0)
        align.add(self.logo)
        vbox.pack_start(align, expand=False)

        self.ostitle = gtk.Label()
        self.ostitle.set_ellipsize(pango.ELLIPSIZE_END)
        align = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
        align.set_padding(6, 0, 0, 0)
        align.add(self.ostitle)
        vbox.pack_start(align, expand=False)

        self.extra = gtk.Label()
        self.extra.set_ellipsize(pango.ELLIPSIZE_END)
        align = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
        align.set_padding(4, 0, 0, 0)
        align.add(self.extra)
        vbox.pack_start(align, expand=False)

        self.size = gtk.Label()
        self.size.set_ellipsize(pango.ELLIPSIZE_END)
        align = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
        align.set_padding(5, 12, 0, 0)
        align.add(self.size)
        vbox.pack_start(align, expand=False)
        self.add(vbox)

        self.ostitle.set_markup('<b>%s</b>' % title)
        #self.set_tooltip_text(title)
        # Take up the space that would otherwise be used to create symmetry.
        self.extra.set_markup('<small>%s</small>' % (extra and extra or ' '))

    def set_size(self, size):
        size = format_size(size)
        self.size.set_markup('<span size="x-large">%s</span>' % size)

    def render_dots(self):
        # FIXME: Dots are rendered over the frame.
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 2)
        cr = cairo.Context(s)
        cr.set_source_rgb(*gtk_to_cairo_color('#c7c7c6'))
        #cr.set_source_rgb(*gtk_to_cairo_color('black'))
        cr.rectangle(1, 1, 1, 1)
        cr.fill()
        pattern = cairo.SurfacePattern(s)
        return pattern

    def paint_background(self, c):
        StylizedFrame.paint_background(self, c)
        x,y,w,h = self.allocation
        #c.save()
        #c.rectangle(x+10, y+10, w-20, h-20)
        #c.clip_preserve()
        w, h = self.allocation.width, self.allocation.height
        pattern = self.render_dots()
        pattern.set_extend(cairo.EXTEND_REPEAT)
        c.set_source(pattern)
        #c.paint()
        c.fill_preserve()

        g = cairo.RadialGradient(w/2, h/2, 0, w/2, h/2, w > h and w or h)
        g.add_color_stop_rgba(0.00, 1, 1, 1, 1)
        g.add_color_stop_rgba(0.25, 1, 1, 1, 0.75)
        g.add_color_stop_rgba(0.4, 1, 1, 1, 0)
        c.set_source(g)
        #c.paint()
        c.fill_preserve()
        #c.restore()

gobject.type_register(PartitionBox)

class StateBox(StylizedFrame):
    __gtype_name__ = 'StateBox'
    __gproperties__ = {
        'label'  : (gobject.TYPE_STRING,
                    'Label',
                    None,
                    'label', gobject.PARAM_READWRITE),
    }
    
    def do_get_property(self, prop):
        if prop.name == 'label':
            return self.label.get_text()
        return getattr(self, prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'label':
            self.label.set_text(value)
            return
        setattr(self, prop.name, value)
    
    def __init__(self, text=''):
        StylizedFrame.__init__(self)
        alignment = gtk.Alignment()
        alignment.set_padding(7, 7, 15, 15)
        hbox = gtk.HBox()
        hbox.set_spacing(10)
        self.image = gtk.Image()
        self.image.set_from_stock(gtk.STOCK_YES, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.label = gtk.Label(text)
        
        self.label.set_alignment(0, 0.5)
        hbox.pack_start(self.image, expand=False)
        hbox.pack_start(self.label)
        alignment.add(hbox)
        self.add(alignment)
        self.show_all()

        self.status = True

    def set_state(self, state):
        self.status = state
        if state:
            self.image.set_from_stock(gtk.STOCK_YES, gtk.ICON_SIZE_LARGE_TOOLBAR)
        else:
            self.image.set_from_stock(gtk.STOCK_NO, gtk.ICON_SIZE_LARGE_TOOLBAR)

    def get_state(self):
        return self.status

gobject.type_register(StateBox)

# TODO: Doesn't show correctly in Glade.
class LabelledEntry(gtk.Entry):
    __gtype_name__ = 'LabelledEntry'
    __gproperties__ = {
        'label'  : (gobject.TYPE_STRING,
                    'Label',
                    None,
                    'label', gobject.PARAM_READWRITE),
    }

    def do_get_property(self, prop):
        if prop.name == 'label':
            return self.get_label()
        return getattr(self, prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'label':
            self.set_label(value)
            return
        setattr(self, prop.name, value)

    def __init__(self, label=''):
        gtk.Entry.__init__(self)
        self.label = label
        self.inactive_color = self.style.fg[gtk.STATE_INSENSITIVE]

    def set_label(self, label):
        self.label = label or ''

    def get_label(self):
        return self.label

    def do_expose_event(self, event):
        gtk.Entry.do_expose_event(self, event)
        # Get the text_area.
        win = self.window.get_children()[0]
        if self.get_text() or self.is_focus():
            return
        gc = win.new_gc()
        layout = self.create_pango_layout('')
        # XXX don't use self.inactive_color for now as it's too dark.
        layout.set_markup('<span foreground="%s">%s</span>' %
            ('#b8b1a8', self.label))
        win.draw_layout(gc, 1, 1, layout)

gobject.type_register(LabelledEntry)

class LabelledComboBoxEntry(gtk.ComboBoxEntry):
    def __init__(self, model=None, column=-1):
        #gtk.ComboBoxEntry.__init__(self, model, column)
        gtk.ComboBox.__init__(self)
        l = LabelledEntry()
        l.set_label('herrow')
        l.show()
        self.add(l)
gobject.type_register(LabelledComboBoxEntry)

# FIXME: This doesn't work as is.
def expo(win):
    for w in win.get_children():
        expo(w)
    cr = win.cairo_create()
    cr.set_source_rgba(0,0,0,0.5)
    cr.rectangle(0, 0, *win.get_geometry()[2:4])
    cr.paint()
    
if __name__ == "__main__":
    options = ('that you have at least 3GB available drive space',
               'that you are plugged in to a power source',
               'that you are connected to the Internet with an ethernet cable')
    w = gtk.Window()
    w.connect('destroy', gtk.main_quit)
    a = gtk.VBox()
    a.set_spacing(5)
    a.set_border_width(20)
    
    # Prepare to install Ubuntu.
    space = StateBox(options[0])
    power = StateBox(options[1])
    inet = StateBox(options[2])
    for widget in (space, power, inet):
        a.pack_start(widget)

    # Partition resizing.
    existing_icon = gtk.image_new_from_icon_name('folder', gtk.ICON_SIZE_DIALOG)
    new_icon = gtk.image_new_from_icon_name('distributor-logo', gtk.ICON_SIZE_DIALOG)
    existing_part = PartitionBox('Files (20 MB)', '', existing_icon)
    new_part = PartitionBox('Ubuntu 10.10', '/dev/sda2 (btrfs)', new_icon)
    hb = ResizeWidget(1024 * 1024 * 100, 1024 * 1024 * 20, 1024 * 1024 * 80, existing_part, new_part)
    a.pack_start(hb)
    button = gtk.Button('Install')
    def func(*args):
        print 'Size:', hb.get_size()
    button.connect('clicked', func)
    a.pack_start(button)

    le = LabelledEntry('A labelled entry')
    a.pack_start(le)

    lcbe = LabelledComboBoxEntry()
    a.pack_start(lcbe)

    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    upower = bus.get_object('org.freedesktop.UPower', '/org/freedesktop/UPower')
    upower = dbus.Interface(upower, 'org.freedesktop.DBus.Properties')
    def power_state_changed():
        power.set_state(upower.Get('/org/freedesktop/UPower', 'OnBattery') == False)
    bus.add_signal_receiver(power_state_changed, 'Changed', 'org.freedesktop.UPower', 'org.freedesktop.UPower')
    power_state_changed()
    
    #w2 = gtk.Window()
    #w2.set_transient_for(w)
    #w2.set_modal(True)
    #w2.show()
    w.add(a)
    w.show_all()
    #w.connect_after('expose-event', lambda w, e: expo(w.window))
    gtk.main()

# TODO: Process layered on top of os-prober (or function) that:
#       - Calls os-prober to find the OS name.
#       - If the above fails, gives us the free space on a partition by
#         mounting it read-only in a separate kernel space.

# TODO: We should be able to construct any widget without passing parameters to
# its constructor.

# TODO: We need a LabelledComboBoxEntry for the timezone page.

# TODO: Bring in the timezone_map, but keep it in a separate file and make it
# so the tz database can be None, in which case it just prints the map
# background.  Give it its own gdk.window or EventBox.
