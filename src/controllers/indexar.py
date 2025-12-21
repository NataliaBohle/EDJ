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


def _assign_n_to_tree(node: dict | list) -> None:
    if isinstance(node, list):
        for idx, item in enumerate(node, 1):
            if isinstance(item, dict):
                item.setdefault("n", f"{idx:04d}")
            _assign_n_to_tree(item)
        return

    if not isinstance(node, dict):
        return

    if "n" not in node and any(key in node for key in ("ruta", "nombre", "titulo", "archivo")):
        node["n"] = "0001"

    contenido = node.get("contenido")
    if isinstance(contenido, list):
        for idx, item in enumerate(contenido, 1):
            if isinstance(item, dict):
                item.setdefault("n", f"{idx:04d}")
            _assign_n_to_tree(item)

    for key, value in node.items():
        if key == "contenido":
            continue
        if isinstance(value, (dict, list)):
            _assign_n_to_tree(value)


def _indexar_item(item: dict) -> bool:
    tree = item.get("descomprimidos")
    if not isinstance(tree, dict):
        return False
    _assign_n_to_tree(tree)
    return True


def indexar_exeva(idp: str, log: Callable[[str], None] | None = None) -> dict:
    payload = _load_payload(idp) or {}
    exeva = payload.get("EXEVA")
    if not isinstance(exeva, dict):
        _log(log, "[INDEXAR] No hay datos EXEVA para indexar.")
        return {}

    documentos = exeva.get("documentos") or []
    if not isinstance(documentos, list):
        _log(log, "[INDEXAR] Formato inesperado de documentos.")
        return {}

    indexados = 0
    for doc in documentos:
        if not isinstance(doc, dict):
            continue
        if _indexar_item(doc):
            indexados += 1
        for key in ("anexos_detectados", "vinculados_detectados"):
            links = doc.get(key) or []
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, dict):
                    continue
                if _indexar_item(link):
                    indexados += 1

    _assign_n_to_tree(documentos)
    _save_payload(idp, payload)
    _log(log, f"[INDEXAR] Ítems con N asignado: {indexados}.")
    return exeva


class IndexarWorker(QObject):
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
            result_data = indexar_exeva(self.project_id, log=self.log_signal.emit)
            success = bool(result_data)
            if success:
                self.log_signal.emit("✅ Indexación de descomprimidos completada.")
            else:
                self.log_signal.emit("⚠️ No hay datos para indexar.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante la indexación: {exc}")
        self.finished_signal.emit(success, result_data)


class IndexarController(QObject):
    index_started = pyqtSignal()
    index_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: IndexarWorker | None = None
        self.thread: QThread | None = None

    def start_index(self, project_id: str) -> None:
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ La indexación ya está en curso.")
            return

        self.index_started.emit()
        self.thread = QThread()
        self.worker = IndexarWorker(project_id)

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.finished_signal.connect(self.index_finished.emit)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._cleanup_thread)

        self.thread.start()

    def _cleanup_thread(self) -> None:
        if self.thread:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None
