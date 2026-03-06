import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { procesoService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Badge, Spinner, EmptyState } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

function StatCard({ label, value, sub, color = '#22D3EE' }) {
  return (
    <Card>
      <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">{label}</p>
      <div className="text-4xl font-black mb-1" style={{ color, fontFamily: 'monospace' }}>{value}</div>
      <p className="text-xs text-slate-600">{sub}</p>
    </Card>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [procesos, setProcesos] = useState([])
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    procesoService.listar()
      .then(r => setProcesos(r.data))
      .catch(() => toast.error('Error cargando procesos.'))
      .finally(() => setLoading(false))
  }, [])

  const total   = procesos.length
  const hoy     = procesos.filter(p => {
    const d = new Date(p.creado_en)
    const n = new Date()
    return d.toDateString() === n.toDateString()
  }).length

  return (
    <AppLayout>
      <div className="p-8 max-w-6xl">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-black text-white tracking-tight">Dashboard</h1>
          <p className="text-slate-400 mt-1">
            Bienvenido, <span className="text-white font-semibold">{user?.nombre_completo}</span>
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Procesos totales"    value={total}  sub="Desde el inicio"       color="#22D3EE" />
          <StatCard label="Creados hoy"         value={hoy}    sub="Nuevos procesos"        color="#4ADE80" />
          <StatCard label="Estado IA"           value="● ON"   sub="Ollama · Llama 3.1 8B" color="#4ADE80" />
          <StatCard label="Costo operativo"     value="S/ 0"   sub="Por mes · 100% local"  color="#FACC15" />
        </div>

        {/* Procesos recientes */}
        <Card>
          <div className="flex items-center justify-between mb-5">
            <CardTitle>📂 Procesos recientes</CardTitle>
            <button onClick={() => navigate('/nuevo-analisis')}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all"
              style={{ background: 'rgba(34,211,238,0.1)', color: '#22D3EE', border: '1px solid rgba(34,211,238,0.25)' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.18)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(34,211,238,0.1)'}>
              + Nuevo análisis
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : procesos.length === 0 ? (
            <EmptyState
              icon="📭"
              title="Sin procesos todavía"
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
            <div className="space-y-3">
              {procesos.slice(0, 8).map(p => (
                <div key={p.id}
                  onClick={() => navigate(`/resultados/${p.id}`)}
                  className="flex items-center justify-between p-4 rounded-xl cursor-pointer transition-all group"
                  style={{ background: '#1A2235', border: '1px solid #2A3A52' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#22D3EE'; e.currentTarget.style.background = '#1e2c44' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = '#2A3A52'; e.currentTarget.style.background = '#1A2235' }}>

                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
                      style={{ background: 'rgba(34,211,238,0.08)', border: '1px solid rgba(34,211,238,0.15)' }}>
                      📋
                    </div>
                    <div>
                      <div className="font-semibold text-white text-sm">{p.nombre_puesto}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {p.total_candidatos ?? 0} candidato{p.total_candidatos !== 1 ? 's' : ''} ·{' '}
                        {new Date(p.creado_en).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Badge variant="green">Completado</Badge>
                    <span className="text-slate-600 group-hover:text-slate-300 transition-colors text-lg">→</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

      </div>
    </AppLayout>
  )
}
