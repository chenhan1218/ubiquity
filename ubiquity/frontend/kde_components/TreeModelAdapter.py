from PyQt4 import QtGui

class Iterator(object):
    def __init__(self, model, parent_item, row):
        self.model = model
        self.parent_item = parent_item
        self.row = row

    def _get_item(self, column=0):
        return self.parent_item.child(self.row, column)

class TreeModelAdapter(object):
    """
    Wraps a QStandardItemModel and exposes it using a Gtk.TreeModel-like API
    """
    def __init__(self, model):
        self.model = model

    def get_iter_first(self):
        return self._create_iterator(None, 0)

    def append(self, parent_it, row=None):
        if parent_it is None:
            parent_item = self.model.invisibleRootItem()
        else:
            parent_item = parent_it._get_item()
        if row is None:
            items = [QtGui.QStandardItem()]
        else:
            items = [QtGui.QStandardItem(x) for x in row]
        parent_item.appendRow(items)
        return self._create_iterator(parent_it, parent_item.rowCount() - 1)

    def get(self, it, column, *args):
        cols = [column]
        cols.extend(args)
        return [it._get_item(x).text() for x in cols]

    def iter_children(self, parent_it):
        return self._create_iterator(parent_it, 0)

    def iter_next(self, it):
        if it is None:
            return None
        if it.row + 1 < it.parent_item.rowCount():
            return Iterator(self.model, it.parent_item, it.row + 1)
        else:
            return None

    def __getitem__(self, row_or_it):
        if isinstance(row_or_it, int):
            it = self._create_iterator(None, row_or_it)
        else:
            it = row_or_it
        return [it.parent_item.child(it.row, x).text() for x in range(self.model.columnCount())]

    def _create_iterator(self, parent_it, row):
        if parent_it is None:
            parent_item = self.model.invisibleRootItem()
        else:
            parent_item = parent_it._get_item()

        if row < parent_item.rowCount():
            return Iterator(self.model, parent_item, row)
        else:
            return None

    def remove(self, it):
        if it is None:
            return
        it.parent_item.removeRow(it.row)
        if it.row < it.parent_item.rowCount():
            return True
        else:
            it.row = -1
            return False
