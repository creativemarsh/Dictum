import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Dictum")
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.move(100, 100)   # force on-screen position
    window.show()
    window.activateWindow()
    window.raise_()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
