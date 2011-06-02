from PyQt4.QtCore import Qt
from PyQt4.QtGui import QLabel, QHBoxLayout, QPixmap, QFrame, QPalette, QCheckBox
import sys

class StateBox(QFrame):
    def __init__(self, parent, text=''):
        QFrame.__init__(self, parent)
        self.setFrameStyle(QFrame.StyledPanel|QFrame.Sunken)
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, Qt.white)
        self.setPalette(palette)
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


class CheckBox(QCheckBox):
    print "im in ur qtwidgets, overridin ur functions"
    def __init__(self, parent=None):
        print "INITIALIZING QCHECKBOX"
        QCheckBox.__init__(self, parent)

    def set_sensitive(self, state):
        QCheckBox.setEnabled(self,state)

    def set_active(self, state):
        QCheckBox.setChecked(self,state)

    def get_active(self):
        return QCheckBox.isChecked(self)
 
