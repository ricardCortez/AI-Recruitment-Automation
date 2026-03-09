# -*- coding: utf-8 -*-
"""
Deteccion de hardware — GPU, RAM, CPU.
La deteccion de GPU es estricta: solo marca "ollama_en_gpu=True"
si el proceso de Ollama tiene VRAM asignada en nvidia-smi.
"""
import os
import subprocess
import psutil


def get_ram_gb() -> float:
    return psutil.virtual_memory().total / (1024 ** 3)


def get_ram_disponible_gb() -> float:
    return psutil.virtual_memory().available / (1024 ** 3)


def get_cpu_pct() -> float:
    return psutil.cpu_percent(interval=0.3)


def get_ram_pct() -> float:
    return psutil.virtual_memory().percent


def get_gpu_info() -> dict:
    """
    Retorna uso real de GPU.
    ollama_en_gpu=True SOLO si nvidia-smi confirma que un proceso
    relacionado a Ollama tiene VRAM asignada.
    No usa fallbacks que den falsos positivos.
    """
    base = {
        "disponible":     False,
        "gpu_pct":        0,
        "vram_usada_mb":  0,
        "vram_total_mb":  0,
        "vram_pct":       0,
        "ollama_en_gpu":  False,
        "ollama_vram_mb": 0,
        "nombre":         "No detectada",
        "mensaje":        "",
    }

    # 1. Leer uso general del GPU
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        if r.returncode != 0:
            return base

        partes = [p.strip() for p in r.stdout.strip().split(",")]
        if len(partes) < 4:
            return base

        nombre    = partes[0]
        gpu_pct   = int(partes[1])
        vram_used = int(partes[2])
        vram_tot  = int(partes[3])

    except Exception:
        return base

    # 2. Leer procesos con VRAM asignada (compute apps)
    # Esto es lo que importa: si Ollama no aparece aqui, NO usa GPU
    ollama_en_gpu  = False
    ollama_vram_mb = 0
    detalle        = ""

    try:
        r2 = subprocess.run(
            ["nvidia-smi",
             "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )

        if r2.returncode == 0:
            lineas = [l.strip() for l in r2.stdout.strip().split("\n") if l.strip()]

            if not lineas:
                # Ningún proceso usando GPU para cómputo (solo display/render)
                detalle = "Ningún proceso usa GPU para cómputo"
            else:
                # Nombres conocidos de Ollama y llama.cpp en Windows
                OLLAMA_PROCS = {
                    "ollama", "ollama.exe",
                    "ollama_llama_server", "ollama_llama_server.exe",
                    "llama_server", "llama_server.exe",
                    "llama-server", "llama-server.exe",
                }

                for linea in lineas:
                    partes2 = [p.strip() for p in linea.split(",")]
                    if len(partes2) < 3:
                        continue
                    try:
                        pid        = int(partes2[0])
                        proc_name  = partes2[1].lower().strip()
                        vmem       = int(partes2[2])

                        # Verificar por nombre reportado por nvidia-smi
                        es_ollama = any(n in proc_name for n in ["ollama", "llama"])

                        # Buscar en psutil si nvidia-smi no da nombre completo
                        if not es_ollama:
                            try:
                                p         = psutil.Process(pid)
                                full_name = p.name().lower()
                                cmdline   = " ".join(p.cmdline()).lower()
                                es_ollama = (
                                    any(n in full_name for n in ["ollama", "llama"]) or
                                    "ollama" in cmdline
                                )
                            except Exception:
                                pass

                        if es_ollama:
                            ollama_en_gpu  = True
                            ollama_vram_mb = vmem
                            detalle = "Ollama usando GPU ({} MB VRAM)".format(vmem)
                            break
                    except Exception:
                        continue

    except Exception as e:
        detalle = "Error al consultar procesos GPU: {}".format(e)

    # Mensaje para el usuario
    if ollama_en_gpu:
        mensaje = ""
    elif vram_used > 100:
        mensaje = (
            "GPU en uso por otros procesos ({} MB), pero Ollama corre en CPU. "
            "Activá GPU en Configuración IA y reiniciá Ollama.".format(vram_used)
        )
    else:
        mensaje = "Ollama corre en CPU. Activá GPU en Configuración IA para acelerar el análisis."

    return {
        "disponible":     True,
        "gpu_pct":        gpu_pct,
        "vram_usada_mb":  vram_used,
        "vram_total_mb":  vram_tot,
        "vram_pct":       round(vram_used / vram_tot * 100, 1) if vram_tot else 0,
        "ollama_en_gpu":  ollama_en_gpu,
        "ollama_vram_mb": ollama_vram_mb,
        "nombre":         nombre,
        "mensaje":        mensaje,
        "detalle":        detalle,
    }


def get_ollama_params_optimos() -> dict:
    ram_total = get_ram_gb()
    cores     = os.cpu_count() or 4
    threads   = max(cores - 2, 2)

    if ram_total >= 28:
        ctx, max_tok = 4096, 1200
    elif ram_total >= 14:
        ctx, max_tok = 3072, 1000
    elif ram_total >= 6:
        ctx, max_tok = 2048, 900
    else:
        ctx, max_tok = 1536, 700

    return {
        "ram_total_gb": round(ram_total, 1),
        "cores":        cores,
        "threads":      threads,
        "ctx":          ctx,
        "max_tokens":   max_tok,
    }
