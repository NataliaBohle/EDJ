import os
import json
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout, QPushButton, QMessageBox, \
    QProgressBar, QFrame, QLineEdit, QPlainTextEdit, QSizePolicy, QTextEdit
from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.controllers.fetch_antgen import FetchAntgenController
from src.controllers.antgen_comp import AntgenCompiler
from src.views.components.field_row import FieldRow
from src.views.components.results_table import EditableTableCard
# 1. IMPORTAR EL TIMELINE
from src.views.components.timeline import Timeline


class AntGenPage(QWidget):
    log_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("AntGenPage")
        self.current_project_id = None
        self.is_loading = False

        # Instanciar el controlador de extracción
        self.fetch_controller = FetchAntgenController(self)
        self.fetch_controller.log_requested.connect(self.log_requested.emit)
        self.fetch_controller.extraction_started.connect(self._on_extraction_started)
        self.fetch_controller.extraction_finished.connect(self._on_extraction_finished)

        # Controlador de compilación
        self.compiler = AntgenCompiler(self)
        self.compiler.log_requested.connect(self.log_requested.emit)
        self.compiler.compilation_started.connect(self._on_compilation_started)
        self.compiler.compilation_finished.connect(self._on_compilation_finished)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # --- HEADER ---
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(40, 30, 40, 10)

        self.header = Chapter("Antecedentes Generales")
        chapter_layout = self.header.layout()

        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 5, 0, 0)
        status_layout.setSpacing(15)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        lbl_status = QLabel("Estado:")
        lbl_status.setStyleSheet("color: #555; font-weight: bold; font-size: 13px;")
        status_layout.addWidget(lbl_status)

        self.status_bar = StatusBar()
        self.status_bar.status_changed.connect(self.save_status_change)

        status_layout.addWidget(self.status_bar)
        chapter_layout.addWidget(status_widget)

        header_layout.addWidget(self.header)
        layout.addWidget(header_container)

        # --- 2. NUEVO: TIMELINE SUPERIOR ---
        # Definimos los pasos específicos para ANTGEN
        self.steps_antgen = ["Detectado", "Descargar", "Compilar"]

        # Creamos contenedor para darle márgenes
        timeline_container = QWidget()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(40, 0, 40, 10)

        self.timeline = Timeline(steps=self.steps_antgen, current_step=0)
        timeline_layout.addWidget(self.timeline)

        layout.addWidget(timeline_container)

        # --- COMMAND BAR ---
        self.command_bar = CommandBar()
        self.command_bar.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_fetch = self.command_bar.add_button("Extraer Información", object_name="BtnActionPrimary")
        self.btn_compile_pdf = self.command_bar.add_button("Compilar en PDF", object_name="BtnActionSuccess")
        self.btn_open_folder = self.command_bar.add_button("Ver Carpeta de Archivos", object_name="BtnActionFolder")
        self.btn_fetch.clicked.connect(self._on_fetch_clicked)
        self.btn_compile_pdf.clicked.connect(self._on_compile_clicked)
        self.btn_open_folder.clicked.connect(self._on_open_folder_clicked)

        self.progress_bar = QProgressBar(self.command_bar)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        self.command_bar.button_layout.addWidget(self.progress_bar)

        layout.addWidget(self.command_bar)

        # --- CONTENIDO ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("PageScroll")
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("PageContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 30, 40, 30)
        self.content_layout.setSpacing(15)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ... (Resto de la inicialización de campos: self.fields_container, self.field_map, Tablas, etc.) ...
        # (MANTENER EL CÓDIGO ORIGINAL DE CREACIÓN DE CAMPOS Y TABLAS AQUÍ)

        # --- DEFINICIÓN DE LOS CAMPOS EDITABLES (RESUMIDO PARA CONTEXTO) ---
        self.fields_container = QFrame()
        self.fields_container.setObjectName("DataCardFrame")
        self.fields_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        fields_layout = QVBoxLayout(self.fields_container)
        fields_layout.setContentsMargins(30, 20, 30, 20)
        fields_layout.setSpacing(10)

        # Mapeo de campos a instancias (usando FieldRow)
        self.row_nombre = FieldRow("Nombre del proyecto", is_multiline=False)
        self.row_forma = FieldRow("Forma de presentación", is_multiline=False)
        self.row_tipo = FieldRow("Tipo de proyecto", is_multiline=False)
        self.row_monto = FieldRow("Monto de inversión", is_multiline=False)
        self.row_estado = FieldRow("Estado actual", is_multiline=False)
        self.row_encargado = FieldRow("Encargado/a", is_multiline=False)
        self.row_descripcion = FieldRow("Descripción", is_multiline=True, rich_editor=True)
        self.row_objetivo = FieldRow("Objetivo del proyecto", is_multiline=True, rich_editor=True)
        self.row_titular = FieldRow("Titular", is_multiline=True)
        self.row_representante = FieldRow("Representante legal", is_multiline=True)
        self.row_consultora = FieldRow("Consultora ambiental", is_multiline=True)

        self.field_map = {
            "nombre_proyecto": self.row_nombre,
            "forma_presentacion": self.row_forma,
            "tipo_proyecto": self.row_tipo,
            "monto_inversion": self.row_monto,
            "estado_actual": self.row_estado,
            "encargado": self.row_encargado,
            "descripcion_proyecto": self.row_descripcion,
            "objetivo_proyecto": self.row_objetivo,
            "titular": self.row_titular,
            "representante_legal": self.row_representante,
            "consultora": self.row_consultora,
        }
        for field_row in self.field_map.values():
            field_row.status_changed.connect(self._on_field_status_changed)
            field_row.content_changed.connect(self._on_field_content_changed)

        # Añadir a la tarjeta
        fields_layout.addWidget(QLabel("<b>DATOS PRINCIPALES</b>"))
        fields_layout.addWidget(self.row_nombre)
        fields_layout.addWidget(self.row_forma)
        fields_layout.addWidget(self.row_tipo)
        fields_layout.addWidget(self.row_monto)
        fields_layout.addWidget(self.row_estado)
        fields_layout.addWidget(self.row_encargado)
        fields_layout.addWidget(self.row_descripcion)
        fields_layout.addWidget(self.row_objetivo)

        fields_layout.addWidget(QLabel("<b>DATOS DE CONTACTO</b>"))
        fields_layout.addWidget(self.row_titular)
        fields_layout.addWidget(self.row_representante)
        fields_layout.addWidget(self.row_consultora)

        # Tablas editables para PAS y Estados
        self.table_pas = EditableTableCard(
            "Permisos Ambientales Sectoriales (PAS)",
            columns=[
                ("articulo", "Artículo"),
                ("nombre", "Nombre"),
                ("tipo", "Tipo"),
                ("certificado", "Certificado"),
            ],
        )
        self.table_pas.status_changed.connect(self._on_table_status_changed)
        self.table_pas.data_changed.connect(self._on_table_content_changed)

        self.table_estados = EditableTableCard(
            "Registro de Estados",
            columns=[
                ("estado", "Estado"),
                ("documento", "Documento"),
                ("numero", "Número"),
                ("fecha", "Fecha"),
                ("autor", "Autor"),
            ],
        )
        self.table_estados.status_changed.connect(self._on_table_status_changed)
        self.table_estados.data_changed.connect(self._on_table_content_changed)

        fields_layout.addWidget(self.table_pas)
        fields_layout.addWidget(self.table_estados)

        # PLACEHOLDER para cuando no hay datos
        self.placeholder_label = QLabel("Pulse 'Extraer Información' para iniciar la búsqueda en el SEIA.")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.placeholder_label)

        # Añadir la tarjeta de campos (Visibilidad controlada en load_project)
        self.content_layout.addWidget(self.fields_container)
        self.content_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        # Inicialmente, el contenedor de campos debe estar oculto
        self.fields_container.setVisible(False)

    # ... (MANTENER MÉTODOS EXISTENTES: _on_fetch_clicked, _on_compile_clicked, _on_extraction_started, etc.)

    def _on_fetch_clicked(self):
        if not self.current_project_id:
            self.log_requested.emit("⚠️ No hay ID de proyecto activo.")
            return
        self.status_bar.set_status("edicion")
        self.log_requested.emit(f"▶️ Iniciando extracción para ID {self.current_project_id}...")
        self.fetch_controller.start_extraction(self.current_project_id)

    def _on_compile_clicked(self):
        if not self.current_project_id:
            self.log_requested.emit("⚠️ No hay ID de proyecto activo.")
            return
        antgen_payload = self._collect_current_data()
        self.log_requested.emit("📝 Compilando Antecedentes Generales en PDF...")
        self.compiler.compile_pdf(self.current_project_id, antgen_payload)

    def _on_open_folder_clicked(self):
        """Abre la carpeta del proyecto actual en el explorador de archivos."""
        if not self.current_project_id:
            self.log_requested.emit("⚠️ No hay un proyecto activo para abrir su carpeta.")
            return

        # Ruta: /Ebook/{ID}
        folder_path = os.path.join(os.getcwd(), "Ebook", self.current_project_id)

        if os.path.exists(folder_path):
            self.log_requested.emit(f"📂 Abriendo carpeta: {folder_path}")
            # QUrl.fromLocalFile maneja correctamente las rutas con espacios o caracteres especiales
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        else:
            self.log_requested.emit(f"⚠️ La carpeta no existe aún: {folder_path}")

    @pyqtSlot()
    def _on_extraction_started(self):
        self.btn_fetch.setEnabled(False)
        self.btn_fetch.setText("Extrayendo...")
        self.progress_bar.setVisible(True)
        self.placeholder_label.setVisible(False)

    @pyqtSlot(bool, dict)
    def _on_extraction_finished(self, success: bool, antgen_data: dict):
        self.progress_bar.setVisible(False)
        if success:
            self.status_bar.set_status("edicion")
            self.log_requested.emit(f"✅ Extracción exitosa.")
            self._display_extracted_data(antgen_data)
            self.fields_container.setVisible(True)
            self.placeholder_label.setVisible(False)
            self.btn_fetch.setText("Volver a Extraer")
            self.btn_fetch.setEnabled(True)

            # NUEVO: Al extraer, avanzamos al paso 1 (Descargar/Edición)
            self.timeline.set_current_step(1, "edicion")
            self._update_step_in_json(1, "edicion")

        else:
            self.status_bar.set_status("error")
            QMessageBox.critical(self, "Error", "No se pudo completar la extracción.")
            self.placeholder_label.setVisible(True)
            self.fields_container.setVisible(False)
            self.btn_fetch.setText("Volver a Extraer")
            self.btn_fetch.setEnabled(True)

    @pyqtSlot()
    def _on_compilation_started(self):
        self.btn_compile_pdf.setEnabled(False)
        self.btn_compile_pdf.setText("Compilando...")

    @pyqtSlot(bool, str)
    def _on_compilation_finished(self, success: bool, output_path: str):
        self.btn_compile_pdf.setEnabled(True)
        self.btn_compile_pdf.setText("Compilar en PDF")

        if success:
            QMessageBox.information(self, "Compilación completa", f"PDF generado:\n{output_path}")

            # --- 3. LOGICA DE AVANCE AUTOMÁTICO ---
            self.log_requested.emit("✅ Proceso de ANTGEN finalizado.")

            # A) Actualizamos Timeline Local (Paso 2 = Compilar, Verificado)
            self.timeline.set_current_step(2, "verificado")

            # B) Actualizamos Status Global Local
            self.status_bar.set_status("verificado")

            # C) Guardamos en JSON para que el ProjectView se entere
            self._update_step_in_json(2, "verificado", global_status="verificado")

        else:
            QMessageBox.critical(self, "Error", "Fallo al generar PDF.")

    def load_project(self, project_id):
        """Carga el estado inicial y los datos extraídos (si existen) al abrir la página."""
        self.current_project_id = project_id
        self.is_loading = True

        self.header.title_label.setText(f"Antecedentes Generales - ID {project_id}")

        data_exists = False
        status = "detectado"

        # Variables para el timeline
        step_index = 0
        step_status = "detectado"

        antgen_data = {}
        field_statuses = {}

        try:
            base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
            json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                antgen_section = data.get("expedientes", {}).get("ANTGEN", {})
                status = antgen_section.get("status", "detectado")

                # Leer estado del paso
                step_index = antgen_section.get("step_index", 0)
                step_status = antgen_section.get("step_status", "detectado")

                antgen_data = antgen_section.get("ANTGEN_DATA", {})
                field_statuses = antgen_section.get("field_statuses", {})

                if antgen_data:
                    data_exists = True
                    self._display_extracted_data(antgen_data, field_statuses)

        except Exception as e:
            self.log_requested.emit(f"⚠️ Error leyendo estado inicial: {e}")

        finally:
            self.fields_container.setVisible(data_exists)
            self.placeholder_label.setVisible(not data_exists)
            self.status_bar.set_status(status)

            # --- 4. ACTUALIZAR TIMELINE LOCAL ---
            self.timeline.set_current_step(step_index, step_status)

            self.btn_fetch.setText("Volver a Extraer" if data_exists else "Extraer Información")
            self.btn_fetch.setEnabled(True)
            self.is_loading = False

    # ... (Resto de métodos auxiliares: _display_extracted_data, save_status_change, etc. MANTENER IGUAL) ...
    # Agrego métodos faltantes en este resumen para que no se pierdan al copiar/pegar

    def _display_extracted_data(self, antgen_data: dict, field_statuses: dict | None = None):
        ant = antgen_data.get("ANTGEN") if isinstance(antgen_data, dict) else None
        if not isinstance(ant, dict):
            ant = antgen_data if isinstance(antgen_data, dict) else {}

        field_statuses = field_statuses or {}
        for key, field_row in self.field_map.items():
            value = ant.get(key, "")
            if isinstance(value, dict):
                lines = []
                if value.get("nombre"): lines.append(f"Nombre: {value['nombre']}")
                if value.get("domicilio"): lines.append(f"Domicilio: {value['domicilio']}")
                if value.get("email"): lines.append(f"Correo: {value['email']}")
                value = "\n".join(lines)

            if isinstance(field_row.editor, QPlainTextEdit):
                field_row.editor.setPlainText(str(value))
                field_row._update_editor_height()
            elif isinstance(field_row.editor, QTextEdit):
                field_row.editor.setHtml(str(value)) if "<" in str(value) else field_row.editor.setPlainText(str(value))
                field_row._update_editor_height()
            elif isinstance(field_row.editor, QLineEdit):
                field_row.editor.setText(str(value))

            status_value = self._normalize_field_status(field_statuses.get(key)) or "detectado"
            field_row.status_bar.set_status(status_value)

        self.table_pas.set_data(ant.get("permisos_ambientales", []))
        self.table_pas.set_status(
            self._normalize_field_status(field_statuses.get("permisos_ambientales")) or "detectado")
        self.table_estados.set_data(ant.get("registro_estados", []))
        self.table_estados.set_status(
            self._normalize_field_status(field_statuses.get("registro_estados")) or "detectado")
        self._update_global_status_from_fields()

    def _normalize_field_status(self, status: str | None) -> str:
        status_value = (status or "").strip().lower()
        return "verificado" if status_value == "validado" else status_value

    @pyqtSlot(str)
    def _on_field_status_changed(self, _status: str):
        self._update_global_status_from_fields()
        self._persist_field_statuses()

    def _on_field_content_changed(self):
        self._persist_field_values()

    def _on_table_status_changed(self, _status: str):
        self._update_global_status_from_fields()
        self._persist_field_statuses()

    def _on_table_content_changed(self):
        self._persist_field_values()

    def _collect_current_data(self) -> dict:
        payload = {key: row.get_value() for key, row in self.field_map.items()}
        payload["permisos_ambientales"] = self.table_pas.get_data()
        payload["registro_estados"] = self.table_estados.get_data()
        return payload

    def _update_global_status_from_fields(self):
        statuses = [self._normalize_field_status(row.status_bar.get_status()) for row in self.field_map.values()]
        statuses.extend([
            self._normalize_field_status(self.table_pas.get_status()),
            self._normalize_field_status(self.table_estados.get_status()),
        ])
        all_validated = statuses and all(status == "verificado" for status in statuses)
        target_status = "verificado" if all_validated else "edicion"
        if self.status_bar.get_status() != target_status:
            self.status_bar.set_status(target_status)

    def save_status_change(self, new_status):
        """
        Maneja el cambio manual en la Status Bar.
        Sincroniza el estado global con el estado visual del paso actual en el Timeline.
        """
        # 1. Obtener en qué paso está el timeline actualmente (0, 1 o 2)
        current_step_index = self.timeline.current_step

        # 2. Actualizar visualmente el Timeline con el nuevo color/estado
        # Esto hace que el punto (y la línea anterior) cambien a Amarillo/Verde/Rojo
        self.timeline.set_current_step(current_step_index, new_status)

        # 3. Guardar todo en el JSON
        # Actualizamos tanto el 'status' global como el 'step_status' del paso actual
        self._update_step_in_json(
            step_index=current_step_index,
            step_status=new_status,
            global_status=new_status,
            status_global_only=False
        )

    def _persist_field_statuses(self):
        # (Este método ya existe en tu código, mantener igual)
        if self.is_loading or not self.current_project_id: return
        # ... lógica de guardado de field_statuses ...
        # Para abreviar en la respuesta, asumo que mantienes tu lógica original aquí
        pass

    def _persist_field_values(self):
        # (Este método ya existe en tu código, mantener igual)
        if self.is_loading or not self.current_project_id: return
        pass

    # --- 5. MÉTODO AUXILIAR PARA GUARDAR PROGRESO (STEP) ---
    def _update_step_in_json(self, step_index=None, step_status=None, global_status=None, status_global_only=False):
        """Actualiza el progreso del expediente en el JSON."""
        if self.is_loading or not self.current_project_id:
            return

        project_id = self.current_project_id
        try:
            base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
            json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if "ANTGEN" in data.get("expedientes", {}):
                    # Actualizar status global si se pide
                    if global_status:
                        data["expedientes"]["ANTGEN"]["status"] = global_status

                    # Actualizar paso si no es solo cambio de status manual
                    if not status_global_only and step_index is not None:
                        data["expedientes"]["ANTGEN"]["step_index"] = step_index
                        data["expedientes"]["ANTGEN"]["step_status"] = step_status or "detectado"

                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)

                    if not status_global_only:
                        self.log_requested.emit(f"💾 Progreso guardado: Paso {step_index} ({step_status})")

        except Exception as e:
            self.log_requested.emit(f"❌ Error al guardar progreso: {e}")