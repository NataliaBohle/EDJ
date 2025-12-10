from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt


class NewId(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("NewId")

        # 1. Usamos Layout HORIZONTAL
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Sin márgenes extra
        layout.setSpacing(10)  # Espacio entre elementos
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Todo alineado a la izquierda
        self.setLayout(layout)

        # 2. Etiqueta
        label = QLabel("Ingrese ID de Proyecto:")
        label.setObjectName("NewIdLabel")
        layout.addWidget(label)

        # 3. Caja de Texto (Le damos un ancho fijo para que no sea gigante)
        self.input_id = QLineEdit()
        self.input_id.setPlaceholderText("Ej: 12345678")
        self.input_id.setObjectName("NewIdInput")
        self.input_id.setFixedWidth(200)  # Ancho controlado
        layout.addWidget(self.input_id)

        # 4. Botón Iniciar
        self.btn_start = QPushButton("Iniciar")
        self.btn_start.setObjectName("NewIdButton")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.btn_start)

        # 5. Empujar todo a la izquierda (el espacio vacío queda a la derecha)
        layout.addStretch()