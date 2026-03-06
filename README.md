# Sistema CV — Análisis Automatizado de CVs con IA

Sistema web local para el área de RR.HH que automatiza el análisis de CVs usando inteligencia artificial.

## Inicio rápido

1. Copiá `.env.example` → `backend/.env` y editá la `SECRET_KEY`
2. Doble clic en **`iniciar.bat`**
3. El navegador se abre automáticamente en `http://localhost:5173`

**Usuario por defecto:** `admin` / `Admin@2025!`

## Requisitos

- Python 3.11+
- Node.js 18+
- Ollama instalado con el modelo `llama3.1:8b` (Versión 2)

## Estructura

```
sistema-cv/
├── backend/    # Python + FastAPI
├── frontend/   # React + Vite + Tailwind
└── docs/       # Manuales
```

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Tailwind CSS |
| Backend | Python 3.11 + FastAPI |
| IA Local | Ollama + Llama 3.1 8B |
| Base de datos | SQLite |
| Auth | JWT + bcrypt + TOTP (2FA) |
