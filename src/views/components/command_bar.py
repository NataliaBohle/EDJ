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
        # 1. Layout para botones a la izquierda
        self.left_layout = QHBoxLayout()
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(15)
        layout.addLayout(self.left_layout)

        # 2. Empujamos el contenido hacia el centro
        layout.addStretch()

        # 3. Creamos un layout secundario para los botones
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(15)
        layout.addLayout(self.button_layout)

        # 4. Empujamos el contenido desde la derecha
        layout.addStretch()

        # 5. Layout para botones a la derecha
        self.right_layout = QHBoxLayout()
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(15)
        layout.addLayout(self.right_layout)

    def add_button(self, text, icon=None, object_name="BtnCommand"):
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon:
            btn.setIcon(icon)

        # Agregamos al layout secundario de botones
        self.button_layout.addWidget(btn)
        return btn

    def add_left_button(self, text, icon=None, object_name="BtnCommand"):
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon:
            btn.setIcon(icon)
        self.left_layout.addWidget(btn)
        return btn

    def add_right_button(self, text, icon=None, object_name="BtnCommand"):
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon:
            btn.setIcon(icon)
        self.right_layout.addWidget(btn)
        return btn