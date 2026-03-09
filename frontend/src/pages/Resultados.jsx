import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { procesoService, cvsService, reportesService } from '../services/procesoService'
import { useAnalisis } from '../context/AnalisisContext'
import AppLayout from '../components/layout/AppLayout'
import { Card, ScoreBar, ScoreNumber, Spinner, EmptyState } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

const MEDALLAS = ['🥇', '🥈', '🥉']
const BORDER_LEFT = ['#FACC15', '#94A3B8', '#CD7F32']

export default function Resultados() {
  const { procesoId } = useParams()
  const navigate = useNavigate()
  const { iniciarAnalisis } = useAnalisis()

  const [proceso, setProceso]     = useState(null)
  const [ranking, setRanking]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [exporting, setExport]    = useState(false)
  const [reanaliz, setReanaliz]   = useState(false)

  useEffect(() => {
    const cargar = async () => {
      try {
        const [{ data: p }, { data: r }] = await Promise.all([
          procesoService.obtener(procesoId),
          procesoService.ranking(procesoId),
        ])
        setProceso(p)
        setRanking(r.items)
      } catch {
        toast.error('Error cargando resultados.')
      } finally {
        setLoading(false)
      }
    }
    cargar()
  }, [procesoId])

  const handleExport = async () => {
    setExport(true)
    try {
      const { data } = await reportesService.exportarExcel(procesoId)
      const url  = URL.createObjectURL(new Blob([data]))
      const link = document.createElement('a')
      link.href  = url
      link.download = `Ranking_${proceso?.nombre_puesto?.replace(/ /g, '_')}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
      toast.success('Excel descargado.')
    } catch {
      toast.error('Error exportando Excel.')
    } finally {
      setExport(false)
    }
  }

  const handleReanalizar = async () => {
    if (!confirm(`¿Re-analizar todos los CVs del proceso "${proceso?.nombre_puesto}"?\n\nEsto sobreescribirá los resultados actuales con el nuevo modelo de evaluación.`)) return
    setReanaliz(true)
    try {
      await cvsService.analizar(procesoId, true)
      // Crear items mock para el contexto (nombre de cada candidato)
      const items = ranking.map(item => ({
        name: item.candidato.nombre || `CV #${item.candidato.id}`
      }))
      iniciarAnalisis(Number(procesoId), items)
      navigate('/nuevo-analisis')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al iniciar re-análisis.')
      setReanaliz(false)
    }
  }

  if (loading) return (
    <AppLayout>
      <div className="flex justify-center items-center h-full py-32">
        <Spinner size={12} />
      </div>
    </AppLayout>
  )

  return (
    <AppLayout>
      <div className="p-8 max-w-5xl">

        {/* Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <button onClick={() => navigate('/dashboard')}
              className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-3 transition-colors">
              ← Dashboard
            </button>
            <h1 className="text-3xl font-black text-white tracking-tight">{proceso?.nombre_puesto}</h1>
            <p className="text-slate-400 mt-1">
              {ranking.length} candidato{ranking.length !== 1 ? 's' : ''} · Ordenados por compatibilidad
            </p>
          </div>

          {/* Botones */}
          <div className="flex gap-3 flex-wrap">
            {/* Re-analizar */}
            {ranking.length > 0 && (
              <button onClick={handleReanalizar} disabled={reanaliz}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-60"
                style={{ border: '1.5px solid rgba(250,204,21,0.4)', background: 'rgba(250,204,21,0.06)', color: '#FACC15' }}
                onMouseEnter={e => !reanaliz && (e.currentTarget.style.background = 'rgba(250,204,21,0.12)')}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(250,204,21,0.06)'}>
                {reanaliz ? <Spinner size={4} /> : '🔄'} Re-analizar
              </button>
            )}
            {/* Exportar */}
            <button onClick={handleExport} disabled={exporting}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all disabled:opacity-60"
              style={{ border: '1.5px solid #22D3EE', background: 'rgba(34,211,238,0.08)', color: '#22D3EE' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.15)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(34,211,238,0.08)'}>
              {exporting ? <Spinner size={4} /> : '📥'} Exportar Excel
            </button>
          </div>
        </div>

        {/* Ranking */}
        {ranking.length === 0 ? (
          <EmptyState icon="⏳" title="Sin resultados aún"
            description="El análisis puede estar en proceso. Esperá unos segundos y recargá." />
        ) : (
          <div className="space-y-3">
            {ranking.map((item) => {
              const puntaje = item.analisis?.puntaje_total
              const pos     = item.posicion
              return (
                <div key={item.candidato.id}
                  onClick={() => navigate(`/resultados/${procesoId}/candidato/${item.candidato.id}`)}
                  className="flex items-center gap-4 p-5 rounded-2xl cursor-pointer transition-all group"
                  style={{
                    background: '#111827',
                    border: '1px solid #2A3A52',
                    borderLeft: pos <= 3 ? `4px solid ${BORDER_LEFT[pos - 1]}` : '1px solid #2A3A52',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#22D3EE'; e.currentTarget.style.background = '#141e30' }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = pos <= 3 ? BORDER_LEFT[pos - 1] : '#2A3A52'
                    e.currentTarget.style.background = '#111827'
                  }}>

                  {/* Medalla / número */}
                  <div className="w-10 text-2xl text-center flex-shrink-0">
                    {pos <= 3 ? MEDALLAS[pos - 1] : <span className="text-slate-600 font-bold text-lg">{pos}</span>}
                  </div>

                  {/* Avatar */}
                  <div className="w-11 h-11 rounded-full flex items-center justify-center text-sm font-black flex-shrink-0"
                    style={{ background: `hsl(${(item.candidato.id * 47) % 360}, 60%, 45%)`, color: 'white' }}>
                    {(item.candidato.nombre || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-white text-base mb-1">
                      {item.candidato.nombre || `CV #${item.candidato.id}`}
                    </div>
                    <div className="flex gap-4 flex-wrap">
                      {item.candidato.email && (
                        <span className="text-xs text-slate-500">📧 {item.candidato.email}</span>
                      )}
                      {item.candidato.telefono && (
                        <span className="text-xs text-slate-500">📞 {item.candidato.telefono}</span>
                      )}
                    </div>
                    {puntaje != null && (
                      <div className="mt-2">
                        <ScoreBar value={puntaje} height={5} />
                      </div>
                    )}
                  </div>

                  {/* Puntaje */}
                  <div className="text-right flex-shrink-0 mr-2">
                    {puntaje != null ? (
                      <>
                        <ScoreNumber value={puntaje} size="md" />
                        <div className="text-xs text-slate-500 mt-0.5">compatibilidad</div>
                      </>
                    ) : (
                      <span className="text-xs text-slate-600">Sin analizar</span>
                    )}
                  </div>

                  <span className="text-slate-600 group-hover:text-slate-300 transition-colors text-xl">→</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
