import json
import os
from datetime import datetime
from html import escape
from string import Template
from typing import Any, Dict, List

import fitz  # PyMuPDF
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class AntgenCompiler(QObject):
    """Compila los datos de Antecedentes Generales en un PDF."""

    log_requested = pyqtSignal(str)
    compilation_started = pyqtSignal()
    compilation_finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_size = (612, 936)  # 8.5in x 13in at 72 dpi (Legal chileno)

    @pyqtSlot(str, dict)
    def compile_pdf(self, project_id: str, antgen_payload: dict | None = None):
        self.compilation_started.emit()

        try:
            payload = antgen_payload or self._load_antgen_payload(project_id)
            if not payload:
                raise ValueError("No hay datos de Antecedentes Generales para compilar.")

            sections = self._build_sections(project_id, payload)
            output_path = self._write_pdf(project_id, sections)
            self.log_requested.emit(f"✅ PDF generado: {output_path}")
            self.compilation_finished.emit(True, output_path)
        except Exception as exc:  # noqa: BLE001
            self.log_requested.emit(f"❌ Error al compilar PDF: {exc}")
            self.compilation_finished.emit(False, "")

    def _load_antgen_payload(self, project_id: str) -> Dict[str, Any]:
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        json_path = os.path.join(base_folder, f"{project_id}_fetch.json")

        if not os.path.exists(json_path):
            return {}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("expedientes", {}).get("ANTGEN", {}).get("ANTGEN_DATA", {})

    def _write_pdf(self, project_id: str, sections: Dict[str, str]) -> str:
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        os.makedirs(base_folder, exist_ok=True)
        output_path = os.path.join(base_folder, "ANTGEN_compilado.pdf")

        doc = fitz.open()
        rect = fitz.Rect(36, 36, self._page_size[0] - 36, self._page_size[1] - 36)

        for key in ("cover", "body"):
            page = doc.new_page(width=self._page_size[0], height=self._page_size[1])
            page.insert_htmlbox(rect, sections[key])

        doc.save(output_path)
        doc.close()
        return output_path

    def _build_sections(self, project_id: str, antgen: Dict[str, Any]) -> Dict[str, str]:
        assets_path = os.path.join(os.getcwd(), "assets", "templates")
        styles_path = os.path.join(assets_path, "pdf_styles.css")
        cover_path = os.path.join(assets_path, "cover_antgen.html")
        template_path = os.path.join(assets_path, "antgen_template.html")

        with open(styles_path, "r", encoding="utf-8") as f:
            styles = f.read()
        with open(cover_path, "r", encoding="utf-8") as f:
            cover_template = Template(f.read())
        with open(template_path, "r", encoding="utf-8") as f:
            body_template = Template(f.read())

        info = self._extract_basic_info(project_id, antgen)
        pas_rows = self._render_pas_table(antgen.get("permisos_ambientales", []))
        estados_rows = self._render_estados_table(antgen.get("registro_estados", []))

        cover_html = self._wrap_html(cover_template.safe_substitute(info), styles)
        body_html = self._wrap_html(body_template.safe_substitute({
            "project_name": escape(info.get("project_name", "")),
            "project_id": escape(info.get("project_id", "")),
            "tipo_proyecto": escape(antgen.get("tipo_proyecto", "No indicado")),
            "forma_presentacion": escape(antgen.get("forma_presentacion", "No indicada")),
            "monto_inversion": escape(antgen.get("monto_inversion", "No indicado")),
            "estado_actual": escape(antgen.get("estado_actual", "No indicado")),
            "encargado": escape(antgen.get("encargado", "")),
            "descripcion_proyecto": self._format_paragraph(antgen.get("descripcion_proyecto", "")),
            "objetivo_proyecto": self._format_paragraph(antgen.get("objetivo_proyecto", "")),
            "titular": self._format_contact_block(antgen.get("titular", {})),
            "representante_legal": self._format_contact_block(antgen.get("representante_legal", {})),
            "consultora": self._format_contact_block(antgen.get("consultora", {})),
            "permisos_rows": pas_rows,
            "registro_rows": estados_rows,
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }), styles)

        return {
            "cover": cover_html,
            "body": body_html,
        }

    def _wrap_html(self, content: str, styles: str) -> str:
        return (
            "<html><head><meta charset='utf-8'><style>"
            + styles +
            "</style></head><body class='pdf-document'>" + content + "</body></html>"
        )

    def _extract_basic_info(self, project_id: str, antgen: Dict[str, Any]) -> Dict[str, str]:
        logo_path = os.path.join(os.getcwd(), "assets", "images", "Logo.png")
        return {
            "project_name": antgen.get("nombre_proyecto", "Proyecto sin título"),
            "forma_ingreso": antgen.get("forma_presentacion", "No informado"),
            "estado": antgen.get("estado_actual", "Detectado"),
            "expediente_tipo": "Antecedentes Generales",
            "project_id": project_id,
            "logo_path": logo_path,
            "generation_date": datetime.now().strftime("%d/%m/%Y"),
        }

    def _format_paragraph(self, text: str) -> str:
        if not text:
            return "<p class='text-muted'>Sin información declarada.</p>"

        sanitized = escape(str(text)).replace("\n", "<br>")
        return f"<p class='text-base'>{sanitized}</p>"

    def _format_contact_block(self, data: Dict[str, str] | str) -> str:
        if isinstance(data, str):
            cleaned = data.strip()
            if cleaned:
                return f"<p class='text-base'>{escape(cleaned).replace('\n', '<br>')}</p>"
            return "<p class='text-muted'>Sin información declarada.</p>"

        if not isinstance(data, dict) or not data:
            return "<p class='text-muted'>Sin información declarada.</p>"

        lines: List[str] = []
        if data.get("nombre"):
            lines.append(f"<strong>Nombre:</strong> {escape(str(data['nombre']))}")
        if data.get("domicilio"):
            lines.append(f"<strong>Domicilio:</strong> {escape(str(data['domicilio']))}")
        if data.get("email"):
            lines.append(f"<strong>Correo:</strong> {escape(str(data['email']))}")

        return "<p class='text-base'>" + "<br>".join(lines) + "</p>"

    def _render_pas_table(self, rows: List[Dict[str, str]]) -> str:
        if not rows:
            return "<tr><td colspan='4' class='text-muted'>Sin permisos declarados.</td></tr>"

        rendered = []
        for row in rows:
            rendered.append(
                "<tr>"
                f"<td>{escape(str(row.get('articulo', '')))}</td>"
                f"<td>{escape(str(row.get('nombre', '')))}</td>"
                f"<td>{escape(str(row.get('tipo', '')))}</td>"
                f"<td>{escape(str(row.get('certificado', '')))}</td>"
                "</tr>"
            )
        return "".join(rendered)

    def _render_estados_table(self, rows: List[Dict[str, str]]) -> str:
        if not rows:
            return "<tr><td colspan='5' class='text-muted'>Sin registro de estados.</td></tr>"

        rendered = []
        for row in rows:
            rendered.append(
                "<tr>"
                f"<td>{escape(str(row.get('estado', '')))}</td>"
                f"<td>{escape(str(row.get('documento', '')))}</td>"
                f"<td>{escape(str(row.get('numero', '')))}</td>"
                f"<td>{escape(str(row.get('fecha', '')))}</td>"
                f"<td>{escape(str(row.get('autor', '')))}</td>"
                "</tr>"
            )
        return "".join(rendered)

