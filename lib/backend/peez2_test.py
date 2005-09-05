#!/usr/bin/python
# -*- coding: utf-8 -*-

# File "peez2_test.py".
# Testing the "peez2" library.
# Created by Antonio Olmo <aolmo@emergya.info> on 29 august 2005.
# Last modified on 5 sep 2005.

from peez2 import *

# Step 1: retrieve the list of drives.
drives = get_drives ()

for i in drives:
    print '%i\t%s\t%i\t%s' % (i ['no'], i ['name'], i ['size'], i ['device'])

# Optional step: retrieve info about the selected drive.
for i in drives:
    info = get_info (i ['device'])

    print info ['prim']
    print info ['ext']
    print info ['logic']
    print info ['free']
    print info ['linux']
    print info ['win']

    for j in info ['status']:
        print j

    if info.has_key ('warn'):

        for j in info ['warn']:
            print j

# Step 2: retrieve the list of suggested actions to perform.
actions = suggest_actions ('/dev/hda')

if None != actions:

    for i in actions.keys ():
        print i, actions [i] [0], actions [i] [1]

print 'Enter selected option: '
option = raw_input ().strip ()

while not option.isdigit ():
    print 'Not valid. Enter again: '
    option = raw_input ().strip ()

# Step 3: retrieve the list of suggested actions to perform.
print get_commands ('/dev/hda', int (option))
print 'Fin de la prueba'

# End of file.

