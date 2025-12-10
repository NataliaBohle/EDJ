from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QWidget, QPlainTextEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextOption  # <-- ¡NUEVA IMPORTACIÓN NECESARIA!
# Necesitamos MiniStatusBar para el estado por campo
from src.views.components.mini_status import MiniStatusBar


class FieldRow(QFrame):
    """
    Componente reutilizable para una fila de datos editable con estado de validación.
    Combina Label, Editor (LineEdit o TextEdit) y MiniStatusBar.
    """
    # Señal que se emite cuando el usuario cambia el estado del campo
    status_changed = pyqtSignal(str)

    def __init__(self, label_text: str, parent: QWidget | None = None, is_multiline: bool = False):
        super().__init__(parent)
        self.setObjectName("FieldRow")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 5, 0, 5)  # Pequeño margen vertical
        layout.setSpacing(10)
        self.setLayout(layout)

        # 1. Etiqueta
        lbl = QLabel(label_text, self)
        lbl.setFixedWidth(180)  # Ancho fijo para alineación vertical
        lbl.setObjectName("FieldRowLabel")
        layout.addWidget(lbl)

        # 2. Editor (Campo de entrada)
        if is_multiline:
            self.editor = QPlainTextEdit(self)
            self.editor.setMinimumHeight(60)  # Altura mínima para multilínea

            # --- CORRECCIÓN FINAL ---
            # Usamos el enum correcto para asegurar que el texto envuelva al ancho del widget.
            self.editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        else:
            self.editor = QLineEdit(self)

        # 3. Empujar el editor para que ocupe el espacio restante
        layout.addWidget(self.editor, stretch=1)

        # 4. Mini Status Bar
        self.status_bar = MiniStatusBar(self)
        self.status_bar.setFixedWidth(120)
        # Conectar el cambio de estado a la señal de la fila
        self.status_bar.status_changed.connect(self.status_changed)
        layout.addWidget(self.status_bar)