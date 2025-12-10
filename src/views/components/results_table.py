from __future__ import annotations

from typing import Iterable, List, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.views.components.mini_status import MiniStatusBar


class EditableTableCard(QFrame):
    """Tarjeta reutilizable para mostrar/editar listas de resultados en tabla."""

    status_changed = pyqtSignal(str)
    data_changed = pyqtSignal()

    def __init__(self, title: str, columns: Iterable[Tuple[str, str]], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("TableCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.columns: List[Tuple[str, str]] = list(columns)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        title_label = QLabel(f"<b>{title}</b>")
        header.addWidget(title_label, stretch=1)

        self.status_bar = MiniStatusBar(self)
        self.status_bar.setFixedWidth(140)
        self.status_bar.status_changed.connect(self.status_changed)
        header.addWidget(self.status_bar)

        layout.addLayout(header)

        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([label for _key, label in self.columns])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.table.cellChanged.connect(self.data_changed.emit)
        layout.addWidget(self.table)

        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.btn_add_row = QPushButton("Agregar fila", self)
        self.btn_add_row.setObjectName("BtnActionSecondary")
        self.btn_add_row.clicked.connect(self._add_empty_row)
        controls_layout.addWidget(self.btn_add_row)
        layout.addLayout(controls_layout)

    # ---- API pública ----
    def set_status(self, status: str | None) -> None:
        self.status_bar.set_status(status)

    def get_status(self) -> str | None:
        return self.status_bar.get_status()

    def set_data(self, rows: Iterable[dict]) -> None:
        """Reemplaza el contenido de la tabla con la lista de diccionarios dada."""
        data_list = list(rows) if rows else []
        blocked = self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            for row_data in data_list:
                self._append_row(row_data)
        finally:
            self.table.blockSignals(blocked)

    def get_data(self) -> List[dict]:
        """Retorna los datos de la tabla como lista de diccionarios."""
        results: List[dict] = []
        for row in range(self.table.rowCount()):
            item_data: dict[str, str] = {}
            for col, (key, _label) in enumerate(self.columns):
                item = self.table.item(row, col)
                item_data[key] = item.text() if item else ""
            results.append(item_data)
        return results

    # ---- Internos ----
    def _append_row(self, values: dict | None = None) -> None:
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        values = values or {}
        for col, (key, _label) in enumerate(self.columns):
            text = str(values.get(key, "")) if values else ""
            self.table.setItem(row_idx, col, QTableWidgetItem(text))

    def _add_empty_row(self) -> None:
        self._append_row({})
        self.data_changed.emit()

