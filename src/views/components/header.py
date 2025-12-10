from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

class Header(QWidget):
    def __init__(self):
        super().__init__()
        # Asignamos un ID para usarlo en el QSS
        self.setObjectName("Header")

        layout = QHBoxLayout()
        # Quitamos los márgenes del layout para que el color toque los bordes
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)

        title_label = QLabel("EDJ App")
        title_label.setObjectName("HeaderTitle") # ID para el texto
        layout.addWidget(title_label)