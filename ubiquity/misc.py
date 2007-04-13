#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import subprocess
import syslog
import codecs


def distribution():
    """Returns the name of the running distribution."""

    proc = subprocess.Popen(['lsb_release', '-is'], stdout=subprocess.PIPE)
    return proc.communicate()[0].strip()


def ex(*args):
    """runs args* in shell mode. Output status is taken."""

    log_args = ['log-output', '-t', 'ubiquity']
    log_args.extend(args)

    try:
        status = subprocess.call(log_args)
    except IOError, e:
        syslog.syslog(syslog.LOG_ERR, ' '.join(log_args))
        syslog.syslog(syslog.LOG_ERR,
                      "OS error(%s): %s" % (e.errno, e.strerror))
        return False
    else:
        if status != 0:
            syslog.syslog(syslog.LOG_ERR, ' '.join(log_args))
            return False
        syslog.syslog(' '.join(log_args))
        return True


def get_progress(str):
    """gets progress percentage of installing process from progress bar message."""

    num = int(str.split()[:1][0])
    text = ' '.join(str.split()[1:])
    return num, text


def format_size(size):
    """Format a partition size."""
    if size < 1024:
        unit = 'B'
        factor = 1
    elif size < 1024 * 1024:
        unit = 'kB'
        factor = 1024
    elif size < 1024 * 1024 * 1024:
        unit = 'MB'
        factor = 1024 * 1024
    elif size < 1024 * 1024 * 1024 * 1024:
        unit = 'GB'
        factor = 1024 * 1024 * 1024
    else:
        unit = 'TB'
        factor = 1024 * 1024 * 1024 * 1024
    return '%.1f %s' % (float(size) / factor, unit)


_supported_locales = None

def get_supported_locales():
    """Returns a list of all locales supported by the installation system."""
    global _supported_locales
    if _supported_locales is None:
        _supported_locales = {}
        supported = open('/usr/share/i18n/SUPPORTED')
        for line in supported:
            (locale, charset) = line.split(None, 1)
            _supported_locales[locale] = charset
        supported.close()
    return _supported_locales


_translations = None

def get_translations(languages=None, core_names=[]):
    """Returns a dictionary {name: {language: description}} of translatable
    strings.

    If languages is set to a list, then only languages in that list will be
    translated. If core_names is also set to a list, then any names in that
    list will still be translated into all languages. If either is set, then
    the dictionary returned will be built from scratch; otherwise, the last
    cached version will be returned."""

    global _translations
    if _translations is None or languages is not None or len(core_names) > 0:
        if languages is None:
            use_langs = None
        else:
            use_langs = set('c')
            for lang in languages:
                ll_cc = lang.lower().split('.')[0]
                ll = ll_cc.split('_')[0]
                use_langs.add(ll_cc)
                use_langs.add(ll)

        _translations = {}
        devnull = open('/dev/null', 'w')
        db = subprocess.Popen(
            ['debconf-copydb', 'templatedb', 'pipe',
             '--config=Name:pipe', '--config=Driver:Pipe',
             '--config=InFd:none',
             '--pattern=^(ubiquity|partman/text/undo_everything|partman/text/unusable|partman-basicfilesystems/bad_mountpoint|partman-newworld/no_newworld|partman-partitioning|partman-target/no_root|grub-installer/bootdev|popularity-contest/participate)'],
            stdout=subprocess.PIPE, stderr=devnull)
        question = None
        descriptions = {}
        fieldsplitter = re.compile(r':\s*')

        for line in db.stdout:
            line = line.rstrip('\n')
            if ':' not in line:
                if question is not None:
                    _translations[question] = descriptions
                    descriptions = {}
                    question = None
                continue

            (name, value) = fieldsplitter.split(line, 1)
            if value == '':
                continue
            name = name.lower()
            if name == 'name':
                question = value
            elif name.startswith('description'):
                namebits = name.split('-', 1)
                if len(namebits) == 1:
                    lang = 'c'
                else:
                    lang = namebits[1].lower()
                    # TODO: recode from specified encoding
                    lang = lang.split('.')[0]
                if (use_langs is None or lang in use_langs or
                    question in core_names):
                    descriptions[lang] = value.replace('\\n', '\n')
            elif name.startswith('extended_description'):
                namebits = name.split('-', 1)
                if len(namebits) == 1:
                    lang = 'c'
                else:
                    lang = namebits[1].lower()
                    # TODO: recode from specified encoding
                    lang = lang.split('.')[0]
                if (use_langs is None or lang in use_langs or
                    question in core_names):
                    if lang not in descriptions:
                        descriptions[lang] = value.replace('\\n', '\n')
                    # TODO cjwatson 2006-09-04: a bit of a hack to get the
                    # description and extended description separately ...
                    if question in ('grub-installer/bootdev',
                                    'partman-newworld/no_newworld'):
                        descriptions["extended:%s" % lang] = \
                            value.replace('\\n', '\n')

        db.wait()
        devnull.close()

    return _translations

string_questions = {
    'new_size_label': 'partman-partitioning/new_size',
    'grub_device_dialog': 'grub-installer/bootdev',
    'grub_device_label': 'grub-installer/bootdev',
    'popcon_checkbutton': 'popularity-contest/participate',
    # TODO: it would be nice to have a neater way to handle stock buttons
    'cancel': 'ubiquity/imported/cancel',
    'back': 'ubiquity/imported/go-back',
    'next': 'ubiquity/imported/go-forward',
    'cancelbutton': 'ubiquity/imported/cancel',
    'exitbutton': 'ubiquity/imported/quit',
    'closebutton1': 'ubiquity/imported/close',
    'cancelbutton1': 'ubiquity/imported/cancel',
    'okbutton1': 'ubiquity/imported/ok',
    'advanced_cancelbutton': 'ubiquity/imported/cancel',
    'advanced_okbutton': 'ubiquity/imported/ok',
}

string_extended = set('grub_device_label')

def map_widget_name(name):
    """Map a widget name to its translatable template."""
    if '/' in name:
        question = name
    elif name in string_questions:
        question = string_questions[name]
    else:
        question = 'ubiquity/text/%s' % name
    return question

def get_string(name, lang):
    """Get the translation of a single string."""
    question = map_widget_name(name)
    translations = get_translations()
    if question not in translations:
        return None

    if lang is None:
        lang = 'c'
    else:
        lang = lang.lower()
    if name in string_extended:
        lang = 'extended:%s' % lang

    if lang in translations[question]:
        text = translations[question][lang]
    else:
        ll_cc = lang.split('.')[0]
        ll = ll_cc.split('_')[0]
        if ll_cc in translations[question]:
            text = translations[question][ll_cc]
        elif ll in translations[question]:
            text = translations[question][ll]
        elif lang.startswith('extended:'):
            text = translations[question]['extended:c']
        else:
            text = translations[question]['c']

    return unicode(text, 'utf-8', 'replace')


# Based on code by Walter Dörwald:
# http://mail.python.org/pipermail/python-list/2007-January/424460.html
def ascii_transliterate(exc):
    if not isinstance(exc, UnicodeEncodeError):
        raise TypeError("don't know how to handle %r" % exc)
    import unicodedata
    s = unicodedata.normalize('NFD', exc.object[exc.start])[:1]
    if ord(s) in range(128):
        return s, exc.start + 1
    else:
        return u'', exc.start + 1

codecs.register_error('ascii_transliterate', ascii_transliterate)


def drop_privileges():
    if 'SUDO_GID' in os.environ:
        gid = int(os.environ['SUDO_GID'])
        os.setregid(gid, gid)
    if 'SUDO_UID' in os.environ:
        uid = int(os.environ['SUDO_UID'])
        os.setreuid(uid, uid)


def will_be_installed(pkg):
    try:
        manifest = open('/cdrom/casper/filesystem.manifest-desktop')
        try:
            for line in manifest:
                if line.strip() == '' or line.startswith('#'):
                    continue
                if line.split()[0] == pkg:
                    return True
        finally:
            manifest.close()
    except IOError:
        return True


def find_on_path(command):
    if 'PATH' in os.environ:
        path = os.environ['PATH']
    else:
        path = ''
    pathdirs = path.split(':')
    for pathdir in pathdirs:
        if pathdir == '':
            realpathdir = '.'
        else:
            realpathdir = pathdir
        trypath = os.path.join(realpathdir, command)
        if os.access(trypath, os.X_OK):
            return trypath
    return None


# vim:ai:et:sts=4:tw=80:sw=4:
