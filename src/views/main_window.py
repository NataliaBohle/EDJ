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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.header = Header()
        self.main_layout.addWidget(self.header)

        self.menu = Menu()
        self.main_layout.addWidget(self.menu)
        self.menu.btn_new.clicked.connect(self.on_new_expediente)
        self.menu.btn_continue.clicked.connect(self.on_continue_expediente)

        # SPLITTER
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_layout.addWidget(self.splitter)

        self.workspace = QWidget()
        self.workspace.setObjectName("Workspace")
        self.splitter.addWidget(self.workspace)

        self.log_screen = LogScreen()
        self.splitter.addWidget(self.log_screen)

        # Configuración inicial
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        # --- CONEXIÓN DE LA SEÑAL DEL LOG ---
        self.log_screen.visibility_changed.connect(self.update_splitter_size)

    def on_new_expediente(self):
        self.log_screen.add_log("Iniciando creación de nuevo expediente...")

    def on_continue_expediente(self):
        self.log_screen.add_log("Retomando expediente existente...")

    # --- FUNCIÓN QUE MUEVE EL DIVISOR ---
    def update_splitter_size(self, collapsed):
        if collapsed:
            # Si se colapsa:
            # Asignamos un tamaño enorme al workspace (index 0)
            # y solo 35px al log (index 1)
            self.splitter.setSizes([100000, 35])

            # Opcional: Bloquear el splitter para que no lo arrastren cuando está cerrado
            # self.splitter.handle(1).setEnabled(False)
        else:
            # Si se expande:
            # Calculamos un tamaño razonable (ej. 150px para el log)
            total_height = self.splitter.height()
            self.splitter.setSizes([total_height - 150, 150])

            # self.splitter.handle(1).setEnabled(True)