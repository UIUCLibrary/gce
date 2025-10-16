from unittest.mock import Mock

import pytest
from PySide6 import QtWidgets, QtGui, QtCore

import gce.editors

def test_multiple_string_widget_editor(qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    editor = gce.editors.multiple_string_widget_editor(parent)
    assert editor.values == []


class TestStringListEditor:
    def test_add_item_action(self, qtbot):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = gce.editors.StringListEditor(parent)
        assert widget.list_widget.count() == 0
        widget.add_item_action.trigger()
        assert widget.list_widget.count() == 1

    def test_remove_item_action(self, qtbot):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = gce.editors.StringListEditor(parent)
        widget.add_item_action.trigger()
        assert widget.list_widget.count() == 1
        widget.list_widget.setCurrentRow(0)
        widget.remove_item_action.trigger()
        assert widget.list_widget.count() == 0


    @pytest.mark.parametrize(
        "text, expected",
        [
            ("some_value", False),
            ("", True),
            (" ", True),
        ]
    )
    def test_handle_list_change(self, qtbot, text, expected):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        widget = gce.editors.StringListEditor(parent)
        widget.list_widget = Mock()
        item = Mock(spec_set=QtWidgets.QListWidgetItem, text=Mock(return_value=text))
        widget.handle_list_change(item)

        assert (widget.list_widget.takeItem.call_count == 1) is expected

class TestEditorWithToolBox:
    @pytest.mark.parametrize(
        "actions_args,expected_visible",
        [
            ([], False),
            ([("open",)], True),
         ]
    )
    def test_toolbar_is_not_visible_unless_actions(self, qtbot, actions_args, expected_visible):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        text_box = QtWidgets.QTextEdit(parent=parent)
        editor = gce.editors.EditorWithToolBox(text_box)
        for action_args in actions_args:
            editor.add_action(QtGui.QAction(*action_args))
        parent.show()
        assert editor.toolbar.isVisible() is expected_visible


    @pytest.mark.parametrize(
        "toolbar_area, compare_y, compare_x",
        [
            (
                QtCore.Qt.ToolBarArea.TopToolBarArea,
                "less_than",
                "equal"
            ),
            (
                QtCore.Qt.ToolBarArea.LeftToolBarArea,
                "equal",
                "less_than"
            ),
            (
                QtCore.Qt.ToolBarArea.RightToolBarArea,
                "equal",
                "greater_than"
            ),
            (
                QtCore.Qt.ToolBarArea.BottomToolBarArea,
                "greater_than",
                "equal"
            ),
        ]
    )
    def test_toolbar_position(self, qtbot, toolbar_area, compare_y, compare_x):
        parent = QtWidgets.QDialog()
        qtbot.addWidget(parent)
        text_box = QtWidgets.QTextEdit(parent=parent)
        editor = gce.editors.EditorWithToolBox(text_box, toolbar_position=toolbar_area)
        editor.add_action(QtGui.QAction("open", text_box))
        parent.show()
        toolbar_pos =editor.toolbar.pos()
        match compare_y:
            case "less_than":
                assert toolbar_pos.y() < editor.decorated.y()
            case "equal":
                assert toolbar_pos.y() == editor.decorated.y()
            case "greater_than":
                assert toolbar_pos.y() > editor.decorated.y()
            case _:
                assert False, f"unknown comparison {compare_y}"

        match compare_x:
            case "equal":
                assert toolbar_pos.x() == editor.decorated.x()
            case "less_than":
                assert toolbar_pos.x() < editor.decorated.x()
            case "greater_than":
                assert toolbar_pos.x() > editor.decorated.x()
            case _:
                assert False, f"unknown comparison: {compare_x}"

    def test_toolbar_with_no_toolbar_area(self, qtbot):
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)
        text_box = QtWidgets.QTextEdit(parent=parent)
        editor = gce.editors.EditorWithToolBox(text_box, toolbar_position=QtCore.Qt.ToolBarArea.NoToolBarArea)
        editor.add_action(QtGui.QAction("open", text_box))
        editor.show()
        assert editor.toolbar.isVisible() is False

def test_text_box_with_action_editor(qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    actions = [QtGui.QAction("open")]
    editor = gce.editors.text_box_with_action_editor(actions=actions, parent=parent)
    assert editor.toolbar.actions() == actions

def test_text_line_with_action_editor(qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    action = QtGui.QAction("open")
    widget = gce.editors.text_line_with_action_editor(parent=parent, action=action)
    assert widget.actions() == [action]

def test_combo_box_factory(qtbot):
    parent = QtWidgets.QWidget()
    qtbot.addWidget(parent)
    choices = ["one", "two"]
    widget = gce.editors.combo_box_factory(parent=parent, choices=choices)
    assert [widget.itemText(i) for i in range(widget.count())] == choices
