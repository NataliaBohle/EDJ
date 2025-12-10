# src/views/components/command_bar.py

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt


class CommandBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("CommandBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)

        # 1. Empujamos el contenido desde la izquierda
        layout.addStretch()

        # 2. Creamos un layout secundario para los botones
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(15)
        layout.addLayout(self.button_layout)

        # 3. Empujamos el contenido desde la derecha
        layout.addStretch()

    def add_button(self, text, icon=None, object_name="BtnCommand"):
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon:
            btn.setIcon(icon)

        # Agregamos al layout secundario de botones
        self.button_layout.addWidget(btn)
        return btn