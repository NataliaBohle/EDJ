from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics


class Timeline(QWidget):
    step_clicked = pyqtSignal(int)

    def __init__(self, steps=None, current_step=0, current_status="detectado"):
        super().__init__()
        self.setObjectName("Timeline")
        self.steps = steps or [
            "Detectado", "Descargar", "Convertir",
            "Formatear", "Índice", "Compilar"
        ]
        self.current_step = current_step

        # Estado actual usando el estándar del sistema
        self.current_status = current_status

        self.setMinimumHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.margin_x = 30
        self.y_center = 20
        self.circle_radius = 6
        self.step_spacing = 0

        # --- COLORES ESTÁNDAR (Coincidentes con status_icons.py) ---
        self.COLORS = {
            "detectado": QColor(37, 99, 235),  # Azul (Listo/Esperando)
            "edicion": QColor(245, 158, 11),  # Ámbar (Trabajando)
            "verificado": QColor(16, 185, 129),  # Verde (Completado)
            "error": QColor(239, 68, 68),  # Rojo (Fallo)
            "pending": QColor("#bdc3c7"),  # Gris (Futuro/Inactivo)
            "text": QColor("#555555")  # Texto
        }

    def set_current_step(self, step_index, status="detectado"):
        """Actualiza el paso y su estado (detectado, edicion, verificado, error)."""
        self.current_step = step_index
        self.current_status = status
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        total_steps = len(self.steps)
        if total_steps > 1:
            self.step_spacing = (width - 2 * self.margin_x) / (total_steps - 1)

        # 1. DIBUJAR LÍNEAS DE CONEXIÓN
        # Línea base gris (todo el largo)
        pen_bg = QPen(self.COLORS["pending"], 2)
        painter.setPen(pen_bg)
        start_x = self.margin_x
        end_x = width - self.margin_x
        painter.drawLine(int(start_x), self.y_center, int(end_x), self.y_center)

        # Línea de progreso
        if self.current_step > 0:
            # La parte "ya recorrida" siempre es VERDE (Verificado)
            pen_done = QPen(self.COLORS["verificado"], 2)
            painter.setPen(pen_done)

            # Calculamos el punto anterior al actual
            prev_x = self.margin_x + ((min(self.current_step, total_steps) - 1) * self.step_spacing)
            painter.drawLine(int(start_x), self.y_center, int(prev_x), self.y_center)

            # La línea que conecta el anterior con el ACTUAL toma el color del estado ACTUAL
            # (Ej: Si estoy en 'edicion', la línea que llega a mí es ámbar)
            if self.current_step < total_steps:
                color_current = self.COLORS.get(self.current_status, self.COLORS["detectado"])
                pen_current = QPen(color_current, 2)
                painter.setPen(pen_current)

                curr_x = self.margin_x + (self.current_step * self.step_spacing)
                painter.drawLine(int(prev_x), self.y_center, int(curr_x), self.y_center)

        # 2. DIBUJAR PUNTOS Y TEXTO
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        fm = QFontMetrics(font)

        for i, label in enumerate(self.steps):
            cx = self.margin_x + (i * self.step_spacing)
            cy = self.y_center

            # Lógica de Color
            if i < self.current_step:
                # Pasos anteriores -> Siempre Verificado (Verde)
                color = self.COLORS["verificado"]
            elif i == self.current_step:
                # Paso actual -> Color dinámico (Azul, Ámbar, Rojo, Verde)
                color = self.COLORS.get(self.current_status, self.COLORS["detectado"])
            else:
                # Pasos futuros -> Gris
                color = self.COLORS["pending"]

            # Círculo
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - self.circle_radius), int(cy - self.circle_radius),
                                self.circle_radius * 2, self.circle_radius * 2)

            # Texto
            painter.setPen(self.COLORS["text"])
            text_width = fm.horizontalAdvance(label)
            painter.drawText(int(cx - text_width / 2), int(cy + self.circle_radius + 12), label)

    def mousePressEvent(self, event):
        click_x = event.pos().x()
        tolerance = 20
        for i in range(len(self.steps)):
            cx = self.margin_x + (i * self.step_spacing)
            if abs(click_x - cx) < tolerance:
                self.step_clicked.emit(i)
                break