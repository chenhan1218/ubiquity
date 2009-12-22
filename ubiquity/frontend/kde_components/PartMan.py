# -*- coding: utf-8 -*-

import os
from PyQt4 import uic
from PyQt4.QtGui import *

from ubiquity.frontend.kde_components.PartitionBar import PartitionsBar
from ubiquity.frontend.kde_components.PartitionModel import PartitionModel

_uidir="/usr/share/ubiquity/qt/"

class PartMan(QWidget):
    
    def __init__(self, controller):
        QWidget.__init__(self)
        self.ctrlr = controller
        
        uic.loadUi(os.path.join(_uidir,'stepPartMan.ui'), self)
        self.part_advanced_warning_hbox.setVisible(False)
        
        self.partition_tree_model = PartitionModel(self, self.partition_list_treeview)
        self.partition_list_treeview.setModel(self.partition_tree_model)
        
        #self.partition_button_new_label.clicked[bool].connect(self.on_partition_list_new_label_activate)
        #self.partition_button_new.clicked[bool].connect(self.on_partition_list_new_activate)
        #self.partition_button_edit.clicked[bool].connect(self.on_partition_list_edit_activate)
        #self.partition_button_delete.clicked[bool].connect(self.on_partition_list_delete_activate)
        #self.partition_button_undo.clicked[bool].connect(self.on_partition_list_undo_activate)
        
    def update(self, disk_cache, partition_cache, cache_order):
        self.partition_tree_model.clear()
        
        for child in self.part_advanced_bar_frame.children():
            if isinstance(child, QWidget):
                child.setParent(None)
                del child
        
        partition_bar = None
        indexCount = -1
        for item in cache_order:
            if item in disk_cache:
                # the item is a disk
                indexCount += 1
                partition_bar = PartitionsBar(self.part_advanced_bar_frame)
                self.part_advanced_bar_frame.layout().addWidget(partition_bar)
                
                #hide all the other bars at first
                if indexCount > 0:
                    partition_bar.setVisible(False)
                    
                self.partition_tree_model.append([item, disk_cache[item], partition_bar], self)
            else:
                # the item is a partition, add it to the current bar
                partition = partition_cache[item]
                
                # add the new partition to our tree display
                self.partition_tree_model.append([item, partition, partition_bar], self)
                indexCount += 1
                
                # data for bar display
                size = int(partition['parted']['size'])
                fs = partition['parted']['fs']
                path = partition['parted']['path'].replace("/dev/","")
                if fs == "free":
                    path = fs
                partition_bar.addPartition(path, size, fs)
        
        self.partition_list_treeview.reset()
        
        model = self.partition_list_treeview.selectionModel()
        model.selectionChanged.connect(self.on_treeviewSelectionChanged)
        
    def on_treeviewSelectionChanged(self, unused, deselected):
        self.partition_button_new_label.setEnabled(False)
        self.partition_button_new.setEnabled(False)
        self.partition_button_edit.setEnabled(False)
        self.partition_button_delete.setEnabled(False)
        
        if deselected:
            deIndex = deselected.indexes()[0]
            item = deIndex.internalPointer()
            
            if item.itemData[2]:
                item.itemData[2].setVisible(False)
            
        indexes = self.partition_list_treeview.selectedIndexes()
        if indexes:
            index = indexes[0]
            
            item = index.internalPointer()
            devpart = item.itemData[0]
            partition = item.itemData[1]
            
            bar = item.itemData[2]
            if bar:
                bar.setVisible(True)
        else:
            devpart = None
            partition = None
            
        if not isinstance(self.ctrlr.dbfilter, partman.Page):
            return

        for action in self.ctrlr.dbfilter.get_actions(devpart, partition):
            if action == 'new_label':
                self.partition_button_new_label.setEnabled(True)
            elif action == 'new':
                self.partition_button_new.setEnabled(True)
            elif action == 'edit':
                self.partition_button_edit.setEnabled(True)
            elif action == 'delete':
                self.partition_button_delete.setEnabled(True)
        self.ui.partition_button_undo.setEnabled(True)
        
    def partman_create_dialog(self, devpart, partition):
        if not self.allowed_change_step:
            return
            
        if not isinstance(self.ctrlr.dbfilter, partman.Page):
            return

        self.create_dialog = QDialog(self.ui)
        uic.loadUi("%s/partition_create_dialog.ui" % UIDIR, self.create_dialog)
        self.app.connect(self.create_dialog.partition_create_use_combo, SIGNAL("currentIndexChanged(int)"), self.on_partition_create_use_combo_changed)
        self.translate_widget_children(self.create_dialog)

        # TODO cjwatson 2006-11-01: Because partman doesn't use a question
        # group for these, we have to figure out in advance whether each
        # question is going to be asked.

        if partition['parted']['type'] == 'pri/log':
            # Is there already a primary partition?
            for child in self.partition_tree_model.children():
                data = child.itemData
                otherpart = data[1]
                if (otherpart['dev'] == partition['dev'] and
                    'id' in otherpart and
                    otherpart['parted']['type'] == 'primary'):
                    self.create_dialog.partition_create_type_logical.setChecked(True)
                    break
            else:
                self.create_dialog.partition_create_type_primary.setChecked(True)
        else:
            self.create_dialog.partition_create_type_label.hide()
            self.create_dialog.partition_create_type_widget.hide()
        # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
        # partman expects.
        max_size_mb = int(partition['parted']['size']) / 1000000
        self.create_dialog.partition_create_size_spinbutton.setMaximum(max_size_mb)
        self.create_dialog.partition_create_size_spinbutton.setValue(max_size_mb)

        self.create_dialog.partition_create_place_beginning.setChecked(True)

        self.create_use_method_names = {}
        for method, name, description in self.ctrlr.dbfilter.create_use_as(devpart):
            self.create_use_method_names[description] = name
            self.create_dialog.partition_create_use_combo.addItem(description)
        if self.create_dialog.partition_create_use_combo.count() == 0:
            self.create_dialog.partition_create_use_combo.setEnabled(False)

        self.create_dialog.partition_create_mount_combo.clear()
        for mp, choice_c, choice in self.ctrlr.dbfilter.default_mountpoint_choices():
            ##FIXME gtk frontend has a nifty way of showing the user readable
            ##'choice' text in the drop down, but only selecting the 'mp' text
            self.create_dialog.partition_create_mount_combo.addItem(mp)
        self.create_dialog.partition_create_mount_combo.clearEditText()

        response = self.create_dialog.exec_()

        if (response == QDialog.Accepted and
            isinstance(self.ctrlr.dbfilter, partman.Page)):
            if partition['parted']['type'] == 'primary':
                prilog = partman.PARTITION_TYPE_PRIMARY
            elif partition['parted']['type'] == 'logical':
                prilog = partman.PARTITION_TYPE_LOGICAL
            elif partition['parted']['type'] == 'pri/log':
                if self.create_dialog.partition_create_type_primary.isChecked():
                    prilog = partman.PARTITION_TYPE_PRIMARY
                else:
                    prilog = partman.PARTITION_TYPE_LOGICAL

            if self.create_dialog.partition_create_place_beginning.isChecked():
                place = partman.PARTITION_PLACE_BEGINNING
            else:
                place = partman.PARTITION_PLACE_END

            method_description = unicode(self.create_dialog.partition_create_use_combo.currentText())
            method = self.create_use_method_names[method_description]

            mountpoint = unicode(self.create_dialog.partition_create_mount_combo.currentText())

            self.allow_change_step(False)
            self.ctrlr.dbfilter.create_partition(
                devpart,
                str(self.create_dialog.partition_create_size_spinbutton.value()),
                prilog, place, method, mountpoint)

    def on_partition_create_use_combo_changed (self, *args):
        if not hasattr(self, 'create_use_method_names'):
            return
        known_filesystems = ('ext4', 'ext3', 'ext2', 'reiserfs', 'jfs', 'xfs',
                             'fat16', 'fat32', 'ntfs', 'uboot')
        text = unicode(self.create_dialog.partition_create_use_combo.currentText())
        if text not in self.create_use_method_names:
            return
        method = self.create_use_method_names[text]
        if method not in known_filesystems:
            self.create_dialog.partition_create_mount_combo.clearEditText()
            self.create_dialog.partition_create_mount_combo.setEnabled(False)
        else:
            self.create_dialog.partition_create_mount_combo.setEnabled(True)
            if isinstance(self.ctrlr.dbfilter, partman.Page):
                self.create_dialog.partition_create_mount_combo.clear()
                for mp, choice_c, choice in \
                    self.ctrlr.dbfilter.default_mountpoint_choices(method):
                    self.create_dialog.partition_create_mount_combo.addItem(mp)

    def partman_edit_dialog(self, devpart, partition):
        if not self.allowed_change_step:
            return
        if not isinstance(self.ctrlr.dbfilter, partman.Page):
            return

        self.edit_dialog = QDialog(self.ui)
        uic.loadUi("%s/partition_edit_dialog.ui" % UIDIR, self.edit_dialog)
        self.app.connect(self.edit_dialog.partition_edit_use_combo, SIGNAL("currentIndexChanged(int)"), self.on_partition_edit_use_combo_changed)
        self.translate_widget_children(self.edit_dialog)

        current_size = None
        if ('can_resize' not in partition or not partition['can_resize'] or
            'resize_min_size' not in partition or
            'resize_max_size' not in partition):
            self.edit_dialog.partition_edit_size_label.hide()
            self.edit_dialog.partition_edit_size_spinbutton.hide()
        else:
            # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
            # partman expects.
            min_size_mb = int(partition['resize_min_size']) / 1000000
            cur_size_mb = int(partition['parted']['size']) / 1000000
            max_size_mb = int(partition['resize_max_size']) / 1000000
            # Bad things happen if the current size is out of bounds.
            min_size_mb = min(min_size_mb, cur_size_mb)
            max_size_mb = max(cur_size_mb, max_size_mb)
            self.edit_dialog.partition_edit_size_spinbutton.setMinimum(min_size_mb)
            self.edit_dialog.partition_edit_size_spinbutton.setMaximum(max_size_mb)
            self.edit_dialog.partition_edit_size_spinbutton.setSingleStep(1)
            self.edit_dialog.partition_edit_size_spinbutton.setValue(cur_size_mb)

            current_size = str(self.edit_dialog.partition_edit_size_spinbutton.value())

        self.edit_use_method_names = {}
        method_descriptions = {}
        self.edit_dialog.partition_edit_use_combo.clear()
        for script, arg, option in partition['method_choices']:
            self.edit_use_method_names[option] = arg
            method_descriptions[arg] = option
            self.edit_dialog.partition_edit_use_combo.addItem(option)
        current_method = self.ctrlr.dbfilter.get_current_method(partition)
        if current_method and current_method in method_descriptions:
            current_method_description = method_descriptions[current_method]
            index = self.edit_dialog.partition_edit_use_combo.findText(current_method_description)
            self.edit_dialog.partition_edit_use_combo.setCurrentIndex(index)

        if 'id' not in partition:
            self.edit_dialog.partition_edit_format_label.hide()
            self.edit_dialog.partition_edit_format_checkbutton.hide()
            current_format = False
        elif 'method' in partition:
            self.edit_dialog.partition_edit_format_label.show()
            self.edit_dialog.partition_edit_format_checkbutton.show()
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(
                'can_activate_format' in partition)
            current_format = (partition['method'] == 'format')
        else:
            self.edit_dialog.partition_edit_format_label.show()
            self.edit_dialog.partition_edit_format_checkbutton.show()
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(False)
            current_format = False
        self.edit_dialog.partition_edit_format_checkbutton.setChecked(
            current_format)

        self.edit_dialog.partition_edit_mount_combo.clear()
        if 'mountpoint_choices' in partition:
            for mp, choice_c, choice in partition['mountpoint_choices']:
                ##FIXME gtk frontend has a nifty way of showing the user readable
                ##'choice' text in the drop down, but only selecting the 'mp' text
                self.edit_dialog.partition_edit_mount_combo.addItem(mp)
        current_mountpoint = self.ctrlr.dbfilter.get_current_mountpoint(partition)
        if current_mountpoint is not None:
            index = self.edit_dialog.partition_edit_mount_combo.findText(current_method)
            if index != -1:
                self.edit_dialog.partition_edit_mount_combo.setCurrentIndex(index)
            else:
                self.edit_dialog.partition_edit_mount_combo.addItem(current_mountpoint)
                self.edit_dialog.partition_edit_mount_combo.setCurrentIndex(self.edit_dialog.partition_edit_mount_combo.count() - 1)

        response = self.edit_dialog.exec_()

        if (response == QDialog.Accepted and
            isinstance(self.ctrlr.dbfilter, partman.Page)):
            size = None
            if current_size is not None:
                size = str(self.edit_dialog.partition_edit_size_spinbutton.value())

            method_description = unicode(self.edit_dialog.partition_edit_use_combo.currentText())
            method = self.edit_use_method_names[method_description]

            fmt = self.edit_dialog.partition_edit_format_checkbutton.isChecked()

            mountpoint = unicode(self.edit_dialog.partition_edit_mount_combo.currentText())

            if (current_size is not None and size is not None and
                current_size == size):
                size = None
            if method == current_method:
                method = None
            if fmt == current_format:
                fmt = None
            if mountpoint == current_mountpoint:
                mountpoint = None

            if (size is not None or method is not None or fmt is not None or
                mountpoint is not None):
                self.allow_change_step(False)
                edits = {'size': size, 'method': method,
                         'mountpoint': mountpoint}
                if fmt is not None:
                    edits['format'] = 'dummy'
                self.ctrlr.dbfilter.edit_partition(devpart, **edits)

    def on_partition_edit_use_combo_changed(self, *args):
        if not hasattr(self, 'edit_use_method_names'):
            return
        # If the selected method isn't a filesystem, then selecting a mount
        # point makes no sense. TODO cjwatson 2007-01-31: Unfortunately we
        # have to hardcode the list of known filesystems here.
        known_filesystems = ('ext4', 'ext3', 'ext2', 'reiserfs', 'jfs', 'xfs',
                             'fat16', 'fat32', 'ntfs', 'uboot')
        text = unicode(self.edit_dialog.partition_edit_use_combo.currentText())
        if text not in self.edit_use_method_names:
            return
        method = self.edit_use_method_names[text]
        if method not in known_filesystems:
            self.edit_dialog.partition_edit_mount_combo.clearEditText()
            self.edit_dialog.partition_edit_mount_combo.setEnabled(False)
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(False)
        else:
            self.edit_dialog.partition_edit_mount_combo.setEnabled(True)
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(True)
            if isinstance(self.ctrlr.dbfilter, partman.Page):
                self.edit_dialog.partition_edit_mount_combo.clear()
                for mp, choice_c, choice in \
                    self.ctrlr.dbfilter.default_mountpoint_choices(method):
                    self.edit_dialog.partition_edit_mount_combo.addItem(mp)

    def on_partition_list_treeview_activated(self, index):
        if not self.allowed_change_step:
            return
        item = index.internalPointer()
        devpart = item.itemData[0]
        partition = item.itemData[1]

        if 'id' not in partition:
            # Are there already partitions on this disk? If so, don't allow
            # activating the row to offer to create a new partition table,
            # to avoid mishaps.
            for child in self.partition_tree_model.children():
                data = child.itemData
                otherpart = data[1]
                if otherpart['dev'] == partition['dev'] and 'id' in otherpart:
                    break
            else:
                if not isinstance(self.ctrlr.dbfilter, partman.Page):
                    return
                self.allow_change_step(False)
                self.ctrlr.dbfilter.create_label(devpart)
        elif partition['parted']['fs'] == 'free':
            if 'can_new' in partition and partition['can_new']:
                self.partman_create_dialog(devpart, partition)
        else:
            self.partman_edit_dialog(devpart, partition)

    def on_partition_list_new_label_activate(self, *args):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]

        if not self.allowed_change_step:
            return
        if not isinstance(self.ctrlr.dbfilter, partman.Page):
            return
        self.allow_change_step(False)
        self.ctrlr.dbfilter.create_label(devpart)

    def on_partition_list_new_activate(self, *args):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]
        partition = item.itemData[1]
        self.partman_create_dialog(devpart, partition)

    def on_partition_list_edit_activate(self, *args):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]
        partition = item.itemData[1]
        self.partman_edit_dialog(devpart, partition)

    def on_partition_list_delete_activate(self, *args):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]

        if not self.allowed_change_step:
            return
        if not isinstance(self.ctrlr.dbfilter, partman.Page):
            return
        self.allow_change_step(False)
        self.ctrlr.dbfilter.delete_partition(devpart)

    def on_partition_list_undo_activate(self, *args):
        if not self.allowed_change_step:
            return
        if not isinstance(self.ctrlr.dbfilter, partman.Page):
            return
        self.allow_change_step(False)
        self.ctrlr.dbfilter.undo()
        
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    app.setStyle("Oxygen")
    
    _uidir = '../../../gui/qt'
    
    styleFile = os.path.join(_uidir, "style.qss")
    sf = open(styleFile, 'r')
    app.setStyleSheet(sf.read())
    sf.close()
    
    win = PartMan(None)
    win.setObjectName("widgetStack")
    win.show()
    
    cache_order = [u'/var/lib/partman/devices/=dev=sda//',                                                 
                 u'/var/lib/partman/devices/=dev=sda//32256-8167703039',                                 
                 u'/var/lib/partman/devices/=dev=sda//8167735296-8587192319',                            
                 u'/var/lib/partman/devices/=dev=sdb//',                                                 
                 u'/var/lib/partman/devices/=dev=sdb//32256-5074997759',                                 
                 u'/var/lib/partman/devices/=dev=sdb//5075030016-5362882559',                            
                 u'/var/lib/partman/devices/=dev=sdc//',                                                 
                 u'/var/lib/partman/devices/=dev=sdc//32256-5074997759',                                 
                 u'/var/lib/partman/devices/=dev=sdc//5075030016-5362882559']
                 
    disk_cache = {u'/var/lib/partman/devices/=dev=sda//': {'dev': u'=dev=sda',                             
                                                         'device': '/dev/sda',                           
                                                         'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sda//',
                                                         'label': ['msdos']},                                                        
                u'/var/lib/partman/devices/=dev=sdb//': {'dev': u'=dev=sdb',                                                         
                                                         'device': '/dev/sdb',                                                       
                                                         'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sdb//',
                                                         'label': ['msdos']},                                                        
                u'/var/lib/partman/devices/=dev=sdc//': {'dev': u'=dev=sdc',                                                         
                                                         'device': '/dev/sdc',                                                       
                                                         'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sdc//',
                                                         'label': ['msdos']}}
                                                         
    partition_cache = {u'/var/lib/partman/devices/=dev=sda//32256-8167703039': {'can_resize': True,                                    
                                                                              'detected_filesystem': 'ext4',                         
                                                                              'dev': u'=dev=sda',                                    
                                                                              'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sda//32256-8167703039',                                                                                                                                                        
                                                                              'id': u'32256-8167703039',                                                         
                                                                              'method_choices': [(u'25filesystem',                                               
                                                                                                  u'ext4',                                                       
                                                                                                  u'Ext4 journaling file system'),                               
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'ext3',                                                       
                                                                                                  u'Ext3 journaling file system'),                               
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'ext2',                                                       
                                                                                                  u'Ext2 file system'),                                          
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'reiserfs',                                                   
                                                                                                  u'ReiserFS journaling file system'),                           
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'jfs',                                                        
                                                                                                  u'JFS journaling file system'),                                
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'xfs',                                                        
                                                                                                  u'XFS journaling file system'),                                
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'fat16',                                                      
                                                                                                  u'FAT16 file system'),                                         
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'fat32',                                                      
                                                                                                  u'FAT32 file system'),                                         
                                                                                                 (u'40swap',                                                     
                                                                                                  u'swap',                                                       
                                                                                                  u'swap area'),                                                 
                                                                                                 (u'70dont_use',                                                 
                                                                                                  u'dontuse',                                                    
                                                                                                  u'do not use the partition')],                                 
                                                                              'parent': u'/dev/sda',                                                             
                                                                              'parted': {'fs': 'ext4',                                                           
                                                                                         'id': '32256-8167703039',                                               
                                                                                         'name': '',                                                             
                                                                                         'num': '1',                                                             
                                                                                         'path': '/dev/sda1',                                                    
                                                                                         'size': '8167670784',                                                   
                                                                                         'type': 'primary'},                                                     
                                                                              'resize_max_size': 8167670784,                                                     
                                                                              'resize_min_size': 2758852608,                                                     
                                                                              'resize_pref_size': 8167670784},                                                   
                     u'/var/lib/partman/devices/=dev=sda//8167735296-8587192319': {'can_resize': True,                                                           
                                                                                   'detected_filesystem': 'linux-swap',                                          
                                                                                   'dev': u'=dev=sda',                                                           
                                                                                   'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sda//8167735296-8587192319',                                                                                                                                              
                                                                                   'id': u'8167735296-8587192319',                                               
                                                                                   'method': 'swap',                                                             
                                                                                   'method_choices': [(u'25filesystem',                                          
                                                                                                       u'ext4',                                                  
                                                                                                       u'Ext4 journaling file system'),                          
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'ext3',                                                  
                                                                                                       u'Ext3 journaling file system'),                          
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'ext2',                                                  
                                                                                                       u'Ext2 file system'),                                     
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'reiserfs',                                              
                                                                                                       u'ReiserFS journaling file system'),                      
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'jfs',                                                   
                                                                                                       u'JFS journaling file system'),                           
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'xfs',                                                   
                                                                                                       u'XFS journaling file system'),                           
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'fat16',                                                 
                                                                                                       u'FAT16 file system'),                                    
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'fat32',                                                 
                                                                                                       u'FAT32 file system'),                                    
                                                                                                      (u'40swap',                                                
                                                                                                       u'swap',                                                  
                                                                                                       u'swap area'),                                            
                                                                                                      (u'70dont_use',                                            
                                                                                                       u'dontuse',                                               
                                                                                                       u'do not use the partition')],                            
                                                                                   'parent': u'/dev/sda',                                                        
                                                                                   'parted': {'fs': 'linux-swap',                                                
                                                                                              'id': '8167735296-8587192319',                                     
                                                                                              'name': '',                                                        
                                                                                              'num': '5',                                                        
                                                                                              'path': '/dev/sda5',                                               
                                                                                              'size': '419457024',                                               
                                                                                              'type': 'logical'},                                                
                                                                                   'resize_max_size': 419457024,                                                 
                                                                                   'resize_min_size': 4096,                                                      
                                                                                   'resize_pref_size': 419457024},                                               
                     u'/var/lib/partman/devices/=dev=sdb//32256-5074997759': {'can_resize': True,                                                                
                                                                              'detected_filesystem': 'ext4',                                                     
                                                                              'dev': u'=dev=sdb',                                                                
                                                                              'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sdb//32256-5074997759',                                                                                                                                                        
                                                                              'id': u'32256-5074997759',                                                         
                                                                              'method_choices': [(u'25filesystem',                                               
                                                                                                  u'ext4',                                                       
                                                                                                  u'Ext4 journaling file system'),                               
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'ext3',                                                       
                                                                                                  u'Ext3 journaling file system'),                               
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'ext2',                                                       
                                                                                                  u'Ext2 file system'),                                          
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'reiserfs',                                                   
                                                                                                  u'ReiserFS journaling file system'),                           
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'jfs',                                                        
                                                                                                  u'JFS journaling file system'),                                
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'xfs',                                                        
                                                                                                  u'XFS journaling file system'),                                
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'fat16',                                                      
                                                                                                  u'FAT16 file system'),                                         
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'fat32',                                                      
                                                                                                  u'FAT32 file system'),                                         
                                                                                                 (u'40swap',                                                     
                                                                                                  u'swap',                                                       
                                                                                                  u'swap area'),                                                 
                                                                                                 (u'70dont_use',                                                 
                                                                                                  u'dontuse',                                                    
                                                                                                  u'do not use the partition')],                                 
                                                                              'parent': u'/dev/sdb',                                                             
                                                                              'parted': {'fs': 'ext4',                                                           
                                                                                         'id': '32256-5074997759',                                               
                                                                                         'name': '',                                                             
                                                                                         'num': '1',                                                             
                                                                                         'path': '/dev/sdb1',                                                    
                                                                                         'size': '5074965504',                                                   
                                                                                         'type': 'primary'},                                                     
                                                                              'resize_max_size': 5074965504,                                                     
                                                                              'resize_min_size': 223924224,                                                      
                                                                              'resize_pref_size': 5074965504},                                                   
                     u'/var/lib/partman/devices/=dev=sdb//5075030016-5362882559': {'can_resize': True,                                                           
                                                                                   'detected_filesystem': 'linux-swap',                                          
                                                                                   'dev': u'=dev=sdb',                                                           
                                                                                   'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sdb//5075030016-5362882559',                                                                                                                                              
                                                                                   'id': u'5075030016-5362882559',                                               
                                                                                   'method': 'swap',                                                             
                                                                                   'method_choices': [(u'25filesystem',                                          
                                                                                                       u'ext4',                                                  
                                                                                                       u'Ext4 journaling file system'),                          
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'ext3',                                                  
                                                                                                       u'Ext3 journaling file system'),                          
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'ext2',                                                  
                                                                                                       u'Ext2 file system'),                                     
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'reiserfs',                                              
                                                                                                       u'ReiserFS journaling file system'),                      
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'jfs',                                                   
                                                                                                       u'JFS journaling file system'),                           
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'xfs',                                                   
                                                                                                       u'XFS journaling file system'),                           
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'fat16',                                                 
                                                                                                       u'FAT16 file system'),                                    
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'fat32',                                                 
                                                                                                       u'FAT32 file system'),                                    
                                                                                                      (u'40swap',                                                
                                                                                                       u'swap',                                                  
                                                                                                       u'swap area'),                                            
                                                                                                      (u'70dont_use',                                            
                                                                                                       u'dontuse',                                               
                                                                                                       u'do not use the partition')],                            
                                                                                   'parent': u'/dev/sdb',                                                        
                                                                                   'parted': {'fs': 'linux-swap',                                                
                                                                                              'id': '5075030016-5362882559',                                     
                                                                                              'name': '',                                                        
                                                                                              'num': '5',                                                        
                                                                                              'path': '/dev/sdb5',                                               
                                                                                              'size': '287852544',                                               
                                                                                              'type': 'logical'},                                                
                                                                                   'resize_max_size': 287852544,                                                 
                                                                                   'resize_min_size': 4096,                                                      
                                                                                   'resize_pref_size': 287852544},                                               
                     u'/var/lib/partman/devices/=dev=sdc//32256-5074997759': {'can_resize': True,                                                                
                                                                              'detected_filesystem': 'ext4',                                                     
                                                                              'dev': u'=dev=sdc',                                                                
                                                                              'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sdc//32256-5074997759',                                                                                                                                                        
                                                                              'id': u'32256-5074997759',                                                         
                                                                              'method_choices': [(u'25filesystem',                                               
                                                                                                  u'ext4',                                                       
                                                                                                  u'Ext4 journaling file system'),                               
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'ext3',                                                       
                                                                                                  u'Ext3 journaling file system'),                               
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'ext2',                                                       
                                                                                                  u'Ext2 file system'),                                          
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'reiserfs',                                                   
                                                                                                  u'ReiserFS journaling file system'),                           
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'jfs',                                                        
                                                                                                  u'JFS journaling file system'),                                
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'xfs',                                                        
                                                                                                  u'XFS journaling file system'),                                
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'fat16',                                                      
                                                                                                  u'FAT16 file system'),                                         
                                                                                                 (u'25filesystem',                                               
                                                                                                  u'fat32',                                                      
                                                                                                  u'FAT32 file system'),                                         
                                                                                                 (u'40swap',                                                     
                                                                                                  u'swap',                                                       
                                                                                                  u'swap area'),                                                 
                                                                                                 (u'70dont_use',                                                 
                                                                                                  u'dontuse',                                                    
                                                                                                  u'do not use the partition')],                                 
                                                                              'parent': u'/dev/sdc',                                                             
                                                                              'parted': {'fs': 'ext4',                                                           
                                                                                         'id': '32256-5074997759',                                               
                                                                                         'name': '',                                                             
                                                                                         'num': '1',                                                             
                                                                                         'path': '/dev/sdc1',                                                    
                                                                                         'size': '5074965504',                                                   
                                                                                         'type': 'primary'},                                                     
                                                                              'resize_max_size': 5074965504,                                                     
                                                                              'resize_min_size': 223928320,                                                      
                                                                              'resize_pref_size': 5074965504},                                                   
                     u'/var/lib/partman/devices/=dev=sdc//5075030016-5362882559': {'can_resize': True,                                                           
                                                                                   'detected_filesystem': 'linux-swap',                                          
                                                                                   'dev': u'=dev=sdc',                                                           
                                                                                   'display': u'60partition_tree__________/var/lib/partman/devices/=dev=sdc//5075030016-5362882559',                                                                                                                                              
                                                                                   'id': u'5075030016-5362882559',                                               
                                                                                   'method': 'swap',                                                             
                                                                                   'method_choices': [(u'25filesystem',                                          
                                                                                                       u'ext4',                                                  
                                                                                                       u'Ext4 journaling file system'),                          
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'ext3',                                                  
                                                                                                       u'Ext3 journaling file system'),                          
                                                                                                      (u'25filesystem',                                          
                                                                                                       u'ext2',                                                  
                                                                                                       u'Ext2 file system'),                                     
                                                                                                      (u'25filesystem',
                                                                                                       u'reiserfs',
                                                                                                       u'ReiserFS journaling file system'),
                                                                                                      (u'25filesystem',
                                                                                                       u'jfs',
                                                                                                       u'JFS journaling file system'),
                                                                                                      (u'25filesystem',
                                                                                                       u'xfs',
                                                                                                       u'XFS journaling file system'),
                                                                                                      (u'25filesystem',
                                                                                                       u'fat16',
                                                                                                       u'FAT16 file system'),
                                                                                                      (u'25filesystem',
                                                                                                       u'fat32',
                                                                                                       u'FAT32 file system'),
                                                                                                      (u'40swap',
                                                                                                       u'swap',
                                                                                                       u'swap area'),
                                                                                                      (u'70dont_use',
                                                                                                       u'dontuse',
                                                                                                       u'do not use the partition')],
                                                                                   'parent': u'/dev/sdc',
                                                                                   'parted': {'fs': 'linux-swap',
                                                                                              'id': '5075030016-5362882559',
                                                                                              'name': '',
                                                                                              'num': '5',
                                                                                              'path': '/dev/sdc5',
                                                                                              'size': '287852544',
                                                                                              'type': 'logical'},
                                                                                   'resize_max_size': 287852544,
                                                                                   'resize_min_size': 4096,
                                                                                   'resize_pref_size': 287852544}}
    
    win.update(disk_cache, partition_cache, cache_order)
    win.update(disk_cache, partition_cache, cache_order)
    
    sys.exit(app.exec_())