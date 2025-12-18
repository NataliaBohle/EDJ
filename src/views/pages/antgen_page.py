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

# Controladores y Modelos
from src.controllers.fetch_antgen import FetchAntgenController
from src.controllers.antgen_comp import AntgenCompiler
from src.models.project_data_manager import ProjectDataManager


class AntGenPage(QWidget):
    log_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("AntGenPage")
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
        self.fetch_controller = FetchAntgenController(self)
        self.fetch_controller.log_requested.connect(self.log_requested.emit)
        self.fetch_controller.extraction_started.connect(self._on_extraction_started)
        self.fetch_controller.extraction_finished.connect(self._on_extraction_finished)

        # Controlador de Compilación
        self.compiler = AntgenCompiler(self)
        self.compiler.log_requested.connect(self.log_requested.emit)
        self.compiler.compilation_started.connect(self._on_compilation_started)
        self.compiler.compilation_finished.connect(self._on_compilation_finished)

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

        self.timeline = Timeline(steps=["Detectado", "Descargar", "Compilar"])
        tl_lay.addWidget(self.timeline)
        layout.addWidget(timeline_widget)

        # --- C. COMMAND BAR ---
        self.command_bar = CommandBar()
        self.command_bar.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_fetch = self.command_bar.add_button("Extraer Información", object_name="BtnActionPrimary")
        self.btn_compile = self.command_bar.add_button("Compilar en PDF", object_name="BtnActionSuccess")
        self.btn_folder = self.command_bar.add_button("Ver Carpeta", object_name="BtnActionFolder")

        self.btn_fetch.clicked.connect(self._on_fetch_clicked)
        self.btn_compile.clicked.connect(self._on_compile_clicked)
        self.btn_folder.clicked.connect(self._on_open_folder)

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

        # 1. Formulario Modular (Aquí vive toda la complejidad de campos)
        self.form = AntGenForm()
        self.form.setVisible(False)

        # Conexiones del formulario
        self.form.data_changed.connect(self._save_field_values)
        self.form.status_changed.connect(self._save_field_statuses)
        self.form.status_changed.connect(self._check_global_status)

        self.content_layout.addWidget(self.form)

        # 2. Placeholder (Mensaje inicial)
        self.lbl_placeholder = QLabel("Pulse 'Extraer Información' para iniciar la búsqueda en el SEIA.")
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.lbl_placeholder)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    # --- LÓGICA ---

    def load_project(self, pid):
        self.current_project_id = pid
        self.is_loading = True
        self.header.title_label.setText(f"Antecedentes Generales - ID {pid}")

        data = self.data_manager.load_data(pid)
        ant_section = data.get("expedientes", {}).get("ANTGEN", {})
        payload = ant_data = ant_section.get("ANTGEN_DATA", {})

        exists = bool(payload)
        self.form.setVisible(exists)
        self.lbl_placeholder.setVisible(not exists)

        if exists:
            # Delegamos el llenado al formulario
            self.form.set_data(payload, ant_section.get("field_statuses", {}))

            st_global = ant_section.get("status", "detectado")
            # Leemos el estado del paso guardado
            step_idx = ant_section.get("step_index", 0)
            step_st = ant_section.get("step_status", "detectado")

            self.status_bar.set_status(st_global)
            # Restauramos el timeline visualmente
            self.timeline.set_current_step(step_idx, step_st)

            self.btn_fetch.setText("Volver a Extraer")
        else:
            self.status_bar.set_status("detectado")
            self.timeline.set_current_step(0, "detectado")
            self.btn_fetch.setText("Extraer Información")

        self.btn_fetch.setEnabled(True)
        self.is_loading = False

    # --- ACCIONES ---

    def _on_fetch_clicked(self):
        if not self.current_project_id: return
        self.status_bar.set_status("edicion")
        self.fetch_controller.start_extraction(self.current_project_id)

    def _on_compile_clicked(self):
        if not self.current_project_id: return
        # El formulario sabe cómo recolectar su data
        payload = self.form.get_data()
        self.compiler.compile_pdf(self.current_project_id, payload)

    def _on_open_folder(self):
        if not self.current_project_id: return
        path = os.path.join(os.getcwd(), "Ebook", self.current_project_id)
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # --- PERSISTENCIA ---

    def save_status_change(self, new_status):
        if self.is_loading or not self.current_project_id: return
        idx = self.timeline.current_step
        self.timeline.set_current_step(idx, new_status)
        self.data_manager.update_step_status(
            self.current_project_id, "ANTGEN",
            step_index=idx, step_status=new_status, global_status=new_status
        )

    def _save_field_values(self):
        if self.is_loading or not self.current_project_id: return
        self.data_manager.save_antgen_field_data(self.current_project_id, self.form.get_data())

    def _save_field_statuses(self):
        if self.is_loading or not self.current_project_id: return
        self.data_manager.save_antgen_field_statuses(self.current_project_id, self.form.get_statuses())

    def _check_global_status(self):
        """Si todos los campos están verdes, sugiere pasar a 'verificado'."""
        if self.is_loading: return
        suggested = self.form.get_global_status_suggestion()
        if self.status_bar.get_status() != suggested:
            self.status_bar.set_status(suggested)

    # --- SLOTS ASYNC ---

    @pyqtSlot()
    def _on_extraction_started(self):
        self.btn_fetch.setEnabled(False)
        self.pbar.setVisible(True)
        self.lbl_placeholder.setVisible(False)

    @pyqtSlot(bool, dict)
    def _on_extraction_finished(self, success, data):
        self.pbar.setVisible(False)
        self.btn_fetch.setEnabled(True)
        if success:
            self.status_bar.set_status("edicion")
            self.form.setVisible(True)
            self.form.set_data(data, {})  # Datos nuevos, status vacíos
            self.btn_fetch.setText("Volver a Extraer")

            # Avanzar a paso 1
            self.timeline.set_current_step(1, "edicion")
            self.data_manager.update_step_status(
                self.current_project_id, "ANTGEN", step_index=1, step_status="edicion"
            )
        else:
            self.status_bar.set_status("error")
            self.form.setVisible(False)
            self.lbl_placeholder.setVisible(True)
            QMessageBox.critical(self, "Error", "Fallo en extracción")

    @pyqtSlot()
    def _on_compilation_started(self):
        self.btn_compile.setEnabled(False)
        self.btn_compile.setText("Compilando...")

    @pyqtSlot(bool, str)
    def _on_compilation_finished(self, success, path):
        self.btn_compile.setEnabled(True)
        self.btn_compile.setText("Compilar en PDF")
        if success:
            QMessageBox.information(self, "Listo", f"PDF guardado en:\n{path}")
            # Avanzar a paso 2
            self.timeline.set_current_step(2, "verificado")
            self.status_bar.set_status("verificado")
            self.data_manager.update_step_status(
                self.current_project_id, "ANTGEN",
                step_index=2, step_status="verificado", global_status="verificado"
            )
        else:
            QMessageBox.critical(self, "Error", "Fallo al compilar")