from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter, QStackedWidget
from PyQt6.QtCore import Qt
from src.views.components.header import Header
from src.views.components.menu import Menu
from src.views.components.log_screen import LogScreen
from src.views.components.sidebar import Sidebar
from src.views.pages.new_ebook import NewEbook
from src.views.pages.cont_ebook import ContEbook
from src.views.pages.project_view import ProjectView
from src.views.pages.antgen_page import AntGenPage
from src.views.pages.exeva_page1 import Exeva1Page
from src.views.pages.exeva_page2 import Exeva2Page
# Asegúrate de que el nombre del archivo coincida (fetch_exp o fetch_exp_controller)
from src.controllers.fetch_exp import FetchExp
from src.controllers.step_controller import StepController


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

        # --- 1. STACK DE PÁGINAS ---
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.setObjectName("WorkspaceStack")
        self.v_splitter.addWidget(self.workspace_stack)

        # Index 0: Página vacía
        self.page_empty = QWidget()
        self.page_empty.setObjectName("PageEmpty")
        self.workspace_stack.addWidget(self.page_empty)

        # Index 1: Nuevo Expediente
        self.page_new_ebook = NewEbook()
        self.workspace_stack.addWidget(self.page_new_ebook)

        # IVista de Proyecto
        self.page_project_view = ProjectView()
        self.workspace_stack.addWidget(self.page_project_view)

        # Continuar proyecto
        self.page_cont_ebook = ContEbook()
        self.workspace_stack.addWidget(self.page_cont_ebook)

        # ANTGEN
        self.antgen_page = AntGenPage()
        self.workspace_stack.addWidget(self.antgen_page)

        # Inicializar Exeva Page
        self.exeva_page = Exeva1Page()
        self.workspace_stack.addWidget(self.exeva_page)

        self.exeva_page2 = Exeva2Page()
        self.workspace_stack.addWidget(self.exeva_page2)

        # --- 2. LOG SCREEN ---
        self.log_screen = LogScreen()
        self.v_splitter.addWidget(self.log_screen)
        self.h_splitter.addWidget(self.content_area)

        # --- 3. CONTROLADORES (¡IMPORTANTE: INICIALIZAR AQUÍ!) ---
        self.fetch_controller = FetchExp(self)
        self.step_controller = StepController(self)

        # --- 4. CONEXIONES ---
        self.menu.btn_new.clicked.connect(self.on_new_expediente)  # Usar función wrapper
        self.menu.btn_continue.clicked.connect(self.show_continue_page)
        self.log_screen.visibility_changed.connect(self.update_log_splitter)

        # Conexiones entre páginas
        self.page_cont_ebook.project_selected.connect(self.show_project_view)
        self.page_project_view.action_requested.connect(self.step_controller.handle_activation)
        self.page_project_view.log_requested.connect(self.log_screen.add_log)
        self.antgen_page.log_requested.connect(self.log_screen.add_log)
        self.exeva_page.log_requested.connect(self.log_screen.add_log)
        self.exeva_page2.log_requested.connect(self.log_screen.add_log)
        self.exeva_page.step2_requested.connect(self.show_exeva_page2)
        self.exeva_page2.back_requested.connect(self.show_exeva_page)


        # --- 5. TAMAÑOS INICIALES ---
        self.h_splitter.setCollapsible(0, False)
        self.h_splitter.setSizes([150, 950])
        self.h_splitter.setStretchFactor(1, 1)

        self.v_splitter.setCollapsible(0, False)
        self.v_splitter.setSizes([550, 150])
        self.v_splitter.setStretchFactor(0, 1)

    # --- FUNCIONES ---
    def show_new_ebook_page(self):
        self.log_screen.add_log("Navegando a: Nuevo Expediente")
        self.workspace_stack.setCurrentWidget(self.page_new_ebook)
        self.sidebar.clear()

    def show_project_view(self, project_id):
        """Cambia a la pantalla de vista de proyecto y carga datos."""
        self.log_screen.add_log(f"📂 Abriendo proyecto existente: {project_id}")
        self.page_project_view.load_project(project_id)
        self.workspace_stack.setCurrentWidget(self.page_project_view)

        self.sidebar.clear()
        self.sidebar.add_option(f"Proyecto Activo\nID {project_id}")

    def show_continue_page(self):
        self.log_screen.add_log("Consultando proyectos guardados...")
        self.page_cont_ebook.load_projects()
        self.workspace_stack.setCurrentWidget(self.page_cont_ebook)

        self.sidebar.clear()
        self.sidebar.add_option("Seleccione un proyecto\nde la lista.")

    def show_antgen_page(self, project_id):
        self.log_screen.add_log(f"Entrando a Antecedentes Generales: {project_id}")
        self.antgen_page.load_project(project_id)
        self.workspace_stack.setCurrentWidget(self.antgen_page)

    def show_exeva_page(self, project_id):
        self.log_screen.add_log(f"Entrando a EXEVA: {project_id}")
        self.exeva_page.load_project(project_id)
        self.workspace_stack.setCurrentWidget(self.exeva_page)

    def show_exeva_page2(self, project_id):
        self.log_screen.add_log(f"Entrando a EXEVA Paso 2: {project_id}")
        self.exeva_page2.load_project(project_id)
        self.workspace_stack.setCurrentWidget(self.exeva_page2)

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