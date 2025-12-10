from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt
from src.views.components.header import Header
from src.views.components.menu import Menu
from src.views.components.log_screen import LogScreen
from src.views.components.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDJ App")
        self.resize(1100, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout Principal (Solo tiene Header y el Splitter Principal)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. HEADER (Arriba del todo)
        self.header = Header()
        self.main_layout.addWidget(self.header)

        # 2. SPLITTER HORIZONTAL PRINCIPAL
        # Izquierda: Sidebar | Derecha: Área de Contenido
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setHandleWidth(1)
        self.main_layout.addWidget(self.h_splitter)

        # --- LADO IZQUIERDO: SIDEBAR ---
        self.sidebar = Sidebar()
        self.h_splitter.addWidget(self.sidebar)

        # --- LADO DERECHO: ÁREA DE CONTENIDO ---
        # Creamos un widget contenedor para agrupar (Menu + Tablas + Log)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # A. Agregamos el MENU arriba del contenido
        self.menu = Menu()
        self.content_layout.addWidget(self.menu)

        # B. Agregamos el Splitter Vertical (Workspace + Log) debajo del menú
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(1)
        self.content_layout.addWidget(self.v_splitter)

        # C. Elementos del Splitter Vertical
        self.workspace = QWidget()
        self.workspace.setObjectName("Workspace")
        self.v_splitter.addWidget(self.workspace)

        self.log_screen = LogScreen()
        self.v_splitter.addWidget(self.log_screen)

        # Finalmente, agregamos todo este lado derecho al splitter principal
        self.h_splitter.addWidget(self.content_area)

        # --- CONEXIONES ---
        self.menu.btn_new.clicked.connect(self.on_new_expediente)
        self.menu.btn_continue.clicked.connect(self.on_continue_expediente)
        self.log_screen.visibility_changed.connect(self.update_log_splitter)

        # --- TAMAÑOS INICIALES ---
        self.h_splitter.setCollapsible(0, False)
        self.h_splitter.setSizes([220, 880])  # Sidebar 220px
        self.h_splitter.setStretchFactor(1, 1)

        self.v_splitter.setCollapsible(0, False)
        self.v_splitter.setSizes([550, 150])  # Log 150px
        self.v_splitter.setStretchFactor(0, 1)

    # --- FUNCIONES ---
    def on_new_expediente(self):
        self.log_screen.add_log("Iniciando creación de nuevo expediente...")
        self.sidebar.add_option(f"Expediente Nuevo")

    def on_continue_expediente(self):
        self.log_screen.add_log("Retomando expediente existente...")

    def update_log_splitter(self, collapsed):
        if collapsed:
            self.v_splitter.setSizes([100000, 35])
        else:
            h = self.v_splitter.height()
            self.v_splitter.setSizes([h - 150, 150])