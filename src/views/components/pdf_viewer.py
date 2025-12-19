import os
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QSpinBox,
)


class PdfViewer(QDialog):
    def __init__(self, doc_data: dict | None = None, parent=None, project_id: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Visor PDF")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        title = doc_data.get("titulo") if isinstance(doc_data, dict) else None
        ruta = doc_data.get("ruta") if isinstance(doc_data, dict) else None
        self._doc_path = self._resolve_doc_path(ruta, project_id)
        self._mode = "normal"
        self._rotation = 0

        title_label = QLabel(title or "Documento EXEVA", self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        route_label = QLabel(f"Ruta: {ruta or 'Pendiente'}", self)
        route_label.setWordWrap(True)
        layout.addWidget(route_label)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.btn_normal = QPushButton("Vista normal", self)
        self.btn_normal.clicked.connect(lambda: self._set_mode("normal"))
        controls.addWidget(self.btn_normal)

        self.btn_grid = QPushButton("Vista grid", self)
        self.btn_grid.clicked.connect(lambda: self._set_mode("grid"))
        controls.addWidget(self.btn_grid)

        self.btn_open_default = QPushButton("Abrir en aplicación", self)
        self.btn_open_default.clicked.connect(self._open_default_app)
        controls.addWidget(self.btn_open_default)

        self.btn_rotate_left = QPushButton("⟲", self)
        self.btn_rotate_left.setToolTip("Rotar a la izquierda")
        self.btn_rotate_left.clicked.connect(lambda: self._rotate_pdf(-90))
        controls.addWidget(self.btn_rotate_left)

        self.btn_rotate_right = QPushButton("⟳", self)
        self.btn_rotate_right.setToolTip("Rotar a la derecha")
        self.btn_rotate_right.clicked.connect(lambda: self._rotate_pdf(90))
        controls.addWidget(self.btn_rotate_right)

        layout.addLayout(controls)

        zoom_row = QHBoxLayout()
        zoom_label = QLabel("Zoom grid:", self)
        zoom_row.addWidget(zoom_label)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._update_grid_zoom)
        zoom_row.addWidget(self.zoom_slider, stretch=1)
        layout.addLayout(zoom_row)

        self.pdf_document = QPdfDocument(self)
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.pdf_document)
        layout.addWidget(self.pdf_view, stretch=1)

        paginator = QHBoxLayout()
        paginator.addStretch(1)
        paginator_label = QLabel("Página", self)
        paginator.addWidget(paginator_label)

        self.page_selector = QSpinBox(self)
        self.page_selector.setMinimum(1)
        self.page_selector.setMaximum(1)
        self.page_selector.valueChanged.connect(self._jump_to_page)
        paginator.addWidget(self.page_selector)

        self.page_total_label = QLabel("de 0", self)
        paginator.addWidget(self.page_total_label)
        paginator.addStretch(1)
        layout.addLayout(paginator)

        self.viewer_status = QLabel("", self)
        self.viewer_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer_status.setStyleSheet("color: #666;")
        layout.addWidget(self.viewer_status)

        self._load_document()
        self._set_mode(self._mode)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self._apply_page_mode(mode)
        if mode == "grid":
            zoom = self.zoom_slider.value()
            self._apply_zoom(zoom)
            self.viewer_status.setText(f"Vista en grid activa (zoom {zoom}%).")
        else:
            self._apply_zoom(100)
            self.viewer_status.setText("Vista normal activa.")

    def _open_default_app(self) -> None:
        if not self._doc_path:
            self.viewer_status.setText("No hay ruta disponible para abrir.")
            return
        doc_path = Path(self._doc_path)
        url = QUrl.fromLocalFile(str(doc_path))
        if not QDesktopServices.openUrl(url):
            self.viewer_status.setText("No se pudo abrir la aplicación por defecto.")

    def _update_grid_zoom(self, value: int) -> None:
        if self._mode == "grid":
            self._apply_zoom(value)
            self.viewer_status.setText(f"Vista en grid activa (zoom {value}%).")

    def _rotate_pdf(self, delta: int) -> None:
        self._rotation = (self._rotation + delta) % 360
        if hasattr(self.pdf_view, "setRotation"):
            self.pdf_view.setRotation(self._rotation)
        elif hasattr(self.pdf_view, "setPageRotation"):
            self.pdf_view.setPageRotation(self._rotation)
        else:
            self.viewer_status.setText("Rotación no soportada por el visor actual.")

    def _resolve_doc_path(self, ruta: str | None, project_id: str | None) -> str:
        if not ruta:
            return ""
        ruta_text = str(ruta)
        if os.path.isabs(ruta_text):
            return ruta_text
        if project_id:
            base = Path(os.getcwd()) / "Ebook" / project_id
            return str((base / ruta_text).resolve())
        return str(Path(ruta_text).resolve())

    def _load_document(self) -> None:
        if not self._doc_path:
            self.viewer_status.setText("Documento sin ruta disponible.")
            return
        if not os.path.exists(self._doc_path):
            self.viewer_status.setText("No se encontró el archivo del documento.")
            return
        status = self.pdf_document.load(self._doc_path)
        if status == QPdfDocument.Status.Ready:
            total = max(self.pdf_document.pageCount(), 1)
            self.page_selector.blockSignals(True)
            self.page_selector.setMaximum(total)
            self.page_selector.setValue(1)
            self.page_selector.blockSignals(False)
            self.page_total_label.setText(f"de {total}")
            self.viewer_status.setText("")
        else:
            self.viewer_status.setText("No se pudo cargar el PDF.")

    def _apply_page_mode(self, mode: str) -> None:
        page_mode = getattr(QPdfView.PageMode, "MultiPage", QPdfView.PageMode.SinglePage)
        self.pdf_view.setPageMode(page_mode)

    def _apply_zoom(self, zoom_percent: int) -> None:
        self.pdf_view.setZoomFactor(max(0.1, zoom_percent / 100.0))

    def _jump_to_page(self, page: int) -> None:
        if hasattr(self.pdf_view, "setPage"):
            self.pdf_view.setPage(max(0, page - 1))
