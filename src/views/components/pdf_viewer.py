from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout


class PdfViewer(QDialog):
    def __init__(self, doc_data: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Visor PDF")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        title = doc_data.get("titulo") if isinstance(doc_data, dict) else None
        ruta = doc_data.get("ruta") if isinstance(doc_data, dict) else None

        title_label = QLabel(title or "Documento EXEVA", self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        route_label = QLabel(f"Ruta: {ruta or 'Pendiente'}", self)
        route_label.setWordWrap(True)
        layout.addWidget(route_label)

        placeholder = QLabel("Vista previa en construcción.", self)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #666;")
        layout.addWidget(placeholder)
