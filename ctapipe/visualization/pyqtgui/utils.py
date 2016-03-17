from PyQt4 import QtGui


def confirm_question(question, parent=None):
        reply = QtGui.QMessageBox.question(
            parent, 'Message',
            "Are you sure to quit?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No,
        )

        if reply == QtGui.QMessageBox.Yes:
            return True
        return False
