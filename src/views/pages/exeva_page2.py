from functools import partial
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QAbstractItemView,
    QHeaderView,
    QPushButton,
)

from src.views.components.results_table import EditableTableCard
from src.views.components.mini_status import MiniStatusBar
from src.views.components.pdf_viewer import PdfViewer
from src.views.components.links_review import LinksReviewDialog


class Exeva2Page(QWidget):
    log_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Exeva2Page")
        self.current_project_id = None
        self.documentos = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(40, 30, 40, 30)
        self.content_layout.setSpacing(15)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_placeholder = QLabel("Resultados EXEVA Paso 2.")
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
                ("anexos_detectados", "Anexos"),
                ("vinculados_detectados", "Vinculados"),
                ("comprimidos", "Comprimidos"),
                ("ver_anexos", "Ver anexos"),
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
            "anexos_detectados",
            "vinculados_detectados",
            "comprimidos",
            "ver_anexos",
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

    def set_documentos(self, documentos: list[dict]) -> None:
        self.documentos = documentos
        self.lbl_placeholder.setVisible(not bool(documentos))
        self._set_results_table(documentos)

    def _set_results_table(self, documentos: list[dict]) -> None:
        rows = [
            {
                "n": doc.get("n", ""),
                "folio": doc.get("folio", ""),
                "titulo": doc.get("titulo", ""),
                "remitido_por": doc.get("remitido_por", ""),
                "fecha": doc.get("fecha", ""),
                "formato": doc.get("formato", ""),
                "anexos_detectados": str(len(doc.get("anexos_detectados") or [])),
                "vinculados_detectados": str(len(doc.get("vinculados_detectados") or [])),
                "comprimidos": str(self._count_compressed_links(doc)),
                "ver_anexos": "",
                "ver_doc": "",
                "estado_doc": "",
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
            estado_col = next(
                (idx for idx, (key, _label) in enumerate(self.results_table.columns) if key == "estado_doc"),
                None,
            )
            if estado_col is not None:
                for row_idx, doc in enumerate(documentos):
                    status_widget = MiniStatusBar(self.results_table.table)
                    status_widget.set_status(doc.get("estado_validacion", "detectado"))
                    self.results_table.table.setCellWidget(row_idx, estado_col, status_widget)
            anexos_col = next(
                (idx for idx, (key, _label) in enumerate(self.results_table.columns) if key == "ver_anexos"),
                None,
            )
            if anexos_col is not None:
                for row_idx, doc in enumerate(documentos):
                    anexos = doc.get("anexos_detectados") or []
                    vinculados = doc.get("vinculados_detectados") or []
                    if anexos or vinculados:
                        button = QPushButton("Ver anexos", self.results_table.table)
                        button.setObjectName("BtnActionSecondary")
                        button.clicked.connect(partial(self._open_links_review, doc))
                        self.results_table.table.setCellWidget(row_idx, anexos_col, button)
            self.results_table.table.resizeColumnsToContents()

    def _open_pdf_viewer(self, doc_data: dict) -> None:
        viewer = PdfViewer(doc_data, self, self.current_project_id)
        viewer.show()

    def _open_links_review(self, doc_data: dict) -> None:
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
            return

        title = str(doc_data.get("titulo") or "Doc")
        parent_n = str(doc_data.get("n") or doc_data.get("num_doc") or "0")
        pid = self.current_project_id or ""

        dialog = LinksReviewDialog(title, links, pid, parent_n, self)

        if dialog.exec() and dialog.modified:
            new_links = dialog.get_links()
            doc_data["anexos_detectados"] = [x for x in new_links if x.get("tipo") == "anexo"]
            doc_data["vinculados_detectados"] = [x for x in new_links if x.get("tipo") == "vinculado"]
            self._refresh_row_counts(doc_data)

    def _refresh_row_counts(self, doc_data: dict) -> None:
        target_n = str(doc_data.get("n") or "")
        table = self.results_table.table

        col_n, col_anex, col_vinc, col_comp = -1, -1, -1, -1
        for c in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(c)
            if not header_item:
                continue
            h = header_item.text()
            if h == "N° Documento":
                col_n = c
            elif h == "Anexos":
                col_anex = c
            elif h == "Vinculados":
                col_vinc = c
            elif h == "Comprimidos":
                col_comp = c

        if col_n == -1:
            return

        for r in range(table.rowCount()):
            item = table.item(r, col_n)
            if item and item.text() == target_n:
                n_a = len(doc_data.get("anexos_detectados", []))
                n_v = len(doc_data.get("vinculados_detectados", []))
                n_c = self._count_compressed_links(doc_data)

                if col_anex != -1:
                    table.item(r, col_anex).setText(str(n_a))
                if col_vinc != -1:
                    table.item(r, col_vinc).setText(str(n_v))
                if col_comp != -1:
                    table.item(r, col_comp).setText(str(n_c))
                return

    def _count_compressed_links(self, doc_data: dict) -> int:
        items = (doc_data.get("anexos_detectados") or []) + (doc_data.get("vinculados_detectados") or [])
        return sum(1 for item in items if self._is_compressed_item(item))

    @staticmethod
    def _compressed_extensions() -> tuple[str, ...]:
        return (
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
            ".tgz",
            ".bz2",
            ".xz",
            ".zst",
            ".tar.gz",
            ".tar.bz2",
            ".tar.xz",
            ".tar.zst",
        )

    def _is_compressed_item(self, item: object) -> bool:
        if isinstance(item, dict):
            candidates = []
            url = str(item.get("url") or "")
            if url:
                parsed = urlparse(url)
                candidates.append(parsed.path or url)
            candidates.extend(
                str(item.get(key) or "")
                for key in ("titulo", "info_extra")
            )
            return any(self._has_compressed_extension(value) for value in candidates)
        return self._has_compressed_extension(str(item))

    def _has_compressed_extension(self, value: str) -> bool:
        if not value:
            return False
        cleaned = value.lower().strip()
        for delimiter in ("?", "#"):
            if delimiter in cleaned:
                cleaned = cleaned.split(delimiter, 1)[0]
        return any(cleaned.endswith(ext) for ext in self._compressed_extensions())
