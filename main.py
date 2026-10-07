import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from gui.main_window import MainWindow

# Nombre del canal local que identifica a la instancia en ejecución.
INSTANCE_KEY = "dictum-single-instance"


def _notify_running_instance() -> bool:
    """Si ya hay un Dictum abierto, le pide que muestre su ventana y devuelve True."""
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_KEY)
    if not sock.waitForConnected(300):
        return False
    sock.write(b"show")
    sock.flush()
    sock.waitForBytesWritten(300)
    sock.disconnectFromServer()
    return True


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Dictum")
    app.setQuitOnLastWindowClosed(False)

    # Dos instancias registrarían el hotkey dos veces y procesarían cada
    # dictado por duplicado.
    if _notify_running_instance():
        return 0

    window = MainWindow()

    server = QLocalServer()
    QLocalServer.removeServer(INSTANCE_KEY)   # restos de un cierre abrupto
    server.listen(INSTANCE_KEY)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), window._show_window()))

    window.move(100, 100)   # force on-screen position
    window.show()
    window.activateWindow()
    window.raise_()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
