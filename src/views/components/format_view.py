from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QHeaderView,
    QAbstractItemView,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QMessageBox,
)
from PyQt6.QtGui import QDesktopServices

from src.views.components.mini_status import MiniStatusBar
from src.views.components.pdf_viewer import PdfViewer


class FormatViewDialog(QDialog):
    SUMMARY_COLUMNS = [
        "PDF",
        "DOC",
        "XLS",
        "TXT",
        "GEO",
        "Comprimidos",
        "Carpetas",
        "Otros",
    ]

    def __init__(self, title: str, files: list[dict], parent=None, project_id: str | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Formatos asociados: {title}")
        self.resize(1100, 650)

        self.files = list(files)
        self.display_files = [item for item in self.files if isinstance(item, dict)]
        self.project_id = project_id

        layout = QVBoxLayout(self)

        lbl_info = QLabel("Resumen de formatos detectados para este documento.")
        lbl_info.setStyleSheet("color: #555; margin-bottom: 6px;")
        layout.addWidget(lbl_info)

        self.summary_table = QTableWidget()
        self.summary_table.setRowCount(1)
        self.summary_table.setColumnCount(len(self.SUMMARY_COLUMNS))
        self.summary_table.setHorizontalHeaderLabels(self.SUMMARY_COLUMNS)
        self.summary_table.setWordWrap(False)
        self.summary_table.setShowGrid(False)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setStyleSheet(
            "QTableWidget { background-color: #fff; border: 1px solid #ddd; }"
            "QTableWidget::item { border-bottom: 1px solid #f0f0f0; padding-left: 5px; }"
            "QHeaderView::section { background-color: #f8f9fa; padding: 4px; border: none; font-weight: bold; color: #555; }"
        )

        header = self.summary_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.summary_table)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(7)
        self.files_table.setHorizontalHeaderLabels(
            [
                "Código",
                "Nombre",
                "Formato",
                "Ver archivo",
                "Formatear",
                "Reemplazar",
                "Estado",
            ]
        )
        self.files_table.setWordWrap(False)
        self.files_table.setShowGrid(False)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.files_table.verticalHeader().setDefaultSectionSize(44)
        self.files_table.setStyleSheet(
            "QTableWidget { background-color: #fff; border: 1px solid #ddd; }"
            "QTableWidget::item { border-bottom: 1px solid #f0f0f0; padding-left: 5px; }"
            "QHeaderView::section { background-color: #f8f9fa; padding: 4px; border: none; font-weight: bold; color: #555; }"
        )

        files_header = self.files_table.horizontalHeader()
        files_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        files_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        files_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        files_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        files_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        files_header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        files_header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.files_table)

        self.placeholder = QLabel(
            "El visor de formatos se completará en la siguiente etapa."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: #777; margin-top: 10px;")
        layout.addWidget(self.placeholder)

        self._populate_summary()
        self._populate_files()

    def _populate_summary(self) -> None:
        counts = {key: 0 for key in self.SUMMARY_COLUMNS}
        for item in self.files:
            if not isinstance(item, dict):
                continue
            fmt = self._infer_format(item)
            category = self._categorize_format(fmt)
            counts[category] += 1

        for col_idx, col_name in enumerate(self.SUMMARY_COLUMNS):
            item = QTableWidgetItem(str(counts[col_name]))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.summary_table.setItem(0, col_idx, item)

    def _populate_files(self) -> None:
        self.files_table.setRowCount(0)
        for row_idx, item in enumerate(self.display_files):
            self.files_table.insertRow(row_idx)

            code = self._format_code(item.get("n"))
            name = self._format_name(item)
            fmt = item.get("formato") or self._infer_format(item)

            code_item = QTableWidgetItem(code)
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.files_table.setItem(row_idx, 0, code_item)
            self.files_table.setItem(row_idx, 1, QTableWidgetItem(name))
            self.files_table.setItem(row_idx, 2, QTableWidgetItem(str(fmt)))

            self._add_action_btn(row_idx, 3, "Ver", self._open_file, enabled=bool(item.get("ruta")))
            self._add_action_btn(row_idx, 4, "Formatear", self._format_file)
            self._add_action_btn(row_idx, 5, "Reemplazar", self._replace_file)

            status_widget = MiniStatusBar(self.files_table)
            status_widget.set_status((item.get("estado_formato") or "detectado"))
            self.files_table.setCellWidget(row_idx, 6, status_widget)

    def _add_action_btn(self, row: int, col: int, text: str, callback, enabled: bool = True) -> None:
        btn = QPushButton(text)
        btn.setEnabled(enabled)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(78, 26)
        btn.setStyleSheet(
            """
            QPushButton {
                border: 1px solid #cbd5f5;
                border-radius: 4px;
                background: #e0edff;
                color: #1d4ed8;
            }
            QPushButton:hover {
                background-color: #c7dcff;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #aaa;
                border-color: #eee;
            }
            """
        )
        btn.clicked.connect(lambda _, r=row: callback(r))

        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn)
        self.files_table.setCellWidget(row, col, wrapper)

    def _open_file(self, row: int) -> None:
        item = self.display_files[row]
        ruta = item.get("ruta")
        if not ruta:
            return
        file_path = self._resolve_path(str(ruta))
        if not file_path:
            QMessageBox.warning(self, "Archivo no encontrado", "No se encontró el archivo.")
            return
        if file_path.lower().endswith(".pdf"):
            viewer = PdfViewer({"ruta": file_path, "titulo": item.get("titulo") or item.get("nombre")}, self, self.project_id)
            viewer.exec()
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def _format_file(self, _row: int) -> None:
        QMessageBox.information(self, "Formatear", "Acción de formateo pendiente de implementación.")

    def _replace_file(self, _row: int) -> None:
        QMessageBox.information(self, "Reemplazar", "Acción de reemplazo pendiente de implementación.")

    def _resolve_path(self, ruta: str) -> str:
        ruta_text = str(ruta)
        if Path(ruta_text).is_absolute():
            return str(Path(ruta_text).resolve())
        if self.project_id:
            base = Path.cwd() / "Ebook" / str(self.project_id)
            return str((base / ruta_text).resolve())
        return str((Path.cwd() / ruta_text).resolve())

    def _format_code(self, code: str | None) -> str:
        if not code:
            return ""
        parts = str(code).split(".")
        cleaned = []
        for part in parts:
            stripped = part.lstrip("0")
            cleaned.append(stripped if stripped else "0")
        return ".".join(cleaned)

    def _format_name(self, item: dict) -> str:
        for key in ("titulo", "nombre", "archivo"):
            value = item.get(key)
            if value:
                return str(value)
        ruta = item.get("ruta")
        if ruta:
            return Path(str(ruta)).name
        return "Archivo"

    def _infer_format(self, item: dict) -> str:
        candidates = [
            item.get("formato"),
            item.get("ruta"),
            item.get("url"),
            item.get("archivo"),
            item.get("nombre"),
            item.get("titulo"),
        ]
        for value in candidates:
            fmt = self._format_from_value(value)
            if fmt:
                return fmt
        return "otros"

    def _format_from_value(self, value: str | None) -> str | None:
        if not value:
            return None
        value_text = str(value).strip().lower()
        if value_text == "carpeta":
            return "carpeta"
        if value_text.startswith("http"):
            value_text = value_text.split("?", 1)[0]
        suffix = Path(value_text).suffix.lower()
        if suffix:
            return suffix.lstrip(".")
        return value_text if value_text else None

    def _categorize_format(self, fmt: str | None) -> str:
        if not fmt:
            return "Otros"
        fmt_lower = fmt.strip().lower()
        if fmt_lower == "carpeta":
            return "Carpetas"
        if fmt_lower in {"pdf"}:
            return "PDF"
        if fmt_lower in {"doc", "docx", "rtf", "odt", "wpd"}:
            return "DOC"
        if fmt_lower in {"xls", "xlsx", "csv", "parquet"}:
            return "XLS"
        if fmt_lower in {"txt", "md", "log"}:
            return "TXT"
        if fmt_lower in {"shp", "shx", "dbf", "prj", "kml", "kmz", "geojson", "gml", "gpkg", "tif", "tiff"}:
            return "GEO"
        if fmt_lower in {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz", "tar.gz", "tar.bz2", "tar.xz"}:
            return "Comprimidos"
        return "Otros"
