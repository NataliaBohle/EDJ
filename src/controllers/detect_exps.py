# fetch_exp.py
# Detecta expedientes (incluye EXPCI/EXA86 por IDR y Recursos como REC_{idr} usando EXREC para extracción)

import os
import json
import requests
import time
import re
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, QThread, pyqtSignal

# --- CONFIGURACIÓN BASE ---
EXPEDIENTES_FRAGMENTS = {
    "ANTGEN": "fichaPrincipal.php",
    "EXEVA": ["xhr_expediente.php", "xhr_documentos.php"],
    "EXPAC": "xhr_documentos_pac.php",
    "EXPCI": "xhr_pci.php",
    "EXA86": "xhr_pci_reunion.php",
    "EXSYF": "seguimiento/xhr_principal.php",
    # EXREC se maneja dinámicamente (REC_{idr} pero se extrae con fetch_code="EXREC")
    "EXSAN": "sanciones/xhr_principal.php",
    "EXREV": "revisionRCA/principal.php",
    #"CAL": "newPlazos.php", no habilitado aún
}

UI_TITLES = {
    "ANTGEN": "Antecedentes Generales",
    "EXEVA": "Evaluación Ambiental",
    "EXPAC": "Participación Ciudadana",
    "EXPCI": "Consulta Indígena",
    "EXA86": "Reunión con GHPPI (Art.86)",
    "EXSYF": "Seguimiento y Fiscalizaciones",
    "EXSAN": "Sanciones",
    "EXREV": "Revisión de RCA",
    "CAL": "Calendario del proceso",
    "EXREC": "Recursos",
}


class FetchWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, int, str)

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "EDJ5/1.0 (+UI)"})

    # ---------------------------
    # Helpers de detección IDR
    # ---------------------------
    def _extraer_idr_desde_onclick(self, onclick: str) -> str | None:
        if not onclick:
            return None
        m = re.search(r"id_expediente=(\d+)", onclick)
        return m.group(1) if m else None

    def _extraer_id_exa86(self, html: str) -> str | None:
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")

        # onclick
        for tag in soup.find_all(onclick=True):
            onclick = tag.get("onclick", "")
            if "xhr_pci_reunion.php" in onclick:
                idr = self._extraer_idr_desde_onclick(onclick)
                if idr:
                    return idr

        # href
        for tag in soup.find_all(href=True):
            href = tag.get("href", "")
            if "xhr_pci_reunion.php" in href:
                m = re.search(r"id_expediente=(\d+)", href)
                if m:
                    return m.group(1)

        return None

    def _extraer_id_expci(self, html: str) -> str | None:
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")

        # onclick
        for tag in soup.find_all(onclick=True):
            onclick = tag.get("onclick", "")
            if "xhr_pci.php" in onclick:
                idr = self._extraer_idr_desde_onclick(onclick)
                if idr:
                    return idr

        # href
        for tag in soup.find_all(href=True):
            href = tag.get("href", "")
            if "xhr_pci.php" in href:
                m = re.search(r"id_expediente=(\d+)", href)
                if m:
                    return m.group(1)

        return None

    # ---------------------------
    # HTTP
    # ---------------------------
    def _fetch_html(self, url: str) -> str | None:
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200 and r.text:
                return r.text
        except Exception:
            pass
        return None

    # ---------------------------
    # Recursos: lista de {idr, fecha, tipo, estado}
    # ---------------------------
    def _obtener_recursos_con_id(self, idp: str) -> list[dict]:
        urls = [
            f"https://seia.sea.gob.cl/expediente/expedientesRecursos.php?modo=ficha&id_expediente={idp}",
            f"https://seia.sea.gob.cl/recursos/xhr_principal.php?modo=ficha&id_expediente={idp}",
            f"https://seia.sea.gob.cl/expediente/expedientesRecursos.php?id_expediente={idp}",
        ]

        soup = None
        for url in urls:
            html = self._fetch_html(url)
            if not html:
                continue
            tmp = BeautifulSoup(html, "html.parser")
            if (
                tmp.find("table", id="tbldocumentos")
                or tmp.select_one("table.dataTable")
                or "Número de registros" in tmp.get_text()
            ):
                soup = tmp
                break

        if not soup:
            return []

        recursos: list[dict] = []
        tabla = (
            soup.find("table", id="tbldocumentos")
            or soup.select_one("table.table-striped.tabla-dinamica")
            or soup.select_one("table.dataTable")
        )

        if not tabla:
            return []

        tbody = tabla.find("tbody")
        filas = tbody.find_all("tr") if tbody else tabla.find_all("tr")

        for fila in filas:
            if fila.find("th"):
                continue

            c = fila.find_all("td")
            if len(c) < 3:
                continue

            fecha = c[0].get_text(strip=True)
            col_tipo = c[1]
            a_tag = col_tipo.find("a", href=True)
            tipo = a_tag.get_text(strip=True) if a_tag else "Recurso"
            href = a_tag["href"] if a_tag else ""

            idr = None
            if href:
                m = re.search(r"id_expediente=(\d+)", href)
                if m:
                    idr = m.group(1)

            if not idr:
                for td in c:
                    btn = td.find("button", onclick=True)
                    if btn:
                        idr_btn = self._extraer_idr_desde_onclick(btn.get("onclick", ""))
                        if idr_btn:
                            idr = idr_btn
                            break

            estado = c[2].get_text(strip=True)

            if idr:
                recursos.append(
                    {
                        "idr": idr,
                        "fecha": fecha,
                        "tipo": tipo,
                        "estado": estado,
                    }
                )

        return recursos

    # ---------------------------
    # RUN
    # ---------------------------
    def run(self):
        idp = self.project_id
        self.log_signal.emit(f"🔍 Consultando SEIA para ID: {idp}...")

        found_count = 0
        expedientes_data: dict[str, dict] = {}

        # 1) Base: ficha principal
        url_base = f"https://seia.sea.gob.cl/expediente/expedientesEvaluacion.php?modo=ficha&id_expediente={idp}"
        html_main = self._fetch_html(url_base)

        exa86_idr = None
        pci_idr = None

        if html_main:
            self.log_signal.emit("Analizando secciones generales...")
            html_lower = html_main.lower()

            # Detectar IDR para EXA86 / EXPCI (si están presentes)
            exa86_idr = self._extraer_id_exa86(html_main)
            pci_idr = self._extraer_id_expci(html_main)

            for code, fragments in EXPEDIENTES_FRAGMENTS.items():
                fragment_list = fragments if isinstance(fragments, (list, tuple, set)) else [fragments]
                is_present = any(fragment.lower() in html_lower for fragment in fragment_list)
                if not is_present:
                    continue

                found_count += 1

                # default: se extrae por IDP
                target_id = idp
                id_mode = "idp"

                # EXPCI/EXA86: si hay IDR, se extrae por IDR
                if code == "EXPCI" and pci_idr:
                    target_id = pci_idr
                    id_mode = "idr"
                elif code == "EXA86" and exa86_idr:
                    target_id = exa86_idr
                    id_mode = "idr"

                expedientes_data[code] = {
                    "status": "detectado",
                    "titulo": UI_TITLES.get(code, code),
                    "tipo": "base",
                    "step_index": 0,
                    "step_status": "detectado",
                    # CLAVE: lo que necesita el extractor
                    "fetch_code": code,      # plantilla a usar en fetch_ex
                    "target_id": target_id,  # idp o idr según corresponda
                    "id_mode": id_mode,      # "idp" | "idr"
                }

                # mantener idr explícito (opcional)
                if id_mode == "idr":
                    expedientes_data[code]["idr"] = target_id

        else:
            self.log_signal.emit("⚠️ No se pudo cargar la ficha principal (posible error de conexión).")

        # 2) Recursos (siempre intentar)
        self.log_signal.emit("🔎 Buscando recursos asociados...")
        recursos_found = self._obtener_recursos_con_id(idp)

        if recursos_found:
            self.log_signal.emit(f"   ↳ ¡Éxito! Se encontraron {len(recursos_found)} recursos.")
            for res in recursos_found:
                found_count += 1
                unique_key = f"REC_{res['idr']}"
                titulo_dinamico = f"{res['tipo']} ({res['fecha']})"

                # IMPORTANTE:
                # - La clave en el JSON es única (REC_{idr}) para carpetas/UI
                # - Pero el extractor debe usar la plantilla "EXREC"
                expedientes_data[unique_key] = {
                    "status": "detectado",
                    "titulo": titulo_dinamico,
                    "tipo": "recurso",
                    "idr": res["idr"],
                    "estado_sea": res["estado"],
                    "step_index": 0,
                    "step_status": "detectado",
                    # CLAVE: lo que necesita el extractor
                    "fetch_code": "EXREC",
                    "target_id": res["idr"],
                    "id_mode": "idr",
                }
        else:
            self.log_signal.emit("   ↳ No se detectaron recursos activos.")

        # 3) Guardado
        if found_count == 0:
            self.log_signal.emit("❌ No se encontró nada (ni ficha base ni recursos).")
            self.finished_signal.emit(True, 0, idp)
            return

        try:
            base_folder = os.path.join(os.getcwd(), "Ebook", idp)
            os.makedirs(base_folder, exist_ok=True)

            payload = {
                "id": idp,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {"found": found_count},
                "expedientes": expedientes_data,
            }

            json_path = os.path.join(base_folder, f"{idp}_fetch.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)

            self.log_signal.emit(f"✅ Análisis finalizado. Total secciones: {found_count}")
            self.finished_signal.emit(True, found_count, idp)

        except Exception as e:
            self.log_signal.emit(f"❌ Error al guardar JSON: {e}")
            self.finished_signal.emit(False, 0, idp)


class FetchExp(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.log = self.main_window.log_screen
        self.page_new = self.main_window.page_new_ebook
        self.page_new.form_id.btn_start.clicked.connect(self.start_process)

    def start_process(self):
        project_id = self.page_new.form_id.input_id.text().strip()
        if not project_id.isdigit():
            self.log.add_log("⚠️ ID inválido.")
            return

        self.page_new.form_id.btn_start.setEnabled(False)
        self.page_new.form_id.btn_start.setText("Buscando...")

        self.worker = FetchWorker(project_id)
        self.worker.log_signal.connect(self.log.add_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, found_count, project_id):
        self.page_new.form_id.btn_start.setEnabled(True)
        self.page_new.form_id.btn_start.setText("Iniciar")
        self.page_new.form_id.input_id.clear()

        from src.views.components.alert import Alert

        if not success and found_count == 0:
            alert = Alert(self.main_window, "Error", "No se pudo conectar o no se encontraron datos.")
            alert.exec()
            return

        if found_count == 0:
            msg = f"No se han encontrado expedientes para la ID {project_id}."
            alert = Alert(self.main_window, "Sin Resultados", msg, alert_type="warning")
            alert.exec()
        else:
            self.log.add_log(f"🚀 Abriendo vista de proyecto para {project_id}")
            self.main_window.sidebar.clear()
            self.main_window.sidebar.add_option(f"Proyecto Activo\nID {project_id}")
            self.main_window.show_project_view(project_id)
