from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton


class Menu(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Menu")

        self.setFixedHeight(50)
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 5, 20, 5)
        layout.setSpacing(15)
        self.setLayout(layout)

        # Botón 1: Nuevo Expediente
        self.btn_new = QPushButton("Nuevo Expediente")
        self.btn_new.setObjectName("BtnNew")
        layout.addWidget(self.btn_new)

        # Botón 2: Continuar Expediente
        self.btn_continue = QPushButton("Continuar Expediente")
        self.btn_continue.setObjectName("BtnContinue")
        layout.addWidget(self.btn_continue)
        layout.addStretch()