#!/usr/bin/python

'''
Noui Frontend

Noui frontend implementation for the installer
This UI implementation consist actually in no UI at all.
It means it's a no interactive method to get the answers.
We don't ask because the answers already exists.

To do that we need to preseed the answers. We'll use a new debconf
package called "express" for this prupose.
We'll take some answers form the express package and others from 
the system. It's because of the user could change some stuff
like timezone, keymap and locales.
'''

import debconf

class Wizard:
  def __init__(self):
    debconf.runFrontEnd()
    self.db = debconf.Debconf()

  def set_progress(self,num):
    for i in range(0,num):
      print ".",
    print "\n%d " % num

  def get_hostname(self):
    hostname = self.db.get('base-config/get-hostname')
    return hostname

  def get_user(self):
    info = []
    # Just for tests. We should use a especific package for this
    # It seems to be because of the installer preseed, so it could be
    # a good idea something like:
    # info.append(self.db.get('express/username'))
    info.append(self.db.get('passwd/username'))
    info.append(self.db.get('passwd/user-fullname'))
    info.append(self.db.get('passwd/user-password'))
    return info
    
  def get_locales(self):
    try:
      timezone = self.db.get('tzconfig/choose_country_zone_multiple')
    except:
      timezone = open('/etc/timezone').readline().strip()
    keymap  = self.db.get('debian-installer/keymap')
    locales = self.db.get('locales/default_environment_locale')
    return timezone, keymap, locales

  def get_partitions(self):
    #FIXME: We've to put here the autopartitioning stuff
    
    # This is just a example info.
    # We should take that info from the debconf
    # Something like:
    # re = self.db.get('express/mountpoints')
    # for path, dev in re:
    #   mountpoints[path] = dev
    mountpoints = {'/'     : '/dev/hda1',
                   'swap'  : '/dev/hda2',
                   '/home' : '/dev/hda3'}
    return mountpoints
 
if __name__ == '__main__':
  w = Wizard()
  name, fullname, password = w.get_user()
  timezone, keymap, locales  =  w.get_locales()
  print '''
  Hostname: %s
  User Full name: %s
  Username: %s
  Password: %s
  Timezone: %s
  Keymap: %s
  Locales: %s
  Mountpoints : %s
  ''' % (w.get_hostname(), fullname, name, password,
  timezone, keymap, locales, w.get_partitions())

# vim:ai:et:sts=2:tw=80:sw=2:
