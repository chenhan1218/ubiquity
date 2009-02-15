# -*- coding: utf-8 -*-
#
# Copyright (C) 2006, 2007, 2008, 2009 Canonical Ltd.
#
# Author:
#   Jonathan Riddell <jriddell@ubuntu.com>
#   Roman Shtylman <shtylman@gmail.com>
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or at your option)
# any later version.
#
# Ubiquity is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with Ubiquity; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##################################################################################

import sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class Partition:
    # colors used to render partition types
    # TODO try to be consistent with the gtk gui?
    filesystemColours = {'ext3': Qt.blue,
                         'ext4': Qt.blue,
                         'free': Qt.white,
                         'linux-swap': Qt.cyan,
                         'fat32': Qt.green,
                         'fat16': Qt.green,
                         'ntfs': Qt.magenta,
                         'none' : Qt.darkCyan}

    def __init__(self, size, index, fs, path):
        self.size = size
        self.fs = fs
        self.path = path
        self.index = index

class PartitionsBar(QWidget):
    """ a widget to graphically show disk partitions. """
    def __init__(self, diskSize, parent = None):
        QWidget.__init__(self, parent)
        self.partitions = []
        self.diskSize = diskSize
        self.setMinimumHeight(50)
        self.setMinimumWidth(500)
        sizePolicy = self.sizePolicy()
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(sizePolicy)
        
    def paintEvent(self, qPaintEvent):
        
        painter = QPainter(self);
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.translate(1,1)
        
        radius = (self.height()-1)//4
        height = radius * 2
        effective_width = self.width() - 1 - height
        
        if len(self.partitions) == 0:
            #TODO...need to draw something..?
            return
        
        #first partition bar starts after the cap
        offset = height//2
        
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, height))
        gradInv = QLinearGradient(QPointF(0, height), QPointF(0, height*1.5))
        
        #create the gradient for colors to populate
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, height * 2))
        
        startCap = False
        for p in self.partitions:
            pix_size = int(effective_width * float(p.size) / self.diskSize)
            
            #use the right color for the filesystem
            if Partition.filesystemColours.has_key(p.fs):
                light = QColor(Partition.filesystemColours[p.fs])
            else:
                light = QColor(Partition.filesystemColours['none'])
                
            dark = QColor(light)
            
            h = light.hueF()
            s = light.saturationF()
            v = light.valueF()
            dark.setHsvF(h, s, v * .6)
            
            #populate gradient
            #gradient is made in such a way that both the object and mirror can be
            #drawn with one brush
            grad.setColorAt(0, dark);
            grad.setColorAt(.22, light);
            grad.setColorAt(.5, dark);
            dark.setAlphaF(.5)
            grad.setColorAt(.501, dark);
            light.setAlpha(0)
            grad.setColorAt(.75, light)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            
            #draw start cap if needed
            if not startCap:
                painter.drawChord(0, 0, height, height, -90*16, -180*16)
                painter.drawChord(0, height, height, height, -90*16, -180*16)
                startCap = True
            
            painter.drawRect(offset, 0, pix_size, height)
            painter.drawRect(offset, height, pix_size, height)
            offset = offset + pix_size
            
        #TODO if space not used up by partitions, render none zone to fill disk
            
        #draw end cap at the end, this will use the last brush and the offset
        painter.drawChord(offset - radius, 0, height, height, 90*16, -180*16)
        painter.drawChord(offset - radius, height, height, height, 90*16, -180*16)

    def addPartition(self, size, index, fs, path):
        partition = Partition(size, index, fs, path)
        self.partitions.append(partition)

    def clicked(self, index):
        self.emit(SIGNAL("clicked(int)"), index)

    def raiseFrames(self):
        for partition in self.partitions:
            partition.frame.setFrameShadow(QFrame.Raised)

    def selected(self, index):
        for partition in partitions:
            if partition.index == index:
                partition.clicked()
                
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    partBar = PartitionsBar(300)
    
    partBar.addPartition(10, 0, "ext3", "/")
    partBar.addPartition(20, 1, "linux-swap", "")
    partBar.addPartition(30, 2, "free", "")
    partBar.addPartition(40, 1, "ntfs", "")
    partBar.addPartition(50, 2, "free", "")
    
    
    partBar.show()
    
    sys.exit(app.exec_())
