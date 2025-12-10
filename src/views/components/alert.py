from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt


class Alert(QDialog):
    def __init__(self, parent=None, title="Alerta", message="Mensaje", alert_type="warning"):
        super().__init__(parent)
        self.setObjectName("AlertDialog")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(400, 200)  # Tamaño fijo compacto

        # Layout principal
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)

        # 1. Título
        lbl_title = QLabel(title)
        lbl_title.setObjectName("AlertTitle")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # 2. Mensaje (Dinámico)
        lbl_msg = QLabel(message)
        lbl_msg.setObjectName("AlertMessage")
        lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_msg.setWordWrap(True)  # Permitir varias líneas
        layout.addWidget(lbl_msg)

        # 3. Botón Aceptar
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Aceptar")
        btn_ok.setObjectName("AlertButton")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(self.accept)  # Cierra el diálogo
        btn_layout.addWidget(btn_ok)

        layout.addStretch()
        layout.addLayout(btn_layout)