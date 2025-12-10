from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QWidget, QPlainTextEdit, QVBoxLayout, QPushButton, \
    QSizePolicy, QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextOption
from src.views.components.mini_status import MiniStatusBar
from src.views.components.rich_text_dialog import RichTextEditorDialog

class FieldRow(QFrame):
    status_changed = pyqtSignal(str)
    content_changed = pyqtSignal()

    def __init__(self, label_text: str, parent: QWidget | None = None, is_multiline: bool = False,
                 rich_editor: bool = False):
        super().__init__(parent)
        self.setObjectName("FieldRow")
        self.label_text = label_text
        self.rich_editor = rich_editor

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 5, 0, 5)  # Pequeño margen vertical
        layout.setSpacing(10)
        self.setLayout(layout)

        # 1. Etiqueta
        lbl = QLabel(label_text, self)
        lbl.setFixedWidth(180)  # Ancho fijo para alineación vertical
        lbl.setObjectName("FieldRowLabel")
        layout.addWidget(lbl)

        editor_container = QWidget(self)
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(4)

        # 2. Editor (Campo de entrada)
        if is_multiline:
            if rich_editor:
                self.editor = QTextEdit(self)
                self.editor.setAcceptRichText(True)
                self.editor.setMinimumHeight(80)
            else:
                self.editor = QPlainTextEdit(self)
                self.editor.setMinimumHeight(60)
            self.editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        else:
            self.editor = QLineEdit(self)

        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._connect_change_signal()
        self._update_editor_height()
        editor_layout.addWidget(self.editor)

        if is_multiline and rich_editor:
            self.rich_button = QPushButton("Editar en ventana", self)
            self.rich_button.setObjectName("FieldRowRichButton")
            self.rich_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.rich_button.setFixedWidth(140)
            self.rich_button.clicked.connect(self._open_rich_editor_dialog)
            editor_layout.addWidget(self.rich_button, alignment=Qt.AlignmentFlag.AlignRight)

        # 3. Empujar el editor para que ocupe el espacio restante
        layout.addWidget(editor_container, stretch=1)

        # 4. Mini Status Bar
        self.status_bar = MiniStatusBar(self)
        self.status_bar.setFixedWidth(120)
        # Conectar el cambio de estado a la señal de la fila
        self.status_bar.status_changed.connect(self.status_changed)
        layout.addWidget(self.status_bar)

    def _connect_change_signal(self):
        if isinstance(self.editor, QLineEdit):
            self.editor.textChanged.connect(self.content_changed.emit)
        else:
            self.editor.textChanged.connect(self._on_multiline_changed)

    def get_value(self):
        if isinstance(self.editor, QTextEdit):
            return self.editor.toHtml() if self.rich_editor else self.editor.toPlainText()
        if isinstance(self.editor, QPlainTextEdit):
            return self.editor.toPlainText()
        return self.editor.text()

    def _open_rich_editor_dialog(self):
        dialog = RichTextEditorDialog(
            self,
            title=f"Editar {self.label_text}",
            initial_html=self.editor.toHtml(),
        )
        if dialog.exec():
            self.editor.setHtml(dialog.get_html())
            if dialog.was_validated():
                self.status_bar.set_status("verificado")
                self.status_changed.emit("verificado")

    def _on_multiline_changed(self):
        self._update_editor_height()
        self.content_changed.emit()

    def _update_editor_height(self):
        if not isinstance(self.editor, (QPlainTextEdit, QTextEdit)):
            return

        document = self.editor.document()
        document.setTextWidth(self.editor.viewport().width())
        contents_height = int(document.size().height())

        margins = self.editor.contentsMargins()
        frame = int(self.editor.frameWidth() * 2)
        min_height = 80 if isinstance(self.editor, QTextEdit) else 60

        line_height = self.editor.fontMetrics().lineSpacing()
        max_lines = 10
        max_allowed_height = line_height * max_lines + margins.top() + margins.bottom() + frame + 6

        target_height = max(min_height, min(max_allowed_height, contents_height + margins.top() + margins.bottom() + frame + 6))
        self.editor.setMinimumHeight(target_height)
        self.editor.setMaximumHeight(target_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_editor_height()
