import { useAnalisis } from '../../context/AnalisisContext'
import { useNavigate, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'

function BannerAnalisis() {
  const { analisisActivo, limpiarAnalisis } = useAnalisis()
  const navigate  = useNavigate()
  const location  = useLocation()

  if (!analisisActivo) return null

  const { paso, progreso, procesoId } = analisisActivo
  const pct      = progreso?.progreso_global || 0
  const t        = progreso?.tiempo_s || 0
  const mm       = String(Math.floor(t / 60)).padStart(2, '0')
  const ss       = String(t % 60).padStart(2, '0')
  const cancelado = progreso?.cancelado || false
  const listo     = paso === 'listo'

  // Color según estado
  const color   = listo && !cancelado ? '#4ADE80' : cancelado ? '#F87171' : '#22D3EE'
  const bgColor = listo && !cancelado ? 'rgba(74,222,128,0.15)' : cancelado ? 'rgba(248,113,113,0.1)' : 'rgba(34,211,238,0.12)'
  const border  = listo && !cancelado ? 'rgba(74,222,128,0.35)'  : cancelado ? 'rgba(248,113,113,0.3)' : 'rgba(34,211,238,0.35)'

  // Si ya estamos en /nuevo-analisis, ocultar el banner (la vista ya muestra el progreso)
  if (location.pathname === '/nuevo-analisis') return null

  const handleBoton = () => {
    if (listo && procesoId && !cancelado) {
      limpiarAnalisis()
      navigate('/resultados/' + procesoId)
    } else {
      // Navegar a la vista del análisis
      navigate('/nuevo-analisis')
    }
  }

  const label = listo && !cancelado
    ? 'Ver resultados →'
    : cancelado
    ? 'Ver cancelado →'
    : 'Ver progreso →'

  const titulo = listo && !cancelado
    ? '¡Análisis completado!'
    : cancelado
    ? 'Análisis cancelado'
    : 'Analizando CVs...'

  return (
    <div
      className="fixed bottom-5 right-5 z-50 w-72 rounded-2xl overflow-hidden"
      style={{
        background: '#0D1520',
        border:     '1px solid ' + border,
        boxShadow:  '0 8px 32px rgba(0,0,0,0.5), 0 0 24px ' + color + '18',
      }}>

      {/* Barra progreso */}
      <div className="h-1" style={{ background: '#1A2235' }}>
        <div className="h-full transition-all duration-500"
          style={{ width: pct + '%', background: color }} />
      </div>

      <div className="p-3">
        {/* Fila título */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            {listo || cancelado
              ? <span className="text-base flex-shrink-0">{cancelado ? '⛔' : '✅'}</span>
              : <div className="w-2 h-2 rounded-full flex-shrink-0 animate-pulse"
                  style={{ background: color }} />
            }
            <span className="text-xs font-bold text-white truncate">{titulo}</span>
          </div>
          <button
            onClick={limpiarAnalisis}
            className="text-slate-600 hover:text-slate-300 transition-colors text-sm ml-2 flex-shrink-0"
            title="Cerrar">✕</button>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xs font-mono font-bold" style={{ color }}>{pct}%</span>
          <span className="text-xs text-slate-500">
            {progreso?.completado ?? 0}/{progreso?.total ?? 0} CVs
          </span>
          <span className="text-xs font-mono text-slate-500">⏱ {mm}:{ss}</span>
        </div>

        {/* Botones */}
        <div className="flex gap-2">
          <button
            onClick={handleBoton}
            className="flex-1 py-1.5 rounded-lg text-xs font-bold transition-all"
            style={{ background: bgColor, color, border: '1px solid ' + border }}
            onMouseEnter={e => e.currentTarget.style.filter = 'brightness(1.15)'}
            onMouseLeave={e => e.currentTarget.style.filter = ''}>
            {label}
          </button>
          {listo && (
            <button
              onClick={limpiarAnalisis}
              className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all"
              style={{ background: 'rgba(255,255,255,0.04)', color: '#64748B', border: '1px solid #2A3A52' }}
              onMouseEnter={e => e.currentTarget.style.borderColor = color}
              onMouseLeave={e => e.currentTarget.style.borderColor = '#2A3A52'}>
              Cerrar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AppLayout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#0A0F1A' }}>
      <Sidebar />
      <BannerAnalisis />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
