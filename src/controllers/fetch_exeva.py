"""
Controlador para extraer documentos del expediente EXEVA.
Basado en la lógica de scraping existente en scripts anteriores,
pero adaptado al estilo de controladores del proyecto actual.
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

BASE_URL = "https://seia.sea.gob.cl"
EXEVA_URL_TEMPLATES = [
    "https://seia.sea.gob.cl/expediente/xhr_expediente2.php?id_expediente={IDP}",
    "https://seia.sea.gob.cl/expediente/xhr_expediente.php?id_expediente={IDP}",
    "https://seia.sea.gob.cl/expediente/xhr_documentos.php?id_expediente={IDP}",
]


# ---------------------------------------------------------------------------
# Utilidades de parsing
# ---------------------------------------------------------------------------

def _log(cb: Callable[[str], None] | None, message: str) -> None:
    if cb:
        cb(message)


def _abs_url(href: str | None) -> Optional[str]:
    if not href:
        return None
    return BASE_URL + href if href.startswith("/") else href


def _infer_formato(url_documento: Optional[str], firmado: bool, inactivo: bool = False) -> str:
    if inactivo:
        return "Documento Inactivo en e-SEIA"
    if not url_documento:
        return "sin enlace"

    url_l = url_documento.lower()
    path = urlparse(url_l).path
    ext = os.path.splitext(path)[1].replace(".", "")

    if "firma.sea.gob.cl" in url_l or "infofirma.sea.gob.cl" in url_l:
        return "pdf firmado"
    if firmado:
        return "doc digital"
    if ext:
        return "doc digital" if ext == "php" else ext
    return "otro"


def _parse_tabla_nueva(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    documentos: List[Dict[str, Any]] = []

    for row in rows:
        celdas = row.find_all("td", recursive=False)
        if len(celdas) < 7:
            continue

        n_visual = (celdas[0].get_text(strip=True) or "")
        n = n_visual.zfill(4) if n_visual.isdigit() else (n_visual or "0").zfill(4)
        num_doc = celdas[1].get_text(strip=True) or None
        folio = celdas[2].get_text(strip=True) or None

        col_doc = celdas[3]
        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        remitido_por = celdas[4].get_text(strip=True) or None
        destinado_a = celdas[5].get_text(strip=True) or None
        fecha_hora = celdas[6].get_text(strip=True)

        fecha, hora = (fecha_hora.split(" ", 1) if " " in fecha_hora else (fecha_hora, None))

        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s))
        inactivo = bool(col_doc.find("img", src=lambda s: s and "leafInactivo.gif" in s))

        anexos = None
        for a in col_doc.find_all("a", href=True):
            if "elementosFisicos/enviados.php" in a["href"]:
                anexos = _abs_url(a["href"])
                break

        formato = _infer_formato(url_documento, firmado, inactivo)

        documentos.append(
            {
                "n": n,
                "num_doc": num_doc,
                "folio": folio,
                "titulo": titulo,
                "remitido_por": remitido_por,
                "destinado_a": destinado_a,
                "fecha": fecha,
                "hora": hora,
                "anexos_expediente": anexos,
                "URL_documento": url_documento,
                "formato": formato,
                "ruta": "",
            }
        )
    return documentos


def _parse_tabla_vieja(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    documentos: List[Dict[str, Any]] = []

    for row in rows:
        celdas = row.find_all("td", recursive=False)
        if len(celdas) < 8:
            continue

        n = (celdas[0].get_text(strip=True) or "").zfill(4)
        num_doc = celdas[1].get_text(strip=True) or None
        folio = celdas[2].get_text(strip=True)
        col_doc = celdas[3]
        col_acc = celdas[7]

        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        remitido_por = celdas[4].get_text(strip=True)
        destinado_a = celdas[5].get_text(strip=True) or None
        fecha_hora = celdas[6].get_text(strip=True)
        fecha, hora = (fecha_hora.split(" ", 1) if " " in fecha_hora else (fecha_hora, None))

        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s)) or (
            url_documento
            and ("firma.sea.gob.cl" in url_documento or "infofirma.sea.gob.cl" in url_documento)
        )
        inactivo = bool(col_doc.find("img", src=lambda s: s and "leafInactivo.gif" in s))

        anexos = None
        for a in col_doc.find_all("a", href=True):
            if "elementosFisicos/enviados.php" in a["href"]:
                anexos = _abs_url(a["href"])
                break
        if not anexos and col_acc:
            btn = col_acc.find(
                lambda t: t.name in ("button", "a")
                and t.has_attr("onclick")
                and "elementosFisicos/enviados.php" in t["onclick"]
            )
            if btn:
                oc = btn["onclick"]
                start = oc.find("('")
                if start != -1:
                    start += 2
                    end = oc.find("'", start)
                    if end != -1:
                        anexos = _abs_url(oc[start:end])

        formato = _infer_formato(url_documento, firmado, inactivo)

        documentos.append(
            {
                "n": n,
                "num_doc": num_doc,
                "folio": folio,
                "titulo": titulo,
                "remitido_por": remitido_por,
                "destinado_a": destinado_a,
                "fecha": fecha,
                "hora": hora,
                "anexos_expediente": anexos,
                "URL_documento": url_documento,
                "formato": formato,
                "ruta": "",
            }
        )
    return documentos


# ---------------------------------------------------------------------------
# Extracción de datos
# ---------------------------------------------------------------------------

def _extract_exeva(idp: str, log: Callable[[str], None] | None = None) -> Dict[str, Any]:
    idp = (idp or "").strip()

    response_text: str | None = None
    for template in EXEVA_URL_TEMPLATES:
        url = template.format(IDP=idp)
        _log(log, f"[EXEVA] Consultando expediente: {url}")

        try:
            r = requests.get(url, timeout=15, verify=False)
        except requests.RequestException as exc:
            _log(log, f"[EXEVA] Error de conexión con '{url}': {exc}")
            continue

        if r.status_code != 200:
            _log(log, f"[EXEVA] Respuesta HTTP inesperada ({r.status_code}) para '{url}'")
            continue

        response_text = r.text
        break

    if response_text is None:
        return {"IDP": idp, "EXEVA": {"documentos": [], "summary": {"total": 0, "format_counts": {}}}}

    soup = BeautifulSoup(response_text, "html.parser")
    documentos: List[Dict[str, Any]] = []

    tabla_nueva = soup.select_one("table.tabla_datos_linea")
    if tabla_nueva:
        documentos = _parse_tabla_nueva(tabla_nueva)
    else:
        tabla_vieja = soup.select_one("#tbldocumentos") or soup.find("table", id="tbldocumentos")
        if tabla_vieja:
            documentos = _parse_tabla_vieja(tabla_vieja)
        else:
            posible = None
            for t in soup.find_all("table"):
                ths = [th.get_text(strip=True).lower() for th in t.find_all("th")]
                headers = " ".join(ths)
                if all(h in headers for h in ["folio", "documento", "remitido", "destinado", "fecha"]):
                    posible = t
                    break
            if posible:
                documentos = _parse_tabla_nueva(posible)
            else:
                _log(log, "[EXEVA] No se encontró tabla de documentos.")

    conteo = Counter(doc.get("formato", "sin formato") for doc in documentos)
    return {
        "IDP": idp,
        "EXEVA": {
            "documentos": documentos,
            "summary": {"total": len(documentos), "format_counts": dict(conteo)},
        },
    }


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def _save_exeva_data(idp: str, exeva_data: dict, new_status: str, log: Callable[[str], None]):
    base_folder = os.path.join(os.getcwd(), "Ebook", idp)
    json_path = os.path.join(base_folder, f"{idp}_fetch.json")

    if not os.path.exists(json_path):
        log("❌ Error al guardar: No se encontró el archivo base de configuración.")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "EXEVA" in data.get("expedientes", {}):
            data["expedientes"]["EXEVA"]["EXEVA_DATA"] = exeva_data
            data["expedientes"]["EXEVA"]["status"] = new_status
            data["expedientes"]["EXEVA"]["step_index"] = 1
            data["expedientes"]["EXEVA"]["step_status"] = "detectado"
            data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as exc:
        log(f"❌ Error crítico al escribir en JSON: {exc}")


# ---------------------------------------------------------------------------
# Worker y controlador
# ---------------------------------------------------------------------------


class ExevaFetchWorker(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, dict)

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id

    @pyqtSlot()
    def run(self):
        self.log_signal.emit(f"🔎 Extracción de EXEVA para ID {self.project_id}...")
        success = False
        result_data: Dict[str, Any] = {}
        try:
            exeva_data = _extract_exeva(self.project_id, log=self.log_signal.emit)
            documentos = exeva_data.get("EXEVA", {}).get("documentos", [])

            if documentos:
                _save_exeva_data(self.project_id, exeva_data, "edicion", log=self.log_signal.emit)
                self.log_signal.emit("✅ Extracción de EXEVA completada.")
                success = True
                result_data = exeva_data
            else:
                _save_exeva_data(self.project_id, exeva_data, "error", log=self.log_signal.emit)
                self.log_signal.emit("❌ Extracción fallida. No se encontraron documentos.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante extracción: {exc}")

        self.finished_signal.emit(success, result_data)


class FetchExevaController(QObject):
    extraction_started = pyqtSignal()
    extraction_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: ExevaFetchWorker | None = None
        self.thread: QThread | None = None
        self._finished_dispatched = False

    def start_extraction(self, project_id: str):
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ Extracción de EXEVA ya está en curso.")
            return

        self.extraction_started.emit()
        self.thread = QThread()
        self.worker = ExevaFetchWorker(project_id)
        self._finished_dispatched = False

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.finished_signal.connect(self._on_finished)
        self.thread.finished.connect(self._on_thread_finished)

        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._reset_thread_state)

        self.thread.start()

    def _reset_thread_state(self):
        self.thread = None
        self.worker = None

    @pyqtSlot(bool, dict)
    def _on_finished(self, success: bool, exeva_data: dict):
        self._finished_dispatched = True
        self.extraction_finished.emit(success, exeva_data)

    @pyqtSlot()
    def _on_thread_finished(self):
        if not self._finished_dispatched:
            self.extraction_finished.emit(False, {})
