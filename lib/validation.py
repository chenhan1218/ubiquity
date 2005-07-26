# -*- coding: utf-8 -*-

# File "validation.py".
# Created by Antonio Olmo <aolmo@emergya.info> on 26 july 2005.
# Validation library.

from string import whitespace

# Index:
# def check_username (name):
# def check_password (passwd1, passwd2):
# def invalid_names ():
    
# Function "check_username" __________________________________________________

def check_username (name):

    """ TODO """

    result = 0

    if name in invalid_names ():
        result = 3
    elif len (set (name).intersection (set (whitespace))) > 0:
        result = 2
    elif len (name) < 4 or len (name) > 12:
        result = 1

    return result

# Function "check_password" __________________________________________________

def check_password (passwd1, passwd2):

    """ TODO """

    result = 0

    if passwd1 != passwd2:
        result = 2
    elif len (passwd1) < 4 or len (passwd1) > 12:
        result = 1

    return result

# Function "invalid_names" ___________________________________________________

def invalid_names ():

    """ TODO """

    # Minimal set:
    result = set (['root'])

    # Maybe all current usernames are reserved as well:
    for i in open ('/etc/passwd'):

        if ':' in i:
            result.add (i [: i.find (':')])

    return result

# End of file.

