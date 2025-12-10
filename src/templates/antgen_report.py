import os
from html import escape
from bs4 import BeautifulSoup
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                PageBreak, Image, Table, TableStyle)
from reportlab.lib.pagesizes import LEGAL
from reportlab.lib import colors
# Asegúrate de que src/templates/pdf_styles.py existe
from src.templates.pdf_styles import get_edj_stylesheet, COLOR_PRIMARIO, COLOR_SECUNDARIO


class AntGenReport:
    def __init__(self, filename):
        self.filename = filename
        self.styles = get_edj_stylesheet()
        self.story = []

        # Configuración de página (Legal)
        self.page_size = LEGAL
        self.margins = {
            'rightMargin': 50,
            'leftMargin': 50,
            'topMargin': 50,
            'bottomMargin': 50
        }

    def _sanitize_text(self, text):
        """
        Limpia el HTML complejo y escapa caracteres especiales para ReportLab.
        """
        if not text:
            return ""

        txt_str = str(text)
        clean_text = txt_str

        # Si parece HTML, intentamos limpiarlo con BS4
        if '<' in txt_str and '>' in txt_str:
            try:
                soup = BeautifulSoup(txt_str, "html.parser")
                clean_text = soup.get_text(separator="\n")
            except Exception:
                clean_text = txt_str

        # Escapar caracteres XML reservados (<, >, &)
        return escape(clean_text.strip())

    def build(self, data: dict):
        """Método principal que orquesta la construcción del PDF."""
        # 1. Portada
        self._create_cover(data)
        # 2. Registro de Estados
        self._create_status_registry(data.get("registro_estados", []))
        # 3. Datos Generales
        self._create_general_data(data)
        # 4. Contactos
        self._create_contacts(data)
        # 5. Permisos (PAS)
        self._create_pas(data.get("permisos_ambientales", []))
        # 6. Descripción
        self._create_description(data)

        # Generar PDF
        doc = SimpleDocTemplate(self.filename, pagesize=self.page_size, **self.margins)
        doc.build(self.story, onFirstPage=self._footer_handler, onLaterPages=self._footer_handler)

    def _create_cover(self, data):
        """Genera la portada."""
        logo_path = os.path.join(os.getcwd(), "assets", "images", "Logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=531 / 5, height=480 / 5)
            img.hAlign = 'LEFT'
            self.story.append(img)

        self.story.append(Spacer(1, 80))
        self.story.append(Paragraph("ANTECEDENTES GENERALES", self.styles['EDJ_Titulo1']))
        self.story.append(Spacer(1, 20))

        nombre_proy = self._sanitize_text(data.get('nombre_proyecto', 'Sin Nombre'))
        self.story.append(Paragraph(f"Proyecto '{nombre_proy}'", self.styles['EDJ_Titulo2']))

        self.story.append(Spacer(1, 80))

        self.story.append(Paragraph("INGRESADO COMO:", self.styles['EDJ_Portada_Label']))
        self.story.append(Paragraph(self._sanitize_text(data.get('forma_presentacion', 'No indicada')),
                                    self.styles['EDJ_Portada_Valor']))

        self.story.append(Spacer(1, 20))

        # Manejo seguro del titular
        raw_titular = data.get('titular')
        titular_txt = "No indicado"
        if isinstance(raw_titular, dict):
            titular_txt = raw_titular.get('nombre', 'No indicado')
        elif raw_titular:
            titular_txt = str(raw_titular)
            if "Nombre:" in titular_txt:
                titular_txt = titular_txt.split('\n')[0].replace("Nombre:", "").strip()

        self.story.append(Paragraph("TITULAR:", self.styles['EDJ_Portada_Label']))
        self.story.append(Paragraph(self._sanitize_text(titular_txt), self.styles['EDJ_Portada_Valor']))
        self.story.append(PageBreak())

    def _create_status_registry(self, estados_list):
        self.story.append(Paragraph("REGISTRO DE ESTADOS DEL PROYECTO", self.styles['EDJ_Titulo2']))
        self.story.append(Spacer(1, 20))

        if not estados_list:
            self.story.append(Paragraph("No hay registros de estado.", self.styles['EDJ_Cuerpo']))
        else:
            table_data = [["Fecha", "Estado", "Documento", "Autor"]]

            for est in estados_list:
                doc_full = f"{est.get('documento', '')} (N° {est.get('numero', '')})"
                table_data.append([
                    Paragraph(str(est.get('fecha', '')), self.styles['EDJ_Tabla_Celda']),
                    Paragraph(str(est.get('estado', '')), self.styles['EDJ_Tabla_Celda']),
                    Paragraph(doc_full, self.styles['EDJ_Tabla_Celda']),
                    Paragraph(str(est.get('autor', '')), self.styles['EDJ_Tabla_Celda']),
                ])

            # Ancho total: 512 pt
            t = Table(table_data, colWidths=[65, 70, 277, 100])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECUNDARIO),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_PRIMARIO),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            self.story.append(t)

        self.story.append(PageBreak())

    def _create_general_data(self, data):
        self.story.append(Paragraph("ANTECEDENTES GENERALES", self.styles['EDJ_Titulo2']))
        self.story.append(Spacer(1, 20))

        campos = [
            ("Monto de Inversión", data.get("monto_inversion", "")),
            ("Estado Actual", data.get("estado_actual", "")),
            ("Encargado/a evaluación", data.get("encargado", "")),
            ("Tipo de Proyecto", data.get("tipo_proyecto", "")),
        ]

        for label, val in campos:
            val_clean = self._sanitize_text(val)
            p = Paragraph(f"<b>{label}:</b> {val_clean}", self.styles['EDJ_Cuerpo'])
            self.story.append(p)

        self.story.append(Spacer(1, 14))

    def _create_contacts(self, data):
        bloques = [
            ("Información del Titular", data.get('titular')),
            ("Representante Legal", data.get('representante_legal')),
            ("Consultora", data.get('consultora'))
        ]

        for titulo, info_data in bloques:
            if not info_data: continue

            self.story.append(Paragraph(titulo, self.styles['EDJ_Subtitulo']))

            if isinstance(info_data, dict):
                detalles = []
                for k, v in info_data.items():
                    if v: detalles.append(f"<b>{k.capitalize()}:</b> {self._sanitize_text(v)}")
                texto_bloque = "<br/>".join(detalles)
                self.story.append(Paragraph(texto_bloque, self.styles['EDJ_Cuerpo']))
            else:
                texto_limpio = self._sanitize_text(info_data)
                texto_html_safe = texto_limpio.replace('\n', '<br/>')
                self.story.append(Paragraph(texto_html_safe, self.styles['EDJ_Cuerpo']))

            self.story.append(Spacer(1, 10))

        self.story.append(PageBreak())

    def _create_pas(self, permisos):
        self.story.append(Paragraph("PERMISOS AMBIENTALES SECTORIALES (PAS)", self.styles['EDJ_Titulo2']))
        self.story.append(Spacer(1, 20))
        self.story.append(Paragraph("Otorgados al proyecto mediante su RCA de acuerdo al Título VII del Reglamento del Sistema de Evaluación de Impacto Ambiental ", self.styles['EDJ_Cuerpo']))
        self.story.append(Spacer(1, 20))

        if not permisos:
            self.story.append(
                Paragraph("No cuenta con Permisos Ambientales Sectoriales declarados.", self.styles['EDJ_Cuerpo']))
        else:
            table_data = [["Art.", "Tipo", "Nombre", "Certificado"]]
            for p in permisos:
                if isinstance(p, dict):
                    table_data.append([
                        str(p.get('articulo', '')),
                        Paragraph(str(p.get('tipo', '')), self.styles['EDJ_Tabla_Celda']),
                        Paragraph(str(p.get('nombre', '')), self.styles['EDJ_Tabla_Celda']),
                        # CAMBIO: Usamos Paragraph para que el texto se ajuste (wrap)
                        Paragraph(str(p.get('certificado', '')), self.styles['EDJ_Tabla_Celda'])
                    ])

            # Anchos ajustados: Total 512 pt
            t = Table(table_data, colWidths=[35, 60, 332, 85])

            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECUNDARIO),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_PRIMARIO),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            self.story.append(t)

        self.story.append(PageBreak())

    def _create_description(self, data):
        self.story.append(Paragraph("DESCRIPCIÓN DEL PROYECTO", self.styles['EDJ_Titulo2']))
        self.story.append(Spacer(1, 20))

        desc = data.get("descripcion_proyecto", "")
        # Usamos _sanitize_text que ahora incluye escape()
        desc_limpia = self._sanitize_text(desc)

        if desc_limpia:
            for parrafo in desc_limpia.split('\n'):
                if parrafo.strip():
                    self.story.append(Paragraph(parrafo, self.styles['EDJ_Cuerpo']))
                    self.story.append(Spacer(1, 6))
        else:
            self.story.append(Paragraph("Sin descripción disponible.", self.styles['EDJ_Cuerpo']))

    def _footer_handler(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(COLOR_PRIMARIO)
        page_num = canvas.getPageNumber()
        canvas.drawCentredString(self.page_size[0] / 2, 30, f"- {page_num} -")
        canvas.restoreState()