from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel


# Usamos QFrame porque ya sabe obedecer a los estilos (CSS) nativamente
class Header(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("Header")
        self.setFixedHeight(60)

        # Layout Principal (Horizontal)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 5, 10, 5)
        self.setLayout(main_layout)

        # --- CAJITA VERTICAL PARA TEXTOS ---
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)  # Sin separación extra
        text_layout.setContentsMargins(90, 0, 0, 0)  # Sin márgenes internos

        # Título
        title = QLabel("Extractor de Expedientes SEIA")
        title.setObjectName("HeaderTitle")
        text_layout.addWidget(title)

        # Subtítulo
        subtitle = QLabel("Procesos v.5 - UI v.1")
        subtitle.setObjectName("HeaderSubTitle")
        text_layout.addWidget(subtitle)

        # Agregamos los textos al layout principal
        main_layout.addLayout(text_layout)

        # Espacio flexible para empujar todo a la izquierda
        main_layout.addStretch()