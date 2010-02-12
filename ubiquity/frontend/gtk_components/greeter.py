#! /usr/bin/python

import sys
import optparse

import glib
import gtk
import rsvg

return_value = 0
options = None
svg = None
window = None
image = None
button1 = None
button2 = None
fixed = None

def recompute_button_positions():
    if button1:
        requisition = button1.get_child_requisition()
        x = window.allocation.width / 4 - requisition[0] / 2
        y = window.allocation.height * options.button1_height
        if button1.allocation.x != x or button1.allocation.y != y:
            fixed.move(button1, int(x), int(y))

    if button2:
        requisition = button2.get_child_requisition()
        x = window.allocation.width * 3 / 4 - requisition[0] / 2
        y = window.allocation.height * options.button2_height
        if button2.allocation.x != x or button2.allocation.y != y:
            fixed.move(button2, int(x), int(y))

    return False

def button_mapped(button):
    glib.timeout_add(100, recompute_button_positions)

def button1_clicked(button):
    global return_value
    return_value = 1
    gtk.main_quit()

def button2_clicked(button):
    global return_value
    return_value = 2
    gtk.main_quit()

def fixed_size_allocate(widget, allocation):
    glib.timeout_add(100, recompute_button_positions)

def window_size_allocate(widget, allocation):
    global image, button1, button2

    pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
        options.filename, allocation.width, allocation.height)

    if image is None:
        image = gtk.image_new_from_pixbuf(pixbuf)
        image.show()
        fixed.put(image, 0, 0)

        button1 = gtk.Button(label="Try Ubuntu")
        button1.connect('clicked', button1_clicked)
        button1.connect('map', button_mapped)
        fixed.put(button1, 0, 0)
        button1.show()

        button2 = gtk.Button(label="Install Ubuntu")
        button2.connect('clicked', button2_clicked)
        button2.connect('map', button_mapped)
        fixed.put(button2, 0, 0)
        button2.show()

def main():
    global options, svg, window, fixed

    usage = '%prog [options]'
    parser = optparse.OptionParser(usage=usage)
    parser.set_defaults(
        filename="test.svg",
        button1_height=0.5,
        button2_height=0.5)
    parser.add_option('-f', '--filename', help='Filename for SVG image')
    parser.add_option('-1', '--button1-y', type='float',
                      help='Button 1 height ratio')
    parser.add_option('-2', '--button2-y', type='float',
                      help='Button 2 height ratio')
    options, args = parser.parse_args()

    svg = rsvg.Handle(file=options.filename)

    window = gtk.Window()
    window.set_title("Welcome to Ubuntu!")

    fixed = gtk.Fixed()
    window.add(fixed)

    window.connect('size-allocate', window_size_allocate)
    fixed.connect('size-allocate', fixed_size_allocate)
    window.connect('delete-event', gtk.main_quit)

    # window.fullscreen()
    window.set_size_request(1280, 1024)

    window.show_all()

    gtk.main()

    return return_value

if __name__ == '__main__':
    sys.exit(main())
