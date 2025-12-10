# src/templates/antgen_report.py
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from src.templates.pdf_styles import COLOR_PRIMARIO, COLOR_SECUNDARIO
from src.templates.base_report import BaseReport  # <--- Importamos la base


class AntGenReport(BaseReport):

    def get_story(self, data: dict):
        """
        Implementación específica para ANTGEN.
        Define qué secciones van y en qué orden.
        """
        # 1. Usamos la portada genérica de la base
        self._create_cover_base(data, "ANTECEDENTES GENERALES")

        # 2. Secciones específicas
        self._create_status_registry(data.get("registro_estados", []))
        self._create_general_data(data)
        self._create_contacts(data)
        self._create_pas(data.get("permisos_ambientales", []))
        self._create_description(data)

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
                texto_html_safe = self._sanitize_text(info_data).replace('\n', '<br/>')
                self.story.append(Paragraph(texto_html_safe, self.styles['EDJ_Cuerpo']))
            self.story.append(Spacer(1, 10))
        self.story.append(PageBreak())

    def _create_pas(self, permisos):
        self.story.append(Paragraph("PERMISOS AMBIENTALES SECTORIALES (PAS)", self.styles['EDJ_Titulo2']))
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
                        Paragraph(str(p.get('certificado', '')), self.styles['EDJ_Tabla_Celda'])
                    ])
            t = Table(table_data, colWidths=[35, 60, 332, 85])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECUNDARIO),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_PRIMARIO),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            self.story.append(t)
        self.story.append(PageBreak())

    def _create_description(self, data):
        self.story.append(Paragraph("DESCRIPCIÓN DEL PROYECTO", self.styles['EDJ_Titulo2']))
        self.story.append(Spacer(1, 20))

        desc = data.get("descripcion_proyecto", "")
        desc_limpia = self._sanitize_text(desc)

        if desc_limpia:
            for parrafo in desc_limpia.split('\n'):
                if parrafo.strip():
                    self.story.append(Paragraph(parrafo, self.styles['EDJ_Cuerpo']))
                    self.story.append(Spacer(1, 6))
        else:
            self.story.append(Paragraph("Sin descripción disponible.", self.styles['EDJ_Cuerpo']))