# -*- coding: utf-8 -*-

# «peez2» - particionamiento automático a través de la herramienta «Peez2»
# 
# Copyright (C) 2005 Junta de Andalucía
# 
# Autor/es (Author/s):
# 
# - Antonio Olmo Titos <aolmo#emergya._info>
# 
# Este fichero es parte del instalador en directo de Guadalinex 2005.
# 
# El instalador en directo de Guadalinex 2005 es software libre. Puede
# redistribuirlo y/o modificarlo bajo los términos de la Licencia Pública
# General de GNU según es publicada por la Free Software Foundation, bien de la
# versión 2 de dicha Licencia o bien (según su elección) de cualquier versión
# posterior. 
# 
# El instalador en directo de Guadalinex 2005 se distribuye con la esperanza de
# que sea útil, pero SIN NINGUNA GARANTÍA, incluso sin la garantía MERCANTIL
# implícita o sin garantizar la CONVENIENCIA PARA UN PROPÓSITO PARTICULAR. Véase
# la Licencia Pública General de GNU para más detalles.
# 
# Debería haber recibido una copia de la Licencia Pública General junto con el
# instalador en directo de Guadalinex 2005. Si no ha sido así, escriba a la Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
# USA.
# 
# -------------------------------------------------------------------------
# 
# This file is part of Guadalinex 2005 live installer.
# 
# Guadalinex 2005 live installer is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License, or
# at your option) any later version.
# 
# Guadalinex 2005 live installer is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# Guadalinex 2005 live installer; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

""" U{pylint<http://logilab.org/projects/pylint>} mark: 8.87 """

# File "peez2.py".
# Automatic partitioning with "peez2".
# Created by Antonio Olmo <aolmo#emergya._info> on 25 aug 2005.
# Last modified on 17 oct 2005.

# TODO: improve debug and log system.

# Index:
# class Peez2:
# def beautify_size (size):
# def beautify_device (device, locale):

from sys         import stderr
from locale      import getdefaultlocale
from popen2      import Popen3
from gtk         import ProgressBar
from string      import lower
from ue.settings import *

class Peez2:

    """ Encapsulates a sequence of operations with I{Peez2} partition
        assistant. The partition scheme is expressed in MB (1024 Bytes).

        Data structures about three different drives follow. The first one is
        a hard drive::

            {'device': '/dev/hda',
             'info':   {'status':   ['STATUS #FRE|FRC|CLN|JLOG|LIN|WIN|FUL|UNP|UNK',
                                     'VALUE  # 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0'],
                        'oks':      [['FREESPACE\\n']],
                        'prim':     '3 + 0 (3)',
                        'win':      0,
                        'free':     1,
                        'ext':      0,
                        'metacoms': ['4\\n',
                                     '5',
                                     '6',
                                     '7'],
                        'linux':    1,
                        'details':  [{'fs':    'ext3',
                                      'no':    '1',
                                      'bytes': 2146765824,
                                      'sec':   '63sec - 4192964sec',
                                      'type':  '0x0:Particion Primaria     ',
                                      'class': 'Type Generic Linux\\n'},
                                     {'fs':    'NOSF',
                                      'no':    '2',
                                      'bytes': 2146798080,
                                      'sec':   '4192965sec - 8385929sec',
                                      'type':  '0x0:Particion Primaria     ',
                                      'class': 'PAV#3'}]},
             'label':  'ST340014A',
             'size':   40020664320L,
             'no':     0}

        This one is a CD-ROM drive::

            {'device': '/dev/hdc',
             'info':   {'warn':   ['Disco vacio sin tabla e particiones o disco no reconocido',
                                   'UNKNOW LAYOUT'],
                        'status': ['STATUS #FRE|FRC|CLN|JLOG|LIN|WIN|FUL|UNP|UNK',
                                   'VALUE  # 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0'],
                        'opts':   [['1',
                                    'CR',
                                    'Nueva partici\xc3\xb3n. Ocupar todo el espacio \\n'],
                                   ['2',
                                    'CR',
                                    'Nueva partici\xc3\xb3n. Dejar espacio libre \\n']]},
             'label':  'HL-DT-STDVD-ROM GDR8163B',
             'size':   575959040,
             'no':     1}

        This is only an example for testing purposes::

            {'device': '/dev/strange',
             'info':   {},
             'size':   1200000000,
             'no':     -1,
             'label':  'FOR DEBUGGING PURPOSES ONLY'}

        """


    # Initialization _________________________________________________________

    def __init__ (self, binary = 'peez2', common_arguments = '2> /dev/null',
                  debug = DEBUGGING_STATUS,
                  partition_scheme = MINIMAL_PARTITION_SCHEME):

        """ Detect locale and scan for drives. """

        self.__binary = binary
        self.__common_arguments = common_arguments
        self.__debug = debug
        self.__partition_scheme = partition_scheme
        self.__locale = getdefaultlocale () [0]
        self.__drives = self.__scan_drives ()

        # Disable this attribute when auto-partitioning is mature enough:
        self.__ONLY_MANUALLY = False

        # Every partitioning command executed will be also written here:
        p = Popen3 ('rm /tmp/guadalinex-express.commands')
        p.wait ()

    # Public method "get_drives" _____________________________________________

    def get_drives (self):

        """ Retrieve a list of drives. Each unit is identified by its device
            name (i.e. C{/dev/hda}) and has an associated human-readable label
            (i.e. I{75 GB, maestro en el bus primario (/dev/hda),
            "ST380011A"}). """

        result = []

        for i in self.__drives:

##             if self.__debug:
##                 stderr.write ('get_drives: drive follows.\n' + str (i) + '\n')

            pretty_device = beautify_device (i ['device'], self.__locale)
            pretty_size = beautify_size (i ['size'])
            label = '%s, %s, "%s"' % (pretty_size, pretty_device, i ['label'])

            # We are not using a more compact construct below to explicit that
            #     the same 3 partitions, in the same order, are always used:
            required_MB = sum (self.__partition_scheme.values ())

            if i ['size'] >= required_MB * 1024 * 1024:
                enough = True
            else:
                enough = False

            associations = None

            if i ['info'].has_key ('details'):
                linux_parts = 0
                linux_space = []
                linux_names = []

                for j in i ['info'] ['details']:

##                     if self.__debug:
##                         stderr.write ('get_drives: drive details follows.\n' +
##                                       str (j) + '\n')

                    if 'linux' in j ['class'].lower () or \
                           'swap' in j ['class'].lower () or \
                           'nofs' in j ['class'].lower () or \
                           'linux' in j ['fs'].lower () or \
                           'swap' in j ['fs'].lower () or \
                           'ext2' in j ['fs'].lower () or \
                           'ext3' in j ['fs'].lower ():
                        linux_space.append (int (j ['bytes']))
                        linux_names.append (i ['device'] + j ['no'])

                if len (linux_space) > 1:
                    associations = {}
                    linux_space.sort ()
                    parts = self.__partition_scheme

                    if len (linux_space) is 2:
                        required = [parts ['root'], parts ['home']]
                        mountpoints = ['root', 'home']
                    else:
                        required = parts.values ()
                        mountpoints = parts.keys ()

                    # During formatting and copying, "root" is known as "/",
                    # and "home" is known as "/home", so it is necessary to
                    # change them before passing mount point associations to
                    # the backend:

                    j = 0

                    while j < len (mountpoints):

                        if 'root' == mountpoints [j].lower ():
                            mountpoints [j] = '/'
                        elif 'home' == mountpoints [j].lower ():
                            mountpoints [j] = '/home'

                        j = j + 1

                    required_bytes = [j * 1024 * 1024 for j in required]
                    required_bytes.sort ()
                    l = 0
                    r = 0

                    while r < len (required_bytes) and l < len (linux_space):

                        if linux_space [l] >= required_bytes [r]:
                            associations [linux_names [l]] = mountpoints [r]
                            r = r + 1

                        l = l + 1

                    if r < len (required_bytes):
                        associations = None

            item = {'id':           str (i ['device']),
                    'label':        label,
                    'info':         i ['info'],
                    'large_enough': enough,
                    'linux_before': associations}
            result.append (item)

        return result

    # Public method "only_manually" __________________________________________

    def only_manually (self):

        """ Decide if manual partitioning should be the only way
            available. """

        return self.__ONLY_MANUALLY

    # Private method "__scan_drives" _________________________________________

    def __scan_drives (self):

        """ Retrieve the list of drives in the computer. Devices B{not}
            beginning with C{/dev/hd} or C{/dev/sd} are ignored. """

        result = []

        lines = self.__call_peez2 () ['out']

        for i in lines:

            if 'LD#' == i [:3]:
                fields = i [3:].split ('|')

                if 'es' == self.__locale [:2]:
                    drive = {}

                    for j in fields:

                        if 'Medio:' == j [:6]:
                            drive ['no'] = int (j [6:])
                        elif 'Modelo:' == j [:7]:
                            drive ['label'] = j [7:]
                        elif 'Ruta:' == j [:5]:
                            drive ['device'] = j [5:]
                        elif 'Total:' == j [:6]:
                            drive ['size'] = int (j [6:])

                    if '/dev/hd' == drive ['device'] [:7] or \
                       '/dev/sd' == drive ['device'] [:7]:
                        extended_info = self.__get_info (drive ['device'])
                        drive ['info'] = extended_info
                        result.append (drive)
                    else:

                        if self.__debug:
                            stderr.write ('__scan_drives: drive "' +
                                          drive ['device'] + '" ignored.\n')
                        
                elif 'en' == self.__locale [:2]:
                    drive = {}

                    for j in fields:

                        if 'Media:' == j [:6]:
                            drive ['no'] = int (j [6:])
                        elif 'Model:' == j [:6]:
                            drive ['label'] = j [6:]
                        elif 'Path:' == j [:5]:
                            drive ['device'] = j [5:]
                        elif 'Total:' == j [:6]:
                            drive ['size'] = int (j [6:])

                    if '/dev/hd' == drive ['device'] [:7] or \
                       '/dev/sd' == drive ['device'] [:7]:
                        result.append (drive)
                        extended_info = self.__get_info (drive ['device'])
                        drive ['info'] = extended_info
                        result.append (drive)
                    else:

                        if self.__debug:
                            stderr.write ('__scan_drives: drive "' +
                                          drive ['device'] + '" ignored.\n')
                        
                else:

                    if self.__debug:
                        stderr.write ('__scan_drives: locale: "' +
                                      self.__locale + '" is wrong.\n')

        return result

    # Private method "__get_info" ____________________________________________

    def __get_info (self, drive, size = None, more_args = '', input = None):

        """ Retrieve information about a C{drive}. If a C{size} (in MB) is
            given, then options to get this space are parsed as well. It is
            also possible to specify some additional arguments (like C{-j} or
            C{-x}). C{input} may be a string that will be piped into
            I{Peez2}. """

        result = None

        # We are not using a more compact construct below to reflect that the
        # same 3 partitions are always used, and in the same order:
        parts = self.__partition_scheme

        if '' != more_args:
            more_args = more_args + ' '

        more_args = more_args + '-v '

        if None != size:

            if None == input:
                lines = self.__call_peez2 ('-a wizard %s-d %s -m %i -M %i' %
                                           (more_args, drive, size, size))['out']
            else:
                lines = self.__call_peez2 ('-a wizard %s-d %s -m %i -M %i' %
                                           (more_args, drive, size, size),
                                           input)['out']

        else:

            if None == input:
                lines = self.__call_peez2 ('-a validate %s-d %s -s %i:%i:%i' %
                                           (more_args, drive, parts ['swap'],
                                            parts ['root'],
                                            parts ['home'])) ['out']
            else:
                lines = self.__call_peez2 ('-a validate %s-d %s -s %i:%i:%i' %
                                           (more_args, drive, parts ['swap'],
                                            parts ['root'], parts ['home']),
                                           input) ['out']

        after_menu = False

        for i in lines:

            # This case temporarily solves last "Peez2" bug:
            if i.startswith ('Please select a choice:') or \
               i.startswith ('Por favor, seleccione una opc'):
                after_menu = True
            # "Aviso":
            elif 'AA#' == i [:3]:

                if None == result:
                    result = {}

                if not result.has_key ('warn'):
                    result ['warn'] = []

                result ['warn'].append (i [3:-1])
            # "información varia":
            elif 'VV#' == i [:3]:

                if None == result:
                    result = {}

                if 'es' == self.__locale [:2]:

                    if 'Particiones primarias totales:' == i [3:33]:
                        result ['prim'] = i [33:-1].strip ()
                    elif 'Particiones extendidas:' == i [3:26]:
                        result ['ext'] = int (i [26:])
                    elif 'Particiones l' == i [3:16] and 'gicas:' == i [17:23]:
                        result ['logic'] = int (i [23:])
                    elif 'Espacios libres:' == i [3:19]:
                        result ['free'] = int (i [19:])
                    elif 'Particiones de linux:' == i [3:24]:
                        result ['linux'] = int (i [24:])
                    elif 'Particiones de Windows(TM):' == i [3:30]:
                        result ['win'] = int (i [30:])
                    elif 'Disk Status#' == i [3:15]:

                        if not result.has_key ('status'):
                            result ['status'] = []

                        (result ['status']).append (i [15:-1])

                elif 'en' == self.__locale [:2]:

                    if 'Total primary partitions:' == i [3:28]:
                        result ['prim'] = i [28:-1]
                    elif 'Total extended partitions:' == i [3:29]:
                        result ['ext'] = int (i [29:])
                    elif 'Total logical partitions:' == i [3:28]:
                        result ['logic'] = int (i [28:])
                    elif 'Total free spaces:' == i [3:21]:
                        result ['free'] = int (i [21:])
                    elif 'Total linux partitions:' == i [3:26]:
                        result ['linux'] = int (i [26:])
                    elif 'Total win partitions:' == i [3:24]:
                        result ['win'] = int (i [24:])
                    elif 'Disk Status#' == i [3:15]:

                        if not result.has_key ('status'):
                            result ['status'] = []

                        (result ['status']).append (i [15:-1])

            # "Listado de particiones":
            elif 'LP#' == i [:3]:
                fields = i [3:].split ('#')

                if None == result:
                    result = {}

                if not result.has_key ('parts'):
                    result ['parts'] = []

                this_part = {'name': fields [0]}

                if 'es' == self.__locale [:2]:

                    for j in fields [1:]:

                        if 'GAINED:' == j [:7]:
                            this_part ['gained'] = int (j [7:].strip ())
                        elif 'SIZE:' == j [:5]:
                            this_part ['size'] = int (j [5:].strip ())
                        elif 'FS:' == j [:3]:
                            this_part ['fs'] = j [3:].strip ()
                        elif 'TYPE:' == j [:5]:
                            this_part ['type'] = j [5:].strip ()

                elif 'en' == self.__locale [:2]:

                    for j in fields [1:]:

                        if 'GAINED:' == j [:7]:
                            this_part ['gained'] = int (j [7:].strip ())
                        elif 'SIZE:' == j [:5]:
                            this_part ['size'] = int (j [5:].strip ())
                        elif 'FS:' == j [:3]:
                            this_part ['fs'] = j [3:].strip ()
                        elif 'TYPE:' == j [:5]:
                            this_part ['type'] = j [5:].strip ()

                result ['parts'].append (this_part)
            # "Opción":
            elif 'OO#' == i [:3]:
                fields = i [3:].split ('#')

                if None == result:
                    result = {}

                if not result.has_key ('opts'):
                    result ['opts'] = []

                result ['opts'].append (fields)
            # "Acción 'validate' exitosa":
            elif 'OK#' == i [:3]:
                fields = i [3:].split ('#')

                if None == result:
                    result = {}

                if not result.has_key ('oks'):
                    result ['oks'] = []

                result ['oks'].append (fields)
            elif 'CC#' == i [:3] and after_menu:
                fields = i [3:].split ('#')

                if None == result:
                    result = {}

                if not result.has_key ('commands'):
                    result ['commands'] = []

                result ['commands'].append (fields [1])
            elif 'MC#' == i [:3]:
                fields = i [3:].split ('#')

                if None == result:
                    result = {}

                if not result.has_key ('metacoms'):
                    result ['metacoms'] = []

                result ['metacoms'].append (fields [1])
            elif 'OD#' == i [:3]:

                if None == result:
                    result = {}

                if not result.has_key ('dest'):
                    result ['dest'] = i [3:]

        lines = self.__call_peez2 ('-a show -d %s -v' % drive) ['out']
        string_of_lines = ''

        for i in lines:
            string_of_lines = string_of_lines + i

        string_of_lines = string_of_lines.split ('\n')

        for i in string_of_lines:

            # "registro de 'lista de particiones'":
            if 'PAV' == i [:3] or 'PAH' == i [:3]:

                # This patch temporarily solves Peez2 output bug:
                # TODO: remove this patch?
                next = i [3:].find ('PAV')
                other_next = i [3:].find ('PAH')

                if other_next < next and other_next > -1:
                    next = other_next

                if next > -1:
                    string_of_lines.append (i [3:] [next:])
                    this_one = i [4:] [:next]
                else:
                    this_one = i [4:]

                if 'PAV#' == i [:4]:

                    fields = this_one.split ('|')

                    if None == result:
                        result = {}

                    if not result.has_key ('details'):
                        result ['details'] = []

                    this_part = {'no':    fields [0],
                                 'type':  fields [1],
                                 'fs':    fields [2],
                                 'sec':   fields [3],
                                 'bytes': int (fields [4]),
                                 'class': fields [5]}
                    result ['details'].append (this_part)

##         if self.__debug and result.has_key ('details'):
##             stderr.write ('__get_info: details "' + \
##                           str (result ['details']) + '"\n')

        return result

    # Public method "auto_partition" _________________________________________

    def auto_partition (self, drive, progress_bar = None,
                        do_it = ACTUAL_PARTITIONING):

        """ Make 3 partitions automatically on the specified C{device}. When
            C{progress_bar} is not C{None}, it is updated dinamically as the
            partitioning process goes on. """

        result = None

        if None != progress_bar:
            progress_bar.pulse ()
            progress_bar.set_text ('Planning partition...')

        if drive.has_key ('info'):

            if drive ['info'].has_key ('primary'):

                if drive ['info'] ['primary'] < 2:
                    # Make 3 new primary partitions?
                    pass

            components = self.__partition_scheme.keys ()
            extended = 0

            for part in components:
                required = self.__partition_scheme [part]

                if None != progress_bar:
                    progress_bar.pulse ()
                    progress_bar.set_text ('Making %i MB partition...' % required)

                if extended > 1:
                    stderr.write ('-- 1 --\n')
                    info = self.__get_info (drive ['id'], required, '-j')
                elif drive.has_key ('info'):
                    stderr.write ('-- 2 --\n')

                    if drive ['info'].has_key ('ext'):

                        if drive ['info'] ['ext'] > 0:
                            extended = 2
                            info = self.__get_info (drive ['id'], required, '-j')

                if extended < 1:
                    stderr.write ('-- 3 --\n')
                    # It is necessary to create an extended partition
                    # (with 10% more space):
                    required = int (sum (self.__partition_scheme.values ()) * 1.1)
                    info = self.__get_info (drive ['id'], required, '-x')
                    components.append (part)
                    extended = extended + 1

                # Now we have to decide which option is better:
                try:
                    options = info ['opts']

                    stderr.write (str (options) + '\n')

                except:

                    if self.__debug:
                        stderr.write ('auto_partition: info contains "' +
                                      str (info) + '".\n')

                what = -1
                i = 1

                while -1 == what and i <= len (options):

                    if 'CR' == options [i - 1] [1] [:2]:
                        what = i

                    i = i + 1

                i = 1

                while -1 == what and i <= len (options):

                    if 'RE' == options [i - 1] [1] [:2]:
                        what = i

                    i = i + 1

                if -1 != what:

                    if info.has_key ('commands'):
                        stderr.write ('========= ' + str (info ['commands']) + '\n\n')
                    
                    if extended < 2:
                        info = self.__get_info (drive ['id'], required,
                                                '-x -i', str (what) + '\n')
                        extended = extended + 1
                    else:
                        info = self.__get_info (drive ['id'], required,
                                                '-j -i', str (what) + '\n')

                    if info.has_key ('commands'):
                        stderr.write ('========= ' + str (info ['commands']) + '\n\n')

                    if info.has_key ('commands'):
                        c = info ['commands']

                        stderr.write ('--> c --> ' + str (c) + '\n')

                    if self.__debug:
                        p = Popen3 ('echo "Creando ' + str (part) +
                                '..." >> /tmp/guadalinex-express.commands')
                        p.wait ()

                    for i in c:

                        # Print the commands:
                        if self.__debug:
                            stderr.write ('auto_partition: command: "' +
                                          i.strip () + '" executed.\n')
                            p = Popen3 ('echo "' + i.strip () +
                                    '" >> /tmp/guadalinex-express.commands')
                            p.wait ()

                        if do_it:
                            # Do it! Execute commands to make partitions!
                            p = Popen3 (i)
                            p.wait ()
                            # Let the system be aware of the change:
                            p = Popen3 ('sleep 5')
                            p.wait ()

                    if info.has_key ('metacoms'):
                        mc = info ['metacoms']

                        for i in mc:

                            if self.__debug:
                                stderr.write ('# ' + i)

                    if info.has_key ('dest') and extended is not 2:

                        if result is None:
                            result = {}

                        result [info ['dest']] = part.strip ()

                        if self.__debug:
                            stderr.write (str (part.strip ()) + \
                                          ' added as ' + \
                                          str (info ['dest']) + '\n')
                    else:
                        extended = extended + 1

        return result

    # Private method "__call_peez2" __________________________________________

    def __call_peez2 (self, args = '', input = ''):

        """ Execute I{peez2} with arguments provided, if any. It is also
            possible to specify an input. """

        command = self.__binary + ' ' + args + ' ' + self.__common_arguments

        if '' != input:
            command = 'echo -e "' + input + '" | ' + command

        if self.__debug:
            stderr.write ('__call_peez2: command "' + command + '" executed.\n')

        child = Popen3 (command, False, 1048576)
#        child.wait ()

        return {'out': child.fromchild,
                'in':  child.tochild,
                'err': child.childerr}

# Function "beautify_size" ___________________________________________________

def beautify_size (size):

    """ Format the size of a drive into a friendly string, i.e. C{64424509440}
        will produce I{60 GB}. """

    result = None

    try:
        bytes = int (size)
    except:
        bytes = -1

    if bytes >= 1024 * 1024 * 1024:
        result = '%i GB' % int (round (bytes / float (1024 * 1024 * 1024)))
    elif bytes >= 1024 * 1024:
        result = '%i MB' % int (round (bytes / float (1024 * 1024)))
    elif bytes >= 1024:
        result = '%i KB' % int (round (bytes / float (1024)))
    elif bytes >= 0:
        result = '%i B' % bytes

    return result

# Function "beautify_device" _________________________________________________

def beautify_device (device, locale):

    """ Format the name of a device to make it more readable, i.e. C{/dev/hdb}
        will produce I{primary slave (/dev/hdb)} or I{esclavo en el bus
        primario (dev/hdb)}, depending on the I{locale}. """

    result = None

    try:
        name = str (device).strip ()
        lang = str (locale) [:2]
    except:
        name = ''

    if '' != name:

        if '/dev/hda' == name:

            if 'es' == lang:
                result = 'maestro en el bus primario (' + name + ')'
            elif 'en' == lang:
                result = 'primary master (' + name + ')'

        elif '/dev/hdb' == name:

            if 'es' == lang:
                result = 'esclavo en el bus primario (' + name + ')'
            elif 'en' == lang:
                result = 'primary slave (' + name + ')'

        elif '/dev/hdc' == name:

            if 'es' == lang:
                result = 'maestro en el bus secundario (' + name + ')'
            elif 'en' == lang:
                result = 'secondary master (' + name + ')'

        elif '/dev/hdd' == name:

            if 'es' == lang:
                result = 'maestro en el bus secundario (' + name + ')'
            elif 'en' == lang:
                result = 'secondary slave (' + name + ')'

        if None == result:
            result = name

    return result

# End of file.

