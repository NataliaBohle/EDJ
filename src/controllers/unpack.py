from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Callable

import py7zr
import rarfile
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from .utils import log as _log

EXT_COMP = {".zip", ".rar", ".7z"}
MAX_RECURSION = 8


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


def _set_unrar_tool(log: Callable[[str], None] | None) -> None:
    unrar_path = Path(__file__).resolve().parent / "UnRAR.exe"
    if unrar_path.exists():
        rarfile.UNRAR_TOOL = str(unrar_path)
        _log(log, f"[UNPACK] Usando UNRAR local: {unrar_path}")


def _extract_with_unrar(archive_path: Path, out_dir: Path) -> None:
    command = [
        str(rarfile.UNRAR_TOOL),
        "x",
        "-y",
        str(archive_path),
        str(out_dir),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "UNRAR falló")


def _extract_archive(archive_path: Path, out_dir: Path, log: Callable[[str], None] | None) -> None:
    ext = archive_path.suffix.lower()
    if ext == ".zip":
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(out_dir)
    elif ext == ".rar":
        try:
            with rarfile.RarFile(str(archive_path), "r") as rar_ref:
                rar_ref.extractall(out_dir)
        except Exception:
            _log(log, f"[UNPACK] rarfile falló con {archive_path.name}. Probando UNRAR...")
            _extract_with_unrar(archive_path, out_dir)
    elif ext == ".7z":
        with py7zr.SevenZipFile(archive_path, mode="r") as seven_zip:
            seven_zip.extractall(path=out_dir)
    else:
        raise ValueError(f"Formato no soportado: {ext}")


def _walk_compressed_files(folder: Path):
    for root, _, files in os.walk(folder):
        for file in files:
            path = Path(root) / file
            if path.suffix.lower() in EXT_COMP:
                yield path


def _extract_recursive(archive_path: Path, log: Callable[[str], None] | None) -> list[dict]:
    failures: list[dict] = []
    queue = [(archive_path, 0)]

    while queue:
        current, depth = queue.pop(0)
        if depth > MAX_RECURSION:
            failures.append({
                "archivo": current.name,
                "ruta": str(current),
                "error": f"Límite de niveles alcanzado ({MAX_RECURSION})",
            })
            continue

        out_dir = current.with_suffix("")
        if not out_dir.exists() or not any(out_dir.iterdir()):
            out_dir.mkdir(parents=True, exist_ok=True)
            try:
                _log(log, f"[UNPACK] Descomprimiendo: {current.name} → {out_dir}")
                _extract_archive(current, out_dir, log)
            except Exception as exc:
                failures.append({
                    "archivo": current.name,
                    "ruta": str(current),
                    "error": str(exc),
                })
                continue

        for nested in _walk_compressed_files(out_dir):
            nested_out = nested.with_suffix("")
            if not nested_out.exists() or not any(nested_out.iterdir()):
                queue.append((nested, depth + 1))

    return failures


def _resolve_file_path(project_root: Path, exeva_root: Path, ruta: str | None) -> Path | None:
    if not ruta:
        return None
    path = Path(str(ruta))
    if path.is_absolute() and path.exists():
        return path

    candidate = project_root / path
    if candidate.exists():
        return candidate

    candidate = exeva_root / path
    if candidate.exists():
        return candidate

    return None


def _normalize_route(path: Path, base_dir: Path) -> str:
    try:
        rel = path.resolve().relative_to(base_dir.resolve())
        return rel.as_posix()
    except Exception:
        return path.as_posix()


def _index_tree(path: Path, base_dir: Path) -> dict:
    info = {
        "nombre": path.name,
        "formato": "carpeta" if path.is_dir() else (path.suffix.lower().lstrip(".") or "desconocido"),
        "ruta": _normalize_route(path, base_dir),
    }
    if path.is_dir():
        children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        info["contenido"] = [_index_tree(child, base_dir) for child in children]
    return info


def _base_for_item(project_root: Path, exeva_root: Path, ruta: str | None) -> Path:
    if ruta and str(ruta).replace("\\", "/").startswith("EXEVA/"):
        return project_root
    return exeva_root


def _mark_unpack_error(item: dict, error: str) -> None:
    item["error_descompresion"] = True
    item.setdefault("errores_descompresion", [])
    item["errores_descompresion"].append(error)


def _clear_unpack_error(item: dict) -> None:
    item.pop("error_descompresion", None)
    item.pop("errores_descompresion", None)


def _process_item(item: dict, project_root: Path, exeva_root: Path,
                  log: Callable[[str], None] | None, failures: list[dict]) -> bool:
    ruta = item.get("ruta")
    archive_path = _resolve_file_path(project_root, exeva_root, ruta)
    if not archive_path:
        if ruta:
            _mark_unpack_error(item, "Archivo no encontrado")
            failures.append({
                "archivo": Path(str(ruta)).name,
                "ruta": str(ruta),
                "error": "Archivo no encontrado",
            })
        return False

    if archive_path.suffix.lower() not in EXT_COMP:
        return False

    current_failures = _extract_recursive(archive_path, log)
    failures.extend(current_failures)

    out_dir = archive_path.with_suffix("")
    if out_dir.exists() and out_dir.is_dir():
        base_dir = _base_for_item(project_root, exeva_root, ruta)
        item["descomprimidos"] = _index_tree(out_dir, base_dir)
        if current_failures:
            for failure in current_failures:
                archivo = failure.get("archivo") or Path(str(ruta)).name
                error_msg = failure.get("error", "Error de descompresión")
                _mark_unpack_error(item, f"{archivo}: {error_msg}")
        else:
            _clear_unpack_error(item)
        return True

    return False


def unpack_exeva_archives(idp: str, log: Callable[[str], None] | None = None) -> dict:
    _set_unrar_tool(log)
    payload = _load_payload(idp) or {}
    exeva = payload.get("EXEVA")
    if not isinstance(exeva, dict):
        _log(log, "[UNPACK] No hay datos EXEVA para descomprimir.")
        return {}

    documentos = exeva.get("documentos") or []
    if not isinstance(documentos, list):
        _log(log, "[UNPACK] Formato inesperado de documentos.")
        return {}

    project_root = Path(os.getcwd()) / "Ebook" / idp
    exeva_root = project_root / "EXEVA"

    total_items = 0
    indexed_items = 0
    failures: list[dict] = []

    for doc in documentos:
        if not isinstance(doc, dict):
            continue

        if "descomprimidos" in doc:
            doc.pop("descomprimidos", None)

        if _process_item(doc, project_root, exeva_root, log, failures):
            indexed_items += 1
        total_items += 1

        for key in ("anexos_detectados", "vinculados_detectados"):
            links = doc.get(key) or []
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, dict):
                    continue
                total_items += 1
                link.pop("descomprimidos", None)
                if _process_item(link, project_root, exeva_root, log, failures):
                    indexed_items += 1

    _save_payload(idp, payload)
    _log(log, f"[UNPACK] Ítems indexados: {indexed_items}/{total_items}.")

    if failures:
        _log(log, "[UNPACK] Archivos con error en descompresión:")
        for failure in failures:
            _log(log, f" - {failure['archivo']}: {failure['error']}")

    return exeva


def unpack_exeva_item(idp: str, ruta: str, log: Callable[[str], None] | None = None) -> bool:
    _set_unrar_tool(log)
    payload = _load_payload(idp) or {}
    exeva = payload.get("EXEVA")
    if not isinstance(exeva, dict):
        _log(log, "[UNPACK] No hay datos EXEVA para descomprimir.")
        return False

    documentos = exeva.get("documentos") or []
    if not isinstance(documentos, list):
        _log(log, "[UNPACK] Formato inesperado de documentos.")
        return False

    project_root = Path(os.getcwd()) / "Ebook" / idp
    exeva_root = project_root / "EXEVA"

    failures: list[dict] = []
    changed = False
    target = str(ruta).replace("\\", "/")

    def _matches(item: dict) -> bool:
        item_path = str(item.get("ruta") or "").replace("\\", "/")
        return bool(item_path) and item_path == target

    for doc in documentos:
        if not isinstance(doc, dict):
            continue
        if _matches(doc):
            if _process_item(doc, project_root, exeva_root, log, failures):
                changed = True
        for key in ("anexos_detectados", "vinculados_detectados"):
            links = doc.get(key) or []
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, dict):
                    continue
                if _matches(link):
                    if _process_item(link, project_root, exeva_root, log, failures):
                        changed = True

    if changed:
        _save_payload(idp, payload)
    else:
        _log(log, "[UNPACK] No se encontró el archivo solicitado.")
    return changed


class UnpackWorker(QObject):
    finished_signal = pyqtSignal(bool, dict)
    log_signal = pyqtSignal(str)

    def __init__(self, project_id: str, ruta: str | None = None):
        super().__init__()
        self.project_id = project_id
        self.ruta = ruta

    @pyqtSlot()
    def run(self) -> None:
        success = False
        result_data: dict = {}
        try:
            if self.ruta:
                success = unpack_exeva_item(self.project_id, self.ruta, log=self.log_signal.emit)
                if success:
                    result_data = _load_payload(self.project_id).get("EXEVA", {})
            else:
                result_data = unpack_exeva_archives(self.project_id, log=self.log_signal.emit)
                success = bool(result_data)

            if success:
                self.log_signal.emit("✅ Descompresión e indexación completadas.")
            else:
                if self.ruta:
                    self.log_signal.emit("⚠️ No se pudo descomprimir el archivo solicitado.")
                else:
                    self.log_signal.emit("⚠️ No hay datos para descomprimir.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error inesperado durante la descompresión: {exc}")
        self.finished_signal.emit(success, result_data)


class UnpackController(QObject):
    unpack_started = pyqtSignal()
    unpack_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: UnpackWorker | None = None
        self.thread: QThread | None = None

    def start_unpack(self, project_id: str) -> None:
        self._start_unpack(project_id, None)

    def start_unpack_item(self, project_id: str, ruta: str) -> None:
        self._start_unpack(project_id, ruta)

    def _start_unpack(self, project_id: str, ruta: str | None) -> None:
        if self.thread and self.thread.isRunning():
            self.log_requested.emit("⚠️ La descompresión ya está en curso.")
            return

        self.unpack_started.emit()
        self.thread = QThread()
        self.worker = UnpackWorker(project_id, ruta)

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.log_signal.connect(self.log_requested.emit)
        self.worker.finished_signal.connect(self.unpack_finished.emit)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
