import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from src.views.components.chapter import Chapter
from src.views.components.expediente_card import ExpedienteCard
from src.utils.expediente_config import steps_for_expediente


class ProjectView(QWidget):
    action_requested = pyqtSignal(str, str, int, dict)
    log_requested = pyqtSignal(str)

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

            for code, info in expedientes.items():
                titulo = info.get("titulo", code)
                saved_step = info.get("step_index", 0)
                saved_step_status = info.get("step_status", "detectado")
                saved_global_status = info.get("status", "detectado")
                mis_pasos = steps_for_expediente(code, info)
                # 3. Creamos tarjeta (pasamos el status global)
                card = ExpedienteCard(title=titulo, code=code, status=saved_global_status, steps=mis_pasos)
                # 4. Actualizamos estado visual del paso
                card.update_progress(saved_step, saved_global_status)

                # 5. Conexiones
                # Guardar progreso al hacer clic en la línea
                card.step_selected.connect(lambda c, s, pid=project_id: self.save_step_change(pid, c, s))

                # --- NUEVA CONEXIÓN CLAVE: MiniStatusBar (Desplegable) ---
                card.status_updated.connect(lambda c, s, pid=project_id: self.save_overall_status_change(pid, c, s))

                # Activar herramienta (Botón)
                card.action_clicked.connect(
                    lambda c, s, exp_info=info, cod=code: self.action_requested.emit(
                        self.project_id_actual,
                        cod,
                        s,
                        self._build_expediente_context(cod, exp_info)
                    )
                )

                self.container_layout.addWidget(card)

        except Exception as e:
            self.container_layout.addWidget(QLabel(f"Error cargando datos: {e}"))

    def _build_expediente_context(self, code, info):
        idp = self.project_id_actual
        idr = info.get("idr")
        return {
            "code": code,
            "tipo": info.get("tipo"),
            "idp": idp,
            "idr": idr,
            "target_id": idr or idp,
        }

    def save_overall_status_change(self, project_id, code, new_status):
        """Guarda el estado global (MiniStatusBar) de un expediente en el JSON."""
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if code in data["expedientes"]:
                # Actualiza el status global
                data["expedientes"][code]["status"] = new_status

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                # 2. Emitir mensaje de éxito al Log
                self.log_requested.emit(f"🔄 [STATUS] {code} estado global guardado como: {new_status.upper()}")

        except Exception as e:
            # 3. Emitir error al Log
            self.log_requested.emit(f"❌ Error al guardar estado global de {code}: {e}")

    def save_step_change(self, project_id, code, new_step):
        print(f"Guardando progreso: {project_id} -> {code} -> Paso {new_step}")
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

        # 1. Cargar y Guardar datos
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if code in data["expedientes"]:
                data["expedientes"][code]["step_index"] = new_step
                data["expedientes"][code]["step_status"] = "detectado"

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

                for i in range(self.container_layout.count()):
                    widget = self.container_layout.itemAt(i).widget()
                    if isinstance(widget, ExpedienteCard) and widget.code == code:
                        # Leemos el estado recién guardado del JSON (o asumimos 'detectado')
                        widget.update_progress(new_step, "detectado")
                        break
                # ----------------------------------------------------------------

        except Exception as e:
            print(f"Error guardando progreso: {e}")
