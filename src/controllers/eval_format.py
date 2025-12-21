from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from .utils import log as _log


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


def _format_from_value(value: str | None) -> str | None:
    if not value:
        return None
    value_lower = value.lower().strip()
    if value_lower.startswith("http"):
        try:
            value_lower = value_lower.split("?", 1)[0]
        except Exception:
            pass
    multi_map = {
        ".tar.gz": "TAR.GZ",
        ".tar.bz2": "TAR.BZ2",
        ".tar.xz": "TAR.XZ",
    }
    for ext, label in multi_map.items():
        if value_lower.endswith(ext):
            return label

    ext = value_lower.rsplit(".", 1)[-1] if "." in value_lower else ""
    ext = f".{ext}" if ext else ""

    simple_map = {
        ".zip": "ZIP",
        ".rar": "RAR",
        ".7z": "7ZIP",
        ".tar": "TAR",
        ".gz": "GZ",
        ".bz2": "BZ2",
        ".xz": "XZ",
        ".tgz": "TAR.GZ",
        ".pdf": "PDF",
        ".doc": "DOC",
        ".docx": "DOCX",
        ".xls": "XLS",
        ".xlsx": "XLSX",
        ".ppt": "PPT",
        ".pptx": "PPTX",
    }
    if ext in simple_map:
        return simple_map[ext]

    for ext_key, label in simple_map.items():
        if ext_key in value_lower:
            return label

    return None


def _record_format(format_value: str | None, total: dict) -> None:
    label = (format_value or "sin formato").strip() or "sin formato"
    total["format_counts"][label] = total["format_counts"].get(label, 0) + 1
    total["archivos_totales"] += 1
    if "pdf" in label.lower():
        total["archivos_pdf"] += 1


def _count_tree_formats(node: dict | list | None, total: dict) -> None:
    if isinstance(node, list):
        for item in node:
            _count_tree_formats(item, total)
        return
    if not isinstance(node, dict):
        return

    formato = node.get("formato")
    if formato and str(formato).lower() != "carpeta":
        _record_format(str(formato), total)

    contenido = node.get("contenido")
    if isinstance(contenido, list):
        for child in contenido:
            _count_tree_formats(child, total)


def _infer_link_format(link: dict) -> str | None:
    if not isinstance(link, dict):
        return None
    if link.get("formato"):
        return str(link.get("formato"))

    candidates = [
        link.get("ruta"),
        link.get("url"),
        link.get("titulo"),
        link.get("info_extra"),
        link.get("archivo"),
    ]
    for value in candidates:
        fmt = _format_from_value(str(value)) if value else None
        if fmt:
            return fmt
    return None


def evaluar_formatos_exeva(idp: str, log: Callable[[str], None] | None = None) -> dict:
    payload = _load_payload(idp) or {}
    exeva = payload.get("EXEVA")
    if not isinstance(exeva, dict):
        _log(log, "[EVAL_FORMAT] No hay datos EXEVA para evaluar formatos.")
        return {}

    documentos = exeva.get("documentos") or []
    if not isinstance(documentos, list):
        _log(log, "[EVAL_FORMAT] Formato inesperado de documentos.")
        return {}

    for doc in documentos:
        if not isinstance(doc, dict):
            continue
        total = {
            "archivos_totales": 0,
            "archivos_pdf": 0,
            "format_counts": {},
        }
        _record_format(doc.get("formato"), total)

        _count_tree_formats(doc.get("descomprimidos"), total)

        for key in ("anexos_detectados", "vinculados_detectados"):
            links = doc.get(key) or []
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, dict):
                    continue
                link_format = _infer_link_format(link)
                _record_format(link_format, total)
                _count_tree_formats(link.get("descomprimidos"), total)

        doc["archivos_totales"] = total["archivos_totales"]
        doc["archivos_pdf"] = total["archivos_pdf"]
        doc["formatos_detectados"] = total["format_counts"]

    _save_payload(idp, payload)
    _log(log, "[EVAL_FORMAT] Conteo de formatos actualizado.")
    return exeva


class EvalFormatWorker(QObject):
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
            result_data = evaluar_formatos_exeva(self.project_id, log=self.log_signal.emit)
            success = bool(result_data)
            if success:
                self.log_signal.emit("✅ Formatos evaluados correctamente.")
            else:
                self.log_signal.emit("⚠️ No hay datos para evaluar formatos.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante la evaluación: {exc}")
        self.finished_signal.emit(success, result_data)


class EvalFormatController(QObject):
    eval_started = pyqtSignal()
    eval_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: EvalFormatWorker | None = None
        self.thread: QThread | None = None

    def start_eval(self, project_id: str) -> None:
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ La evaluación de formatos ya está en curso.")
            return

        self.eval_started.emit()
        self.thread = QThread()
        self.worker = EvalFormatWorker(project_id)

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.finished_signal.connect(self.eval_finished.emit)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._cleanup_thread)

        self.thread.start()

    def _cleanup_thread(self) -> None:
        if self.thread:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None
