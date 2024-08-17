import sys
import os
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtQml import QQmlApplicationEngine


class Backend(QObject):
    fileOpened = pyqtSignal(str)

    @pyqtSlot(str)
    def openFile(self, filePath):
        if os.path.exists(filePath):
            self.fileOpened.emit(filePath)
            print(f"File opened: {filePath}")
        else:
            print(f"Error: File does not exist - {filePath}")


def main():
    app = QApplication(sys.argv)

    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    qml_file_path = os.path.join(os.path.dirname(__file__), "main.qml")

    if not os.path.exists(qml_file_path):
        print(f"Error: QML file not found at {qml_file_path}")
        sys.exit(-1)

    print(f"Loading QML file from {qml_file_path}")
    try:
        engine.load(QUrl.fromLocalFile(qml_file_path))
    except Exception as e:
        print(f"Error loading QML file: {e}")
        sys.exit(-1)

    if not engine.rootObjects():
        print("Error: No root objects loaded. Exiting.")
        sys.exit(-1)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
