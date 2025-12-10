from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QWidget, QPlainTextEdit, QVBoxLayout, QPushButton, \
    QSizePolicy, QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextOption
from src.views.components.mini_status import MiniStatusBar
from src.views.components.rich_text_dialog import RichTextEditorDialog

class FieldRow(QFrame):
    status_changed = pyqtSignal(str)

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

    def _open_rich_editor_dialog(self):
        dialog = RichTextEditorDialog(
            self,
            title=f"Editar {self.label_text}",
            initial_html=self.editor.toHtml(),
        )
        if dialog.exec():
            self.editor.setHtml(dialog.get_html())