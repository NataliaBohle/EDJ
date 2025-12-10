import os
from html import escape
from bs4 import BeautifulSoup
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.units import inch  # <--- Necesario para definir el tamaño personalizado
from reportlab.lib import colors
from src.templates.pdf_styles import get_edj_stylesheet, COLOR_PRIMARIO

# Definimos el tamaño Oficio / Legal Chileno (8.5 x 13 pulgadas)
LEGAL_CHILE = (8.5 * inch, 13 * inch)


class BaseReport:
    """
    Clase padre para todos los reportes del sistema (ANTGEN, EXEVA, EXPAC, etc.).
    Maneja la configuración de página, estilos comunes, sanitización y pie de página.
    """

    def __init__(self, filename):
        self.filename = filename
        self.styles = get_edj_stylesheet()
        self.story = []

        # Usamos el tamaño personalizado para Chile
        self.page_size = LEGAL_CHILE

        self.margins = {
            'rightMargin': 50, 'leftMargin': 50,
            'topMargin': 50, 'bottomMargin': 50
        }

    def get_story(self, data: dict):
        """
        Método que DEBE ser sobrescrito por los reportes hijos.
        Aquí es donde cada reporte define su estructura única.
        """
        raise NotImplementedError("Cada reporte debe implementar su propio get_story()")

    def build(self, data: dict):
        """Método maestro que genera el PDF."""
        # 1. Construir la historia usando la lógica del hijo
        self.get_story(data)

        # 2. Generar el archivo físico
        doc = SimpleDocTemplate(self.filename, pagesize=self.page_size, **self.margins)
        doc.build(self.story, onFirstPage=self._footer_handler, onLaterPages=self._footer_handler)

    def _sanitize_text(self, text):
        """Limpia HTML y escapa caracteres. Disponible para todos los hijos."""
        if not text: return ""
        txt_str = str(text)
        clean_text = txt_str

        if '<' in txt_str and '>' in txt_str:
            try:
                soup = BeautifulSoup(txt_str, "html.parser")
                clean_text = soup.get_text(separator="\n")
            except Exception:
                pass
        return escape(clean_text.strip())

    def _create_cover_base(self, data, titulo_reporte):
        """
        Generador de portada genérico.
        Los hijos pueden usar esto o crear su propia portada si es muy distinta.
        """
        logo_path = os.path.join(os.getcwd(), "assets", "images", "Logo.png")
        if os.path.exists(logo_path):
            img = Image(logo_path, width=531 / 5, height=480 / 5)
            img.hAlign = 'LEFT'
            self.story.append(img)

        self.story.append(Spacer(1, 80))
        self.story.append(Paragraph(titulo_reporte, self.styles['EDJ_Titulo1']))
        self.story.append(Spacer(1, 20))

        nombre = self._sanitize_text(data.get('nombre_proyecto', 'Sin Nombre'))
        self.story.append(Paragraph(f"Proyecto '{nombre}'", self.styles['EDJ_Titulo2']))

        self.story.append(Spacer(1, 80))

        self.story.append(Paragraph("INGRESADO COMO:", self.styles['EDJ_Portada_Label']))
        presentacion = self._sanitize_text(data.get('forma_presentacion', 'No indicada'))
        self.story.append(Paragraph(presentacion, self.styles['EDJ_Portada_Valor']))

        self.story.append(Spacer(1, 20))

        # Lógica de titular común
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

    def _footer_handler(self, canvas, doc):
        """Pie de página común."""
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(COLOR_PRIMARIO)
        page_num = canvas.getPageNumber()
        # Ajustamos la posición del pie de página al nuevo tamaño
        # self.page_size[0] es el ancho
        canvas.drawCentredString(self.page_size[0] / 2, 30, f"- {page_num} -")
        canvas.restoreState()