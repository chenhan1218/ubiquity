#!/usr/bin/python

'''
This UI implementation consist actually in no UI at all.
It means it's a no interactive method to get the answers.
We don't ask because the answers already exists.
'''

import debconf

class Wizard:
  def __init__(self):
    debconf.runFrontEnd()
    self.db = debconf.Debconf()

  def get_hostname(self):
    hostname = self.db.get('base-config/get-hostname')
    return hostname

  def get_user(self):
    info = []
    info.append(self.db.get('passwd/username'))
    info.append(self.db.get('passwd/user-fullname'))
    info.append(self.db.get('passwd/user-password'))
    info.append(self.db.get('passwd/user-password-again'))
    return info

  def set_progress(self,num):
    for i in range(0,num):
      print ".",
    print "\n%d " % num

# vim:ai:et:sts=2:tw=80:sw=2:
