from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter, QStackedWidget
from PyQt6.QtCore import Qt
from src.views.components.header import Header
from src.views.components.menu import Menu
from src.views.components.log_screen import LogScreen
from src.views.components.sidebar import Sidebar
from src.views.pages.new_ebook import NewEbook
from src.views.pages.cont_ebook import ContEbook
from src.controllers.fetch_exp import FetchExp
from src.views.pages.project_view import ProjectView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDJ App")
        self.resize(1100, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.header = Header()
        self.main_layout.addWidget(self.header)

        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setHandleWidth(1)
        self.main_layout.addWidget(self.h_splitter)

        self.sidebar = Sidebar()
        self.h_splitter.addWidget(self.sidebar)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.menu = Menu()
        self.content_layout.addWidget(self.menu)

        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(1)
        self.content_layout.addWidget(self.v_splitter)

        # --- CAMBIO 1: STACK DE PÁGINAS ---
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("WorkspaceStack")
        self.v_splitter.addWidget(self.workspace_stack)

        # A. Agregamos una página vacía primero (Índice 0)
        # Esto asegura que al iniciar la app, se vea blanco/vacío.
        self.page_empty = QWidget()
        self.page_empty.setObjectName("PageEmpty")  # ID por si quieres darle color luego
        self.workspace_stack.addWidget(self.page_empty)

        # B. Página de Nuevo Expediente (Índice 1)
        self.page_new_ebook = NewEbook()
        self.workspace_stack.addWidget(self.page_new_ebook)

        # Index 2: Vista de Proyecto (NUEVO)
        self.page_project_view = ProjectView()
        self.workspace_stack.addWidget(self.page_project_view)

        # Index 3: Continuar (NUEVO)
        self.page_cont_ebook = ContEbook()
        self.workspace_stack.addWidget(self.page_cont_ebook)

       # --- Splitters
        self.log_screen = LogScreen()
        self.v_splitter.addWidget(self.log_screen)

        self.h_splitter.addWidget(self.content_area)

        # --- CONEXIONES ---
        self.menu.btn_new.clicked.connect(self.show_new_ebook_page)
        self.menu.btn_continue.clicked.connect(self.show_continue_page)
        self.log_screen.visibility_changed.connect(self.update_log_splitter)
        self.page_cont_ebook.project_selected.connect(self.show_project_view)

        # --- CAMBIO 2: TAMAÑOS INICIALES ---
        self.h_splitter.setCollapsible(0, False)
        # Ajustamos el sidebar a 150px (más angosto) y el resto al contenido
        self.h_splitter.setSizes([150, 950])
        self.h_splitter.setStretchFactor(1, 1)

        self.v_splitter.setCollapsible(0, False)
        self.v_splitter.setSizes([550, 150])
        self.v_splitter.setStretchFactor(0, 1)
    # --- CONTROLADORES ---
        self.fetch_controller = FetchExp(self)
    # --- FUNCIONES ---
    def show_new_ebook_page(self):
        self.log_screen.add_log("Navegando a: Nuevo Expediente")
        # Cambiamos a la página del formulario
        self.workspace_stack.setCurrentWidget(self.page_new_ebook)

    def show_project_view(self, project_id):
        """Cambia a la pantalla de vista de proyecto y carga datos."""
        self.page_project_view.load_project(project_id)
        self.workspace_stack.setCurrentWidget(self.page_project_view)

    def show_continue_page(self):
        self.log_screen.add_log("Consultando proyectos guardados...")
        self.page_cont_ebook.load_projects()  # Refrescar lista al entrar
        self.workspace_stack.setCurrentWidget(self.page_cont_ebook)

        # Actualizar Sidebar
        self.sidebar.clear()
        self.sidebar.add_option("Seleccione un proyecto\nde la lista.")

    def on_continue_expediente(self):
        self.log_screen.add_log("Retomando expediente existente...")

    def on_new_expediente(self):
        self.log_screen.add_log("Navegando a: Nuevo Expediente")
        self.workspace_stack.setCurrentWidget(self.page_new_ebook)
        self.sidebar.clear()

    def update_log_splitter(self, collapsed):
        if collapsed:
            self.v_splitter.setSizes([100000, 35])
        else:
            h = self.v_splitter.height()
            self.v_splitter.setSizes([h - 150, 150])
