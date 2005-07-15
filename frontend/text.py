#!/usr/bin/python

'''
This is just a silly example.
Later we'll convert it into a real one
'''

class Wizard:
  def __init__(self):
    print "Welcome to the UbuntuExpress"

  def get_hostname(self):
    print "Please enter the hostname for this system."
    hostname = raw_input("Hostname: ")
    return hostname

  def set_progress(self,num):
    for i in range(0,num):
      print ".",
    print "\n%d " % num

# vim:ai:et:sts=2:tw=80:sw=2:
