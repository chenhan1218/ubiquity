from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import sys

class PartitionFrame(QFrame):
    def mouseReleaseEvent(self, event):
        self.emit(SIGNAL("clicked()"))
        self.setFrameShadow(QFrame.Sunken)
        print "mouse release event"

class Partition:

    filesystemColours = {'ext3': Qt.red,
                         'free': Qt.yellow,
                         'linux-swap': Qt.cyan,
                         'fat32': Qt.green,
                         'fat16': Qt.green,
                         'ntfs': Qt.magenta}

    def __init__(self, size, index, fs, path, parent):
        self.size = size
        self.frame = PartitionFrame(parent)
        self.frame.setLineWidth(3)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setFrameShape(QFrame.Box)
        sizePolicy = self.frame.sizePolicy()
        sizePolicy.setHorizontalStretch(size)
        self.frame.setSizePolicy(sizePolicy)
        #QApplication.instance().connect(self.frame, SIGNAL("clicked()"), parent.clicked)
        QApplication.instance().connect(self.frame, SIGNAL("clicked()"), self.clicked)
        self.fs = fs
        self.path = path

        layout = QHBoxLayout(self.frame)
        label = QLabel(path, self.frame)
        layout.addWidget(label)

        self.frame.setAutoFillBackground(True)
        palette = self.frame.palette()
        try:
          palette.setColor(QPalette.Normal, QPalette.Background, self.filesystemColours[fs])
          """ #FIXME doesn't do anything
          colour = QColor(self.filesystemColours[fs])
          red = 256 - colour.red()
          green = 256 - colour.green()
          blue = 256 - colour.blue()
          inverseColour = QColor(red, green, blue)
          palette.setColor(QPalette.Normal, QPalette.Text, inverseColour)
          label.setPalette(palette)
          """
          self.frame.setPalette(palette)
        except KeyError:
          pass

        self.index = index

        parent.layout.addWidget(self.frame)
        self.parent = parent

    def clicked(self):
        self.parent.clicked(self.index)
        #self.emit(SIGNAL("clicked()"))

    def raiseFrames(self):
        self.frame.setFrameShadow(QFrame.Raised)

class PartitionsBar(QWidget):
    def __init__(self, diskSize, parent = None):
        QWidget.__init__(self, parent)
        self.layout = QHBoxLayout()
        self.layout.setMargin(2)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        self.partitions = []
        self.diskSize = diskSize
        #self.resize(200, 100)
        self.setMinimumHeight(30)
        sizePolicy = self.sizePolicy()
        sizePolicy.setVerticalStretch(10)
        sizePolicy.setVerticalPolicy(QSizePolicy.Fixed)
        self.setSizePolicy(sizePolicy)

    def addPartition(self, size, index, fs, path):
        partition = Partition(size, index, fs, path, self)
        self.partitions.append(partition)

    def clicked(self, index):
        self.emit(SIGNAL("clicked(int)"), index)
        #self.emit(SIGNAL("clicked()"))

    def raiseFrames(self):
        print "PartitionsBar clicked"
        for partition in self.partitions:
            partition.frame.setFrameShadow(QFrame.Raised)

    def selected(self, index):
        for partition in partitions:
            if partition.index == index:
                partition.clicked()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    frame = QFrame()
    layout = QVBoxLayout(frame)
    frame.setLayout(layout)
    partitionBar = PartitionsBar(1000, frame)
    partitionBar.addPartition(2146/1000)
    partitionBar.addPartition(10733/1000)
    partitionBar.addPartition(69462/1000)
    layout.addWidget(partitionBar)
    layout.addStretch()
    partitionBar.show()
    frame.show()
    sys.exit(app.exec_())
