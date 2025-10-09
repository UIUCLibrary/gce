from unittest.mock import Mock

from gce import actions


def test_load_toml():
    dialog_get = Mock(return_value=("some_file.toml", ""))
    mw = Mock()
    actions.load_toml(mw, dialog_get)
    assert mw.toml_file == "some_file.toml"
