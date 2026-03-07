import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { procesoService, reportesService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Spinner, EmptyState } from '../components/ui/index.jsx'
import api from '../services/api'
import toast from 'react-hot-toast'

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
               border: `1px solid ${ok ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)'}` }}>
      <span className="w-2 h-2 rounded-full" style={{ background: ok ? '#4ADE80' : '#F87171' }} />
      {ok ? `IA Lista · ${status.modelo_requerido}` : 'IA no disponible'}
    </span>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate  = useNavigate()

  const [procesos, setProcesos]         = useState([])
  const [loading, setLoading]           = useState(true)
  const [ollamaStatus, setOllamaStatus] = useState(null)
  const [exportando, setExportando]     = useState(null) // proceso_id en curso
  const [eliminando, setEliminando]     = useState(null)

  const cargar = () => {
    procesoService.listar()
      .then(r => setProcesos(r.data))
      .catch(() => toast.error('Error cargando procesos.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    cargar()
    api.get('/cvs/ollama/estado')
      .then(r => setOllamaStatus(r.data))
      .catch(() => setOllamaStatus({ ollama_disponible: false, modelo_disponible: false }))
  }, [])

  const handleExportar = async (proceso) => {
    setExportando(proceso.id)
    try {
      const { data } = await reportesService.exportarExcel(proceso.id)
      const url  = URL.createObjectURL(new Blob([data]))
      const link = document.createElement('a')
      link.href  = url
      link.download = `Ranking_${proceso.nombre_puesto.replace(/ /g, '_')}.xlsx`
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
    if (!confirm(`¿Eliminar el proceso "${proceso.nombre_puesto}" y todos sus CVs?\nEsta acción no se puede deshacer.`)) return
    setEliminando(proceso.id)
    try {
      await api.delete(`/procesos/${proceso.id}`)
      toast.success('Proceso eliminado.')
      cargar()
    } catch {
      toast.error('Error eliminando el proceso.')
    } finally {
      setEliminando(null)
    }
  }

  const totalCandidatos = procesos.reduce((s, p) => s + (p.total_candidatos || 0), 0)
  const hoy = procesos.filter(p => new Date(p.creado_en).toDateString() === new Date().toDateString()).length
  const formatFecha = iso => new Date(iso).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })

  return (
    <AppLayout>
      <div className="p-8 max-w-6xl">

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
          <StatCard icon="📅" label="Creados hoy"    value={hoy}              sub="Nuevos procesos"       color="#A78BFA" />
          <StatCard icon="💰" label="Costo IA"       value="S/ 0"             sub="100% local · Ollama"  color="#FACC15" />
        </div>

        {/* Tabla de procesos */}
        <Card>
          <CardTitle>📋 Procesos de selección</CardTitle>

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
                    {['Puesto', 'CVs', 'Fecha', 'Acciones'].map(h => (
                      <th key={h} className="text-left text-xs font-bold text-slate-600 uppercase tracking-widest pb-4 pr-4">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A2235]">
                  {procesos.map(p => (
                    <tr key={p.id} className="group">

                      {/* Puesto */}
                      <td className="py-3 pr-4">
                        <button onClick={() => navigate(`/resultados/${p.id}`)}
                          className="font-semibold text-white text-sm hover:text-cyan-400 transition-colors text-left">
                          {p.nombre_puesto}
                        </button>
                      </td>

                      {/* CVs */}
                      <td className="py-3 pr-4">
                        <span className="text-sm font-mono font-bold" style={{ color: '#22D3EE' }}>
                          {p.total_candidatos}
                        </span>
                        <span className="text-xs text-slate-600 ml-1">CVs</span>
                      </td>

                      {/* Fecha */}
                      <td className="py-3 pr-4">
                        <span className="text-xs text-slate-500">{formatFecha(p.creado_en)}</span>
                      </td>

                      {/* Acciones */}
                      <td className="py-3">
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">

                          {/* Ver ranking */}
                          <button onClick={() => navigate(`/resultados/${p.id}`)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                            style={{ background: 'rgba(34,211,238,0.08)', color: '#22D3EE', border: '1px solid rgba(34,211,238,0.2)' }}
                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.15)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'rgba(34,211,238,0.08)'}>
                            Ver ranking
                          </button>

                          {/* Exportar Excel */}
                          <button
                            onClick={() => handleExportar(p)}
                            disabled={exportando === p.id || p.total_candidatos === 0}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-40"
                            style={{ background: 'rgba(74,222,128,0.08)', color: '#4ADE80', border: '1px solid rgba(74,222,128,0.2)' }}
                            onMouseEnter={e => !e.currentTarget.disabled && (e.currentTarget.style.background = 'rgba(74,222,128,0.15)')}
                            onMouseLeave={e => e.currentTarget.style.background = 'rgba(74,222,128,0.08)'}>
                            {exportando === p.id ? '...' : '📥 Excel'}
                          </button>

                          {/* Eliminar */}
                          <button
                            onClick={() => handleEliminar(p)}
                            disabled={eliminando === p.id}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-40"
                            style={{ background: 'rgba(248,113,113,0.08)', color: '#F87171', border: '1px solid rgba(248,113,113,0.2)' }}
                            onMouseEnter={e => !e.currentTarget.disabled && (e.currentTarget.style.background = 'rgba(248,113,113,0.15)')}
                            onMouseLeave={e => e.currentTarget.style.background = 'rgba(248,113,113,0.08)'}>
                            {eliminando === p.id ? '...' : '🗑 Eliminar'}
                          </button>

                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  )
}