from __future__ import annotations

from pathlib import Path
import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QMessageBox, QLabel, QWidget
)
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtCore import QUrl


# Worker interno para el reintento sin congelar la UI
class RetryWorker(QObject):
    finished = pyqtSignal(bool, int)  # success, row_index

    def __init__(self, idp, parent_n, link_obj, row_index):
        super().__init__()
        self.idp = idp
        self.parent_n = parent_n
        self.link_obj = link_obj
        self.row_index = row_index

    def run(self):
        try:
            # Importación lazy
            from pathlib import Path
            import sys
            project_root = Path(__file__).resolve().parents[2]
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            from src.controllers.down_anexos import download_single_attachment

            # Ejecutar descarga
            ok = download_single_attachment(self.idp, self.parent_n, self.link_obj)
            self.finished.emit(ok, self.row_index)
        except Exception:
            self.finished.emit(False, self.row_index)


class LinksReviewDialog(QDialog):
    """Ventana para revisar enlaces. Incluye Reintentar descargas fallidas."""

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
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #555; margin-bottom: 5px;")
        layout.addWidget(lbl_info)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Título / Info",
            "URL",
            "Origen",
            "Estado",
            "Ver archivo",
            "Eliminar",
            "Excluir por siempre",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget { background-color: #fff; }")

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed);
        self.table.setColumnWidth(2, 90)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed);
        self.table.setColumnWidth(3, 90)  # Estado
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed);
        self.table.setColumnWidth(4, 110)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed);
        self.table.setColumnWidth(5, 110)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed);
        self.table.setColumnWidth(6, 140)

        layout.addWidget(self.table)

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

    def _populate_table(self):
        self.table.setRowCount(0)
        for i, link in enumerate(self.links):
            self.table.insertRow(i)

            # 0. Título
            titulo = link.get("titulo", "Sin título")
            extra = link.get("info_extra", "")
            display_text = f"{titulo}\n({extra})" if extra else titulo
            item_tit = QTableWidgetItem(display_text)
            self.table.setItem(i, 0, item_tit)

            # 1. URL
            url = link.get("url", "")
            item_url = QTableWidgetItem(url)
            item_url.setForeground(QColor("#2563eb"))
            self.table.setItem(i, 1, item_url)

            # 2. Origen
            origen = link.get("origen", "desc")
            self.table.setItem(i, 2, QTableWidgetItem(origen))

            # 3. Estado + Reintentar (según corresponda)
            has_error = link.get("error")
            has_ruta = link.get("ruta")

            w_status = QWidget()
            l_status = QVBoxLayout(w_status)
            l_status.setContentsMargins(4, 2, 4, 2)
            l_status.setSpacing(2)

            status_text = "Por Descargar"
            status_color = QColor("gray")
            status_bg = None
            if has_error:
                status_text = "Error"
                status_color = QColor("red")
                status_bg = QColor("#ffebee")
            elif has_ruta:
                status_text = "Descargado"
                status_color = QColor("green")

            status_label = QLabel(status_text)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setStyleSheet(f"color: {status_color.name()};")
            if status_bg:
                status_label.setStyleSheet(
                    f"color: {status_color.name()}; background-color: {status_bg.name()};"
                )
            status_label.setFixedHeight(16)
            l_status.addWidget(status_label)

            if has_ruta or has_error:
                btn_retry = QPushButton("Reintentar")
                btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_retry.setStyleSheet(
                    "border: 1px solid #f59e0b; border-radius: 4px; background: #fef3c7; color: #b45309;")
                btn_retry.setFixedHeight(20)
                btn_retry.clicked.connect(lambda _, idx=i: self._retry_link(idx))
                l_status.addWidget(btn_retry, alignment=Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 3, w_status)

            # 4. Acción 1 (Ver archivo)
            w_view = QWidget()
            l_view = QHBoxLayout(w_view)
            l_view.setContentsMargins(4, 2, 4, 2)

            btn_view = QPushButton("Ver")
            btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_view.setStyleSheet("border: 1px solid #93c5fd; border-radius: 4px; background: #dbeafe; color: #1d4ed8;")
            btn_view.clicked.connect(lambda _, idx=i: self._open_link_file(idx))
            btn_view.setEnabled(bool(link.get("ruta")))
            l_view.addWidget(btn_view)
            self.table.setCellWidget(i, 4, w_view)

            # 5. Acción 2 (Borrar)
            w_acc1 = QWidget()
            l_acc1 = QHBoxLayout(w_acc1)
            l_acc1.setContentsMargins(4, 2, 4, 2)

            btn_del = QPushButton("Borrar")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; background: #f8f9fa; color: #333;")
            btn_del.clicked.connect(lambda _, idx=i: self._delete_link(idx))
            l_acc1.addWidget(btn_del)

            self.table.setCellWidget(i, 5, w_acc1)

            # 6. Acción 3 (Excluir)
            btn_ban = QPushButton("Excluir")
            btn_ban.setToolTip("Excluir URL permanentemente")
            btn_ban.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_ban.setStyleSheet("border: 1px solid #fca5a5; border-radius: 4px; background: #fee2e2; color: #7f1d1d;")
            btn_ban.clicked.connect(lambda _, idx=i: self._exclude_forever(idx))

            w_ban = QWidget()
            l_ban = QHBoxLayout(w_ban);
            l_ban.setContentsMargins(4, 2, 4, 2)
            l_ban.addWidget(btn_ban)
            self.table.setCellWidget(i, 6, w_ban)

        self.table.resizeRowsToContents()

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
                import sys;
                from pathlib import Path
                project_root = Path(__file__).resolve().parents[2]
                if str(project_root) not in sys.path: sys.path.insert(0, str(project_root))
                from src.controllers.fetch_anexos import add_global_exclusion
                add_global_exclusion(url)
                self._delete_link(index)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _retry_link(self, index):
        """Inicia el reintento de descarga."""
        link = self.links[index]

        # Deshabilitar botón visualmente (poniendo texto cargando en tabla)
        self.table.item(index, 3).setText("...")

        # Crear worker
        self.worker = RetryWorker(self.idp, self.parent_n, link, index)
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
            # El objeto self.links[index] ya fue modificado por el worker (es referencia)
            self.modified = True  # Para que al cerrar se guarde en JSON
            QMessageBox.information(self, "Éxito", "Descarga completada.")
        else:
            QMessageBox.warning(self, "Error", "La descarga falló nuevamente.")

        self._populate_table()  # Refrescar estado

    def _resolve_link_path(self, ruta: str) -> str:
        ruta_text = str(ruta).replace("/", os.sep).replace("\\", os.sep)
        if os.path.isabs(ruta_text):
            return str(Path(ruta_text).resolve())
        base = Path(os.getcwd()) / "Ebook" / str(self.idp) / "EXEVA"
        return str((base / ruta_text).resolve())

    def _open_link_file(self, index):
        link = self.links[index]
        ruta = link.get("ruta")
        if not ruta:
            QMessageBox.information(self, "Sin archivo", "Este enlace no tiene un archivo descargado.")
            return

        file_path = Path(self._resolve_link_path(ruta))
        if not file_path.exists():
            QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró el archivo:\n{file_path}")
            return

        ext = file_path.suffix.lower()
        compressed_exts = {".zip", ".rar", ".7z"}
        if ext == ".pdf":
            try:
                from src.views.components.pdf_viewer import PdfViewer
                viewer = PdfViewer(
                    {"ruta": str(file_path), "titulo": link.get("titulo") or file_path.name},
                    self,
                    self.idp,
                )
                viewer.exec()
            except Exception as exc:
                QMessageBox.warning(self, "Error", f"No se pudo abrir el PDF:\n{exc}")
            return

        if ext in compressed_exts:
            folder = file_path.parent
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))

    def get_links(self):
        return self.links
