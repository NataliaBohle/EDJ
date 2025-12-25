from __future__ import annotations

"""
EXEVA3: Detección de Anexos y Vinculados (REFACTORIZADO).
Usa utilidades centralizadas.
"""

import concurrent.futures
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Set
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

# Intentar importar pypdf
try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

# =========================
# Configuración y Filtros
# =========================

BASE_URL = "https://seia.sea.gob.cl"
EXCLUSIONS_FILE = Path(__file__).resolve().parent / "user_exclusions.json"

BASE_EXCLUSIONS = {
    "exact": {"", "#", "/"},
    "contains": {
        "javascript:", "mailto:", "tel:", "whatsapp:",
        "facebook.com", "twitter.com", "linkedin.com", "instagram.com",
        "recaptcha", "google.com/recaptcha", "void(0)",
        "http://www.sea.gob.cl/",
        "/busqueda/buscarProyecto.php",
        "/pacDia/publico/index.php",
        "/externos/proyectos_en_pac.php",
        "/busqueda/buscadorParticipacionCiudadana.php",
        "/pertinencia/buscarPertinencia.php",
        "/recursos/busqueda/buscar.php",
        "/busqueda/buscarRevisionRCA.php",
        "/busqueda/buscarNotificaciones.php",
        "/busqueda/buscarConsultor.php",
        "logout.php",
        "certInfoAjaxModal",
        "getXmlFile",
        "verificarFirma",
    },
}


def _log(cb: Callable[[str], None] | None, message: str) -> None:
    if cb:
        cb(message)


def _get_ex_json_path(idp: str, code: str) -> Path:
    return Path(os.getcwd()) / "Ebook" / idp / code / f"{idp}_{code}.json"


def _load_payload(idp: str, code: str) -> dict:
    path = _get_ex_json_path(idp, code)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_result(payload: dict, idp: str, code: str) -> Path:
    path = _get_ex_json_path(idp, code)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
    return path


def _get_user_exclusions() -> Set[str]:
    if not EXCLUSIONS_FILE.exists():
        return set()
    try:
        data = json.loads(EXCLUSIONS_FILE.read_text(encoding="utf-8"))
        return set(data.get("contains", []))
    except Exception:
        return set()


def add_global_exclusion(substring: str) -> None:
    current = _get_user_exclusions()
    if substring not in current:
        current.add(substring)
        data = {"contains": sorted(list(current))}
        EXCLUSIONS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _is_valid_url(href: str) -> bool:
    if not href: return False
    href_lower = href.lower().strip()

    if href_lower in BASE_EXCLUSIONS["exact"]: return False
    for exclusion in BASE_EXCLUSIONS["contains"]:
        if exclusion in href_lower: return False

    user_exc = _get_user_exclusions()
    for exclusion in user_exc:
        if exclusion.lower() in href_lower: return False

    return True


def _normalize_url(base_context_url: str, href: str) -> str:
    href = href.strip()
    if href.startswith("http") or href.startswith("https"):
        return href
    return urljoin(BASE_URL, href)


def _fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, timeout=30, verify=False)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def _resolve_and_extract_id(url: str) -> str | None:
    if not url: return None
    if "docId=" in url:
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            if "docId" in qs: return qs["docId"][0]
        except Exception:
            pass

    if "documento.php" in url:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10, verify=False)
            final_url = resp.url
            if "docId=" in final_url:
                parsed = urlparse(final_url)
                qs = parse_qs(parsed.query)
                if "docId" in qs: return qs["docId"][0]
        except Exception:
            pass

    return None


def _extract_links_from_html_table(html: str, context_url: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links_encontrados = []

    tablas = soup.find_all("table")
    for tabla in tablas:
        if tabla.find("table"): continue

        filas = tabla.find_all("tr")
        for fila in filas:
            celdas = fila.find_all(["td", "th"])
            if not celdas: continue

            enlace = fila.find("a", href=True)
            if not enlace: continue

            href = enlace["href"]
            if not _is_valid_url(href): continue

            full_url = _normalize_url(context_url, href)
            texto_enlace = enlace.get_text(" ", strip=True)

            extra_info = []
            for celda in celdas:
                txt = celda.get_text(" ", strip=True)
                if len(txt) > 200: continue
                if txt and txt != texto_enlace:
                    clean_txt = " ".join(txt.split())
                    extra_info.append(clean_txt)

            links_encontrados.append({
                "titulo": texto_enlace or "Documento vinculado",
                "url": full_url,
                "origen": "html",
                "info_extra": " | ".join(extra_info[:3])
            })
    return links_encontrados


def _extract_links_from_pdf_file(file_path: Path) -> List[Dict[str, str]]:
    if not PYPDF_AVAILABLE or not file_path.exists():
        return []
    links = []
    try:
        reader = PdfReader(str(file_path))
        for page in reader.pages:
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    obj = annot.get_object()
                    if "/A" in obj and "/URI" in obj["/A"]:
                        uri = obj["/A"]["/URI"]
                        if _is_valid_url(uri):
                            links.append({
                                "titulo": "Enlace en PDF",
                                "url": uri,
                                "origen": "pdf_interno"
                            })
    except Exception:
        pass
    return links


# =========================
# Lógica Principal (Workers + Guardado Incremental)
# =========================

def _process_doc_attachments(doc: dict, detect_dir: Path, log: Callable | None) -> None:
    anexos_list = []
    vinculados_list = []
    urls_vistas = set()

    doc_titulo = str(doc.get("titulo", "Doc"))[:40]

    parent_url = doc.get("URL_documento")
    parent_doc_id = _resolve_and_extract_id(parent_url) if parent_url else None

    # 1. ANEXOS
    url_anexos = doc.get("anexos_expediente")
    if url_anexos and _is_valid_url(url_anexos):
        html = _fetch_html(url_anexos)
        if html:
            encontrados = _extract_links_from_html_table(html, url_anexos)
            for item in encontrados:
                if item["url"] not in urls_vistas:
                    anexos_list.append(item)
                    urls_vistas.add(item["url"])

    # 2. DOC DIGITAL
    formato = str(doc.get("formato", "")).lower()
    url_doc = doc.get("URL_documento")
    if formato == "doc digital" and url_doc and _is_valid_url(url_doc):
        html = _fetch_html(url_doc)
        if html:
            encontrados = _extract_links_from_html_table(html, url_doc)
            for item in encontrados:
                link_id = _resolve_and_extract_id(item["url"])
                if parent_doc_id and link_id and parent_doc_id == link_id: continue
                if item["url"] not in urls_vistas:
                    item["tipo"] = "vinculado_html"
                    vinculados_list.append(item)
                    urls_vistas.add(item["url"])

    # 3. PDF LOCAL
    ruta_local = doc.get("ruta")
    if ruta_local:
        try:
            ruta_clean = str(ruta_local).replace("\\", "/")
            path_obj = Path(ruta_clean)
            if not path_obj.is_absolute():
                path_obj = detect_dir / path_obj

            if path_obj.exists() and path_obj.suffix.lower() == ".pdf":
                pdf_links = _extract_links_from_pdf_file(path_obj)
                for item in pdf_links:
                    link_id = _resolve_and_extract_id(item["url"])
                    if parent_doc_id and link_id and parent_doc_id == link_id: continue
                    if item["url"] not in urls_vistas:
                        item["tipo"] = "vinculado_pdf"
                        vinculados_list.append(item)
                        urls_vistas.add(item["url"])
        except Exception:
            pass

    doc["anexos_detectados"] = anexos_list
    doc["vinculados_detectados"] = vinculados_list

    if anexos_list or vinculados_list:
        _log(log, f"[Worker] {doc_titulo}: {len(anexos_list)} anexos, {len(vinculados_list)} vinculados.")


def detect_attachments(idp: str, code: str = "EXEVA", log: Callable[[str], None] | None = None) -> dict:
    code = (code or "EXEVA").strip()
    payload = _load_payload(idp, code) or {}
    ex_section = payload.get(code)
    if not isinstance(ex_section, dict):
        _log(log, f"[ANEXOS] No hay bloque {code} para ID {idp}.")
        return {}

    documentos = ex_section.get("documentos") or []
    total = len(documentos)
    detect_dir = Path(os.getcwd()) / "Ebook" / idp

    _log(log, f"[ANEXOS] ({code}) Iniciando análisis concurrente (10 workers) sobre {total} documentos...")

    SAVE_INTERVAL = 10
    processed_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for d in documentos:
            if isinstance(d, dict):
                f = executor.submit(_process_doc_attachments, d, detect_dir, log)
                futures.append(f)

        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
                processed_count += 1
                if processed_count % SAVE_INTERVAL == 0:
                    payload[code] = ex_section
                    _save_result(payload, idp, code)
                    _log(log, f"[Persistencia] ({code}) Progreso parcial guardado ({processed_count}/{total}).")
            except Exception as e:
                _log(log, f"[ANEXOS] ({code}) Error en un hilo: {e}")

    path_res = _save_result(payload, idp, code)
    _log(log, f"[ANEXOS] ({code}) Proceso finalizado. Datos guardados en: {path_res}")
    return ex_section


class AnexosDetectWorker(QObject):
    finished_signal = pyqtSignal(bool, dict)
    log_signal = pyqtSignal(str)

    def __init__(self, project_id: str, code: str = "EXEVA"):
        super().__init__()
        self.project_id = project_id
        self.code = code

    @pyqtSlot()
    def run(self) -> None:
        success = False
        result_data: dict = {}
        try:
            result_data = detect_attachments(self.project_id, self.code, log=self.log_signal.emit)
            if result_data:
                success = True
                self.log_signal.emit(f"✅ Detección de anexos completada para {self.code}.")
            else:
                self.log_signal.emit(f"⚠️ No se detectaron anexos para {self.code}.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante detección de anexos: {exc}")
        self.finished_signal.emit(success, result_data)


class FetchAnexosController(QObject):
    detection_started = pyqtSignal()
    detection_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: AnexosDetectWorker | None = None
        self.thread: QThread | None = None
        self._finished_dispatched = False

    def start_detection(self, project_id: str, code: str = "EXEVA") -> None:
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ Detección de anexos ya está en curso.")
            return

        self.detection_started.emit()
        self.thread = QThread()
        self.worker = AnexosDetectWorker(project_id, code)
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

    def _reset_thread_state(self) -> None:
        self.thread = None
        self.worker = None

    @pyqtSlot(bool, dict)
    def _on_finished(self, success: bool, exeva_data: dict) -> None:
        self._finished_dispatched = True
        self.detection_finished.emit(success, exeva_data)

    @pyqtSlot()
    def _on_thread_finished(self) -> None:
        if not self._finished_dispatched:
            self.detection_finished.emit(False, {})
