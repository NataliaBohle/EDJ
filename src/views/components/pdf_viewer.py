import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QPixmap, QTransform
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QSpinBox,
    QScrollArea,
    QMessageBox,
    QWidget,
    QGridLayout,
)


class _ThumbLabel(QLabel):
    clicked = pyqtSignal(int)
    doubleClicked = pyqtSignal(int)

    def __init__(self, page_index: int, parent=None) -> None:
        super().__init__(parent)
        self._page_index = page_index
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._page_index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit(self._page_index)
        super().mouseDoubleClickEvent(event)


class PdfViewer(QDialog):
    """
    Visor PDF basado en QPdfDocument (render a imagen) para asegurar:
      - Conteo de páginas confiable
      - Rotación real (0/90/180/270)
      - Vista grid tipo Acrobat (miniaturas en filas/columnas)
    """

    def __init__(self, doc_data: dict | None = None, parent=None, project_id: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Visor PDF")
        self.setMinimumWidth(420)

        self._mode = "normal"
        # Rotación pendiente (edición real del PDF): delta por página en grados (0/90/180/270)
        self._page_rotation_delta: dict[int, int] = {}
        self._dirty_rotations = False
        self._current_page = 0  # 0-index
        self._thumb_target_width = 220  # base
        self._thumb_cache: dict[tuple[int, int, int], QPixmap] = {}  # (page, width, rotation)->pixmap

        title = doc_data.get("titulo") if isinstance(doc_data, dict) else None
        ruta = doc_data.get("ruta") if isinstance(doc_data, dict) else None
        self._doc_path = self._resolve_doc_path(ruta, project_id)

        layout = QVBoxLayout(self)

        title_label = QLabel(title or "Documento EXEVA", self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        route_label = QLabel(f"Ruta: {ruta or 'Pendiente'}", self)
        route_label.setWordWrap(True)
        layout.addWidget(route_label)

        # Controls
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

        # Rotación (edición del documento)
        self.btn_rot_all_left = QPushButton("⟲todas", self)
        self.btn_rot_all_left.setToolTip("Rotar TODAS las páginas a la izquierda")
        self.btn_rot_all_left.clicked.connect(lambda: self._rotate_all_pages(-90))
        controls.addWidget(self.btn_rot_all_left)

        self.btn_rot_current_left = QPushButton("⟲actual", self)
        self.btn_rot_current_left.setToolTip("Rotar la página actual a la izquierda")
        self.btn_rot_current_left.clicked.connect(lambda: self._rotate_current_page(-90))
        controls.addWidget(self.btn_rot_current_left)

        self.btn_rot_current_right = QPushButton("⟳actual", self)
        self.btn_rot_current_right.setToolTip("Rotar la página actual a la derecha")
        self.btn_rot_current_right.clicked.connect(lambda: self._rotate_current_page(90))
        controls.addWidget(self.btn_rot_current_right)

        self.btn_rot_all_right = QPushButton("⟳todas", self)
        self.btn_rot_all_right.setToolTip("Rotar TODAS las páginas a la derecha")
        self.btn_rot_all_right.clicked.connect(lambda: self._rotate_all_pages(90))
        controls.addWidget(self.btn_rot_all_right)

        layout.addLayout(controls)

        # Grid zoom (solo afecta vista grid)
        zoom_row = QHBoxLayout()
        zoom_label = QLabel("Zoom grid:", self)
        zoom_row.addWidget(zoom_label)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._request_grid_rerender)
        zoom_row.addWidget(self.zoom_slider, stretch=1)
        layout.addLayout(zoom_row)

        # Document
        self.pdf_document = QPdfDocument(self)
        self.pdf_document.statusChanged.connect(self._on_doc_status_changed)

        # Normal view: rendered page inside scroll area
        self.page_label = QLabel(self)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("background: #444;")  # similar a visor de PDF
        self.page_label.setMinimumHeight(240)

        self.normal_scroll = QScrollArea(self)
        self.normal_scroll.setWidgetResizable(False)
        self.normal_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.normal_scroll.setWidget(self.page_label)

        # Grid view: thumbnails in a scrollable grid
        self.grid_container = QWidget(self)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)
        self.grid_layout.setHorizontalSpacing(18)
        self.grid_layout.setVerticalSpacing(18)

        self.grid_scroll = QScrollArea(self)
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setWidget(self.grid_container)

        layout.addWidget(self.normal_scroll, stretch=1)
        layout.addWidget(self.grid_scroll, stretch=1)
        self.grid_scroll.hide()

        # Paginator
        paginator = QHBoxLayout()
        paginator.addStretch(1)
        paginator.addWidget(QLabel("Página", self))

        self.page_selector = QSpinBox(self)
        self.page_selector.setMinimum(1)
        self.page_selector.setMaximum(1)
        self.page_selector.setInvertedControls(True)
        self.page_selector.valueChanged.connect(self._jump_to_page_1based)
        paginator.addWidget(self.page_selector)

        self.page_total_label = QLabel("de 0", self)
        paginator.addWidget(self.page_total_label)
        paginator.addStretch(1)
        layout.addLayout(paginator)

        self.viewer_status = QLabel("", self)
        self.viewer_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer_status.setStyleSheet("color: #666;")
        layout.addWidget(self.viewer_status)

        # Throttle grid rerenders when dragging slider
        self._grid_rerender_timer = QTimer(self)
        self._grid_rerender_timer.setSingleShot(True)
        self._grid_rerender_timer.timeout.connect(self._render_grid)

        self._load_view_state()
        self._load_document()
        self._set_mode(self._mode)

    # ---------- UI / mode ----------
    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "grid":
            self.normal_scroll.hide()
            self.grid_scroll.show()
            self._render_grid()
            self.viewer_status.setText(f"Vista en grid activa (zoom {self.zoom_slider.value()}%).")
        else:
            self.grid_scroll.hide()
            self.normal_scroll.show()
            self._render_current_page()
            self.viewer_status.setText("Vista normal activa.")

    def _open_default_app(self) -> None:
        if not self._doc_path:
            self.viewer_status.setText("No hay ruta disponible para abrir.")
            return
        doc_path = Path(self._doc_path)
        url = QUrl.fromLocalFile(str(doc_path))
        if not QDesktopServices.openUrl(url):
            self.viewer_status.setText("No se pudo abrir la aplicación por defecto.")

    # ---------- rotation ----------
    def _rotate_current_page(self, delta: int) -> None:
        if self.pdf_document.status() != QPdfDocument.Status.Ready:
            return
        total = self.pdf_document.pageCount()
        if total <= 0:
            return
        page = max(0, min(self._current_page, total - 1))
        self._apply_rotation_delta([page], delta)

    def _rotate_all_pages(self, delta: int) -> None:
        if self.pdf_document.status() != QPdfDocument.Status.Ready:
            return
        total = self.pdf_document.pageCount()
        if total <= 0:
            return
        self._apply_rotation_delta(list(range(total)), delta)

    def _apply_rotation_delta(self, pages: list[int], delta: int) -> None:
        # Normalizar delta a múltiplos de 90
        step = delta % 360
        if step not in (0, 90, 180, 270):
            step = 90 if delta > 0 else 270

        changed = False
        for p in pages:
            cur = self._page_rotation_delta.get(p, 0) % 360
            nxt = (cur + step) % 360
            if nxt == 0:
                if p in self._page_rotation_delta:
                    del self._page_rotation_delta[p]
                    changed = True
            else:
                if cur != nxt:
                    self._page_rotation_delta[p] = nxt
                    changed = True

        if not changed:
            return

        self._dirty_rotations = True
        self._thumb_cache.clear()
        if self._mode == "grid":
            self._render_grid()
            self.viewer_status.setText(f"Vista en grid activa (zoom {self.zoom_slider.value()}%).")
        else:
            self._render_current_page()
            self.viewer_status.setText("Vista normal activa.")

    # ---------- path / load ----------
    def _view_state_path(self) -> Path | None:
        if not self._doc_path:
            return None
        path = Path(self._doc_path)
        if path.suffix:
            return path.with_suffix(f"{path.suffix}.view.json")
        return path.with_name(f"{path.name}.view.json")

    def _load_view_state(self) -> None:
        path = self._view_state_path()
        if not path or not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        rotations = data.get("rotations", {})
        if isinstance(rotations, dict):
            self._page_rotation_delta = {}
            for key, value in rotations.items():
                try:
                    page_index = int(key)
                    rotation = int(value) % 360
                except (TypeError, ValueError):
                    continue
                if rotation:
                    self._page_rotation_delta[page_index] = rotation

        page = data.get("page")
        if isinstance(page, int):
            self._pending_restore_page = page

        zoom = data.get("grid_zoom")
        if isinstance(zoom, int):
            self.zoom_slider.setValue(max(50, min(200, zoom)))

        mode = data.get("mode")
        if mode in ("normal", "grid"):
            self._mode = mode

        self._dirty_rotations = False

    def _save_view_state(self) -> None:
        path = self._view_state_path()
        if not path:
            return
        data = {
            "page": self._current_page,
            "rotations": {str(k): v for k, v in self._page_rotation_delta.items()},
            "mode": self._mode,
            "grid_zoom": self.zoom_slider.value(),
        }
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

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

        # En PyQt6, load puede quedar en Loading y luego pasar a Ready.
        self.viewer_status.setText("Cargando PDF...")
        self.pdf_document.load(self._doc_path)

    def _on_doc_status_changed(self, status: QPdfDocument.Status) -> None:
        if status == QPdfDocument.Status.Ready:
            total = max(self.pdf_document.pageCount(), 1)
            self.page_selector.blockSignals(True)
            self.page_selector.setMaximum(total)
            # Restaurar página tras guardado (si aplica) o mantener la actual
            restore = getattr(self, "_pending_restore_page", None)
            if restore is not None:
                try:
                    restore_i = int(restore)
                except Exception:
                    restore_i = 0
                self._current_page = max(0, min(restore_i, total - 1))
                self._pending_restore_page = None
            else:
                self._current_page = min(self._current_page, total - 1)
            self.page_selector.setValue(self._current_page + 1)
            self.page_selector.blockSignals(False)
            self.page_total_label.setText(f"de {total}")
            self.viewer_status.setText("")
            # Render inicial
            if self._mode == "grid":
                self._render_grid()
            else:
                self._render_current_page()
        elif status == QPdfDocument.Status.Error:
            self.viewer_status.setText("No se pudo cargar el PDF.")
        else:
            # Loading / Null
            pass

    # ---------- pagination ----------
    def _jump_to_page_1based(self, page_1based: int) -> None:
        # QSpinBox entrega 1..N
        self._current_page = max(0, page_1based - 1)
        if self._mode == "grid":
            # En grid, saltar también al hacer click se gestiona aparte
            self._set_mode("normal")
        else:
            self._render_current_page()

    # ---------- rendering ----------
    def _page_point_size(self, page_index: int) -> tuple[float, float]:
        # QSizeF en puntos; puede variar por página.
        try:
            sz = self.pdf_document.pagePointSize(page_index)
            return float(sz.width()), float(sz.height())
        except Exception:
            return 595.0, 842.0  # fallback A4 aprox

    def _render_page_pixmap(self, page_index: int, target_width: int, rotation_deg: int) -> QPixmap | None:
        cache_key = (page_index, target_width, rotation_deg)
        if cache_key in self._thumb_cache:
            return self._thumb_cache[cache_key]

        w_pt, h_pt = self._page_point_size(page_index)
        if w_pt <= 0 or h_pt <= 0:
            return None

        aspect = h_pt / w_pt
        target_height = max(1, int(target_width * aspect))
        # Si la página está rotada 90/270, renderiza con dimensiones invertidas para que el ancho final
        # (post-rotación) se mantenga cercano a target_width.
        if rotation_deg % 360 in (90, 270):
            target_size = QSize(target_height, max(1, int(target_width)))
        else:
            target_size = QSize(max(1, int(target_width)), target_height)

        try:
            img = self.pdf_document.render(page_index, target_size)
            if img.isNull():
                return None

            # Algunos backends dejan el fondo transparente; compón sobre blanco para evitar "negros"
            from PyQt6.QtGui import QImage, QPainter

            if img.hasAlphaChannel():
                base = QImage(img.size(), QImage.Format.Format_RGB32)
                base.fill(Qt.GlobalColor.white)
                p = QPainter(base)
                p.drawImage(0, 0, img)
                p.end()
                img = base
            else:
                # asegurar formato consistente
                img = img.convertToFormat(QImage.Format.Format_RGB32)

            if rotation_deg:
                tr = QTransform().rotate(rotation_deg)
                img = img.transformed(tr, Qt.TransformationMode.SmoothTransformation)

            pm = QPixmap.fromImage(img)
            self._thumb_cache[cache_key] = pm
            return pm
        except Exception:
            return None

    def _render_current_page(self) -> None:
        if self.pdf_document.status() != QPdfDocument.Status.Ready:
            return
        total = self.pdf_document.pageCount()
        if total <= 0:
            return

        # Render a un ancho basado en el viewport actual
        viewport_w = max(640, self.normal_scroll.viewport().width() - 24)
        # Un tope para no generar imágenes gigantes (mantener usabilidad)
        viewport_w = min(viewport_w, 1600)

        pm = self._render_page_pixmap(
            self._current_page,
            viewport_w,
            self._page_rotation_delta.get(self._current_page, 0),
        )
        if pm is None:
            self.page_label.setText("No se pudo renderizar la página.")
            return
        self.page_label.setPixmap(pm)
        self.page_label.setFixedSize(pm.size())
        self.page_label.adjustSize()

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        # Re-render de página actual al redimensionar para mantener legibilidad
        if self._mode == "normal":
            self._thumb_cache.clear()
            self._render_current_page()

    def closeEvent(self, event):  # type: ignore[override]
        self._save_view_state()
        super().closeEvent(event)

    # ---------- grid ----------
    def _request_grid_rerender(self, _value: int) -> None:
        if self._mode != "grid":
            return
        # throttle mientras se arrastra
        self._grid_rerender_timer.start(140)

    def _clear_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _render_grid(self) -> None:
        if self.pdf_document.status() != QPdfDocument.Status.Ready:
            return

        total = self.pdf_document.pageCount()
        if total <= 0:
            return

        zoom = self.zoom_slider.value()
        target_w = int(self._thumb_target_width * (zoom / 100.0))
        target_w = max(120, min(target_w, 600))

        # número de columnas aproximado como Acrobat (depende del ancho visible)
        available_w = max(360, self.grid_scroll.viewport().width() - 24)
        col_w = target_w + 18  # spacing
        cols = max(2, min(8, available_w // col_w))

        self._clear_grid()

        row = 0
        col = 0
        for i in range(total):
            wrapper = QWidget(self.grid_container)
            v = QVBoxLayout(wrapper)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(6)

            thumb = _ThumbLabel(i, wrapper)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            border = "2px solid #2f74ff" if i == self._current_page else "1px solid #bbb"
            thumb.setStyleSheet(f"background: #fff; border: {border};")
            pm = self._render_page_pixmap(i, target_w, self._page_rotation_delta.get(i, 0))
            if pm is not None:
                thumb.setPixmap(pm)
                thumb.setFixedSize(pm.size())
            else:
                thumb.setText("Sin preview")
                thumb.setFixedSize(target_w, int(target_w * 1.3))

            thumb.clicked.connect(self._on_thumb_selected)
            thumb.doubleClicked.connect(self._on_thumb_open)
            v.addWidget(thumb)

            num = QLabel(str(i + 1), wrapper)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet("color: #444;")
            v.addWidget(num)

            self.grid_layout.addWidget(wrapper, row, col)

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _on_thumb_selected(self, page_index: int) -> None:
        # Selección en grid (no cambia de vista)
        self._current_page = max(0, page_index)
        self.page_selector.blockSignals(True)
        self.page_selector.setValue(self._current_page + 1)
        self.page_selector.blockSignals(False)
        if self._mode == "grid":
            self._thumb_cache.clear()
            self._render_grid()

    def _on_thumb_open(self, page_index: int) -> None:
        # Doble click: abrir en vista normal
        self._current_page = max(0, page_index)
        self.page_selector.blockSignals(True)
        self.page_selector.setValue(self._current_page + 1)
        self.page_selector.blockSignals(False)
        self._set_mode("normal")
