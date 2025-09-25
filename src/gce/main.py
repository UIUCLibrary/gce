from PySide6 import QtWidgets, QtCore
from gce import gui
import sys


def set_color_scheme(color_scheme, dialog: gui.JinjaEditorDialog) -> None:
    if color_scheme == QtCore.Qt.ColorScheme.Light:
        dialog.pygments_style = "sas"
    elif color_scheme == QtCore.Qt.ColorScheme.Dark:
        dialog.pygments_style = "monokai"
    else:
        print("System color scheme changed to Unknown")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)

    dialog = gui.JinjaEditorDialog()
    app.styleHints().colorSchemeChanged.connect(
        lambda colors_scheme: set_color_scheme(colors_scheme, dialog)
    )
    set_color_scheme(app.styleHints().colorScheme(), dialog)
    dialog.setMinimumWidth(640)
    dialog.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
