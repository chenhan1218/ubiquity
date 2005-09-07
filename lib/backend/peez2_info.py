#!/usr/bin/python
# -*- coding: utf-8 -*-

# File "peez2_info.py".
# Showing all info about current system with "peez2" library.
# Created by Antonio Olmo <aolmo@emergya.info> on 7 sep 2005.

from sys import stdout, stderr
from peez2 import *

print '\n1. Unidades de disco:'
drives = get_drives ()

for i in drives:
    print '\t#%i ("%s"), de %s, %s.' % \
          (i ['no'], i ['name'], \
           beautify_size (i ['size']), beautify_device (i ['device']))

print '\n2. Info sobre cada unidad:'

for i in drives:
    info = get_info (i ['device'])
    print ('\t#%i %s, %i, %i, %i, %i, %i' % (i ['no'], info ['prim'], info ['ext'],
                                         info ['logic'], info ['free'],
                                         info ['linux'], info ['win']))

    for j in info ['status']:
        print '\t   ' + j

    if info.has_key ('warn'):

        for j in info ['warn']:
            print '\t   ' + j

    if info.has_key ('parts'):

        for j in info ['parts']:
            print '\t   %s, %i, %i, %i' % (j ['name'], j ['gained'],
                                           j ['size'], j ['fs'], j ['type'])

print ''

actions = suggest_actions ('/dev/hda')

if None != actions:

    for i in actions.keys ():
        print i, actions [i] [0], actions [i] [1]

# stdout.write ('Enter selected option: ')
# option = raw_input ().strip ()

# while not option.isdigit ():
#     stdout.write ('Not valid. Enter again: ')
#     option = raw_input ().strip ()

# # Step 3: retrieve the list of suggested actions to perform.
# print get_commands ('/dev/hda', int (option))
# print 'Fin de la prueba'

# End of file.

