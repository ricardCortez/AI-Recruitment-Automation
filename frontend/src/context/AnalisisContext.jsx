/**
 * AnalisisContext — mantiene el estado del análisis activo globalmente.
 * Si el usuario navega a otra página, el análisis sigue corriendo en background
 * y puede volver a verlo desde el banner o desde Nuevo Análisis.
 */
import { createContext, useContext, useState, useRef, useCallback } from 'react'
import { cvsService } from '../services/procesoService'
import toast from 'react-hot-toast'

const AnalisisContext = createContext(null)

export function AnalisisProvider({ children }) {
  const [analisisActivo, setAnalisisActivo] = useState(null)
  // { procesoId, paso: 'analizando'|'listo', progreso: {...} }

  const pollRef = useRef(null)

  const iniciarAnalisis = useCallback((procesoId, archivos) => {
    setAnalisisActivo({
      procesoId,
      paso: 'analizando',
      progreso: {
        completado: 0, total: archivos.length, progreso_global: 0,
        log_actual: 'Preparando...', cancelado: false, tiempo_s: 0,
        items: archivos.map(f => ({ nombre: f.name, estado: 'pendiente' })),
      }
    })
    _poll(procesoId, archivos.length)
  }, [])

  const _poll = (id, totalEsperado) => {
    let sinCambio = 0
    let ultimoCompletado = -1

    const check = async () => {
      try {
        const { data } = await cvsService.estado(id)
        const procesados = data.completado + data.error

        setAnalisisActivo(prev => {
          if (!prev || prev.procesoId !== id) return prev
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
              items: prev.progreso.items.map((item, i) => ({
                ...item,
                estado: i < data.completado  ? 'completado'
                      : i < procesados        ? 'error'
                      : data.procesando > 0 && i === procesados ? 'procesando'
                      : 'pendiente',
              }))
            }
          }
        })

        if (data.listo === true && procesados >= data.total && data.total > 0) {
          setAnalisisActivo(prev => prev ? { ...prev, paso: 'listo' } : prev)
          return
        }

        // Detectar cuelgue real: 10 min sin avance
        if (procesados === ultimoCompletado) {
          sinCambio++
          if (sinCambio >= 300) {
            setAnalisisActivo(prev => prev ? { ...prev, paso: 'listo' } : prev)
            return
          }
        } else {
          sinCambio = 0
          ultimoCompletado = procesados
        }

        pollRef.current = setTimeout(check, 2000)
      } catch {
        pollRef.current = setTimeout(check, 3000)
      }
    }

    if (pollRef.current) clearTimeout(pollRef.current)
    check()
  }

  const limpiarAnalisis = useCallback(() => {
    if (pollRef.current) clearTimeout(pollRef.current)
    setAnalisisActivo(null)
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
