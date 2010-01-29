# -*- coding: utf-8 -*-
from PyQt4.QtCore import Qt, QRectF
from PyQt4.QtGui import QWidget, QFont, QPainter
from PyQt4.QtSvg import QSvgRenderer
from PyQt4 import uic

import subprocess
import sys
import os

IMG_DIR = "/usr/share/ubiquity/qt/images"

#U+ , or +U+ ... to string
def fromUnicodeString(raw):
    if raw[0:2] == "U+":
        return unichr(int(raw[2:], 16))
    elif raw[0:2] == "+U":
        return unichr(int(raw[3:], 16))
        
    return ""

class Keyboard(QWidget):
    
    kb_104 = [
        (0, [0x29, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9, 0xa, 0xb, 0xc, 0xd]),
        (55, [0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x2b]),
        (70, [0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28]),
        (84, [0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35]),
        (0, [])]
        
    kb_105 = [
        (0, [0x29, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9, 0xa, 0xb, 0xc, 0xd]),
        (55, [0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b]),
        (70, [0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2b]),
        (45, [0x54, 0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35]),
        (0, [])]
        
    kb_106 = [
        (0, [0x29, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0x9, 0xa, 0xb, 0xc, 0xd, 0xe]),
        (55, [0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b]),
        (70, [0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29]),
        (94, [0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36]),
        (0, [])]
        
    lowerFont = QFont("Helvetica", 10, QFont.DemiBold)
    upperFont = QFont("Helvetica", 8)
    
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        self.codes = []
        
        self.layout = "us"
        self.variant = ""
        
        self.setFixedSize(565, 185)#670#.843
        self.kw = 40 * .843
        self.ks = 5  * .843
        
        self.svg = None
        self.kb = None
        
        #self.loadCodes()
        #self.loadInfo()
        
    def setLayout(self, layout):
        self.layout = layout
        
    def setVariant(self, variant):
        self.variant = variant
        self.loadCodes()
        self.loadInfo()
        self.repaint()
        
    def loadInfo(self):
        kbl_104 = ["us", "th"]
        kbl_106 = ["jp"]
        
        if self.layout in kbl_104:
            if self.kb != self.kb_104:
                self.svg = QSvgRenderer(os.path.join(IMG_DIR, "104_key.svg"))
                self.kb = self.kb_104
        elif self.layout in kbl_106:
            if self.kb != self.kb_106:
                self.svg = QSvgRenderer(os.path.join(IMG_DIR, "106_key.svg"))
                self.kb = self.kb_106
        elif self.kb != self.kb_105:
            self.svg = QSvgRenderer(os.path.join(IMG_DIR, "105_key.svg"))
            self.kb = self.kb_105
        
    def paintEvent(self, pe):
        if not self.svg:
            return
    
        p = QPainter(self)
        self.svg.render(p)
        
        kw = self.kw
        ks = self.ks
        
        y = 2
        for r in self.kb:
            x = r[0] + 6
            
            for k in r[1]:
                p.setFont(self.lowerFont)
                rect = QRectF(x, y, kw, kw-1)
                p.drawText(rect, Qt.AlignLeft | Qt.AlignBottom, self.regular_text(k))
                
                p.setFont(self.upperFont)
                p.drawText(rect, Qt.AlignLeft | Qt.AlignTop, self.shift_text(k))
                
                #p.drawText(x, y, kw-10, kw, Qt.AlignRight | Qt.AlignBottom, self.ctrl_text(k))
                #p.drawText(x, y, kw-10, kw, Qt.AlignRight | Qt.AlignTop, self.alt_text(k))
                x += kw + ks
            y += ks + kw
    
        QWidget.paintEvent(self, pe)
        
    def regular_text(self, index):
        return self.codes[index - 1][0]
        
    def shift_text(self, index):
        return self.codes[index - 1][1]
        
    def ctrl_text(self, index):
        return self.codes[index - 1][2]
        
    def alt_text(self, index):
        return self.codes[index - 1][3]
        
    def loadCodes(self):
        if self.layout is None:
            return
            
        variantParam = ""
        if self.variant:
            variantParam = "-variant %s" % self.variant;
            
        cmd="ckbcomp -model pc106 -layout %s %s -compact" % (self.layout, variantParam)
        #print cmd
        
        pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=None)
        cfile = pipe.communicate()[0]
        
        #clear the current codes
        del self.codes[:]
        
        for l in cfile.split('\n'):
            if l[:7] != "keycode":
                continue
                
            codes = l.split('=')[1].strip().split(' ')
            
            plain = fromUnicodeString(codes[0])
            shift = fromUnicodeString(codes[1])
            ctrl = fromUnicodeString(codes[2])
            alt = fromUnicodeString(codes[3])
            
            if ctrl == plain:
                ctrl = ""
                
            if alt == plain:
                alt = ""
            
            self.codes.append((plain, shift, ctrl, alt))

## testing 
if __name__ == "__main__":
    from PyQt4.QtGui import *
    
    IMG_DIR = "../../../gui/qt/images"
    
    app = QApplication(sys.argv)

    win = QWidget()
    l = QVBoxLayout(win)

    def addKb(layout, variant = ""):
        kb1 = Keyboard()
        kb1.setLayout(layout)
        kb1.setVariant(variant)
        l.addWidget(kb1)
        
    addKb("us")
    addKb("gb")
    addKb("th")
    addKb("gr")

    win.show()

    app.exec_()