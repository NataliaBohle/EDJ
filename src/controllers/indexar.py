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
