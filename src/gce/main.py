from PySide6 import QtWidgets
from gce import gui
import sys

def main() -> None:
    app = QtWidgets.QApplication(sys.argv)

    dialog = gui.JinjaEditorDialog()
    dialog.setMinimumWidth(640)
    dialog.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
