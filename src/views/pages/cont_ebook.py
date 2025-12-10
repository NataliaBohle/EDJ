import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QScrollArea, QLabel, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from src.views.components.chapter import Chapter


class ProjectItem(QFrame):
    """Tarjeta simple para mostrar un proyecto en la lista de 'Continuar'"""
    clicked = pyqtSignal(str)  # Emite el ID del proyecto

    def __init__(self, project_id, date, count):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
            }
            QFrame:hover {
                border: 1px solid #3498db;
                background-color: #f0f8ff;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_id = project_id

        layout = QHBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(layout)

        # Info del proyecto
        info_layout = QVBoxLayout()
        lbl_id = QLabel(f"📁 Proyecto ID: {project_id}")
        lbl_id.setStyleSheet("font-weight: bold; font-size: 14px; border: none; background: transparent;")

        lbl_detail = QLabel(f"📅 Creado: {date} | 📄 Expedientes: {count}")
        lbl_detail.setStyleSheet("color: #7f8c8d; font-size: 12px; border: none; background: transparent;")

        info_layout.addWidget(lbl_id)
        info_layout.addWidget(lbl_detail)
        layout.addLayout(info_layout)

        layout.addStretch()

        # Flechita visual
        lbl_arrow = QLabel("▶")
        lbl_arrow.setStyleSheet("color: #bdc3c7; font-size: 16px; border: none; background: transparent;")
        layout.addWidget(lbl_arrow)

    def mousePressEvent(self, event):
        self.clicked.emit(self.project_id)


class ContEbook(QWidget):
    project_selected = pyqtSignal(str)  # Señal para avisar al Main Window

    def __init__(self):
        super().__init__()
        self.setObjectName("ContEbookPage")

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Encabezado
        self.header = Chapter("Continuar Proyecto Existente")
        layout.addWidget(self.header)

        # Área de Scroll para la lista
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setSpacing(10)

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        # Botón de refrescar
        btn_refresh = QPushButton("🔄 Actualizar Lista")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(
            "background-color: #95a5a6; color: white; padding: 8px; border-radius: 4px; border: none;")
        btn_refresh.clicked.connect(self.load_projects)
        layout.addWidget(btn_refresh)

        # Cargar lista inicial
        self.load_projects()

    def load_projects(self):
        """Escanea la carpeta Ebook/ y lista los JSON encontrados."""
        # Limpiar lista anterior
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        base_dir = os.path.join(os.getcwd(), "Ebook")
        if not os.path.exists(base_dir):
            self.container_layout.addWidget(QLabel("No se encontró la carpeta 'Ebook'."))
            return

        found = False
        # Listar carpetas
        for name in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, name)
            json_path = os.path.join(folder_path, f"{name}_fetch.json")

            if os.path.isdir(folder_path) and os.path.exists(json_path):
                found = True
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        timestamp = data.get("timestamp", "Sin fecha")
                        summary = data.get("summary", {})
                        count = summary.get("found", 0)

                        item = ProjectItem(name, timestamp, count)
                        item.clicked.connect(self._on_project_clicked)
                        self.container_layout.addWidget(item)
                except Exception:
                    continue

        if not found:
            self.container_layout.addWidget(QLabel("No hay proyectos guardados aún."))

    def _on_project_clicked(self, project_id):
        self.project_selected.emit(project_id)