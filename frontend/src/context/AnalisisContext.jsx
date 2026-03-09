/**
 * AnalisisContext — estado global del análisis.
 * Persiste en sessionStorage para sobrevivir navegación entre vistas.
 * NO comparte entre pestañas (cada pestaña es independiente — correcto).
 */
import { createContext, useContext, useState, useRef, useCallback, useEffect } from 'react'
import { cvsService } from '../services/procesoService'

const AnalisisContext = createContext(null)
const SS_KEY = 'analisis_activo'

function leerSS() {
  try {
    const s = sessionStorage.getItem(SS_KEY)
    return s ? JSON.parse(s) : null
  } catch { return null }
}

function guardarSS(data) {
  try {
    if (data) sessionStorage.setItem(SS_KEY, JSON.stringify(data))
    else sessionStorage.removeItem(SS_KEY)
  } catch {}
}

export function AnalisisProvider({ children }) {
  const [analisisActivo, _setAnalisis] = useState(() => leerSS())
  const pollRef    = useRef(null)
  const activoRef  = useRef(analisisActivo)

  // Wrapper que sincroniza con sessionStorage
  const setAnalisis = useCallback((updater) => {
    _setAnalisis(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      activoRef.current = next
      guardarSS(next)
      return next
    })
  }, [])

  // Al montar: si había un análisis en curso, reanudar polling
  useEffect(() => {
    const guardado = leerSS()
    if (guardado?.paso === 'analizando') {
      _poll(guardado.procesoId)
    }
  }, [])

  // Reanudar al volver a la pestaña (cambio de vista dentro del mismo tab)
  useEffect(() => {
    const onVisible = () => {
      if (!document.hidden && activoRef.current?.paso === 'analizando') {
        if (pollRef.current) clearTimeout(pollRef.current)
        _poll(activoRef.current.procesoId)
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [])

  const iniciarAnalisis = useCallback((procesoId, archivos) => {
    const estado = {
      procesoId,
      paso: 'analizando',
      progreso: {
        completado: 0, total: archivos.length, progreso_global: 0,
        log_actual: 'Preparando...', cancelado: false, tiempo_s: 0,
        items: archivos.map(f => ({ nombre: f.name, estado: 'pendiente' })),
      }
    }
    setAnalisis(estado)
    _poll(procesoId)
  }, [])

  const _poll = (id) => {
    let sinCambio       = 0
    let ultimoCompletado = -1
    let errorBackoff    = 2000  // Crece exponencialmente en fallos de red

    const check = async () => {
      // Verificar que sigue activo (podría haberse limpiado)
      const actual = activoRef.current
      if (!actual || actual.procesoId !== id || actual.paso !== 'analizando') return

      try {
        const { data } = await cvsService.estado(id)
        errorBackoff = 2000  // Resetear backoff al recuperar conexión
        const procesados = data.completado + data.error

        setAnalisis(prev => {
          if (!prev || prev.procesoId !== id) return prev

          // Actualizar items preservando el estado real de cada uno.
          // Se preserva el estado anterior si ya estaba completado/error.
          const items = prev.progreso.items.map((item, i) => {
            if (item.estado === 'completado' || item.estado === 'error') return item
            if (i < data.completado) return { ...item, estado: 'completado' }
            if (i < procesados)      return { ...item, estado: 'error' }
            if (data.procesando > 0 && i === procesados) return { ...item, estado: 'procesando' }
            return { ...item, estado: 'pendiente' }
          })

          return {
            ...prev,
            progreso: {
              ...prev.progreso,
              completado:      procesados,
              total:           data.total,
              progreso_global: data.progreso_global,
              log_actual:      data.log_actual || prev.progreso.log_actual,
              cancelado:       data.cancelado || false,
              tiempo_s:        data.tiempo_transcurrido_s || 0,
              items,
            }
          }
        })

        // Terminar polling si listo o cancelado
        const terminado = (data.listo === true && procesados >= data.total && data.total > 0)
                       || data.cancelado === true
        if (terminado) {
          setAnalisis(prev => prev ? { ...prev, paso: 'listo' } : prev)
          return
        }

        if (procesados === ultimoCompletado) {
          sinCambio++
          if (sinCambio >= 300) { // 10 min sin cambio → dar por terminado
            setAnalisis(prev => prev ? { ...prev, paso: 'listo' } : prev)
            return
          }
        } else {
          sinCambio = 0
          ultimoCompletado = procesados
        }

        pollRef.current = setTimeout(check, 2000)
      } catch {
        // Backoff exponencial en errores de red: 2s → 4s → 8s → 16s → 30s (máx)
        errorBackoff = Math.min(errorBackoff * 2, 30000)
        pollRef.current = setTimeout(check, errorBackoff)
      }
    }

    if (pollRef.current) clearTimeout(pollRef.current)
    check()
  }

  const limpiarAnalisis = useCallback(() => {
    if (pollRef.current) clearTimeout(pollRef.current)
    setAnalisis(null)
  }, [])

  return (
    <AnalisisContext.Provider value={{ analisisActivo, iniciarAnalisis, limpiarAnalisis }}>
      {children}
    </AnalisisContext.Provider>
  )
}

export function useAnalisis() {
  return useContext(AnalisisContext)
}
