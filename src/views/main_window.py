from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt
from src.views.components.header import Header
from src.views.components.menu import Menu
from src.views.components.log_screen import LogScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDJ App")
        self.resize(800, 600)

        # Widget central base
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal (Vertical)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. ELEMENTOS FIJOS (Header y Menu)
        self.header = Header()
        self.main_layout.addWidget(self.header)

        self.menu = Menu()
        self.main_layout.addWidget(self.menu)

        # 2. ZONA DE DIVISIÓN (Splitter)
        # Esto permite redimensionar entre el área de trabajo y el log
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_layout.addWidget(self.splitter)

        # --- Parte Superior del Splitter: Área de Trabajo ---
        # Aquí irán tus tablas o formularios en el futuro
        self.workspace = QWidget()
        self.workspace.setObjectName("Workspace") # ID para darle color si quieres
        self.splitter.addWidget(self.workspace)

        # --- Parte Inferior del Splitter: LogScreen ---
        self.log_screen = LogScreen()
        self.splitter.addWidget(self.log_screen)

        # Configuración inicial del Splitter:
        # Darle mucho espacio al workspace (índice 0) y menos al log (índice 1)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        # --- FUNCIONES DE ACCIÓN ---
        def on_new_expediente(self):
            # 1. Escribir en el log
            self.log_screen.add_log("Iniciando creación de nuevo expediente...")

            # Aquí iría la lógica futura (ej. limpiar tabla, mostrar formulario)
            print("Lógica de nuevo expediente aquí")

        def on_continue_expediente(self):
            self.log_screen.add_log("Retomando expediente existente...")
            # Aquí iría la lógica para cargar datos