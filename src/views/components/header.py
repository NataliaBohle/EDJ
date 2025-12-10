from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
class Header(QFrame):
    def __init__(self):
        super().__init__()
        # Asignamos un ID para usarlo en el QSS
        self.setObjectName("Header")

        # Configurar altura fija (como preguntaste antes)
        self.setFixedHeight(90)

        layout = QHBoxLayout()
        # Quitamos los márgenes para que el color llegue al borde
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        title_label = QLabel("EDJ App")
        title_label.setObjectName("HeaderTitle")
        layout.addWidget(title_label)