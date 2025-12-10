from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget, QPushButton
from PyQt6.QtCore import Qt


class Sidebar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        # Título
        self.title_label = QLabel("PANEL DE CONTROL")
        self.title_label.setObjectName("SidebarTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setObjectName("SidebarScroll")

        self.container = QWidget()
        self.container.setObjectName("SidebarContainer")

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(5)

        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        # --- CAMBIO: Ya no agregamos "Opción General" aquí ---
        # La sidebar inicia vacía.

    def add_option(self, text):
        btn = QPushButton(text)
        btn.setObjectName("SidebarButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.container_layout.addWidget(btn)

    def clear(self):
        """Borra todos los botones del sidebar."""
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()