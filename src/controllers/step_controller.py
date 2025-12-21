from PyQt6.QtCore import QObject


class StepController(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.log = self.main_window.log_screen

    def handle_activation(self, project_id, code, step_index):
        """
        Enruta la acción según el código del expediente y el número de paso.
        """
        self.log.add_log(f"⚡ Solicitud: {code} -> Paso Índice {step_index}")

        # LÓGICA DE MAPEO
        accion = None

        if code == "ANTGEN":
            # CORRECCIÓN: Para ANTGEN, siempre queremos abrir la página de detalles,
            # incluso si el paso es "Compilar" (2) o "Listo".
            # La compilación real se hace desde dentro de esa página.
            self.main_window.show_antgen_page(project_id)
            return

        if code == "EXEVA":
            if step_index >= 2:
                self.main_window.show_exeva_page2(project_id)
            else:
                self.main_window.show_exeva_page(project_id)
            return

        else:
            # Lógica para otros expedientes futuros (EXEVA, EXPAC, etc.)
            if step_index == 1:
                accion = "DESCARGAR"
            elif step_index == 2:
                accion = "CONVERTIR"
            elif step_index == 3:
                accion = "FORMATEAR"
            elif step_index == 4:
                accion = "INDICE"
            elif step_index == 5:
                accion = "COMPILAR"

        # EJECUCIÓN (Solo para módulos que no redirigen a una página específica aún)
        if accion == "DESCARGAR":
            self.log.add_log(f"--> Iniciando módulo de DESCARGA para {code}...")
            # self.main_window.show_download_view(project_id, code)

        elif accion == "CONVERTIR":
            self.log.add_log(f"--> Iniciando módulo de CONVERSIÓN OCR para {code}...")

        elif accion == "FORMATEAR":
            self.log.add_log(f"--> Iniciando módulo de FORMATEO LEGAL para {code}...")

        elif accion == "INDICE":
            self.log.add_log(f"--> Iniciando Generador de ÍNDICE para {code}...")

        elif accion == "COMPILAR":
            self.log.add_log(f"--> Iniciando COMPILADOR DE TOMOS para {code}...")

        else:
            if code != "ANTGEN": # Evitar log duplicado si ya entramos al if de arriba
                self.log.add_log(f"⚠️ No hay acción configurada para el paso {step_index} en {code}.")
