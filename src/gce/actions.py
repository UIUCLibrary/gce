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


def load_toml(
    parent: gui.MainWindow,
    open_dialog_strategy: Callable[
        [QtWidgets.QWidget], Tuple[str, str]
    ] = functools.partial(
        QtWidgets.QFileDialog.getOpenFileName,
        caption="Open config File",
        filter="Mapping Toml (*.toml);;All Files (*)",
    ),
) -> None:
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
