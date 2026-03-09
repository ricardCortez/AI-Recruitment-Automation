# -*- coding: utf-8 -*-
"""
Endpoint de configuración del sistema: GPU/CPU, modelo, RAM.
La config se guarda en backend/config.json
"""

import json
import subprocess
import time
import psutil
from pathlib import Path
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.dependencies import require_admin, require_reclutador_or_admin
from app.models.user import User
from app.models.enums import Dispositivo
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"

DEFAULT_CONFIG = {
    "dispositivo":   "cpu",      # "cpu" | "gpu"
    "num_gpu":       0,          # 0=CPU, -1=todas las capas GPU, N=N capas GPU
    "num_threads":   4,          # Threads CPU
    "modelo":        "qwen2.5:14b",
    "max_tokens":    2500,
    "temperature":   0,
    "seed":          42,
}


def leer_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                saved = json.load(f)
            return {**DEFAULT_CONFIG, **saved}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def guardar_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    # Actualizar el modelo en settings en caliente
    settings.OLLAMA_MODEL = cfg.get("modelo", settings.OLLAMA_MODEL)


def detectar_gpu() -> dict:
    """Detecta GPU NVIDIA y memoria disponible."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            gpus = []
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpus.append({
                        "nombre":      parts[0],
                        "vram_total":  int(parts[1]),
                        "vram_libre":  int(parts[2]),
                        "uso_pct":     int(parts[3]),
                    })
            return {"disponible": True, "gpus": gpus}
    except Exception:
        pass
    return {"disponible": False, "gpus": []}


def detectar_ram() -> dict:
    """Detecta RAM del sistema."""
    try:
        mem = psutil.virtual_memory()
        return {
            "total_gb":     round(mem.total / 1024**3, 1),
            "disponible_gb": round(mem.available / 1024**3, 1),
            "uso_pct":       mem.percent,
        }
    except Exception:
        pass
    # Fallback sin psutil
    try:
        result = subprocess.run(
            ["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory", "/Value"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            total = free = 0
            for line in result.stdout.splitlines():
                if "TotalVisibleMemorySize" in line:
                    total = int(line.split("=")[1].strip()) // 1024
                if "FreePhysicalMemory" in line:
                    free  = int(line.split("=")[1].strip()) // 1024
            return {
                "total_gb":      round(total / 1024, 1),
                "disponible_gb": round(free  / 1024, 1),
                "uso_pct":       round((1 - free / max(total, 1)) * 100, 1),
            }
    except Exception:
        pass
    return {"total_gb": 0, "disponible_gb": 0, "uso_pct": 0}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def obtener_config(_: User = Depends(require_admin)):
    cfg = leer_config()
    gpu = detectar_gpu()
    ram = detectar_ram()

    # Requerimientos estimados por modelo
    reqs = {
        "llama3.1:8b":  {"ram_gb": 6,  "vram_gb": 6},
        "qwen2.5:7b":   {"ram_gb": 6,  "vram_gb": 6},
        "qwen2.5:14b":  {"ram_gb": 10, "vram_gb": 10},
        "qwen2.5:32b":  {"ram_gb": 20, "vram_gb": 20},
        "llama3.3:70b": {"ram_gb": 48, "vram_gb": 48},
    }
    req_actual = reqs.get(cfg.get("modelo", ""), {"ram_gb": 8, "vram_gb": 8})

    # Modelos instalados en Ollama
    modelos_instalados = []
    try:
        import ollama
        result = ollama.list()
        modelos_instalados = [m["name"] for m in result.get("models", [])]
    except Exception:
        pass

    return {
        "config":             cfg,
        "gpu":                gpu,
        "ram":                ram,
        "req_modelo":         req_actual,
        "modelos_instalados": modelos_instalados,
        "ram_suficiente":     ram["disponible_gb"] >= req_actual["ram_gb"] * 0.8,
        "vram_suficiente": (
            gpu["disponible"] and
            len(gpu["gpus"]) > 0 and
            gpu["gpus"][0].get("vram_libre", 0) >= req_actual["vram_gb"] * 1024 * 0.8
        ),
    }


class ConfigUpdate(BaseModel):
    dispositivo: Optional[str] = None
    num_gpu:     Optional[int] = None
    num_threads: Optional[int] = None
    modelo:      Optional[str] = None
    max_tokens:  Optional[int] = None


@router.post("/")
def actualizar_config(data: ConfigUpdate, _: User = Depends(require_admin)):
    cfg = leer_config()
    update = data.model_dump(exclude_none=True)
    cfg.update(update)

    # Sincronizar num_gpu según dispositivo
    if "dispositivo" in update:
        cfg["num_gpu"] = -1 if update["dispositivo"] == Dispositivo.GPU else 0

    guardar_config(cfg)

    # Aplicar cambios en caliente a ia_service
    from app.core.config import settings
    if "modelo" in update:
        settings.OLLAMA_MODEL = update["modelo"]

    return {"mensaje": "Configuración guardada.", "config": cfg}


@router.get("/diagnostico-gpu")
async def diagnostico_gpu(_: User = Depends(require_admin)):
    """
    Diagnóstico completo de GPU para Ollama.
    Detecta la causa raíz de por qué Ollama no usa GPU.
    """
    cfg   = leer_config()
    modelo = cfg.get("modelo", "qwen2.5:14b")
    checks = []

    # ── CHECK 1: nvidia-smi disponible ──────────────────────────────────────
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,compute_cap",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            checks.append({
                "id": "nvidia_smi", "ok": True,
                "label": "NVIDIA GPU detectada",
                "detalle": parts[0] if parts else "GPU OK",
            })
            gpu_nombre = parts[0] if parts else "GPU NVIDIA"
        else:
            checks.append({"id": "nvidia_smi", "ok": False,
                "label": "NVIDIA GPU no detectada",
                "detalle": "nvidia-smi no encontrado o sin GPU NVIDIA"})
            return {"checks": checks, "gpu_activa": False,
                    "causa_raiz": "sin_gpu", "tiempo_respuesta_s": 0}
    except Exception as e:
        checks.append({"id": "nvidia_smi", "ok": False,
            "label": "nvidia-smi no ejecutable", "detalle": str(e)})
        return {"checks": checks, "gpu_activa": False, "causa_raiz": "sin_nvidia_smi"}

    # ── CHECK 2: CUDA version ────────────────────────────────────────────────
    try:
        r2 = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
        cuda_ok = "CUDA Version" in r2.stdout
        cuda_ver = ""
        for line in r2.stdout.splitlines():
            if "CUDA Version" in line:
                cuda_ver = line.strip()
                break
        checks.append({
            "id": "cuda", "ok": cuda_ok,
            "label": "CUDA disponible" if cuda_ok else "CUDA no encontrado",
            "detalle": cuda_ver or "No se encontró versión CUDA en nvidia-smi",
        })
    except Exception as e:
        checks.append({"id": "cuda", "ok": False, "label": "Error verificando CUDA", "detalle": str(e)})

    # ── CHECK 3: Ollama corriendo ────────────────────────────────────────────
    ollama_pid = None
    try:
        import ollama as _ollama
        _ollama.list()
        checks.append({"id": "ollama_running", "ok": True,
            "label": "Ollama está corriendo", "detalle": "API responde en localhost:11434"})
        # Buscar PID de Ollama
        for proc in psutil.process_iter(["pid", "name"]):
            if "ollama" in proc.info["name"].lower():
                ollama_pid = proc.info["pid"]
                break
    except Exception as e:
        checks.append({"id": "ollama_running", "ok": False,
            "label": "Ollama no está corriendo", "detalle": str(e)})
        return {"checks": checks, "gpu_activa": False, "causa_raiz": "ollama_no_corre"}

    # ── CHECK 4: Modelo instalado ────────────────────────────────────────────
    try:
        import ollama as _ollama
        modelos = [m["name"] for m in _ollama.list().get("models", [])]
        base = modelo.split(":")[0]
        modelo_ok = any(base in n for n in modelos)
        checks.append({
            "id": "modelo", "ok": modelo_ok,
            "label": "Modelo " + modelo + (" instalado" if modelo_ok else " NO instalado"),
            "detalle": ("Modelos disponibles: " + ", ".join(modelos[:3])) if modelos else "Sin modelos",
        })
        if not modelo_ok:
            return {"checks": checks, "gpu_activa": False, "causa_raiz": "modelo_no_instalado",
                    "comando_fix": "ollama pull " + modelo}
    except Exception as e:
        checks.append({"id": "modelo", "ok": False, "label": "Error listando modelos", "detalle": str(e)})

    # ── CHECK 5: Hacer inferencia con num_gpu=999 ────────────────────────────
    elapsed = 0
    try:
        import ollama as _ollama
        start = time.time()
        _ollama.chat(
            model    = modelo,
            messages = [{"role": "user", "content": "1+1="}],
            options  = {"num_predict": 3, "num_gpu": 999, "temperature": 0},
        )
        elapsed = round(time.time() - start, 2)
        checks.append({"id": "inferencia", "ok": True,
            "label": "Inferencia completada en " + str(elapsed) + "s",
            "detalle": "GPU rápida < 5s | CPU lenta > 20s con qwen2.5:14b"})
    except Exception as e:
        checks.append({"id": "inferencia", "ok": False, "label": "Error en inferencia", "detalle": str(e)})
        return {"checks": checks, "gpu_activa": False, "causa_raiz": "error_inferencia"}

    # ── CHECK 6: Verificar VRAM de ollama_llama_server (la prueba real) ──────
    gpu_activa    = False
    ollama_vram   = 0
    proc_gpu_name = ""
    try:
        r3 = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if r3.returncode == 0 and r3.stdout.strip():
            for linea in r3.stdout.strip().splitlines():
                partes = [p.strip() for p in linea.split(",")]
                if len(partes) >= 3:
                    try:
                        pid_p  = int(partes[0])
                        name_p = partes[1].lower()
                        vram_p = int(partes[2])
                        if any(n in name_p for n in ["ollama", "llama"]):
                            gpu_activa    = True
                            ollama_vram   = vram_p
                            proc_gpu_name = partes[1]
                            break
                    except Exception:
                        pass

        checks.append({
            "id": "vram_asignada", "ok": gpu_activa,
            "label": "VRAM asignada a Ollama: " + str(ollama_vram) + " MB" if gpu_activa
                     else "Ollama NO tiene VRAM asignada (corre en CPU)",
            "detalle": "Proceso GPU: " + proc_gpu_name if gpu_activa
                       else "nvidia-smi --query-compute-apps no muestra proceso de Ollama con VRAM",
        })
    except Exception as e:
        checks.append({"id": "vram_asignada", "ok": False, "label": "Error verificando VRAM", "detalle": str(e)})

    # ── Causa raíz y solución ────────────────────────────────────────────────
    causa_raiz = "ok" if gpu_activa else "ollama_sin_cuda"
    velocidad  = "gpu" if elapsed < 8 else "cpu"

    return {
        "checks":             checks,
        "gpu_activa":         gpu_activa,
        "ollama_vram_mb":     ollama_vram,
        "tiempo_respuesta_s": elapsed,
        "velocidad_detectada": velocidad,
        "causa_raiz":         causa_raiz,
        "mensaje": (
            "GPU activa - Ollama usa " + str(ollama_vram) + " MB VRAM (" + str(elapsed) + "s)"
            if gpu_activa else
            "Ollama corre en CPU (" + str(elapsed) + "s) - sin VRAM asignada en nvidia-smi"
        ),
        "pasos_solucion": None if gpu_activa else [
            "Cerrá Ollama completamente (taskkill /IM ollama.exe /F en cmd)",
            "Descargá la última versión de Ollama desde https://ollama.com (ya incluye CUDA)",
            "Instalá sobre la versión existente (no necesitás desinstalar primero)",
            "Usá el iniciar_gpu.bat que setea OLLAMA_NUM_GPU=999 antes de arrancar",
            "Verificá con: nvidia-smi dmon -s u (debe subir la VRAM al cargar " + modelo + ")",
        ]
    }


@router.get("/recursos")
def estado_recursos(_: User = Depends(require_reclutador_or_admin)):
    """
    Monitor en tiempo real: CPU, RAM, GPU, y si Ollama usa GPU.
    Se llama cada 3s desde el frontend durante el analisis.
    """
    from app.utils.hardware import get_cpu_pct, get_ram_pct, get_ram_disponible_gb, get_gpu_info
    gpu  = get_gpu_info()
    return {
        "cpu_pct":           get_cpu_pct(),
        "ram_pct":           get_ram_pct(),
        "ram_disponible_gb": round(get_ram_disponible_gb(), 1),
        "gpu":               gpu,
    }
