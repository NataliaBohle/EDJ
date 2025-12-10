from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt


class CommandBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("CommandBar")

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)

        # --- CAMBIO: Alineación Central ---
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def add_button(self, text, icon=None, object_name="BtnCommand"):
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon:
            btn.setIcon(icon)

        self.layout().addWidget(btn)
        return btn