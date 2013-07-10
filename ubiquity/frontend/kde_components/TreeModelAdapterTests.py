#!/usr/bin/env python
import sys
import unittest

from PyQt4 import QtCore
from PyQt4 import QtGui

from TreeModelAdapter import TreeModelAdapter

def create_model(txt):
    model = QtGui.QStandardItemModel()
    parents = [model.invisibleRootItem()]
    last_added_item = None
    last_indent = 0
    for line in txt.strip().splitlines():
        line = line.strip()
        indent = line.count("-")
        assert indent <= last_indent + 1
        item = QtGui.QStandardItem(line[indent:])

        if indent > last_indent:
            parents.append(last_added_item)
        elif indent < last_indent:
            parents = parents[:indent + 1]
        parents[-1].appendRow(item)
        last_added_item = item
        last_indent = indent
    return model


def dump_model(model, indent=0, parent=QtCore.QModelIndex()):
    count = model.rowCount(parent)
    for row in range(count):
        sys.stdout.write(" " * indent + "#%d" % row)
        for col in range(model.columnCount(parent)):
            txt = model.index(row, col, parent).data().toString()
            sys.stdout.write(" %s" % txt)
        print
        index = model.index(row, 0, parent)
        if model.hasChildren(index):
            dump_model(model, indent + 2, index)


class TreeModelAdapterTestCase(unittest.TestCase):
    def test_get_iter_first(self):
        model = create_model(
            """
            1
            -a
            -b
            -c
            2
            -d
            -e
            """
            )
        adapter = TreeModelAdapter(model)
        it = adapter.get_iter_first()
        self.assertEquals(it.row, 0)

        model = QtGui.QStandardItemModel()
        adapter = TreeModelAdapter(model)
        it = adapter.get_iter_first()
        self.assert_(it is None)

    def test_append(self):
        model = QtGui.QStandardItemModel()
        adapter = TreeModelAdapter(model)
        it2 = adapter.append(None, ["root0", "root1"])
        self.assert_(it2 is not None)
        self.assertEquals(adapter[it2], ["root0", "root1"])

        it = adapter.get_iter_first()
        adapter.append(it, ["child0", "child1"])
        parent = model.item(0, 0)
        self.assertEquals(parent.child(0, 0).text(), "child0")
        self.assertEquals(parent.child(0, 1).text(), "child1")

    def test_iter_children(self):
        model = create_model(
            """
            1
            -a
            -b
            -c
            2
            -d
            -e
            """
            )
        adapter = TreeModelAdapter(model)
        it1 = adapter.iter_children(None) # Points to 1
        self.assertEquals(adapter.get(it1, 0), ["1"])
        it2 = adapter.iter_children(it1) # Points to a
        self.assertEquals(adapter.get(it2, 0), ["a"])
        it3 = adapter.iter_children(it2) # None
        self.assert_(it3 is None)

    def test_getitem__(self):
        model = create_model(
            """
            1
            -a
            -b
            -c
            2
            -d
            -e
            """
            )
        adapter = TreeModelAdapter(model)
        self.assertEquals(adapter[0], ["1"])
        self.assertEquals(adapter[1], ["2"])

        it = adapter.iter_children(None)
        self.assertEquals(adapter[it], ["1"])

    def test_iter_next(self):
        model = create_model(
            """
            1
            -a
            -b
            """)
        adapter = TreeModelAdapter(model)
        it = adapter.get_iter_first()
        it = adapter.iter_next(it)
        self.assert_(it is None)

        it = adapter.get_iter_first() # Points to 1
        it2 = adapter.iter_children(it) # Points to a
        it2 = adapter.iter_next(it2) # Points to b
        self.assertEquals(adapter.get(it2, 0), ["b"])
        it2 = adapter.iter_next(it2)
        self.assert_(it2 is None)

    def test_remove(self):
        model = create_model(
            """
            1
            -a
            -b
            """)
        adapter = TreeModelAdapter(model)
        it = adapter.get_iter_first() # Points to 1
        it2 = adapter.iter_children(it) # Points to a
        self.assert_(adapter.remove(it2))
        # it2 now points b
        self.assertEquals(adapter.get(it2, 0), ["b"])

        self.assert_(not adapter.remove(it2))
        self.assertEquals(it2.row, -1)



if __name__ == "__main__":
    unittest.main()
