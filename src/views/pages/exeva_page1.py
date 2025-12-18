from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout,
    QProgressBar, QFrame, QMessageBox
)

# Componentes
from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.views.components.timeline import Timeline

# Controladores y Modelos de antgen
from src.controllers.fetch_exeva import FetchExevaController
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
        """Inicializa gestores y futuros controladores."""
        self.data_manager = ProjectDataManager(self)
        self.data_manager.log_requested.connect(self.log_requested.emit)

        # Controladores a implementar en siguientes iteraciones
        self.fetch_controller = FetchExevaController(self)
        self.fetch_controller.log_requested.connect(self.log_requested.emit)
        self.fetch_controller.extraction_started.connect(self._on_extraction_started)
        self.fetch_controller.extraction_finished.connect(self._on_extraction_finished)
        self.fetch_anexos_controller = None
        self.down_anexos_controller = None

    def _setup_ui(self):
        """Construye la interfaz gráfica siguiendo el patrón de AntGen."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- A. HEADER Y STATUS ---
        header_widget = QWidget()
        header_lay = QVBoxLayout(header_widget)
        header_lay.setContentsMargins(40, 30, 40, 10)

        self.header = Chapter("Evaluación Ambiental")

        status_box = QWidget()
        sb_lay = QHBoxLayout(status_box)
        sb_lay.setContentsMargins(0, 5, 0, 0)
        sb_lay.setSpacing(15)
        sb_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

        lbl_estado = QLabel("Estado:")
        lbl_estado.setStyleSheet("color:#555; font-weight:bold; font-size:13px;")
        sb_lay.addWidget(lbl_estado)

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

        self.btn_fetchexeva = self.command_bar.add_button(
            "1. Descargar Expediente", object_name="BtnActionPrimary"
        )
        self.btn_fetchanexos = self.command_bar.add_button(
            "2. Detectar Anexos", object_name="BtnActionPrimary"
        )
        self.btn_downanexos = self.command_bar.add_button(
            "3. Descargar Anexos", object_name="BtnActionPrimary"
        )

        self.btn_fetchexeva.clicked.connect(self._on_fetchexeva_clicked)
        self.btn_fetchanexos.clicked.connect(self._on_fetchanexos_clicked)
        self.btn_downanexos.clicked.connect(self._on_downanexos_clicked)

        self.pbar = QProgressBar(self.command_bar)
        self.pbar.setVisible(False)
        self.pbar.setFixedWidth(200)
        self.command_bar.button_layout.addWidget(self.pbar)

        layout.addWidget(self.command_bar)

        # --- D. ÁREA DE CONTENIDO (SCROLL) ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 30, 40, 30)
        self.content_layout.setSpacing(15)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_placeholder = QLabel(
            "Los resultados del expediente EXEVA aparecerán aquí una vez implementada la extracción."
        )
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.lbl_placeholder)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def load_project(self, pid: str):
        """Carga el estado del proyecto desde disco y ajusta la UI."""
        self.current_project_id = pid
        self.is_loading = True
        self.header.title_label.setText(f"Expediente EXEVA - ID {pid}")

        data = self.data_manager.load_data(pid)
        exeva_section = data.get("expedientes", {}).get("EXEVA", {})
        exeva_payload = exeva_section.get("EXEVA_DATA", {})

        step_idx = exeva_section.get("step_index", 0)
        step_status = exeva_section.get("step_status", "detectado")
        global_status = exeva_section.get("status", "detectado")

        self.timeline.set_current_step(step_idx, step_status)
        self.status_bar.set_status(global_status)

        documentos = exeva_payload.get("EXEVA", {}).get("documentos", [])
        has_docs = bool(documentos)

        if has_docs:
            total = len(documentos)
            self.lbl_placeholder.setText(f"Expediente descargado: {total} documentos detectados.")
            self.btn_fetchexeva.setText("Volver a Descargar")
        else:
            self.lbl_placeholder.setText(
                "Los resultados del expediente EXEVA aparecerán aquí una vez implementada la extracción."
            )
            self.btn_fetchexeva.setText("1. Descargar Expediente")
        self.lbl_placeholder.setVisible(True)
        self.is_loading = False

    def save_status_change(self, new_status: str):
        if self.is_loading or not self.current_project_id:
            return

        idx = self.timeline.current_step
        self.timeline.set_current_step(idx, new_status)
        self.data_manager.update_step_status(
            self.current_project_id,
            "EXEVA",
            step_index=idx,
            step_status=new_status,
            global_status=new_status,
        )

    # --- ACCIONES (PLACEHOLDERS) ---

    def _on_fetchexeva_clicked(self):
        if not self.current_project_id:
            return
        self.status_bar.set_status("edicion")
        self.fetch_controller.start_extraction(self.current_project_id)

    def _on_fetchanexos_clicked(self):
        if not self.current_project_id:
            return
        self.log_requested.emit("🚧 Detectar anexos pendiente de implementación.")

    def _on_downanexos_clicked(self):
        if not self.current_project_id:
            return
        self.log_requested.emit("🚧 Descarga de anexos pendiente de implementación.")

    # --- SLOTS ASYNC ---

    def _on_extraction_started(self):
        self.btn_fetchexeva.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.lbl_placeholder.setVisible(False)

    def _on_extraction_finished(self, success: bool, data: dict):
        self.pbar.setVisible(False)
        self.btn_fetchexeva.setEnabled(True)
        self.pbar.setRange(0, 100)

        if success:
            documentos = data.get("EXEVA", {}).get("documentos", [])
            total = len(documentos)
            self.lbl_placeholder.setText(f"Expediente descargado: {total} documentos detectados.")
            self.lbl_placeholder.setVisible(True)
            self.status_bar.set_status("edicion")
            self.timeline.set_current_step(1, "edicion")
            self.data_manager.update_step_status(
                self.current_project_id, "EXEVA", step_index=1, step_status="edicion", global_status="edicion"
            )
            self.btn_fetchexeva.setText("Volver a Descargar")
        else:
            self.status_bar.set_status("error")
            self.timeline.set_current_step(self.timeline.current_step, "error")
            self.lbl_placeholder.setText("No se pudo descargar el expediente. Intente nuevamente.")
            self.lbl_placeholder.setVisible(True)
            QMessageBox.critical(self, "Error", "Fallo en la extracción de EXEVA.")
