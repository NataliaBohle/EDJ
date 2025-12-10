from __future__ import annotations
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
from PyQt6.QtCore import Qt


def _circle_icon(color: QColor, size: int = 12) -> QIcon:
    """Dibuja un círculo de color y lo devuelve como QIcon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()

    return QIcon(pm)


def blue_icon() -> QIcon:
    """Ícono circular azul por defecto (detectado)."""
    return _circle_icon(QColor(37, 99, 235))  # blue-600


def status_icon(status: str | None) -> QIcon:
    """Ícono por estado: detectado(azul), edicion(ámbar), verificado(verde), error(rojo)."""
    s = (status or "detectado").strip().lower()
    if s == "verificado":
        return _circle_icon(QColor(16, 185, 129))  # green-500
    if s == "edicion":
        return _circle_icon(QColor(245, 158, 11))  # amber-500
    if s == "error":
        return _circle_icon(QColor(239, 68, 68))  # red-500
    return _circle_icon(QColor(37, 99, 235))  # blue-600 (detectado por defecto)