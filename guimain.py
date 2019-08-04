import sys
import datetime as dt

from PySide2.QtWidgets import QApplication, QMainWindow, QWidget


class Gui(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('XtraPlaceMatcher GUI')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = Gui()
    gui.show()
    sys.exit(app.exec_())
