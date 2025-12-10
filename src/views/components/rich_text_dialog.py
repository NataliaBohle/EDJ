from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox


class RichTextEditorDialog(QDialog):
    """Dialogo sencillo para editar contenido enriquecido."""

    def __init__(self, parent=None, title: str = "Editar contenido", initial_html: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(True)
        if initial_html:
            # Usamos HTML para preservar tablas, imágenes u otro formato pegado
            self.editor.setHtml(initial_html)

        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
                                   parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_html(self) -> str:
        return self.editor.toHtml()