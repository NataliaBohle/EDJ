import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar


class AntGenPage(QWidget):
    # Nueva señal para enviar mensajes al LogScreen de la ventana principal
    log_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("AntGenPage")
        self.current_project_id = None
        # Bandera para evitar guardar mientras cargamos los datos iniciales
        self.is_loading = False

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
        # --- CONEXIÓN CLAVE: Cuando cambie el estado, guardamos ---
        self.status_bar.status_changed.connect(self.save_status_change)

        status_layout.addWidget(self.status_bar)
        chapter_layout.addWidget(status_widget)

        header_layout.addWidget(self.header)
        layout.addWidget(header_container)

        # 2. COMMAND BAR
        self.command_bar = CommandBar()
        self.command_bar.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_fetch = self.command_bar.add_button("Extraer Información", object_name="BtnActionPrimary")
        layout.addWidget(self.command_bar)

        # 3. CONTENIDO
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("PageScroll")
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("PageContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 30, 40, 30)
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

    def load_project(self, project_id):
        """Carga el proyecto y sincroniza el estado de los botones."""
        self.current_project_id = project_id
        self.is_loading = True  # Bloqueamos guardado automático

        self.header.title_label.setText(f"Antecedentes Generales - ID {project_id}")

        # Leer JSON para setear el estado correcto
        try:
            base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
            json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Buscamos el estado de ANTGEN
                # Nota: Asumimos que ANTGEN siempre existe si el fetch corrió
                status = data.get("expedientes", {}).get("ANTGEN", {}).get("status", "detectado")

                # Actualizamos los botones visualmente
                self.status_bar.set_status(status)

        except Exception as e:
            self.log_requested.emit(f"⚠️ Error leyendo estado inicial: {e}")
        finally:
            self.is_loading = False  # Liberamos el bloqueo

    def save_status_change(self, new_status):
        """Se ejecuta automáticamente al presionar un botón de estado."""
        if self.is_loading or not self.current_project_id:
            return

        project_id = self.current_project_id

        # 1. Mensaje al Log
        self.log_requested.emit(f"🔄 Cambiando estado de ANTGEN a: {new_status.upper()}")

        # 2. Guardar en JSON
        try:
            base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
            json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Actualizar el valor
                if "ANTGEN" in data.get("expedientes", {}):
                    data["expedientes"]["ANTGEN"]["status"] = new_status

                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)

                    self.log_requested.emit(f"✅ Estado guardado correctamente.")
                else:
                    self.log_requested.emit(f"⚠️ No se encontró ANTGEN en el archivo de configuración.")

        except Exception as e:
            self.log_requested.emit(f"❌ Error al guardar estado: {e}")