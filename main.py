import sys
import os

# Ajuste de path (según tu archivo original)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from src.views.pages.main_window import MainWindow

def load_styles(app):
    style_path = os.path.join(os.path.dirname(__file__), 'src', 'views', 'styles.qss')
    # --- CAMBIO AQUÍ: Agregamos encoding='utf-8' ---
    with open(style_path, 'r', encoding='utf-8') as f:
        contenido = f.read()
        app.setStyleSheet(contenido)

def main():
    app = QApplication(sys.argv)
    # 1. Cargar estilos
    load_styles(app)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()