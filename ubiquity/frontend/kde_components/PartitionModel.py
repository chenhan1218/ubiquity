# -*- coding: utf-8 -*-

import syslog

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from ubiquity.misc import *
from ubiquity.components import partman, partman_commit

# describes the display for the manual partition view widget
class PartitionModel(QAbstractItemModel):
    def __init__(self, ubiquity, parent=None):
        QAbstractItemModel.__init__(self, parent)

        rootData = []
        rootData.append(QVariant(ubiquity.get_string('partition_column_device')))
        rootData.append(QVariant(ubiquity.get_string('partition_column_type')))
        rootData.append(QVariant(ubiquity.get_string('partition_column_mountpoint')))
        rootData.append(QVariant(ubiquity.get_string('partition_column_format')))
        rootData.append(QVariant(ubiquity.get_string('partition_column_size')))
        rootData.append(QVariant(ubiquity.get_string('partition_column_used')))
        self.rootItem = TreeItem(rootData)

    def append(self, data, ubiquity):
        self.rootItem.appendChild(TreeItem(data, ubiquity, self.rootItem))

    def columnCount(self, parent):
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()

        if role == Qt.CheckStateRole and index.column() == 3:
            return QVariant(item.data(index.column()))
        elif role == Qt.DisplayRole and index.column() != 3:
            return QVariant(item.data(index.column()))
        else:
            return QVariant()

    def setData(self, index, value, role):
        item = index.internalPointer()
        if role == Qt.CheckStateRole and index.column() == 3:
            item.partman_column_format_toggled(value.toBool())
        self.emit(SIGNAL("dataChanged(const QModelIndex&, const QModelIndex&)"), index, index)
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        #self.setData(index, QVariant(Qt.Checked), Qt.CheckStateRole)
        #return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 3:
            item = index.internalPointer()
            if item.formatEnabled():
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
            else:
                return Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.rootItem.data(section)

        return QVariant()

    def index(self, row, column, parent = QModelIndex()):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def children(self):
        return self.rootItem.children()

class TreeItem:
    def __init__(self, data, ubiquity=None, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
        self.ubiquity = ubiquity

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def children(self):
        return self.childItems

    def columnCount(self):
        if self.parentItem is None:
            return len(self.itemData)
        else:
            return 5

    def data(self, column):
        if self.parentItem is None:
            return QVariant(self.itemData[column])
        elif column == 0:
            return QVariant(self.partman_column_name())
        elif column == 1:
            return QVariant(self.partman_column_type())
        elif column == 2:
            return QVariant(self.partman_column_mountpoint())
        elif column == 3:
            return QVariant(self.partman_column_format())
        elif column == 4:
            return QVariant(self.partman_column_size())
        elif column == 5:
            return QVariant(self.partman_column_used())
        else:
            return QVariant("other")

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0

    def partman_column_name(self):
        partition = self.itemData[1]
        if 'id' not in partition:
            # whole disk
            return partition['device']
        elif partition['parted']['fs'] != 'free':
            return '  %s' % partition['parted']['path']
        elif partition['parted']['type'] == 'unusable':
            return '  %s' % self.ubiquity.get_string('partman/text/unusable')
        else:
            # partman uses "FREE SPACE" which feels a bit too SHOUTY for
            # this interface.
            return '  %s' % self.ubiquity.get_string('partition_free_space')

    def partman_column_type(self):
        partition = self.itemData[1]
        if 'id' not in partition or 'method' not in partition:
            if ('parted' in partition and
                partition['parted']['fs'] != 'free' and
                'detected_filesystem' in partition):
                return partition['detected_filesystem']
            else:
                return ''
        elif ('filesystem' in partition and
              partition['method'] in ('format', 'keep')):
            return partition['acting_filesystem']
        else:
            return partition['method']

    def partman_column_mountpoint(self):
        partition = self.itemData[1]
        if isinstance(self.ubiquity.dbfilter, partman.Partman):
            mountpoint = self.ubiquity.dbfilter.get_current_mountpoint(partition)
            if mountpoint is None:
                mountpoint = ''
        else:
            mountpoint = ''
        return mountpoint

    def partman_column_format(self):
        partition = self.itemData[1]
        if 'id' not in partition:
            return ''
            #cell.set_property('visible', False)
            #cell.set_property('active', False)
            #cell.set_property('activatable', False)
        elif 'method' in partition:
            if partition['method'] == 'format':
                return Qt.Checked
            else:
                return Qt.Unchecked
            #cell.set_property('visible', True)
            #cell.set_property('active', partition['method'] == 'format')
            #cell.set_property('activatable', 'can_activate_format' in partition)
        else:
            return Qt.Unchecked  ##FIXME should be enabled(False)
            #cell.set_property('visible', True)
            #cell.set_property('active', False)
            #cell.set_property('activatable', False)

    def formatEnabled(self):
        """is the format tickbox enabled"""
        partition = self.itemData[1]
        return 'method' in partition and 'can_activate_format' in partition

    def partman_column_format_toggled(self, value):
        if not self.ubiquity.allowed_change_step:
            return
        if not isinstance(self.ubiquity.dbfilter, partman.Partman):
            return
        #model = user_data
        #devpart = model[path][0]
        #partition = model[path][1]
        devpart = self.itemData[0]
        partition = self.itemData[1]
        if 'id' not in partition or 'method' not in partition:
            return
        self.ubiquity.allow_change_step(False)
        self.ubiquity.dbfilter.edit_partition(devpart, format='dummy')

    def partman_column_size(self):
        partition = self.itemData[1]
        if 'id' not in partition:
            return ''
        else:
            # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
            # partman expects.
            size_mb = int(partition['parted']['size']) / 1000000
            return '%d MB' % size_mb

    def partman_column_used(self):
        partition = self.itemData[1]
        if 'id' not in partition or partition['parted']['fs'] == 'free':
            return ''
        elif 'resize_min_size' not in partition:
            return self.ubiquity.get_string('partition_used_unknown')
        else:
            # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
            # partman expects.
            size_mb = int(partition['resize_min_size']) / 1000000
            return '%d MB' % size_mb
            
#TODO much of this is duplicated from gtk_ui, abstract it
class ResizeWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        frame = QFrame(self)
        layout = QHBoxLayout(self)
        layout.addWidget(frame)

        frame.setLineWidth(1)
        frame.setFrameShadow(QFrame.Plain)
        frame.setFrameShape(QFrame.StyledPanel)

        layout = QHBoxLayout(frame)
        layout.setMargin(2)
        splitter = QSplitter(frame)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        self.old_os = QFrame(splitter)
        self.old_os.setLineWidth(1)
        self.old_os.setFrameShadow(QFrame.Raised)
        self.old_os.setFrameShape(QFrame.Box)
        layout = QHBoxLayout(self.old_os)
        self.old_os_label = QLabel(self.old_os)
        layout.addWidget(self.old_os_label)

        self.new_os = QFrame(splitter)
        self.new_os.setLineWidth(1)
        self.new_os.setFrameShadow(QFrame.Raised)
        self.new_os.setFrameShape(QFrame.Box)
        layout = QHBoxLayout(self.new_os)
        self.new_os_label = QLabel(self.new_os)
        layout.addWidget(self.new_os_label)
        
        self.old_os_label.setAlignment(Qt.AlignHCenter)
        self.new_os_label.setAlignment(Qt.AlignHCenter)

        self.old_os.setAutoFillBackground(True)
        palette = self.old_os.palette()
        palette.setColor(QPalette.Active, QPalette.Background, QColor("#FFA500"))
        palette.setColor(QPalette.Inactive, QPalette.Background, QColor("#FFA500"))

        self.new_os.setAutoFillBackground(True)
        palette = self.new_os.palette()
        palette.setColor(QPalette.Active, QPalette.Background, Qt.white)
        palette.setColor(QPalette.Inactive, QPalette.Background, Qt.white)

        self.part_size = 0
        self.old_os_title = ''
        self._set_new_os_title()
        self.max_size = 0
        self.min_size = 0
            
        QApplication.instance().connect(splitter, 
            SIGNAL("splitterMoved(int,int)"), self._spitter_moved)

    # handle the moved splitter slot and emit a custom signal
    def _spitter_moved(self, pos, index):
        self.emit(SIGNAL("resized(int, int)"), pos, index)

    def paintEvent(self, event):
        self._update_min()
        self._update_max()

        s1 = self.old_os.width()
        s2 = self.new_os.width()
        total = s1 + s2

        percent = (float(s1) / float(total))
        txt = '%s\n%.0f%% (%s)' % (self.old_os_title,
            (percent * 100.0),
            format_size(percent * self.part_size))
        self.old_os_label.setText(txt)
        self.old_os.setToolTip(txt)

        percent = (float(s2) / float(total))
        txt = '%s\n%.0f%% (%s)' % (self.new_os_title,
            (percent * 100.0),
            format_size(percent * self.part_size))
        self.new_os_label.setText(txt)
        self.new_os.setToolTip(txt)

    def set_min(self, size):
        self.min_size = size

    def set_max(self, size):
        self.max_size = size

    def set_part_size(self, size):
        self.part_size = size

    def _update_min(self):
        total = self.new_os.width() + self.old_os.width()
        tmp = self.min_size / self.part_size
        pixels = int(tmp * total)
        self.old_os.setMinimumWidth(pixels)

    def _update_max(self):
        total = self.new_os.width() + self.old_os.width()
        tmp = ((self.part_size - self.max_size) / self.part_size)
        pixels = int(tmp * total)
        self.new_os.setMinimumWidth(pixels)

    def _set_new_os_title(self):
        self.new_os_title = ''
        fp = None
        try:
            fp = open('/cdrom/.disk/info')
            line = fp.readline()
            if line:
                self.new_os_title = ' '.join(line.split()[:2])
        except:
            syslog.syslog(syslog.LOG_ERR,
                "Unable to determine the distribution name from /cdrom/.disk/info")
        finally:
            if fp is not None:
                fp.close()
        if not self.new_os_title:
            self.new_os_title = 'Kubuntu'

    def set_device(self, dev):
        '''Sets the title of the old partition to the name found in os_prober.
           On failure, sets the title to the device name or the empty string.'''
        if dev:
            self.old_os_title = find_in_os_prober(dev)
        if dev and not self.old_os_title:
            self.old_os_title = dev
        elif not self.old_os_title:
            self.old_os_title = ''

    def get_size(self):
        '''Returns the size of the old partition, clipped to the minimum and
           maximum sizes.'''
        s1 = self.old_os.width()
        s2 = self.new_os.width()
        totalwidth = s1 + s2
        size = int(float(s1) * self.part_size / float(totalwidth))
        if size < self.min_size:
            return self.min_size
        elif size > self.max_size:
            return self.max_size
        else:
            return size

    def get_value(self):
        '''Returns the percent the old partition is of the maximum size it can be.'''
        return int((float(self.get_size()) / self.max_size) * 100)