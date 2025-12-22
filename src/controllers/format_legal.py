import os
import json
from pathlib import Path
from collections import Counter
from PIL import Image
from reportlab.lib.pagesizes import legal
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import pymupdf
from docx2pdf import convert as convert_docx
from win32com import client
import shutil
import tempfile
import unicodedata
import uuid
import sys

def format_legal(CLAVE, ID):
    LEGAL_WIDTH, LEGAL_HEIGHT = (8.5 * inch, 13 * inch)
    MARGEN = 50

    CONVERTIBLES_IMG = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff']
    CARPETA = f"{CLAVE}_{ID}"
    PDF_OUT = Path(CARPETA) / "Archivos_pdf"
    PDF_OUT.mkdir(parents=True, exist_ok=True)
    JSON_IN = Path(CARPETA) / f"03{CLAVE}_{ID}.json"
    JSON_OUT = Path(CARPETA) / f"04{CLAVE}_{ID}.json"

    with open(JSON_IN, encoding='utf-8') as f:
        data = json.load(f)

    RUTAS_PROCESADAS = set()

    def contar_formatos(obj):
        if isinstance(obj, dict):
            return Counter([obj['formato']] if 'formato' in obj and obj['formato'] else []) + sum((contar_formatos(v) for v in obj.values()), Counter())
        elif isinstance(obj, list):
            return sum((contar_formatos(e) for e in obj), Counter())
        return Counter()

    def generar_nombre_unico(base_path, nombre_base):
        nombre_final = Path(nombre_base)
        contador = 1
        while (base_path / nombre_final).exists():
            stem = Path(nombre_base).stem
            sufijo = Path(nombre_base).suffix
            nombre_final = Path(f"{stem}_{contador}{sufijo}")
            contador += 1
        return base_path / nombre_final

    def rotar_si_horizontal(img):
        if img.width > img.height:
            return img.rotate(90, expand=True)
        return img

    def img2pdf_auto(img, salida):
        img = rotar_si_horizontal(img)
        escala = min((LEGAL_WIDTH - 2 * MARGEN) / img.width, (LEGAL_HEIGHT - 2 * MARGEN) / img.height)
        new_size = (int(img.width * escala), int(img.height * escala))
        img = img.resize(new_size, Image.LANCZOS)

        x = (LEGAL_WIDTH - img.width) / 2
        y = (LEGAL_HEIGHT - img.height) / 2

        temp = "temp_img.png"
        img.save(temp)
        c = canvas.Canvas(salida, pagesize=legal)
        c.drawImage(temp, x, y, width=img.width, height=img.height)
        c.save()
        os.remove(temp)

    def pdf2imgpdf(ruta_pdf, salida_pdf):
        try:
            doc = pymupdf.open(ruta_pdf)
            if len(doc) == 0:
                raise Exception("Documento vacío")

            nuevo = pymupdf.open()
            ya_es_legal = True

            for i in range(len(doc)):
                page = doc[i]
                w, h = page.rect.width, page.rect.height
                rotate = 0

                # Detectar si la página necesita procesarse
                if abs(w - LEGAL_WIDTH) >= 3 or abs(h - LEGAL_HEIGHT) >= 3:
                    ya_es_legal = False

                # Si es horizontal, rotamos
                if w > h:
                    rotate = 90
                    w, h = h, w  # tras rotar

                # ESCALADO mejorado:
                # Si es horizontal rotada, ajustamos al ancho completo
                escala = LEGAL_WIDTH / w
                new_w = LEGAL_WIDTH
                new_h = h * escala

                # Si excede el alto legal, recalcamos la escala para ajustar al ALTO
                if new_h > LEGAL_HEIGHT:
                    escala = LEGAL_HEIGHT / h
                    new_w = w * escala
                    new_h = LEGAL_HEIGHT

                dx = (LEGAL_WIDTH - new_w) / 2
                dy = (LEGAL_HEIGHT - new_h) / 2

                nueva_pagina = nuevo.new_page(width=LEGAL_WIDTH, height=LEGAL_HEIGHT)
                nueva_pagina.show_pdf_page(
                    pymupdf.Rect(dx, dy, dx + new_w, dy + new_h),
                    doc,
                    i,
                    rotate=rotate
                )

            if ya_es_legal:
                print(f"✔️ Ya está en formato legal: {ruta_pdf}")
                return False

            nuevo.save(salida_pdf)
            print(f"✅ PDF ajustado: {salida_pdf}")
            return True

        except Exception as e:
            print(f"❌ Error: {e}")
            if os.path.exists(salida_pdf):
                os.remove(salida_pdf)
            return False

        except Exception as e:
            print(f"❌ Error: {e}")
            if os.path.exists(salida_pdf):
                os.remove(salida_pdf)
            return False

    def doc2pdf(doc_path, out_pdf, max_path_len=240):
        doc_path = Path(doc_path).resolve()
        out_pdf = Path(out_pdf).resolve()

        if not doc_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {doc_path}")

        word = client.Dispatch("Word.Application")
        word.Visible = False

        def attempt_conversion(source_path, target_path):
            try:
                doc = word.Documents.Open(str(source_path))
                doc.SaveAs(str(target_path), FileFormat=17)  # 17 = wdFormatPDF
                doc.Close()
                return True
            except Exception as e:
                print(f"⚠️ Error al abrir {source_path.name}: {e}")
                return False

        try:
            print(f"📝 {doc_path.name} → DOC a PDF")

            # Caso normal si ruta es corta
            if len(str(doc_path)) < max_path_len and len(str(out_pdf)) < max_path_len:
                if attempt_conversion(doc_path, out_pdf):
                    return out_pdf

            # Caso ruta larga o fallo: usar temporal
            with tempfile.TemporaryDirectory() as tmpdir:
                # Nombre temporal seguro
                safe_stem = unicodedata.normalize("NFKD", doc_path.stem).encode("ascii", "ignore").decode("ascii")
                safe_stem = safe_stem.replace(" ", "_")[:40]
                safe_stem += f"_{uuid.uuid4().hex[:6]}"
                temp_doc = Path(tmpdir) / f"{safe_stem}.docx"
                temp_pdf = Path(tmpdir) / f"{safe_stem}.pdf"

                shutil.copy2(doc_path, temp_doc)
                print(f"🔁 Reintentando con archivo temporal: {temp_doc.name}")

                if attempt_conversion(temp_doc, temp_pdf):
                    shutil.copy2(temp_pdf, out_pdf)
                    return out_pdf
                else:
                    raise RuntimeError(f"❌ No se pudo convertir ni el archivo original ni el temporal: {doc_path.name}")

        finally:
            word.Quit()

    def txt2pdf(txt_path, out_pdf):
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        c = canvas.Canvas(out_pdf, pagesize=legal)
        width, height = legal
        y = height - 50
        for line in lines:
            if y < 50:
                c.showPage()
                y = height - 50
            c.drawString(50, y, line.strip())
            y -= 14
        c.save()
        return out_pdf

    def procesar(obj):
        if isinstance(obj, dict):
            if 'ruta' in obj and 'formato' in obj and obj['ruta']:
                ruta = os.path.normpath(Path(obj['ruta']))
                nombre = os.path.basename(ruta)
                if not nombre:
                    print(f"⚠️ Ruta vacía, se omite: {ruta}")
                    return
                ext = os.path.splitext(ruta)[1].lower()
                salida_pdf = str(generar_nombre_unico(PDF_OUT, Path(nombre).with_suffix(".pdf").name))

                if not os.path.exists(ruta):
                    print(f"❌ {nombre} → No encontrado: {ruta}")
                elif ruta in RUTAS_PROCESADAS:
                    print(f"🔁 {nombre} → Ya procesado anteriormente. Se omite.")
                else:
                    RUTAS_PROCESADAS.add(ruta)
                    try:
                        if ext == '.pdf':
                            print(f"📄 {nombre} → PDF a imágenes PDF")
                            if pdf2imgpdf(ruta, salida_pdf):
                                obj['conv'] = salida_pdf.replace("\\", "/")
                        elif ext in CONVERTIBLES_IMG:
                            print(f"🖼️ {nombre} → Imagen")
                            img = Image.open(ruta)
                            img2pdf_auto(img, salida_pdf)
                            if os.path.exists(salida_pdf):
                                obj['conv'] = salida_pdf.replace("\\", "/")
                        elif ext in ['.doc', '.docx']:
                            print(f"📝 {nombre} → DOC a PDF")
                            temp_doc_pdf = str(PDF_OUT / Path(nombre).with_suffix(".intermediate.pdf").name)
                            doc2pdf(ruta, temp_doc_pdf)
                            if os.path.exists(temp_doc_pdf):
                                print(f"📄 Convertido → Ajuste a tamaño legal")
                                if pdf2imgpdf(temp_doc_pdf, salida_pdf):
                                    obj['conv'] = salida_pdf.replace("\\", "/")
                                os.remove(temp_doc_pdf)
                            else:
                                print(f"⚠️ Falló conversión Word")
                        elif ext == '.txt':
                            print(f"📄 {nombre} → TXT a PDF")
                            temp_txt_pdf = str(PDF_OUT / Path(nombre).with_suffix(".intermediate.pdf").name)
                            txt2pdf(ruta, temp_txt_pdf)
                            if os.path.exists(temp_txt_pdf):
                                print(f"📄 Convertido → Ajuste a tamaño legal")
                                if pdf2imgpdf(temp_txt_pdf, salida_pdf):
                                    obj['conv'] = salida_pdf.replace("\\", "/")
                                os.remove(temp_txt_pdf)
                            else:
                                print(f"⚠️ Falló conversión TXT")
                        else:
                            print(f"📁 {nombre} → Formato no convertible")
                    except Exception as e:
                        print(f"⚠️ {nombre} → Error: {e}")

            for v in obj.values():
                procesar(v)

        elif isinstance(obj, list):
            for item in obj:
                procesar(item)

    print("📊 Formatos detectados:")
    for fmt, cantidad in contar_formatos(data).items():
        print(f"{fmt}: {cantidad}")

    procesar(data)

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ JSON actualizado: {JSON_OUT}")
