#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_system.py — Lanzador del Sistema CV

Uso:
  python run_system.py          # modo CPU (por defecto)
  python run_system.py --gpu    # modo GPU (activa CUDA en Ollama)
  python run_system.py --stop   # detiene todos los servicios

Distribuible como ejecutable:
  pip install pyinstaller
  pyinstaller --onefile --name SistemaCV run_system.py
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────
BACKEND_URL  = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
OLLAMA_URL   = "http://localhost:11434"

BASE_DIR     = Path(__file__).resolve().parent
BACKEND_DIR  = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
VENV_PYTHON  = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
VENV_ACTIVATE = BACKEND_DIR / "venv" / "Scripts" / "activate.bat"

# Procesos iniciados por este launcher (para poder detenerlos)
_procesos: list[subprocess.Popen] = []


# ── Utilidades ────────────────────────────────────────────────────────────────

def _titulo(texto: str):
    ancho = 60
    print()
    print("  " + "=" * ancho)
    print(f"  {texto}")
    print("  " + "=" * ancho)


def _ok(msg: str):
    print(f"  [OK] {msg}")


def _info(msg: str):
    print(f"  [+]  {msg}")


def _warn(msg: str):
    print(f"  [!]  {msg}")


def _error(msg: str):
    print(f"  [ERROR] {msg}")


def _esperar_servicio(url: str, nombre: str, intentos: int = 15, intervalo: float = 2.0) -> bool:
    """Polling al health endpoint hasta que responde o se agota el tiempo."""
    import urllib.request
    import urllib.error
    for i in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return True
        except Exception:
            pass
        print(f"  ... esperando {nombre} ({i}/{intentos})", end="\r")
        time.sleep(intervalo)
    print()
    return False


def _servicio_activo(url: str) -> bool:
    """Devuelve True si el servicio ya está respondiendo."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status < 500
    except Exception:
        return False


# ── Verificaciones previas ────────────────────────────────────────────────────

def verificar_python():
    if not VENV_PYTHON.exists():
        _error("Entorno virtual no encontrado.")
        print()
        print("  Solución:")
        print(f"    cd {BACKEND_DIR}")
        print("    python -m venv venv")
        print("    venv\\Scripts\\activate")
        print("    pip install -r requirements.txt")
        sys.exit(1)
    _ok(f"Entorno virtual: {VENV_PYTHON}")


def verificar_env():
    env_path = BACKEND_DIR / ".env"
    ejemplo  = BACKEND_DIR / ".env.example"
    if not env_path.exists():
        if ejemplo.exists():
            shutil.copy(ejemplo, env_path)
            _warn(".env creado desde .env.example — verifica que SECRET_KEY esté configurada.")
        else:
            _error(f"No se encontró {env_path}")
            print("  Crea el archivo con al menos:  SECRET_KEY=tu_clave_aqui")
            sys.exit(1)
    _ok(".env encontrado.")


def verificar_node():
    if not shutil.which("node"):
        _error("Node.js no está instalado o no está en el PATH.")
        print("  Descargalo desde https://nodejs.org")
        sys.exit(1)
    _ok(f"Node.js: {shutil.which('node')}")


def verificar_ollama() -> str:
    """Devuelve la ruta al ejecutable de Ollama o sale si no se encuentra."""
    rutas_candidatas = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
        r"C:\Program Files\Ollama\ollama.exe",
    ]
    for ruta in rutas_candidatas:
        if Path(ruta).exists():
            _ok(f"Ollama: {ruta}")
            return ruta
    # Intentar via PATH
    en_path = shutil.which("ollama")
    if en_path:
        _ok(f"Ollama en PATH: {en_path}")
        return en_path
    _error("Ollama no encontrado.")
    print("  Descargalo desde https://ollama.com")
    sys.exit(1)


def instalar_frontend_deps():
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        _info("Instalando dependencias del frontend (primera vez)...")
        subprocess.run(
            ["npm", "install", "--silent"],
            cwd=FRONTEND_DIR,
            shell=True,
            check=True,
        )
        _ok("Dependencias del frontend instaladas.")


# ── Inicio de servicios ───────────────────────────────────────────────────────

def iniciar_ollama(ollama_exe: str, gpu: bool):
    if _servicio_activo(OLLAMA_URL):
        _ok("Ollama ya está corriendo.")
        return

    env = os.environ.copy()
    env["OLLAMA_HOST"] = "127.0.0.1:11434"
    if gpu:
        env.update({
            "OLLAMA_NUM_GPU":       "999",
            "OLLAMA_GPU_LAYERS":    "999",
            "CUDA_VISIBLE_DEVICES": "0",
            "OLLAMA_FLASH_ATTENTION": "1",
        })
        _info(f"Iniciando Ollama con GPU...")
    else:
        _info("Iniciando Ollama (CPU)...")

    p = subprocess.Popen(
        [ollama_exe, "serve"],
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    _procesos.append(p)

    if _esperar_servicio(OLLAMA_URL, "Ollama", intentos=12, intervalo=2):
        _ok(f"Ollama listo en {OLLAMA_URL}")
    else:
        _warn("Ollama no respondió a tiempo — continuando de todas formas.")


def iniciar_backend():
    _info("Iniciando Backend...")
    cmd = (
        f'"{VENV_ACTIVATE}" && '
        f'uvicorn main:app --host 127.0.0.1 --port 8000'
    )
    p = subprocess.Popen(
        ["cmd", "/k", cmd],
        cwd=BACKEND_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    _procesos.append(p)

    if _esperar_servicio(f"{BACKEND_URL}/health", "Backend", intentos=15, intervalo=2):
        _ok(f"Backend listo en {BACKEND_URL}")
    else:
        _warn("Backend no respondió a tiempo — continuando de todas formas.")


def iniciar_frontend():
    _info("Iniciando Frontend...")
    p = subprocess.Popen(
        ["cmd", "/k", "npm run dev"],
        cwd=FRONTEND_DIR,
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    _procesos.append(p)

    if _esperar_servicio(FRONTEND_URL, "Frontend", intentos=10, intervalo=2):
        _ok(f"Frontend listo en {FRONTEND_URL}")
    else:
        _warn("Frontend no respondió a tiempo — abriendo navegador igual.")


# ── Detener servicios ─────────────────────────────────────────────────────────

def detener_servicios():
    _titulo("Deteniendo Sistema CV")

    # Primero intentar detener los procesos lanzados por este script
    for p in _procesos:
        try:
            p.terminate()
        except Exception:
            pass

    # Luego matar por nombre de proceso (por si fueron lanzados por los .bat)
    for nombre in ["uvicorn.exe"]:
        subprocess.run(
            ["taskkill", "/FI", f"IMAGENAME eq {nombre}", "/F"],
            capture_output=True,
        )

    for titulo in ["SistemaCV-Frontend", "SistemaCV-Backend", "SistemaCV-Ollama"]:
        subprocess.run(
            ["taskkill", "/FI", f"WINDOWTITLE eq {titulo}", "/F"],
            capture_output=True,
        )

    # Liberar puerto 8000 si quedó ocupado
    try:
        result = subprocess.run(
            ["netstat", "-aon"],
            capture_output=True, text=True,
        )
        for line in result.stdout.splitlines():
            if ":8000 " in line:
                partes = line.split()
                pid = partes[-1]
                subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
    except Exception:
        pass

    _ok("Sistema detenido.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Lanzador del Sistema CV — IA de Reclutamiento Local",
    )
    parser.add_argument(
        "--gpu", action="store_true",
        help="Iniciar Ollama con soporte GPU (NVIDIA CUDA)",
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="Detener todos los servicios",
    )
    args = parser.parse_args()

    if args.stop:
        detener_servicios()
        return

    modo = "GPU (CUDA)" if args.gpu else "CPU"
    _titulo(f"SISTEMA CV  —  IA de Reclutamiento Local  [{modo}]")

    # ── Verificaciones ────────────────────────────────────────────────────────
    _info("Verificando dependencias...")
    verificar_python()
    verificar_env()
    verificar_node()
    ollama_exe = verificar_ollama()
    instalar_frontend_deps()

    # ── Inicio de servicios ───────────────────────────────────────────────────
    print()
    _info("[1/3] Ollama")
    iniciar_ollama(ollama_exe, gpu=args.gpu)

    print()
    _info("[2/3] Backend")
    iniciar_backend()

    print()
    _info("[3/3] Frontend")
    iniciar_frontend()

    # ── Abrir navegador ───────────────────────────────────────────────────────
    time.sleep(1)
    _info("Abriendo navegador...")
    webbrowser.open(FRONTEND_URL)

    # ── Resumen ───────────────────────────────────────────────────────────────
    print()
    print("  " + "=" * 60)
    print(f"  Sistema iniciado correctamente  [{modo}]")
    print()
    print(f"  Frontend  ->  {FRONTEND_URL}")
    print(f"  Backend   ->  {BACKEND_URL}")
    print(f"  Ollama    ->  {OLLAMA_URL}")
    print()
    print("  Para detener:  python run_system.py --stop")
    print("                 o cierra las ventanas de cada servicio")
    print("  " + "=" * 60)
    print()

    # Mantener el script vivo para poder hacer Ctrl+C
    try:
        print("  Presiona Ctrl+C para detener todos los servicios...")
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print()
        detener_servicios()


if __name__ == "__main__":
    main()
