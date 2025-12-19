from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)


class LinksReviewDialog(QDialog):
    def __init__(self, links: Iterable[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Revisión de anexos y vínculos")
        self.setMinimumWidth(720)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        links_list = list(links)
        if not links_list:
            layout.addWidget(QLabel("No hay anexos o vínculos detectados."))
            self._add_footer(layout)
            return

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Tipo", "Título", "URL", "Origen", "Info", "Abrir"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setRowCount(len(links_list))

        for row_idx, link in enumerate(links_list):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(link.get("tipo", ""))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(link.get("titulo", ""))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(link.get("url", ""))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(link.get("origen", ""))))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(link.get("info_extra", ""))))

            button = QPushButton("Abrir")
            button.setObjectName("BtnActionSecondary")
            button.clicked.connect(lambda _checked=False, url=link.get("url", ""): self._open_url(url))
            self.table.setCellWidget(row_idx, 5, button)

        layout.addWidget(self.table)
        self._add_footer(layout)

    def _add_footer(self, layout: QVBoxLayout) -> None:
        footer = QHBoxLayout()
        footer.addStretch(1)
        close_btn = QPushButton("Cerrar")
        close_btn.setObjectName("BtnActionSecondary")
        close_btn.clicked.connect(self.close)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def _open_url(self, url: str) -> None:
        if not url:
            return
        QDesktopServices.openUrl(QUrl(url))
