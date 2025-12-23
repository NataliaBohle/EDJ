from PyQt6.QtCore import QObject


class StepController(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.log = self.main_window.log_screen

    def handle_activation(self, project_id, code, step_index, exp_context):
        """
        Enruta la acción según el código del expediente y el número de paso.
        """
        target_id = exp_context.get("target_id", project_id)
        self.log.add_log(
            f"⚡ Solicitud: {code} -> Paso Índice {step_index} (target: {target_id})"
        )

        self.main_window.show_ex_page(exp_context)
