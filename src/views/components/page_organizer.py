# page_organizer.py
# Componente independiente para "Organizar Páginas" (SIN WebEngine).
# - Grid de miniaturas (raster)
# - Rotar página seleccionada / todas
# - Guardar rotación REAL en el PDF (PyPDF2 o pypdf)
#
# Requisitos:
#   pip install PyQt6
#   y además UNO de:
#     pip install PyPDF2
#     pip install pypdf
#   Para miniaturas:
#     PyQt6 con QtPdf disponible (PyQt6.QtPdf -> QPdfDocument)

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize, QTimer, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QTransform, QAction, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)

# QtPdf
try:
    from PyQt6.QtPdf import QPdfDocument

    QT_PDF_AVAILABLE = True
except Exception:
    QT_PDF_AVAILABLE = False
    QPdfDocument = None

# Writer backend
PdfReader = None
PdfWriter = None
PDF_AVAILABLE = False

try:
    from PyPDF2 import PdfReader as _R, PdfWriter as _W

    PdfReader, PdfWriter = _R, _W
    PDF_AVAILABLE = True
except Exception:
    try:
        from pypdf import PdfReader as _R, PdfWriter as _W

        PdfReader, PdfWriter = _R, _W
        PDF_AVAILABLE = True
    except Exception:
        PDF_AVAILABLE = False


def _norm_rot(deg: int) -> int:
    d = int(deg) % 360
    return (round(d / 90) * 90) % 360


def _rotate_page_obj(page, deg: int) -> None:
    a = _norm_rot(deg)
    if a == 0:
        return
    if hasattr(page, "rotate") and callable(getattr(page, "rotate")):
        page.rotate(a)
        return
    if hasattr(page, "rotate_clockwise") and callable(getattr(page, "rotate_clockwise")):
        page.rotate_clockwise(a)
        return
    if hasattr(page, "rotateClockwise") and callable(getattr(page, "rotateClockwise")):
        page.rotateClockwise(a)
        return
    raise RuntimeError("No se encontró método de rotación compatible en Page.")


class PageOrganizer(QDialog):
    def __init__(self, pdf_path: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Organizar Páginas")
        self.resize(1200, 800)

        self.pdf_path = str(Path(pdf_path).resolve())
        self.saved = False

        self._rotations: dict[int, int] = {}  # idx -> deg
        self._page_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Toolbar
        bar = QWidget()
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)

        self.btn_l_cur = QPushButton("⟲ actual")
        self.btn_r_cur = QPushButton("⟳ actual")
        self.btn_l_all = QPushButton("⟲ todas")
        self.btn_r_all = QPushButton("⟳ todas")

        self.btn_save = QPushButton("Guardar")
        self.btn_close = QPushButton("Cerrar")

        self.lbl = QLabel("")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.btn_l_cur.clicked.connect(lambda: self._rotate_selected(-90))
        self.btn_r_cur.clicked.connect(lambda: self._rotate_selected(+90))
        self.btn_l_all.clicked.connect(lambda: self._rotate_all(-90))
        self.btn_r_all.clicked.connect(lambda: self._rotate_all(+90))
        self.btn_save.clicked.connect(self._save)
        self.btn_close.clicked.connect(self.close)

        self._thumb_w = 100
        self._thumb_w_min = 100
        self._thumb_w_max = 600
        self._thumb_pad = 12
        self._page_ratio = 1.35
        self._thumb_step = 40

        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_out.setToolTip("Reducir miniaturas")
        self.btn_zoom_in.setToolTip("Aumentar miniaturas")
        self.btn_zoom_out.clicked.connect(lambda: self._change_zoom(-1))
        self.btn_zoom_in.clicked.connect(lambda: self._change_zoom(+1))

        bl.addWidget(self.btn_l_all)
        bl.addWidget(self.btn_l_cur)
        bl.addWidget(self.btn_r_cur)
        bl.addWidget(self.btn_r_all)
        bl.addWidget(self.btn_save)
        bl.addWidget(self.btn_close)
        bl.addWidget(self.lbl, 1)
        bl.addWidget(self.btn_zoom_out)
        bl.addWidget(self.btn_zoom_in)

        root.addWidget(bar)

        # Grid thumbs
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setSpacing(10)
        self.list.setUniformItemSizes(True)
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._apply_thumb_sizes()
        self.list.setStyleSheet("""
            QListWidget::item { border: 2px solid transparent; padding: 6px; }
            QListWidget::item:selected { background: white; border: 2px solid #5aa0ff; }
        """)

        # Context menu
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        a1 = QAction("Rotar ⟲ (90°)", self.list)
        a2 = QAction("Rotar ⟳ (90°)", self.list)
        a1.triggered.connect(lambda: self._rotate_selected(-90))
        a2.triggered.connect(lambda: self._rotate_selected(+90))
        self.list.addAction(a1)
        self.list.addAction(a2)

        root.addWidget(self.list, 1)

        # Backend QtPdf
        self.doc = QPdfDocument(self) if QT_PDF_AVAILABLE else None

        self._load()

    def _apply_thumb_sizes(self) -> None:
        w = int(self._thumb_w)
        h = int(w * self._page_ratio)

        # tamaño del icono (imagen)
        self.list.setIconSize(QSize(w, h))

        # tamaño de la celda (icono + texto + padding)
        self.list.setGridSize(QSize(w + 60, h + 90))

        # tamaño mínimo del item (evita colapsos raros)
        self.list.setSpacing(14)

        # Forzar relayout real
        self.list.doItemsLayout()
        self.list.viewport().update()

    def _change_zoom(self, direction: int) -> None:
        if direction > 0:
            self._thumb_w = min(self._thumb_w_max, self._thumb_w + self._thumb_step)
        else:
            self._thumb_w = max(self._thumb_w_min, self._thumb_w - self._thumb_step)

        self._apply_thumb_sizes()

        # Re-render con el nuevo iconSize, manteniendo los mismos items
        for i in range(self._page_count):
            self._refresh_item(i)

        self._set_status()

    def _load(self) -> None:
        if not os.path.exists(self.pdf_path) or not self.pdf_path.lower().endswith(".pdf"):
            QMessageBox.critical(self, "Organizar páginas", "PDF inválido.")
            self._disable_all()
            return

        if not QT_PDF_AVAILABLE or self.doc is None:
            QMessageBox.critical(
                self,
                "Organizar páginas",
                "QtPdf no está disponible (PyQt6.QtPdf/QPdfDocument).\n"
                "Sin eso no puedo generar miniaturas.",
            )
            self._disable_all()
            return

        self.doc.close()
        err = self.doc.load(self.pdf_path)
        if err != QPdfDocument.Error.None_:
            QMessageBox.critical(self, "Organizar páginas", f"No se pudo cargar PDF. Error: {err}")
            self._disable_all()
            return

        self._page_count = int(self.doc.pageCount())
        self._rotations.clear()
        self.saved = False

        # --- LÓGICA MEJORADA: Detección inteligente de ratio (Mediana) ---
        ratios = []
        # Escaneamos solo las primeras 20 páginas para no perder rendimiento
        scan_limit = min(self._page_count, 20)

        for i in range(scan_limit):
            ps = self.doc.pagePointSize(i)
            if not ps.isEmpty() and ps.width() > 0:
                # Calculamos proporción: alto / ancho
                ratios.append(float(ps.height()) / float(ps.width()))

        if ratios:
            # Ordenamos para encontrar la mediana (el valor central)
            # Esto evita que un solo plano gigante deforme el grid de un informe A4
            ratios.sort()
            median_ratio = ratios[len(ratios) // 2]

            # Aplicamos límites de seguridad (Clamp)
            # Mínimo 0.6 (muy apaisado) - Máximo 1.8 (muy vertical)
            # Así evitamos que documentos extraños rompan la interfaz visualmente
            self._page_ratio = max(0.6, min(median_ratio, 1.8))
        else:
            # Valor por defecto si no se pudo leer geometría
            self._page_ratio = 1.35

            # ---------------------------------------------------------------

        self._apply_thumb_sizes()
        self._build_items()
        self._set_status()

    def _disable_all(self) -> None:
        for b in (self.btn_l_cur, self.btn_r_cur, self.btn_l_all, self.btn_r_all, self.btn_save):
            b.setEnabled(False)

    def _set_status(self) -> None:
        dirty = len(self._rotations)
        self.lbl.setText(f"{os.path.basename(self.pdf_path)} | {self._page_count} pág | {dirty} rotadas")

    def _build_items(self) -> None:
        self.list.clear()

        # 1. Crear un placeholder del tamaño exacto que esperamos
        icon_size = self.list.iconSize()
        placeholder = QPixmap(icon_size)
        placeholder.fill(Qt.GlobalColor.transparent)  # O Qt.GlobalColor.white si prefieres
        dummy_icon = QIcon(placeholder)

        for i in range(self._page_count):
            it = QListWidgetItem(f"{i + 1}")
            it.setData(Qt.ItemDataRole.UserRole, i)
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)

            # 2. Asignar el placeholder INMEDIATAMENTE para reservar espacio
            it.setIcon(dummy_icon)

            self.list.addItem(it)

        self._render_i = 0
        QTimer.singleShot(0, self._render_step)

    def _render_step(self) -> None:
        i = getattr(self, "_render_i", 0)
        if i >= self._page_count:
            return

        it = self.list.item(i)
        if it is not None:
            rot = _norm_rot(self._rotations.get(i, 0))
            pix = self._render_thumb(i, rot=rot, target_w=self._thumb_w)

            if rot:
                it.setText(f"{i + 1}  ⟳{rot}°")
            else:
                it.setText(f"{i + 1}")
            it.setIcon(QIcon(pix))

        self._render_i = i + 1
        QTimer.singleShot(0, self._render_step)

    def _render_thumb(self, page_idx: int, rot: int, target_w: int) -> QPixmap:
        # 1. Configurar caja final y área de contenido
        icon_size = self.list.iconSize()
        out_w = max(80, int(icon_size.width()))
        out_h = max(80, int(icon_size.height()))

        content_w = max(40, out_w - (self._thumb_pad * 2))
        content_h = max(40, out_h - (self._thumb_pad * 2))

        # 2. Obtener dimensiones originales para mantener el ratio al renderizar
        ps = self.doc.pagePointSize(page_idx)
        if ps.isEmpty() or ps.width() <= 0 or ps.height() <= 0:
            page_ratio = 1.35
        else:
            page_ratio = float(ps.height()) / float(ps.width())

        # 3. Calcular tamaño de renderizado CORRECTO (sin deformar)
        #    Usamos una resolución alta para calidad, pero respetando 'page_ratio'
        max_side = max(1000, max(content_w, content_h) * 3)

        if page_ratio > 1:  # Es vertical
            render_w = int(max_side / page_ratio)
            render_h = max_side
        else:  # Es horizontal o cuadrado
            render_w = max_side
            render_h = int(max_side * page_ratio)

        # Renderizar: Ahora sí pedimos el tamaño proporcional, no un cuadrado forzado
        img = self.doc.render(page_idx, QSize(render_w, render_h))

        if img.isNull():
            pm = QPixmap(QSize(out_w, out_h))
            pm.fill(Qt.GlobalColor.white)
            return pm

        img = img.convertToFormat(QImage.Format.Format_ARGB32)

        # 4. Rotar la imagen limpia
        rot_n = _norm_rot(rot)
        if rot_n:
            t = QTransform()
            t.rotate(rot_n)
            img = img.transformed(t, Qt.TransformationMode.SmoothTransformation)

        # 5. Escalar para que QUEPA en la celda (KeepAspectRatio)
        #    Esto asegura que se vea toda la hoja sin cortes ni estiramientos
        scaled = img.scaled(
            QSize(content_w, content_h),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 6. Componer en el centro del fondo blanco
        out = QImage(QSize(out_w, out_h), QImage.Format.Format_ARGB32)
        out.fill(0xFFFFFFFF)

        p = QPainter(out)

        # Calcular offset para centrar (letterbox vertical u horizontal)
        x_off = (out_w - scaled.width()) // 2
        y_off = (out_h - scaled.height()) // 2

        p.drawImage(x_off, y_off, scaled)

        # Borde gris alrededor de la hoja real
        p.setPen(Qt.GlobalColor.lightGray)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(x_off - 1, y_off - 1, scaled.width() + 1, scaled.height() + 1)

        p.end()

        return QPixmap.fromImage(out)

    def _selected_index(self) -> Optional[int]:
        sel = self.list.selectedItems()
        if not sel:
            return None
        v = sel[0].data(Qt.ItemDataRole.UserRole)
        try:
            return int(v)
        except Exception:
            return None

    def _rotate_selected(self, delta: int) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        cur = _norm_rot(self._rotations.get(idx, 0))
        new = _norm_rot(cur + delta)
        if new == 0:
            self._rotations.pop(idx, None)
        else:
            self._rotations[idx] = new
        self._refresh_item(idx)
        self._set_status()

    def _rotate_all(self, delta: int) -> None:
        for i in range(self._page_count):
            cur = _norm_rot(self._rotations.get(i, 0))
            new = _norm_rot(cur + delta)
            if new == 0:
                self._rotations.pop(i, None)
            else:
                self._rotations[i] = new
        # refrescar todo (simple)
        self._build_items()
        self._set_status()

    def _refresh_item(self, idx: int) -> None:
        it = self.list.item(idx)
        if it is None:
            return

        rot = _norm_rot(self._rotations.get(idx, 0))
        pix = self._render_thumb(idx, rot=rot, target_w=self._thumb_w)

        if rot:
            it.setText(f"{idx + 1}  ⟳{rot}°")
        else:
            it.setText(f"{idx + 1}")

        it.setIcon(QIcon(pix))

    def _save(self) -> None:
        if not self._rotations:
            QMessageBox.information(self, "Guardar", "No hay rotaciones pendientes.")
            return
        if not PDF_AVAILABLE:
            QMessageBox.critical(self, "Guardar", "No está disponible PyPDF2 ni pypdf para escribir el PDF.")
            return

        src = self.pdf_path
        tmp = src + ".tmp"
        bak = src + ".bak"

        try:
            # backup
            try:
                if os.path.exists(bak):
                    os.remove(bak)
                shutil.copy2(src, bak)
            except Exception:
                # si falla el backup, igual intentamos guardar, pero avisamos
                pass

            reader = PdfReader(src)
            writer = PdfWriter()

            for i, page in enumerate(reader.pages):
                rot = _norm_rot(self._rotations.get(i, 0))
                if rot:
                    _rotate_page_obj(page, rot)
                writer.add_page(page)

            with open(tmp, "wb") as f:
                writer.write(f)

            shutil.move(tmp, src)
            self._rotations.clear()
            self.saved = True
            QMessageBox.information(self, "Guardar", "Rotaciones aplicadas al PDF.")
            self._load()

        except Exception as e:
            # limpiar tmp si quedó
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            QMessageBox.critical(self, "Error al guardar", str(e))
