# src/controllers/antgen_comp.py
from __future__ import annotations
import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# Importamos la nueva clase plantilla
from src.templates.antgen_report import AntGenReport

class AntgenCompiler(QObject):
    """
    Controlador encargado de la compilación del PDF de Antecedentes Generales.
    Delega el diseño visual a src.templates.antgen_report.AntGenReport.
    """

    log_requested = pyqtSignal(str)
    compilation_started = pyqtSignal()
    compilation_finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @pyqtSlot(str, dict)
    def compile_pdf(self, project_id: str, antgen_payload: dict | None = None):
        """
        Inicia el proceso de compilación.
        :param project_id: ID del expediente.
        :param antgen_payload: Diccionario con los datos. Si es None, intenta cargar del JSON.
        """
        self.compilation_started.emit()
        self.log_requested.emit(f"⚙️ Preparando compilación para ID {project_id}...")

        try:
            # 1. Obtener datos
            payload = antgen_payload or self._load_antgen_payload(project_id)
            if not payload:
                raise ValueError("No se encontraron datos para compilar (JSON vacío o inexistente).")

            # 2. Definir ruta de salida
            base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
            os.makedirs(base_folder, exist_ok=True)
            output_path = os.path.join(base_folder, f"ANTGEN_{project_id}.pdf")

            # 3. Instanciar la Plantilla y Generar
            # Aquí ocurre la magia visual
            report = AntGenReport(output_path)
            report.build(payload)

            self.log_requested.emit(f"✅ PDF generado exitosamente: {output_path}")
            self.compilation_finished.emit(True, output_path)

        except Exception as exc:
            self.log_requested.emit(f"❌ Error crítico al compilar PDF: {exc}")
            import traceback
            traceback.print_exc()
            self.compilation_finished.emit(False, "")

    def _load_antgen_payload(self, project_id: str) -> dict:
        """Carga los datos desde el archivo JSON local si no se proveen en memoria."""
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

        if not os.path.exists(json_path):
            self.log_requested.emit(f"⚠️ Archivo JSON no encontrado: {json_path}")
            return {}

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Retornamos solo la parte de datos de ANTGEN
            return data.get("expedientes", {}).get("ANTGEN", {}).get("ANTGEN_DATA", {})
        except Exception as e:
            self.log_requested.emit(f"⚠️ Error leyendo JSON: {e}")
            return {}