from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel


class Chapter(QFrame):
    def __init__(self, title_text="Título"):
        super().__init__()
        self.setObjectName("Chapter")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        self.setLayout(layout)

        # Etiqueta del título
        self.title_label = QLabel(title_text)
        self.title_label.setObjectName("ChapterTitle")
        layout.addWidget(self.title_label)