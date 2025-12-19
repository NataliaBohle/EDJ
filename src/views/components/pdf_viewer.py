from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
)


class PdfViewer(QDialog):
    def __init__(self, doc_data: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Visor PDF")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        title = doc_data.get("titulo") if isinstance(doc_data, dict) else None
        ruta = doc_data.get("ruta") if isinstance(doc_data, dict) else None
        self._doc_path = str(ruta or "")
        self._mode = "normal"

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

        self.btn_rotate = QPushButton("Rotar PDF", self)
        self.btn_rotate.clicked.connect(self._rotate_pdf)
        controls.addWidget(self.btn_rotate)

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

        self.viewer_status = QLabel("Vista previa en construcción.", self)
        self.viewer_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer_status.setStyleSheet("color: #666;")
        layout.addWidget(self.viewer_status)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "grid":
            zoom = self.zoom_slider.value()
            self.viewer_status.setText(f"Vista en grid activa (zoom {zoom}%).")
        else:
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
            self.viewer_status.setText(f"Vista en grid activa (zoom {value}%).")

    def _rotate_pdf(self) -> None:
        self.viewer_status.setText("Rotación del PDF pendiente de implementación.")
