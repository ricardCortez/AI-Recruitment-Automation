import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { procesoService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, ScoreBar, ScoreNumber, Spinner } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CUMPLE_CFG = {
  si:      { icon: '✅', label: 'Cumple',         color: '#4ADE80', bg: 'rgba(74,222,128,0.06)',  border: 'rgba(74,222,128,0.2)' },
  parcial: { icon: '⚠️', label: 'Parcial',        color: '#FACC15', bg: 'rgba(250,204,21,0.06)',  border: 'rgba(250,204,21,0.2)' },
  no:      { icon: '❌', label: 'No cumple',       color: '#F87171', bg: 'rgba(248,113,113,0.06)', border: 'rgba(248,113,113,0.2)' },
}

function scoreColor(v) {
  if (v >= 70) return '#4ADE80'
  if (v >= 50) return '#FACC15'
  return '#F87171'
}

function scoreBg(v) {
  if (v >= 70) return 'rgba(74,222,128,0.08)'
  if (v >= 50) return 'rgba(250,204,21,0.08)'
  return 'rgba(248,113,113,0.08)'
}

function scoreBorder(v) {
  if (v >= 70) return 'rgba(74,222,128,0.25)'
  if (v >= 50) return 'rgba(250,204,21,0.25)'
  return 'rgba(248,113,113,0.25)'
}

function proveedorLabel(p) {
  if (!p) return 'IA local'
  if (p.startsWith('ollama/')) return `Ollama · ${p.slice(7)} · local`
  if (p === 'ollama') return 'Ollama · 100% local'
  if (p.startsWith('openai/')) return `OpenAI · ${p.slice(7)}`
  if (p === 'openai') return 'OpenAI'
  return p
}

// Barra con etiqueta izquierda y valor derecha
function LabelBar({ label, value, max = 100, color, rightLabel }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-xs text-slate-400 truncate pr-2 flex-1">{label}</span>
        <span className="text-xs font-black font-mono flex-shrink-0" style={{ color: color || scoreColor(value) }}>
          {rightLabel ?? `${value.toFixed(0)}%`}
        </span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: '#1A2235' }}>
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color || scoreColor(value) }} />
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────
export default function DetalleCandidato() {
  const { procesoId, candidatoId } = useParams()
  const navigate = useNavigate()
  const [data, setData]       = useState(null)
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

  // Criterios filtrados (sin nombre vacío)
  const criterios = (analisis?.detalle_json || []).filter(c => c.criterio?.trim())

  // Detectar si tienen campo "peso" (análisis nuevo) o no (análisis viejo)
  const tienePeso = criterios.length > 0 && criterios[0].peso != null

  // Detectar datos viejos: puntaje <= peso_maximo_esperado (ej: todos <= 40 cuando hay 4 criterios)
  // En datos viejos el "puntaje" guardado era el peso del criterio, no el cumplimiento 0-100
  const esDatoViejo = !tienePeso && criterios.length > 0 &&
    criterios.every(c => (c.puntaje || 0) <= Math.ceil(100 / criterios.length) + 5)

  // Para datos viejos, derivar puntaje 0-100 del campo cumple
  const _puntajeDesde = (cumple) => cumple === 'si' ? 90 : cumple === 'parcial' ? 55 : 15

  // Para cada criterio calcular su aporte real al total
  const criteriosConAporte = criterios.map(c => {
    const peso    = tienePeso ? (c.peso || 0) : (100 / criterios.length)
    const puntaje = esDatoViejo ? _puntajeDesde(c.cumple) : (c.puntaje || 0)
    const aporte  = parseFloat((peso * puntaje / 100).toFixed(1))
    return { ...c, peso, puntaje, aporte }
  })

  const puntajeTotal  = analisis?.puntaje_total || 0
  const tieneError    = analisis?.estado === 'error'
  const mensajeError  = analisis?.error_msg && !analisis.error_msg.startsWith('[PROG:')
    ? analisis.error_msg : 'El análisis de este CV falló.'

  const initials = (candidato.nombre || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()
  const avatarBg = `hsl(${(candidato.id * 47) % 360}, 60%, 45%)`

  // Veredicto
  const esApto        = puntajeTotal >= 70
  const esAptoParcial = puntajeTotal >= 50 && puntajeTotal < 70
  const veredictoColor  = scoreColor(puntajeTotal)
  const veredictoLabel  = esApto ? 'APTO PARA EL PUESTO' : esAptoParcial ? 'APTO CON RESERVAS' : 'NO APTO PARA EL PUESTO'
  const veredictoIcon   = esApto ? '✅' : esAptoParcial ? '⚠️' : '❌'

  return (
    <AppLayout>
      <div className="p-8 max-w-5xl">

        {/* Back */}
        <button onClick={() => navigate(`/resultados/${procesoId}`)}
          className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-5 transition-colors">
          ← Volver al ranking
        </button>

        {/* Banner de error */}
        {tieneError && (
          <div className="flex items-center gap-3 p-4 rounded-xl mb-5"
            style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.25)' }}>
            <span className="text-2xl">⚠️</span>
            <div>
              <div className="font-bold text-red-400 text-sm mb-0.5">Análisis con error</div>
              <div className="text-xs text-slate-400">{mensajeError}</div>
            </div>
          </div>
        )}

        {/* Header candidato */}
        <div className="flex items-center gap-6 p-6 rounded-2xl mb-6"
          style={{ background: '#111827', border: `1px solid ${scoreBorder(puntajeTotal)}` }}>
          <div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-black flex-shrink-0"
            style={{ background: avatarBg, color: 'white' }}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-2xl font-black text-white mb-2">{candidato.nombre || `CV #${candidato.id}`}</div>
            <div className="flex gap-5 flex-wrap">
              {candidato.email    && <span className="text-sm text-slate-400">📧 {candidato.email}</span>}
              {candidato.telefono && <span className="text-sm text-slate-400">📞 {candidato.telefono}</span>}
              <span className="text-sm text-slate-400">🏆 Puesto #{posicion} del ranking</span>
            </div>
          </div>
          {puntajeTotal != null && (
            <div className="text-right flex-shrink-0">
              <div className="text-5xl font-black font-mono" style={{ color: veredictoColor }}>
                {puntajeTotal.toFixed(1)}%
              </div>
              <div className="text-xs text-slate-500 mt-1">Compatibilidad</div>
            </div>
          )}
        </div>

        {/* Aviso de datos viejos */}
        {esDatoViejo && (
          <div className="flex items-center gap-3 p-3 rounded-xl mb-4"
            style={{ background: 'rgba(250,204,21,0.06)', border: '1px solid rgba(250,204,21,0.2)' }}>
            <span className="text-lg flex-shrink-0">⚡</span>
            <p className="text-xs text-yellow-300">
              Este análisis fue generado con una versión anterior. Los porcentajes por criterio son estimados.
              <strong className="ml-1">Re-analizá el proceso para obtener datos exactos.</strong>
            </p>
          </div>
        )}

        {/* Veredicto */}
        <div className="flex items-center gap-4 p-5 rounded-2xl mb-6"
          style={{ background: scoreBg(puntajeTotal), border: `1.5px solid ${scoreBorder(puntajeTotal)}` }}>
          <span className="text-3xl flex-shrink-0">{veredictoIcon}</span>
          <div className="flex-1">
            <div className="text-lg font-black" style={{ color: veredictoColor }}>{veredictoLabel}</div>
            {analisis?.resumen_ia && (
              <p className="text-sm text-slate-300 mt-1 leading-relaxed">{analisis.resumen_ia}</p>
            )}
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-xs text-slate-500 mb-1">Modelo IA</div>
            <div className="text-xs font-bold" style={{ color: '#22D3EE' }}>{proveedorLabel(analisis?.proveedor_ia)}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ── Columna izquierda ────────────────────────────────────────── */}
          <div className="space-y-4">

            {/* Evaluacion por requisito */}
            <Card>
              <CardTitle>✅ Evaluación por requisito</CardTitle>
              {criterios.length === 0 ? (
                <p className="text-sm text-slate-500 py-2">Sin criterios disponibles.</p>
              ) : (
                <div className="space-y-3">
                  {criteriosConAporte.map((c, i) => {
                    const cfg = CUMPLE_CFG[c.cumple] || CUMPLE_CFG.no
                    return (
                      <div key={i} className="rounded-xl overflow-hidden"
                        style={{ border: `1px solid ${cfg.border}` }}>

                        {/* Header criterio */}
                        <div className="flex items-center justify-between px-4 py-3"
                          style={{ background: cfg.bg }}>
                          <div className="flex items-center gap-2">
                            <span className="text-base">{cfg.icon}</span>
                            <span className="font-bold text-white text-sm">{c.criterio}</span>
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0">
                            {tienePeso && (
                              <span className="text-xs text-slate-500">peso {c.peso}%</span>
                            )}
                            <span className="text-sm font-black font-mono" style={{ color: cfg.color }}>
                              {cfg.label}
                            </span>
                          </div>
                        </div>

                        {/* Barra de cumplimiento + descripcion */}
                        <div className="px-4 py-3" style={{ background: '#0D1421' }}>
                          <div className="flex justify-between items-center mb-1.5">
                            <span className="text-xs text-slate-500">Cumplimiento del criterio</span>
                            <span className="text-sm font-black font-mono" style={{ color: scoreColor(c.puntaje) }}>
                              {c.puntaje?.toFixed(0)}%
                            </span>
                          </div>
                          <div className="h-3 rounded-full overflow-hidden mb-2" style={{ background: '#1A2235' }}>
                            <div className="h-full rounded-full transition-all duration-700"
                              style={{ width: `${c.puntaje || 0}%`, background: scoreColor(c.puntaje) }} />
                          </div>
                          {c.descripcion && (
                            <p className="text-xs text-slate-400 leading-relaxed">{c.descripcion}</p>
                          )}
                          {tienePeso && (
                            <div className="mt-2 text-xs text-slate-600">
                              Aporte al total: <span className="font-bold text-slate-400">{c.aporte.toFixed(1)} pts</span>
                              {' '}({c.peso}% × {c.puntaje?.toFixed(0)}% = {c.aporte.toFixed(1)})
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </Card>

            {/* Como se calcula el total */}
            {tienePeso && criteriosConAporte.length > 0 && (
              <Card style={{ background: 'rgba(34,211,238,0.02)', border: '1px solid rgba(34,211,238,0.12)' }}>
                <CardTitle>🧮 Cálculo del puntaje total</CardTitle>
                <div className="space-y-1.5 mb-3">
                  {criteriosConAporte.map((c, i) => (
                    <div key={i} className="flex items-center justify-between text-xs py-1"
                      style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <span className="text-slate-400 truncate flex-1 pr-2">{c.criterio}</span>
                      <span className="text-slate-500 flex-shrink-0 font-mono">
                        {c.peso}% × {c.puntaje?.toFixed(0)}% =
                      </span>
                      <span className="font-black font-mono ml-2 flex-shrink-0 w-12 text-right"
                        style={{ color: scoreColor(c.puntaje) }}>
                        {c.aporte.toFixed(1)}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="flex justify-between items-center pt-2"
                  style={{ borderTop: '2px solid rgba(34,211,238,0.2)' }}>
                  <span className="text-sm font-bold text-white">Total calculado</span>
                  <span className="text-xl font-black font-mono" style={{ color: veredictoColor }}>
                    {criteriosConAporte.reduce((s, c) => s + c.aporte, 0).toFixed(1)}%
                  </span>
                </div>
                {Math.abs(criteriosConAporte.reduce((s,c)=>s+c.aporte,0) - puntajeTotal) > 1.5 && (
                  <div className="text-xs text-slate-600 mt-2">
                    * Valor guardado: {puntajeTotal.toFixed(1)}% (diferencia por redondeo en criterios)
                  </div>
                )}
              </Card>
            )}
          </div>

          {/* ── Columna derecha ───────────────────────────────────────────── */}
          <div className="space-y-4">

            {/* Compatibilidad por criterio — barras comparativas */}
            {criteriosConAporte.length > 0 && (
              <Card>
                <CardTitle>📊 Compatibilidad por criterio</CardTitle>
                <div className="space-y-4">
                  {criteriosConAporte.map((c, i) => (
                    <div key={i}>
                      <LabelBar
                        label={c.criterio}
                        value={c.puntaje || 0}
                        color={scoreColor(c.puntaje)}
                      />
                      {tienePeso && (
                        <div className="text-xs text-slate-600 mt-1 ml-0.5">
                          Peso en el total: {c.peso}%
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Leyenda */}
                <div className="mt-5 pt-4 flex flex-wrap gap-3"
                  style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                  {[
                    { color: '#4ADE80', label: '≥ 70% Cumple' },
                    { color: '#FACC15', label: '50–69% Parcial' },
                    { color: '#F87171', label: '< 50% No cumple' },
                  ].map(l => (
                    <div key={l.label} className="flex items-center gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: l.color }} />
                      <span className="text-xs text-slate-500">{l.label}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Resumen estadistico */}
            {criteriosConAporte.length > 0 && (
              <Card>
                <CardTitle>📈 Resumen estadístico</CardTitle>
                <div className="grid grid-cols-3 gap-3 mb-4">
                  {[
                    {
                      label: 'Cumple',
                      value: criteriosConAporte.filter(c => c.cumple === 'si').length,
                      color: '#4ADE80',
                      bg: 'rgba(74,222,128,0.08)',
                    },
                    {
                      label: 'Parcial',
                      value: criteriosConAporte.filter(c => c.cumple === 'parcial').length,
                      color: '#FACC15',
                      bg: 'rgba(250,204,21,0.08)',
                    },
                    {
                      label: 'No cumple',
                      value: criteriosConAporte.filter(c => c.cumple === 'no').length,
                      color: '#F87171',
                      bg: 'rgba(248,113,113,0.08)',
                    },
                  ].map(s => (
                    <div key={s.label} className="p-3 rounded-xl text-center"
                      style={{ background: s.bg }}>
                      <div className="text-2xl font-black" style={{ color: s.color }}>{s.value}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
                    </div>
                  ))}
                </div>

                {/* Criterios mas fuertes y debiles */}
                {criteriosConAporte.length >= 2 && (() => {
                  const sorted = [...criteriosConAporte].sort((a, b) => b.puntaje - a.puntaje)
                  const mejor  = sorted[0]
                  const peor   = sorted[sorted.length - 1]
                  return (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 p-2.5 rounded-lg"
                        style={{ background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.15)' }}>
                        <span className="text-lg">💪</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-slate-500">Punto más fuerte</div>
                          <div className="text-sm font-bold text-white truncate">{mejor.criterio}</div>
                        </div>
                        <span className="text-sm font-black font-mono" style={{ color: '#4ADE80' }}>
                          {mejor.puntaje?.toFixed(0)}%
                        </span>
                      </div>
                      <div className="flex items-center gap-2 p-2.5 rounded-lg"
                        style={{ background: scoreBg(peor.puntaje), border: `1px solid ${scoreBorder(peor.puntaje)}` }}>
                        <span className="text-lg">
                          {peor.puntaje >= 70 ? '📊' : peor.puntaje >= 50 ? '⚠️' : '📌'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-slate-500">
                            {peor.puntaje >= 70 ? 'Punto más bajo (aun cumple)' : peor.puntaje >= 50 ? 'Área de mejora' : 'Brecha principal'}
                          </div>
                          <div className="text-sm font-bold text-white truncate">{peor.criterio}</div>
                        </div>
                        <span className="text-sm font-black font-mono" style={{ color: scoreColor(peor.puntaje) }}>
                          {peor.puntaje?.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )
                })()}
              </Card>
            )}

            {/* Aporte al total — barras de contribución */}
            {tienePeso && criteriosConAporte.length > 0 && (
              <Card>
                <CardTitle>🎯 Aporte de cada criterio al total</CardTitle>
                <div className="space-y-3">
                  {[...criteriosConAporte]
                    .sort((a, b) => b.aporte - a.aporte)
                    .map((c, i) => (
                      <LabelBar
                        key={i}
                        label={c.criterio}
                        value={c.aporte}
                        max={c.peso}  // maximo posible = su peso
                        color={scoreColor(c.puntaje)}
                        rightLabel={`${c.aporte.toFixed(1)} / ${c.peso} pts`}
                      />
                    ))}
                </div>
                <div className="text-xs text-slate-600 mt-3">
                  Cada barra muestra cuántos puntos aportó vs cuántos podría aportar
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
