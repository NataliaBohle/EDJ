from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QComboBox
from PyQt6.QtGui import QColor

# Reutilizar helper de íconos de estado si está disponible
try:
    from .status_icons import _circle_icon  # type: ignore
except Exception:
    _circle_icon = None  # fallback más abajo


class MiniStatusBar(QWidget):
    """Selector compacto de estado para campos: lista desplegable.

    Reemplaza los tres botones por un QComboBox para evitar crashes y
    simplificar la interacción. Mantiene la misma API pública:
      - señal status_changed(str)
      - get_status() -> str | None
      - set_status(str | None) -> None
    """

    status_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.combo = QComboBox(self)
        # Orden consistente con el resto de la app
        self._values = [
            ("Detectado", "detectado"),
            ("Edición", "edicion"),
            ("Verificado", "verificado"),
            ("Error", "error"),
        ]
        # Colores por estado
        colors = {
            "detectado": QColor(37, 99, 235),     # azul
            "edicion": QColor(245, 158, 11),      # ámbar
            "verificado": QColor(16, 185, 129),   # verde
            "error": QColor(239, 68, 68),         # rojo
        }

        for label, val in self._values:
            # Icono coloreado
            if _circle_icon:
                icon = _circle_icon(colors[val])  # type: ignore[index]
            else:
                # Fallback simple sin dependencia: sin icono
                icon = None
            if icon is not None:
                idx = self.combo.count()
                self.combo.addItem(icon, label)
            else:
                self.combo.addItem(label)
            # Color de texto del item
            idx = self.combo.count() - 1
            try:
                self.combo.setItemData(idx, colors[val], Qt.ItemDataRole.ForegroundRole)
            except Exception:
                pass

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.combo)

        # Emitir estado normalizado cuando cambia la selección
        self.combo.currentIndexChanged.connect(self._on_changed)

    # ---- API ----
    def _on_changed(self, _index: int) -> None:
        st = self.get_status()
        if st:
            self.status_changed.emit(st)

    def get_status(self) -> str | None:
        idx = self.combo.currentIndex()
        if 0 <= idx < len(self._values):
            return self._values[idx][1]
        return None

    def set_status(self, status: str | None) -> None:
        s = (status or "").strip().lower()
        # Evitar emitir durante el set programático
        blocked = self.combo.blockSignals(True)
        try:
            if not s:
                self.combo.setCurrentIndex(0)
                return
            for i, (_label, val) in enumerate(self._values):
                if val == s:
                    self.combo.setCurrentIndex(i)
                    return
            # Si no hay coincidencia exacta, dejar en Detectado
            self.combo.setCurrentIndex(0)
        finally:
            self.combo.blockSignals(blocked)
