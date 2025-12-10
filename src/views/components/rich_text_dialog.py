from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QActionGroup, QFont, QTextImageFormat, QTextListFormat
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QColorDialog,
    QFontComboBox,
    QToolBar,
    QVBoxLayout,
    QTextEdit,
    QInputDialog,
)

class RichTextEditorDialog(QDialog):
    """Dialogo sencillo para editar contenido enriquecido."""

    def __init__(self, parent=None, title: str = "Editar contenido", initial_html: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(True)
        if initial_html:
            # Usamos HTML para preservar tablas, imágenes u otro formato pegado
            self.editor.setHtml(initial_html)

        self.toolbar = self._build_toolbar()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.editor)

        self._validated = False

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        save_and_validate = buttons.addButton(
            "Guardar y validar", QDialogButtonBox.ButtonRole.AcceptRole
        )
        save_and_validate.clicked.connect(self._accept_and_validate)
        layout.addWidget(buttons)

    def was_validated(self) -> bool:
        return self._validated

    def _accept_and_validate(self) -> None:
        self._validated = True
        self.accept()

    def get_html(self) -> str:
        return self.editor.toHtml()

    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar(self)
        toolbar.setMovable(False)

        font_box = QFontComboBox(toolbar)
        font_box.currentFontChanged.connect(self.editor.setCurrentFont)
        toolbar.addWidget(font_box)

        size_box = QComboBox(toolbar)
        sizes = ["10", "12", "14", "16", "18", "24", "32", "48"]
        size_box.addItems(sizes)
        size_box.setCurrentText("12")
        size_box.setEditable(True)
        size_box.currentTextChanged.connect(self._update_font_size)
        toolbar.addWidget(size_box)

        bold_action = QAction("Negrita", toolbar)
        bold_action.setCheckable(True)
        bold_action.triggered.connect(self._toggle_bold)
        toolbar.addAction(bold_action)

        italic_action = QAction("Cursiva", toolbar)
        italic_action.setCheckable(True)
        italic_action.triggered.connect(self.editor.setFontItalic)
        toolbar.addAction(italic_action)

        underline_action = QAction("Subrayar", toolbar)
        underline_action.setCheckable(True)
        underline_action.triggered.connect(self.editor.setFontUnderline)
        toolbar.addAction(underline_action)

        strike_action = QAction("Tachado", toolbar)
        strike_action.setCheckable(True)
        strike_action.triggered.connect(self._toggle_strike)
        toolbar.addAction(strike_action)

        color_action = QAction("Color", toolbar)
        color_action.triggered.connect(self._pick_color)
        toolbar.addAction(color_action)

        toolbar.addSeparator()

        self.heading_box = QComboBox(toolbar)
        self.heading_box.addItems(["Párrafo", "Título 1", "Título 2", "Título 3"])
        self.heading_box.currentIndexChanged.connect(self._apply_heading)
        toolbar.addWidget(self.heading_box)

        bullet_action = QAction("• Lista", toolbar)
        bullet_action.triggered.connect(self._insert_bulleted_list)
        toolbar.addAction(bullet_action)

        numbered_action = QAction("1. Lista", toolbar)
        numbered_action.triggered.connect(self._insert_numbered_list)
        toolbar.addAction(numbered_action)

        toolbar.addSeparator()

        self.align_group = QActionGroup(toolbar)
        self.align_group.setExclusive(True)
        alignments = [
            ("Izq", Qt.AlignmentFlag.AlignLeft),
            ("Centro", Qt.AlignmentFlag.AlignHCenter),
            ("Der", Qt.AlignmentFlag.AlignRight),
            ("Just", Qt.AlignmentFlag.AlignJustify),
        ]
        for label, alignment in alignments:
            action = QAction(label, toolbar)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, a=alignment: self.editor.setAlignment(a))
            self.align_group.addAction(action)
            toolbar.addAction(action)
        self.align_group.actions()[0].setChecked(True)

        toolbar.addSeparator()

        image_action = QAction("Imagen", toolbar)
        image_action.triggered.connect(self._insert_image)
        toolbar.addAction(image_action)

        table_action = QAction("Tabla", toolbar)
        table_action.triggered.connect(self._insert_table)
        toolbar.addAction(table_action)

        horizontal_action = QAction("Línea", toolbar)
        horizontal_action.triggered.connect(self._insert_horizontal_rule)
        toolbar.addAction(horizontal_action)

        quote_action = QAction("Cita", toolbar)
        quote_action.triggered.connect(self._toggle_blockquote)
        toolbar.addAction(quote_action)

        self.editor.selectionChanged.connect(self._sync_actions)
        self.editor.cursorPositionChanged.connect(self._sync_actions)

        return toolbar

    def _update_font_size(self, size_text: str) -> None:
        try:
            size = float(size_text)
        except ValueError:
            return
        self.editor.setFontPointSize(size)

    def _toggle_bold(self, checked: bool) -> None:
        weight = QFont.Weight.Bold if checked else QFont.Weight.Normal
        self.editor.setFontWeight(weight)

    def _toggle_strike(self, checked: bool) -> None:
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontStrikeOut(checked)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(parent=self, initial=self.editor.textColor())
        if color.isValid():
            self.editor.setTextColor(color)

    def _apply_heading(self, index: int) -> None:
        cursor = self.editor.textCursor()
        block_format = cursor.blockFormat()
        char_format = cursor.charFormat()

        sizes = [12, 20, 16, 14]
        weights = [QFont.Weight.Normal, QFont.Weight.Bold, QFont.Weight.Bold, QFont.Weight.DemiBold]

        char_format.setFontPointSize(sizes[index])
        char_format.setFontWeight(weights[index])
        block_format.setHeadingLevel(index)

        cursor.mergeCharFormat(char_format)
        cursor.mergeBlockFormat(block_format)
        self.editor.setTextCursor(cursor)

    def _insert_bulleted_list(self) -> None:
        cursor = self.editor.textCursor()
        fmt = QTextListFormat()
        fmt.setStyle(QTextListFormat.Style.ListDisc)
        cursor.createList(fmt)

    def _insert_numbered_list(self) -> None:
        cursor = self.editor.textCursor()
        fmt = QTextListFormat()
        fmt.setStyle(QTextListFormat.Style.ListDecimal)
        cursor.createList(fmt)

    def _insert_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Insertar imagen",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif);;Todos los archivos (*)",
        )
        if not filename:
            return
        cursor = self.editor.textCursor()
        img_format = QTextImageFormat()
        img_format.setName(filename)
        cursor.insertImage(img_format)

    def _insert_table(self) -> None:
        rows, ok_rows = QInputDialog.getInt(self, "Insertar tabla", "Número de filas:", 3, 1, 30)
        if not ok_rows:
            return
        cols, ok_cols = QInputDialog.getInt(self, "Insertar tabla", "Número de columnas:", 3, 1, 15)
        if not ok_cols:
            return
        cursor = self.editor.textCursor()
        cursor.insertTable(rows, cols)

    def _insert_horizontal_rule(self) -> None:
        cursor = self.editor.textCursor()
        cursor.insertHtml("<hr />")

    def _toggle_blockquote(self) -> None:
        cursor = self.editor.textCursor()
        block_format = cursor.blockFormat()
        left_margin = 30 if block_format.leftMargin() == 0 else 0
        block_format.setLeftMargin(left_margin)
        cursor.mergeBlockFormat(block_format)
        self.editor.setTextCursor(cursor)

    def _sync_actions(self) -> None:
        cursor = self.editor.textCursor()
        char_format = cursor.charFormat()
        block_format = cursor.blockFormat()

        for action in self.toolbar.actions():
            text = action.text()
            if text == "Negrita":
                action.setChecked(char_format.fontWeight() >= QFont.Weight.Bold)
            elif text == "Cursiva":
                action.setChecked(char_format.fontItalic())
            elif text == "Subrayar":
                action.setChecked(char_format.fontUnderline())
            elif text == "Tachado":
                action.setChecked(char_format.fontStrikeOut())
            elif text in {"Izq", "Centro", "Der", "Just"}:
                alignment = self.editor.alignment()
                expected = {
                    "Izq": Qt.AlignmentFlag.AlignLeft,
                    "Centro": Qt.AlignmentFlag.AlignHCenter,
                    "Der": Qt.AlignmentFlag.AlignRight,
                    "Just": Qt.AlignmentFlag.AlignJustify,
                }[text]
                action.setChecked(alignment == expected)

        heading_level = block_format.headingLevel()
        self.heading_box.blockSignals(True)
        self.heading_box.setCurrentIndex(min(max(heading_level, 0), self.heading_box.count() - 1))
        self.heading_box.blockSignals(False)