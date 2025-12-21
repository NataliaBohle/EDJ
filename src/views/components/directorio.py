from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class DirectorioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Directorio descomprimido")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.info_label = QLabel("Estructura de descompresión")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.info_label)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, stretch=1)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #dc2626; font-weight: 600;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        actions = QHBoxLayout()
        actions.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.retry_button = QPushButton("Reintentar descompresión", self)
        self.retry_button.setObjectName("BtnActionPrimary")
        self.retry_button.setVisible(False)
        actions.addWidget(self.retry_button)

        self.close_button = QPushButton("Cerrar", self)
        self.close_button.setObjectName("BtnActionSecondary")
        actions.addWidget(self.close_button)

        layout.addLayout(actions)

        self.close_button.clicked.connect(self.close)

    def set_data(self, estructura: dict | None, errores: list[str] | None,
                 on_retry: Callable[[], None] | None = None) -> None:
        self.tree.clear()

        if estructura:
            root = self._build_tree_item(estructura)
            self.tree.addTopLevelItem(root)
            self.tree.expandAll()
        else:
            placeholder = QTreeWidgetItem(["(Sin datos de descompresión)"])
            self.tree.addTopLevelItem(placeholder)

        if errores:
            error_text = "\n".join(f"• {err}" for err in errores)
            self.error_label.setText(f"Errores detectados:\n{error_text}")
            self.error_label.setVisible(True)
            self.retry_button.setVisible(True)
            if on_retry:
                try:
                    self.retry_button.clicked.disconnect()
                except Exception:
                    pass
                self.retry_button.clicked.connect(on_retry)
        else:
            self.error_label.setVisible(False)
            self.retry_button.setVisible(False)

    def _build_tree_item(self, node: dict) -> QTreeWidgetItem:
        nombre = node.get("nombre") or "(sin nombre)"
        formato = (node.get("formato") or "").lower()

        prefix = "📄"
        if formato == "carpeta":
            prefix = "📁"
        elif formato in {"zip", "rar", "7z"}:
            prefix = "🗜️"

        item = QTreeWidgetItem([f"{prefix} {nombre}"])
        if formato == "carpeta":
            item.setForeground(0, QColor("#1f2937"))
        else:
            item.setForeground(0, QColor("#111827"))

        for child in node.get("contenido", []) or []:
            item.addChild(self._build_tree_item(child))

        return item
