"""Generador de PDFs para Antecedentes Generales usando ReportLab."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from reportlab.lib import colors
from reportlab.lib.pagesizes import inch
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import mm
from reportlab.platypus import (  # type: ignore
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class AntgenCompiler(QObject):
    """Compila los datos de Antecedentes Generales en un PDF con estilo formal."""

    log_requested = pyqtSignal(str)
    compilation_started = pyqtSignal()
    compilation_finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_size = (8.5 * inch, 13 * inch)  # Tamaño legal chileno

    @pyqtSlot(str, dict)
    def compile_pdf(self, project_id: str, antgen_payload: dict | None = None):
        self.compilation_started.emit()

        try:
            payload = antgen_payload or self._load_antgen_payload(project_id)
            if not payload:
                raise ValueError("No hay datos de Antecedentes Generales para compilar.")

            output_path = self._build_pdf(project_id, payload)
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

    def _build_pdf(self, project_id: str, antgen: Dict[str, Any]) -> str:
        base_folder = os.path.join(os.getcwd(), "Ebook", project_id)
        os.makedirs(base_folder, exist_ok=True)
        output_path = os.path.join(base_folder, "ANTGEN_compilado.pdf")

        styles = self._build_styles()
        story: List[Any] = []

        self._add_cover(story, styles, project_id, antgen)
        self._add_registro_estados(story, styles, antgen.get("registro_estados", []))
        self._add_datos_generales(story, styles, antgen)
        self._add_contacto(story, styles, antgen)
        self._add_permisos(story, styles, antgen.get("permisos_ambientales", []))
        self._add_descripcion(story, styles, antgen)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=self._page_size,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=f"ANTGEN_{project_id}",
        )

        doc.build(story, onLaterPages=self._add_page_number(styles))
        return output_path

    def _build_styles(self) -> StyleSheet1:
        primary = colors.HexColor("#1F3A93")
        accent = colors.HexColor("#4B6D88")
        gray = colors.HexColor("#555555")

        styles = StyleSheet1()
        styles.add(ParagraphStyle(name="TitleCover", fontName="Helvetica-Bold", fontSize=20, textColor=primary, spaceAfter=12))
        styles.add(ParagraphStyle(name="SubtitleCover", fontName="Helvetica", fontSize=11, textColor=gray, spaceAfter=6))
        styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=14, textColor=primary, spaceBefore=8, spaceAfter=6))
        styles.add(ParagraphStyle(name="Subsection", fontName="Helvetica-Bold", fontSize=12, textColor=accent, spaceBefore=6, spaceAfter=4))
        styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=13, textColor=colors.black, spaceAfter=4))
        styles.add(ParagraphStyle(name="Muted", fontName="Helvetica", fontSize=10, leading=13, textColor=colors.HexColor("#777777"), spaceAfter=4))
        styles.add(ParagraphStyle(name="TableHeader", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white, alignment=1))
        styles.add(ParagraphStyle(name="TableBody", fontName="Helvetica", fontSize=10, textColor=colors.black))
        return styles

    def _add_cover(self, story: List[Any], styles: StyleSheet1, project_id: str, antgen: Dict[str, Any]):
        logo_path = os.path.join(os.getcwd(), "assets", "images", "Logo.png")
        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=120, height=80))
        story.append(Spacer(1, 30))

        story.append(Paragraph("ANTECEDENTES GENERALES", styles["TitleCover"]))
        story.append(Paragraph("Informe del expediente", styles["SubtitleCover"]))
        story.append(Spacer(1, 12))

        meta_rows = [
            ("Nombre del proyecto", antgen.get("nombre_proyecto", "No informado")),
            ("Tipo de expediente", "Antecedentes Generales"),
            ("Forma de ingreso", antgen.get("forma_presentacion", "No indicada")),
            ("Estado", antgen.get("estado_actual", "No indicado")),
            ("ID del proyecto", project_id),
            ("Fecha de generación", datetime.now().strftime("%d/%m/%Y")),
        ]

        table = Table(meta_rows, hAlign="LEFT", colWidths=[140, 320])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6EBF1")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1F3A93")),
            ("LINEBELOW", (0, 0), (-1, -1), colors.HexColor("#D3D9E2")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(PageBreak())

    def _add_registro_estados(self, story: List[Any], styles: StyleSheet1, registros: Iterable[Dict[str, Any]]):
        story.append(Paragraph("Registro de estados", styles["Section"]))

        headers = [Paragraph("Estado", styles["TableHeader"]), Paragraph("Documento", styles["TableHeader"]), Paragraph("Número", styles["TableHeader"]), Paragraph("Fecha", styles["TableHeader"]), Paragraph("Autor", styles["TableHeader"])]
        rows = [headers]
        for row in registros or []:
            rows.append([
                Paragraph(str(row.get("estado", "")), styles["TableBody"]),
                Paragraph(str(row.get("documento", "")), styles["TableBody"]),
                Paragraph(str(row.get("numero", "")), styles["TableBody"]),
                Paragraph(str(row.get("fecha", "")), styles["TableBody"]),
                Paragraph(str(row.get("autor", "")), styles["TableBody"]),
            ])

        if len(rows) == 1:
            rows.append([Paragraph("Sin registro de estados.", styles["Muted"])] + ["", "", "", ""])

        self._style_table(rows, story)
        story.append(Spacer(1, 12))
        story.append(PageBreak())

    def _add_datos_generales(self, story: List[Any], styles: StyleSheet1, antgen: Dict[str, Any]):
        story.append(Paragraph("Antecedentes generales", styles["Section"]))
        campos = [
            ("Tipo de proyecto", antgen.get("tipo_proyecto", "No indicado")),
            ("Monto de inversión", antgen.get("monto_inversion", "No indicado")),
            ("Estado actual", antgen.get("estado_actual", "No indicado")),
            ("Encargado/a evaluación", antgen.get("encargado", "No indicado")),
        ]

        for label, value in campos:
            story.append(Paragraph(f"<b>{label}:</b> {self._format_text(value)}", styles["Body"]))

        story.append(Spacer(1, 10))
        story.append(PageBreak())

    def _add_contacto(self, story: List[Any], styles: StyleSheet1, antgen: Dict[str, Any]):
        blocks = [
            ("Información del titular", antgen.get("titular", {})),
            ("Información del representante legal", antgen.get("representante_legal", {})),
            ("Consultora ambiental", antgen.get("consultora", {})),
        ]

        for title, data in blocks:
            story.append(Paragraph(title, styles["Subsection"]))
            story.append(Paragraph(self._format_contact_block(data), styles["Body"]))
            story.append(Spacer(1, 6))

        story.append(PageBreak())

    def _add_permisos(self, story: List[Any], styles: StyleSheet1, permisos: Iterable[Dict[str, Any]]):
        story.append(Paragraph("Permisos Ambientales Asociados", styles["Section"]))

        headers = [Paragraph("Artículo", styles["TableHeader"]), Paragraph("Nombre", styles["TableHeader"]), Paragraph("Tipo", styles["TableHeader"]), Paragraph("Certificado", styles["TableHeader"])]
        rows = [headers]
        for row in permisos or []:
            rows.append([
                Paragraph(str(row.get("articulo", "")), styles["TableBody"]),
                Paragraph(str(row.get("nombre", "")), styles["TableBody"]),
                Paragraph(str(row.get("tipo", "")), styles["TableBody"]),
                Paragraph(str(row.get("certificado", "")), styles["TableBody"]),
            ])

        if len(rows) == 1:
            rows.append([Paragraph("No cuenta con Permisos Ambientales Sectoriales", styles["Muted"])] + ["", "", ""])

        self._style_table(rows, story)
        story.append(Spacer(1, 10))
        story.append(PageBreak())

    def _add_descripcion(self, story: List[Any], styles: StyleSheet1, antgen: Dict[str, Any]):
        story.append(Paragraph("Descripción del proyecto", styles["Section"]))
        descripcion = self._split_paragraphs(antgen.get("descripcion_proyecto", ""))
        if descripcion:
            for p in descripcion:
                story.append(Paragraph(p, styles["Body"]))
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("Sin información declarada.", styles["Muted"]))

        story.append(Spacer(1, 10))

        story.append(Paragraph("Objetivo del proyecto", styles["Section"]))
        objetivo = self._split_paragraphs(antgen.get("objetivo_proyecto", ""))
        if objetivo:
            for p in objetivo:
                story.append(Paragraph(p, styles["Body"]))
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("Sin información declarada.", styles["Muted"]))

    def _style_table(self, rows: List[List[Any]], story: List[Any]):
        table = Table(rows, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A93")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D3D9E2")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1F3A93")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    def _format_text(self, text: Any) -> str:
        if text is None:
            return "No indicado"
        return str(text).strip() or "No indicado"

    def _format_contact_block(self, data: Dict[str, Any] | str) -> str:
        if isinstance(data, str):
            value = data.strip()
            return value or "Sin información declarada."

        if not isinstance(data, dict) or not data:
            return "Sin información declarada."

        parts = []
        for label, key in [
            ("Nombre", "nombre"),
            ("Domicilio", "domicilio"),
            ("Ciudad", "ciudad"),
            ("Teléfono", "telefono"),
            ("Fax", "fax"),
            ("Correo", "email"),
        ]:
            if data.get(key):
                parts.append(f"<b>{label}:</b> {self._format_text(data[key])}")

        return "<br/>".join(parts) or "Sin información declarada."

    def _split_paragraphs(self, text: Any) -> List[str]:
        if not text:
            return []
        return [segment.strip() for segment in str(text).split("\n") if segment.strip()]

    def _add_page_number(self, styles: StyleSheet1):
        def _callback(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#777777"))
            page_number = canvas.getPageNumber()
            canvas.drawRightString(self._page_size[0] - 18 * mm, 12 * mm, f"Página {page_number}")
            canvas.restoreState()

        return _callback

