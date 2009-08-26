# -*- coding: utf-8 -*-

import subprocess
import re
import PyQt4
import os

from PyQt4 import QtCore
from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import *

uidir = "/usr/share/ubiquity/qt/"

class Keyboard(QWidget):
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        
        self.codes = []
        self.shiftCodes = []
        self.layout = None
        self.variant = None
        
        #load the ui
        uic.loadUi(os.path.join(uidir, "keyboard.ui"), self)
        
    def setLayout(self, layout):
        self.layout = layout
        
    def setVariant(self, variant):
        self.variant = variant
        self.loadCodes()
        
        for row in self.children():
            for key in row.children():
                if type(key) == QPushButton:
                    index = "0%s" % key.objectName()
                    if "0x00" in index:
                        continue
                    key.setText(self.plain_text(int(index, 16)))
        
    #given a keyboard index? scancode?
    #return the unicode character
    def plain_text(self, index):
        
        if index == 0xe:
            return "<"
        elif index == 0x2a or index == 0x36:
            return "Shift"
        elif index == 0x1c:
            return "Enter"
        elif index == 0x1d:
            return "Ctrl"
        elif index == 0xf:
            return "Tab"
        elif index == 0x3a:
            return "Caps"
        elif index == 0x38:
            return "Alt"

        full = self.codes[index]
        code = full
        
        if (0xf000 & full):
            type = (full >> 8) & 0xff
            code = full & 0xff
            
        return unichr(code)
        
    def printCodes(self):
        counter=1
        for c in self.codes:
            if counter % 9 == 0:
                counter = 1
                print ""
            
            print "0x%x" % c,
            counter += 1
        
    def loadCodes(self):
        if self.layout is None:
            return
            
        variantParam = ""
        
        if self.variant:
            variantParam = "-variant %s" % self.variant;
            
        cmd="ckbcomp -model pc105 -layout %s %s" % (self.layout, variantParam)
        print cmd
        cmd2="loadkeys -mu"
        
        #setup pipe between the two programs
        pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        pipe2 = subprocess.Popen(cmd2, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        ret = pipe2.communicate(pipe.communicate()[0])

        cfile = ret[0]
        
        #clear the current codes
        del self.codes[:]

        inNormal = False;
        lines = cfile.split('\n')
        for l in lines:
            if inNormal and "}" in l:
                inNormal = False;
            
            if inNormal:
                for code in l.split(','):
                    if len(code) > 0:
                        self.codes.append(int(code.strip(), 16))
            
            if "u_short plain_map[NR_KEYS] = {" in l:
                inNormal = True;
                