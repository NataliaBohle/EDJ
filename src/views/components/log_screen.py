from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QPlainTextEdit, QFileDialog, QSizePolicy)
from PyQt6.QtCore import QDateTime, Qt


class LogScreen(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("LogScreen")

        # Layout principal vertical
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        # --- 1. BARRA SUPERIOR (Control) ---
        self.control_bar = QFrame()
        self.control_bar.setObjectName("LogControlBar")
        self.control_bar.setFixedHeight(35)

        control_layout = QHBoxLayout(self.control_bar)
        control_layout.setContentsMargins(10, 0, 10, 0)

        # Etiqueta de título
        title_label = QLabel("Registro de Actividad")
        title_label.setObjectName("LogTitle")
        control_layout.addWidget(title_label)

        control_layout.addStretch()  # Empuja botones a la derecha

        # Botón Exportar
        self.btn_export = QPushButton("💾 Guardar registros de la sesión")
        self.btn_export.setObjectName("BtnLogExport")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_logs)
        control_layout.addWidget(self.btn_export)

        # Botón Colapsar/Expandir
        self.btn_toggle = QPushButton("▼")  # Empieza mostrando contenido
        self.btn_toggle.setObjectName("BtnLogToggle")
        self.btn_toggle.setFixedSize(30, 25)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_view)
        control_layout.addWidget(self.btn_toggle)

        self.main_layout.addWidget(self.control_bar)

        # --- 2. ÁREA DE TEXTO (Logs) ---
        self.log_area = QPlainTextEdit()
        self.log_area.setObjectName("LogArea")
        self.log_area.setReadOnly(True)  # El usuario no debe editarlo
        self.log_area.setMinimumHeight(100)  # Altura mínima cuando está abierto
        self.main_layout.addWidget(self.log_area)

        # Mensaje inicial
        self.add_log("Sistema iniciado correctamente.")

    def add_log(self, message):
        """Agrega un mensaje con timestamp al log."""
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.log_area.appendPlainText(f"[{timestamp}] {message}")
        # Scroll automático al final
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )

    def toggle_view(self):
        """Alterna entre colapsar y expandir la vista del log."""
        if self.log_area.isVisible():
            # --- ACCIÓN: COLAPSAR ---
            self.log_area.hide()
            self.btn_toggle.setText("▲")

            # Obligamos al widget a no medir más de 35px (altura de la barra)
            # El Splitter detectará esto y reducirá el espacio automáticamente.
            self.setMaximumHeight(35)

        else:
            # --- ACCIÓN: EXPANDIR ---
            # 1. Quitamos el límite de altura PRIMERO
            self.setMaximumHeight(16777215)  # Constante de Qt para "Sin límite" (QWIDGETSIZE_MAX)
            self.setMinimumHeight(0)

            # 2. Mostramos el área
            self.log_area.show()
            self.btn_toggle.setText("▼")

            # 3. Truco: Si está muy pequeño, forzamos un tamaño inicial cómodo
            if self.height() < 100:
                self.resize(self.width(), 150)

    def export_logs(self):
        """Guarda el contenido actual en un archivo de texto."""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Guardar Logs", "", "Text Files (*.txt)"
        )
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(self.log_area.toPlainText())
            self.add_log( f"Logs exportados exitosamente a: {file_name}")