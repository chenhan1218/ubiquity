#!/usr/bin/python
# -*- coding: utf-8 -*-

# File "peez2_test.py".
# Testing the "peez2" library.
# Created by Antonio Olmo <aolmo@emergya.info> on 29 aug 2005.
# Last modified on 8 sep 2005.

from sys import stdout, stderr, exit
from peez2 import *

peez2 = Peez2 ()
print peez2.locale, type (peez2.locale)
print peez2.drives, type (peez2.drives)

parts = partition_scheme.split (':')
stdout.write ('Numero de particiones deseadas: %i\nTamanos: ' % len (parts))

for i in parts:
    stdout.write ('%i ' % int (i))

print ''

# Step 1: select one drive, in case there are many:
drives = get_drives ()

if len (drives) > 1:

    for i in drives:
        print '#%i ("%s"), de %s, %s.' % \
              (i ['no'], i ['name'], \
               beautify_size (i ['size']), beautify_device (i ['device']))

    stdout.write ('Seleccionar unidad: ')
    option = raw_input ().strip ()

    while not option.isdigit ():
        print 'No es válida. Indicar otra vez: '
        option = raw_input ().strip ()

    unidad = ''

    for i in drives:

        if int (option) == i ['name']:
            unidad = i ['device']

elif 1 == len (drives):
    print 'Unidad seleccionada automaticamente: #%i ("%s"), de %s, %s.' % \
          (drives [0] ['no'], drives [0] ['name'], \
           beautify_size (drives [0] ['size']), \
           beautify_device (drives [0] ['device']))
else:
    exit ('No se ha encontrado ninguna unidad de disco.')

# # Optional step: retrieve info about the selected drive.
# for i in drives:
#     info = get_info (i ['device'])

#     print info ['prim']
#     print info ['ext']
#     print info ['logic']
#     print info ['free']
#     print info ['linux']
#     print info ['win']

#     for j in info ['status']:
#         print j

#     if info.has_key ('warn'):

#         for j in info ['warn']:
#             print j

# Step 2: retrieve the list of suggested actions to perform.
actions = suggest_actions ('/dev/hda')

if None != actions:

    for i in actions.keys ():
        print i, actions [i] [0], actions [i] [1]

stdout.write ('Enter selected option: ')
option = raw_input ().strip ()

while not option.isdigit ():
    stdout.write ('Not valid. Enter again: ')
    option = raw_input ().strip ()

# Step 3: retrieve the list of suggested actions to perform.
print get_commands ('/dev/hda', int (option))
print 'Fin de la prueba'

# End of file.

