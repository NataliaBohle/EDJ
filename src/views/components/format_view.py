from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QHeaderView,
    QAbstractItemView,
)


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

    def __init__(self, title: str, files: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Formatos asociados: {title}")
        self.resize(1100, 650)

        self.files = list(files)

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

        self.placeholder = QLabel(
            "El visor de formatos se completará en la siguiente etapa."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: #777; margin-top: 10px;")
        layout.addWidget(self.placeholder)

        self._populate_summary()

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
