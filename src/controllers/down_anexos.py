from __future__ import annotations

"""
Descarga de Anexos y Vinculados detectados (OPTIMIZADO).

Mejoras de rendimiento:
- Workers reducidos a 4 para evitar saturación de red/disco.
- Guardado incremental cada 50 ítems (menos I/O de disco).
- Uso de utilidades centralizadas (utils.py).
"""

from pathlib import Path
from typing import Callable
import concurrent.futures
import json
import os
import shutil

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

# Importar utilidades centralizadas
from .utils import log as _log, sanitize_filename, url_extension, url_filename, download_binary


def _doc_folder_name(n: str) -> str:
    try:
        num = int(n)
        return f"{num:02d}"
    except Exception:
        n = (n or "").strip()
        return (n[-2:] or "00").zfill(2)


def _process_link_item(
    link_obj: dict,
    parent_n: str,
    out_base_dir: Path,
    detect_dir: Path,
    idp: str,
    log: Callable | None,
    *,
    overwrite: bool = False,
) -> bool:
    url = link_obj.get("url")
    if not url: return False

    # Si ya tiene ruta válida, saltar
    if link_obj.get("ruta"):
        # Validación rápida: si el archivo existe, no hacemos nada.
        # Si no existe (se borró), download_binary lo bajará de nuevo.
        try:
            full_path = detect_dir / link_obj["ruta"]
            if full_path.exists() and full_path.stat().st_size > 0:
                return True
        except Exception:
            pass

    titulo = link_obj.get("titulo", "archivo")
    original_name = url_filename(url)
    original_stem = Path(original_name).stem if original_name else ""

    # Crear carpeta del documento madre: Archivos_{IDP}/Anexos/{0004}/
    doc_dir = out_base_dir / _doc_folder_name(parent_n)
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Definir nombre base y extensión
    safe_title = sanitize_filename(original_stem or titulo)
    ext = Path(original_name).suffix or url_extension(url) or ".bin"
    target_path = doc_dir / (safe_title + ext)

    _log(log, f"[Worker] Procesando anexo: {safe_title}")

    # Descarga inteligente (verifica si existe, renombra si hay colisión, etc.)
    # Timeout de 90s para archivos grandes de anexos
    ok, final_path = download_binary(url, target_path, timeout=90, overwrite=overwrite)

    if ok:
        try:
            # Calcular ruta relativa para el JSON
            rel = final_path.resolve().relative_to(detect_dir.resolve())
            clean_path = str(rel).replace("\\", "/")

            # Guardar en el objeto del link
            link_obj["ruta"] = clean_path

            # Limpiar marca de error si existía
            if "error" in link_obj:
                del link_obj["error"]
            return True
        except Exception:
            pass

    # Si falló, marcar error para que la UI lo muestre en rojo
    link_obj["error"] = True
    _log(log, f"[Worker] Error descargando: {url}")
    return False


def _get_exeva_json_path(idp: str) -> Path:
    return Path(os.getcwd()) / "Ebook" / idp / "EXEVA" / f"{idp}_EXEVA.json"


def _load_payload(idp: str) -> dict:
    path = _get_exeva_json_path(idp)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_payload(idp: str, payload: dict) -> Path:
    path = _get_exeva_json_path(idp)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
    return path


def download_attachments_files(idp: str, log: Callable[[str], None] | None = None) -> dict:
    payload = _load_payload(idp) or {}
    exeva = payload.get("EXEVA")
    if not isinstance(exeva, dict):
        return {}

    documentos = exeva.get("documentos") or []
    exeva_dir = Path(os.getcwd()) / "Ebook" / idp / "EXEVA"
    detect_dir = exeva_dir
    out_base = exeva_dir / "files"

    tasks = []

    # 1. Recolectar tareas
    for doc in documentos:
        if not isinstance(doc, dict): continue
        n = str(doc.get("n") or "0000").strip()

        # Unificar listas de anexos y vinculados
        listas = (doc.get("anexos_detectados") or []) + (doc.get("vinculados_detectados") or [])

        for link in listas:
            # Procesar si no tiene ruta O si tuvo error previo
            if not link.get("ruta") or link.get("error"):
                tasks.append((link, n))

    total = len(tasks)
    if total == 0:
        _log(log, "[Descarga de Anexos] Todos los anexos están descargados.")
        return exeva

    _log(log, f"[Descarga de Anexos] Iniciando descarga de {total} anexos (4 workers)...")

    # OPTIMIZACIÓN: Intervalo de guardado más largo para no saturar disco
    SAVE_INTERVAL = 50
    processed = 0

    # OPTIMIZACIÓN: Menos workers para estabilidad en descargas pesadas
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for link_obj, parent_n in tasks:
            f = executor.submit(_process_link_item, link_obj, parent_n, out_base, detect_dir, idp, log)
            futures.append(f)

        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
                processed += 1

                # Guardado parcial menos frecuente
                if processed % SAVE_INTERVAL == 0:
                    _save_payload(idp, payload)
                    _log(log, f"[Persistencia] Progreso anexos: {processed}/{total}")

            except Exception as e:
                _log(log, f"Error en hilo: {e}")

    # Guardado final asegurado
    path_res = _save_payload(idp, payload)
    _log(log, f"[Descarga de Anexos] Proceso finalizado. Datos actualizados.")

    return exeva


def _clear_attachment_node(link_obj: dict, detect_dir: Path, log: Callable | None) -> None:
    ruta = link_obj.get("ruta")
    if ruta:
        try:
            full_path = detect_dir / ruta
            if full_path.exists():
                if full_path.is_dir():
                    shutil.rmtree(full_path)
                else:
                    full_path.unlink()
            extracted_path = full_path.with_suffix("")
            if extracted_path.exists() and extracted_path.is_dir():
                shutil.rmtree(extracted_path)
        except Exception as exc:
            _log(log, f"[Worker] No se pudo limpiar archivo previo: {exc}")

    for key in ("ruta", "descomprimidos", "error"):
        link_obj.pop(key, None)


def download_single_attachment(
    idp: str,
    parent_n: str,
    link_obj: dict,
    log: Callable[[str], None] | None = None,
) -> bool:
    """Descarga un único anexo (para el botón Reintentar de la UI)."""
    exeva_dir = Path(os.getcwd()) / "Ebook" / idp / "EXEVA"
    detect_dir = exeva_dir
    out_base = exeva_dir / "files"

    _clear_attachment_node(link_obj, detect_dir, log)

    return _process_link_item(
        link_obj,
        parent_n,
        out_base,
        detect_dir,
        idp,
        log,
        overwrite=True,
    )


class AnexosDownloadWorker(QObject):
    finished_signal = pyqtSignal(bool, dict)
    log_signal = pyqtSignal(str)

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id

    @pyqtSlot()
    def run(self) -> None:
        success = False
        result_data: dict = {}
        try:
            result_data = download_attachments_files(self.project_id, log=self.log_signal.emit)
            if result_data:
                success = True
                self.log_signal.emit("✅ Descarga de anexos completada.")
            else:
                self.log_signal.emit("⚠️ No hay anexos para descargar.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante descarga de anexos: {exc}")
        self.finished_signal.emit(success, result_data)


class DownAnexosController(QObject):
    download_started = pyqtSignal()
    download_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: AnexosDownloadWorker | None = None
        self.thread: QThread | None = None
        self._finished_dispatched = False

    def start_download(self, project_id: str) -> None:
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ Descarga de anexos ya está en curso.")
            return

        self.download_started.emit()
        self.thread = QThread()
        self.worker = AnexosDownloadWorker(project_id)
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
        self.download_finished.emit(success, exeva_data)

    @pyqtSlot()
    def _on_thread_finished(self) -> None:
        if not self._finished_dispatched:
            self.download_finished.emit(False, {})
