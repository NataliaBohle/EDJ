from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from src.views.components.mini_status import MiniStatusBar
from src.views.components.timeline import Timeline


class ExpedienteCard(QFrame):
    # Señal cuando hacen clic en la línea de tiempo (para cambiar el paso visualmente)
    step_selected = pyqtSignal(str, int)
    # Señal cuando hacen clic en el botón (Código, Paso Actual) -> Para abrir la herramienta
    action_clicked = pyqtSignal(str, int)
    # --- NUEVA SEÑAL: Reporta el cambio de estado global (código, nuevo_status) ---
    status_updated = pyqtSignal(str, str)

    def __init__(self, title="Expediente", code="ANTGEN", status="detectado", steps=None):
        super().__init__()
        self.setObjectName("ExpedienteCard")
        self.code = code

        # Variable interna para rastrear el paso actual
        self.current_step_index = 0

        # Si no envían pasos, usamos el default completo
        default_steps = [
            "Detectado", "Descargar", "Convertir",
            "Formatear", "Índice", "Compilar"
        ]
        self.steps_list = steps if steps else default_steps

        # Layout Principal
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        self.setLayout(layout)

        # --- LÍNEA 1: Título y Código ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_label = QLabel(f"{title}")
        title_label.setObjectName("CardTitle")

        code_label = QLabel(f"({code})")
        code_label.setObjectName("CardCode")

        header_layout.addWidget(title_label)
        header_layout.addWidget(code_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # --- LÍNEA 2: Timeline | Status | Botón ---
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)

        # Timeline
        self.timeline = Timeline(steps=self.steps_list, current_step=0)
        self.timeline.step_clicked.connect(self._on_timeline_click)
        controls_layout.addWidget(self.timeline, stretch=1)

        # Selector de Estado
        self.status_selector = MiniStatusBar()
        self.status_selector.set_status(status)
        self.status_selector.setFixedWidth(110)

        # --- CONEXIÓN CLAVE: Conectar el desplegable a la función de re-emisión ---
        self.status_selector.status_changed.connect(self._on_status_change)

        controls_layout.addWidget(self.status_selector)

        # Botón de Acción
        self.btn_action = QPushButton("Activar")
        self.btn_action.setObjectName("CardActionButton")  # ID clave para el CSS
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setFixedSize(90, 30)

        # Conectamos a método interno para enviar datos completos
        self.btn_action.clicked.connect(self._on_activate_click)

        # Estado inicial para el estilo (definido en styles.qss)
        self.btn_action.setProperty("status", "detectado")

        controls_layout.addWidget(self.btn_action)

        layout.addLayout(controls_layout)

    # --- NUEVO MÉTODO DE RE-EMISIÓN ---
    def _on_status_change(self, new_status: str):
        """Captura el cambio del MiniStatusBar y lo re-emite con el código."""
        # 1. Avisamos al ProjectView para que guarde en el JSON
        self.status_updated.emit(self.code, new_status)

        # 2. Actualizamos la visualización de la tarjeta (botón y timeline)
        self.update_progress(self.current_step_index, new_status)

    def _on_timeline_click(self, step_index):
        """Reenvía la señal de la línea de tiempo hacia afuera."""
        self.step_selected.emit(self.code, step_index)

    def _on_activate_click(self):
        """Al hacer clic en el botón, avisamos qué expediente y en qué paso está."""
        self.action_clicked.emit(self.code, self.current_step_index)

    def update_progress(self, step_index, step_status="detectado"):
        """Actualiza el progreso visual y el estilo del botón."""
        self.current_step_index = step_index

        # 1. Timeline actualiza los colores
        self.timeline.set_current_step(step_index, step_status)

        # 2. Configurar texto del botón según estado
        if step_status == "edicion":
            self.btn_action.setText("Continuar")
        elif step_status == "error":
            self.btn_action.setText("Reintentar")
        elif step_status == "verificado":
            self.btn_action.setText("Listo")
        else:
            self.btn_action.setText("Activar")

        # 3. Cambio de ESTILO usando Propiedades Dinámicas
        self.btn_action.setProperty("status", step_status)

        # Forzamos a Qt a repintar el estilo inmediatamente
        self.btn_action.style().unpolish(self.btn_action)
        self.btn_action.style().polish(self.btn_action)