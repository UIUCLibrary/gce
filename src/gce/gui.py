from __future__ import annotations

import typing
from typing import Type, Optional
from PySide6 import QtWidgets, QtCore, QtGui
import pygments.styles
import pygments.lexers

if typing.TYPE_CHECKING:
    from pygments.style import Style as PygmentsStyle

import logging

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
    def jinja_pygments_style(self):
        return self._jinja_editor.jinja_pygments_style

    @jinja_pygments_style.setter
    def jinja_pygments_style(self, value: str) -> None:
        self._jinja_editor.jinja_pygments_style = value


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

        self.xml_text_edit_widget = QtWidgets.QTextEdit(self)
        self.xml_text_edit_widget.setAcceptRichText(False)
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
        self.output.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.output.setReadOnly(True)
        self._widget_layout.addWidget(self.output, 4, 0, 1, 2)


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

    @property
    def jinja_pygments_style(self) -> str:
        return self._widgets.jinja_expression.pygments_style

    @jinja_pygments_style.setter
    def jinja_pygments_style(self, value: str) -> None:
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

        # Set a fixed height based on font metrics for a single line
        font_metrics = self.fontMetrics()
        line_height = font_metrics.height() + self.padding  # Add some padding
        self.setFixedHeight(line_height)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._style: Type[PygmentsStyle] = pygments.styles.get_style_by_name(
            "default"
        )
        self._highlighter = PygmentsHighlighter(parent=self.document())
        self._highlighter.lexer = pygments.lexers.get_lexer_by_name("jinja")

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
        # Prevent newlines (Enter key)
        if (
            event.key() == QtCore.Qt.Key.Key_Return
            or event.key() == QtCore.Qt.Key.Key_Enter
        ):
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
