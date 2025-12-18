import os
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout,
    QPushButton, QMessageBox, QProgressBar, QFrame
)

# Componentes
from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.views.components.timeline import Timeline
from src.views.components.forms.antgen_form import AntGenForm

'''
# Controladores y Modelos de antgen

from src.controllers.antgen_comp import AntgenCompiler
'''
from src.controllers.fetch_exeva import FetchAntgenController
from src.controllers.fetch_anexos import FetchAnexosController
from src.controllers.down_anexos import DownAnexosController
from src.models.project_data_manager import ProjectDataManager

class Exeva1Page(QWidget):
    log_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Exeva1Page")
        self.current_project_id = None
        self.is_loading = False

        # 1. Inicializar Lógica de Negocio (Controladores y Modelos)
        self._init_controllers()

        # 2. Construir Interfaz Gráfica (Layouts y Widgets)
        self._setup_ui()

        def _init_controllers(self):
            """Inicializa los controladores y conecta sus señales."""
            # Gestor de Datos
            self.data_manager = ProjectDataManager(self)
            self.data_manager.log_requested.connect(self.log_requested.emit)

            # Controlador de Extracción
            self.fetch_controller = FetchExEvaController(self)
            self.fetch_controller.log_requested.connect(self.log_requested.emit)
            self.fetch_controller.extraction_started.connect(self._on_extraction_started)
            self.fetch_controller.extraction_finished.connect(self._on_extraction_finished)
'''
            # Controlador de Compilación
            self.compiler = ExEvaCompiler(self)
            self.compiler.log_requested.connect(self.log_requested.emit)
            self.compiler.compilation_started.connect(self._on_compilation_started)
            self.compiler.compilation_finished.connect(self._on_compilation_finished)
'''


def _setup_ui(self):
    """Construye y organiza todos los elementos visuales de la página."""
    # Layout Principal
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # --- A. HEADER Y STATUS ---
    header_widget = QWidget()
    header_lay = QVBoxLayout(header_widget)
    header_lay.setContentsMargins(40, 30, 40, 10)

    self.header = Chapter("Antecedentes Generales")

    # Mini-layout para el Status en la derecha del header
    status_box = QWidget()
    sb_lay = QHBoxLayout(status_box)
    sb_lay.setContentsMargins(0, 5, 0, 0)
    sb_lay.setSpacing(15)
    sb_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

    sb_lay.addWidget(QLabel("Estado:", styleSheet="color:#555; font-weight:bold; font-size:13px;"))
    self.status_bar = StatusBar()
    self.status_bar.status_changed.connect(self.save_status_change)
    sb_lay.addWidget(self.status_bar)

    self.header.layout().addWidget(status_box)
    header_lay.addWidget(self.header)
    layout.addWidget(header_widget)

    # --- B. TIMELINE ---
    timeline_widget = QWidget()
    tl_lay = QVBoxLayout(timeline_widget)
    tl_lay.setContentsMargins(40, 0, 40, 10)

    self.timeline = Timeline(steps=[
            "Detectado", "Descargar", "Convertir",
            "Formatear", "Índice", "Compilar"
        ])
    tl_lay.addWidget(self.timeline)
    layout.addWidget(timeline_widget)

    # --- C. COMMAND BAR ---
    self.command_bar = CommandBar()
    self.command_bar.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)

    self.btn_fetchexeva = self.command_bar.add_button("1. Descargar Expediente", object_name="BtnActionPrimary")
    self.btn_fetchanexos = self.command_bar.add_button("2. Detectar Anexos", object_name="BtnActionPrimary")
    self.btn_downanexos = self.command_bar.add_button("3. Descargar Anexos", object_name="BtnActionPrimary")

    self.btn_fetchexeva.clicked.connect(self._on_fetchexeva_clicked)
    self.btn_fetchanexos.clicked.connect(self._on_fetchanexos_clicked)
    self.btn_downanexos.clicked.connect(self._on_downanexos_folder)

    self.pbar = QProgressBar(self.command_bar)
    self.pbar.setVisible(False)
    self.pbar.setFixedWidth(200)
    self.command_bar.button_layout.addWidget(self.pbar)

    layout.addWidget(self.command_bar)

    # --- D. ÁREA DE CONTENIDO (SCROLL) ---

    # POR COMPLETAR CON TABLA DE RESULTADOS

    # 2. Placeholder (Mensaje inicial)
    self.lbl_placeholder = QLabel("Pulse 'Extraer Información' para iniciar la búsqueda en el SEIA.")
    self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.content_layout.addWidget(self.lbl_placeholder)

    self.scroll.setWidget(self.content_widget)
    layout.addWidget(self.scroll)