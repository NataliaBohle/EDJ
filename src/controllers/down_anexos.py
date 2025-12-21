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

# Importar utilidades centralizadas
from .utils import log as _log, sanitize_filename, url_extension, download_binary

from EDJ5_pro import a_detect


def _process_link_item(link_obj: dict, parent_n: str, out_base_dir: Path, detect_dir: Path, idp: str,
                       log: Callable | None) -> bool:
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

    # Crear carpeta del documento madre: Archivos_{IDP}/Anexos/{0004}/
    doc_dir = out_base_dir / parent_n
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Definir nombre base y extensión
    safe_title = sanitize_filename(titulo)
    ext = url_extension(url) or ".bin"
    target_path = doc_dir / (safe_title + ext)

    _log(log, f"[Worker] Procesando anexo: {safe_title}")

    # Descarga inteligente (verifica si existe, renombra si hay colisión, etc.)
    # Timeout de 90s para archivos grandes de anexos
    ok, final_path = download_binary(url, target_path, timeout=90)

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


def download_attachments_files(idp: str, log: Callable[[str], None] | None = None) -> dict:
    payload = a_detect.load_payload(idp) or {}
    exeva = payload.get("EXEVA")
    if not isinstance(exeva, dict):
        return {}

    documentos = exeva.get("documentos") or []
    detect_dir = Path(__file__).resolve().parent / "Detect"
    out_base = detect_dir / f"Archivos_{idp}" / "Anexos"

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
                    a_detect.save_result(payload)
                    _log(log, f"[Persistencia] Progreso anexos: {processed}/{total}")

            except Exception as e:
                _log(log, f"Error en hilo: {e}")

    # Guardado final asegurado
    path_res = a_detect.save_result(payload)
    _log(log, f"[Descarga de Anexos] Proceso finalizado. Datos actualizados.")

    return exeva


def download_single_attachment(idp: str, parent_n: str, link_obj: dict,
                               log: Callable[[str], None] | None = None) -> bool:
    """Descarga un único anexo (para el botón Reintentar de la UI)."""
    detect_dir = Path(__file__).resolve().parent / "Detect"
    out_base = detect_dir / f"Archivos_{idp}" / "Anexos"

    # Forzar descarga borrando ruta previa si existe
    if "ruta" in link_obj:
        del link_obj["ruta"]

    return _process_link_item(link_obj, parent_n, out_base, detect_dir, idp, log)