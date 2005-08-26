# -*- coding: utf-8 -*-

""" U{pylint<http://logilab.org/projects/pylint>} mark: 8.33 """

# File "peez2.py".
# Automatic partitioning with "peez2".
# Created by Antonio Olmo <aolmo@emergya.info> on 25 august 2005.
# Last modified on 26 august 2005.

from popen2 import Popen3

# Index:
# def get_drives ():
# def get_info (drive):
# def get_commands (drive):
# def call_peez2 (args):

binary = 'peez2'
    
# Function "get_drives" ______________________________________________________

def get_drives ():

    """ Retrieve the list of drives in the computer. """

    result = []

    # TODO: parse I/O.

    # For every drive found:
    drive = {'no':     0,
             'name':   None,
             'device': None,
             'size':   0}
    result.append (drive)

    return result

# Function "get_info" ________________________________________________________

def get_info (drive):

    """ Retrieve information about a drive. """

    result = None

    child = call_peez2 ('-d ' + drive)
    # TODO: parse I/O.
    print child

    # If everything goes right:
    stats = {'primary':  0,
             'extended': 0,
             'logical':  0}
    parts = [None, None, None]
    result = {'stats': stats,
              'parts': parts}

    return result

# Function "get_commands" ____________________________________________________

def get_commands (drive):

    """ Get the recommended sequence of partitioning commands, if any. """

    result = []

    child = call_peez2 ('-a wizard -i -d ' + drive)
    # TODO: parse I/O.
    print child

    # For every command found:
    result.append (None)

    return result

# Function "call_peez2" ______________________________________________________

def call_peez2 (args):

    """ Executes "peez2". """

    result = Popen3 (binary + ' ' + args)

    return result

# End of file.

