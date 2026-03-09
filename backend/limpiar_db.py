"""
limpiar_db.py — Limpia procesos de prueba del sistema CV RRHH
Uso:
  python limpiar_db.py              → lista todo, pregunta que borrar
  python limpiar_db.py --todo       → borra TODO (procesos + CVs + analisis)
  python limpiar_db.py --proceso 5  → borra solo el proceso con ID 5
  python limpiar_db.py --keepfiles  → borra BD pero mantiene los PDFs en disco
"""

import sys, os, shutil, sqlite3
from pathlib import Path
from datetime import datetime

# ── Ruta a la BD (ajustar si es diferente) ──────────────────────────────────
DB_PATH  = Path(__file__).parent / "database" / "sistema_cv.db"
CVS_DIR  = Path(__file__).parent / "storage" / "cvs"

def conectar():
    if not DB_PATH.exists():
        print(f"ERROR: No se encontro la BD en {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def listar_procesos(cur):
    cur.execute("""
        SELECT p.id, p.nombre_puesto, p.creado_en,
               COUNT(DISTINCT c.id) as cvs,
               COUNT(DISTINCT a.id) as analizados
        FROM procesos p
        LEFT JOIN candidatos c ON c.proceso_id = p.id
        LEFT JOIN analisis   a ON a.candidato_id = c.id AND a.estado = 'completado'
        GROUP BY p.id
        ORDER BY p.id DESC
    """)
    return cur.fetchall()

def borrar_proceso(con, cur, proceso_id: int, keepfiles: bool):
    """Borra un proceso y todos sus candidatos/analisis en cascada."""
    # Obtener archivos PDF
    cur.execute("SELECT archivo_pdf FROM candidatos WHERE proceso_id = ?", (proceso_id,))
    pdfs = [r[0] for r in cur.fetchall()]

    # Borrar en orden por FK
    cur.execute("DELETE FROM analisis WHERE candidato_id IN (SELECT id FROM candidatos WHERE proceso_id = ?)", (proceso_id,))
    cur.execute("DELETE FROM candidatos WHERE proceso_id = ?", (proceso_id,))
    cur.execute("DELETE FROM procesos WHERE id = ?", (proceso_id,))
    con.commit()

    # Borrar PDFs del disco
    if not keepfiles:
        borrados = 0
        for pdf in pdfs:
            try:
                p = Path(pdf)
                if p.exists():
                    p.unlink()
                    borrados += 1
            except Exception as e:
                print(f"  Aviso: no se pudo borrar {pdf}: {e}")
        # Borrar carpeta del proceso si quedo vacia
        carpeta = CVS_DIR / str(proceso_id)
        if carpeta.exists() and not any(carpeta.iterdir()):
            carpeta.rmdir()
        return len(pdfs), borrados
    return len(pdfs), 0

def vacuum(con):
    con.execute("VACUUM")
    con.commit()

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    keepfiles = "--keepfiles" in args

    con = conectar()
    cur = con.cursor()

    procesos = listar_procesos(cur)

    print("\n" + "="*65)
    print("  SISTEMA CV RRHH — Limpieza de base de datos")
    print("="*65)

    if not procesos:
        print("  No hay procesos en la BD.")
        con.close()
        return

    print(f"\n  {'ID':>4}  {'Puesto':<35}  {'CVs':>4}  {'Anal':>4}  {'Creado'}")
    print("  " + "-"*61)
    for pid, nombre, creado, cvs, anal in procesos:
        fecha = creado[:10] if creado else "?"
        print(f"  {pid:>4}  {nombre[:35]:<35}  {cvs:>4}  {anal:>4}  {fecha}")

    total_procesos = len(procesos)
    total_cvs = sum(r[3] for r in procesos)
    print(f"\n  Total: {total_procesos} proceso(s), {total_cvs} CV(s)\n")

    # Modo --todo
    if "--todo" in args:
        resp = input("  Borrar TODO? Esto es irreversible. Escribi CONFIRMAR: ").strip()
        if resp != "CONFIRMAR":
            print("  Cancelado.")
            con.close()
            return
        eliminados = 0
        for pid, nombre, *_ in procesos:
            n, d = borrar_proceso(con, cur, pid, keepfiles)
            print(f"  Proceso {pid} '{nombre[:30]}' — {n} CVs eliminados")
            eliminados += n
        vacuum(con)
        print(f"\n  Listo. {total_procesos} procesos y {eliminados} CVs borrados.")
        con.close()
        return

    # Modo --proceso ID
    if "--proceso" in args:
        try:
            idx = args.index("--proceso")
            pid = int(args[idx + 1])
        except (ValueError, IndexError):
            print("  ERROR: usa --proceso <ID>")
            con.close()
            return
        match = next((r for r in procesos if r[0] == pid), None)
        if not match:
            print(f"  ERROR: proceso {pid} no encontrado.")
            con.close()
            return
        resp = input(f"  Borrar proceso {pid} '{match[1]}' con {match[3]} CVs? (s/N): ").strip().lower()
        if resp != "s":
            print("  Cancelado.")
            con.close()
            return
        n, d = borrar_proceso(con, cur, pid, keepfiles)
        vacuum(con)
        print(f"  Proceso {pid} eliminado. {n} CVs en BD, {d} PDFs borrados del disco.")
        con.close()
        return

    # Modo interactivo — seleccionar cuales borrar
    print("  Opciones:")
    print("    python limpiar_db.py --todo              Borrar todo")
    print("    python limpiar_db.py --proceso <ID>      Borrar un proceso")
    print("    python limpiar_db.py --keepfiles         Mantener PDFs en disco")
    print()
    entrada = input("  Ingresa IDs a borrar separados por coma (o Enter para salir): ").strip()
    if not entrada:
        con.close()
        return

    ids = [int(x.strip()) for x in entrada.split(",") if x.strip().isdigit()]
    if not ids:
        print("  Sin IDs validos.")
        con.close()
        return

    seleccionados = [r for r in procesos if r[0] in ids]
    if not seleccionados:
        print("  No se encontraron los procesos indicados.")
        con.close()
        return

    print(f"\n  Se borrarán {len(seleccionados)} proceso(s):")
    for pid, nombre, _, cvs, *_ in seleccionados:
        print(f"    [{pid}] {nombre} — {cvs} CVs")

    resp = input("\n  Confirmar? (s/N): ").strip().lower()
    if resp != "s":
        print("  Cancelado.")
        con.close()
        return

    for pid, nombre, *_ in seleccionados:
        n, d = borrar_proceso(con, cur, pid, keepfiles)
        print(f"  Proceso {pid} '{nombre[:30]}' — {n} CVs eliminados")

    vacuum(con)
    print(f"\n  Listo. BD compactada.")
    con.close()

if __name__ == "__main__":
    main()
