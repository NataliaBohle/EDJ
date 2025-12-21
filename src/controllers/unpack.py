import os
import json
import shutil
import zipfile
import rarfile
import py7zr
import subprocess
from pathlib import Path

EXT_COMP = {".zip", ".rar", ".7z"}
fallidos = []

def extrae(clave, ID):
    # Ajusta la ruta del UNRAR si usas binario local
    rarfile.UNRAR_TOOL = r"src/controllers/UnRAR.exe"

    carpeta = f"{clave}_{ID}"
    ruta_base = Path(carpeta) / "Archivos"
    json_original = Path(carpeta) / f"02{clave}_{ID}.json"
    json_nuevo = Path(carpeta) / f"03{clave}_{ID}.json"
    ruta_base.mkdir(parents=True, exist_ok=True)
    shutil.copy(json_original, json_nuevo)

    with open(json_nuevo, "r", encoding="utf-8") as f:
        documentos = json.load(f)

    def ex_unrar(archivo_rar, carpeta_destino):
        print(f"[PASA A SUBPROCESO] {archivo_rar.name}")
        comando = [
            str(rarfile.UNRAR_TOOL), "x", "-y",
            str(archivo_rar),
            str(carpeta_destino)
        ]
        resultado = subprocess.run(comando, capture_output=True, text=True)
        if resultado.returncode != 0:
            raise RuntimeError(f"UNRAR falló:\n{resultado.stderr.strip()}")

    def ex_recursivo(archivo, folder_out, nivel=0, max_nivel=20):
        ext = archivo.suffix.lower()
        try:
            if nivel > max_nivel:
                raise RecursionError(f"Límite de niveles alcanzado ({max_nivel})")
            print(f"Descomprimiendo: {archivo.name} → {folder_out}")
            if ext == ".zip":
                with zipfile.ZipFile(archivo, 'r') as zip_ref:
                    zip_ref.extractall(folder_out)
            elif ext == ".rar":
                try:
                    with rarfile.RarFile(str(archivo), 'r') as rar_ref:
                        rar_ref.extractall(folder_out)
                except Exception:
                    print(f"rarfile falló con {archivo.name}, usando subproceso...")
                    ex_unrar(archivo, folder_out)
            elif ext == ".7z":
                with py7zr.SevenZipFile(archivo, mode="r") as z:
                    z.extractall(path=folder_out)
            else:
                raise ValueError(f"Error en extensión: {ext}")

            # Descomprime también los anidados
            for root, _, files in os.walk(folder_out):
                for fname in files:
                    fpath = Path(root) / fname
                    if fpath.suffix.lower() in EXT_COMP:
                        nueva_carpeta = fpath.with_suffix("")
                        if not nueva_carpeta.exists() or not any(nueva_carpeta.iterdir()):
                            nueva_carpeta.mkdir(parents=True, exist_ok=True)
                            ex_recursivo(fpath, nueva_carpeta, nivel + 1)
        except Exception as e:
            fallidos.append({
                "archivo": archivo.name,
                "ruta": str(archivo),
                "error": str(e)
            })

    print("🔍 Buscando y descomprimiendo archivos...")
    for root, _, files in os.walk(ruta_base):
        for file in files:
            archivo = Path(root) / file
            if not archivo.exists():
                encontrados = list(ruta_base.rglob(archivo.name))
                if encontrados:
                    archivo = encontrados[0]
                    print(f"🛠️ Redirigido a ruta encontrada: {archivo}")
                else:
                    print(f"❌ Archivo no encontrado: {archivo}")
                    fallidos.append({
                        "archivo": archivo.name,
                        "ruta": str(archivo),
                        "error": "Archivo no encontrado"
                    })
                    continue
            if archivo.suffix.lower() in EXT_COMP:
                carpeta_out = archivo.with_suffix("")
                if not carpeta_out.exists() or not any(carpeta_out.iterdir()):
                    carpeta_out.mkdir(parents=True, exist_ok=True)
                    ex_recursivo(archivo, carpeta_out)

    def normalizar_ruta(ruta):
        return str(Path(ruta).as_posix())

    def ruta_sin_repeticiones(carpeta, archivo_rel):
        partes = Path(archivo_rel).parts
        if partes and partes[0] == "Archivos":
            partes = partes[1:]  # elimina 'Archivos' si ya viene en la ruta
        return normalizar_ruta(Path(carpeta) / "Archivos" / Path(*partes))

    def ajson(path: Path):
        def indexar(path: Path):
            carpeta_top = f"{clave}_{ID}"
            estructura = {
                "nombre": path.name,
                "formato": "carpeta" if path.is_dir() else (path.suffix.lower().lstrip(".") or "desconocido"),
                "ruta": ruta_sin_repeticiones(carpeta_top, path.relative_to(ruta_base)),
            }
            if path.is_dir():
                estructura["contenido"] = []
                carpetas = sorted([p for p in path.iterdir() if p.is_dir()])
                archivos = sorted([p for p in path.iterdir() if p.is_file()])
                for carpeta_ in carpetas:
                    estructura["contenido"].append(indexar(carpeta_))
                for archivo_ in archivos:
                    estructura["contenido"].append({
                        "nombre": archivo_.name,
                        "formato": archivo_.suffix.lower().lstrip(".") or "desconocido",
                        "ruta": ruta_sin_repeticiones(carpeta_top, archivo_.relative_to(ruta_base))
                    })
            return estructura
        return indexar(path)

    # Asignar N recursivamente
    def asignarN(nodo):
        if isinstance(nodo, dict):
            if "contenido" in nodo and isinstance(nodo["contenido"], list):
                for idx, item in enumerate(nodo["contenido"], 1):
                    item["n"] = f"{idx:04d}"
                    asignarN(item)
            if "ruta" in nodo and "n" not in nodo:
                nodo["n"] = "0001"
            for v in nodo.values():
                asignarN(v)
        elif isinstance(nodo, list):
            for item in nodo:
                asignarN(item)

    # NUEVO: indexar descomprimidos para doc principal y para url_a_exp/url_a_docdig/url_a_pdf
    def indexar_descomprimidos_para_item(item) -> bool:
        """
        Si item contiene 'ruta' a un comprimido, busca la carpeta con el mismo nombre sin extensión
        y, si existe, inserta item['descomprimidos'] = ajson(carpeta).
        Devuelve True si indexó, False si no.
        """
        ruta_item = item.get("ruta")
        if not ruta_item:
            return False
        p = Path(ruta_item)
        # Asegurar que sea relativo desde la raíz del proyecto
        if not p.is_absolute():
            p = Path(".") / p
        if not p.exists():
            return False
        if p.suffix.lower() not in EXT_COMP:
            return False
        carpeta_ext = p.with_suffix("")
        if carpeta_ext.exists() and carpeta_ext.is_dir():
            try:
                item["descomprimidos"] = ajson(carpeta_ext)
                return True
            except Exception as e:
                print(f"⚠️ No se pudo indexar carpeta {carpeta_ext}: {e}")
        return False

    indexados_docs = 0
    indexados_anexos = 0

    print("🗂️ Indexando archivos descomprimidos en JSON...")
    for idx, doc in enumerate(documentos, 1):
        print(f"   → Documento {idx}/{len(documentos)}: {doc.get('titulo', '')[:60]}...")

        # 1) Doc principal si fuera comprimido
        if "ruta" in doc:
            if indexar_descomprimidos_para_item(doc):
                indexados_docs += 1

        # 2) Listas de anexos conocidas
        for lista_nombre in ("url_a_exp", "url_a_docdig", "url_a_pdf", "vinculos"):
            lista = doc.get(lista_nombre, [])
            if not isinstance(lista, list):
                continue
            for item in lista:
                # Si ya tenía una indexación previa, limpiarla para regenerar
                if "descomprimidos" in item:
                    del item["descomprimidos"]
                if indexar_descomprimidos_para_item(item):
                    indexados_anexos += 1

    print(f"🔢 Asignando N...")
    asignarN(documentos)

    with open(json_nuevo, "w", encoding="utf-8") as f:
        json.dump(documentos, f, indent=2, ensure_ascii=False)

    print(f"\n✅ JSON nuevo guardado en: {json_nuevo}")
    print(f"📦 Descomprimidos indexados: doc={indexados_docs}, anexos={indexados_anexos}")

    if fallidos:
        print("\n⚠️ Archivos que NO pudieron ser descomprimidos:")
        for f in fallidos:
            print(f"- {f['archivo']} ({f['ruta']})")
            print(f"  Motivo: {f['error']}")
    else:
        print("\n🟢 Todos los archivos descomprimidos correctamente.")
