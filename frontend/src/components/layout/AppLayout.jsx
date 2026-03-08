import { useAnalisis } from '../../context/AnalisisContext'
import { useNavigate } from 'react-router-dom'
import Sidebar from './Sidebar'

function BannerAnalisis() {
  const { analisisActivo } = useAnalisis()
  const navigate = useNavigate()
  if (!analisisActivo) return null
  const { paso, progreso, procesoId } = analisisActivo
  const pct = progreso.progreso_global || 0
  const t   = progreso.tiempo_s || 0
  const mm  = String(Math.floor(t / 60)).padStart(2, '0')
  const ss  = String(t % 60).padStart(2, '0')

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 px-4 pb-4 pointer-events-none"
      style={{ paddingLeft: '272px' }}>
      <div className="pointer-events-auto rounded-2xl p-4 flex items-center gap-4 shadow-2xl"
        style={{ background: '#111827', border: '1px solid rgba(34,211,238,0.3)',
                 boxShadow: '0 0 30px rgba(34,211,238,0.08)' }}>

        {/* Indicador */}
        {paso === 'analizando' ? (
          <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center"
            style={{ background: 'rgba(34,211,238,0.1)', border: '1px solid rgba(34,211,238,0.3)' }}>
            <div className="w-3 h-3 rounded-full animate-pulse" style={{ background: '#22D3EE' }} />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center"
            style={{ background: 'rgba(74,222,128,0.1)' }}>
            <span className="text-sm">✅</span>
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1.5">
            <span className="text-xs font-bold text-white">
              {paso === 'analizando' ? 'Analizando CVs...' : 'Análisis completado'}
            </span>
            <span className="text-xs font-mono" style={{ color: '#22D3EE' }}>{pct}%</span>
            <span className="text-xs font-mono text-slate-500">⏱ {mm}:{ss}</span>
            <span className="text-xs text-slate-500">
              {progreso.completado}/{progreso.total} CVs
            </span>
          </div>
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#2A3A52' }}>
            <div className="h-full rounded-full transition-all duration-500"
              style={{ width: pct + '%',
                       background: paso === 'listo' ? '#4ADE80' : '#22D3EE' }} />
          </div>
        </div>

        {/* Botón ver */}
        <button onClick={() => navigate('/nuevo-analisis')}
          className="px-3 py-1.5 rounded-lg text-xs font-bold flex-shrink-0 transition-all"
          style={{ background: 'rgba(34,211,238,0.1)', color: '#22D3EE',
                   border: '1px solid rgba(34,211,238,0.25)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.2)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(34,211,238,0.1)'}>
          Ver progreso →
        </button>
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
