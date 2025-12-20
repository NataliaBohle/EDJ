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

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QTransform, QAction
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

        bl.addWidget(self.btn_l_all)
        bl.addWidget(self.btn_l_cur)
        bl.addWidget(self.btn_r_cur)
        bl.addWidget(self.btn_r_all)
        bl.addWidget(self.btn_save)
        bl.addWidget(self.btn_close)
        bl.addWidget(self.lbl, 1)

        root.addWidget(bar)

        # Grid thumbs
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setSpacing(10)
        self.list.setUniformItemSizes(True)
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.setIconSize(QSize(240, 320))
        self.list.setStyleSheet("""
            QListWidget::item { border: 1px solid transparent; padding: 6px; }
            QListWidget::item:selected { background: transparent; border: 1px solid #5aa0ff; }
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
        for i in range(self._page_count):
            it = QListWidgetItem(f"{i+1}")
            it.setData(Qt.ItemDataRole.UserRole, i)
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.list.addItem(it)

        self._render_i = 0
        QTimer.singleShot(0, self._render_step)

    def _render_step(self) -> None:
        i = getattr(self, "_render_i", 0)
        if i >= self._page_count:
            return

        it = self.list.item(i)
        if it is not None:
            pix = self._render_thumb(i, target_w=240)
            rot = _norm_rot(self._rotations.get(i, 0))
            if rot:
                pix = self._rotate_pix(pix, rot)
                it.setText(f"{i+1}  ⟳{rot}°")
            else:
                it.setText(f"{i+1}")
            it.setIcon(pix)

        self._render_i = i + 1
        QTimer.singleShot(0, self._render_step)

    def _render_thumb(self, page_idx: int, target_w: int) -> QPixmap:
        ps = self.doc.pagePointSize(page_idx)
        if ps.isEmpty() or ps.width() <= 0 or ps.height() <= 0:
            render_size = QSize(target_w * 3, target_w * 4)
        else:
            ratio = float(ps.height()) / float(ps.width())
            target_h = max(120, int(target_w * ratio))
            render_size = QSize(target_w * 3, target_h * 3)

        img = self.doc.render(page_idx, render_size)
        if img.isNull():
            pm = QPixmap(render_size)
            pm.fill(Qt.GlobalColor.white)
            return pm

        img = img.convertToFormat(QImage.Format.Format_ARGB32)

        # fondo blanco (evita transparencias oscuras)
        out = QImage(img.size(), QImage.Format.Format_ARGB32)
        out.fill(0xFFFFFFFF)
        p = QPainter(out)
        p.drawImage(0, 0, img)
        p.end()

        pm = QPixmap.fromImage(out)
        return pm.scaled(QSize(target_w, int(target_w * 1.4)),
                         Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)

    def _rotate_pix(self, pm: QPixmap, deg: int) -> QPixmap:
        t = QTransform()
        t.rotate(_norm_rot(deg))
        return pm.transformed(t, Qt.TransformationMode.SmoothTransformation)

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
        pix = self._render_thumb(idx, target_w=240)
        rot = _norm_rot(self._rotations.get(idx, 0))
        if rot:
            pix = self._rotate_pix(pix, rot)
            it.setText(f"{idx+1}  ⟳{rot}°")
        else:
            it.setText(f"{idx+1}")
        it.setIcon(pix)

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
