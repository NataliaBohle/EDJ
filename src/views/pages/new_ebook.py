from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from src.views.components.chapter import Chapter
from src.views.components.new_id import NewId


class NewEbook(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("NewEbookPage")

        # Layout vertical para la página
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Alineamos todo arriba
        layout.setContentsMargins(20, 20, 20, 20)  # Margen generoso alrededor
        layout.setSpacing(20)  # Espacio entre el título y el formulario
        self.setLayout(layout)

        # 1. Agregamos el Chapter (Título)
        self.chapter = Chapter("Nuevo Expediente")
        layout.addWidget(self.chapter)

        # 2. Agregamos el Formulario
        self.form_id = NewId()
        layout.addWidget(self.form_id)

        # Espacio flexible al final
        layout.addStretch()