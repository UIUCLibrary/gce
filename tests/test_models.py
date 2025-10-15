import io
from typing import List, Tuple
from unittest.mock import Mock

import pytest
from PySide6 import QtCore
import tomllib
from gce import models


class TestTomlModel:
    @pytest.fixture
    def toml_data(self):
        return """
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

[[mapping]]
key = "Citations"
matching_marc_fields = [
    "510a",
    "510c",
]
delimiter = "||"
existing_data = "keep"

[[mapping]]
key = "Associated Entities"
serialize_method = "jinja2template"
delimiter = "||"
existing_data = "replace"
jinja_template = "{% for field in fields['700'] %}{{ field['a'] }}{% if field['q'] %} {{field['q']}}{%endif%} {{ field['d'] }}{% if not loop.last %}||{% endif %}{% endfor %}"

"""

    @pytest.fixture
    def toml_data_fp(self, toml_data):
        with io.StringIO() as stream:
            stream.write(toml_data)
            stream.seek(0)
            yield stream

    @pytest.fixture
    def populated_model(self, toml_data_fp):
        return models.load_toml_fp(toml_data_fp)

    def test_all_mapping_values_is_under_a_mapping_node(
        self, populated_model, toml_data
    ):
        mapping_values_index = populated_model.index(1, 0)
        rows = populated_model.rowCount(mapping_values_index)
        for row in range(rows):
            index = populated_model.index(row, 0, parent=mapping_values_index)
            heading = populated_model.data(
                index, role=QtCore.Qt.ItemDataRole.DisplayRole
            )
            expected = f'mapping - "{tomllib.loads(toml_data)["mapping"][row]["key"]}"'
            assert heading == expected, (
                f'expected: "{expected}", got "{heading}"'
            )

    def test_load_toml_fp_model_number_of_mappings(
        self, toml_data_fp, toml_data
    ):
        model = models.load_toml_fp(toml_data_fp)
        mapping_values_index = model.index(1, 0)
        toml_data_fp.seek(0)
        assert model.rowCount(mapping_values_index) == len(
            tomllib.loads(toml_data)["mapping"]
        )

    def test_load_toml_fp_model_mappings_has_only_expected_keys(
        self, populated_model, toml_data
    ):
        mapping_values_index = populated_model.index(1, 0)
        for row in range(populated_model.rowCount(mapping_values_index)):
            index = populated_model.index(row, 0, parent=mapping_values_index)
            row_count = populated_model.rowCount(index)
            expected_row_count = len(tomllib.loads(toml_data)["mapping"][row])
            assert row_count == expected_row_count, (
                f"expected {expected_row_count}, got :{row_count}"
            )

    @pytest.mark.parametrize(
        "indices, expected_text",
        [
            ([(0, 0)], "identifier_key"),
            ([(1, 0)], "Mapping values"),
            ([(1, 0), (0, 0), (0, 0)], "key"),
            ([(1, 0), (0, 0), (0, 1)], "Uniform Title"),
            ([(1, 0), (0, 0), (1, 0)], "matching_marc_fields"),
            ([(1, 0), (0, 0), (1, 1)], ["240$a"]),
            ([(1, 0), (0, 0), (2, 0)], "delimiter"),
            ([(1, 0), (0, 0), (2, 1)], "||"),
            ([(1, 0), (1, 0), (0, 1)], "Dummy"),
            ([(1, 0), (1, 0), (1, 1)], ["220$a"]),
            ([(1, 0), (2, 0), (0, 1)], "Citations"),
            ([(1, 0), (2, 0), (1, 1)], ["510a", "510c"]),
        ],
    )
    def test_mapping_values(
        self,
        populated_model,
        get_index_factory,
        indices,
        expected_text,
    ):
        assert (
            populated_model.data(
                get_index_factory(populated_model, indices),
                role=QtCore.Qt.ItemDataRole.DisplayRole,
            )
            == expected_text
        )

    @pytest.mark.parametrize(
        "indices,expected_is_editable, expected_is_selectable",
        [
            ([(1, 0), (0, 0), (0, 0)], False, True),
            ([(1, 0), (0, 0), (0, 1)], True, True),
        ],
    )
    def test_selectable(
        self,
        populated_model,
        get_index_factory,
        indices,
        expected_is_editable,
        expected_is_selectable,
    ):
        index = get_index_factory(populated_model, indices)
        assert (
            bool(
                populated_model.flags(index)
                & QtCore.Qt.ItemFlag.ItemIsEditable
            )
        ) is expected_is_editable

        assert (
            bool(
                populated_model.flags(index)
                & QtCore.Qt.ItemFlag.ItemIsSelectable
            )
        ) is expected_is_selectable

    @pytest.mark.parametrize(
        "indices, expected_starting_text",
        [
            ([(0, 1)], "Bibliographic Identifier"),
            ([(1, 0), (0, 0), (0, 1)], "Uniform Title"),
        ],
    )
    def test_set_data_in_toml_model(
        self,
        populated_model,
        get_index_factory,
        indices,
        expected_starting_text,
    ):
        index = get_index_factory(populated_model, indices)
        assert (
            populated_model.data(
                index, role=QtCore.Qt.ItemDataRole.DisplayRole
            )
            == expected_starting_text
        )
        assert populated_model.setData(index, "somthingelse") is True
        assert (
            populated_model.data(
                index, role=QtCore.Qt.ItemDataRole.DisplayRole
            )
            == "somthingelse"
        )

    @pytest.mark.parametrize(
        "header_index", range(len(models.TomlModel.headers))
    )
    def test_header_data(self, populated_model, header_index):
        assert (
            populated_model.headerData(
                header_index, QtCore.Qt.Orientation.Horizontal
            )
            == populated_model.headers[header_index]
        )

    @pytest.mark.parametrize(
        "indices, expected",
        [
            ([], True),
            ([(0, 0)], False),
            ([(1, 0)], True),
        ],
    )
    def test_has_children(
        self, populated_model, get_index_factory, indices, expected
    ):
        assert (
            populated_model.hasChildren(
                parent=get_index_factory(populated_model, indices)
            )
            is expected
        )

    @pytest.mark.parametrize(
        "header_index", [len(models.TomlModel.headers) + 1, -1]
    )
    def test_request_invalid_header_returns_none(
        self, populated_model, header_index
    ):
        assert (
            populated_model.headerData(
                header_index, QtCore.Qt.Orientation.Horizontal
            )
            is None
        )

    @pytest.fixture
    def get_index_factory(self):
        def _make_index(
            model: QtCore.QAbstractItemModel, indices: List[Tuple[int, int]]
        ) -> QtCore.QModelIndex:
            ind = indices.copy()
            index = QtCore.QModelIndex()
            while len(ind) > 0:
                index = model.index(*ind.pop(0), parent=index)
            return index

        return _make_index

    @pytest.mark.parametrize(
        "indices, expected",
        [
            ([], 2),
            ([(1, 0)], 4),
            ([(1, 0), (0, 0)], 4),
        ],
    )
    def test_row_count(
        self, populated_model, indices, get_index_factory, expected
    ):
        assert (
            populated_model.rowCount(
                parent=get_index_factory(populated_model, indices)
            )
            == expected
        )


def test_data_has_changed(example_toml_data_fp):
    model = models.load_toml_fp(example_toml_data_fp)
    example_toml_data_fp.seek(0)
    starting_data = example_toml_data_fp.read()
    assert models.data_has_changed(starting_data, model) is False
    index = model.index(0, 1)
    model.setData(index, "somthingelse")
    assert models.data_has_changed(starting_data, model)


@pytest.fixture
def example_toml_data_fp():
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


def test_load_toml_fp_gets_model(example_toml_data_fp):
    assert isinstance(
        models.load_toml_fp(example_toml_data_fp), QtCore.QAbstractItemModel
    )


def test_export_toml_top_level_data(example_toml_data_fp):
    model = models.load_toml_fp(example_toml_data_fp)
    assert model.setData(model.index(0, 1), "somthingelse") is True
    assert (
        tomllib.loads(models.export_toml(model=model))["mappings"][
            "identifier_key"
        ]
        == "somthingelse"
    )


def test_export_toml_mapping_values_correct_number(example_toml_data_fp):
    model = models.load_toml_fp(example_toml_data_fp)
    toml_text = models.export_toml(model=model)
    toml_data = tomllib.loads(toml_text)
    assert len(toml_data["mapping"]) == 2


def test_export_toml_mapping_values(example_toml_data_fp):
    model = models.load_toml_fp(example_toml_data_fp)
    toml_text = models.export_toml(model=model)
    new_toml_data = tomllib.loads(toml_text)
    example_toml_data_fp.seek(0)
    assert tomllib.loads(example_toml_data_fp.read()) == new_toml_data


class TestMappingNode:
    @pytest.mark.parametrize(
        "children,expected",
        [
            (
                [Mock(key="key", value="Uniform Title")],
                'mapping - "Uniform Title"',
            ),
            ([], "mapping"),
        ],
    )
    def test_key_dynamic_based_on_children(self, children, expected):
        model = models.MappingNode()
        model.children = children
        assert model.key == expected
