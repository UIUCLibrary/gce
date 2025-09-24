import os
from unittest.mock import Mock

import pygments.lexer
import pygments.style
import pytest
from PySide6 import QtWidgets, QtCore, QtTest

from gce import gui


class TestJinjaEditorDialog:
    def test_rejected_on_close(self, qtbot):
        dialog = gui.JinjaEditorDialog()
        qtbot.addWidget(dialog)
        with qtbot.waitSignal(dialog.rejected):
            dialog.button_box.button(QtWidgets.QDialogButtonBox.Close).click()


class TestJinjaEditor:
    def test_xml_text_changed_signal_emitted(self, qtbot):
        editor = gui.JinjaEditor()
        qtbot.addWidget(editor)
        with qtbot.waitSignal(editor.xml_data_changed):
            editor.xml_text = "New text"

    def test_jinja_expression_changed_signal_emitted(self, qtbot):
        editor = gui.JinjaEditor()
        qtbot.addWidget(editor)
        with qtbot.waitSignal(editor.jinja_expression_changed):
            editor.jina_text = "New expression"

    def test_jina_text_property(self, qtbot):
        editor = gui.JinjaEditor()
        qtbot.addWidget(editor)
        test_value = "Test expression"
        editor.jina_text = test_value
        assert editor.jina_text == test_value

    def test_xml_text_property(self, qtbot):
        editor = gui.JinjaEditor()
        qtbot.addWidget(editor)
        test_value = "Test XML"
        editor.xml_text = test_value
        assert editor.xml_text == test_value

    def test_set_pygments_style(self, qtbot):
        editor = gui.JinjaEditor()
        qtbot.addWidget(editor)
        test_style = "monokai"
        editor.jinja_pygments_style = test_style
        assert editor.jinja_pygments_style == test_style

    def test_update_output(self, qtbot):
        editor = gui.JinjaEditor()
        qtbot.addWidget(editor)
        editor.update_output = Mock()
        editor.xml_text = "<root><element>Value</element></root>"
        editor.jina_text = "{{ fields['001'] }}"
        editor.update_output.assert_called()


class TestLineEditSyntaxHighlighting:
    def test_size_hint(self, qtbot):
        line_edit = gui.LineEditSyntaxHighlighting()
        qtbot.addWidget(line_edit)
        size_hint = line_edit.sizeHint()
        assert size_hint.width() > 0
        assert size_hint.height() > 0

    def test_set_text_updates_text(self, qtbot):
        line_edit = gui.LineEditSyntaxHighlighting()
        qtbot.addWidget(line_edit)
        test_value = "Test text"
        line_edit.text = test_value
        assert line_edit.text == test_value

    def test_set_text_emits_text_changed(self, qtbot):
        line_edit = gui.LineEditSyntaxHighlighting()
        qtbot.addWidget(line_edit)
        test_value = "Test text"
        spy = QtTest.QSignalSpy(line_edit.textChanged)
        with qtbot.waitSignal(line_edit.textChanged):
            line_edit.text = test_value
        assert spy.count() == 1

    def test_pressing_entier_emits_edit_finished_signal(self, qtbot):
        line_edit = gui.LineEditSyntaxHighlighting()
        qtbot.addWidget(line_edit)
        spy = QtTest.QSignalSpy(line_edit.editingFinished)
        with qtbot.waitSignal(line_edit.editingFinished):
            qtbot.keyClicks(line_edit, "Some text")
            qtbot.keyPress(line_edit, QtCore.Qt.Key.Key_Return)
        assert spy.count() == 1

    def test_style_setting(self):
        line_edit = gui.LineEditSyntaxHighlighting()
        line_edit.style = "monokai"
        assert line_edit.style == "monokai"

    def test_style_colors_changed_changed_signal_emitted(self, qtbot):
        line_edit = gui.LineEditSyntaxHighlighting()
        qtbot.addWidget(line_edit)
        spy = QtTest.QSignalSpy(line_edit.style_colors_changed)
        with qtbot.waitSignal(line_edit.style_colors_changed):
            line_edit.pygments_style = "monokai"
        assert spy.count() == 1


class TestPygmentsHighlighter:
    def test_setting_lexer_emits_signal(self, qtbot):
        parent = QtCore.QObject()
        highlighter = gui.PygmentsHighlighter(parent)
        spy = QtTest.QSignalSpy(highlighter.lexer_changed)
        with qtbot.waitSignal(highlighter.lexer_changed):
            highlighter.lexer = Mock(spec_set=pygments.lexer.Lexer)
        assert spy.count() == 1

    def test_setting_style_emits_signal(self, qtbot):
        parent = QtCore.QObject()
        highlighter = gui.PygmentsHighlighter(parent)
        spy = QtTest.QSignalSpy(highlighter.style_changed)
        with qtbot.waitSignal(highlighter.style_changed):
            highlighter.style = Mock(
                spec=pygments.style.Style, list_styles=lambda: []
            )
        assert spy.count() == 1


class TestJinjaRenderer:
    @pytest.fixture
    def sample_xml(self):
        with open(os.path.join(os.path.dirname(__file__), "example.xml")) as f:
            return f.read()

    @pytest.mark.parametrize(
        "jinja_text, expected_text, is_valid",
        [
            ("{{ fields['040'][0].a }}", "PUL", True),
            ("{{ fields['040'][0].b }}", "eng", True),
            (
                "{{ fields['040'][0].b }",
                "Jinja expression Template Syntax Error : unexpected '}'",
                False,
            ),
            (
                "{{ record['040'][0].b }}",
                "jinja2 exception Undefined Error : 'record' is undefined",
                False,
            ),
        ],
    )
    def test_render_with_valid_input(
        self, sample_xml, jinja_text, expected_text, is_valid
    ):
        renderer = gui.JinjaRenderer()
        renderer.jinja_text = jinja_text
        renderer.xml = sample_xml
        output = renderer.render()
        assert output == expected_text
        assert renderer.is_valid is is_valid

    def test_invalid_xml_error(self):
        renderer = gui.JinjaRenderer()
        renderer.jinja_text = "{{ fields['040'][0].a }}"
        renderer.xml = "This is not an XML"
        output = renderer.render()
        assert "Unable to parse xml data" in output
        assert renderer.is_valid is False

    def test_empty_xml_is_not_an_error(self):
        renderer = gui.JinjaRenderer()
        renderer.jinja_text = "{{ fields['040'][0].a }}"
        renderer.xml = ""
        output = renderer.render()
        assert "" == output
        assert renderer.is_valid is True
