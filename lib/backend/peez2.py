# -*- coding: utf-8 -*-

""" U{pylint<http://logilab.org/projects/pylint>} mark: 9.55 """

# File "peez2.py".
# Automatic partitioning with "peez2".
# Created by Antonio Olmo <aolmo@emergya.info> on 25 aug 2005.
# Last modified on 13 sep 2005.

# TODO: improve debug and log system.

from sys    import stderr
from locale import getdefaultlocale
from popen2 import Popen3

debug = True
binary = 'peez2'
common_arguments = '2> /dev/null'
partition_scheme = '256:1536:512'        # A conservative scheme.
# partition_scheme = '1024:20480:30720'    # A more realistic scheme.

class Peez2:

    """ """

    def __init__ (self):

        """ """

        self.locale = getdefaultlocale () [0]
        self.drives = [{'device': '/dev/hdb',
                        'label':  'DEBUGGING - JUST A TEST',
                        'size':   '75 GB'},
                       {'device': '/dev/sda',
                        'label':  'DEBUGGING - JUST A TEST',
                        'size':   '13 GB'},]
        print self.scan_drives ()

    def get_drives (self):

        """ """

        return self.drives

    def scan_drives (self):

        """ Retrieve the list of drives in the computer. """

        result = []

        lines = call_peez2 () ['out']

        for i in lines:

            if 'LD#' == i [:3]:
                fields = i [3:].split ('|')

                if 'es' == self.locale [:2]:
                    drive = {}

                    for j in fields:

                        if 'Medio:' == j [:6]:
                            drive ['no'] = int (j [6:])
                        elif 'Modelo:' == j [:7]:
                            drive ['name'] = j [7:]
                        elif 'Ruta:' == j [:5]:
                            drive ['device'] = j [5:]
                        elif 'Total:' == j [:6]:
                            drive ['size'] = int (j [6:])

                    result.append (drive)
                elif 'en' == self.locale [:2]:
                    drive = {}

                    for j in fields:

                        if 'Media:' == j [:6]:
                            drive ['no'] = int (j [6:])
                        elif 'Model:' == j [:6]:
                            drive ['name'] = j [6:]
                        elif 'Path:' == j [:5]:
                            drive ['device'] = j [5:]
                        elif 'Total:' == j [:6]:
                            drive ['size'] = int (j [6:])

                    result.append (drive)

        return result

# Function "system_analysis" _________________________________________________

def system_analysis ():

    """ """

    result = None

    # TODO

    return result

# Function "get_info" ________________________________________________________

def get_info (drive):

    """ Retrieve information about a drive. """

    result = None

    lines = call_peez2 ('-d ' + drive) ['out']

    for i in lines:

        if 'AA#' == i [:3]:

            if None == result:
                result = {}

            if not result.has_key ('warn'):
                result ['warn'] = []

            result ['warn'].append (i [3:-1])
        elif 'VV#' == i [:3]:

            if None == result:
                result = {}

            if 'es' == self.locale [:2]:

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

            elif 'en' == self.locale [:2]:

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

        elif 'LP#' == i [:3]:
            fields = i [3:].split ('#')

            if None == result:
                result = {}

            if not result.has_key ('parts'):
                result ['parts'] = []

            this_part = {'name': fields [0]}

            if 'es' == self.locale [:2]:

                for j in fields [1:]:

                    if 'GAINED:' == j [:7]:
                        this_part ['gained'] = int (j [7:].strip ())
                    elif 'SIZE:' == j [:5]:
                        this_part ['size'] = int (j [5:].strip ())
                    elif 'FS:' == j [:3]:
                        this_part ['fs'] = j [3:].strip ()
                    elif 'TYPE:' == j [:5]:
                        this_part ['type'] = j [5:].strip ()

            elif 'en' == self.locale [:2]:

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

    return result

# Function "suggest_actions" _________________________________________________

def suggest_actions (drive):

    """ Get all the possibilities proposed by "peez2", if any. """

    result = None

    lines = call_peez2 ('-a validate -d ' + drive + ' -s ' +
                        partition_scheme) ['out']

    for i in lines:

        if 'OO#' == i [:3]:
            fields = i [3:].split ('#')

            if None == result:
                result = {}

            result [fields [0]] = [fields [1], fields [2].strip ()]

    return result

# Function "get_commands" ____________________________________________________

def get_commands (drive, option = 1):

    """ Get the recommended sequence of partitioning commands, if any. """

    result = None

    no_options = 0
    child = call_peez2 ('-a validate -i -d ' + drive + ' -s ' +
                        partition_scheme, str (option))

    child_out = child ['out']
    result = {'commands': '',
              'metacoms': ''}
    line = child_out.readline ()

    while '' != line:

        if 'CC#' == line [:3]:
            result ['commands'] = result ['commands'] + line [3:]
        elif 'MC#' == line [:3]:
            result ['metacoms'] = result ['metacoms'] + line [3:]

        line = child_out.readline ()

#     print child_in.readline ()
#     print '**********************************'

#     for i in child_out:
#         print '*' + i + '*'

    return result

# Function "call_peez2" ______________________________________________________

def call_peez2 (args = '', input = ''):

    """ Execute "peez2" with arguments provided, if any. It is also possible
        to specify an input. """

    command = binary + ' ' + args + ' ' + common_arguments

    if '' != input:
        command = 'echo -e "' + input + '" | ' + command

    if debug:
        stderr.write (command + '\n')

    child = Popen3 (command, False, 1048576)

    return {'out': child.fromchild,
            'in':  child.tochild,
            'err': child.childerr}

# Function "beautify_size" ___________________________________________________

def beautify_size (size):

    """ Format the size of a drive into a friendly string, i.e. 64424509440
        will produce '60 GB'. """

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

def beautify_device (device):

    """ Format the name of a device to make it more readable, i.e. '/dev/hdb'
        will produce 'primary slave' or 'esclavo en el bus primario',
        depending on the "locale". """

    result = None

    try:
        name = str (device)
    except:
        name = ''

    if '' != name:

        if '/dev/hda' == name:

            if 'es' == locale [:2]:
                result = 'maestro en el bus primario (' + name + ')'
            elif 'en' == device:
                result = 'primary master'

        if '/dev/hdb' == name:

            if 'es' == locale [:2]:
                result = 'esclavo en el bus primario (' + name + ')'
            elif 'en' == device:
                result = 'primary slave'

        if '/dev/hdc' == name:

            if 'es' == locale [:2]:
                result = 'maestro en el bus secundario (' + name + ')'
            elif 'en' == device:
                result = 'secondary master'

        if '/dev/hdd' == name:

            if 'es' == locale [:2]:
                result = 'maestro en el bus secundario (' + name + ')'
            elif 'en' == device:
                result = 'secondary slave'

    return result

# End of file.

