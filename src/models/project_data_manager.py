import os
import json
from PyQt6.QtCore import QObject, pyqtSignal


class ProjectDataManager(QObject):
    """
    Gestor centralizado para leer y escribir en los JSON del proyecto.
    Evita tener 'with open(...)' dispersos por toda la interfaz.
    """
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def _get_json_path(self, project_id: str) -> str:
        return os.path.join(os.getcwd(), "Ebook", project_id, f"{project_id}_fetch.json")

    def _get_exeva_json_path(self, project_id: str) -> str:
        return os.path.join(os.getcwd(), "Ebook", project_id, "EXEVA", f"{project_id}_EXEVA.json")

    def load_data(self, project_id: str) -> dict:
        """Carga el JSON completo del proyecto."""
        path = self._get_json_path(project_id)
        if not os.path.exists(path):
            self.log_requested.emit(f"⚠️ Archivo JSON no encontrado: {path}")
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log_requested.emit(f"❌ Error leyendo JSON: {e}")
            return {}

    def load_exeva_data(self, project_id: str) -> dict:
        """Carga el JSON específico de EXEVA si existe."""
        path = self._get_exeva_json_path(project_id)
        if not os.path.exists(path):
            self.log_requested.emit(f"⚠️ Archivo EXEVA no encontrado: {path}")
            return {}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log_requested.emit(f"❌ Error leyendo JSON de EXEVA: {e}")
            return {}

    def save_antgen_field_data(self, project_id: str, field_data: dict):
        """Guarda un diccionario de valores (campos) dentro de ANTGEN_DATA."""
        data = self.load_data(project_id)
        if not data: return

        try:
            # Asegurar estructura
            if "expedientes" not in data: data["expedientes"] = {}
            if "ANTGEN" not in data["expedientes"]: data["expedientes"]["ANTGEN"] = {}

            # Actualizar o crear ANTGEN_DATA
            target = data["expedientes"]["ANTGEN"].setdefault("ANTGEN_DATA", {})
            target.update(field_data)

            self._write_json(project_id, data)
            # self.log_requested.emit("💾 Datos guardados.") # Opcional: muy verborrágico
        except Exception as e:
            self.log_requested.emit(f"❌ Error guardando campos: {e}")

    def save_antgen_field_statuses(self, project_id: str, status_data: dict):
        """Guarda el diccionario de estados de cada campo (field_statuses)."""
        data = self.load_data(project_id)
        if not data: return

        try:
            if "ANTGEN" in data.get("expedientes", {}):
                data["expedientes"]["ANTGEN"]["field_statuses"] = status_data
                self._write_json(project_id, data)
        except Exception as e:
            self.log_requested.emit(f"❌ Error guardando estados de campos: {e}")

    def update_step_status(self, project_id: str, section: str, step_index: int = None,
                           step_status: str = None, global_status: str = None):
        """Actualiza el progreso (timeline) y el estado global de una sección."""
        data = self.load_data(project_id)
        if not data: return

        try:
            if section in data.get("expedientes", {}):
                target = data["expedientes"][section]

                if global_status:
                    target["status"] = global_status

                if step_index is not None:
                    target["step_index"] = step_index
                    target["step_status"] = step_status or "detectado"

                self._write_json(project_id, data)

                if step_index is not None:
                    self.log_requested.emit(f"💾 Progreso {section}: Paso {step_index} ({step_status})")
        except Exception as e:
            self.log_requested.emit(f"❌ Error actualizando status: {e}")

    def _write_json(self, project_id, data):
        """Escribe los datos al disco."""
        path = self._get_json_path(project_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)