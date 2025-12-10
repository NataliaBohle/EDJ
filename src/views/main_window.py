from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from src.views.components.header import Header
from src.views.components.menu import Menu

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDJ App")
        self.resize(800, 600)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Configurar el layout principal (Vertical)
        # Los elementos agregados aquí se estirarán al ancho total automáticamente
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)  # Elimina bordes blancos alrededor
        self.layout.setSpacing(0)

        # Agregar el Header
        self.header = Header()
        self.layout.addWidget(self.header)

        # Agrega el Menu
        self.menu = Menu()
        self.layout.addWidget(self.menu)

        # Añadir un espacio flexible al final para empujar el header hacia arriba
        self.layout.addStretch()