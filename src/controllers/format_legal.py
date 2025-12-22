import os
import json
from pathlib import Path
from collections import Counter
from typing import Iterable
from PIL import Image
from reportlab.lib.pagesizes import legal
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import pymupdf
from win32com import client
import shutil
import tempfile
import unicodedata
import uuid

LEGAL_WIDTH, LEGAL_HEIGHT = (8.5 * inch, 13 * inch)
MARGEN = 50

DOC_EXTENSIONS = {".doc", ".docx", ".rtf", ".odt", ".wpd"}
PPT_EXTENSIONS = {".ppt", ".pptx", ".odp", ".key", ".gslides", ".sxi", ".shw", ".prz"}
IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff"}
PDF_EXTENSIONS = {".pdf"}
CONVERTIBLE_EXTENSIONS = DOC_EXTENSIONS | PPT_EXTENSIONS | IMG_EXTENSIONS | PDF_EXTENSIONS


def _resolve_project_path(project_id: str | None, ruta: str) -> Path:
    ruta_text = str(ruta).replace("/", os.sep).replace("\\", os.sep)
    ruta_path = Path(ruta_text)
    if ruta_path.is_absolute():
        return ruta_path.resolve()
    if project_id:
        base = Path(os.getcwd()) / "Ebook" / str(project_id)
        parts = [p.lower() for p in ruta_path.parts]
        if len(parts) >= 2 and parts[0] == "ebook" and parts[1] == str(project_id).lower():
            return (Path(os.getcwd()) / ruta_path).resolve()
        return (base / ruta_path).resolve()
    return (Path(os.getcwd()) / ruta_path).resolve()


def _conv_dir(project_id: str | None) -> Path:
    base = Path(os.getcwd())
    if project_id:
        base = base / "Ebook" / str(project_id)
    return base / "EXEVA" / "conv"


def _generar_nombre_unico(base_path: Path, nombre_base: str) -> Path:
    nombre_final = Path(nombre_base)
    contador = 1
    while (base_path / nombre_final).exists():
        stem = Path(nombre_base).stem
        sufijo = Path(nombre_base).suffix
        nombre_final = Path(f"{stem}_{contador}{sufijo}")
        contador += 1
    return base_path / nombre_final


def _rotar_si_horizontal(img: Image.Image) -> Image.Image:
    if img.width > img.height:
        return img.rotate(90, expand=True)
    return img


def img2pdf_auto(img: Image.Image, salida: str) -> None:
    img = _rotar_si_horizontal(img)
    escala = min((LEGAL_WIDTH - 2 * MARGEN) / img.width, (LEGAL_HEIGHT - 2 * MARGEN) / img.height)
    new_size = (int(img.width * escala), int(img.height * escala))
    img = img.resize(new_size, Image.LANCZOS)

    x = (LEGAL_WIDTH - img.width) / 2
    y = (LEGAL_HEIGHT - img.height) / 2

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        temp = tmp.name
    try:
        img.save(temp)
        c = canvas.Canvas(salida, pagesize=legal)
        c.drawImage(temp, x, y, width=img.width, height=img.height)
        c.save()
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def pdf2imgpdf(ruta_pdf: str | Path, salida_pdf: str | Path) -> bool:
    try:
        doc = pymupdf.open(str(ruta_pdf))
        if len(doc) == 0:
            raise Exception("Documento vacío")

        nuevo = pymupdf.open()
        ya_es_legal = True

        for i in range(len(doc)):
            page = doc[i]
            w, h = page.rect.width, page.rect.height
            rotate = 0

            if abs(w - LEGAL_WIDTH) >= 3 or abs(h - LEGAL_HEIGHT) >= 3:
                ya_es_legal = False

            if w > h:
                rotate = 90
                w, h = h, w

            escala = LEGAL_WIDTH / w
            new_w = LEGAL_WIDTH
            new_h = h * escala

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
                rotate=rotate,
            )

        salida_pdf = str(salida_pdf)
        if ya_es_legal:
            shutil.copy2(str(ruta_pdf), salida_pdf)
            print(f"✔️ Ya está en formato legal: {ruta_pdf}")
            return True

        nuevo.save(salida_pdf)
        print(f"✅ PDF ajustado: {salida_pdf}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        if os.path.exists(str(salida_pdf)):
            os.remove(str(salida_pdf))
        return False


def _attempt_word_conversion(word, source_path: Path, target_path: Path) -> bool:
    try:
        doc = word.Documents.Open(str(source_path))
        doc.SaveAs(str(target_path), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close()
        return True
    except Exception as e:
        print(f"⚠️ Error al abrir {source_path.name}: {e}")
        return False


def _attempt_ppt_conversion(powerpoint, source_path: Path, target_path: Path) -> bool:
    try:
        presentation = powerpoint.Presentations.Open(str(source_path), WithWindow=False)
        presentation.SaveAs(str(target_path), FileFormat=32)  # 32 = ppSaveAsPDF
        presentation.Close()
        return True
    except Exception as e:
        print(f"⚠️ Error al abrir {source_path.name}: {e}")
        return False


def doc2pdf(doc_path: str | Path, out_pdf: str | Path, max_path_len: int = 240) -> Path:
    doc_path = Path(doc_path).resolve()
    out_pdf = Path(out_pdf).resolve()

    if not doc_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {doc_path}")

    word = client.Dispatch("Word.Application")
    word.Visible = False

    try:
        print(f"📝 {doc_path.name} → DOC a PDF")

        if len(str(doc_path)) < max_path_len and len(str(out_pdf)) < max_path_len:
            if _attempt_word_conversion(word, doc_path, out_pdf):
                return out_pdf

        with tempfile.TemporaryDirectory() as tmpdir:
            safe_stem = unicodedata.normalize("NFKD", doc_path.stem).encode("ascii", "ignore").decode("ascii")
            safe_stem = safe_stem.replace(" ", "_")[:40]
            safe_stem += f"_{uuid.uuid4().hex[:6]}"
            temp_doc = Path(tmpdir) / f"{safe_stem}{doc_path.suffix}"
            temp_pdf = Path(tmpdir) / f"{safe_stem}.pdf"

            shutil.copy2(doc_path, temp_doc)
            print(f"🔁 Reintentando con archivo temporal: {temp_doc.name}")

            if _attempt_word_conversion(word, temp_doc, temp_pdf):
                shutil.copy2(temp_pdf, out_pdf)
                return out_pdf
            raise RuntimeError(f"❌ No se pudo convertir ni el archivo original ni el temporal: {doc_path.name}")
    finally:
        word.Quit()


def ppt2pdf(ppt_path: str | Path, out_pdf: str | Path, max_path_len: int = 240) -> Path:
    ppt_path = Path(ppt_path).resolve()
    out_pdf = Path(out_pdf).resolve()

    if not ppt_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ppt_path}")

    powerpoint = client.Dispatch("PowerPoint.Application")
    powerpoint.Visible = False

    try:
        print(f"📊 {ppt_path.name} → PPT a PDF")

        if len(str(ppt_path)) < max_path_len and len(str(out_pdf)) < max_path_len:
            if _attempt_ppt_conversion(powerpoint, ppt_path, out_pdf):
                return out_pdf

        with tempfile.TemporaryDirectory() as tmpdir:
            safe_stem = unicodedata.normalize("NFKD", ppt_path.stem).encode("ascii", "ignore").decode("ascii")
            safe_stem = safe_stem.replace(" ", "_")[:40]
            safe_stem += f"_{uuid.uuid4().hex[:6]}"
            temp_ppt = Path(tmpdir) / f"{safe_stem}{ppt_path.suffix}"
            temp_pdf = Path(tmpdir) / f"{safe_stem}.pdf"

            shutil.copy2(ppt_path, temp_ppt)
            print(f"🔁 Reintentando con archivo temporal: {temp_ppt.name}")

            if _attempt_ppt_conversion(powerpoint, temp_ppt, temp_pdf):
                shutil.copy2(temp_pdf, out_pdf)
                return out_pdf
            raise RuntimeError(f"❌ No se pudo convertir ni el archivo original ni el temporal: {ppt_path.name}")
    finally:
        powerpoint.Quit()


def convert_file_to_pdf(source_path: Path, output_dir: Path) -> Path | None:
    ext = source_path.suffix.lower()
    if ext not in CONVERTIBLE_EXTENSIONS:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _generar_nombre_unico(output_dir, source_path.with_suffix(".pdf").name)

    try:
        if ext in PDF_EXTENSIONS:
            if pdf2imgpdf(source_path, output_path):
                return output_path
            return None

        if ext in IMG_EXTENSIONS:
            img = Image.open(source_path)
            img2pdf_auto(img, str(output_path))
            return output_path if output_path.exists() else None

        if ext in DOC_EXTENSIONS:
            temp_doc_pdf = output_dir / f"{source_path.stem}.intermediate.pdf"
            doc2pdf(source_path, temp_doc_pdf)
            try:
                if pdf2imgpdf(temp_doc_pdf, output_path):
                    return output_path
            finally:
                if temp_doc_pdf.exists():
                    temp_doc_pdf.unlink()
            return None

        if ext in PPT_EXTENSIONS:
            temp_ppt_pdf = output_dir / f"{source_path.stem}.intermediate.pdf"
            ppt2pdf(source_path, temp_ppt_pdf)
            try:
                if pdf2imgpdf(temp_ppt_pdf, output_path):
                    return output_path
            finally:
                if temp_ppt_pdf.exists():
                    temp_ppt_pdf.unlink()
            return None
    except Exception as exc:
        print(f"⚠️ Error al convertir {source_path.name}: {exc}")
        if output_path.exists():
            output_path.unlink()
        return None

    return None


def convert_exeva_item(project_id: str | None, item: dict) -> tuple[bool, str | None, str | None]:
    try:
        ruta = item.get("ruta")
        if not ruta:
            return False, None, "Sin ruta para convertir."

        source_path = _resolve_project_path(project_id, str(ruta))
        if not source_path.exists():
            return False, None, f"Archivo no encontrado: {source_path}"

        ext = source_path.suffix.lower()
        if ext not in CONVERTIBLE_EXTENSIONS:
            return False, None, "Formato no convertible."

        conv_value = item.get("conv")
        if conv_value:
            conv_path = _resolve_project_path(project_id, str(conv_value))
            if conv_path.exists():
                return True, str(conv_value), None

        output_dir = _conv_dir(project_id)
        output_path = convert_file_to_pdf(source_path, output_dir)
        if not output_path:
            return False, None, "Error al convertir."

        try:
            base = Path(os.getcwd())
            if project_id:
                base = base / "Ebook" / str(project_id)
            rel = output_path.resolve().relative_to(base.resolve())
            conv_rel = rel.as_posix()
        except Exception:
            conv_rel = output_path.as_posix()
        return True, conv_rel, None
    except Exception as exc:
        return False, None, f"Error al convertir: {exc}"


def _iter_items(obj: dict | list) -> Iterable[dict]:
    if isinstance(obj, list):
        for item in obj:
            yield from _iter_items(item)
        return
    if isinstance(obj, dict):
        if "ruta" in obj:
            yield obj
        for v in obj.values():
            yield from _iter_items(v)


def format_legal(CLAVE, ID):
    carpeta = f"{CLAVE}_{ID}"
    json_in = Path(carpeta) / f"03{CLAVE}_{ID}.json"
    json_out = Path(carpeta) / f"04{CLAVE}_{ID}.json"

    with open(json_in, encoding="utf-8") as f:
        data = json.load(f)

    rutas_procesadas = set()

    def contar_formatos(obj):
        if isinstance(obj, dict):
            return Counter([obj["formato"]] if "formato" in obj and obj["formato"] else []) + sum(
                (contar_formatos(v) for v in obj.values()), Counter()
            )
        if isinstance(obj, list):
            return sum((contar_formatos(e) for e in obj), Counter())
        return Counter()

    print("📊 Formatos detectados:")
    for fmt, cantidad in contar_formatos(data).items():
        print(f"{fmt}: {cantidad}")

    for obj in _iter_items(data):
        ruta = obj.get("ruta")
        if not ruta:
            continue
        ruta_norm = os.path.normpath(Path(ruta))
        if ruta_norm in rutas_procesadas:
            print(f"🔁 {ruta} → Ya procesado anteriormente. Se omite.")
            continue
        rutas_procesadas.add(ruta_norm)

        source_path = Path(ruta_norm)
        ext = source_path.suffix.lower()
        if ext not in CONVERTIBLE_EXTENSIONS:
            print(f"📁 {source_path.name} → Formato no convertible")
            continue

        output_dir = Path(carpeta) / "EXEVA" / "conv"
        output_path = convert_file_to_pdf(source_path, output_dir)
        if output_path:
            obj["conv"] = output_path.as_posix()
        else:
            print(f"⚠️ {source_path.name} → Error al convertir")

    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ JSON actualizado: {json_out}")

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
