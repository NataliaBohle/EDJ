# src/controllers/fetch_antgen.py

import os
import json
import time
import requests
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from bs4 import BeautifulSoup
from typing import Callable, Dict, Any, List


# --- LÓGICA DE PERSISTENCIA ---

def _save_antgen_data(idp: str, antgen_data: dict, new_status: str, log: Callable[[str], None]):
    """Guarda la data extraída y actualiza el estado del expediente ANTGEN."""
    base_folder = os.path.join(os.getcwd(), "Ebook", idp)
    json_path = os.path.join(base_folder, f"{idp}_fetch.json")

    if not os.path.exists(json_path):
        log("❌ Error al guardar: No se encontró el archivo base de configuración.")
        return

    try:
        # 1. Cargar payload existente
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 2. Actualizar ANTGEN: datos, estado global y avance de pasos
        if "ANTGEN" in data.get("expedientes", {}):
            data["expedientes"]["ANTGEN"]["ANTGEN_DATA"] = antgen_data  # Almacena todos los datos
            data["expedientes"]["ANTGEN"]["status"] = new_status  # Cambia el estado global
            data["expedientes"]["ANTGEN"]["step_index"] = 1  # Avanza al paso "Descargar"
            data["expedientes"]["ANTGEN"]["step_status"] = "detectado"  # Resetea el paso 1 a "Detectado"
            data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # 3. Guardar payload modificado
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    except Exception as e:
        log(f"❌ Error crítico al escribir en JSON: {e}")


# --- LÓGICA DE EXTRACCIÓN (Basada en b1_antgen.py) ---

ANTGEN_URL_TEMPLATE = (
    "https://seia.sea.gob.cl/expediente/ficha/fichaPrincipal.php?modo=normal&id_expediente={IDP}"
)


def _extract_antgen(idp: str, log: Callable[[str], None]) -> Dict[str, Any]:
    """Extrae los Antecedentes Generales de la ficha del expediente."""
    url = ANTGEN_URL_TEMPLATE.format(IDP=idp)
    log(f"🔎 Conectando a {url}...")

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()  # Lanza excepción si el estado HTTP es 4xx o 5xx
    except requests.RequestException as e:
        log(f"❌ Error de conexión/HTTP: {e}")
        return {}

    soup = BeautifulSoup(r.text, "html.parser")
    ant: Dict[str, Any] = {}

    # Título y forma de presentación
    titulo = soup.find("h2", class_="sg-title text-title text-primary")
    if titulo and titulo.text:
        ant["nombre_proyecto"] = titulo.text.split(":")[-1].strip()

    forma = soup.find("h2", string=lambda t: t and "Forma de Presen" in t)
    if forma and forma.text:
        ant["forma_presentacion"] = forma.text.split(":")[-1].strip()

    # Bloques principales (Tipo, Monto, Estado, Encargado)
    bloques = soup.find_all("div", class_="sg-row-file-data")
    for bloque in bloques:
        label = bloque.find("div", class_="col-md-3")
        value = bloque.find("div", class_="col-md-9")
        if not label or not value: continue
        key = label.get_text(strip=True)
        val = value.get_text(strip=True)
        if key == "Tipo de Proyecto":
            ant["tipo_proyecto"] = val
        elif key == "Monto de Inversión":
            ant["monto_inversion"] = val
        elif key == "Estado Actual":
            ant["estado_actual"] = val
        elif "Encargado" in key:
            link = value.find("a")
            ant["encargado"] = link.text.strip() if link else val

    # Descripción y objetivo
    descripcion_tag = soup.find("div", class_="sg-description-file")
    if descripcion_tag:
        ant["descripcion_proyecto_html"] = str(descripcion_tag)
        texto = descripcion_tag.get_text(separator="\n", strip=True)
        partes = texto.split("Objetivo")
        ant["descripcion_proyecto"] = partes[0].strip() if partes else ""
        if len(partes) > 1:
            ant["objetivo_proyecto"] = partes[1].strip()

    # Datos de contacto (Titular/Rep/Cons) - Lógica simplificada
    def extraer_contacto(nombre_boton: str) -> Dict[str, str]:
        datos: Dict[str, str] = {}
        accordion = soup.find("button", string=lambda s: s and nombre_boton.lower() in s.lower())
        if accordion:
            body = accordion.find_next("div", class_="accordion-body")
            if body:
                for fila in body.find_all("div", class_="row"):
                    label = fila.find("div", class_="col-md-3").get_text(strip=True).lower()
                    value = fila.find("div", class_="col-md-9").get_text(strip=True)
                    if "nombre" in label:
                        datos["nombre"] = value
                    elif "domicilio" in label:
                        datos["domicilio"] = value
                    elif "mail" in label or "correo" in label:
                        datos["email"] = value
        return datos

    ant["titular"] = extraer_contacto("Titular")
    ant["representante_legal"] = extraer_contacto("Representante Legal")
    ant["consultora"] = extraer_contacto("Consultora Ambiental")

    # Permisos Ambientales Sectoriales (PAS)
    permisos: List[Dict[str, str]] = []
    tabla_pas = soup.select_one("table#example2")
    if tabla_pas:
        cuerpo = tabla_pas.find("tbody") or tabla_pas
        for row in cuerpo.find_all("tr"):
            celdas = [td.get_text(" ", strip=True) for td in row.find_all("td")]
            if len(celdas) >= 3:
                fila = {"articulo": celdas[0], "nombre": celdas[1], "tipo": celdas[2]}
                if len(celdas) >= 4:
                    fila["certificado"] = celdas[3]
                permisos.append(fila)
    if permisos:
        ant["permisos_ambientales"] = permisos

    # Registro de estados del proyecto
    estados: List[Dict[str, str]] = []
    tabla_estados = soup.find("table", id="detallelistado")
    if tabla_estados:
        filas = tabla_estados.find_all("tr")
        for i, row in enumerate(filas):
            celdas = row.find_all("td")
            if len(celdas) >= 5:
                estado = celdas[0].get_text(strip=True)
                doc_link = celdas[1].find("a")
                documento = doc_link.get_text(strip=True) if doc_link else celdas[1].get_text(strip=True)
                numero = celdas[2].get_text(strip=True)
                fecha = celdas[3].get_text(strip=True)
                autor = celdas[4].get_text(strip=True)
                # Ignorar encabezado si viene como fila
                if i == 0 and estado.lower() == "estado" and documento.lower() == "documento":
                    continue
                estados.append({
                    "estado": estado,
                    "documento": documento,
                    "numero": numero,
                    "fecha": fecha,
                    "autor": autor,
                })
    if estados:
        ant["registro_estados"] = estados

    return ant


# --- WORKER Y CONTROLADOR ---

class AntgenFetchWorker(QObject):
    log_signal = pyqtSignal(str)
    # Emite (success: bool, antgen_data: dict)
    finished_signal = pyqtSignal(bool, dict)

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id

    @pyqtSlot()
    def run(self):
        self.log_signal.emit(f"🔎 Extracción en curso para ID {self.project_id}...")
        success = False
        result_data = {}
        try:
            antgen_data = _extract_antgen(self.project_id, log=self.log_signal.emit)
            if antgen_data.get("nombre_proyecto"):
                _save_antgen_data(self.project_id, antgen_data, "edicion", log=self.log_signal.emit)
                self.log_signal.emit(f"✅ Extracción de ANTGEN completada.")
                success = True
                result_data = antgen_data
            else:
                _save_antgen_data(self.project_id, {}, "error", log=self.log_signal.emit)
                self.log_signal.emit(f"❌ Extracción fallida. No se encontraron datos principales.")
        except Exception as e:
            self.log_signal.emit(f"❌ Error inesperado durante extracción: {e}")

        self.finished_signal.emit(success, result_data)


class FetchAntgenController(QObject):
    extraction_started = pyqtSignal()
    extraction_finished = pyqtSignal(bool, dict)  # (success, antgen_data)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.thread = None
        self._finished_dispatched = False

    def start_extraction(self, project_id: str):
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ Extracción de ANTGEN ya está en curso.")
            return

        self.extraction_started.emit()
        self.thread = QThread()
        self.worker = AntgenFetchWorker(project_id)
        self._finished_dispatched = False

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        # Conectar señales
        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.finished_signal.connect(self._on_finished)
        self.thread.finished.connect(self._on_thread_finished)

        # Limpieza
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._reset_thread_state)

        self.thread.start()

    def _reset_thread_state(self):
        self.thread = None
        self.worker = None

    @pyqtSlot(bool, dict)
    def _on_finished(self, success: bool, antgen_data: dict):
        self._finished_dispatched = True
        self.extraction_finished.emit(success, antgen_data)

    @pyqtSlot()
    def _on_thread_finished(self):
        if not self._finished_dispatched:
            # Fallback para asegurar que la UI se reactive aunque el worker falle
            self.extraction_finished.emit(False, {})