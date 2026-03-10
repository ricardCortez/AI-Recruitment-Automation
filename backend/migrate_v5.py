"""
Migración v5 — agrega alertas_json y preguntas_json a la tabla analisis.
Ejecutar UNA SOLA VEZ después de actualizar analisis.py:

    cd backend
    python migrate_v5.py

SQLite no soporta ALTER TABLE ADD COLUMN con tipo JSON nativo,
pero lo guarda como TEXT (que es lo que SQLAlchemy usa internamente).
"""

import sqlite3
import os
import sys

def _resolver_ruta_db() -> str:
    """
    Busca la BD en los lugares posibles, en orden de prioridad:
    1. Variable DATABASE_URL del .env
    2. database/sistema_cv.db  (ruta estándar del proyecto)
    3. ../database/sistema_cv.db (si se ejecuta desde app/)
    4. Cualquier .db encontrado dentro del proyecto
    """
    # 1. Leer .env si existe
    for env_path in [".env", "../.env"]:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        ruta = url.replace("sqlite:///./", "").replace("sqlite:///", "")
                        if os.path.exists(ruta):
                            return ruta

    # 2. Rutas conocidas del proyecto
    candidatos = [
        "database/sistema_cv.db",
        "../database/sistema_cv.db",
        "sistema_cv.db",
        "sql_app.db",
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c

    # 3. Buscar cualquier .db en el árbol de directorios (hasta 3 niveles)
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ("venv", ".venv", "node_modules", "__pycache__")]
        depth = root.count(os.sep)
        if depth > 3:
            continue
        for f in files:
            if f.endswith(".db"):
                return os.path.join(root, f)

    return ""


DB_PATH = _resolver_ruta_db()

def migrar():
    if not DB_PATH or not os.path.exists(DB_PATH):
        print("[ERROR] No se encontró la base de datos.")
        print("Rutas buscadas: database/sistema_cv.db, .env → DATABASE_URL, y archivos *.db cercanos.")
        print("Solución: ejecutá el script desde la carpeta backend/ del proyecto.")
        sys.exit(1)
    
    print(f"[OK] BD encontrada en: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    print(f"  Abriendo: {os.path.abspath(DB_PATH)}")
    cur  = conn.cursor()

    # Verificar columnas existentes
    cur.execute("PRAGMA table_info(analisis)")
    cols = {row[1] for row in cur.fetchall()}

    agregadas = []

    if "alertas_json" not in cols:
        cur.execute("ALTER TABLE analisis ADD COLUMN alertas_json TEXT")
        agregadas.append("alertas_json")

    if "preguntas_json" not in cols:
        cur.execute("ALTER TABLE analisis ADD COLUMN preguntas_json TEXT")
        agregadas.append("preguntas_json")

    conn.commit()
    conn.close()

    if agregadas:
        print(f"[OK] Columnas agregadas: {', '.join(agregadas)}")
    else:
        print("[OK] Las columnas ya existían — nada que hacer.")

if __name__ == "__main__":
    migrar()
