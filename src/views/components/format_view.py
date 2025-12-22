from __future__ import annotations

import os
import json
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QHeaderView,
    QAbstractItemView,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QMessageBox,
    QFileDialog,
    QSizePolicy,
)
from PyQt6.QtGui import QDesktopServices

from src.views.components.mini_status import MiniStatusBar
from src.views.components.pdf_viewer import PdfViewer


class FormatViewDialog(QDialog):
    SUMMARY_COLUMNS = [
        "PDF",
        "DOC",
        "XLS",
        "PPT",
        "TXT",
        "GEO",
        "WEB",
        "IMG",
        "Comprimidos",
        "Carpetas",
        "Otros",
    ]

    def __init__(self, title: str, files: list[dict], parent=None, project_id: str | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Formatos asociados: {title}")

        # Mantuvimos el ancho aumentado para que se vea bien tu nueva distribución
        self.resize(1350, 700)

        self.files = list(files)
        self._source_files = [item for item in self.files if isinstance(item, dict)]
        self.display_files = [dict(item) for item in self._source_files]
        self.project_id = project_id
        self.modified = False
        self._row_items: list[dict] = []
        self._is_populating = False

        layout = QVBoxLayout(self)

        lbl_info = QLabel("Resumen de formatos detectados para este documento.")
        lbl_info.setObjectName("FormatViewInfoLabel")
        layout.addWidget(lbl_info)

        # --- Summary Table ---
        self.summary_table = QTableWidget()
        self.summary_table.setObjectName("FormatViewSummaryTable")
        self.summary_table.setRowCount(1)
        self.summary_table.setColumnCount(len(self.SUMMARY_COLUMNS))
        self.summary_table.setHorizontalHeaderLabels(self.SUMMARY_COLUMNS)
        self.summary_table.setWordWrap(False)
        self.summary_table.setShowGrid(False)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.summary_table.setMaximumHeight(90)

        header = self.summary_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.summary_table)

        # --- Files Table ---
        self.files_table = QTableWidget()
        self.files_table.setObjectName("FormatViewFilesTable")
        self.files_table.setColumnCount(9)
        self.files_table.setHorizontalHeaderLabels(
            [
                "Código",
                "Nombre",
                "Formato",
                "Ver archivo",
                "Formatear",
                "Reemplazar",
                "Estado",
                "Excluir",
                "Observaciones",
            ]
        )
        self.files_table.setWordWrap(True)
        self.files_table.setShowGrid(False)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.files_table.setSortingEnabled(False)

        # --- AJUSTE DE ALTURA DE FILAS ---
        self.files_table.verticalHeader().setDefaultSectionSize(48)
        self.files_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        self.files_table.itemChanged.connect(self._on_item_changed)

        files_header = self.files_table.horizontalHeader()
        files_header.setSortIndicatorShown(True)
        #files_header.sectionClicked.connect(self._on_sort_requested)

        # --- TU CONFIGURACIÓN DE COLUMNAS ---

        # 0. Código: Fijo, pequeño
        files_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.files_table.setColumnWidth(0, 50)

        # 1. Nombre: Interactivo
        files_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.files_table.setColumnWidth(1, 200)

        # 2. Formato: Interactivo
        files_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.files_table.setColumnWidth(2, 90)

        # 3, 4, 5. Botones: Interactivo
        for col_idx in [3, 4, 5]:
            files_header.setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Interactive)
            self.files_table.setColumnWidth(col_idx, 100)

        # 6. Estado: Interactivo
        files_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self.files_table.setColumnWidth(6, 120)

        # 7. Excluir: Interactivo
        files_header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        self.files_table.setColumnWidth(7, 100)

        # 8. Observaciones: STRETCH. Toma TODO el espacio restante
        files_header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.files_table)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch(1)
        self.save_button = QPushButton("Guardar cambios")
        self.save_button.setObjectName("FormatViewSaveButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.setFixedHeight(32)
        self.save_button.clicked.connect(self._save_and_close)
        actions_layout.addWidget(self.save_button)
        layout.addLayout(actions_layout)

        self.placeholder = QLabel(
            "El visor de formatos se completará en la siguiente etapa."
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setObjectName("FormatViewPlaceholder")
        layout.addWidget(self.placeholder)

        self._populate_summary()
        self._populate_files()

    def _populate_summary(self) -> None:
        counts = {key: 0 for key in self.SUMMARY_COLUMNS}
        for item in self.files:
            if not isinstance(item, dict):
                continue
            fmt = self._infer_format(item)
            category = self._categorize_format(fmt)
            counts[category] += 1

        for col_idx, col_name in enumerate(self.SUMMARY_COLUMNS):
            item = QTableWidgetItem(str(counts[col_name]))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.summary_table.setItem(0, col_idx, item)

    def _populate_files(self) -> None:
        self._is_populating = True
        self._row_items = []
        self.files_table.setSortingEnabled(False)
        self.files_table.setRowCount(0)
        for row_idx, item in enumerate(self.display_files):
            self.files_table.insertRow(row_idx)
            self._row_items.append(item)

            code = self._format_code_from_item(item)
            name = self._format_name(item)
            fmt = item.get("formato") or self._infer_format(item)

            code_item = QTableWidgetItem(code)
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.files_table.setItem(row_idx, 0, code_item)
            self.files_table.setItem(row_idx, 1, QTableWidgetItem(name))
            self.files_table.setItem(row_idx, 2, QTableWidgetItem(str(fmt)))

            self._add_action_btn(row_idx, 3, "Ver", self._open_file, enabled=bool(item.get("ruta")))
            self._add_action_btn(row_idx, 4, "Formatear", self._format_file)
            has_replacement = bool(item.get("archivo_original"))
            self._add_action_btn(
                row_idx,
                5,
                "Reemplazar",
                self._replace_file,
                is_green=has_replacement,
            )

            status_widget = MiniStatusBar(self.files_table)
            status_widget.set_status(self._default_status(item, fmt))
            self.files_table.setCellWidget(row_idx, 6, status_widget)

            # Observaciones
            default_observation = self._default_observation(item, fmt)
            existing_observation = item.get("observacion")

            if not existing_observation and default_observation:
                item["observacion"] = default_observation
                self.modified = True
            elif "observacion" not in item:
                item["observacion"] = existing_observation or ""

            had_excluir = "excluir" in item
            item.setdefault("excluir", "N")
            if not had_excluir:
                self.modified = True

            observations = QTableWidgetItem(item.get("observacion", ""))
            observations.setFlags(observations.flags() | Qt.ItemFlag.ItemIsEditable)
            self.files_table.setItem(row_idx, 8, observations)

            # Botón Excluir
            self._ensure_excluir_for_special(item, fmt)
            is_excluded = self._should_exclude_red(item, fmt)
            self._add_action_btn(row_idx, 7, "Excluir", self._exclude_file, is_red=is_excluded)
            self._refresh_format_button(row_idx, item, fmt)

        self._is_populating = False
        self.files_table.setSortingEnabled(True)

    def _add_action_btn(
        self,
        row: int,
        col: int,
        text: str,
        callback,
        enabled: bool = True,
        is_red: bool = False,
        is_green: bool = False,
    ) -> None:
        btn = QPushButton(text)
        btn.setEnabled(enabled)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn.setObjectName("FormatViewActionButton")
        if is_red:
            self._set_action_variant(btn, "danger")
        elif is_green:
            self._set_action_variant(btn, "success")
        else:
            self._set_action_variant(btn, "primary")
        btn.clicked.connect(lambda _, r=row: callback(r))

        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        # CAMBIO AQUÍ: Poner todos los márgenes en 0
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn)
        self.files_table.setCellWidget(row, col, wrapper)

    def _open_file(self, row: int) -> None:
        item = self.display_files[row]
        ruta = item.get("ruta")
        if not ruta:
            return
        file_path = self._resolve_path(str(ruta))
        if not file_path or not Path(file_path).exists():
            QMessageBox.warning(self, "Archivo no encontrado", "No se encontró el archivo.")
            return
        if file_path.lower().endswith(".pdf"):
            viewer = PdfViewer({"ruta": file_path, "titulo": item.get("titulo") or item.get("nombre")}, self,
                               self.project_id)
            viewer.exec()
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def _format_file(self, _row: int) -> None:
        QMessageBox.information(self, "Formatear", "Acción de formateo pendiente de implementación.")

    def _replace_file(self, _row: int) -> None:
        if _row >= len(self.display_files):
            return
        item = self.display_files[_row]
        ruta_actual = item.get("ruta")
        initial_dir = ""
        if ruta_actual:
            resolved = self._resolve_path(str(ruta_actual))
            if resolved:
                initial_dir = str(Path(resolved).parent)
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de reemplazo",
            initial_dir,
            "Todos los archivos (*)",
        )
        if not filename:
            return

        nueva_ruta = self._normalize_replacement_path(filename)
        if ruta_actual and "archivo_original" not in item:
            item["archivo_original"] = ruta_actual

        if nueva_ruta == ruta_actual:
            return

        item["ruta"] = nueva_ruta
        item["archivo"] = Path(filename).name

        fmt = self._format_from_value(nueva_ruta) or item.get("formato")
        if fmt:
            item["formato"] = fmt

        name_item = self.files_table.item(_row, 1)
        if name_item:
            name_item.setText(self._format_name(item))
        format_item = self.files_table.item(_row, 2)
        if format_item:
            format_item.setText(str(item.get("formato") or self._infer_format(item)))
        self._refresh_format_button(_row, item)

        view_wrapper = self.files_table.cellWidget(_row, 3)
        if view_wrapper:
            view_button = view_wrapper.findChild(QPushButton)
            if view_button:
                view_button.setEnabled(bool(item.get("ruta")))

        replace_wrapper = self.files_table.cellWidget(_row, 5)
        if replace_wrapper:
            replace_button = replace_wrapper.findChild(QPushButton)
            if replace_button:
                self._set_action_variant(replace_button, "success")

        self.modified = True

    def _exclude_file(self, row: int) -> None:
        if row >= self.files_table.rowCount():
            return
        item_data = self._row_items[row]

        if item_data.get("excluir") == "S":
            # Revertir
            item_data["excluir"] = "N"
            default_obs = self._default_observation(item_data, item_data.get("formato"))
            current_obs = item_data.get("observacion", "")
            excluded_msg = 'Este archivo no se puede presentar en este documento. Revise la carpeta "Excepciones".'

            if current_obs == excluded_msg:
                item_data["observacion"] = default_obs
        else:
            # Excluir
            item_data["excluir"] = "S"
            message = (
                'Este archivo no se puede presentar en este documento. '
                'Revise la carpeta "Excepciones".'
            )
            item_data["observacion"] = message

        self.files_table.blockSignals(True)
        table_item = self.files_table.item(row, 8)
        if not table_item:
            table_item = QTableWidgetItem()
            self.files_table.setItem(row, 8, table_item)

        table_item.setText(item_data["observacion"])
        table_item.setFlags(table_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.files_table.blockSignals(False)

        self._refresh_exclude_button(row)

        self.modified = True

    def _save_and_close(self) -> None:
        try:
            self._apply_changes()

            cambios = {}
            for item in self.display_files:
                ruta = item.get("ruta")
                if not ruta:
                    continue

                attrs = {}
                if item.get("excluir") == "S":
                    attrs["excluir"] = "S"
                elif "excluir" in item and item.get("excluir") != "S":
                    attrs["excluir"] = "N"

                if item.get("observacion"):
                    attrs["observacion"] = item["observacion"]

                if attrs:
                    cambios[ruta] = attrs

            if self.project_id and cambios:
                success = False
                try:
                    from src.controllers.eval_format import actualizar_atributos_exeva
                    success = actualizar_atributos_exeva(self.project_id, cambios)
                except ImportError:
                    try:
                        from .eval_format import actualizar_atributos_exeva
                        success = actualizar_atributos_exeva(self.project_id, cambios)
                    except ImportError:
                        try:
                            from eval_format import actualizar_atributos_exeva
                            success = actualizar_atributos_exeva(self.project_id, cambios)
                        except ImportError:
                            raise ImportError("No se pudo importar 'actualizar_atributos_exeva'.")

                if not success:
                    QMessageBox.warning(self, "Advertencia",
                                        "No se pudieron guardar los cambios en el archivo JSON.")
                    return

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error de Guardado",
                                 f"Ocurrió un error crítico al intentar guardar:\n{str(e)}")

    def _apply_changes(self) -> None:
        for original, edited in zip(self._source_files, self.display_files):
            for key in ("excluir", "observacion", "ruta", "archivo_original", "archivo", "formato"):
                if key in edited:
                    original[key] = edited.get(key)
                elif key in {"excluir", "observacion"}:
                    original.pop(key, None)

    def _resolve_path(self, ruta: str) -> str:
        ruta_text = str(ruta).replace("/", os.sep).replace("\\", os.sep)
        if os.path.isabs(ruta_text):
            return str(Path(ruta_text).resolve())
        if self.project_id:
            base = Path(os.getcwd()) / "Ebook" / str(self.project_id)
            return str((base / ruta_text).resolve())
        return str((Path(os.getcwd()) / ruta_text).resolve())

    def _normalize_replacement_path(self, ruta: str) -> str:
        ruta_path = Path(str(ruta)).expanduser().resolve()
        if self.project_id:
            exeva_base = Path(os.getcwd()) / "Ebook" / str(self.project_id) / "EXEVA"
            try:
                rel = ruta_path.relative_to(exeva_base.resolve())
                return rel.as_posix()
            except Exception:
                pass
        return ruta_path.as_posix()

    def _format_code(self, code: str | None) -> str:
        if not code:
            return ""
        if isinstance(code, str) and "." in code:
            parts = code.split(".")
            cleaned = []
            for part in parts:
                stripped = part.lstrip("0")
                cleaned.append(stripped if stripped else "0")
            return ".".join(cleaned)
        if isinstance(code, str) and code.isdigit():
            return str(int(code)) if code else ""
        return str(code)

    def _format_code_from_item(self, item: dict) -> str:
        code_value = item.get("codigo") or item.get("n")
        return self._format_code(str(code_value)) if code_value else ""

    def _format_name(self, item: dict) -> str:
        for key in ("titulo", "nombre", "archivo"):
            value = item.get(key)
            if value:
                return str(value)
        ruta = item.get("ruta")
        if ruta:
            return Path(str(ruta)).name
        return "Archivo"

    def _default_status(self, item: dict, fmt: str | None) -> str:
        fmt_lower = (fmt or "").strip().lower()
        if fmt_lower in {
            "doc digital", "carpeta", "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz",
            "tar.gz", "tar.bz2", "tar.xz",
        }:
            return "verificado"
        return (item.get("estado_formato") or "detectado")

    def _default_observation(self, item: dict, fmt: str | None) -> str:
        fmt_lower = (fmt or "").strip().lower()
        if fmt_lower == "carpeta":
            return "Esta entrada corresponde a una carpeta. Se conserva para reflejar el orden de expediente"
        if fmt_lower == "doc digital":
            return ""
        category = self._categorize_format(fmt_lower)
        if category in {"Comprimidos", "GEO", "XLS", "Otros"}:
            return 'Este archivo no se puede convertir a PDF. Revise la carpeta "Archivos no PDF".'
        return ""

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._is_populating:
            return
        row = item.row()
        if row >= len(self._row_items):
            return
        if item.column() == 8:
            self._row_items[row]["observacion"] = item.text()
            self._ensure_excluir_for_special(self._row_items[row])
            self.modified = True
            self._refresh_exclude_button(row)

    def _should_exclude_red(self, item: dict, fmt: str | None = None) -> bool:
        current_fmt = fmt or item.get("formato") or self._infer_format(item)
        category = self._categorize_format(current_fmt)
        has_observacion = bool(item.get("observacion"))
        return (
            item.get("excluir") == "S"
            or category in {"Carpetas", "Comprimidos"}
            or has_observacion
        )

    def _ensure_excluir_for_special(self, item: dict, fmt: str | None = None) -> None:
        current_fmt = fmt or item.get("formato") or self._infer_format(item)
        category = self._categorize_format(current_fmt)
        has_observacion = bool(item.get("observacion"))
        if category in {"Carpetas", "Comprimidos"} or has_observacion:
            if item.get("excluir") != "S":
                item["excluir"] = "S"
                self.modified = True

    def _refresh_exclude_button(self, row: int) -> None:
        if row >= len(self._row_items):
            return
        item_data = self._row_items[row]
        self._ensure_excluir_for_special(item_data)
        is_red_style = self._should_exclude_red(item_data, item_data.get("formato"))
        wrapper = self.files_table.cellWidget(row, 7)
        if not wrapper:
            return
        btn = wrapper.findChild(QPushButton)
        if not btn:
            return
        if is_red_style:
            self._set_action_variant(btn, "danger")
        else:
            self._set_action_variant(btn, "primary")
        self._refresh_format_button(row, item_data)

    def _set_action_variant(self, btn: QPushButton, variant: str) -> None:
        btn.setProperty("variant", variant)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _refresh_format_button(
        self,
        row: int,
        item: dict | None = None,
        fmt: str | None = None,
    ) -> None:
        if row >= len(self._row_items):
            return
        item_data = item or self._row_items[row]
        current_fmt = fmt or item_data.get("formato") or self._infer_format(item_data)
        fmt_lower = (current_fmt or "").strip().lower()
        is_doc_digital = fmt_lower == "doc digital"
        is_excluded = self._should_exclude_red(item_data, current_fmt)
        wrapper = self.files_table.cellWidget(row, 4)
        if not wrapper:
            return
        btn = wrapper.findChild(QPushButton)
        if not btn:
            return
        if is_doc_digital:
            self._set_action_variant(btn, "success")
            btn.setProperty("formatLocked", "true")
            btn.setEnabled(False)
        else:
            self._set_action_variant(btn, "primary")
            btn.setProperty("formatLocked", False)
            btn.setEnabled(not is_excluded)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _infer_format(self, item: dict) -> str:
        candidates = [
            item.get("formato"), item.get("ruta"), item.get("url"),
            item.get("archivo"), item.get("nombre"), item.get("titulo"),
        ]
        for value in candidates:
            fmt = self._format_from_value(value)
            if fmt:
                return fmt
        return "otros"

    def _format_from_value(self, value: str | None) -> str | None:
        if not value:
            return None
        value_text = str(value).strip().lower()
        if value_text == "carpeta":
            return "carpeta"
        if value_text.startswith("http"):
            value_text = value_text.split("?", 1)[0]
        suffix = Path(value_text).suffix.lower()
        if suffix:
            return suffix.lstrip(".")
        return value_text if value_text else None

    def _categorize_format(self, fmt: str | None) -> str:
        if not fmt:
            return "Otros"
        fmt_lower = fmt.strip().lower()
        if fmt_lower == "carpeta":
            return "Carpetas"
        if fmt_lower in {"pdf"}:
            return "PDF"
        if fmt_lower in {"doc", "docx", "rtf", "odt", "wpd"}:
            return "DOC"
        if fmt_lower in {"xls", "xlsx", "xlsm", "csv", "parquet", "ods", "fods", "tsv", "dbf", "gsheet", "numbers"}:
            return "XLS"
        if fmt_lower in {"ppt", "pptx", "odp", "key", "gslides", "sxi", "shw", "prz"}:
            return "PPT"
        if fmt_lower in {"txt", "md", "log"}:
            return "TXT"
        if fmt_lower in {"shp", "shx", "dbf", "prj", "kml", "kmz", "geojson", "gml", "gpkg"}:
            return "GEO"
        if fmt_lower in {"jpg", "jpeg", "png", "gif", "tiff", "tif", "bmp"}:
            return "IMG"
        if fmt_lower in {"html", "php", "bin"}:
            return "WEB"
        if fmt_lower in {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz", "tar.gz", "tar.bz2", "tar.xz"}:
            return "Comprimidos"
        return "Otros"
