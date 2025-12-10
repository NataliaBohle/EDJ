from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget, QPushButton
from PyQt6.QtCore import Qt


class Sidebar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")

        # Layout principal de la barra
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        # 1. Título o Cabecera del Sidebar
        self.title_label = QLabel("PANEL DE CONTROL")
        self.title_label.setObjectName("SidebarTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        # 2. Área Scrollable (Para tus elementos dinámicos)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)  # Sin borde feo
        self.scroll_area.setObjectName("SidebarScroll")

        # Contenedor interno donde irán los widgets reales
        self.container = QWidget()
        self.container.setObjectName("SidebarContainer")

        # Layout para los elementos (se irán apilando hacia arriba)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(5)

        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        # --- Ejemplo: Agregar un botón de prueba ---
        self.add_option("Opción General")

    def add_option(self, text):
        """Método helper para agregar botones dinámicamente desde fuera."""
        btn = QPushButton(text)
        btn.setObjectName("SidebarButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.container_layout.addWidget(btn)