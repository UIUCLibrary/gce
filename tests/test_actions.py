from unittest.mock import Mock

from gce import actions
def test_load_toml():
    dialog_get = Mock(return_value=("some_file.toml", ""))
    mw = Mock()
    actions.load_toml(mw, dialog_get)
    mw.set_toml_file.assert_called_with("some_file.toml")
