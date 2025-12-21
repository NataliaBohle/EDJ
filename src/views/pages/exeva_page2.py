from PyQt6.QtCore import Qt, pyqtSignal
from urllib.parse import urlparse

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QAbstractItemView,
    QHeaderView,
)

from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.views.components.timeline import Timeline
from src.views.components.results_table import EditableTableCard
from src.views.components.mini_status import MiniStatusBar
from src.views.components.directorio import DirectorioDialog
from src.models.project_data_manager import ProjectDataManager
from src.controllers.unpack import UnpackController


class Exeva2Page(QWidget):
    log_requested = pyqtSignal(str)
    back_requested = pyqtSignal(str)
    continue_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Exeva2Page")
        self.current_project_id = None
        self.is_loading = False
        self.result_cards = []
        self.exeva_payload = {}

        self._init_controllers()
        self._setup_ui()

    def _init_controllers(self):
        self.data_manager = ProjectDataManager(self)
        self.data_manager.log_requested.connect(self.log_requested.emit)
        self.unpack_controller = UnpackController(self)
        self.unpack_controller.log_requested.connect(self.log_requested.emit)
        self.unpack_controller.unpack_started.connect(self._on_unpack_started)
        self.unpack_controller.unpack_finished.connect(self._on_unpack_finished)

    def _setup_ui(self):
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

        self.btn_back_step1 = self.command_bar.add_left_button(
            "Volver a Paso 1", object_name="BtnActionFolder"
        )
        self.btn_unzip_index = self.command_bar.add_button(
            "Descomprimir e indexar", object_name="BtnActionPrimary"
        )
        self.btn_continue_step3 = self.command_bar.add_right_button(
            "Continuar a paso 3", object_name="BtnActionPrimary"
        )

        self.btn_back_step1.clicked.connect(self._on_back_clicked)
        self.btn_unzip_index.clicked.connect(self._on_unzip_index_clicked)
        self.btn_continue_step3.clicked.connect(self._on_continue_clicked)

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
            "La tabla de resultados de EXEVA Paso 2 se configurará en la siguiente etapa."
        )
        self.lbl_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.lbl_placeholder)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def load_project(self, pid: str):
        self.current_project_id = pid
        self.is_loading = True
        self.header.title_label.setText(f"Expediente EXEVA - Paso 2 - ID {pid}")
        step_idx = 2
        step_status = "detectado"
        global_status = "detectado"

        self.timeline.set_current_step(step_idx, step_status)
        self.status_bar.set_status(global_status)
        self.data_manager.update_step_status(
            self.current_project_id,
            "EXEVA",
            step_index=step_idx,
            step_status=step_status,
            global_status=global_status,
        )
        self._load_results_tables()
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

    def _on_back_clicked(self):
        if not self.current_project_id:
            return
        self.back_requested.emit(self.current_project_id)

    def _on_continue_clicked(self):
        if not self.current_project_id:
            return
        self.continue_requested.emit(self.current_project_id)

    def _on_unzip_index_clicked(self):
        if not self.current_project_id:
            return
        self.unpack_controller.start_unpack(self.current_project_id)

    def _on_unpack_started(self) -> None:
        self.btn_unzip_index.setEnabled(False)
        self.log_requested.emit("⏳ Descomprimiendo archivos comprimidos...")

    def _on_unpack_finished(self, success: bool, _data: dict) -> None:
        self.btn_unzip_index.setEnabled(True)
        if success:
            self._load_results_tables()
            self.log_requested.emit("✅ Descompresión e indexación finalizadas.")
        else:
            self.log_requested.emit("⚠️ No se pudieron descomprimir archivos.")

    def _load_results_tables(self) -> None:
        exeva_payload = self.data_manager.load_exeva_data(self.current_project_id)
        self.exeva_payload = exeva_payload or {}
        documentos = exeva_payload.get("EXEVA", {}).get("documentos", [])
        self._render_compressed_tables(documentos)

    def _render_compressed_tables(self, documentos: list[dict]) -> None:
        self._clear_result_cards()

        cards_created = 0
        for doc in documentos:
            anexos = doc.get("anexos_detectados") or []
            vinculados = doc.get("vinculados_detectados") or []
            if not (anexos or vinculados):
                continue

            compressed_rows = self._build_compressed_rows(anexos + vinculados)
            if not compressed_rows:
                continue

            title = self._format_doc_title(doc)
            card = EditableTableCard(
                title,
                columns=[
                    ("tipo", "Tipo"),
                    ("archivo", "Archivo"),
                    ("ruta", "URL / Ruta"),
                    ("formato", "Formato comprimido"),
                    ("estado", "Estado"),
                ],
                parent=self.content_widget,
            )
            card.status_bar.setVisible(False)
            card.btn_add_row.setVisible(False)
            card.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            header = card.table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            card.set_data(compressed_rows)
            self._attach_row_status_bars(card, compressed_rows)
            card.table.resizeColumnsToContents()

            self.content_layout.addWidget(card)
            self.result_cards.append(card)
            cards_created += 1

        if cards_created == 0:
            self.lbl_placeholder.setText(
                "No se encontraron anexos o vínculos comprimidos para este expediente."
            )
            self.lbl_placeholder.setVisible(True)
        else:
            self.lbl_placeholder.setVisible(False)

    def _clear_result_cards(self) -> None:
        for card in self.result_cards:
            self.content_layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self.result_cards = []

    def _format_doc_title(self, doc: dict) -> str:
        n_doc = doc.get("n") or doc.get("num_doc") or "0"
        titulo = doc.get("titulo") or "Documento"
        return f"Documento principal {n_doc}: {titulo}"

    def _build_compressed_rows(self, links: list[dict]) -> list[dict]:
        rows = []
        for link in links:
            formato = self._detect_compressed_format(link)
            if not formato:
                continue
            rows.append({
                "tipo": self._format_link_type(link),
                "archivo": self._format_link_name(link),
                "ruta": self._format_link_source(link),
                "formato": formato,
                "estado": self._derive_link_status(link),
                "_link": link,
            })
        return rows

    def _format_link_type(self, link: dict) -> str:
        tipo = (link.get("tipo") or "").lower()
        if "vinculado" in tipo:
            return "Vinculado"
        return "Anexo"

    def _format_link_name(self, link: dict) -> str:
        titulo = (link.get("titulo") or "").strip()
        if titulo:
            return titulo
        ruta = link.get("ruta") or link.get("url") or ""
        return ruta.split("/")[-1] if ruta else "Archivo comprimido"

    def _format_link_source(self, link: dict) -> str:
        return link.get("ruta") or link.get("url") or ""

    def _detect_compressed_format(self, link: dict) -> str | None:
        candidates = [
            link.get("ruta"),
            link.get("url"),
            link.get("titulo"),
            link.get("info_extra"),
        ]
        for value in candidates:
            format_label = self._format_from_value(value)
            if format_label:
                return format_label
        return None

    def _derive_link_status(self, link: dict) -> str:
        manual_status = (link.get("estado_descompresion") or "").strip().lower()
        if manual_status:
            return manual_status
        if link.get("error_descompresion") or link.get("error"):
            return "error"
        if link.get("descomprimidos"):
            return "verificado"
        return "detectado"

    def _attach_row_status_bars(self, card: EditableTableCard, rows: list[dict]) -> None:
        status_column = None
        for idx, (key, _label) in enumerate(card.columns):
            if key == "estado":
                status_column = idx
                break
        if status_column is None:
            return

        for row_idx, row_data in enumerate(rows):
            widget = QWidget(card.table)
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            status = MiniStatusBar(widget)
            status.set_status(row_data.get("estado"))
            link_ref = row_data.get("_link")
            if link_ref is not None:
                status.status_changed.connect(
                    lambda value, link=link_ref: self._on_row_status_changed(link, value)
                )

            btn_view = QPushButton("Ver directorio", widget)
            btn_view.setObjectName("BtnActionSecondary")
            btn_view.setEnabled(bool(row_data.get("_link")))
            btn_view.clicked.connect(lambda _checked=False, link=row_data.get("_link"): self._show_directorio(link))

            layout.addWidget(status)
            layout.addWidget(btn_view)
            layout.addStretch()
            card.table.setCellWidget(row_idx, status_column, widget)

    def _show_directorio(self, link: dict | None) -> None:
        if not link:
            return
        dialog = DirectorioDialog(self)
        estructura = link.get("descomprimidos")
        errores = link.get("errores_descompresion") or []

        def _retry() -> None:
            ruta = link.get("ruta")
            if not ruta or not self.current_project_id:
                return
            dialog.close()
            self.unpack_controller.start_unpack_item(self.current_project_id, ruta)

        dialog.set_data(estructura, errores, on_retry=_retry if errores else None)
        dialog.exec()

    def _on_row_status_changed(self, link: dict, status: str) -> None:
        link["estado_descompresion"] = status
        if self.current_project_id and self.exeva_payload:
            self.data_manager.save_exeva_data(self.current_project_id, self.exeva_payload)

    def _format_from_value(self, value: str | None) -> str | None:
        if not value:
            return None
        value_lower = value.lower().strip()
        if value_lower.startswith("http"):
            value_lower = urlparse(value_lower).path

        multi_map = {
            ".tar.gz": "TAR.GZ",
            ".tar.bz2": "TAR.BZ2",
            ".tar.xz": "TAR.XZ",
        }
        for ext, label in multi_map.items():
            if value_lower.endswith(ext):
                return label

        ext = value_lower.rsplit(".", 1)[-1] if "." in value_lower else ""
        ext = f".{ext}" if ext else ""

        simple_map = {
            ".zip": "ZIP",
            ".rar": "RAR",
            ".7z": "7ZIP",
            ".tar": "TAR",
            ".gz": "GZ",
            ".bz2": "BZ2",
            ".xz": "XZ",
            ".tgz": "TAR.GZ",
        }
        if ext in simple_map:
            return simple_map[ext]

        for ext_key, label in simple_map.items():
            if ext_key in value_lower:
                return label

        return None
