import subprocess
import sys
import os
import importlib.util


def install_package(package):
    """Instala un paquete usando pip si no existe."""
    print(f"🔧 Instalando herramienta necesaria: {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def update_requirements():
    """Ejecuta pipreqs para actualizar el archivo."""
    print("📂 Escaneando directorio en busca de librerías utilizadas...")

    # Obtenemos la ruta del directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Comandos para ejecutar pipreqs
    # --force: Sobreescribe el archivo existente
    # --encoding=utf-8: Evita errores de caracteres en Windows
    # --ignore: Ignora carpetas virtuales o de sistema
    cmd = [
        "pipreqs",
        current_dir,
        "--force",
        "--encoding=utf-8",
        "--ignore=.venv,venv,env,.git,.idea,__pycache__"
    ]

    try:
        subprocess.check_call(cmd)
        print("\n✅ ¡Éxito! Tu archivo 'requirements.txt' ha sido actualizado.")

        # Mostramos el contenido
        print("-" * 30)
        with open("requirements.txt", "r") as f:
            print(f.read())
        print("-" * 30)

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Hubo un error al generar el archivo: {e}")
    except FileNotFoundError:
        print("\n⚠️ No se encontró el comando 'pipreqs'. Intentando ejecutar como módulo...")
        # Intento alternativo si el PATH falla
        try:
            subprocess.check_call([sys.executable, "-m", "pipreqs.pipreqs", "."] + cmd[2:])
            print("\n✅ ¡Éxito (modo alternativo)!")
        except Exception as e:
            print(f"\n❌ Error fatal: {e}")


if __name__ == "__main__":
    # 1. Verificar si pipreqs está instalado
    if importlib.util.find_spec("pipreqs") is None:
        install_package("pipreqs")

    # 2. Ejecutar la actualización
    update_requirements()