from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton


class Menu(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Menu")

        # Layout horizontal para los botones
        layout = QHBoxLayout()
        # Márgenes: Izquierda, Arriba, Derecha, Abajo
        layout.setContentsMargins(100, 10, 20, 10)
        layout.setSpacing(15)  # Espacio entre botones
        self.setLayout(layout)

        # Botón 1: Nuevo Expediente
        self.btn_new = QPushButton("Nuevo Expediente")
        self.btn_new.setObjectName("BtnNew")  # ID para darle color verde
        layout.addWidget(self.btn_new)

        # Botón 2: Continuar Expediente
        self.btn_continue = QPushButton("Continuar Expediente")
        self.btn_continue.setObjectName("BtnContinue")  # ID para darle color azul
        layout.addWidget(self.btn_continue)

        # Empujar botones a la izquierda (el espacio sobrante se va a la derecha)
        layout.addStretch()