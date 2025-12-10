import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout, QPushButton, QMessageBox, \
    QProgressBar, QFrame, QLineEdit, \
    QPlainTextEdit, QSizePolicy, QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.controllers.fetch_antgen import FetchAntgenController
from src.views.components.field_row import FieldRow


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

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # 1. HEADER INTEGRADO
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

        # 2. COMMAND BAR
        self.command_bar = CommandBar()
        self.command_bar.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_fetch = self.command_bar.add_button("Extraer Información", object_name="BtnActionPrimary")
        self.btn_fetch.clicked.connect(self._on_fetch_clicked)
        # Barra de Progreso
        self.progress_bar = QProgressBar(self.command_bar)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        self.command_bar.button_layout.addWidget(self.progress_bar)

        # --- CORRECCIÓN: Agregamos el CommandBar al Layout principal SOLO UNA VEZ ---
        layout.addWidget(self.command_bar)

        # 3. CONTENIDO (Área de Trabajo Principal)
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

        # --- DEFINICIÓN DE LOS CAMPOS EDITABLES ---
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

    def _on_fetch_clicked(self):
        """Maneja el clic en el botón Extraer Información."""
        if not self.current_project_id:
            self.log_requested.emit("⚠️ No hay ID de proyecto activo.")
            return

        # 1. Cambiar estado global a Edición (indica que estamos trabajando)
        self.status_bar.set_status("edicion")

        # 2. Iniciar la extracción en el controlador
        self.log_requested.emit(
            f"▶️ Iniciando extracción de Antecedentes Generales para ID {self.current_project_id}...")
        self.fetch_controller.start_extraction(self.current_project_id)

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
            self.log_requested.emit(f"✅ Extracción exitosa. Expediente listo para Descargar.")

            self._display_extracted_data(antgen_data)
            self.fields_container.setVisible(True)
            self.placeholder_label.setVisible(False)
            self.btn_fetch.setText("Volver a Extraer")
            self.btn_fetch.setEnabled(True)

        else:
            self.status_bar.set_status("error")
            QMessageBox.critical(self, "Error de Extracción",
                                 "No se pudo completar la extracción. Revise el Log para detalles.")

            self.placeholder_label.setVisible(True)
            self.fields_container.setVisible(False)
            self.btn_fetch.setText("Volver a Extraer")
            self.btn_fetch.setEnabled(True)
            if self.fields_container.isVisible():
                self.btn_fetch.setText("Volver a Extraer")
            else:
                self.btn_fetch.setText("Extraer Información")

    def _display_extracted_data(self, antgen_data: dict, field_statuses: dict | None = None):
        ant = antgen_data.get("ANTGEN") if isinstance(antgen_data, dict) else None
        if not isinstance(ant, dict):
            ant = antgen_data if isinstance(antgen_data, dict) else {}

        field_statuses = field_statuses or {}
        for key, field_row in self.field_map.items():
            value = ant.get(key, "")

            if isinstance(value, dict):
                lines = []
                if value.get("nombre"):
                    lines.append(f"Nombre: {value['nombre']}")
                if value.get("domicilio"):
                    lines.append(f"Domicilio: {value['domicilio']}")
                if value.get("email"):
                    lines.append(f"Correo: {value['email']}")
                value = "\n".join(lines)

            if isinstance(field_row.editor, QPlainTextEdit):
                field_row.editor.setPlainText(str(value))
            elif isinstance(field_row.editor, QTextEdit):
                text_value = str(value)
                if "<" in text_value and ">" in text_value:
                    field_row.editor.setHtml(text_value)
                else:
                    field_row.editor.setPlainText(text_value)
            elif isinstance(field_row.editor, QLineEdit):
                field_row.editor.setText(str(value))

            status_value = self._normalize_field_status(field_statuses.get(key)) or "detectado"
            field_row.status_bar.set_status(status_value)

        # Aquí sí llamas al método de la clase
        self._update_global_status_from_fields()

    def _normalize_field_status(self, status: str | None) -> str:
        status_value = (status or "").strip().lower()
        # Normalizar "validado" a "verificado"
        return "verificado" if status_value == "validado" else status_value

    @pyqtSlot(str)
    def _on_field_status_changed(self, _status: str):
        """Se llama cada vez que cambia el estado de un FieldRow."""
        self._update_global_status_from_fields()
        self._persist_field_statuses()

    def _update_global_status_from_fields(self):
        """Recalcula el estado global de ANTGEN a partir de los campos individuales."""
        statuses = [
            self._normalize_field_status(row.status_bar.get_status())
            for row in self.field_map.values()
        ]

        all_validated = statuses and all(status == "verificado" for status in statuses)
        target_status = "verificado" if all_validated else "edicion"

        if self.status_bar.get_status() != target_status:
            self.status_bar.set_status(target_status)
    def load_project(self, project_id):
        """Carga el estado inicial y los datos extraídos (si existen) al abrir la página."""
        self.current_project_id = project_id
        self.is_loading = True

        self.header.title_label.setText(f"Antecedentes Generales - ID {project_id}")

        data_exists = False
        status = "detectado"
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
                antgen_data = antgen_section.get("ANTGEN_DATA", {})
                field_statuses = antgen_section.get("field_statuses", {})

                if antgen_data:
                    data_exists = True
                    # Cargar la data mapeada
                    self._display_extracted_data(antgen_data, field_statuses)

        except Exception as e:
            self.log_requested.emit(f"⚠️ Error leyendo estado inicial: {e}")

        finally:
            # Control de visibilidad
            self.fields_container.setVisible(data_exists)
            self.placeholder_label.setVisible(not data_exists)

            # Sincronización de estado
            self.status_bar.set_status(status)

            # Control del botón: Deshabilitar si ya existen datos
            self.btn_fetch.setText("Volver a Extraer" if data_exists else "Extraer Información")
            self.btn_fetch.setEnabled(True)
            self.is_loading = False

    def save_status_change(self, new_status):
        """Guarda el estado global de ANTGEN (se ejecuta al presionar botones de Status Bar)."""
        if self.is_loading or not self.current_project_id:
            return

        project_id = self.current_project_id
        self.log_requested.emit(f"🔄 Cambiando estado de ANTGEN a: {new_status.upper()}")

        try:
            base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
            json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if "ANTGEN" in data.get("expedientes", {}):
                    data["expedientes"]["ANTGEN"]["status"] = new_status

                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)

                    self.log_requested.emit(f"✅ Estado guardado correctamente.")
        except Exception as e:
            self.log_requested.emit(f"❌ Error al guardar estado: {e}")

    def _persist_field_statuses(self):
        """Guarda los estados individuales de cada campo en el JSON del proyecto."""
        if self.is_loading or not self.current_project_id:
            return

        project_id = self.current_project_id
        statuses_payload = {
            key: self._normalize_field_status(row.status_bar.get_status()) or "detectado"
            for key, row in self.field_map.items()
        }

        try:
            base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
            json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

            if not os.path.exists(json_path):
                self.log_requested.emit(
                    "⚠️ No se encontró el archivo de configuración para guardar estados de campos.")
                return

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            antgen_section = data.get("expedientes", {}).get("ANTGEN")
            if antgen_section is None:
                self.log_requested.emit("⚠️ No existe la sección ANTGEN en el archivo de configuración.")
                return

            antgen_section["field_statuses"] = statuses_payload

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            self.log_requested.emit("✅ Estados de campos guardados correctamente.")
        except Exception as e:
            self.log_requested.emit(f"❌ Error al guardar estados de campos: {e}")