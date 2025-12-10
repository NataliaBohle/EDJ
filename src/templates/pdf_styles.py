# src/templates/pdf_styles.py
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT

# Colores Corporativos (Basados en tu x_genestilo)
COLOR_PRIMARIO = colors.HexColor("#156082")  # Azul Institucional
COLOR_SECUNDARIO = colors.HexColor("#d3d3d3")  # Gris claro para tablas
COLOR_TEXTO = colors.black


def get_edj_stylesheet():
    """Retorna la hoja de estilos personalizada para el proyecto."""
    styles = getSampleStyleSheet()

    # Eliminamos estilos por defecto que no queramos o los sobreescribimos

    # 1. Títulos
    styles.add(ParagraphStyle(
        name='EDJ_Titulo1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=26,
        textColor=COLOR_PRIMARIO,
        alignment=TA_CENTER,
        leading=32,
        spaceAfter=20
    ))

    styles.add(ParagraphStyle(
        name='EDJ_Titulo2',
        parent=styles['Heading2'],
        fontName='Helvetica',
        fontSize=16,
        textColor=COLOR_PRIMARIO,
        alignment=TA_CENTER,
        spaceAfter=14
    ))

    styles.add(ParagraphStyle(
        name='EDJ_Subtitulo',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=COLOR_PRIMARIO,
        alignment=TA_LEFT,
        spaceAfter=10
    ))

    # 2. Textos de Cuerpo
    styles.add(ParagraphStyle(
        name='EDJ_Cuerpo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=14,
        spaceAfter=6
    ))

    # 3. Estilos Específicos de Portada
    styles.add(ParagraphStyle(
        name='EDJ_Portada_Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        alignment=TA_CENTER,
        textColor=colors.black
    ))

    styles.add(ParagraphStyle(
        name='EDJ_Portada_Valor',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.black
    ))

    # 4. Tablas
    styles.add(ParagraphStyle(
        name='EDJ_Tabla_Header',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=TA_CENTER,
        textColor=COLOR_PRIMARIO
    ))

    styles.add(ParagraphStyle(
        name='EDJ_Tabla_Celda',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        alignment=TA_LEFT
    ))

    return styles