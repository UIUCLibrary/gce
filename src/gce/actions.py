from __future__ import annotations

import functools
import logging
from typing import Callable, Tuple
import typing
from PySide6 import QtWidgets
import pathlib
import gce.models

if typing.TYPE_CHECKING:
    from gce import gui
    from PySide6 import QtCore

def use_dialog_box_to_confirm_with_user(parent: QtWidgets.QWidget, message: str, message_box_factory=QtWidgets.QMessageBox) -> bool:
    message_box = message_box_factory()
    message_box.setParent(parent)
    message_box.setIcon(QtWidgets.QMessageBox.Icon.Question)
    message_box.setText(message)
    message_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
    message_box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
    reply = message_box.exec()
    if reply == QtWidgets.QMessageBox.StandardButton.Yes:
        return True
    elif reply == QtWidgets.QMessageBox.StandardButton.No:
        return False
    raise ValueError("Unknown reply")

def load_toml(
    parent: gui.MainWindow,
    open_dialog_strategy: Callable[
        [QtWidgets.QWidget], Tuple[str, str]
    ] = functools.partial(
        QtWidgets.QFileDialog.getOpenFileName,
        caption="Open config File",
        filter="Mapping Toml (*.toml);;All Files (*)",
    ),
    confirm_existing_strategy: Callable[
        [QtWidgets.QWidget], bool
    ] = functools.partial(use_dialog_box_to_confirm_with_user, message="The document has unsaved changes. Are you sure you want to load a new file?"),
) -> None:
    if parent.unsaved_changes:
        user_confirmed = confirm_existing_strategy(parent)
        if not user_confirmed:
            return
    file_path, _ = open_dialog_strategy(parent)
    if file_path:
        parent.toml_file = file_path


def save_toml(parent: gui.MainWindow, file_path: QtCore.QUrl) -> None:
    model = typing.cast(gce.models.TomlModel, parent.toml_view.model())
    if model is not None:
        parent.status_message_updated.emit("Saving", logging.INFO)
        file = pathlib.Path(file_path.toLocalFile())
        parent.write_to_file(file, model)
        parent.status_message_updated.emit(f"Saved {file.name}", logging.INFO)
