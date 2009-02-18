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

from ubiquity.misc import format_size

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
        self.next = None

class PartitionsBar(QWidget):
    """ a widget to graphically show disk partitions. """
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        self.partitions = []
        self.radius = 4
        self.height = 25 #should be a multiple of 2
        self.rounded = True
        self.diskSize = 0
        self.setMinimumHeight(self.height*2 + 10)
        self.setMinimumWidth(500)
        sizePolicy = self.sizePolicy()
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(sizePolicy)
        
        self.resize_loc = 0
        self.resizing = False
        self.resize_part = None
        
    def paintEvent(self, qPaintEvent):
        
        painter = QPainter(self);
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        height = self.height
        height_2 = height/2
        effective_width = self.width() - 1
        
        #create the gradient for colors to populate
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, height * 2))
        
        path = QPainterPath()
        mirrPath = QPainterPath()
        
        if self.rounded:
            path.addRoundedRect(0, 0, self.width()-1, height, self.radius, self.radius)
            mirrPath.addRoundedRect(0, height, self.width()-1, height, self.radius, self.radius)
        else:
            path.addRect(0, 0, self.width()-1, height)
            mirrPath.addRect(0, height, self.width()-1, height)
        
        part_offset = 0
        label_offset = 0
        trunc_pix = 0
        for p in self.partitions:
            #this is done so that even after resizing, other partitions draw in the same places
            trunc_pix += (effective_width * float(p.size) / self.diskSize)
            pix_size = int(round(trunc_pix))
            trunc_pix -= pix_size
            
            #use the right color for the filesystem
            if Partition.filesystemColours.has_key(p.fs):
                pColor = QColor(Partition.filesystemColours[p.fs])
            else:
                pColor = QColor(Partition.filesystemColours['free'])
            
            pal = QPalette(pColor)
            light = pal.color(QPalette.Light)
            mid = pal.color(QPalette.Mid)
            dark = pal.color(QPalette.Dark)
            
            #populate gradient
            #gradient is made in such a way that both the object and mirror can be
            #drawn with one brush
            grad.setColorAt(0, light);
            grad.setColorAt(.5, dark);
            dark.setAlphaF(.5)
            grad.setColorAt(.501, dark);
            light.setAlpha(0)
            grad.setColorAt(.75, light)
            
            painter.setPen(dark)
            painter.setBrush(QBrush(grad))
            
            painter.setClipRect(part_offset, 0, pix_size, height*2)
            painter.drawPath(path)
            painter.setPen(Qt.NoPen)
            painter.drawPath(mirrPath)
                
            #draw the labels
            painter.setPen(Qt.black)
            painter.setBrush(mid)
            painter.setClipping(False)
            
            draw_labels = True
            if draw_labels:
                metrics = painter.fontMetrics()
                
                #name is the path by default, or free space if unpartitioned
                name = p.path
                if p.fs == 'free':
                    name = 'free space'
                
                labelText = "%s" % name
                labelTextSize = metrics.size(Qt.TextSingleLine, labelText)
                
                size_text = format_size(p.size)
                infoLabelText = "%.01f%% (%s)" % (float(p.size) / self.diskSize * 100, size_text)
                infoLabelTextSize = metrics.size(Qt.TextSingleLine, infoLabelText)
                
                #label vertical location
                labelY = height + 8
                
                # draw the label text
                painter.drawText(label_offset + 15, labelY + labelTextSize.height()/2, labelText)
                painter.drawText(label_offset + 15, labelY + labelTextSize.height() + infoLabelTextSize.height()/2, infoLabelText)
                
                #turn off antialiasing for label square
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.drawRect(label_offset, labelY - 2, 10, 10)
                label_offset += max(labelTextSize.width(), infoLabelTextSize.width()) + 30
                painter.setRenderHint(QPainter.Antialiasing, True)
            
            painter.setClipPath(path)
            
            #if this is partition after one we are resizing draw handle
            #this way it appears on top of both partitions
            if self.resize_part and p == self.resize_part.next:
                resize_pen = QPen(Qt.black)
                part = self.resize_part
                
                # draw a resize handle
                xloc = part_offset
                self.resize_loc = xloc
                side = 1
                arr_dist = 5
                
                resize_pen.setWidth(1)
                painter.setPen(resize_pen)
                
                if part.size > part.minsize:
                    painter.drawLine(xloc - arr_dist, height_2, xloc, height/2)
                    
                if part.size < part.maxsize:
                    painter.drawLine(xloc, height/2, xloc + arr_dist, height/2)
                
                resize_pen.setWidth(2)
                painter.setPen(resize_pen)
                
                painter.drawLine(xloc, 0, xloc, height)
                
                if part.size > part.minsize:
                    painter.drawLine(xloc - arr_dist, height_2, xloc - arr_dist + side, height_2+side)
                    painter.drawLine(xloc - arr_dist, height_2, xloc - arr_dist + side, height_2-side)
                    
                if part.size < part.maxsize:
                    painter.drawLine(xloc + arr_dist, height_2, xloc + arr_dist - side, height_2+side)
                    painter.drawLine(xloc + arr_dist, height_2, xloc + arr_dist - side, height_2-side)
                
            #increment the partition offset
            part_offset += pix_size

    def addPartition(self, name, size, index, fs, path):
        partition = Partition(size, index, fs, path)
        self.diskSize += size
        
        #set the previous partition to have this one as next partition
        if len(self.partitions) > 0:
            last = self.partitions[len(self.partitions)-1]
            last.next = partition
            
        self.partitions.append(partition)
        
    def setResizePartition(self, path, minsize, maxsize, origsize, new_label):
        part = None
        index = 0
        for p in self.partitions:
            if p.path == path:
                part = p
                break
            index += 1
        
        if not part:
            return
        
        new_size = (minsize + p.size)/2
        part.size = new_size
        part.minsize = minsize
        part.maxsize = maxsize
        part.origsize = origsize
        self.resize_part = part
        
        if part.next == None or part.next.index != -1:
            #if our resize partition is at the end or the next one is not free space
            p = Partition(origsize - new_size, 0, '', 'Kubuntu')
            p.next = part.next
            part.next = p
            
            #insert a new fake partition after the resize partition
            self.partitions.insert(index + 1, p)
        else:
            #we had a next partition that was free space, use that
            #set the size of the next partition accordingly
            part.next.size += origsize - part.size
        
        # need mouse tracking to be able to change the cursor
        self.setMouseTracking(True)
    
    # @return the new size of the resize partition if set (in bytes)
    def resizePartSize():
        # fail if no resize_part, we don't want to accidentally return 0
        assert self.resize_part != None, "No resize partition defined"
        return self.resize_part.size
                
    def mousePressEvent(self, qMouseEvent):
        if self.resize_part:
            # if pressed on bar
            if abs(qMouseEvent.x() - self.resize_loc) < 3:
                self.resizing = True
        
    def mouseMoveEvent(self, qMouseEvent):
        if self.resizing:    
            start = 0
            for p in self.partitions:
                if p == self.resize_part:
                    break
                start += p.size
            
            ew = self.width() - 1
            bpp = self.diskSize / float(ew)
            
            # mouse position in bytes within this partition
            mx = qMouseEvent.x() * bpp - start
            
            #make sure we are within resize range
            if mx < self.resize_part.minsize:
                mx = self.resize_part.minsize
            elif mx > self.resize_part.maxsize:
                mx = self.resize_part.maxsize
            
            #chagne the partition sizes
            span = self.resize_part.origsize
            percent = mx / float(span)
            oldsize = self.resize_part.size
            self.resize_part.size = int(round(span * percent))
            self.resize_part.next.size -= self.resize_part.size - oldsize
            
            #sum the partitions and make sure the disk size is still the same
            #this is a precautionary measure
            t = 0
            for p in self.partitions:
                t = t + p.size
            assert t == self.diskSize
            
            #using PyQt object to avoid wrapping the size otherwise qt truncates to 32bit int
            self.emit(SIGNAL("partitionResized(PyQt_PyObject, PyQt_PyObject)"), 
                self.resize_part.path, self.resize_part.size)
            
            #finally redraw
            self.update()
        else:
            if self.resize_part:
                if abs(qMouseEvent.x() - self.resize_loc) < 3:
                    self.setCursor(Qt.SplitHCursor)
                elif self.cursor != Qt.ArrowCursor:
                    self.setCursor(Qt.ArrowCursor)
            
    def mouseReleaseEvent(self, qMouseEvent):
        self.resizing = False
                
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    wid = QWidget()
    layout = QVBoxLayout(wid)
    
    partBar = PartitionsBar(wid)
    layout.addWidget(partBar)
    
    '''partBar.addPartition('', 5000, 1, "linux-swap", "/dev/sdb1")
    partBar.addPartition('', 20000, 2, "ext3", "/dev/sdb2")
    partBar.addPartition('', 30000, 3, "linux-swap", "/dev/sdb3")
    partBar.addPartition('', 50000, 4, "ntfs", "/dev/sdb4")
    partBar.setResizePartition('/dev/sdb2', 5000, 15000, 20000, 'Kubuntu')'''
    
    '''partBar.addPartition('', 4005679104, 1, 'ext4', '/dev/sdb1')
    partBar.addPartition('', 53505446400, -1, 'free', '/dev/sdb-1')
    partBar.addPartition('', 2500452864, 5, 'linux-swap', '/dev/sdb5')
    partBar.setResizePartition('/dev/sdb1', 230989824, 55143440896, 4005679104, 'Kubuntu')'''
    
    partBar.addPartition('', 57511125504, 1, 'ext4', '/dev/sdb1')
    partBar.addPartition('', 2500452864, 5, 'linux-swap', '/dev/sdb5')
    partBar.setResizePartition('/dev/sdb1', 230989824, 55143440896, 57511125504, 'Kubuntu')
    
    wid.show()
    
    sys.exit(app.exec_())
