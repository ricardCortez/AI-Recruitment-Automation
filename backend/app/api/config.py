"""
Endpoint de configuración del sistema: GPU/CPU, modelo, RAM.
La config se guarda en backend/config.json
"""

import json
import subprocess
from pathlib import Path
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.dependencies import require_admin, require_reclutador_or_admin, get_current_user
from app.models.user import User
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
    from app.core.config import settings
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


def detectar_cpu() -> dict:
    """Detecta nucleos fisicos y logicos del CPU."""
    import os
    total_logicos = os.cpu_count() or 4
    fisicos = total_logicos
    try:
        import psutil
        fisicos = psutil.cpu_count(logical=False) or total_logicos
    except ImportError:
        try:
            import subprocess, re
            r = subprocess.run(
                ["wmic", "cpu", "get", "NumberOfCores,NumberOfLogicalProcessors", "/Value"],
                capture_output=True, text=True, timeout=5
            )
            for line in r.stdout.splitlines():
                if "NumberOfCores=" in line:
                    fisicos = int(line.split("=")[1].strip())
                if "NumberOfLogicalProcessors=" in line:
                    total_logicos = int(line.split("=")[1].strip())
        except Exception:
            pass
    # Threads optimos: dejar 1-2 hilos libres para el SO
    optimo = max(total_logicos - 2, 2)
    return {
        "logicos":  total_logicos,
        "fisicos":  fisicos,
        "optimo":   optimo,
    }


def detectar_ram() -> dict:
    """Detecta RAM del sistema."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb":     round(mem.total / 1024**3, 1),
            "disponible_gb": round(mem.available / 1024**3, 1),
            "uso_pct":       mem.percent,
        }
    except ImportError:
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
def obtener_config(current_user: User = Depends(get_current_user)):
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

    cpu = detectar_cpu()

    # Si num_threads en config.json es el default (4) o menor al optimo real,
    # actualizar automaticamente al optimo detectado
    if cfg.get("num_threads", 4) < cpu["optimo"]:
        cfg["num_threads"] = cpu["optimo"]
        guardar_config(cfg)
        logger.info("CPU detectado: %s hilos logicos → num_threads actualizado a %s",
                    cpu["logicos"], cpu["optimo"])

    return {
        "config":             cfg,
        "gpu":                gpu,
        "ram":                ram,
        "cpu":                cpu,
        "req_modelo":         req_actual,
        "modelos_instalados": modelos_instalados,
        "ram_suficiente":     ram["disponible_gb"] >= req_actual["ram_gb"] * 0.8,
        "vram_suficiente": (
            gpu["disponible"] and
            len(gpu["gpus"]) > 0 and
            gpu["gpus"][0]["vram_libre"] >= req_actual["vram_gb"] * 1024 * 0.8
        ),
        "user_rol": current_user.rol,
    }


class ConfigUpdate(BaseModel):
    dispositivo: Optional[str] = None
    num_gpu:     Optional[int] = None
    num_threads: Optional[int] = None
    modelo:      Optional[str] = None
    max_tokens:  Optional[int] = None


@router.post("/")
def actualizar_config(data: ConfigUpdate, current_user: User = Depends(get_current_user)):
    cfg = leer_config()
    update = data.model_dump(exclude_none=True)

    # Solo superadmin puede cambiar configuración avanzada
    es_superadmin = current_user.rol == "admin"
    CAMPOS_AVANZADOS = {"num_threads", "max_tokens", "temperature", "seed", "num_gpu"}
    if not es_superadmin:
        # Filtrar solo modelo y dispositivo
        update = {k: v for k, v in update.items() if k not in CAMPOS_AVANZADOS}

    cfg.update(update)

    # Sincronizar num_gpu según dispositivo
    if "dispositivo" in update:
        cfg["num_gpu"] = -1 if update["dispositivo"] == "gpu" else 0

    guardar_config(cfg)

    # Aplicar cambios en caliente a ia_service
    from app.core.config import settings
    if "modelo" in update:
        settings.OLLAMA_MODEL = update["modelo"]

    return {"mensaje": "Configuración guardada.", "config": cfg}


@router.get("/diagnostico-gpu")
async def diagnostico_gpu(_: User = Depends(require_admin)):
    """
    Verifica si Ollama está usando GPU haciendo una llamada de prueba
    y leyendo nvidia-smi antes y después.
    """
    import ollama, time

    cfg   = leer_config()
    antes = detectar_gpu()
    uso_antes = antes["gpus"][0]["uso_pct"] if antes["disponible"] and antes["gpus"] else 0

    try:
        # Llamada mínima para forzar carga del modelo en GPU
        start = time.time()
        ollama.chat(
            model    = cfg.get("modelo", "qwen2.5:14b"),
            messages = [{"role": "user", "content": "Di 'ok'"}],
            options  = {
                "num_predict": 5,
                "num_gpu":     999 if cfg.get("dispositivo") == "gpu" else 0,
                "temperature": 0,
            },
        )
        elapsed = round(time.time() - start, 2)
    except Exception as e:
        return {"error": str(e), "ollama_disponible": False}

    despues  = detectar_gpu()
    uso_despues = despues["gpus"][0]["uso_pct"] if despues["disponible"] and despues["gpus"] else 0

    gpu_activa = uso_despues > uso_antes + 5  # Si el uso subió, está usando GPU

    return {
        "dispositivo_config": cfg.get("dispositivo"),
        "num_gpu_enviado":    999 if cfg.get("dispositivo") == "gpu" else 0,
        "tiempo_respuesta_s": elapsed,
        "gpu_uso_antes_pct":  uso_antes,
        "gpu_uso_despues_pct": uso_despues,
        "gpu_activa":         gpu_activa,
        "mensaje": (
            "✅ GPU en uso — el uso de GPU subió durante la inferencia."
            if gpu_activa else
            "⚠️ No se detectó actividad en GPU. Verificá que Ollama tenga soporte CUDA."
        ),
        "solucion": (
            None if gpu_activa else
            "1. Abrí https://ollama.com/download y reinstalá Ollama (versión con CUDA). "
            "2. Ejecutá en terminal: ollama run " + cfg.get("modelo", "qwen2.5:14b") + " (primera vez carga en GPU). "
            "3. Verificá con nvidia-smi que el proceso 'ollama' aparece usando VRAM."
        )
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
