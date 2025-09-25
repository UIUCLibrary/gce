from PySide6 import QtWidgets
from gce import gui
import sys

def main() -> None:
    app = QtWidgets.QApplication(sys.argv)

    dialog = gui.JinjaEditorDialog()
    with open("/Users/hborcher/PycharmProjects/sandbox/sample.xml", "r") as f:
        dialog.xml_text = f.read()
    dialog.setMinimumWidth(640)
    dialog.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
