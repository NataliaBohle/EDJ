"""
Controlador para extraer documentos del expediente (EX).

- EXREX -> EXREC (corregido).
- Soporta códigos dinámicos tipo REC_215... (usa plantilla base EXREC).
- EXPCI / EXA86 / EXREC construyen URL con IDR.
- Parsers: EXEVA (nueva/vieja), PAC, PCI, Art.86, Recursos.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

BASE_URL = "https://seia.sea.gob.cl"

# Plantillas por "código base" (no por código dinámico).
EX_URL_TEMPLATES: Dict[str, List[str]] = {
    "EXEVA": [
        f"{BASE_URL}/expediente/xhr_expediente2.php?id_expediente={{IDP}}",
        f"{BASE_URL}/expediente/xhr_expediente.php?id_expediente={{IDP}}",
        f"{BASE_URL}/expediente/xhr_documentos.php?id_expediente={{IDP}}",
    ],
    "EXPAC": [f"{BASE_URL}/expediente/xhr_documentos_pac.php?id_expediente={{IDP}}"],
    "EXPCI": [f"{BASE_URL}/expediente/xhr_pci.php?id_expediente={{IDR}}"],
    "EXA86": [f"{BASE_URL}/expediente/xhr_pci_reunion.php?id_expediente={{IDR}}"],

    # EXREC: endpoints a probar (ajusta a tu endpoint real si ya lo tienes)
    "EXREC": [
        f"{BASE_URL}/expediente/xhr_recurso.php?id_recurso={{IDR}}",
        f"{BASE_URL}/expediente/xhr_recurso.php?id_expediente={{IDP}}&id_recurso={{IDR}}",
        f"{BASE_URL}/expediente/xhr_recursos.php?id_expediente={{IDP}}",
    ],
}

EXPEDIENTES_FRAGMENTS = {
    "ANTGEN": "fichaPrincipal.php",
    "EXEVA": ["xhr_expediente.php", "xhr_documentos.php"],
    "EXPAC": "xhr_documentos_pac.php",
    "EXPCI": "xhr_pci.php",
    "EXA86": "xhr_pci_reunion.php",
    "EXSYF": "seguimiento/xhr_principal.php",
    "EXSAN": "sanciones/xhr_principal.php",
    "EXREV": "revisionRCA/principal.php",
    "CAL": "newPlazos.php",
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# -----------------------------------------------------------------------------
# HTTP
# -----------------------------------------------------------------------------

def _make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        }
    )
    return s


def _http_get(session: requests.Session, url: str, timeout: int = 20) -> Tuple[int, str]:
    r = session.get(url, timeout=timeout, verify=False)
    return r.status_code, (r.text or "")


# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------

def _log(cb: Optional[Callable[[str], None]], message: str) -> None:
    if cb:
        cb(message)


def _sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in name)
    cleaned = cleaned.strip()
    return cleaned or "documento"


def _url_extension(url: str) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1]


def _abs_url(href: Optional[str]) -> Optional[str]:
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


def _doc_folder_name(n: str) -> str:
    try:
        num = int(n)
        return f"{num:02d}"
    except Exception:
        n = (n or "").strip()
        return (n[-2:] or "00").zfill(2)


def _normalize_code(code: str) -> Tuple[str, Optional[str]]:
    c = (code or "").strip()
    for prefix, base in (
        ("REC_", "EXREC"),
        ("PCI_", "EXPCI"),
        ("A86_", "EXA86"),
        ("PAC_", "EXPAC"),
    ):
        if c.startswith(prefix):
            suffix = c[len(prefix):].strip() or None
            return base, suffix
    return c, None


# -----------------------------------------------------------------------------
# Parsing
# -----------------------------------------------------------------------------

def _parse_tabla_exeva_nueva(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    docs: List[Dict[str, Any]] = []

    for row in rows:
        c = row.find_all("td", recursive=False)
        if len(c) < 7:
            continue

        n_visual = (c[0].get_text(strip=True) or "")
        n = n_visual.zfill(4) if n_visual.isdigit() else (n_visual or "0").zfill(4)
        num_doc = c[1].get_text(strip=True) or None
        folio = c[2].get_text(strip=True) or None

        col_doc = c[3]
        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        remitido_por = c[4].get_text(strip=True) or None
        destinado_a = c[5].get_text(strip=True) or None
        fecha_hora = c[6].get_text(strip=True)
        fecha, hora = (fecha_hora.split(" ", 1) if " " in fecha_hora else (fecha_hora, None))

        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s))
        inactivo = bool(col_doc.find("img", src=lambda s: s and "leafInactivo.gif" in s))

        anexos = None
        for a in col_doc.find_all("a", href=True):
            if "elementosFisicos/enviados.php" in a["href"]:
                anexos = _abs_url(a["href"])
                break

        formato = _infer_formato(url_documento, firmado, inactivo)

        docs.append(
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
    return docs


def _parse_tabla_exeva_vieja(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    docs: List[Dict[str, Any]] = []

    for row in rows:
        c = row.find_all("td", recursive=False)
        if len(c) < 8:
            continue

        n = (c[0].get_text(strip=True) or "").zfill(4)
        num_doc = c[1].get_text(strip=True) or None
        folio = c[2].get_text(strip=True) or None
        col_doc = c[3]
        col_acc = c[7]

        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        remitido_por = c[4].get_text(strip=True) or None
        destinado_a = c[5].get_text(strip=True) or None
        fecha_hora = c[6].get_text(strip=True)
        fecha, hora = (fecha_hora.split(" ", 1) if " " in fecha_hora else (fecha_hora, None))

        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s)) or (
            url_documento and ("firma.sea.gob.cl" in url_documento or "infofirma.sea.gob.cl" in url_documento)
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

        docs.append(
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
    return docs


def _parse_tabla_pac(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    docs: List[Dict[str, Any]] = []

    for row in rows:
        c = row.find_all("td", recursive=False)
        if len(c) < 7:
            continue

        n_visual = (c[1].get_text(strip=True) or "")
        n = n_visual.zfill(4) if n_visual.isdigit() else (n_visual or "0").zfill(4)

        folio = c[2].get_text(strip=True) or None
        col_doc = c[3]
        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        remitido_por = c[4].get_text(strip=True) or None
        destinado_a = c[5].get_text(strip=True) or None

        fecha_hora = c[6].get_text(strip=True)
        fecha, hora = (fecha_hora.split(" ", 1) if " " in fecha_hora else (fecha_hora, None))

        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s)) or (
            url_documento and ("firma.sea.gob.cl" in url_documento or "infofirma.sea.gob.cl" in url_documento)
        )
        inactivo = bool(col_doc.find("img", src=lambda s: s and "leafInactivo.gif" in s))

        anexos = None
        for a in col_doc.find_all("a", href=True):
            if "elementosFisicos/enviados.php" in a["href"]:
                anexos = _abs_url(a["href"])
                break

        formato = _infer_formato(url_documento, firmado, inactivo)

        docs.append(
            {
                "n": n,
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
    return docs


def _parse_tabla_pci(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    docs: List[Dict[str, Any]] = []

    for row in rows:
        c = row.find_all("td", recursive=False)
        if len(c) < 7:
            continue

        n_visual = (c[0].get_text(strip=True) or "")
        n = n_visual.zfill(4) if n_visual.isdigit() else (n_visual or "0").zfill(4)
        num_doc = c[1].get_text(strip=True) or None
        etapa = c[2].get_text(strip=True) or None

        col_doc = c[3]
        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        fecha_exp_txt = c[4].get_text(strip=True)
        fecha_exp, hora_exp = (fecha_exp_txt.split(" ", 1) if " " in fecha_exp_txt else (fecha_exp_txt, None))

        autor = c[5].get_text(strip=True) or None

        fecha_gen_txt = c[6].get_text(strip=True) if len(c) >= 7 else ""
        fecha_gen, hora_gen = (fecha_gen_txt.split(" ", 1) if " " in fecha_gen_txt else (fecha_gen_txt, None))

        col_acc = c[-1]
        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s)) or (
            url_documento and ("firma.sea.gob.cl" in url_documento or "infofirma.sea.gob.cl" in url_documento)
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

        docs.append(
            {
                "n": n,
                "num_doc": num_doc,
                "etapa": etapa,
                "titulo": titulo,
                "remitido_por": autor,
                "destinado_a": None,
                "fecha_exp": fecha_exp,
                "hora_exp": hora_exp,
                "fecha_gen": fecha_gen,
                "hora_gen": hora_gen,
                "anexos_expediente": anexos,
                "URL_documento": url_documento,
                "formato": formato,
                "ruta": "",
            }
        )
    return docs


def _parse_tabla_reunion_a86(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    docs: List[Dict[str, Any]] = []

    for row in rows:
        c = row.find_all("td", recursive=False)
        if len(c) < 6:
            continue

        n_visual = (c[1].get_text(strip=True) or "")
        n = n_visual.zfill(4) if n_visual.isdigit() else (n_visual or "0").zfill(4)

        col_doc = c[2]
        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        fecha_pub_txt = c[3].get_text(strip=True)
        fecha_pub, hora_pub = (fecha_pub_txt.split(" ", 1) if " " in fecha_pub_txt else (fecha_pub_txt, None))

        autor = c[4].get_text(strip=True) or None

        fecha_gen_txt = c[5].get_text(strip=True) if len(c) > 5 else ""
        fecha_gen, hora_gen = (fecha_gen_txt.split(" ", 1) if " " in fecha_gen_txt else (fecha_gen_txt, None))

        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s)) or (
            url_documento and ("firma.sea.gob.cl" in url_documento or "infofirma.sea.gob.cl" in url_documento)
        )
        inactivo = bool(col_doc.find("img", src=lambda s: s and "leafInactivo.gif" in s))

        formato = _infer_formato(url_documento, firmado, inactivo)

        docs.append(
            {
                "n": n,
                "titulo": titulo,
                "remitido_por": autor,
                "destinado_a": None,
                "fecha": fecha_pub,
                "hora": hora_pub,
                "fecha_gen": fecha_gen,
                "hora_gen": hora_gen,
                "anexos_expediente": None,
                "URL_documento": url_documento,
                "formato": formato,
                "ruta": "",
            }
        )
    return docs


def _parse_tabla_recursos(tabla) -> List[Dict[str, Any]]:
    tbody = tabla.find("tbody") or tabla
    rows = tbody.find_all("tr", recursive=False)
    docs: List[Dict[str, Any]] = []

    for row in rows:
        c = row.find_all("td", recursive=False)
        if len(c) < 6:
            continue

        n_visual = (c[1].get_text(strip=True) or "")
        n = n_visual.zfill(4) if n_visual.isdigit() else (n_visual or "0").zfill(4)

        folio = c[2].get_text(strip=True) or None
        col_doc = c[3]
        a_doc = col_doc.find("a", href=True)
        titulo = a_doc.get_text(strip=True) if a_doc else "Sin título"
        url_documento = _abs_url(a_doc["href"]) if a_doc else None

        remitido_por = c[4].get_text(strip=True) or None

        fecha_txt = c[5].get_text(strip=True)
        fecha, hora = (fecha_txt.split(" ", 1) if " " in fecha_txt else (fecha_txt, None))

        firmado = bool(col_doc.find("img", src=lambda s: s and "certd.gif" in s)) or (
            url_documento and ("firma.sea.gob.cl" in url_documento or "infofirma.sea.gob.cl" in url_documento)
        )
        inactivo = bool(col_doc.find("img", src=lambda s: s and "leafInactivo.gif" in s))

        formato = _infer_formato(url_documento, firmado, inactivo)

        docs.append(
            {
                "n": n,
                "folio": folio,
                "titulo": titulo,
                "remitido_por": remitido_por,
                "destinado_a": None,
                "fecha": fecha,
                "hora": hora,
                "anexos_expediente": None,
                "URL_documento": url_documento,
                "formato": formato,
                "ruta": "",
            }
        )
    return docs


def _parse_documentos_from_html(html: str, log: Optional[Callable[[str], None]]) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html or "", "html.parser")

    tabla_exeva_nueva = soup.select_one("table.tabla_datos_linea")
    if tabla_exeva_nueva:
        return _parse_tabla_exeva_nueva(tabla_exeva_nueva)

    tabla_exeva_vieja = soup.select_one("#tbldocumentos") or soup.select_one("table.tbldocumentos") or soup.find(
        "table", id="tbldocumentos"
    )
    if tabla_exeva_vieja:
        return _parse_tabla_exeva_vieja(tabla_exeva_vieja)

    tabla_pac = soup.select_one("table.tabla-dinamica_pac") or soup.select_one("table.tabla_dinamica_pac")
    if tabla_pac:
        return _parse_tabla_pac(tabla_pac)

    tabla_pci = soup.select_one("#pci") or soup.select_one("table.pci") or soup.select_one(
        "table.tabla-dinamica_pci"
    ) or soup.select_one("table.tabla_dinamica_pci")
    if tabla_pci:
        return _parse_tabla_pci(tabla_pci)

    tabla_reunion = soup.select_one("table.tabla-dinamica_reunion") or soup.select_one(
        "table.tabla_dinamica_reunion"
    ) or soup.find("table", id="example23")
    if tabla_reunion:
        return _parse_tabla_reunion_a86(tabla_reunion)

    tabla_rec = soup.find("table", id="table-expediente-recurso") or soup.select_one("table#table-expediente-recurso")
    if tabla_rec:
        return _parse_tabla_recursos(tabla_rec)

    _log(log, "[EX] No se reconoció ninguna tabla de documentos en el HTML.")
    return []


# -----------------------------------------------------------------------------
# Descarga (mantiene contrato)
# -----------------------------------------------------------------------------

def _download_binary(session: requests.Session, url: str, out_path: Path) -> Tuple[bool, Path]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with session.get(url, stream=True, timeout=40, verify=False) as r:
            if r.status_code != 200:
                return False, out_path
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True, out_path
    except Exception:
        return False, out_path


def _process_doc(
    session: requests.Session,
    d: dict,
    base_dir: Path,
    code: str,
    log: Optional[Callable[[str], None]],
    overwrite: bool = False,
) -> bool:
    ex_dir = base_dir / code
    files_root = ex_dir / "files"

    if not overwrite:
        ruta_prev = d.get("ruta")
        if ruta_prev:
            try:
                p_str = str(ruta_prev).replace("/", os.sep).replace("\\", os.sep)
                p_prev = Path(p_str)
                if not p_prev.is_absolute():
                    p_prev = (base_dir / p_prev).resolve()
                if p_prev.is_file():
                    return True
            except Exception:
                pass

    folio = str(d.get("folio") or "").strip()
    titulo = str(d.get("titulo") or "").strip()
    n = str(d.get("n") or d.get("num_doc") or "").strip() or "0"
    url = d.get("URL_documento") or d.get("url") or ""
    if not url:
        d["error_descarga"] = True
        return False

    folder_name = _doc_folder_name(n)
    out_dir = files_root / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = _sanitize_filename("_".join([p for p in [n, folio, titulo] if p])) or "documento"
    ext_url = _url_extension(url)
    final_ext = ext_url or ".bin"
    if ext_url in ("", ".php") or "documento.php" in url.lower():
        final_ext = ".pdf"

    saved_path = out_dir / (base_name + final_ext)

    _log(log, f"[Worker] Descargando: {titulo}")
    ok, saved_path = _download_binary(session, url, saved_path)

    if ok:
        try:
            rel = saved_path.resolve().relative_to(base_dir.resolve())
        except Exception:
            rel = Path(code) / "files" / folder_name / saved_path.name

        d["ruta"] = str(rel).replace("\\", "/").lstrip("/")
        d.pop("error_descarga", None)
        return True

    d["error_descarga"] = True
    return False


def _download_documents(project_id: str, code: str, ex_data: dict, log: Optional[Callable[[str], None]] = None) -> None:
    documentos = ex_data.get(code, {}).get("documentos", []) if isinstance(ex_data, dict) else []
    total = len(documentos)
    if total == 0:
        return

    base_dir = Path(os.getcwd()) / "Ebook" / project_id
    base_dir.mkdir(parents=True, exist_ok=True)

    _log(log, f"[EX] Iniciando descarga de {total} documentos...")
    session = _make_session()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_process_doc, session, d, base_dir, code, log, False) for d in documentos]
        done = 0
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception:
                pass
            done += 1
            if done % 10 == 0 or done == total:
                _log(log, f"[EX] Descarga {done}/{total}")

    _log(log, "[EX] Descarga finalizada.")


# -----------------------------------------------------------------------------
# Extracción
# -----------------------------------------------------------------------------

def _extract_expediente(
    code: str,
    idp: Optional[str],
    idr: Optional[str] = None,
    log: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    idp = (idp or "").strip()
    idr = (idr or "").strip()

    template_code, embedded_idr = _normalize_code(code)
    if not idr and embedded_idr:
        idr = embedded_idr

    templates = EX_URL_TEMPLATES.get(template_code, [])
    if not templates:
        _log(log, f"[EX] No hay templates configuradas para {template_code} (code='{code}').")
        return {"IDP": idp, "IDR": idr, code: {"documentos": [], "summary": {"total": 0, "format_counts": {}}}}

    session = _make_session()
    documentos: List[Dict[str, Any]] = []

    for tpl in templates:
        if "{IDR}" in tpl:
            if not idr:
                _log(log, f"[{code}] Falta IDR para construir URL (template requiere IDR).")
                continue
            url = tpl.format(IDR=idr, IDP=idp)
        else:
            if not idp:
                _log(log, f"[{code}] Falta IDP para construir URL (template requiere IDP).")
                continue
            url = tpl.format(IDP=idp, IDR=idr)

        _log(log, f"[{code}] Consultando: {url}")
        status, body = _http_get(session, url, timeout=25)

        if status != 200 or not body:
            _log(log, f"[{code}] HTTP {status} (sin contenido útil) para '{url}'")
            continue

        documentos = _parse_documentos_from_html(body, log)
        if documentos:
            break

        _log(log, f"[{code}] Respuesta sin documentos desde '{url}', probando siguiente plantilla.")

    if not documentos:
        return {"IDP": idp, "IDR": idr, code: {"documentos": [], "summary": {"total": 0, "format_counts": {}}}}

    conteo = Counter(doc.get("formato", "sin formato") for doc in documentos)
    return {
        "IDP": idp,
        "IDR": idr,
        code: {"documentos": documentos, "summary": {"total": len(documentos), "format_counts": dict(conteo)}},
    }


# -----------------------------------------------------------------------------
# Persistencia (mantiene contrato)
# -----------------------------------------------------------------------------

def _save_ex_data(idp: str, code: str, ex_data: dict, new_status: str, log: Callable[[str], None]):
    base_folder = os.path.join(os.getcwd(), "Ebook", idp)
    base_json_path = os.path.join(base_folder, f"{idp}_fetch.json")
    ex_folder = os.path.join(base_folder, code)
    ex_json_path = os.path.join(ex_folder, f"{idp}_{code}.json")

    os.makedirs(ex_folder, exist_ok=True)

    try:
        with open(ex_json_path, "w", encoding="utf-8") as f:
            json.dump(ex_data, f, indent=2, ensure_ascii=False)
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
                json.dump(data, f, indent=2, ensure_ascii=False)

            log(f"💾 Progreso {code}: Paso 0 ({new_status})")
        else:
            log(f"⚠️ No se encontró el código {code} en {base_json_path} para actualizar estado.")
    except Exception as exc:
        log(f"❌ Error actualizando estado en {base_json_path}: {exc}")


# -----------------------------------------------------------------------------
# Integración con la app
# -----------------------------------------------------------------------------

class ExFetchWorker(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, dict)

    def __init__(self, project_id: str, code: str, target_id: str):
        super().__init__()
        self.project_id = str(project_id)
        self.code = str(code)
        self.target_id = str(target_id)

    @pyqtSlot()
    def run(self):
        self.log_signal.emit(f"🔎 Extracción de {self.code} para ID {self.target_id}...")
        success = False
        result_data: Dict[str, Any] = {}

        try:
            template_code, embedded_idr = _normalize_code(self.code)

            if template_code in ("EXPCI", "EXA86", "EXREC"):
                idr = embedded_idr or self.target_id
                ex_data = _extract_expediente(self.code, idp=self.project_id, idr=idr, log=self.log_signal.emit)
            else:
                ex_data = _extract_expediente(self.code, idp=self.target_id, idr=None, log=self.log_signal.emit)

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


class ExRetryWorker(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, dict)

    def __init__(self, project_id: str, code: str, doc_data: dict):
        super().__init__()
        self.project_id = str(project_id)
        self.code = str(code)
        self.doc_data = doc_data or {}

    @pyqtSlot()
    def run(self):
        success = False
        doc_label = self.doc_data.get("titulo") or self.doc_data.get("n") or "documento"
        self.log_signal.emit(f"🔁 Reintentando descarga de {doc_label}...")

        try:
            base_dir = Path(os.getcwd()) / "Ebook" / self.project_id
            session = _make_session()
            success = _process_doc(
                session,
                self.doc_data,
                base_dir,
                self.code,
                log=self.log_signal.emit,
                overwrite=True,
            )
            if success:
                self.log_signal.emit("✅ Descarga reintentada correctamente.")
            else:
                self.log_signal.emit("⚠️ No se pudo reintentar la descarga.")
        except Exception as exc:
            self.log_signal.emit(f"❌ Error durante el reintento: {exc}")
            success = False

        self.finished_signal.emit(success, self.doc_data)


class ExFetchController(QObject):
    extraction_started = pyqtSignal()
    extraction_finished = pyqtSignal(bool, dict)
    log_requested = pyqtSignal(str)

    retry_log_requested = pyqtSignal(str)
    retry_started = pyqtSignal()
    retry_finished = pyqtSignal(bool, dict)
    fetch_finished = pyqtSignal(bool, dict)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.thread: Optional[QThread] = None
        self.worker: Optional[ExFetchWorker] = None

        self.retry_thread: Optional[QThread] = None
        self.retry_worker: Optional[ExRetryWorker] = None
        self._fetch_finished_dispatched = False
        self._retry_finished_dispatched = False

    def start_fetch(self, project_id: str, code: str, target_id: str) -> None:
        if self.thread is not None:
            return

        self.extraction_started.emit()
        self._fetch_finished_dispatched = False
        self.thread = QThread()
        self.worker = ExFetchWorker(project_id, code, target_id)
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

    def start_extraction(self, project_id: str, code: str, target_id: str) -> None:
        self.start_fetch(project_id, code, target_id)

    def _reset_thread_state(self) -> None:
        self.thread = None
        self.worker = None

    @pyqtSlot(bool, dict)
    def _on_finished(self, success: bool, doc_data: dict) -> None:
        self._fetch_finished_dispatched = True
        self.fetch_finished.emit(success, doc_data)
        self.extraction_finished.emit(success, doc_data)

    @pyqtSlot()
    def _on_thread_finished(self) -> None:
        if not self._fetch_finished_dispatched:
            self.fetch_finished.emit(False, {})
            self.extraction_finished.emit(False, {})

    def start_retry(self, project_id: str, code: str, doc_data: dict) -> None:
        if self.retry_thread is not None:
            return

        self.retry_started.emit()
        self._retry_finished_dispatched = False
        self.retry_thread = QThread()
        self.retry_worker = ExRetryWorker(project_id, code, doc_data)
        self.retry_worker.moveToThread(self.retry_thread)

        self.retry_thread.started.connect(self.retry_worker.run)
        self.retry_worker.log_signal.connect(self.retry_log_requested.emit)
        self.retry_worker.log_signal.connect(self.log_requested.emit)
        self.retry_worker.finished_signal.connect(self._on_retry_finished)
        self.retry_thread.finished.connect(self._on_retry_thread_finished)

        self.retry_worker.finished_signal.connect(self.retry_thread.quit)
        self.retry_worker.finished_signal.connect(self.retry_worker.deleteLater)
        self.retry_thread.finished.connect(self.retry_thread.deleteLater)
        self.retry_thread.finished.connect(self._reset_retry_thread_state)

        self.retry_thread.start()

    def retry_download(self, project_id: str, code: str, doc_data: dict) -> None:
        self.start_retry(project_id, code, doc_data)

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
