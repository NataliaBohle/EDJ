# pdf_viewer.py
# Solo modo lectura (QWebEngine PDF seleccionable).
# Incluye un solo botón "Organizar Páginas" que abre un componente aparte: page_organizer.py
#
# Importante (estabilidad):
# - NO usa QDialog.exec() (modal) para evitar crashes con QWebEngine.
# - Se entrega una API "exec()" compatible: internamente hace show() y retorna 0.
#
# Requisitos:
#   pip install PyQt6 PyQt6-WebEngine
#
# Integración esperada:
#   viewer = PdfViewer(doc_data, parent=self, project_id=...)
#   viewer.exec()  # OK: no bloquea, pero no crashea

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QSizePolicy,
)

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

from src.views.components.page_organizer import PageOrganizer  # componente aparte


class PdfViewer(QDialog):
    def __init__(self, doc_data: dict | None = None, parent: Optional[QWidget] = None, project_id: str | None = None):
        super().__init__(parent)

        self._doc_data = doc_data or {}
        self._project_id = project_id

        self._pdf_path = self._resolve_doc_path(self._doc_data.get("ruta"), project_id)
        title = self._doc_data.get("titulo") or "Documento"

        self.setWindowTitle(f"Visor PDF - {title}")
        self.resize(1280, 820)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ---- Toolbar minimal ----
        toolbar = QWidget()
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(8)

        self.btn_organize = QPushButton("Organizar Páginas")
        self.btn_organize.clicked.connect(self._open_organizer)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        tl.addWidget(self.btn_organize)
        tl.addWidget(self.lbl_status, 1)

        root.addWidget(toolbar)

        # ---- WebEngine PDF (lectura) ----
        self.web = QWebEngineView(self)
        s = self.web.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        root.addWidget(self.web, 1)

        # Carga inicial
        if self._pdf_path and os.path.exists(self._pdf_path) and self._pdf_path.lower().endswith(".pdf"):
            self._load_pdf(self._pdf_path)
        else:
            self.web.setHtml("<h3 style='font-family:sans-serif'>Documento no encontrado o inválido.</h3>")
            self.btn_organize.setEnabled(False)
            self._set_status("Sin documento")

        # Evitar modalidad real (WebEngine + exec() suele crashear)
        self.setModal(False)

    # ---------- API compatible ----------
    def exec(self) -> int:  # compat con tu app (no bloqueante)
        self.show()
        self.raise_()
        self.activateWindow()
        return 0

    def open_url(self, url: QUrl) -> None:
        if url.isLocalFile():
            self._load_pdf(url.toLocalFile())
        else:
            self.web.setHtml("<h3 style='font-family:sans-serif'>Solo se admiten PDFs locales.</h3>")
            self.btn_organize.setEnabled(False)
            self._set_status("URL no local")

    # ---------- Internals ----------
    def _load_pdf(self, path: str) -> None:
        p = str(Path(path).resolve())
        self._pdf_path = p

        if not os.path.exists(p) or not p.lower().endswith(".pdf"):
            self.web.setHtml("<h3 style='font-family:sans-serif'>Archivo inválido o no es PDF.</h3>")
            self.btn_organize.setEnabled(False)
            self._set_status("Archivo inválido")
            return

        self.btn_organize.setEnabled(True)
        self.web.load(QUrl.fromLocalFile(p))
        self._set_status(os.path.basename(p))

    def _open_organizer(self) -> None:
        if not self._pdf_path or not os.path.exists(self._pdf_path):
            QMessageBox.warning(self, "Organizar páginas", "No hay un PDF válido cargado.")
            return

        # Importante: liberar el PDF desde WebEngine antes de que el organizador escriba.
        # Esto evita locks (Windows) y crashes raros.
        current_pdf = self._pdf_path
        self.web.setUrl(QUrl("about:blank"))

        dlg = PageOrganizer(pdf_path=current_pdf, parent=self)
        dlg.exec()  # este componente NO usa WebEngine, por lo que modal está OK

        # Si el organizador guardó, recargar
        if dlg.saved:
            self._load_pdf(current_pdf)
        else:
            # aunque no guardó, recargar igual para volver al doc
            self._load_pdf(current_pdf)

    def _set_status(self, text: str) -> None:
        self.lbl_status.setText(text)

    @staticmethod
    def _resolve_doc_path(ruta: str | None, project_id: str | None) -> str:
        if not ruta:
            return ""

        ruta_text = str(ruta).replace("/", os.sep).replace("\\", os.sep)

        if os.path.isabs(ruta_text):
            return str(Path(ruta_text).resolve())

        if project_id:
            base = Path(os.getcwd()) / "Ebook" / str(project_id)
            return str((base / ruta_text).resolve())

        return str((Path(os.getcwd()) / ruta_text).resolve())
