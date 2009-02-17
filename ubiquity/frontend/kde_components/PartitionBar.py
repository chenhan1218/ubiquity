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
    filesystemColours = {'ext3': Qt.darkCyan,
                         'ext4': Qt.darkCyan,
                         'free': Qt.white,
                         'linux-swap': Qt.cyan,
                         'fat32': Qt.green,
                         'fat16': Qt.green,
                         'ntfs': Qt.magenta}

    def __init__(self, size, index, fs, path):
        self.size = size
        self.fs = fs
        self.path = path
        self.index = index

class PartitionsBar(QWidget):
    """ a widget to graphically show disk partitions. """
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        self.partitions = []
        self.radius = 10
        self.setMinimumHeight(self.radius*4)
        self.setMinimumWidth(500)
        sizePolicy = self.sizePolicy()
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(sizePolicy)
        
    def paintEvent(self, qPaintEvent):
        
        painter = QPainter(self);
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        height = self.radius * 2
        effective_width = self.width() - 1
        
        #create the gradient for colors to populate
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, height * 2))
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width()-1, height, self.radius, self.radius)
        
        mirrPath = QPainterPath()
        mirrPath.addRoundedRect(0, height, self.width()-1, height, self.radius, self.radius)
        
        # do this dynamically to prevent bookeeping elsewhere
        diskSize = 0
        for p in self.partitions:
            diskSize += p.size
        
        part_offset = 0
        label_offset = 0
        for p in self.partitions:
            pix_size = round(effective_width * float(p.size) / diskSize + .5)
            
            #use the right color for the filesystem
            if Partition.filesystemColours.has_key(p.fs):
                pColor = QColor(Partition.filesystemColours[p.fs])
            else:
                pColor = QColor(Partition.filesystemColours['free'])
                
            top = QColor.fromHsvF(pColor.hueF(), pColor.saturationF(), pColor.valueF() * .8)
            light = QColor.fromHsvF(pColor.hueF(), pColor.saturationF(), pColor.valueF() * .9)
            bot = QColor.fromHsvF(pColor.hueF(), pColor.saturationF(), pColor.valueF() * .6)
            
            #populate gradient
            #gradient is made in such a way that both the object and mirror can be
            #drawn with one brush
            grad.setColorAt(0, top);
            grad.setColorAt(.2, light);
            grad.setColorAt(.5, bot);
            bot.setAlphaF(.5)
            grad.setColorAt(.501, bot);
            light.setAlpha(0)
            grad.setColorAt(.75, light)
            
            painter.setPen(bot)
            painter.setBrush(QBrush(grad))
            
            painter.setClipRect(part_offset, 0, pix_size, height*2)
            part_offset += pix_size
            
            painter.drawPath(path)
            painter.setPen(Qt.NoPen)
            painter.drawPath(mirrPath)
            
            painter.setPen(Qt.black)
            painter.setBrush(top)
            painter.setClipping(False)
            
            draw_labels = True
            if draw_labels:
                metrics = painter.fontMetrics()
                
                #name is the path by default, or free space if unpartitioned
                name = p.path
                if p.fs == 'free':
                    name = 'free space'
                    
                labelText = "%s (%.01f%%)" % (name, float(p.size) / diskSize * 100)
                labelTextSize = metrics.size(Qt.TextSingleLine, labelText)
                
                #label vertical location
                labelY = height * 1.5
                
                # draw the label text
                painter.drawText(label_offset + 15, labelY + labelTextSize.height()/2, labelText)
                
                #turn off antialiasing for label square
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.drawRect(label_offset, labelY - 2, 10, 10)
                label_offset += labelTextSize.width() + 30
                painter.setRenderHint(QPainter.Antialiasing, True)

    def addPartition(self, name, size, index, fs, path):
        partition = Partition(size, index, fs, path)
        self.partitions.append(partition)
    
    def resizePart(self, path, new_size):
        for p in self.partitions:
            if p.path == path:
                p.size = new_size
                return
    
    #def clicked(self, index):
    #    self.emit(SIGNAL("clicked(int)"), index)

    def selected(self, index):
        for partition in partitions:
            if partition.index == index:
                partition.clicked()
                
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    wid = QWidget()
    layout = QVBoxLayout(wid)
    
    blank = PartitionsBar(100 ,wid)
    layout.addWidget(blank)
    
    partBar = PartitionsBar(300 ,wid)
    layout.addWidget(partBar)
    partBar.addPartition(20, 0, "ext3", "/")
    partBar.addPartition(30, 1, "linux-swap", "")
    partBar.addPartition(50, 1, "ntfs", "")
    partBar.addPartition(60, 2, "fat32", "")
    
    
    wid.show()
    
    sys.exit(app.exec_())
