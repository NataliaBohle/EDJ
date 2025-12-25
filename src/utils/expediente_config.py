DEFAULT_STEPS = ["Detectado", "Descargar", "Convertir", "Formatear", "Índice", "Compilar"]
SHORT_STEPS = ["Detectado", "Descargar", "Compilar"]


def steps_for_expediente(code, info):
    expediente_tipo = info.get("tipo")
    if code == "ANTGEN":
        return SHORT_STEPS
    return DEFAULT_STEPS
