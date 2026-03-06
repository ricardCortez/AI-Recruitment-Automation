import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { procesoService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, ScoreBar, ScoreNumber, Spinner } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

const CUMPLE_CFG = {
  si:      { icon: '✅', label: 'Cumple',          color: '#4ADE80', bg: 'rgba(74,222,128,0.05)',  border: 'rgba(74,222,128,0.2)' },
  parcial: { icon: '⚠️', label: 'Cumple parcial',  color: '#FACC15', bg: 'rgba(250,204,21,0.05)',  border: 'rgba(250,204,21,0.2)' },
  no:      { icon: '❌', label: 'No cumple',        color: '#F87171', bg: 'rgba(248,113,113,0.05)', border: 'rgba(248,113,113,0.2)' },
}

export default function DetalleCandidato() {
  const { procesoId, candidatoId } = useParams()
  const navigate = useNavigate()

  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    procesoService.ranking(procesoId)
      .then(({ data: r }) => {
        const item = r.items.find(i => String(i.candidato.id) === String(candidatoId))
        if (!item) toast.error('Candidato no encontrado.')
        setData(item)
      })
      .catch(() => toast.error('Error cargando detalle.'))
      .finally(() => setLoading(false))
  }, [procesoId, candidatoId])

  if (loading) return (
    <AppLayout>
      <div className="flex justify-center items-center py-32"><Spinner size={12} /></div>
    </AppLayout>
  )

  if (!data) return (
    <AppLayout>
      <div className="p-8 text-slate-400">Candidato no encontrado.</div>
    </AppLayout>
  )

  const { candidato, analisis, posicion } = data
  const criterios = analisis?.detalle_json || []
  const initials  = (candidato.nombre || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()
  const avatarBg  = `hsl(${(candidato.id * 47) % 360}, 60%, 45%)`

  return (
    <AppLayout>
      <div className="p-8 max-w-5xl">

        {/* Back */}
        <button onClick={() => navigate(`/resultados/${procesoId}`)}
          className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-5 transition-colors">
          ← Volver al ranking
        </button>

        {/* Header del candidato */}
        <div className="flex items-center gap-6 p-6 rounded-2xl mb-6"
          style={{ background: '#111827', border: '1px solid #2A3A52' }}>
          <div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-black flex-shrink-0"
            style={{ background: avatarBg, color: 'white' }}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-2xl font-black text-white mb-2">
              {candidato.nombre || `CV #${candidato.id}`}
            </div>
            <div className="flex gap-5 flex-wrap">
              {candidato.email    && <span className="text-sm text-slate-400">📧 {candidato.email}</span>}
              {candidato.telefono && <span className="text-sm text-slate-400">📞 {candidato.telefono}</span>}
              <span className="text-sm text-slate-400">🏆 Puesto #{posicion} del ranking</span>
            </div>
          </div>
          {analisis?.puntaje_total != null && (
            <div className="text-right flex-shrink-0">
              <ScoreNumber value={analisis.puntaje_total} size="lg" />
              <div className="text-xs text-slate-500 mt-1">Compatibilidad</div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Evaluación por requisito */}
          <div>
            <Card>
              <CardTitle>✅ Evaluación por requisito</CardTitle>

              {criterios.length === 0 ? (
                <p className="text-sm text-slate-500">Sin criterios disponibles.</p>
              ) : (
                <div className="space-y-3">
                  {criterios.map((c, i) => {
                    const cfg = CUMPLE_CFG[c.cumple] || CUMPLE_CFG.no
                    return (
                      <div key={i} className="flex items-start gap-3 p-4 rounded-xl"
                        style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                        <span className="text-xl flex-shrink-0 mt-0.5">{cfg.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-bold text-white text-sm mb-1">{c.criterio}</div>
                          <div className="text-xs text-slate-400 leading-relaxed">{c.descripcion}</div>
                        </div>
                        <span className="text-sm font-bold flex-shrink-0" style={{ color: cfg.color, fontFamily: 'monospace' }}>
                          {c.puntaje?.toFixed(0)}%
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </Card>
          </div>

          {/* Columna derecha */}
          <div className="flex flex-col gap-4">

            {/* Barras de compatibilidad */}
            {criterios.length > 0 && (
              <Card>
                <CardTitle>📊 Compatibilidad por criterio</CardTitle>
                <div className="space-y-4">
                  {criterios.map((c, i) => (
                    <div key={i}>
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="text-xs text-slate-400 truncate pr-2 flex-1">{c.criterio}</span>
                        <span className="text-xs font-bold flex-shrink-0" style={{
                          color: c.puntaje >= 70 ? '#4ADE80' : c.puntaje >= 50 ? '#FACC15' : '#F87171',
                          fontFamily: 'monospace',
                        }}>
                          {c.puntaje?.toFixed(0)}%
                        </span>
                      </div>
                      <ScoreBar value={c.puntaje || 0} height={6} />
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Resumen IA */}
            {analisis?.resumen_ia && (
              <Card style={{ background: 'rgba(34,211,238,0.03)', border: '1px solid rgba(34,211,238,0.2)' }}>
                <CardTitle>🤖 Resumen generado por IA</CardTitle>
                <div className="text-xs font-bold uppercase tracking-widest mb-3"
                  style={{ color: '#22D3EE' }}>
                  {analisis.proveedor_ia === 'ollama' ? 'Ollama · Llama 3.1 8B · 100% local' : 'OpenAI GPT-4o-mini'}
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">{analisis.resumen_ia}</p>
              </Card>
            )}
          </div>

        </div>
      </div>
    </AppLayout>
  )
}
