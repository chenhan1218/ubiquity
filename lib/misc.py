#!/usr/bin/python

def grub_dev(dev):
	leter = {'a': '0', 'b': '1', 'c': '2', 'd': '3', 'e': '4',
		 'f': '5', 'g': '6', 'h': '7', 'i': '8'}
	num   = {'1': '0', '2': '1', '3': '2', '4': '3', '5': '4',
		 '6': '5', '7': '6', '8': '7', '9': '8'}

	ext = dev[7:]
	name = 'hd%s,%s' % (leter[ext[0]], num[ext[1:]])
	return name
