import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useAnalisis } from '../context/AnalisisContext'
import { procesoService, reportesService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Spinner, EmptyState } from '../components/ui/index.jsx'
import api from '../services/api'
import toast from 'react-hot-toast'

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatFechaHora(iso) {
  if (!iso) return '—'
  // Forzar interpretación UTC → convierte a hora local del navegador
  const utc = iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z'
  const d = new Date(utc)
  const fecha = d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })
  const hora  = d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false })
  return { fecha, hora }
}

function formatTiempo(s) {
  if (!s || s <= 0) return null
  if (s < 60)   return s + 's'
  const m = Math.floor(s / 60), seg = s % 60
  return m + 'm ' + (seg > 0 ? seg + 's' : '')
}

// ── Componentes ───────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color, icon }) {
  return (
    <Card>
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">{label}</p>
        <span className="text-xl">{icon}</span>
      </div>
      <div className="text-4xl font-black mb-1" style={{ color, fontFamily: 'monospace' }}>{value}</div>
      <p className="text-xs text-slate-600">{sub}</p>
    </Card>
  )
}

function OllamaBadge({ status }) {
  if (!status) return (
    <span className="flex items-center gap-1.5 text-xs text-slate-500">
      <span className="w-2 h-2 rounded-full bg-slate-600 animate-pulse" /> Verificando IA...
    </span>
  )
  const ok = status.ollama_disponible && status.modelo_disponible
  return (
    <span className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full"
      style={{ background: ok ? 'rgba(74,222,128,0.1)' : 'rgba(248,113,113,0.1)',
               color: ok ? '#4ADE80' : '#F87171',
               border: '1px solid ' + (ok ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)') }}>
      <span className="w-2 h-2 rounded-full" style={{ background: ok ? '#4ADE80' : '#F87171' }} />
      {ok ? 'IA Lista · ' + status.modelo_requerido : 'IA no disponible'}
    </span>
  )
}

function BadgeEstado({ estado, completados, total }) {
  const cfg = {
    sin_analisis: { label: 'Sin analizar',  color: '#475569', bg: 'rgba(71,85,105,0.12)',   dot: '#475569' },
    pendiente:    { label: 'Pendiente',     color: '#94A3B8', bg: 'rgba(148,163,184,0.1)',  dot: '#94A3B8' },
    en_proceso:   { label: 'En proceso',    color: '#22D3EE', bg: 'rgba(34,211,238,0.1)',   dot: '#22D3EE', pulse: true },
    parcial:      { label: 'Parcial',       color: '#FACC15', bg: 'rgba(250,204,21,0.1)',   dot: '#FACC15' },
    finalizado:   { label: 'Finalizado',    color: '#4ADE80', bg: 'rgba(74,222,128,0.1)',   dot: '#4ADE80' },
  }[estado] || { label: estado, color: '#94A3B8', bg: 'rgba(148,163,184,0.1)', dot: '#94A3B8' }

  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full w-fit"
      style={{ background: cfg.bg, border: '1px solid ' + cfg.color + '30' }}>
      <span className={'w-1.5 h-1.5 rounded-full flex-shrink-0' + (cfg.pulse ? ' animate-pulse' : '')}
        style={{ background: cfg.dot }} />
      <span className="text-xs font-semibold" style={{ color: cfg.color }}>
        {cfg.label}
        {estado === 'en_proceso' && total > 0 && (
          <span className="ml-1 opacity-70">{completados}/{total}</span>
        )}
      </span>
    </div>
  )
}

// ── Dashboard principal ──────────────────────────────────────────────────────
export default function Dashboard() {
  const { user }     = useAuth()
  const navigate     = useNavigate()
  const { analisisActivo } = useAnalisis()

  const [procesos, setProcesos]         = useState([])
  const [loading, setLoading]           = useState(true)
  const [ollamaStatus, setOllamaStatus] = useState(null)
  const [exportando, setExportando]     = useState(null)
  const [eliminando, setEliminando]     = useState(null)

  const cargar = useCallback(() => {
    procesoService.listar()
      .then(r => setProcesos(r.data))
      .catch(() => toast.error('Error cargando procesos.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    cargar()
    api.get('/cvs/ollama/estado')
      .then(r => setOllamaStatus(r.data))
      .catch(() => setOllamaStatus({ ollama_disponible: false, modelo_disponible: false }))
  }, [])

  // Recargar tabla cuando termina el análisis
  useEffect(() => {
    if (analisisActivo?.paso === 'listo') {
      setTimeout(cargar, 800)
    }
  }, [analisisActivo?.paso])

  // Mientras corre el análisis, refrescar la tabla cada 5s
  // para que el estado y el contador de CVs se actualicen
  useEffect(() => {
    if (analisisActivo?.paso !== 'analizando') return
    const iv = setInterval(cargar, 5000)
    return () => clearInterval(iv)
  }, [analisisActivo?.paso, cargar])

  // Recargar al volver a la pestaña (Page Visibility API)
  useEffect(() => {
    const onVisible = () => { if (!document.hidden) cargar() }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [cargar])

  const handleExportar = async (proceso) => {
    setExportando(proceso.id)
    try {
      const { data } = await reportesService.exportarExcel(proceso.id)
      const url  = URL.createObjectURL(new Blob([data]))
      const link = document.createElement('a')
      link.href     = url
      link.download = 'Ranking_' + proceso.nombre_puesto.replace(/ /g, '_') + '.xlsx'
      link.click()
      URL.revokeObjectURL(url)
      toast.success('Excel descargado.')
    } catch {
      toast.error('Error exportando. Verificá que el proceso tenga análisis completados.')
    } finally {
      setExportando(null)
    }
  }

  const handleEliminar = async (proceso) => {
    if (!confirm('¿Eliminar el proceso "' + proceso.nombre_puesto + '" y todos sus CVs?\nEsta acción no se puede deshacer.')) return
    setEliminando(proceso.id)
    try {
      await api.delete('/procesos/' + proceso.id)
      toast.success('Proceso eliminado.')
      cargar()
    } catch {
      toast.error('Error eliminando el proceso.')
    } finally {
      setEliminando(null)
    }
  }

  const totalCandidatos  = procesos.reduce((s, p) => s + (p.total_candidatos || 0), 0)
  const hoy = procesos.filter(p => {
    // Forzar UTC → local para comparar fechas correctamente sin importar timezone del servidor
    const utc = p.creado_en?.endsWith('Z') || p.creado_en?.includes('+') ? p.creado_en : p.creado_en + 'Z'
    const d   = new Date(utc)
    const n   = new Date()
    return d.toLocaleDateString() === n.toLocaleDateString()
  }).length
  const finalizados = procesos.filter(p => p.estado === 'finalizado').length

  return (
    <AppLayout>
      <div className="p-8 max-w-7xl">

        {/* Header */}
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-black text-white tracking-tight">Dashboard</h1>
            <p className="text-slate-400 mt-1">
              Bienvenido, <span className="text-white font-semibold">{user?.nombre_completo}</span>
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <OllamaBadge status={ollamaStatus} />
            <button onClick={() => navigate('/nuevo-analisis')}
              className="px-4 py-2 rounded-xl text-sm font-bold transition-all"
              style={{ background: '#22D3EE', color: '#0A0F1A' }}
              onMouseEnter={e => e.currentTarget.style.filter = 'brightness(1.08)'}
              onMouseLeave={e => e.currentTarget.style.filter = ''}>
              + Nuevo análisis
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard icon="📂" label="Procesos"       value={procesos.length}  sub="Total histórico"       color="#22D3EE" />
          <StatCard icon="👤" label="CVs analizados" value={totalCandidatos}  sub="En todos los procesos" color="#4ADE80" />
          <StatCard icon="✅" label="Finalizados"    value={finalizados}      sub="Análisis completos"    color="#A78BFA" />
          <StatCard icon="💰" label="Costo IA"       value="S/ 0"             sub="100% local · Ollama"  color="#FACC15" />
        </div>

        {/* Tabla */}
        <Card>
          <div className="flex items-center justify-between mb-5">
            <CardTitle>📋 Procesos de selección</CardTitle>
            {analisisActivo?.paso === 'analizando' && (
              <button onClick={() => navigate('/nuevo-analisis')}
                className="flex items-center gap-2 text-xs font-bold px-3 py-1.5 rounded-full animate-pulse"
                style={{ background: 'rgba(34,211,238,0.1)', color: '#22D3EE', border: '1px solid rgba(34,211,238,0.25)' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                Análisis en curso — ver progreso
              </button>
            )}
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : procesos.length === 0 ? (
            <EmptyState
              icon="📭" title="Sin procesos todavía"
              description="Cargá CVs y definí los requisitos del puesto para empezar."
              action={
                <button onClick={() => navigate('/nuevo-analisis')}
                  className="px-5 py-2.5 rounded-xl text-sm font-bold"
                  style={{ background: '#22D3EE', color: '#0A0F1A' }}>
                  Crear primer proceso →
                </button>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    {['Puesto', 'CVs', 'Fecha', 'Hora', 'Duración', 'Estado', 'Acciones'].map(h => (
                      <th key={h} className="text-left text-xs font-bold text-slate-600 uppercase tracking-widest pb-4 pr-4 whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A2235]">
                  {procesos.map(p => {
                    const { fecha, hora } = formatFechaHora(p.creado_en)
                    const duracion = formatTiempo(p.tiempo_analisis_s)
                    const esActivo = analisisActivo?.procesoId === p.id

                    return (
                      <tr key={p.id} className="group hover:bg-white/[0.02] transition-colors">

                        {/* Puesto */}
                        <td className="py-3.5 pr-4">
                          <div className="flex items-center gap-2">
                            <button onClick={() => navigate('/resultados/' + p.id)}
                              className="font-semibold text-white text-sm hover:text-cyan-400 transition-colors text-left">
                              {p.nombre_puesto}
                            </button>
                            {esActivo && (
                              <span className="text-xs px-1.5 py-0.5 rounded-full font-bold animate-pulse"
                                style={{ background: 'rgba(34,211,238,0.1)', color: '#22D3EE' }}>
                                activo
                              </span>
                            )}
                          </div>
                        </td>

                        {/* CVs */}
                        <td className="py-3.5 pr-4 whitespace-nowrap">
                          <span className="text-sm font-mono font-bold" style={{ color: '#22D3EE' }}>
                            {p.completados > 0 ? p.completados + '/' : ''}{p.total_candidatos}
                          </span>
                          <span className="text-xs text-slate-600 ml-1">CVs</span>
                        </td>

                        {/* Fecha */}
                        <td className="py-3.5 pr-4 whitespace-nowrap">
                          <span className="text-xs text-slate-400">{fecha}</span>
                        </td>

                        {/* Hora */}
                        <td className="py-3.5 pr-4 whitespace-nowrap">
                          <span className="text-xs font-mono" style={{ color: '#64748B' }}>{hora}</span>
                        </td>

                        {/* Duración */}
                        <td className="py-3.5 pr-4 whitespace-nowrap">
                          {esActivo ? (
                            <span className="text-xs font-mono px-2 py-0.5 rounded-lg animate-pulse"
                              style={{ background: 'rgba(34,211,238,0.08)', color: '#22D3EE',
                                       border: '1px solid rgba(34,211,238,0.15)' }}>
                              ⏱ {formatTiempo(analisisActivo.progreso.tiempo_s)}
                            </span>
                          ) : duracion ? (
                            <span className="text-xs font-mono px-2 py-0.5 rounded-lg"
                              style={{ background: 'rgba(167,139,250,0.08)', color: '#A78BFA',
                                       border: '1px solid rgba(167,139,250,0.15)' }}>
                              ⏱ {duracion}
                            </span>
                          ) : (
                            <span className="text-xs text-slate-700">—</span>
                          )}
                        </td>

                        {/* Estado */}
                        <td className="py-3.5 pr-4">
                          <BadgeEstado
                            estado={esActivo ? 'en_proceso' : p.estado}
                            completados={esActivo ? analisisActivo.progreso.completado : p.completados}
                            total={p.total_candidatos}
                          />
                        </td>

                        {/* Acciones — siempre visibles */}
                        <td className="py-3.5">
                          <div className="flex gap-2 flex-wrap">
                            <button onClick={() => navigate('/resultados/' + p.id)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap"
                              style={{ background: 'rgba(34,211,238,0.08)', color: '#22D3EE', border: '1px solid rgba(34,211,238,0.2)' }}
                              onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.15)'}
                              onMouseLeave={e => e.currentTarget.style.background = 'rgba(34,211,238,0.08)'}>
                              Ver ranking
                            </button>

                            <button
                              onClick={() => handleExportar(p)}
                              disabled={exportando === p.id || p.completados === 0}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-40 whitespace-nowrap"
                              style={{ background: 'rgba(74,222,128,0.08)', color: '#4ADE80', border: '1px solid rgba(74,222,128,0.2)' }}
                              onMouseEnter={e => !e.currentTarget.disabled && (e.currentTarget.style.background = 'rgba(74,222,128,0.15)')}
                              onMouseLeave={e => e.currentTarget.style.background = 'rgba(74,222,128,0.08)'}>
                              {exportando === p.id ? '...' : '📥 Excel'}
                            </button>

                            <button
                              onClick={() => handleEliminar(p)}
                              disabled={eliminando === p.id}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-40"
                              style={{ background: 'rgba(248,113,113,0.08)', color: '#F87171', border: '1px solid rgba(248,113,113,0.2)' }}
                              onMouseEnter={e => !e.currentTarget.disabled && (e.currentTarget.style.background = 'rgba(248,113,113,0.15)')}
                              onMouseLeave={e => e.currentTarget.style.background = 'rgba(248,113,113,0.08)'}>
                              {eliminando === p.id ? '...' : '🗑'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  )
}
