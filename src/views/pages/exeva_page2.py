from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout, QFrame
)

from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.views.components.timeline import Timeline
from src.models.project_data_manager import ProjectDataManager


class Exeva2Page(QWidget):
    log_requested = pyqtSignal(str)
    back_requested = pyqtSignal(str)
    continue_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Exeva2Page")
        self.current_project_id = None
        self.is_loading = False

        self._init_controllers()
        self._setup_ui()

    def _init_controllers(self):
        self.data_manager = ProjectDataManager(self)
        self.data_manager.log_requested.connect(self.log_requested.emit)

    def _setup_ui(self):
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

        self.btn_back_step1 = self.command_bar.add_left_button(
            "Volver a Paso 1", object_name="BtnActionFolder"
        )
        self.btn_continue_step3 = self.command_bar.add_right_button(
            "Continuar a paso 3", object_name="BtnActionPrimary"
        )

        self.btn_back_step1.clicked.connect(self._on_back_clicked)
        self.btn_continue_step3.clicked.connect(self._on_continue_clicked)

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
            "La tabla de resultados de EXEVA Paso 2 se configurará en la siguiente etapa."
        )
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.lbl_placeholder)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def load_project(self, pid: str):
        self.current_project_id = pid
        self.is_loading = True
        self.header.title_label.setText(f"Expediente EXEVA - Paso 2 - ID {pid}")
        step_idx = 2
        step_status = "detectado"
        global_status = "detectado"

        self.timeline.set_current_step(step_idx, step_status)
        self.status_bar.set_status(global_status)
        self.data_manager.update_step_status(
            self.current_project_id,
            "EXEVA",
            step_index=step_idx,
            step_status=step_status,
            global_status=global_status,
        )
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

    def _on_back_clicked(self):
        if not self.current_project_id:
            return
        self.back_requested.emit(self.current_project_id)

    def _on_continue_clicked(self):
        if not self.current_project_id:
            return
        self.continue_requested.emit(self.current_project_id)
