import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
# --- CORRECCIÓN AQUÍ: Agregamos pyqtSignal ---
from PyQt6.QtCore import Qt, pyqtSignal
from src.views.components.chapter import Chapter
from src.views.components.expediente_card import ExpedienteCard


class ProjectView(QWidget):
    # Ahora sí funcionará esta señal
    action_requested = pyqtSignal(str, str, int)

    def __init__(self):
        super().__init__()
        self.setObjectName("ProjectViewPage")

        self.project_id_actual = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # 1. Cabecera
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(40, 40, 40, 20)
        self.header = Chapter("Vista de Proyecto")
        header_layout.addWidget(self.header)
        layout.addWidget(header_container)

        # 2. Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("ProjectScroll")

        self.container = QWidget()
        self.container.setObjectName("ProjectContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(40, 0, 40, 40)
        self.container_layout.setSpacing(20)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

    def load_project(self, project_id):
        self.project_id_actual = project_id
        self.header.title_label.setText(f"Expediente ID: {project_id}")

        # Limpiar
        while self.container_layout.count():
            w = self.container_layout.takeAt(0).widget()
            if w: w.deleteLater()

        # Ruta JSON
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

        if not os.path.exists(json_path):
            self.container_layout.addWidget(QLabel("Error: Archivo de configuración no encontrado."))
            return

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            expedientes = data.get("expedientes", {})
            if not expedientes:
                self.container_layout.addWidget(QLabel("Este proyecto no tiene expedientes detectados."))
                return

            # Definición de pasos
            STEPS_DEFAULT = ["Detectado", "Descargar", "Convertir", "Formatear", "Índice", "Compilar"]
            STEPS_SHORT = ["Detectado", "Descargar", "Compilar"]

            # --- TU BLOQUE FOR CORREGIDO ---
            for code, info in expedientes.items():
                if info.get("status") == "detectado":
                    titulo = info.get("titulo", code)

                    # 1. Definimos variables
                    saved_step = info.get("step_index", 0)
                    saved_step_status = info.get("step_status", "detectado")

                    # 2. Elegimos pasos
                    if code == "ANTGEN":
                        mis_pasos = STEPS_SHORT
                    else:
                        mis_pasos = STEPS_DEFAULT

                    # 3. Creamos tarjeta
                    card = ExpedienteCard(title=titulo, code=code, status="detectado", steps=mis_pasos)

                    # 4. Actualizamos estado visual
                    card.update_progress(saved_step, saved_step_status)

                    # 5. Conexiones
                    # Guardar progreso al hacer clic en la línea
                    card.step_selected.connect(lambda c, s, pid=project_id: self.save_step_change(pid, c, s))

                    # Activar herramienta (Botón)
                    card.action_clicked.connect(
                        lambda c, s, cod=code: self.action_requested.emit(self.project_id_actual, cod, s)
                    )

                    self.container_layout.addWidget(card)
            # -------------------------------

        except Exception as e:
            self.container_layout.addWidget(QLabel(f"Error cargando datos: {e}"))

    def save_step_change(self, project_id, code, new_step):
        print(f"Guardando progreso: {project_id} -> {code} -> Paso {new_step}")
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if code in data["expedientes"]:
                data["expedientes"][code]["step_index"] = new_step
                data["expedientes"][code]["step_status"] = "detectado"

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando progreso: {e}")