/**
 * Instancia centralizada de Axios.
 * - Agrega automáticamente el Bearer token en cada request.
 * - Si el servidor devuelve 401, limpia la sesión y redirige al login.
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000, // 60s — el análisis IA puede tardar
})

// ── Request: agregar token ────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response: manejar errores globales ────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
