from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path
from functools import partial

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QHBoxLayout,
    QFrame,
    QAbstractItemView,
    QHeaderView,
    QPushButton,
)

from src.views.components.chapter import Chapter
from src.views.components.status_bar import StatusBar
from src.views.components.command_bar import CommandBar
from src.views.components.timeline import Timeline
from src.views.components.results_table import EditableTableCard
from src.views.components.pdf_viewer import PdfViewer
from src.views.components.mini_status import MiniStatusBar
from src.views.components.format_view import FormatViewDialog
from src.models.project_data_manager import ProjectDataManager
from src.controllers.eval_format import EvalFormatController
from src.controllers.format_legal import convert_exeva_item, CONVERTIBLE_EXTENSIONS


class Exeva3Page(QWidget):
    log_requested = pyqtSignal(str)
    back_requested = pyqtSignal(str)
    continue_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Exeva3Page")
        self.current_project_id = None
        self.is_loading = False
        self.documentos = []
        self.exeva_payload = {}

        self._init_controllers()
        self._setup_ui()

    def _init_controllers(self):
        self.data_manager = ProjectDataManager(self)
        self.data_manager.log_requested.connect(self.log_requested.emit)
        self.eval_controller = EvalFormatController(self)
        self.eval_controller.log_requested.connect(self.log_requested.emit)
        self.eval_controller.eval_started.connect(self._on_eval_started)
        self.eval_controller.eval_finished.connect(self._on_eval_finished)

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

        self.btn_back_step2 = self.command_bar.add_left_button(
            "Volver a Paso 2", object_name="BtnActionFolder"
        )
        self.btn_format_edit = self.command_bar.add_button(
            "Formatear", object_name="BtnActionPrimary"
        )
        self.btn_continue_step4 = self.command_bar.add_right_button(
            "Continuar a paso 4", object_name="BtnActionPrimary"
        )

        self.btn_back_step2.clicked.connect(self._on_back_clicked)
        self.btn_format_edit.clicked.connect(self._on_format_clicked)
        self.btn_continue_step4.clicked.connect(self._on_continue_clicked)

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
            "La tabla de resultados de EXEVA Paso 3 se configurará en la siguiente etapa."
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
                ("formato", "Formato"),
                ("archivos_totales", "Archivos totales"),
                ("archivos_pdf", "Archivos PDF"),
                ("revisar_anexos", "Revisar Formatos de anexos"),
                ("ver_doc", "Ver doc"),
                ("estado_doc", "Estado"),
            ],
            parent=self.content_widget,
        )
        self.results_table.status_bar.setVisible(False)
        self.results_table.btn_add_row.setVisible(False)
        self.results_table.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.results_table.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        fixed_cols = {
            "n",
            "folio",
            "fecha",
            "formato",
            "archivos_totales",
            "archivos_pdf",
            "revisar_anexos",
            "ver_doc",
            "estado_doc",
        }
        for idx, (key, _label) in enumerate(self.results_table.columns):
            if key in fixed_cols:
                header.setSectionResizeMode(idx, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.results_table.setVisible(False)
        self.content_layout.addWidget(self.results_table)

        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)

    def load_project(self, pid: str):
        self.current_project_id = pid
        self.is_loading = True
        self.header.title_label.setText(f"Expediente EXEVA - Paso 3 - ID {pid}")

        data = self.data_manager.load_data(pid)
        exeva_section = data.get("expedientes", {}).get("EXEVA", {})
        step_idx = max(exeva_section.get("step_index", 0), 3)
        step_status = exeva_section.get("step_status", "detectado")
        global_status = exeva_section.get("status", "detectado")

        exeva_payload = self.data_manager.load_exeva_data(pid)
        self.exeva_payload = exeva_payload or {}
        documentos = exeva_payload.get("EXEVA", {}).get("documentos", [])
        self.documentos = documentos
        self._ensure_document_counts(self.documentos)

        self.timeline.set_current_step(step_idx, step_status)
        self.status_bar.set_status(global_status)
        self.data_manager.update_step_status(
            self.current_project_id,
            "EXEVA",
            step_index=step_idx,
            step_status=step_status,
            global_status=global_status,
        )
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

    def _on_eval_clicked(self):
        if not self.current_project_id:
            return
        self.eval_controller.start_eval(self.current_project_id)

    def _on_format_clicked(self) -> None:
        if not self.current_project_id:
            return
        total = 0
        converted = 0
        errors = 0

        self.log_requested.emit("⚙️ Iniciando formateo masivo...")

        for doc in self.documentos:
            if not isinstance(doc, dict):
                continue
            has_success = False
            has_error = False

            files_to_process = self._collect_document_files(doc)

            for item in files_to_process:
                try:
                    if not self._is_item_convertible(item):
                        continue

                    total += 1
                    success, conv_path, _error = convert_exeva_item(
                        self.current_project_id,
                        item,
                        log_callback=self.log_requested.emit,
                    )

                    if success:
                        if conv_path:
                            item["conv"] = conv_path
                        item["estado_formato"] = "edicion"
                        has_success = True
                        converted += 1
                        # Opcional: Loguear éxito en la app también si quieres mucho detalle
                        # self.log_requested.emit(f"✅ Convertido: {item.get('nombre')}")
                    else:
                        # CAMBIO AQUI: print -> self.log_requested.emit
                        msg_err = f"⚠️ Error convirtiendo {item.get('nombre')}: {_error}"
                        self.log_requested.emit(msg_err)

                        item["estado_formato"] = "error"
                        has_error = True
                        errors += 1

                except Exception as e:
                    # CAMBIO AQUI: print -> self.log_requested.emit
                    msg_exc = f"❌ Excepción en archivo {item.get('nombre')}: {e}"
                    self.log_requested.emit(msg_exc)

                    item["estado_formato"] = "error"
                    has_error = True
                    errors += 1

            if has_error:
                doc["estado_formato"] = "error"
            elif has_success:
                doc["estado_formato"] = "edicion"

        if total == 0:
            self.log_requested.emit("⚠️ No hay archivos convertibles para formatear.")
            return

        self._persist_exeva_payload()
        self._set_results_table(self.documentos)
        self.log_requested.emit(
            f"✅ Conversión finalizada. Convertidos: {converted}. Errores: {errors}."
        )

    def _on_back_clicked(self):
        if not self.current_project_id:
            return
        self.back_requested.emit(self.current_project_id)

    def _on_continue_clicked(self):
        if not self.current_project_id:
            return
        self.continue_requested.emit(self.current_project_id)

    def _on_eval_started(self) -> None:
        self.btn_eval_formato.setEnabled(False)
        self.log_requested.emit("⏳ Evaluando formatos del expediente...")

    def _on_eval_finished(self, success: bool, _data: dict) -> None:
        self.btn_eval_formato.setEnabled(True)
        if success:
            self._reload_exeva_data()
            self.log_requested.emit("✅ Evaluación de formatos finalizada.")
        else:
            self.log_requested.emit("⚠️ No se pudo evaluar los formatos.")

    def _reload_exeva_data(self) -> None:
        if not self.current_project_id:
            return
        exeva_payload = self.data_manager.load_exeva_data(self.current_project_id)
        self.exeva_payload = exeva_payload or {}
        documentos = exeva_payload.get("EXEVA", {}).get("documentos", [])
        self.documentos = documentos
        self._ensure_document_counts(self.documentos)
        self._set_results_table(documentos)

    def _set_results_table(self, documentos: list[dict]) -> None:
        self.documentos = documentos
        rows = [
            {
                "n": doc.get("n", ""),
                "folio": doc.get("folio", ""),
                "titulo": doc.get("titulo", ""),
                "remitido_por": doc.get("remitido_por", ""),
                "fecha": doc.get("fecha", ""),
                "formato": doc.get("formato", ""),
                "archivos_totales": str(doc.get("archivos_totales", 0)),
                "archivos_pdf": str(doc.get("archivos_pdf", 0)),
                "revisar_anexos": "",
                "ver_doc": "",
                "estado_doc": "",
            }
            for doc in documentos
        ]
        self.results_table.set_data(rows)
        has_rows = bool(rows)
        self.results_table.setVisible(has_rows)
        self.lbl_placeholder.setVisible(not has_rows)
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
            estado_col = next(
                (idx for idx, (key, _label) in enumerate(self.results_table.columns) if key == "estado_doc"),
                None,
            )
            if estado_col is not None:
                for row_idx, doc in enumerate(documentos):
                    status_widget = MiniStatusBar(self.results_table.table)
                    status = self._derive_doc_status(doc)
                    status_widget.set_status(status)
                    status_widget.status_changed.connect(
                        partial(self._on_row_status_changed, doc, status_widget)
                    )
                    self.results_table.table.setCellWidget(row_idx, estado_col, status_widget)
            anexos_col = next(
                (idx for idx, (key, _label) in enumerate(self.results_table.columns) if key == "revisar_anexos"),
                None,
            )
            if anexos_col is not None:
                for row_idx, doc in enumerate(documentos):
                    if self._doc_has_links(doc):
                        button = QPushButton("Revisar", self.results_table.table)
                        button.setObjectName("BtnActionSecondary")
                        button.clicked.connect(partial(self._open_format_review, doc))
                        self.results_table.table.setCellWidget(row_idx, anexos_col, button)
            self.results_table.table.resizeColumnsToContents()
            self._update_global_status_from_rows()

    def _ensure_document_counts(self, documentos: list[dict]) -> None:
        for doc in documentos:
            if not isinstance(doc, dict):
                continue
            counts = self._count_doc_files(doc)
            doc["archivos_totales"] = counts["archivos_totales"]
            doc["archivos_pdf"] = counts["archivos_pdf"]

    def _count_doc_files(self, doc: dict) -> dict:
        total = {"archivos_totales": 0, "archivos_pdf": 0}
        self._record_format(doc.get("formato"), total)
        self._count_tree_formats(doc.get("descomprimidos"), total)
        for key in ("anexos_detectados", "vinculados_detectados"):
            links = doc.get(key) or []
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, dict):
                    continue
                self._record_format(self._infer_link_format(link), total)
                self._count_tree_formats(link.get("descomprimidos"), total)
        return total

    def _record_format(self, format_value: str | None, total: dict) -> None:
        label = (format_value or "sin formato").strip() or "sin formato"
        total["archivos_totales"] += 1
        if "pdf" in label.lower():
            total["archivos_pdf"] += 1

    def _count_tree_formats(self, node: dict | list | None, total: dict) -> None:
        if isinstance(node, list):
            for item in node:
                self._count_tree_formats(item, total)
            return
        if not isinstance(node, dict):
            return
        formato = node.get("formato")
        if formato and str(formato).lower() != "carpeta":
            self._record_format(str(formato), total)
        contenido = node.get("contenido")
        if isinstance(contenido, list):
            for child in contenido:
                self._count_tree_formats(child, total)

    def _infer_link_format(self, link: dict) -> str | None:
        if link.get("formato"):
            return str(link.get("formato"))
        candidates = [
            link.get("ruta"),
            link.get("url"),
            link.get("titulo"),
            link.get("info_extra"),
            link.get("archivo"),
        ]
        for value in candidates:
            fmt = self._format_from_value(str(value)) if value else None
            if fmt:
                return fmt
        return None

    def _format_from_value(self, value: str | None) -> str | None:
        if not value:
            return None
        value_lower = value.lower().strip()
        if value_lower.startswith("http"):
            value_lower = value_lower.split("?", 1)[0]
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
            ".pdf": "PDF",
            ".doc": "DOC",
            ".docx": "DOCX",
            ".xls": "XLS",
            ".xlsx": "XLSX",
            ".ppt": "PPT",
            ".pptx": "PPTX",
        }
        if ext in simple_map:
            return simple_map[ext]
        for ext_key, label in simple_map.items():
            if ext_key in value_lower:
                return label
        return None

    def _is_item_convertible(self, item: dict) -> bool:
        ruta = item.get("ruta") or ""
        if not ruta:
            return False
        fmt_value = (item.get("formato") or "").strip().lower()
        if fmt_value == "doc digital":
            return False
        if fmt_value in {"pdf", "doc", "docx", "rtf", "odt", "wpd"}:
            return True
        if fmt_value in {"ppt", "pptx", "odp", "key", "gslides", "sxi", "shw", "prz"}:
            return True
        if fmt_value in {"jpg", "jpeg", "png", "gif", "tiff", "tif", "bmp"}:
            return True
        suffix = Path(str(ruta)).suffix.lower()
        return suffix in CONVERTIBLE_EXTENSIONS

    def _open_pdf_viewer(self, doc_data: dict) -> None:
        viewer = PdfViewer(doc_data, self, self.current_project_id)
        viewer.show()

    def _open_format_review(self, doc_data: dict) -> None:
        titulo = doc_data.get("titulo") or "Documento"
        files = self._collect_document_files(doc_data)
        dialog = FormatViewDialog(
            titulo,
            files,
            self,
            self.current_project_id,
            log_callback=self.log_requested.emit,
        )
        dialog.exec()
        if dialog.modified:
            self._persist_exeva_payload()
            self._set_results_table(self.documentos)

    def _collect_document_files(self, doc_data: dict) -> list[dict]:
        files: list[dict] = []
        base_code = ""
        next_index = 1
        if isinstance(doc_data, dict):
            base_code = self._format_code_part(doc_data.get("n") or doc_data.get("num_doc"))
            doc_data["codigo"] = base_code
            files.append(doc_data)
            next_index = self._collect_tree_files(doc_data.get("descomprimidos"), files, base_code, next_index)
        for key in ("anexos_detectados", "vinculados_detectados"):
            links = doc_data.get(key) or []
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, dict):
                    continue
                code = self._compose_code(base_code, next_index)
                link["codigo"] = code
                files.append(link)
                next_index += 1
                next_index = self._collect_tree_files(link.get("descomprimidos"), files, code, next_index=1)
        return files

    def _collect_tree_files(
        self,
        node: dict | list | None,
        files: list[dict],
        parent_code: str,
        next_index: int = 1,
    ) -> int:
        if isinstance(node, list):
            for item in node:
                next_index = self._collect_tree_item(item, files, parent_code, next_index)
            return next_index
        if not isinstance(node, dict):
            return next_index
        return self._collect_tree_item(node, files, parent_code, next_index)

    def _collect_tree_item(
        self,
        node: dict,
        files: list[dict],
        parent_code: str,
        next_index: int,
    ) -> int:
        code = self._compose_code(parent_code, next_index)
        node["codigo"] = code
        files.append(node)
        next_index += 1
        contenido = node.get("contenido")
        if isinstance(contenido, list):
            self._collect_tree_files(contenido, files, code, next_index=1)
        return next_index

    def _format_code_part(self, value: str | None) -> str:
        if not value:
            return ""
        parts = str(value).split(".")
        cleaned = []
        for part in parts:
            stripped = part.lstrip("0")
            cleaned.append(stripped if stripped else "0")
        return ".".join(cleaned)

    def _compose_code(self, parent_code: str, index: int) -> str:
        if not parent_code:
            return str(index)
        return f"{parent_code}.{index}"

    def _derive_doc_status(self, doc_data: dict) -> str:
        has_links = self._doc_has_links(doc_data)
        formato = (doc_data.get("formato") or "").strip().lower()
        current = (doc_data.get("estado_formato") or "").strip().lower()

        if current:
            return current
        if not has_links and formato == "doc digital":
            doc_data["estado_formato"] = "verificado"
            return "verificado"
        doc_data["estado_formato"] = "detectado"
        return "detectado"

    def _doc_has_links(self, doc_data: dict) -> bool:
        return bool((doc_data.get("anexos_detectados") or []) + (doc_data.get("vinculados_detectados") or []))

    def _on_row_status_changed(self, doc_data: dict, widget: MiniStatusBar, status: str) -> None:
        doc_data["estado_formato"] = status
        widget.set_status(status)
        self._persist_exeva_payload()
        self._update_global_status_from_rows()

    def _persist_exeva_payload(self) -> None:
        payload = dict(self.exeva_payload or {})
        payload.setdefault("EXEVA", {})
        payload["EXEVA"]["documentos"] = self.documentos
        self.exeva_payload = payload
        if self.current_project_id:
            self.data_manager.save_exeva_data(self.current_project_id, payload)

    def _update_global_status_from_rows(self) -> None:
        if not self.documentos or not self.current_project_id:
            return
        statuses = [self._derive_doc_status(doc) for doc in self.documentos]
        if any(status == "error" for status in statuses):
            global_status = "error"
        elif all(status == "verificado" for status in statuses):
            global_status = "verificado"
        elif all(status == "detectado" for status in statuses):
            global_status = "detectado"
        else:
            global_status = "edicion"
        idx = self.timeline.current_step
        self.status_bar.set_status(global_status)
        self.timeline.set_current_step(idx, global_status)
        self.data_manager.update_step_status(
            self.current_project_id,
            "EXEVA",
            step_index=idx,
            step_status=global_status,
            global_status=global_status,
        )
