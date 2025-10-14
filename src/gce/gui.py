from __future__ import annotations

import abc
import pathlib
import xml.etree.ElementTree as ET
import logging
import typing
from typing import Type, Optional, Union

import jinja2
from PySide6 import QtWidgets, QtCore, QtGui
import pygments.styles
import pygments.lexers
import galatea
from galatea.merge_data import serialize_with_jinja_template, MappingConfig
from gce import models

if typing.TYPE_CHECKING:
    from pygments.style import Style as PygmentsStyle


logger = logging.getLogger(__name__)


class JinjaEditorDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle("Jinja Editor")
        self._jinja_editor = JinjaEditor()
        self._layout.addWidget(self._jinja_editor)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        self.button_box.rejected.connect(self.reject)
        self._layout.addWidget(self.button_box)

    @property
    def xml_text(self):
        return self._jinja_editor.xml_text

    @xml_text.setter
    def xml_text(self, text: str) -> None:
        self._jinja_editor.xml_text = text

    @property
    def jina_text(self) -> str:
        return self._jinja_editor.jina_text

    @jina_text.setter
    def jina_text(self, text: str) -> None:
        self._jinja_editor.jina_text = text

    @property
    def pygments_style(self):
        return self._jinja_editor.pygments_style

    @pygments_style.setter
    def pygments_style(self, value: str) -> None:
        self._jinja_editor.pygments_style = value


class XMLViewer(QtWidgets.QTextEdit):
    style_colors_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptRichText(False)
        self._highlighter = PygmentsHighlighter(parent=self.document())
        self._highlighter.lexer = pygments.lexers.get_lexer_by_name("xml")
        self.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        )

    @property
    def pygments_style(self) -> str:
        return self._highlighter.style.name

    @pygments_style.setter
    def pygments_style(self, value: str):
        if (
            self._highlighter.style is None
            or value != self._highlighter.style.name
        ):
            self._highlighter.style = pygments.styles.get_style_by_name(value)
            self.style_colors_changed.emit()


class _JinjaEditor(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widget_layout = QtWidgets.QGridLayout(self)
        self._widget_layout.setContentsMargins(0, 0, 0, 0)
        self.marc_xml_label = QtWidgets.QLabel("MARC XML")
        self._widget_layout.addWidget(
            self.marc_xml_label,
            0,
            0,
            1,
            1,
            alignment=QtCore.Qt.AlignmentFlag.AlignTop,
        )

        self.xml_text_edit_widget = XMLViewer(self)
        self.xml_text_edit_widget.setTabChangesFocus(True)
        self._widget_layout.addWidget(self.xml_text_edit_widget, 0, 1, 1, 1)

        self.jinja_expression_label = QtWidgets.QLabel("Jinja Expression")
        self._widget_layout.addWidget(self.jinja_expression_label, 1, 0, 1, 1)

        self.jinja_expression = LineEditSyntaxHighlighting(self)
        self.jinja_expression.lexer = pygments.lexers.get_lexer_by_name(
            "jinja"
        )
        self._widget_layout.addWidget(self.jinja_expression, 1, 1, 1, 1)

        self._spacer = QtWidgets.QSpacerItem(
            20,
            20,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._widget_layout.addItem(self._spacer)

        self.output_label = QtWidgets.QLabel("Output")

        self._widget_layout.addWidget(
            self.output_label,
            3,
            0,
            1,
            2,
            alignment=QtCore.Qt.AlignmentFlag.AlignHCenter,
        )

        self.output = QtWidgets.QLineEdit(self)
        self.output.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        )
        self.output.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.output.setReadOnly(True)
        self._widget_layout.addWidget(self.output, 4, 0, 1, 2)


class JinjaRenderer:
    def __init__(self):
        super().__init__()
        self.jinja_text = ""
        self.xml = ""
        self.output = ""
        self.is_valid = True
        self.error_message = None

    def render(self):
        config = MappingConfig(
            key="",
            matching_keys=[],
            delimiter="||",
            existing_data="keep",
            serialize_method="jinja2",
            experimental={"jinja2": {"template": self.jinja_text}},
        )
        try:
            self.error_message = None
            res = serialize_with_jinja_template(
                ET.fromstring(self.xml),
                config,
                enable_experimental_features=True,
            )
            self.is_valid = True
            self.output = res
            return res
        except jinja2.exceptions.UndefinedError as e:
            self.error_message = f"jinja2 exception Undefined Error : {e}"
            self.output = ""
            self.is_valid = False
            return self.error_message

        except jinja2.exceptions.TemplateSyntaxError as e:
            self.error_message = (
                f"Jinja expression Template Syntax Error : {e}"
            )
            self.output = ""
            self.is_valid = False
            return self.error_message
        except ET.ParseError as e:
            if self.xml == "":
                self.is_valid = True
                return self.output
            self.error_message = f"Unable to parse xml data: {e}"
            self.output = ""
            self.is_valid = False
            return self.error_message


class JinjaEditor(QtWidgets.QWidget):
    xml_data_changed = QtCore.Signal()
    jinja_expression_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widgets = _JinjaEditor(self)
        self._widgets.xml_text_edit_widget.textChanged.connect(
            self.xml_data_changed
        )
        self._widgets.jinja_expression.textChanged.connect(
            self.jinja_expression_changed
        )
        self._widget_layout = QtWidgets.QVBoxLayout(self)
        self._widget_layout.addWidget(self._widgets)
        self.xml_data_changed.connect(self.update_output)
        self.jinja_expression_changed.connect(self.update_output)

    def update_output(self):
        renderer = JinjaRenderer()
        renderer.jinja_text = self._widgets.jinja_expression.text
        renderer.xml = self._widgets.xml_text_edit_widget.toPlainText()
        self._widgets.output.setText(renderer.render())

        palette = self.palette()
        if renderer.is_valid:
            default_text_color = palette.text()
            self._widgets.output.setStyleSheet(
                f"color: {default_text_color.color().value()};"
            )
        else:
            alert_text = palette.highlightedText()
            error_style_sheet = (
                f"color: {alert_text.color().value()}; font-style: italic"
            )
            self._widgets.output.setStyleSheet(error_style_sheet)

    @property
    def pygments_style(self) -> str:
        return self._widgets.jinja_expression.pygments_style

    @pygments_style.setter
    def pygments_style(self, value: str) -> None:
        self._widgets.xml_text_edit_widget.pygments_style = value
        self._widgets.jinja_expression.pygments_style = value

    @property
    def jina_text(self) -> str:
        return self._widgets.jinja_expression.text

    @jina_text.setter
    def jina_text(self, value: str) -> None:
        self._widgets.jinja_expression.text = value

    @property
    def xml_text(self) -> str:
        return self._widgets.xml_text_edit_widget.toPlainText()

    @xml_text.setter
    def xml_text(self, value: str) -> None:
        self._widgets.xml_text_edit_widget.setPlainText(value)

    @property
    def output_text(self) -> str:
        return self._widgets.output.text()


class LineEditSyntaxHighlighting(QtWidgets.QPlainTextEdit):
    editingFinished = QtCore.Signal()
    style_colors_changed = QtCore.Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._highlighter = None
        self.padding = 10
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )  # Hide vertical scrollbar
        self.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setTabChangesFocus(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._style: Type[PygmentsStyle] = pygments.styles.get_style_by_name(
            "default"
        )
        self._highlighter = PygmentsHighlighter(parent=self.document())
        self._highlighter.lexer = pygments.lexers.get_lexer_by_name("jinja")
        self.setFont(
            QtGui.QFontDatabase.systemFont(
                QtGui.QFontDatabase.SystemFont.FixedFont
            )
        )

    @property
    def pygments_style(self) -> str:
        return self._style.name

    @pygments_style.setter
    def pygments_style(self, value: str) -> None:
        if value != self._style.name:
            self._style = pygments.styles.get_style_by_name(value)
            if self._highlighter is not None:
                self._highlighter.style = self._style
                self.style_colors_changed.emit()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Tab:
            self.editingFinished.emit()
            return
        super().keyPressEvent(event)

    @property
    def text(self):
        return self.toPlainText()

    @text.setter
    def text(self, value: str) -> None:
        self.setPlainText(value)

    def sizeHint(self, /):
        font_metrics = self.fontMetrics()
        line_height = font_metrics.height() + self.padding  # Add some padding
        return QtCore.QSize(self.width(), line_height)


class PygmentsHighlighter(QtGui.QSyntaxHighlighter):
    lexer_changed = QtCore.Signal()
    style_changed = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self._lexer = None
        self._style: Optional[Type[PygmentsStyle]] = None

    @property
    def lexer(self):
        return self._lexer

    @lexer.setter
    def lexer(self, value) -> None:
        if value != self._lexer:
            self._lexer = value
            self.lexer_changed.emit()
            self.rehighlight()

    @property
    def style(self) -> Optional[Type[PygmentsStyle]]:
        return self._style

    @style.setter
    def style(self, value: Type[PygmentsStyle]) -> None:
        if value != self._style:
            self._style = value
            self.style_changed.emit()
            self._formats = self._get_pygments_formats()
            self.rehighlight()

    def _get_pygments_formats(self):
        formats = {}
        for token_enum, style in self._style.list_styles():
            formats[token_enum] = self._create_format(
                color=QtGui.QColor(f"#{style['color']}"),
                italic=style["italic"],
                bold=style["bold"],
            )
        return formats

    def _create_format(
        self, color, bold=False, italic=False, underlined=False
    ):
        fmt = QtGui.QTextCharFormat()
        if bold:
            fmt.setFontWeight(QtGui.QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        if underlined:
            fmt.setUnderlineColor(color)
            fmt.setUnderlineStyle(
                QtGui.QTextCharFormat.UnderlineStyle.SingleUnderline
            )
        fmt.setForeground(color)
        return fmt

    def highlightBlock(self, text: str) -> None:
        if not self._lexer or not self._style:
            return
        for start, token_type, value in self._lexer.get_tokens_unprocessed(
            text
        ):
            length = len(value)
            if token_type in self._formats:
                self.setFormat(start, length, self._formats[token_type])
            else:
                logger.warning("%s was called but not implemented", token_type)


class TomlView(QtWidgets.QTreeView):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.clicked.connect(self._edit)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if (
            event.key() == QtCore.Qt.Key.Key_Return
            or event.key() == QtCore.Qt.Key.Key_Enter
        ):
            if self.state() != self.State.EditingState:
                for index in self.selectedIndexes():
                    if index.column() == 1:
                        self._edit(index)
        super().keyPressEvent(event)

    def _edit(self, index: QtCore.QModelIndex) -> None:
        if index.column() == 1:
            if index.internalPointer().is_editable:
                self.edit(index)


class MainWindow(QtWidgets.QMainWindow):
    save_file_requested = QtCore.Signal(QtCore.QUrl)
    open_file_requested = QtCore.Signal()
    status_message_updated = QtCore.Signal(str, int)

    @classmethod
    def is_model_data_different_than_file(
        cls,
        toml_file: pathlib.Path,
        toml_model: models.TomlModel,
        comparison_strategy=models.data_has_changed,
    ) -> bool:
        with toml_file.open() as f:
            og_text = f.read()
        return comparison_strategy(og_text, toml_model)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.toml_view = TomlView(parent=self)
        self.toml_view.setAlternatingRowColors(True)
        self._current_file: Optional[str] = None
        self.setCentralWidget(self.toml_view)
        # self.setWindowTitle("TOML Editor")
        toolbar = QtWidgets.QToolBar("File Toolbar")
        self.addToolBar(QtCore.Qt.ToolBarArea.LeftToolBarArea, toolbar)
        toolbar.setMovable(False)
        self.status_bar = self.statusBar()
        self.load_action = QtGui.QAction(
            QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.DocumentOpen),
            "&Open",
            self,
        )
        self.load_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self.save_action = QtGui.QAction(
            QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.DocumentSave),
            "&Save",
            enabled=False,
            parent=self,
        )
        self.save_action.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self._connect_toolbar(toolbar)
        self.addToolBar(QtCore.Qt.ToolBarArea.LeftToolBarArea, toolbar)
        self.state: MainWindowState = NoDocumentLoadedState(self)
        StateUtility.update_window(
            self, typing.cast(models.TomlModel, self.toml_view.model())
        )
        self.toml_view.setFocus()
        self.load_toml_strategy = load_toml
        self.write_toml_strategy = write_toml

    @property
    def unsaved_changes(self) -> bool:
        if self.toml_file is None:
            return False
        model = typing.cast(Optional[models.TomlModel], self.toml_view.model())
        if model is None:
            raise ValueError(
                f"toml model not loaded in viewer. toml_file = {self.toml_file}"
            )
        return self.is_model_data_different_than_file(
            pathlib.Path(self.toml_file), model
        )

    def _connect_toolbar(self, toolbar):
        self.load_action.triggered.connect(self.open_file_requested)
        toolbar.addAction(self.load_action)
        self.save_action.triggered.connect(
            lambda: self.save_file_requested.emit(
                QtCore.QUrl.fromLocalFile(self._current_file)
            )
            if self._current_file
            else None
        )
        toolbar.addAction(self.save_action)

    @property
    def toml_file(self) -> Optional[str]:
        return self._current_file

    @toml_file.setter
    def toml_file(self, value: Union[str, None]) -> None:
        self._current_file = value
        self.state.set_toml_file(
            pathlib.Path(value) if value is not None else None
        )

    def write_to_file(
        self, file: pathlib.Path, model: models.TomlModel
    ) -> None:
        self.state.write_toml_file(file, model)


def write_toml(
    toml_file: pathlib.Path,
    model: models.TomlModel,
    serialization_strategy=models.export_toml,
) -> None:
    data = serialization_strategy(model)
    with toml_file.open("w", encoding="utf-8") as f:
        f.write(data)


def load_toml(
    toml_file: pathlib.Path, load_strategy=models.load_toml_fp
) -> models.TomlModel:
    with toml_file.open() as fp:
        try:
            return load_strategy(fp)
        except galatea.merge_data.BadMappingDataError as e:
            raise galatea.merge_data.BadMappingFileError(
                source_file=toml_file,
                details=f"Error parsing {toml_file.name}.\n{e.details}",
            ) from e


class MainWindowState(abc.ABC):
    def __init__(self, context: MainWindow) -> None:
        self.context = context

    def set_toml_file(
        self,
        toml_file: Optional[pathlib.Path],
    ) -> None: ...
    def data_modified(self, toml_model: models.TomlModel): ...

    def write_toml_file(
        self, file: pathlib.Path, toml_model: models.TomlModel
    ): ...


class StateUtility:
    @classmethod
    def set_toml_file(
        cls, context: MainWindow, toml_file: Optional[pathlib.Path]
    ) -> None:
        if toml_file is None:
            context.save_action.setEnabled(False)
            context.toml_view.setModel(None)
            if context.toml_file is not None:
                context.toml_file = None
            return
        try:
            model = context.load_toml_strategy(pathlib.Path(toml_file))
            model.dataChanged.connect(
                lambda *_: context.state.data_modified(model)
            )

        except (
            galatea.merge_data.BadMappingFileError,
            galatea.merge_data.BadMappingDataError,
        ) as e:
            cls.reset_workspace(context)
            if context.toml_file is not None:
                context.toml_file = None
            context.status_message_updated.emit(e.details, logging.ERROR)
            context.status_message_updated.emit(
                f"Unable to open {pathlib.Path(toml_file).name}", logging.INFO
            )
            context.state = NoDocumentLoadedState(context)
            return
        model.setParent(context.toml_view)
        context.toml_view.setModel(model)
        context.toml_view.setColumnWidth(0, 300)
        context.status_message_updated.emit(
            f"Opened {pathlib.Path(toml_file).name}", logging.INFO
        )
        context.setWindowTitle(f"TOML Editor: {pathlib.Path(toml_file).name}")
        context.state = FileLoadedUnmodifiedState(context)

    @staticmethod
    def reset_workspace(context: MainWindow) -> None:
        context.setWindowTitle("TOML Editor")
        context.save_action.setEnabled(False)
        context.toml_view.setModel(None)
        context.state = NoDocumentLoadedState(context)

    @classmethod
    def update_window(
        cls, context: MainWindow, toml_model: Optional[models.TomlModel]
    ) -> None:
        if toml_model is None:
            # Then nothing is loaded and should be an empty document
            cls.reset_workspace(context)
            return

        if context.toml_file is not None:
            toml_file = pathlib.Path(context.toml_file)
            if context.unsaved_changes:
                context.save_action.setEnabled(True)
                context.setWindowTitle(
                    f"TOML Editor: {toml_file.name} (Unsaved)"
                )
                context.state = FileLoadedModifiedState(context)
            else:
                context.save_action.setEnabled(False)
                context.setWindowTitle(f"TOML Editor: {toml_file.name}")
                context.state = FileLoadedUnmodifiedState(context)


class NoDocumentLoadedState(MainWindowState):
    def set_toml_file(self, toml_file: Optional[pathlib.Path]) -> None:
        StateUtility.set_toml_file(context=self.context, toml_file=toml_file)


class FileLoadedModifiedState(MainWindowState):
    def set_toml_file(self, toml_file: Optional[pathlib.Path]) -> None:
        StateUtility.set_toml_file(context=self.context, toml_file=toml_file)
        StateUtility.update_window(
            context=self.context,
            toml_model=typing.cast(
                Optional[models.TomlModel], self.context.toml_view.model()
            ),
        )

    def data_modified(self, toml_model: models.TomlModel) -> None:
        StateUtility.update_window(context=self.context, toml_model=toml_model)

    def write_toml_file(
        self, file: pathlib.Path, toml_model: models.TomlModel
    ):
        self.context.write_toml_strategy(file, toml_model)
        StateUtility.update_window(context=self.context, toml_model=toml_model)


class FileLoadedUnmodifiedState(MainWindowState):
    def set_toml_file(self, toml_file: Optional[pathlib.Path]) -> None:
        StateUtility.set_toml_file(context=self.context, toml_file=toml_file)

    def data_modified(self, toml_model: models.TomlModel) -> None:
        StateUtility.update_window(context=self.context, toml_model=toml_model)
