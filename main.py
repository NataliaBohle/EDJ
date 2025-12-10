import sys
import os

# Ajuste de path (según tu archivo original)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication
from src.views.main_window import MainWindow

def load_styles(app):
    # Ruta al archivo de estilos
    style_path = os.path.join(os.path.dirname(__file__), 'src', 'views', 'styles.qss')
    if os.path.exists(style_path):
        with open(style_path, 'r') as f:
            app.setStyleSheet(f.read())

def main():
    app = QApplication(sys.argv)
    # 1. Cargar estilos
    load_styles(app)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()