# -*- coding: utf-8 -*-

""" U{pylint<http://logilab.org/projects/pylint>} mark: 9.27 """

# File "peez2.py".
# Automatic partitioning with "peez2".
# Created by Antonio Olmo <aolmo@emergya.info> on 25 aug 2005.
# Last modified on 14 sep 2005.

# TODO: improve debug and log system.

# Index:
# class Peez2:
# def beautify_size (size):
# def beautify_device (device, locale):

from sys    import stderr
from locale import getdefaultlocale
from popen2 import Popen3

class Peez2:

    """ Encapsulates a sequence of operations with I{Peez2} partition
        assistant. The partition scheme is expressed in MB (1024 Bytes). """

    # Initialization _________________________________________________________

    def __init__ (self, binary = 'peez2', common_arguments = '2> /dev/null',
                  debug = True, partition_scheme = {'swap':  256,
                                                    'root': 1536,
                                                    'home':  512}):

        """ Detect locale and scan for drives. """

        # A more realistic scheme: 1024, 20480, 30720.

        self.__binary = binary
        self.__common_arguments = common_arguments
        self.__debug = debug
        self.__partition_scheme = partition_scheme
        self.__locale = getdefaultlocale () [0]
        self.__drives = self.__scan_drives ()

    # Public method "get_drives"  ____________________________________________

    def get_drives (self):

        """ Retrieve a list of drives. Each unit is identified by its device
            name (i.e. C{/dev/hda}) and has an associated human-readable label
            (i.e. I{75 GB, maestro en el bus primario (/dev/hda),
            "ST380011A"}). """

        result = []

        for i in self.__drives:
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

            item = {'id':           str (i ['device']),
                    'label':        label,
                    'info':         i ['info'],
                    'large_enough': enough}
            result.append (item)

        return result

    # Private method "__scan_drives"  ________________________________________

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

        if self.__debug:
            dummy_drive = {'device': '/dev/strange',
                           'label': 'FOR DEBUGGING PURPOSES ONLY',
                           'size': 1200000000,
                           'no': -1,
                           'info': {}}
            result.append (dummy_drive)

        return result

    # Private method "__get_info"  ___________________________________________

    def __get_info (self, drive):

        """ Retrieve information about a drive. """

        result = None

        # We are not using a more compact construct below to explicit that the
        #     same 3 partitions are always used, and in the same order:
        parts = self.__partition_scheme
        lines = self.__call_peez2 ('-a validate -d ' + drive + ' -s ' +
                                   str (parts ['swap']) + ':' +
                                   str (parts ['root']) + ':' +
                                   str (parts ['home'])) ['out']

        for i in lines:

            # "Aviso":
            if 'AA#' == i [:3]:

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

        return result

    # TODO method "get_commands" _____________________________________________

    def get_commands (self, drive, option = 1):

        """ Get the recommended sequence of partitioning commands, if any. """

        result = None

        no_options = 0
        child = self.__call_peez2 ('-a validate -i -d ' + drive + ' -s ' +
                            self.__partition_scheme, str (option))

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

