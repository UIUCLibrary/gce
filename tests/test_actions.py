import pathlib
from unittest.mock import Mock

import pytest
from PySide6 import QtWidgets

from gce import actions, gui


def test_load_toml():
    dialog_get = Mock(return_value=("some_file.toml", ""))
    mw = Mock(spec_set=gui.MainWindow)
    actions.load_toml(
        mw, dialog_get, confirm_existing_strategy=Mock(return_value=True)
    )
    assert mw.toml_file == "some_file.toml"


def test_load_toml_when_unsaved_changes_confirms_with_user():
    mw = Mock(spec_set=gui.MainWindow, unsaved_changes=True)
    confirm_dialog_strategy = Mock()
    actions.load_toml(
        mw,
        Mock(name="open_dialog_strategy", return_value=("some_file.toml", "")),
        confirm_existing_strategy=confirm_dialog_strategy,
    )
    confirm_dialog_strategy.assert_called_with(mw)


@pytest.mark.parametrize(
    "user_response, expected_call", [(True, True), (False, False)]
)
def test_load_toml_continues_based_on_user_response(
    user_response, expected_call
):
    mw = Mock(spec_set=gui.MainWindow, unsaved_changes=True)
    confirm_dialog_strategy = Mock(return_value=user_response)
    open_dialog_strategy = Mock(
        name="open_dialog_strategy", return_value=("some_file.toml", "")
    )
    actions.load_toml(
        mw,
        open_dialog_strategy,
        confirm_existing_strategy=confirm_dialog_strategy,
    )
    assert open_dialog_strategy.called is expected_call


def test_load_toml_when_no_unsaved_changes_does_not_confirm_with_user():
    mw = Mock(spec_set=gui.MainWindow, unsaved_changes=False)
    confirm_dialog_strategy = Mock()
    actions.load_toml(
        mw,
        Mock(name="open_dialog_strategy", return_value=("some_file.toml", "")),
        confirm_existing_strategy=confirm_dialog_strategy,
    )
    confirm_dialog_strategy.assert_not_called()


def test_save_toml():
    toml_view = Mock()
    mw = Mock(spec=gui.MainWindow, unsaved_changes=True, toml_view=toml_view)
    actions.save_toml(
        mw, Mock(toLocalFile=Mock(return_value="some_file.toml"))
    )
    mw.write_to_file.assert_called_once_with(
        pathlib.Path("some_file.toml"), toml_view.model()
    )


def test_use_dialog_box_to_confirm_with_user_sets_message():
    mw = Mock(spec_set=gui.MainWindow)
    message_box = Mock(
        spec_set=QtWidgets.QMessageBox,
        exec=Mock(return_value=QtWidgets.QMessageBox.StandardButton.No),
    )

    message_box_factory = Mock(
        name="message_box_factory", return_value=message_box
    )
    actions.use_dialog_box_to_confirm_with_user(
        mw, "some message", message_box_factory
    )
    message_box.setText.assert_called_with("some message")


@pytest.mark.parametrize(
    "button_pressed, expected",
    [
        (QtWidgets.QMessageBox.StandardButton.No, False),
        (QtWidgets.QMessageBox.StandardButton.Yes, True),
    ],
)
def test_use_dialog_box_to_confirm_with_user_button_response(
    button_pressed, expected
):
    mw = Mock(spec_set=gui.MainWindow)
    message_box = Mock(
        spec_set=QtWidgets.QMessageBox, exec=Mock(return_value=button_pressed)
    )

    message_box_factory = Mock(
        name="message_box_factory", return_value=message_box
    )
    assert (
        actions.use_dialog_box_to_confirm_with_user(
            mw, "some message", message_box_factory
        )
        is expected
    )


def test_use_dialog_box_to_confirm_invalid_response_raises_value_error():
    mw = Mock(spec_set=gui.MainWindow)
    message_box = Mock(
        spec_set=QtWidgets.QMessageBox,
        exec=Mock(return_value=QtWidgets.QMessageBox.StandardButton.SaveAll),
    )

    message_box_factory = Mock(
        name="message_box_factory", return_value=message_box
    )
    with pytest.raises(ValueError):
        actions.use_dialog_box_to_confirm_with_user(
            mw, "some message", message_box_factory
        )
