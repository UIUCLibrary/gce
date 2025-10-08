from __future__ import annotations

import functools
import logging
from typing import Callable, Tuple
import typing
from PySide6 import QtWidgets

if typing.TYPE_CHECKING:
    from gce import gui


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
        parent.set_toml_file(file_path)
