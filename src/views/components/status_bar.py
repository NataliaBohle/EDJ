from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup


class StatusBar(QWidget):
    """Barra de estado con botones exclusivos: Detectado, Edición, Verificado, Error.

    Expone:
    - signal status_changed(str)
    - get_status() -> str | None
    - set_status(str | None)
    """

    status_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.btn_detected = QPushButton("Detectado", self)
        self.btn_detected.setObjectName("StatusDetected")
        self.btn_detected.setCheckable(True)

        self.btn_editing = QPushButton("Edición", self)
        self.btn_editing.setObjectName("StatusEditing")
        self.btn_editing.setCheckable(True)

        self.btn_verified = QPushButton("Verificado", self)
        self.btn_verified.setObjectName("StatusVerified")
        self.btn_verified.setCheckable(True)

        self.btn_error = QPushButton("Error", self)
        self.btn_error.setObjectName("StatusError")
        self.btn_error.setCheckable(True)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.addButton(self.btn_detected)
        self._group.addButton(self.btn_editing)
        self._group.addButton(self.btn_verified)
        self._group.addButton(self.btn_error)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addStretch()
        lay.addWidget(self.btn_detected)
        lay.addWidget(self.btn_editing)
        lay.addWidget(self.btn_verified)
        lay.addWidget(self.btn_error)
        lay.addStretch()

        # Emitir cuando cambie alguno (sólo en activación)
        self.btn_detected.toggled.connect(self._on_toggled)
        self.btn_editing.toggled.connect(self._on_toggled)
        self.btn_verified.toggled.connect(self._on_toggled)
        self.btn_error.toggled.connect(self._on_toggled)

    # ---- API ----
    def _on_toggled(self, checked: bool) -> None:
        if not checked:
            return
        st = self.get_status()
        if st:
            self.status_changed.emit(st)

    def get_status(self) -> str | None:
        if self.btn_detected.isChecked():
            return "detectado"
        if self.btn_editing.isChecked():
            return "edicion"
        if self.btn_verified.isChecked():
            return "verificado"
        if self.btn_error.isChecked():
            return "error"
        return None

    def set_status(self, status: str | None) -> None:
        s = (status or "").strip().lower()
        if s == "detectado":
            self.btn_detected.setChecked(True)
        elif s == "edicion":
            self.btn_editing.setChecked(True)
        elif s == "verificado":
            self.btn_verified.setChecked(True)
        elif s == "error":
            self.btn_error.setChecked(True)
        else:
            # limpiar selección
            self.btn_detected.setChecked(False)
            self.btn_editing.setChecked(False)
            self.btn_verified.setChecked(False)
            self.btn_error.setChecked(False)
