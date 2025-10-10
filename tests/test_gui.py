import io
import logging
import os
import pathlib
from unittest.mock import Mock, ANY, MagicMock, patch, mock_open

import galatea.merge_data
import pygments.lexer
import pygments.style
import pytest
from PySide6 import QtWidgets, QtCore, QtTest

import gce.gui
import gce.models
import gce.actions
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
        editor.pygments_style = test_style
        assert editor.pygments_style == test_style

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


class TestTomlView:
    @pytest.fixture
    def example_toml_data_fp(self):
        with io.StringIO() as stream:
            stream.write("""
[mappings]
identifier_key = "Bibliographic Identifier"

[[mapping]]
key = "Uniform Title"
matching_marc_fields = ["240$a"]
delimiter = "||"
existing_data = "keep"

[[mapping]]
key = "Dummy"
matching_marc_fields = ["220$a"]
delimiter = "||"
existing_data = "keep"
""")
            stream.seek(0)
            yield stream

    def test_keyboard_edit_toggle(self, qtbot, example_toml_data_fp):
        model = gce.models.load_toml_fp(example_toml_data_fp)
        base = QtWidgets.QWidget()
        qtbot.addWidget(base)
        view = gui.TomlView(base)
        view.setModel(model)
        view.setCurrentIndex(model.index(0, 0))
        assert view.state() != QtWidgets.QAbstractItemView.State.EditingState
        qtbot.keyPress(view, QtCore.Qt.Key.Key_Return)
        assert view.state() == QtWidgets.QAbstractItemView.State.EditingState


class TestMainWindow:
    def test_load_action(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        with qtbot.waitSignal(mw.open_file_requested):
            mw.load_action.trigger()

    def test_save_action(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        starting_model = gce.models.TomlModel()
        starting_model.add_top_level_config("bacon", "eggs")
        mw.load_toml_strategy = lambda _: starting_model
        mw.toml_file = "dummy.toml"
        with qtbot.waitSignal(mw.save_file_requested):
            mw.is_model_data_different_than_file = lambda *_: True
            mw.toml_view.model().setData(
                mw.toml_view.model().index(0, 1), "spam"
            )
            mw.save_action.trigger()

    def test_state_no_file_means_save_is_disabled(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        assert mw.save_action.isEnabled() is False

    def test_set_toml_file_with_bad_data_sets_empty_state(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)

        mw.load_toml_strategy = Mock(return_value=gui.models.TomlModel())
        mw.toml_file = "goodfile.toml"
        assert not isinstance(mw.state, gui.NoDocumentLoadedState)

        mw.load_toml_strategy = Mock(
            side_effect=galatea.merge_data.BadMappingFileError(
                source_file="badfile.toml"
            )
        )
        mw.toml_file = "badfile.toml"
        assert isinstance(mw.state, gui.NoDocumentLoadedState)

    def test_set_toml_file_with_error_writes_to_error(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        mw.load_toml_strategy = Mock(
            side_effect=galatea.merge_data.BadMappingFileError(
                source_file="badfile.toml", details="bad data"
            )
        )
        with qtbot.waitSignal(mw.status_message_updated) as update:
            mw.toml_file = "badfile.toml"
            assert isinstance(mw.state, gui.NoDocumentLoadedState)
        assert update.args == ["bad data", logging.ERROR]

    def test_loading_toml_file_without_editing_has_save_disabled(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        assert mw.save_action.isEnabled() is False
        mw.load_toml_strategy = lambda _: gce.models.TomlModel()
        mw.toml_file = "dummy.toml"
        assert mw.save_action.isEnabled() is False

    def test_loading_toml_file_editing_has_enables_save(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        mw.is_model_data_different_than_file = lambda *_: False
        assert mw.save_action.isEnabled() is False
        dummy = gce.models.TomlModel()
        dummy.add_top_level_config("spam", "bacon")
        mw.load_toml_strategy = lambda _: dummy
        mw.toml_file = "dummy.toml"
        model = mw.toml_view.model()
        mw.is_model_data_different_than_file = lambda *_: True
        with qtbot.waitSignal(model.dataChanged):
            assert model.setData(model.index(0, 1), "eggs")
        assert mw.save_action.isEnabled() is True

    def test_loading_bad_file_while_have_working_one(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        assert mw.toml_view.model() is None
        load_good_data = gce.models.TomlModel()
        load_good_data.add_top_level_config("spam", "bacon")
        mw.load_toml_strategy = lambda _: load_good_data
        mw.toml_file = "spam.toml"
        assert mw.toml_view.model().rowCount() == 2

        def load_bad_data(toml_file: pathlib.Path):
            raise galatea.merge_data.BadMappingFileError(source_file=toml_file)

        mw.load_toml_strategy = load_bad_data
        mw.toml_file = "bad_data.toml"
        assert mw.toml_view.model() is None

    @patch(
        "pathlib.Path.open", new_callable=mock_open, read_data="mocked content"
    )
    def test_is_model_data_different_than_file(self, mock_file_open, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        model = Mock()
        comparison_strategy = Mock()
        mw.is_model_data_different_than_file(
            pathlib.Path("something.toml"), model, comparison_strategy
        )
        comparison_strategy.assert_called_once_with("mocked content", model)

    def test_write_to_file_calls_state_method(self, qtbot):
        mw = gui.MainWindow()
        qtbot.addWidget(mw)
        model = Mock()
        mw.state.write_toml_file = Mock()
        toml_file = pathlib.Path("something.toml")
        mw.write_to_file(toml_file, model)
        mw.state.write_toml_file.assert_called_once_with(toml_file, model)


class TestNoDocumentLoadedState:
    @pytest.mark.parametrize(
        "method_name, args",
        [
            ("write_toml_file", [pathlib.Path("something"), None]),
            ("data_modified", [Mock(name="tomlModel")]),
        ],
    )
    def test_no_op_states(self, method_name, args):
        main_window = Mock(spec_set=True)
        state = gce.gui.NoDocumentLoadedState(main_window)
        method = getattr(state, method_name)
        method(*args)
        main_window.assert_not_called()

    def test_set_toml_file(self, monkeypatch):
        main_window = Mock()
        set_toml_file = Mock()
        monkeypatch.setattr(
            gce.gui.StateUtility, "set_toml_file", set_toml_file
        )
        state = gce.gui.NoDocumentLoadedState(main_window)
        state.set_toml_file(pathlib.Path("something"))


class TestFileLoadedUnmodifiedState:
    @pytest.mark.parametrize(
        "method_name, args",
        [
            ("write_toml_file", [pathlib.Path("something"), None]),
        ],
    )
    def test_no_op_states(self, method_name, args):
        main_window = Mock(spec_set=True)
        state = gce.gui.FileLoadedUnmodifiedState(main_window)
        method = getattr(state, method_name)
        method(*args)
        main_window.assert_not_called()

    def test_set_toml_file(self, monkeypatch):
        main_window = Mock(spec_set=True)
        state = gce.gui.FileLoadedUnmodifiedState(main_window)
        set_toml_file = Mock(
            name="set_toml_file", spec_set=gce.gui.StateUtility.set_toml_file
        )
        monkeypatch.setattr(
            gce.gui.StateUtility, "set_toml_file", set_toml_file
        )
        model = Mock()
        state.set_toml_file(model)
        set_toml_file.assert_called_with(main_window, model)

    def test_data_modified(self, monkeypatch):
        main_window = Mock(spec_set=True)
        state = gce.gui.FileLoadedUnmodifiedState(main_window)
        update_window = Mock(
            name="update_window", spec_set=gce.gui.StateUtility.update_window
        )
        monkeypatch.setattr(
            gce.gui.StateUtility, "update_window", update_window
        )
        model = Mock()
        state.data_modified(model)
        update_window.assert_called_with(main_window, model)


class TestFileLoadedModifiedState:
    def test_data_modified(self, monkeypatch):
        main_window = Mock(spec_set=True)
        state = gce.gui.FileLoadedModifiedState(main_window)
        update_window = Mock(
            name="update_window", spec_set=gce.gui.StateUtility.update_window
        )
        monkeypatch.setattr(
            gce.gui.StateUtility, "update_window", update_window
        )
        model = Mock()
        state.data_modified(model)
        update_window.assert_called_with(main_window, model)

    def test_write_toml_file(self, monkeypatch):
        main_window = Mock()
        state = gce.gui.FileLoadedModifiedState(main_window)
        update_window = Mock(
            name="update_window", spec_set=gce.gui.StateUtility.update_window
        )
        monkeypatch.setattr(
            gce.gui.StateUtility, "update_window", update_window
        )
        model = Mock()

        state.write_toml_file(pathlib.Path("somefile"), model)
        update_window.assert_called_with(main_window, model)
        main_window.write_toml_strategy.assert_called_with(
            pathlib.Path("somefile"), model
        )

    def test_set_toml_file(self, monkeypatch):
        main_window = Mock()
        state = gce.gui.FileLoadedModifiedState(main_window)
        set_toml_file = Mock(
            name="set_toml_file", spec_set=gce.gui.StateUtility.set_toml_file
        )
        monkeypatch.setattr(
            gce.gui.StateUtility, "set_toml_file", set_toml_file
        )
        update_window = Mock(
            name="update_window", spec_set=gce.gui.StateUtility.update_window
        )
        monkeypatch.setattr(
            gce.gui.StateUtility, "update_window", update_window
        )
        state.set_toml_file(pathlib.Path("somefile"))
        set_toml_file.assert_called_with(main_window, pathlib.Path("somefile"))
        update_window.assert_called_with(main_window, ANY)


class TestStateUtility:
    def test_set_toml_file_success_changes_state_to_unmodified(self):
        main_window = Mock()
        toml_file = pathlib.Path("somefile")
        gce.gui.StateUtility.set_toml_file(main_window, toml_file)
        assert isinstance(main_window.state, gce.gui.FileLoadedUnmodifiedState)

    def test_set_toml_file_unsuccess_changes_state_to_no_document_loaded(self):
        main_window = Mock(
            load_toml_strategy=Mock(
                side_effect=galatea.merge_data.BadMappingDataError(
                    details="something went wrong"
                )
            )
        )
        toml_file = pathlib.Path("somefile")
        gce.gui.StateUtility.set_toml_file(main_window, toml_file)
        assert isinstance(main_window.state, gce.gui.NoDocumentLoadedState)

    def test_update_window_with_no_model_sets_window_title_to_default(self):
        main_window = Mock()
        gce.gui.StateUtility.update_window(main_window, None)
        main_window.setWindowTitle.assert_called_once_with("TOML Editor")

    def test_update_window_no_changes_set_to_unmodified_state(self):
        main_window = Mock(toml_file="dummy.toml", unsaved_changes = False)
        toml_model = Mock()
        gce.gui.StateUtility.update_window(main_window, toml_model)
        assert isinstance(main_window.state, gce.gui.FileLoadedUnmodifiedState)

    def test_update_window_changes_set_to_modified_state(self):
        main_window = Mock(toml_file="dummy.toml")
        main_window.is_model_data_different_than_file = lambda *_: True
        toml_model = Mock()
        gce.gui.StateUtility.update_window(main_window, toml_model)
        assert isinstance(main_window.state, gce.gui.FileLoadedModifiedState)


def test_write_toml():
    file_path = Mock(open=MagicMock(), spec_set=pathlib.Path)
    model = Mock()
    serialization_strategy = Mock()
    gce.gui.write_toml(
        file_path, model, serialization_strategy=serialization_strategy
    )
    serialization_strategy.assert_called_once_with(model)


@patch("pathlib.Path.open", new_callable=mock_open, read_data="mocked content")
def test_load_toml(mock_file_open):
    load_strategy = Mock()
    gce.gui.load_toml(pathlib.Path("somefile"), load_strategy=load_strategy)
    mock_file_open.assert_called_once()


@patch("pathlib.Path.open", new_callable=mock_open, read_data="mocked content")
def test_load_toml_bad_mapping_data_passes_to_bad_mapping_file(mock_file_open):
    load_strategy = Mock(
        side_effect=galatea.merge_data.BadMappingDataError(
            details="something went wrong"
        )
    )
    with pytest.raises(galatea.merge_data.BadMappingFileError) as error:
        gce.gui.load_toml(
            pathlib.Path("somefile"), load_strategy=load_strategy
        )
    assert error.value.source == pathlib.Path("somefile")
