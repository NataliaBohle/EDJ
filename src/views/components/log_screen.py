from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QPlainTextEdit, QFileDialog)
from PyQt6.QtCore import QDateTime, Qt, pyqtSignal


class LogScreen(QFrame):
    # 2. Definimos la señal (True = colapsado, False = expandido)
    visibility_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("LogScreen")

        # Layout principal
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        # --- BARRA SUPERIOR ---
        self.control_bar = QFrame()
        self.control_bar.setObjectName("LogControlBar")
        self.control_bar.setFixedHeight(35)

        control_layout = QHBoxLayout(self.control_bar)
        control_layout.setContentsMargins(10, 0, 10, 0)

        title_label = QLabel("Registro de Actividad")
        title_label.setObjectName("LogTitle")
        control_layout.addWidget(title_label)

        control_layout.addStretch()

        self.btn_export = QPushButton("💾 Exportar .txt")
        self.btn_export.setObjectName("BtnLogExport")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_logs)
        control_layout.addWidget(self.btn_export)

        self.btn_toggle = QPushButton("▼")
        self.btn_toggle.setObjectName("BtnLogToggle")
        self.btn_toggle.setFixedSize(30, 25)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.clicked.connect(self.toggle_view)
        control_layout.addWidget(self.btn_toggle)

        self.main_layout.addWidget(self.control_bar)

        # --- ÁREA DE TEXTO ---
        self.log_area = QPlainTextEdit()
        self.log_area.setObjectName("LogArea")
        self.log_area.setReadOnly(True)
        # Eliminamos setMinimumHeight para evitar conflictos con el splitter
        self.main_layout.addWidget(self.log_area)

        self.add_log("Sistema iniciado correctamente.")

    def add_log(self, message):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.log_area.appendPlainText(f"[{timestamp}] {message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )

    def toggle_view(self):
        """Solo oculta/muestra y avisa al padre."""
        if self.log_area.isVisible():
            self.log_area.hide()
            self.btn_toggle.setText("▲")
            # Avisamos que estamos colapsados (True)
            self.visibility_changed.emit(True)
        else:
            self.log_area.show()
            self.btn_toggle.setText("▼")
            # Avisamos que estamos expandidos (False)
            self.visibility_changed.emit(False)

    def export_logs(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Guardar Logs", "", "Text Files (*.txt)"
        )
        if file_name:
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(self.log_area.toPlainText())
            self.add_log(f"Logs exportados exitosamente a: {file_name}")