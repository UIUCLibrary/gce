import io
from typing import (
    Dict,
    Union,
    Optional,
    List,
    TypeVar,
    Generic,
)
import typing

import galatea.merge_data
from PySide6 import QtCore
import tomllib
import tomli_w

T = TypeVar("T")

TOML_TYPE = Union[str, int, float, bool]
TOML_SPEC = Union[TOML_TYPE, List[TOML_TYPE], Dict[str, TOML_TYPE]]


class TomlNode(Generic[T]):
    def __init__(
        self, key: Optional[str] = None, parent: Optional["TomlNode"] = None
    ):
        self._parent = parent
        self._key = key
        self._value: Optional[T] = None
        self.children: List[TomlNode[T]] = []
        self.is_editable = True
        self.is_selectable = True

    @property
    def key(self) -> Optional[str]:
        return self._key

    @property
    def value(self) -> Optional[T]:
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        self._value = value

    def parent(self) -> Optional["TomlNode"]:
        return self._parent

    def child(self, row: int) -> "TomlNode":
        return self.children[row]

    def child_count(self) -> int:
        return len(self.children)


class MappingNode(TomlNode):
    def __init__(
        self, key: Optional[str] = None, parent: Optional[TomlNode] = None
    ) -> None:
        super().__init__(key, parent)
        self.is_editable = False

    @property
    def key(self) -> str:
        for child in self.children:
            if child.key == "key":
                return f'mapping - "{child.value}"'
        return "mapping"


class TomlModel(QtCore.QAbstractItemModel):
    headers = ["Property", "Value"]

    def __init__(
        self,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._root = TomlNode[TOML_SPEC]()
        self._mappings = TomlNode[TOML_SPEC](
            "Mapping values", parent=self._root
        )
        self._mappings.is_editable = False
        self._root.children.append(self._mappings)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Optional[str]:
        if (
            orientation == QtCore.Qt.Orientation.Horizontal
            and role == QtCore.Qt.ItemDataRole.DisplayRole
        ):
            return (
                self.headers[section]
                if 0 <= section < len(self.headers)
                else None
            )
        return None

    def add_top_level_config(
        self, key: str, value: Optional[TOML_TYPE] = None
    ) -> None:
        new_node = TomlNode[TOML_SPEC](key, parent=self._root)
        if value is not None:
            new_node.value = value
        self._root.children.insert(self._root.child_count() - 1, new_node)

    def get_item(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> TomlNode[TOML_SPEC]:
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self._root

    def index(
        self,
        row: int,
        column: int,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = QtCore.QModelIndex(),
    ) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        parent_node = self.get_item(parent)
        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        return QtCore.QModelIndex()

    def columnCount(
        self,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = QtCore.QModelIndex(),
    ) -> int:
        return 2

    def rowCount(
        self,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = QtCore.QModelIndex(),
    ) -> int:
        return self.get_item(parent).child_count()

    def add_mapping(self, data: Dict[str, TOML_TYPE]) -> None:
        new_mapping_node = MappingNode("mapping", parent=self._mappings)
        for k, v in data.items():
            item = TomlNode[TOML_TYPE](k, parent=new_mapping_node)
            item.value = v
            new_mapping_node.children.append(item)
        self._mappings.children.append(new_mapping_node)

    @typing.overload
    def parent(self) -> QtCore.QObject: ...

    @typing.overload
    def parent(
        self,
        child: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = QtCore.QModelIndex(),
    ) -> QtCore.QModelIndex: ...

    def parent(
        self,
        child: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = QtCore.QModelIndex(),
    ) -> Union[QtCore.QModelIndex, QtCore.QObject]:
        if not child.isValid():
            return QtCore.QModelIndex()

        child_node = self.get_item(child)
        parent_node = child_node.parent()

        if parent_node == self._root:
            return QtCore.QModelIndex()
        if parent_node:
            row = parent_node.children.index(child_node)
            return self.createIndex(row, 0, parent_node)
        return QtCore.QModelIndex()

    def setData(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        value: T,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if not index.isValid():
            return False
        if role == QtCore.Qt.ItemDataRole.EditRole:
            node = index.internalPointer()
            if index.column() == 1 and node.is_editable:
                node.value = value
                return True
        return False

    def data(
        self,
        index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Union[TOML_SPEC, None]:
        if not index.isValid():
            return None
        p = self.get_item(index)
        if index.column() == 0 and role == QtCore.Qt.ItemDataRole.DisplayRole:
            return p.key
        if index.column() == 1:
            if role == QtCore.Qt.ItemDataRole.DisplayRole:
                if len(p.children) == 0:
                    return p.value
            if role == QtCore.Qt.ItemDataRole.EditRole:
                return p.value
        return None

    def hasChildren(
        self,
        parent: Union[
            QtCore.QModelIndex, QtCore.QPersistentModelIndex
        ] = QtCore.QModelIndex(),
    ) -> bool:
        if not parent.isValid():
            parent_node = self._root
        else:
            parent_node = parent.internalPointer()
        return parent_node.child_count() > 0

    def flags(
        self, index: Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex]
    ) -> QtCore.Qt.ItemFlag:
        default_flags = super().flags(index)

        p = index.internalPointer()
        flags = default_flags
        if p is None:
            return flags
        if p.is_editable and index.column() == 1:
            flags = (
                flags
                | QtCore.Qt.ItemFlag.ItemIsEditable
                | QtCore.Qt.ItemFlag.ItemIsEnabled
            )
        else:
            flags = flags | QtCore.Qt.ItemFlag.ItemIsEnabled
        if p.is_selectable:
            flags = flags | QtCore.Qt.ItemFlag.ItemIsSelectable
        return flags


class TomlConfigFormat(typing.TypedDict):
    mappings: Dict[str, TOML_TYPE]
    mapping: List[Dict[str, TOML_TYPE]]


class TomlConfigDictionaryBuilder:
    def __init__(self) -> None:
        self._mappings: Dict[str, TOML_TYPE] = {}
        self._mapping: List[Dict[str, TOML_TYPE]] = []

    def __setitem__(self, key: str, value: TOML_TYPE) -> None:
        self._mappings[key] = value

    def create(self) -> TomlConfigFormat:
        return {"mappings": self._mappings, "mapping": self._mapping}

    def add_mapping(self, **kwargs: TOML_TYPE) -> None:
        self._mapping.append({**kwargs})


def convert_item_model_to_dictionary(
    model: QtCore.QAbstractItemModel,
) -> TomlConfigFormat:
    builder = TomlConfigDictionaryBuilder()
    for top_level_row in range(model.rowCount()):
        key_index = model.index(top_level_row, 0)
        mappings_key = model.data(key_index)
        mappings_value = model.data(model.index(top_level_row, 1))
        if mappings_key == "Mapping values":
            for mapping_row in range(model.rowCount(parent=key_index)):
                mapping_index = model.index(mapping_row, 0, parent=key_index)

                # Take the key from the 1st column, and the value from the 2nd
                builder.add_mapping(**{
                    model.data(
                        model.index(data_row, 0, parent=mapping_index)
                    ): model.data(
                        model.index(data_row, 1, parent=mapping_index)
                    )
                    for data_row in range(model.rowCount(parent=mapping_index))
                })
        else:
            builder[mappings_key] = (
                mappings_value if mappings_value is not None else ""
            )
    return builder.create()


def load_toml_fp(fp: io.TextIOBase) -> TomlModel:
    try:
        data: TomlConfigFormat = typing.cast(
            TomlConfigFormat, tomllib.loads(fp.read())
        )
    except tomllib.TOMLDecodeError as error:
        raise galatea.merge_data.BadMappingDataError(
            details=str(error)
        ) from error
    model = TomlModel()
    try:
        for key, value in data["mappings"].items():
            model.add_top_level_config(key, value)

        for item in data["mapping"]:
            model.add_mapping(item)
    except KeyError as error:
        raise galatea.merge_data.BadMappingDataError(
            details="Not a valid galatea mapping configration toml format file"
        ) from error
    return model


def export_toml(model: TomlModel) -> str:
    return tomli_w.dumps(convert_item_model_to_dictionary(model))
