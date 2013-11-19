# Config file for english label values
# Author: Dan Chapman <daniel@chapman-mail.com>
# Copyright (C) 2013
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


def get_distribution():
    """Returns the name of the running distribution."""
    with open('/cdrom/.disk/info') as f:
        for line in f:
            distro = line[:max(line.find(' '), 0) or None]
            if distro:
                return str(distro)
            raise SystemError("Could not get distro name")

distro_flavor = get_distribution()

stepLanguage = {
    "release_notes_label": 'You may wish to read the <a href="release-notes">'
    'release notes</a>.',
    "page_title": 'page_title= <span size="xx-large">Welcome</span>'
}

stepPrepare = {
    "page_title": '<span size="xx-large">Preparing to install {0}</span>'
    .format(distro_flavor),
    "prepare_best_results": 'For best results, please ensure that this '
    'computer:',
    "prepare_foss_disclaimer": 'Ubuntu uses third-party software to play '
    'Flash, MP3 and other media, and to work with some graphics and wi-fi '
    'hardware. Some of this software is proprietary. The software is subject '
    'to license terms included with its documentation.',
    "prepare_download_updates": 'Download updates while installing',
    "prepare_nonfree_software": 'Install this third-party software',
    "prepare_network_connection": 'is connected to the Internet',
    "prepare_sufficient_space": 'has at least 6.0 GB available drive space'
}


stepPartAsk = {
    "page_title": '<span size="xx-large">Installation type</span>',
    "use_device": 'Erase disk and install {0}'.format(distro_flavor),
    "use_device_desc": '<span size="small"><span foreground="darkred">'
    'Warning:</span> This will delete any files on the disk.</span>',
    "use_crypto": 'Encrypt the new Ubuntu installation for security',
    "use_crypto_desc": '<span size="small">You will choose a security key in '
    'the next step.</span>',
    "use_lvm": 'Use LVM with the new Ubuntu installation',
    "use_lvm_desc": '<span size="small">This will set up Logical Volume '
    'Management. It allows taking snapshots and easier partition '
    'resizing.</span>',
    "custom_partitioning": 'Something else',
    "custom_partitioning_desc": '<span size="small">You can create or resize '
    'partitions yourself, or choose multiple partitions for Ubuntu.</span>'
}


stepPartCrypto = {
    "page_title": '<span size="xx-large">Choose a security key:</span>',
    "verified_crypto_label": 'Confirm the security key:',
    "crypto_label": 'Choose a security key:',
    "crypto_description": 'Disk encryption protects your files in case you '
    'lose your computer. It requires you to enter a security key each time '
    'the computer starts up.',
    "crypto_warning": '<span foreground="darkred">Warning:</span> If you lose '
    'this security key, all data will be lost. If you need to, write down '
    'your key and keep it in a safe place elsewhere.',
    "crypto_extra_label": 'For more security:',
    "crypto_extra_time": 'The installation may take much longer.',
    "crypto_description_2": 'Any files outside of Ubuntu will not be '
    'encrypted.',
    "crypto_overwrite_space": 'Overwrite empty disk space'
}

stepLocation = {
    "page_title": '<span size="xx-large">Where are you?</span>'
}

stepKeyboardConf = {
    "page_title": '<span size="xx-large">Keyboard layout</span>'
}

stepUserInfo = {
    "page_title": '<span size="xx-large">Who are you?</span>',
    "hostname_label": "Your computer's name:",
    "username_label": 'Pick a username:',
    "password_label": 'Choose a password:',
    "verified_password_label": 'Confirm your password:',
    "hostname_extra_label": 'The name it uses when it talks to other '
    'computers.'
}
