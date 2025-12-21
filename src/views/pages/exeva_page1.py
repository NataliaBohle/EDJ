from PyQt6.QtCore import Qt, pyqtSignal
from functools import partial

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout,
    QProgressBar, QFrame, QMessageBox, QAbstractItemView, QHeaderView, QPushButton
)

# Componentes
from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.views.components.timeline import Timeline
from src.views.components.results_table import EditableTableCard
from src.views.components.pdf_viewer import PdfViewer
from src.views.components.links_review import LinksReviewDialog

# Controladores y Modelos de antgen
from src.controllers.fetch_exeva import FetchExevaController
from src.controllers.fetch_anexos import FetchAnexosController
from src.controllers.down_anexos import DownAnexosController
from src.models.project_data_manager import ProjectDataManager


class Exeva1Page(QWidget):
    log_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Exeva1Page")
        self.current_project_id = None
        self.is_loading = False

        # 1. Inicializar Lógica de Negocio (Controladores y Modelos)
        self._init_controllers()

        # 2. Construir Interfaz Gráfica (Layouts y Widgets)
        self._setup_ui()

    def _init_controllers(self):
        """Inicializa gestores y futuros controladores."""
        self.data_manager = ProjectDataManager(self)
        self.data_manager.log_requested.connect(self.log_requested.emit)

        # Controladores a implementar en siguientes iteraciones
        self.fetch_controller = FetchExevaController(self)
        self.fetch_controller.log_requested.connect(self.log_requested.emit)
        self.fetch_controller.extraction_started.connect(self._on_extraction_started)
        self.fetch_controller.extraction_finished.connect(self._on_extraction_finished)
        self.fetch_anexos_controller = FetchAnexosController(self)
        self.fetch_anexos_controller.log_requested.connect(self.log_requested.emit)
        self.fetch_anexos_controller.detection_started.connect(self._on_anexos_detection_started)
        self.fetch_anexos_controller.detection_finished.connect(self._on_anexos_detection_finished)
        self.down_anexos_controller = DownAnexosController(self)
        self.down_anexos_controller.log_requested.connect(self.log_requested.emit)
        self.down_anexos_controller.download_started.connect(self._on_anexos_download_started)
        self.down_anexos_controller.download_finished.connect(self._on_anexos_download_finished)

    def _setup_ui(self):
        """Construye la interfaz gráfica siguiendo el patrón de AntGen."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- A. HEADER Y STATUS ---
        header_widget = QWidget()
        header_lay = QVBoxLayout(header_widget)
        header_lay.setContentsMargins(40, 30, 40, 10)

        self.header = Chapter("Evaluación Ambiental")

        status_box = QWidget()
        sb_lay = QHBoxLayout(status_box)
        sb_lay.setContentsMargins(0, 5, 0, 0)
        sb_lay.setSpacing(15)
        sb_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

        lbl_estado = QLabel("Estado:")
        lbl_estado.setStyleSheet("color:#555; font-weight:bold; font-size:13px;")
        sb_lay.addWidget(lbl_estado)

        self.status_bar = StatusBar()
        self.status_bar.status_changed.connect(self.save_status_change)
        sb_lay.addWidget(self.status_bar)

        self.header.layout().addWidget(status_box)
        header_lay.addWidget(self.header)
        layout.addWidget(header_widget)

        # --- B. TIMELINE ---
        timeline_widget = QWidget()
        tl_lay = QVBoxLayout(timeline_widget)
        tl_lay.setContentsMargins(40, 0, 40, 10)

        self.timeline = Timeline(steps=[
            "Detectado", "Descargar", "Convertir",
            "Formatear", "Índice", "Compilar"
        ])
        tl_lay.addWidget(self.timeline)
        layout.addWidget(timeline_widget)

        # --- C. COMMAND BAR ---
        self.command_bar = CommandBar()
        self.command_bar.layout().setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_fetchexeva = self.command_bar.add_button(
            "1. Descargar Expediente", object_name="BtnActionPrimary"
        )
        self.btn_fetchanexos = self.command_bar.add_button(
            "2. Detectar Anexos", object_name="BtnActionPrimary"
        )
        self.btn_downanexos = self.command_bar.add_button(
            "3. Descargar Anexos", object_name="BtnActionPrimary"
        )

        self.btn_fetchexeva.clicked.connect(self._on_fetchexeva_clicked)
        self.btn_fetchanexos.clicked.connect(self._on_fetchanexos_clicked)
        self.btn_downanexos.clicked.connect(self._on_downanexos_clicked)

        self.pbar = QProgressBar(self.command_bar)
        self.pbar.setVisible(False)
        self.pbar.setFixedWidth(200)
        self.command_bar.button_layout.addWidget(self.pbar)

        layout.addWidget(self.command_bar)

        # --- D. ÁREA DE CONTENIDO (SCROLL) ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 30, 40, 30)
        self.content_layout.setSpacing(15)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_placeholder = QLabel(
            "Los resultados del expediente EXEVA aparecerán aquí una vez implementada la extracción."
        )
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.lbl_placeholder)

        self.results_table = EditableTableCard(
            "Resultados EXEVA",
            columns=[
                ("n", "N° Documento"),
                ("folio", "Folio"),
                ("titulo", "Nombre"),
                ("remitido_por", "Remitido por"),
                ("fecha", "Fecha"),
                ("anexos_detectados", "Anexos"),
                ("vinculados_detectados", "Vinculados"),
                ("ver_anexos", "Ver anexos"),
                ("ver_doc", "Ver doc"),
            ],
            parent=self.content_widget,
        )
        self.results_table.btn_add_row.setVisible(False)
        self.results_table.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.results_table.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        self.results_table.setVisible(False)
        self.content_layout.addWidget(self.results_table)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def load_project(self, pid: str):
        """Carga el estado del proyecto desde disco y ajusta la UI."""
        self.current_project_id = pid
        self.is_loading = True
        self.header.title_label.setText(f"Expediente EXEVA - ID {pid}")

        data = self.data_manager.load_data(pid)
        exeva_section = data.get("expedientes", {}).get("EXEVA", {})
        exeva_payload = self.data_manager.load_exeva_data(pid)

        step_idx = exeva_section.get("step_index", 0)
        step_status = exeva_section.get("step_status", "detectado")
        global_status = exeva_section.get("status", "detectado")

        self.timeline.set_current_step(step_idx, step_status)
        self.status_bar.set_status(global_status)

        documentos = exeva_payload.get("EXEVA", {}).get("documentos", [])
        has_docs = bool(documentos)

        if has_docs:
            total = len(documentos)
            self.lbl_placeholder.setText(f"Expediente descargado: {total} documentos detectados.")
            self.btn_fetchexeva.setText("Volver a Descargar")
        else:
            self.lbl_placeholder.setText(
                "Los resultados del expediente EXEVA aparecerán aquí una vez implementada la extracción."
            )
            self.btn_fetchexeva.setText("1. Descargar Expediente")
        self.lbl_placeholder.setVisible(True)
        self._set_results_table(documentos)
        self.is_loading = False

    def save_status_change(self, new_status: str):
        if self.is_loading or not self.current_project_id:
            return

        idx = self.timeline.current_step
        self.timeline.set_current_step(idx, new_status)
        self.data_manager.update_step_status(
            self.current_project_id,
            "EXEVA",
            step_index=idx,
            step_status=new_status,
            global_status=new_status,
        )

    # --- ACCIONES (PLACEHOLDERS) ---

    def _on_fetchexeva_clicked(self):
        if not self.current_project_id:
            return
        self.status_bar.set_status("edicion")
        self.fetch_controller.start_extraction(self.current_project_id)

    def _on_fetchanexos_clicked(self):
        if not self.current_project_id:
            return
        self.fetch_anexos_controller.start_detection(self.current_project_id)

    def _on_downanexos_clicked(self):
        if not self.current_project_id:
            return
        self.down_anexos_controller.start_download(self.current_project_id)

    # --- SLOTS ASYNC ---

    def _on_extraction_started(self):
        self.btn_fetchexeva.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)
        self.lbl_placeholder.setVisible(False)

    def _on_extraction_finished(self, success: bool, data: dict):
        self.pbar.setVisible(False)
        self.btn_fetchexeva.setEnabled(True)
        self.pbar.setRange(0, 100)

        if success:
            documentos = data.get("EXEVA", {}).get("documentos", [])
            total = len(documentos)
            self.lbl_placeholder.setText(f"Expediente descargado: {total} documentos detectados.")
            self.lbl_placeholder.setVisible(True)
            self._set_results_table(documentos)
            self.status_bar.set_status("edicion")
            self.timeline.set_current_step(1, "edicion")
            self.data_manager.update_step_status(
                self.current_project_id, "EXEVA", step_index=1, step_status="edicion", global_status="edicion"
            )
            self.btn_fetchexeva.setText("Volver a Descargar")
        else:
            self.status_bar.set_status("error")
            self.timeline.set_current_step(self.timeline.current_step, "error")
            self.lbl_placeholder.setText("No se pudo descargar el expediente. Intente nuevamente.")
            self.lbl_placeholder.setVisible(True)
            self._set_results_table([])
            QMessageBox.critical(self, "Error", "Fallo en la extracción de EXEVA.")

    def _on_anexos_detection_started(self):
        self.btn_fetchanexos.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)

    def _on_anexos_detection_finished(self, success: bool, _data: dict):
        self.pbar.setVisible(False)
        self.btn_fetchanexos.setEnabled(True)
        self.pbar.setRange(0, 100)

        if success:
            exeva_payload = self.data_manager.load_exeva_data(self.current_project_id)
            documentos = exeva_payload.get("EXEVA", {}).get("documentos", [])
            self._set_results_table(documentos)
            self.log_requested.emit("✅ Anexos detectados y tabla actualizada.")
        else:
            self.log_requested.emit("⚠️ No se pudieron detectar anexos.")

    def _on_anexos_download_started(self):
        self.btn_downanexos.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setRange(0, 0)

    def _on_anexos_download_finished(self, success: bool, _data: dict):
        self.pbar.setVisible(False)
        self.btn_downanexos.setEnabled(True)
        self.pbar.setRange(0, 100)

        if success:
            exeva_payload = self.data_manager.load_exeva_data(self.current_project_id)
            documentos = exeva_payload.get("EXEVA", {}).get("documentos", [])
            self._set_results_table(documentos)
            self.log_requested.emit("✅ Descarga de anexos finalizada y tabla actualizada.")
        else:
            self.log_requested.emit("⚠️ No se pudieron descargar anexos.")

    def _set_results_table(self, documentos: list[dict]) -> None:
        rows = [
            {
                "n": doc.get("n", ""),
                "folio": doc.get("folio", ""),
                "titulo": doc.get("titulo", ""),
                "remitido_por": doc.get("remitido_por", ""),
                "fecha": doc.get("fecha", ""),
                "anexos_detectados": str(len(doc.get("anexos_detectados") or [])),
                "vinculados_detectados": str(len(doc.get("vinculados_detectados") or [])),
                "ver_anexos": "",
                "ver_doc": "",
            }
            for doc in documentos
        ]
        self.results_table.set_data(rows)
        has_rows = bool(rows)
        self.results_table.setVisible(has_rows)
        if has_rows:
            ver_col = next(
                (idx for idx, (key, _label) in enumerate(self.results_table.columns) if key == "ver_doc"),
                None,
            )
            if ver_col is not None:
                for row_idx, doc in enumerate(documentos):
                    button = QPushButton("Ver doc", self.results_table.table)
                    button.setObjectName("BtnActionSecondary")
                    button.clicked.connect(partial(self._open_pdf_viewer, doc))
                    self.results_table.table.setCellWidget(row_idx, ver_col, button)
            anexos_col = next(
                (idx for idx, (key, _label) in enumerate(self.results_table.columns) if key == "ver_anexos"),
                None,
            )
            if anexos_col is not None:
                for row_idx, doc in enumerate(documentos):
                    button = QPushButton("Ver anexos", self.results_table.table)
                    button.setObjectName("BtnActionSecondary")
                    button.clicked.connect(partial(self._open_links_review, doc))
                    self.results_table.table.setCellWidget(row_idx, anexos_col, button)
            self.results_table.table.resizeColumnsToContents()

    def _open_pdf_viewer(self, doc_data: dict) -> None:
        viewer = PdfViewer(doc_data, self, self.current_project_id)
        viewer.show()

    def _open_links_review(self, doc_data: dict) -> None:
        """Abre el diálogo, y si hay cambios, actualiza SOLO la fila afectada."""
        # 1. Recuperar listas
        raw_anexos = doc_data.get("anexos_detectados") or []
        raw_vinculados = doc_data.get("vinculados_detectados") or []

        links = []
        for item in raw_anexos:
            payload = dict(item)
            payload.setdefault("tipo", "anexo")
            links.append(payload)
        for item in raw_vinculados:
            payload = dict(item)
            payload.setdefault("tipo", "vinculado")
            links.append(payload)

        if not links:
            QMessageBox.information(self, "Sin enlaces", "Este documento no tiene anexos ni vinculados.")
            return

        # 2. Configurar y abrir diálogo
        title = str(doc_data.get("titulo") or "Doc")
        parent_n = str(doc_data.get("n") or doc_data.get("num_doc") or "0")
        pid = self.current_project_id or ""

        dialog = LinksReviewDialog(title, links, pid, parent_n, self)

        # 3. Si el usuario guardó cambios
        if dialog.exec():
            if dialog.modified:
                new_links = dialog.get_links()

                # Separar y actualizar en memoria
                doc_data["anexos_detectados"] = [x for x in new_links if x.get("tipo") == "anexo"]
                doc_data["vinculados_detectados"] = [x for x in new_links if x.get("tipo") == "vinculado"]

                # ACTUALIZAR LA UI
                self._refresh_row_counts(doc_data)
                self.log_requested.emit(f"Enlaces actualizados para documento N° {parent_n}")

    def _refresh_row_counts(self, doc_data: dict):
        """Busca la fila del documento y actualiza los números de anexos/vinculados."""
        target_n = str(doc_data.get("n") or "")
        table = self.results_table.table

        # Buscar índices de columnas dinámicamente
        col_n, col_anex, col_vinc = -1, -1, -1
        for c in range(table.columnCount()):
            h = table.horizontalHeaderItem(c).text()
            if h == "N° Documento":
                col_n = c
            elif h == "Anexos":
                col_anex = c
            elif h == "Vinculados":
                col_vinc = c

        if col_n == -1: return

        # Buscar la fila y actualizar
        for r in range(table.rowCount()):
            item = table.item(r, col_n)
            if item and item.text() == target_n:
                # Encontramos la fila, actualizamos los contadores
                n_a = len(doc_data.get("anexos_detectados", []))
                n_v = len(doc_data.get("vinculados_detectados", []))

                if col_anex != -1:
                    table.item(r, col_anex).setText(str(n_a))
                if col_vinc != -1:
                    table.item(r, col_vinc).setText(str(n_v))
                return

    def _set_results_table_row_count(self, doc_data: dict):
        """Helper opcional para refrescar solo los contadores en la tabla sin recargar todo."""
        # Encuentra la fila correspondiente (esto puede requerir iterar self.results_table.data)
        # O simplemente llamamos a _set_results_table completo si no es costoso:
        # self._set_results_table( [toda la lista de docs] ) -> esto requiere tener la lista completa a mano.
        pass
