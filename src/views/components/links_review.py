from __future__ import annotations

from pathlib import Path
import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QMessageBox, QLabel, QWidget, QAbstractItemView
)
from PyQt6.QtGui import QColor, QDesktopServices, QFontMetrics
from PyQt6.QtCore import QUrl


class RetryWorker(QObject):
    finished = pyqtSignal(bool, int)

    def __init__(self, idp, parent_n, link_obj, row_index):
        super().__init__()
        self.idp = idp
        self.parent_n = parent_n
        self.link_obj = link_obj
        self.row_index = row_index

    def run(self):
        try:
            from pathlib import Path
            import sys
            project_root = Path(__file__).resolve().parents[2]
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from src.controllers.down_anexos import download_single_attachment

            ok = download_single_attachment(self.idp, self.parent_n, self.link_obj)
            self.finished.emit(ok, self.row_index)
        except Exception:
            self.finished.emit(False, self.row_index)


class LinksReviewDialog(QDialog):
    def __init__(self, title: str, links: list, idp: str, parent_n: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Revisión de vínculos: {title}")
        self.resize(1200, 600)

        self.links = list(links)
        self.idp = idp
        self.parent_n = parent_n
        self.modified = False

        layout = QVBoxLayout(self)

        lbl_info = QLabel("Revise los enlaces detectados. Si hubo errores de descarga, use 'Reintentar'.")
        lbl_info.setStyleSheet("color: #555; margin-bottom: 5px;")
        layout.addWidget(lbl_info)

        # --- TABLA ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Título / Info", "URL", "Origen", "Estado", "Ver archivo", "Eliminar", "Excluir por siempre"
        ])

        # 1. NO WordWrap para evitar filas gigantes
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # 2. FIJAR ALTURA MÍNIMA DE FILA (Soluciona que los botones se vean cortados)
        self.table.verticalHeader().setDefaultSectionSize(48)

        self.table.setStyleSheet(
            "QTableWidget { background-color: #fff; border: 1px solid #ddd; }"
            "QTableWidget::item { border-bottom: 1px solid #f0f0f0; padding-left: 5px; }"
            "QHeaderView::section { background-color: #f8f9fa; padding: 4px; border: none; font-weight: bold; color: #555; }"
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # Anchos fijos ajustados
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 70)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 110)  # Un poco más ancho para el estado
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 80)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 130)

        layout.addWidget(self.table)

        # Botones inferiores
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar y Cerrar")
        btn_save.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 6px 12px;")
        btn_save.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

        self._populate_table()

    def _smart_truncate(self, text, max_chars=50):
        """Corta el texto en el medio: 'https://inicio...final.pdf'"""
        if len(text) <= max_chars:
            return text
        # Guardar un poco del principio y un poco del final (donde suele estar la extensión)
        keep_start = 25
        keep_end = 25
        return f"{text[:keep_start]}...{text[-keep_end:]}"

    def _populate_table(self):
        self.table.setRowCount(0)

        for i, link in enumerate(self.links):
            self.table.insertRow(i)

            # --- 0. Título ---
            titulo = link.get("titulo", "Sin título")
            extra = link.get("info_extra", "")
            full_title = f"{titulo} ({extra})" if extra else titulo

            # Usamos un QLabel dentro si queremos control total, pero QTableWidgetItem está bien
            # Truco: Tooltip tiene todo el texto, display tiene versión acortada si es muy larga
            item_tit = QTableWidgetItem(full_title)
            item_tit.setToolTip(full_title)
            item_tit.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(i, 0, item_tit)

            # --- 1. URL (MEJORADO) ---
            url_full = link.get("url", "")
            # Cortamos visualmente el medio para que se vea el nombre del archivo
            url_display = self._smart_truncate(url_full, max_chars=60)

            item_url = QTableWidgetItem(url_display)
            item_url.setForeground(QColor("#2563eb"))
            item_url.setToolTip(url_full)  # Tooltip muestra la URL real completa al pasar el mouse
            item_url.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(i, 1, item_url)

            # --- 2. Origen ---
            origen = link.get("origen", "desc")
            item_org = QTableWidgetItem(origen)
            item_org.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, item_org)

            # --- 3. Estado (Layout Vertical) ---
            self._set_status_cell(i, link)

            # --- 4, 5, 6. Botones ---
            self._add_action_btn(i, 4, "Ver", "#dbeafe", "#1d4ed8", "#93c5fd",
                                 self._open_link_file, enabled=bool(link.get("ruta")))

            self._add_action_btn(i, 5, "Borrar", "#f8f9fa", "#333", "#ccc",
                                 self._delete_link)

            self._add_action_btn(i, 6, "Excluir", "#fee2e2", "#7f1d1d", "#fca5a5",
                                 self._exclude_forever, tooltip="Excluir URL permanentemente")

    def _add_action_btn(self, row, col, text, bg, color, border, callback, enabled=True, tooltip=""):
        btn = QPushButton(text)
        btn.setEnabled(enabled)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip: btn.setToolTip(tooltip)
        # Altura fija pequeña para que el botón se vea centrado y prolijo
        btn.setFixedSize(65, 26)
        btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {border}; 
                border-radius: 4px; 
                background: {bg}; 
                color: {color};
            }}
            QPushButton:hover {{
                background-color: {border}; 
                color: #000;
            }}
            QPushButton:disabled {{
                background-color: #f0f0f0; color: #aaa; border-color: #eee;
            }}
        """)
        btn.clicked.connect(lambda _, r=row: callback(r))

        # Layout contenedor centrado
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(btn)
        self.table.setCellWidget(row, col, w)

    def _set_status_cell(self, row, link):
        has_error = link.get("error")
        has_ruta = link.get("ruta")

        w_status = QWidget()
        l_status = QVBoxLayout(w_status)
        # Márgenes pequeños arriba/abajo para que respire dentro de la fila de 48px
        l_status.setContentsMargins(0, 4, 0, 4)
        l_status.setSpacing(1)
        l_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_text = "Por Descargar"
        status_color = "#6b7280"  # Gris
        status_bg = "transparent"

        if has_error:
            status_text = "Error"
            status_color = "#dc2626"  # Rojo
            status_bg = "#ffebee"
        elif has_ruta:
            status_text = "Descargado"
            status_color = "#16a34a"  # Verde

        # Etiqueta de estado
        lbl = QLabel(status_text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_style = f"color: {status_color}; background-color: {status_bg}; border-radius: 3px; font-size: 11px; padding: 2px;"
        lbl.setStyleSheet(lbl_style)
        # Altura fija pequeña para la etiqueta
        lbl.setFixedHeight(18)
        l_status.addWidget(lbl)

        # Botón reintentar (solo si aplica)
        if has_ruta or has_error:
            btn_retry = QPushButton("Reintentar")
            btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_retry.setFixedSize(65, 20)
            btn_retry.setStyleSheet("""
                QPushButton {
                    border: 1px solid #f59e0b; border-radius: 3px; 
                    background: #fef3c7; color: #b45309; font-size: 10px;
                }
                QPushButton:hover { background: #fcd34d; }
            """)
            btn_retry.clicked.connect(lambda _, idx=row: self._retry_link(idx))
            l_status.addWidget(btn_retry)

        self.table.setCellWidget(row, 3, w_status)

    # --- Resto de métodos lógicos (sin cambios visuales)   ---
    def _delete_link(self, index):
        del self.links[index]
        self.modified = True
        self._populate_table()

    def _exclude_forever(self, index):
        link = self.links[index]
        url = link.get("url", "")
        if not url: return
        confirm = QMessageBox.question(self, "Confirmar", f"¿Excluir URL para siempre?\n{url}",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                import sys
                from pathlib import Path
                project_root = Path(__file__).resolve().parents[2]
                if str(project_root) not in sys.path: sys.path.insert(0, str(project_root))
                from src.controllers.fetch_anexos import add_global_exclusion
                add_global_exclusion(url)
                self._delete_link(index)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _retry_link(self, index):
        w = self.table.cellWidget(index, 3)
        if w:
            for child in w.findChildren(QLabel): child.setText("...")
            for child in w.findChildren(QPushButton): child.setEnabled(False)

        self.worker = RetryWorker(self.idp, self.parent_n, self.links[index], index)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self._on_retry_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def _on_retry_finished(self, success, index):
        if success:
            self.modified = True
        else:
            QMessageBox.warning(self, "Error", "La descarga falló nuevamente.")
        self._populate_table()

    def _resolve_link_path(self, ruta: str) -> str:
        ruta_text = str(ruta).replace("/", os.sep).replace("\\", os.sep)
        if os.path.isabs(ruta_text): return str(Path(ruta_text).resolve())
        base = Path(os.getcwd()) / "Ebook" / str(self.idp) / "EXEVA"
        return str((base / ruta_text).resolve())

    def _open_link_file(self, index):
        link = self.links[index]
        ruta = link.get("ruta")
        if not ruta: return
        file_path = Path(self._resolve_link_path(ruta))
        if not file_path.exists():
            QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró:\n{file_path}")
            return
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            try:
                from src.views.components.pdf_viewer import PdfViewer
                viewer = PdfViewer({"ruta": str(file_path), "titulo": link.get("titulo")}, self, self.idp)
                viewer.exec()
            except:
                QMessageBox.warning(self, "Error", "Error abriendo PDF.")
            return
        if ext in {".zip", ".rar", ".7z"}:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent)))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))

    def get_links(self):
        return self.links