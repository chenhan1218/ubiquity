# -*- coding: utf-8 -*-

def grub_dev(dev):
	leter = {'a': '0', 'b': '1', 'c': '2', 'd': '3', 'e': '4',
		 'f': '5', 'g': '6', 'h': '7', 'i': '8'}
	num   = {'1': '0', '2': '1', '3': '2', '4': '3', '5': '4',
		 '6': '5', '7': '6', '8': '7', '9': '8'}

	ext = dev[7:]
	name = 'hd%s,%s' % (leter[ext[0]], num[ext[1:]])
	return name

def make_yaboot_header(target, target_dev):
    import os, re

    yaboot_conf = open(target + '/etc/yaboot.conf', 'w')
    timeout = 50
    
    partition_regex = re.compile(r'[0-9]+$')
    partition = partition.search(target_dev).group()
    
    device_regex = re.compile(r'/dev/[a-z]+')
    device = device_regex.search(target_dev).group()
    device_of = subprocess.Popen(['ofpath', device], stdout=subprocess.PIPE).communicate()[0]
    
    boot_pipe1 = subprocess.Popen(['/sbin/fdisk', '-l', device], stdout=subprocess.PIPE)
    boot_pipe2 = subprocess.Popen(['grep', 'Apple_Bootstrap'], stdin=boot_pipe1.stdout, stdout=subprocess.PIPE)
    boot_stdout = boot_pipe2.communicate()[0]
    boot_partition_regex = re.compile(r'/dev/[a-z]+[0-9]+')
    boot_partition = boot_partition_regex.search(boot_stdout).group()
    
    yaboot_conf.write(' \
    ## yaboot.conf generated by the Ubuntu installer \
    ## \
    ## run: "man yaboot.conf" for details. Do not make changes until you have!! \
    ## see also: /usr/share/doc/yaboot/examples for example configurations. \
    ## \
    ## For a dual-boot menu, add one or more of: \
    ## bsd=/dev/hdaX, macos=/dev/hdaY, macosx=/dev/hdaZ \
    \
    boot=%s \
    device=%s \
    partition=%s \
    root=%s \
    timeout=%s \
    install=/usr/lib/yaboot/yaboot \
    magicboot=/usr/lib/yaboot/ofboot \
    enablecdboot \
    ' % (boot_partition, device_of, partition, target_dev, timeout) )

def ex(*args):
    import subprocess
    status = subprocess.call(args)
    msg = ''
    for word in args:
      msg += str(word) + ' '
    if status != 0:
      pre_log('error', msg)
      return False
    pre_log('info', msg)
    return True

def ret_ex(*args):
    import subprocess
    msg = ''
    for word in args:
      msg += str(word) + ' '
    try:
      proc = subprocess.Popen(args, stdout=PIPE, close_fds=True)
    except IOError, e:
      pre_log('error', msg)
      pre_log('error', "I/O error(%s): %s" % (e.errno, e.strerror))
      return None
    else:    
      pre_log('info', msg)
      return proc.stdout

def get_var():
  import cPickle
  file = open('/tmp/vars')
  var = cPickle.load(file)
  file.close()
  return var
  
def set_var(var):
  import cPickle
  file = open('/tmp/vars', 'w')
  cPickle.dump(var, file, -1)
  file.close()

def pre_log(code, msg=''):
  import logging
  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s %(levelname)-8s %(message)s',
                      datefmt='%a, %d %b %Y %H:%M:%S',
                      filename='/var/log/installer',
                      filemode='a')
  eval('logging.%s(\'%s\')' % (code,msg))
  
def post_log(code, msg=''):
  import logging
  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s %(levelname)-8s %(message)s',
                      datefmt='%a, %d %b %Y %H:%M:%S',
                      filename='/target/var/log/installer',
                      filemode='a')
  eval('logging.%s(\'%s\')' % (code,msg))
  
def get_progress(str):
  num = int(str.split()[:1][0])
  text = ' '.join(str.split()[1:])
  return num, text

# vim:ai:et:sts=2:tw=80:sw=2:
