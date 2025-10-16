from __future__ import annotations
import typing
from typing import List, Optional, Callable, Any
from PySide6 import QtWidgets, QtGui, QtCore

__all__ = [
    "combo_box_factory",
    "text_line_with_action_editor",
    "text_box_with_action_editor",
    "multiple_string_widget_editor",
    "StringListEditor",
]


class DelegateFactory(typing.Protocol):
    def __call__(self, parent: QtWidgets.QWidget) -> QtWidgets.QWidget: ...


def combo_box_factory(
    parent: QtWidgets.QWidget, choices: List[str]
) -> QtWidgets.QComboBox:
    widget = QtWidgets.QComboBox(parent=parent)
    # widget.setCurrentText(node.value)
    widget.addItems(choices)
    return widget


def text_line_with_action_editor(
    parent: QtWidgets.QWidget, action: QtGui.QAction
) -> QtWidgets.QLineEdit:
    widget = QtWidgets.QLineEdit(parent=parent)
    action.setParent(widget)
    widget.addAction(
        action, QtWidgets.QLineEdit.ActionPosition.TrailingPosition
    )
    return widget


def text_box_with_action_editor(
    actions: Optional[List[QtGui.QAction]] = None,
    minimum_number_lines_visible: int = 3,
    toolbar_position=QtCore.Qt.ToolBarArea.TopToolBarArea,
    parent: Optional[QtWidgets.QWidget] = None,
) -> EditorWithToolBox:
    text_edit = QtWidgets.QTextEdit(parent=parent)
    text_edit.setAcceptRichText(False)
    widget = EditorWithToolBox(text_edit, toolbar_position=toolbar_position)
    for action in actions or []:
        widget.add_action(action)
    two_line_height = (
        text_edit.fontMetrics().lineSpacing() * minimum_number_lines_visible
    )
    document_margin = int(
        text_edit.document().documentMargin() * minimum_number_lines_visible
    )
    widget.setMinimumHeight(two_line_height + document_margin)
    widget.set_data = lambda value: text_edit.setText(value.value)
    widget.get_data = text_edit.toPlainText
    return widget


class EditorWithToolBox(QtWidgets.QWidget):
    _icon_size = QtCore.QSize(15, 15)

    def __init__(
        self,
        decorated: QtWidgets.QWidget,
        toolbar_position: QtCore.Qt.ToolBarArea = QtCore.Qt.ToolBarArea.TopToolBarArea,
    ) -> None:
        super().__init__()
        self.setParent(decorated.parent())
        self.decorated = decorated
        self.decorated.setParent(self)
        self.toolbar = QtWidgets.QToolBar(
            "Toolbar",
            self.decorated,
        )
        self.set_data: Callable[[Any], None] = lambda _: None
        self.get_data: Callable[[], Optional[str]] = lambda: None
        self.toolbar.setOrientation(
            QtCore.Qt.Orientation.Horizontal
            if toolbar_position
            in {
                QtCore.Qt.ToolBarArea.TopToolBarArea.TopToolBarArea.TopToolBarArea,
                QtCore.Qt.ToolBarArea.TopToolBarArea.BottomToolBarArea,
            }
            else QtCore.Qt.Orientation.Vertical
        )
        self.toolbar.setVisible(False)
        self.toolbar.setIconSize(self._icon_size)
        self._layout = (
            QtWidgets.QVBoxLayout()
            if toolbar_position
            in {
                QtCore.Qt.ToolBarArea.TopToolBarArea,
                QtCore.Qt.ToolBarArea.BottomToolBarArea,
            }
            else QtWidgets.QHBoxLayout()
        )
        self.setAutoFillBackground(True)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.setLayout(self._layout)

        if toolbar_position in {
            QtCore.Qt.ToolBarArea.TopToolBarArea,
            QtCore.Qt.ToolBarArea.LeftToolBarArea,
        }:
            self._layout.addWidget(self.toolbar)
            self._layout.addWidget(self.decorated)
        elif toolbar_position in {
            QtCore.Qt.ToolBarArea.BottomToolBarArea,
            QtCore.Qt.ToolBarArea.RightToolBarArea,
        }:
            self._layout.addWidget(self.decorated)
            self._layout.addWidget(self.toolbar)
            self.toolbar.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Preferred,
                QtWidgets.QSizePolicy.Policy.Maximum,
            )
        elif toolbar_position == QtCore.Qt.ToolBarArea.NoToolBarArea:
            self._layout.addWidget(self.decorated)
            self.toolbar.setVisible(False)
        if toolbar_position in {
            QtCore.Qt.ToolBarArea.RightToolBarArea,
            QtCore.Qt.ToolBarArea.LeftToolBarArea,
        }:
            self._layout.setAlignment(
                self.toolbar, QtCore.Qt.AlignmentFlag.AlignTop
            )

    def add_action(self, action: QtGui.QAction) -> None:
        self.toolbar.setVisible(True)
        self.toolbar.addAction(action)
        action.setParent(self.toolbar)


class StringListEditor(QtWidgets.QWidget):
    def _remove_selected_item(self) -> None:
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            self.list_widget.takeItem(current_row)

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.toolbar = QtWidgets.QToolBar("Toolbar", self)
        self.toolbar.setIconSize(QtCore.QSize(15, 15))
        self.add_item_action = QtGui.QAction(
            QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListAdd), "Add", self
        )
        self.add_item_action.triggered.connect(self._add_new_item)
        self.toolbar.addAction(self.add_item_action)

        self.remove_item_action = QtGui.QAction(
            QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListRemove),
            "Remove",
            self,
        )
        self.remove_item_action.triggered.connect(self._remove_selected_item)
        self.remove_item_action.setEnabled(False)
        self.toolbar.addAction(self.remove_item_action)

        self.list_widget = QtWidgets.QListWidget(parent=parent)
        self.list_widget.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.list_widget.itemChanged.connect(self.handle_list_change)

        # The remove action should only be enabled if something is selected
        self.list_widget.itemSelectionChanged.connect(
            lambda: self.remove_item_action.setEnabled(
                True if self.list_widget.currentRow() >= 0 else False
            )
        )

        self.list_widget.setAutoFillBackground(True)
        self.list_widget.setAlternatingRowColors(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.list_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def _add_new_item(self) -> None:
        new_item = QtWidgets.QListWidgetItem()
        new_item.setFlags(new_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(new_item)
        self.list_widget.editItem(new_item)

    @property
    def values(self) -> List[str]:
        values = []
        for i in range(self.list_widget.count()):
            results = self.list_widget.item(i).text()
            if results.strip() != "":
                values.append(results)
        return values

    @values.setter
    def values(self, values: List[str]):
        self.list_widget.clear()
        self.list_widget.addItems(values)
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)

    def handle_list_change(self, item: QtWidgets.QListWidgetItem) -> None:
        if item.text().strip() == "":
            self.list_widget.takeItem(self.list_widget.row(item))


def multiple_string_widget_editor(
    parent: QtWidgets.QWidget,
) -> StringListEditor:
    widget = StringListEditor(parent=parent)
    return widget
