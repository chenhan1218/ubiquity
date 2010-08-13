from PyQt4 import uic
from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QPixmap

class StateBox(QWidget):
    def __init__(self, parent, text=''):
        QWidget.__init__(self, parent)
        layout = QHBoxLayout(self)
        self.setLayout(layout)
        self.image = QLabel(self)
        self.image.setPixmap(QPixmap("/usr/share/icons/oxygen/32x32/actions/dialog-ok.png"))
        layout.addWidget(self.image)
        self.label = QLabel(text, self)
        layout.addWidget(self.label)
        layout.addStretch()
        self.status = True

    def set_state(self, state):
        self.status = state
        if state:
            self.image.setPixmap(QPixmap("/usr/share/icons/oxygen/32x32/actions/dialog-ok.png"))
        else:
            self.image.setPixmap(QPixmap("/usr/share/icons/oxygen/32x32/actions/dialog-cancel.png"))

    def get_state(self):
        return self.status

    def set_property(self, prop, value):
        if prop == "label":
            self.label.setText(value)
        else:
            print >>sys.stderr, "qtwidgets.StateBox set_property() only implemented for label"
