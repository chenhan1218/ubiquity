# -*- coding: utf-8 -*-

""" U{pylint<http://logilab.org/projects/pylint>} mark: 9.55 """

# File "peez2.py".
# Automatic partitioning with "peez2".
# Created by Antonio Olmo <aolmo@emergya.info> on 25 august 2005.
# Last modified on 5 september 2005.

# TODO: improve "locale" detection.
# TODO: improve debug and log system.

from popen2 import Popen3

# Index:
# def get_drives ():
# def get_info (drive):
# def suggest_actions (drive):
# def get_commands (drive, option):
# def call_peez2 (args):

locale = 'es'
debug = True
binary = 'peez2'
common_arguments = '2> /dev/null'
partition_scheme = '256:1536:512'          # A conservative scheme.
# partition_scheme = '1024:20480:30720'    # A more realistic scheme.

# Function "get_drives" ______________________________________________________

def get_drives ():

    """ Retrieve the list of drives in the computer. """

    result = []

    lines = call_peez2 () ['out']

    for i in lines:

        if 'LD#' == i [:3]:
            fields = i [3:].split ('|')

            if 'es' == locale:
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
            elif 'en' == locale:
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

            if 'es' == locale:

                if 'Particiones primarias totales:' == i [3:33]:
                    result ['prim'] = i [33:-1]
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

            elif 'en' == locale:

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

    return result

# Function "suggest_actions" _________________________________________________

def suggest_actions (drive):

    """ Get all the possibilities proposed by "peez2", if any. """

    result = None

    lines = call_peez2 ('-a wizard -d ' + drive + ' -s ' +
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
    child = call_peez2 ('-a wizard -i -d ' + drive + ' -s ' +
                        partition_scheme)

    child_out = child ['out']
    child_in = child ['in']

    line = child_out.readline ()

#     while '' != line:
#         print line
#         line = child_out.readline ()

#     print child_in.readline ()
#     print '**********************************'

#     for i in child_out:
#         print '*' + i + '*'

#         if 'OO#' == i [:3]:
#             no_options = no_options + 1

    if option >= 1 and option <= no_options:
        child_in.write (option + '\n')

    return result

# Function "call_peez2" ______________________________________________________

def call_peez2 (args = ''):

    """ Execute "peez2" with arguments provided, if any. """

    if debug:
        print binary + ' ' + common_arguments + ' ' + args

    child = Popen3 (binary + ' ' + common_arguments + ' ' + args, False, 1048576)

    return {'out': child.fromchild,
            'in':  child.tochild,
            'err': child.childerr}

# End of file.

