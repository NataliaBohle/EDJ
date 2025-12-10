from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout,
    QPushButton, QMessageBox, QProgressBar, QFrame, QLineEdit,
    QPlainTextEdit, QSizePolicy, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt

from src.views.components.field_row import FieldRow
from src.views.components.results_table import EditableTableCard


class AntGenForm(QWidget):
    data_changed = pyqtSignal()
    status_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        # Contenedor visual (la tarjeta gris)
        self.card_frame = QFrame()
        self.card_frame.setObjectName("DataCardFrame")
        self.card_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.card_layout = QVBoxLayout(self.card_frame)
        self.card_layout.setContentsMargins(30, 20, 30, 20)
        self.card_layout.setSpacing(10)

        # 1. Inicializar Campos
        self._init_fields()

        # 2. Inicializar Tablas
        self._init_tables()

        self.layout.addWidget(self.card_frame)

    def _init_fields(self):
        """Crea y mapea todos los campos de texto."""
        # Definición de campos
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

        # Diccionario
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

        # Layout y Conexiones
        self.card_layout.addWidget(QLabel("<b>DATOS PRINCIPALES</b>"))
        for key, row in self.field_map.items():
            # Agregamos separador visual antes de los contactos
            if key == "titular":
                self.card_layout.addWidget(QLabel("<b>DATOS DE CONTACTO</b>"))

            self.card_layout.addWidget(row)

            # Conectar señales internas a las señales públicas del formulario
            row.content_changed.connect(self.data_changed.emit)
            row.status_changed.connect(self.status_changed.emit)

    def _init_tables(self):
        """Crea las tablas PAS y Estados."""
        self.table_pas = EditableTableCard(
            "Permisos Ambientales Sectoriales (PAS)",
            columns=[("articulo", "Artículo"), ("nombre", "Nombre"), ("tipo", "Tipo"), ("certificado", "Certificado")]
        )
        self.table_estados = EditableTableCard(
            "Registro de Estados",
            columns=[("estado", "Estado"), ("documento", "Documento"), ("numero", "Número"), ("fecha", "Fecha"),
                     ("autor", "Autor")]
        )

        # Conexiones
        for table in [self.table_pas, self.table_estados]:
            self.card_layout.addWidget(table)
            table.data_changed.connect(self.data_changed.emit)
            table.status_changed.connect(self.status_changed.emit)

    # --- API PÚBLICA ---

    def set_data(self, data: dict, statuses: dict):
        """Rellena todo el formulario con los datos y estados proporcionados."""
        if not data: return

        # 1. Campos Simples
        for key, row in self.field_map.items():
            value = data.get(key, "")

            # Lógica de formateo visual específica de ANTGEN
            if isinstance(value, dict):
                lines = []
                if value.get("nombre"): lines.append(f"Nombre: {value['nombre']}")
                if value.get("domicilio"): lines.append(f"Domicilio: {value['domicilio']}")
                if value.get("email"): lines.append(f"Correo: {value['email']}")
                value = "\n".join(lines)

            # Setear valor en el editor correspondiente
            if isinstance(row.editor, (QPlainTextEdit, QTextEdit)):
                if isinstance(row.editor, QTextEdit) and ("<" in str(value) and ">" in str(value)):
                    row.editor.setHtml(str(value))
                else:
                    row.editor.setPlainText(str(value))
                row._update_editor_height()  # Método interno de FieldRow
            elif isinstance(row.editor, QLineEdit):
                row.editor.setText(str(value))

            # Setear estado
            st_val = self._normalize_status(statuses.get(key))
            row.status_bar.set_status(st_val)

        # 2. Tablas
        self.table_pas.set_data(data.get("permisos_ambientales", []))
        self.table_pas.set_status(self._normalize_status(statuses.get("permisos_ambientales")))

        self.table_estados.set_data(data.get("registro_estados", []))
        self.table_estados.set_status(self._normalize_status(statuses.get("registro_estados")))

    def get_data(self) -> dict:
        """Devuelve el diccionario completo de datos del formulario."""
        payload = {key: row.get_value() for key, row in self.field_map.items()}
        payload["permisos_ambientales"] = self.table_pas.get_data()
        payload["registro_estados"] = self.table_estados.get_data()
        return payload

    def get_statuses(self) -> dict:
        """Devuelve el diccionario de estados de validación."""
        statuses = {
            key: self._normalize_status(row.status_bar.get_status())
            for key, row in self.field_map.items()
        }
        statuses["permisos_ambientales"] = self._normalize_status(self.table_pas.get_status())
        statuses["registro_estados"] = self._normalize_status(self.table_estados.get_status())
        return statuses

    def get_global_status_suggestion(self) -> str:
        """Calcula si el estado global debería ser 'verificado' o 'edicion'."""
        all_statuses = list(self.get_statuses().values())
        if all_statuses and all(s == "verificado" for s in all_statuses):
            return "verificado"
        return "edicion"

    def _normalize_status(self, status: str | None) -> str:
        s = (status or "").strip().lower()
        return "verificado" if s == "validado" else (s or "detectado")