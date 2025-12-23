"""
Controlador para extraer documentos del expediente (EX).
Basado en la lógica de scraping existente en scripts anteriores,
pero adaptado al estilo de controladores del proyecto actual.
"""

from __future__ import annotations

import json
import os
import time
import base64
import concurrent.futures
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

BASE_URL = "https://seia.sea.gob.cl"
EX_URL_TEMPLATES = {
    "EXEVA": [
        "https://seia.sea.gob.cl/expediente/xhr_expediente2.php?id_expediente={IDP}",
        "https://seia.sea.gob.cl/expediente/xhr_expediente.php?id_expediente={IDP}",
        "https://seia.sea.gob.cl/expediente/xhr_documentos.php?id_expediente={IDP}",
    ],
    # TODO: agregar templates por expediente aquí.
    # "EXPAC": ["..."],
    # "EXPCI": ["..."],
    # "EXA86": ["..."],
}

# Silenciar advertencias de certificados autofirmados/ausentes durante las
# peticiones a los servicios de EXEVA. Se mantienen las solicitudes con
# verify=False para compatibilidad, pero sin inundar los logs con
# InsecureRequestWarning.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Utilidades de parsing
# ---------------------------------------------------------------------------

def _log(cb: Callable[[str], None] | None, message: str) -> None:
    if cb:
        cb(message)


def _sanitize_filename(name: str) -> str:
    """Limpia nombres de archivo eliminando caracteres peligrosos."""

    invalid = '<>:\"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in name)
    return cleaned.strip() or "documento"


def _url_extension(url: str) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1]


def _download_binary(url: str, out_path: Path) -> Tuple[bool, Path]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=30, verify=False) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True, out_path
    except Exception:
        return False, out_path


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


def _parse_documentos_from_html(html: str, log: Callable[[str], None] | None) -> List[Dict[str, Any]]:
    """Parsea HTML del expediente y devuelve la lista de documentos encontrados."""

    soup = BeautifulSoup(html, "html.parser")
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
                _log(log, "[EX] No se encontró tabla de documentos.")

    return documentos


# ---------------------------------------------------------------------------
# Descarga de documentos
# ---------------------------------------------------------------------------


def _print_docdigital(url: str, out_path: Path, log: Callable[[str], None] | None = None) -> Tuple[bool, Path]:
    """Imprime un documento digital usando Selenium (modo headless)."""

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        from webdriver_manager.chrome import ChromeDriverManager

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1280,2000")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        WebDriverWait(driver, timeout=45).until(lambda d: d.execute_script("return document.readyState") == "complete")

        pdf = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True, "paperWidth": 8.5, "paperHeight": 13})

        if out_path.suffix.lower() != ".pdf":
            out_path = out_path.with_suffix(".pdf")

        with open(out_path, "wb") as f:
            f.write(base64.b64decode(pdf["data"]))

        driver.quit()
        return True, out_path
    except Exception as exc:
        _log(log, f"[EX] Falló la impresión Selenium: {exc}")
        return False, out_path


def _doc_folder_name(n: str) -> str:
    try:
        num = int(n)
        return f"{num:02d}"
    except Exception:
        n = (n or "").strip()
        return (n[-2:] or "00").zfill(2)


def _process_doc(
    d: dict,
    base_dir: Path,
    code: str,
    project_id: str,
    log: Callable | None,
    overwrite: bool = False,
) -> bool:
    ex_dir = base_dir / code
    files_root = ex_dir / "files"

    # 1. Validar si ya existe
    if not overwrite:
        ruta_prev = d.get("ruta")
        try:
            if ruta_prev:
                p_str = str(ruta_prev).replace("/", os.sep).replace("\\", os.sep)
                p_prev = Path(p_str)
                if not p_prev.is_absolute():
                    p_prev = (base_dir / p_prev).resolve()
                if p_prev.is_file():
                    return True
        except Exception:
            pass

    # 2. Datos
    folio = str(d.get("folio") or "").strip()
    titulo = str(d.get("titulo") or "").strip()
    n = str(d.get("n") or d.get("num_doc") or "").strip()
    formato = (d.get("formato") or "").strip().lower()
    url = d.get("URL_documento") or d.get("url") or ""

    if not url:
        d["error_descarga"] = True
        return False

    folder_name = _doc_folder_name(n)
    out_dir = files_root / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # 3. Ruta usando utilidades
    base_name = _sanitize_filename("_".join([p for p in [n, folio, titulo] if p])) or "documento"
    ext_url = _url_extension(url)
    is_php_like = ext_url in ("", ".php") or "documento.php" in url.lower()

    final_ext = ext_url or ".bin"
    if is_php_like or formato == "doc digital" or "pdf" in formato:
        final_ext = ".pdf"

    saved_path = out_dir / (base_name + final_ext)

    # 4. Descarga
    use_printer = (is_php_like or formato == "doc digital") and ("pdf firmado" not in formato)

    ok = False
    if use_printer:
        if overwrite:
            _log(log, f"[Worker] Recargando (Selenium): {titulo}")
        else:
            _log(log, f"[Worker] Imprimiendo: {titulo}")
        ok, saved_path = _print_docdigital(url, saved_path, log=log)
    else:
        if overwrite:
            _log(log, f"[Worker] Recargando: {titulo}")
        else:
            _log(log, f"[Worker] Descargando: {titulo}")
        ok, saved_path = _download_binary(url, saved_path)

    # 5. Guardar ruta
    if ok:
        try:
            rel = saved_path.resolve().relative_to(base_dir.resolve())
        except Exception:
            rel = Path(code) / "files" / saved_path.name

        clean_path = str(rel).replace("\\", "/")
        if clean_path.startswith("/"):
            clean_path = clean_path[1:]

        d["ruta"] = clean_path
        d.pop("error_descarga", None)
        return True

    _log(log, f"[Worker] Falló: {titulo}")
    d["error_descarga"] = True
    return False


def _download_documents(
    project_id: str,
    code: str,
    ex_data: dict,
    log: Callable[[str], None] | None = None,
) -> None:
    documentos = ex_data.get(code, {}).get("documentos", []) if isinstance(ex_data, dict) else []
    total = len(documentos)

    base_dir = Path(os.getcwd()) / "Ebook" / project_id
    base_dir.mkdir(parents=True, exist_ok=True)
    if total == 0:
        return

    _log(log, f"[EX] Iniciando descarga de {total} documentos...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(_process_doc, d, base_dir, code, project_id, log, False)
            for d in documentos
        ]

        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            try:
                future.result()
            except Exception as exc:
                _log(log, f"[EX] Error en descarga concurrente: {exc}")

    _log(log, "[EX] Descarga finalizada.")


# ---------------------------------------------------------------------------
# Extracción de datos
# ---------------------------------------------------------------------------

def _extract_expediente(code: str, idp: str, log: Callable[[str], None] | None = None) -> Dict[str, Any]:
    idp = (idp or "").strip()

    documentos: List[Dict[str, Any]] = []
    templates = EX_URL_TEMPLATES.get(code, [])
    if not templates:
        _log(log, f"[EX] No hay templates configuradas para {code}.")
        return {"IDP": idp, code: {"documentos": [], "summary": {"total": 0, "format_counts": {}}}}

    for template in templates:
        url = template.format(IDP=idp)
        _log(log, f"[{code}] Consultando expediente: {url}")

        try:
            r = requests.get(url, timeout=15, verify=False)
        except requests.RequestException as exc:
            _log(log, f"[{code}] Error de conexión con '{url}': {exc}")
            continue

        if r.status_code != 200:
            _log(log, f"[{code}] Respuesta HTTP inesperada ({r.status_code}) para '{url}'")
            continue

        documentos = _parse_documentos_from_html(r.text, log)
        if documentos:
            break
        _log(log, f"[{code}] Respuesta sin documentos desde '{url}', probando siguiente plantilla...")

    if not documentos:
        return {"IDP": idp, code: {"documentos": [], "summary": {"total": 0, "format_counts": {}}}}

    conteo = Counter(doc.get("formato", "sin formato") for doc in documentos)
    return {
        "IDP": idp,
        code: {
            "documentos": documentos,
            "summary": {"total": len(documentos), "format_counts": dict(conteo)},
        },
    }


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def _save_ex_data(idp: str, code: str, ex_data: dict, new_status: str, log: Callable[[str], None]):
    base_folder = os.path.join(os.getcwd(), "Ebook", idp)
    base_json_path = os.path.join(base_folder, f"{idp}_fetch.json")
    ex_folder = os.path.join(base_folder, code)
    ex_json_path = os.path.join(ex_folder, f"{idp}_{code}.json")

    os.makedirs(ex_folder, exist_ok=True)

    try:
        with open(ex_json_path, "w", encoding="utf-8") as f:
            json.dump(ex_data, f, indent=4, ensure_ascii=False)
        log(f"💾 Datos {code} guardados en {ex_json_path}")
    except Exception as exc:
        log(f"❌ Error crítico al escribir datos {code}: {exc}")

    if not os.path.exists(base_json_path):
        log("⚠️ No se encontró el archivo base de configuración para actualizar el estado.")
        return

    try:
        with open(base_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if code in data.get("expedientes", {}):
            data["expedientes"][code]["status"] = new_status
            data["expedientes"][code]["step_index"] = 1
            data["expedientes"][code]["step_status"] = "detectado"
            data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(base_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as exc:
        log(f"❌ Error crítico al actualizar estado en JSON base: {exc}")


# ---------------------------------------------------------------------------
# Worker y controlador
# ---------------------------------------------------------------------------


class ExFetchWorker(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, dict)

    def __init__(self, project_id: str, target_id: str, code: str):
        super().__init__()
        self.project_id = project_id
        self.target_id = target_id
        self.code = code

    @pyqtSlot()
    def run(self):
        self.log_signal.emit(f"🔎 Extracción de {self.code} para ID {self.target_id}...")
        success = False
        result_data: Dict[str, Any] = {}
        try:
            ex_data = _extract_expediente(self.code, self.target_id, log=self.log_signal.emit)
            documentos = ex_data.get(self.code, {}).get("documentos", [])

            if documentos:
                _download_documents(self.project_id, self.code, ex_data, log=self.log_signal.emit)
                _save_ex_data(self.project_id, self.code, ex_data, "edicion", log=self.log_signal.emit)
                self.log_signal.emit(f"✅ Extracción de {self.code} completada.")
                success = True
                result_data = ex_data
            else:
                _save_ex_data(self.project_id, self.code, ex_data, "error", log=self.log_signal.emit)
                self.log_signal.emit("❌ Extracción fallida. No se encontraron documentos.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante extracción: {exc}")

        self.finished_signal.emit(success, result_data)


class SingleDocDownloadWorker(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, dict)

    def __init__(self, project_id: str, code: str, doc_data: dict):
        super().__init__()
        self.project_id = project_id
        self.code = code
        self.doc_data = doc_data

    @pyqtSlot()
    def run(self) -> None:
        success = False
        try:
            base_dir = Path(os.getcwd()) / "Ebook" / self.project_id
            success = _process_doc(
                self.doc_data,
                base_dir,
                self.code,
                self.project_id,
                self.log_signal.emit,
                overwrite=True,
            )
            if success:
                self.log_signal.emit("✅ Reintento de descarga completado.")
            else:
                self.log_signal.emit("⚠️ Reintento de descarga fallido.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante reintento: {exc}")
        self.finished_signal.emit(success, self.doc_data)


class FetchExController(QObject):
    extraction_started = pyqtSignal()
    extraction_finished = pyqtSignal(bool, dict)
    retry_started = pyqtSignal()
    retry_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: ExFetchWorker | None = None
        self.thread: QThread | None = None
        self._finished_dispatched = False
        self.retry_worker: SingleDocDownloadWorker | None = None
        self.retry_thread: QThread | None = None
        self._retry_finished_dispatched = False

    def start_extraction(self, project_id: str, target_id: str, code: str):
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ Extracción de expediente ya está en curso.")
            return

        self.extraction_started.emit()
        self.thread = QThread()
        self.worker = ExFetchWorker(project_id, target_id, code)
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

    def retry_download(self, project_id: str, code: str, doc_data: dict) -> None:
        if self.retry_thread and self.retry_thread.isRunning():
            self.log_requested.emit("⚠️ Ya hay un reintento de descarga en curso.")
            return

        self.retry_started.emit()
        self.retry_thread = QThread()
        self.retry_worker = SingleDocDownloadWorker(project_id, code, doc_data)
        self._retry_finished_dispatched = False

        self.retry_worker.moveToThread(self.retry_thread)
        self.retry_thread.started.connect(self.retry_worker.run)

        self.retry_worker.log_signal.connect(self.log_requested.emit)
        self.retry_worker.finished_signal.connect(self._on_retry_finished)
        self.retry_thread.finished.connect(self._on_retry_thread_finished)

        self.retry_worker.finished_signal.connect(self.retry_thread.quit)
        self.retry_worker.finished_signal.connect(self.retry_worker.deleteLater)
        self.retry_thread.finished.connect(self.retry_thread.deleteLater)
        self.retry_thread.finished.connect(self._reset_retry_thread_state)

        self.retry_thread.start()

    def _reset_retry_thread_state(self) -> None:
        self.retry_thread = None
        self.retry_worker = None

    @pyqtSlot(bool, dict)
    def _on_retry_finished(self, success: bool, doc_data: dict) -> None:
        self._retry_finished_dispatched = True
        self.retry_finished.emit(success, doc_data)

    @pyqtSlot()
    def _on_retry_thread_finished(self) -> None:
        if not self._retry_finished_dispatched:
            self.retry_finished.emit(False, {})
