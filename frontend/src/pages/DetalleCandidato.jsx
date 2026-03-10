import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { procesoService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { PageContainer } from '../components/ui/index.jsx'
import { useTheme } from '../components/lg/ThemeContext'
import { GlassCard, ScoreRing, ScoreBar, LGBadge, LGSpinner, BackButton, SectionLabel, ActionButton } from '../components/lg/components'
import { AC, scoreColor, blur } from '../components/lg/theme'
import toast from 'react-hot-toast'
import api from '../services/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────
const CUMPLE_CFG = {
  si:      { icon: '✅', label: 'Cumple',   color: AC.green,  bg: AC.green  + '10', border: AC.green  + '35' },
  parcial: { icon: '⚠️', label: 'Parcial',  color: AC.orange, bg: AC.orange + '10', border: AC.orange + '35' },
  no:      { icon: '❌', label: 'No cumple', color: AC.red,    bg: AC.red    + '10', border: AC.red    + '35' },
}
const ALERTA_CFG = {
  inconsistencia: { icon: '🔀', color: AC.orange },
  vacio:          { icon: '⬜', color: AC.yellow },
  riesgo:         { icon: '⚠️', color: AC.red    },
  verificar:      { icon: '🔍', color: AC.teal   },
}
const NIVEL_CFG = {
  alta:  { label: 'Alta',  color: AC.red    },
  media: { label: 'Media', color: AC.orange },
  baja:  { label: 'Baja',  color: AC.teal   },
}
const PREGUNTA_CFG = {
  brecha:    { icon: '📌', color: AC.red,    label: 'Brecha'    },
  excedente: { icon: '⭐', color: AC.green,  label: 'Excedente' },
  alerta:    { icon: '🔍', color: AC.orange, label: 'Alerta'    },
  fit:       { icon: '🤝', color: AC.purple, label: 'Fit/Rol'   },
}

function scoreBg(v)     { return v>=70?AC.green+'10':v>=50?AC.orange+'10':AC.red+'10' }
function scoreBorder(v) { return v>=70?AC.green+'40':v>=50?AC.orange+'40':AC.red+'40' }

function proveedorLabel(p) {
  if (!p) return 'IA local'
  if (p.startsWith('ollama/')) return `Ollama · ${p.slice(7)} · local`
  if (p === 'ollama') return 'Ollama · 100% local'
  if (p.startsWith('openai/')) return `OpenAI · ${p.slice(7)}`
  return p
}

function LabelBar({ label, value, max = 100, color, rightLabel, T }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  const c = color || scoreColor(value)
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 12, color: T.t2, flex: 1, paddingRight: 8,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'monospace', color: c, flexShrink: 0 }}>
          {rightLabel ?? `${value.toFixed(0)}%`}
        </span>
      </div>
      <div style={{ height: 5, background: T.t4, borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, borderRadius: 3,
          background: c, boxShadow: `0 0 5px ${c}55`, transition: 'width 0.6s' }}/>
      </div>
    </div>
  )
}

// ─── Modal Historial ──────────────────────────────────────────────────────────
function ModalHistorial({ candidatoId, nombre, T, onClose }) {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(`/cvs/${candidatoId}/historial`)
      .then(r => setData(r.data))
      .catch(() => toast.error('Error cargando historial.'))
      .finally(() => setLoading(false))
  }, [candidatoId])

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.55)',
      ...blur(8),
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()}
        style={{
          width: '90%', maxWidth: 560, borderRadius: 20,
          background: T.sidebarBg, border: `1px solid ${T.glassBorder}`,
          boxShadow: T.shadow, padding: '24px 22px',
          ...blur(30),
        }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.t1 }}>Historial del candidato</div>
            <div style={{ fontSize: 12, color: T.t3 }}>{nombre}</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none',
            cursor: 'pointer', fontSize: 18, color: T.t3 }}>✕</button>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
            <LGSpinner />
          </div>
        ) : !data || data.total_procesos <= 1 ? (
          <div style={{ textAlign: 'center', padding: '28px 0', color: T.t3, fontSize: 13 }}>
            <div style={{ fontSize: 32, marginBottom: 10 }}>🔍</div>
            Primera vez que este candidato aparece en el sistema.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.historial.map((h, i) => (
              <div key={i}
                onClick={() => { if (!h.es_actual) navigate(`/resultados/${h.proceso_id}/candidato/${h.candidato_id}`) }}
                style={{
                  padding: '12px 14px', borderRadius: 12,
                  border: `1px solid ${h.es_actual ? AC.blue + '40' : T.glassBorder}`,
                  background: h.es_actual ? AC.blue + '0C' : T.glass,
                  cursor: h.es_actual ? 'default' : 'pointer',
                  transition: 'all 0.15s',
                  ...blur(16),
                }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: T.t1 }}>
                        {h.nombre_puesto}
                      </span>
                      {h.es_actual && <LGBadge color={AC.blue}>Actual</LGBadge>}
                    </div>
                    <div style={{ fontSize: 11, color: T.t3 }}>
                      {h.creado_en ? new Date(h.creado_en).toLocaleDateString('es', {year:'numeric',month:'short',day:'numeric'}) : '—'}
                    </div>
                    {h.resumen && (
                      <div style={{ fontSize: 11, color: T.t2, marginTop: 5, lineHeight: 1.4,
                        overflow: 'hidden', textOverflow: 'ellipsis',
                        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                        {h.resumen}
                      </div>
                    )}
                  </div>
                  {h.puntaje != null && (
                    <div style={{ textAlign: 'center', flexShrink: 0, marginLeft: 12 }}>
                      <div style={{ fontSize: 20, fontWeight: 900, fontFamily: 'monospace',
                        color: scoreColor(h.puntaje) }}>
                        {h.puntaje.toFixed(0)}%
                      </div>
                      <div style={{ fontSize: 9, color: T.t3 }}>puntaje</div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────
export default function DetalleCandidato() {
  const { procesoId, candidatoId } = useParams()
  const navigate = useNavigate()
  const theme    = useTheme()
  const { T }    = theme || {}

  if (!T) return null

  const [data,       setData]       = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [reanalizar, setReanalizar] = useState(false)
  const [progreso,   setProgreso]   = useState(null)
  const [showHistorial, setShowHistorial] = useState(false)

  const cargar = () => {
    setLoading(true)
    procesoService.ranking(procesoId)
      .then(({ data: r }) => {
        const item = r.items.find(i => String(i.candidato.id) === String(candidatoId))
        if (!item) toast.error('Candidato no encontrado.')
        setData(item)
      })
      .catch(() => toast.error('Error cargando detalle.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [procesoId, candidatoId])

  const handleReanalizar = async () => {
    if (!window.confirm(`¿Re-analizar el CV de ${data?.candidato?.nombre}?\nSe reemplazará el análisis actual.`)) return
    setReanalizar(true)
    setProgreso('Iniciando…')
    try {
      await api.post(`/cvs/${candidatoId}/reanalizar`)
      const poll = setInterval(async () => {
        try {
          const { data: r } = await procesoService.ranking(procesoId)
          const item  = r.items.find(i => String(i.candidato.id) === String(candidatoId))
          const estado = item?.analisis?.estado
          const msg    = item?.analisis?.progress_msg || ''
          const match  = msg.match(/\[PROG:(\d+)\]\s*(.*)/)
          if (match) setProgreso(`${match[1]}% — ${match[2]}`)
          if (estado === 'completado' || estado === 'error') {
            clearInterval(poll)
            setReanalizar(false)
            setProgreso(null)
            setData(item)
            if (estado === 'completado') toast.success('Re-análisis completado.')
            else toast.error('Error en el re-análisis.')
          }
        } catch { /* continuar */ }
      }, 2500)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al iniciar re-análisis.')
      setReanalizar(false)
      setProgreso(null)
    }
  }

  if (loading) return (
    <AppLayout>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <LGSpinner size={32} />
      </div>
    </AppLayout>
  )
  if (!data) return (
    <AppLayout><p style={{ color: T.t3, padding: 16 }}>Candidato no encontrado.</p></AppLayout>
  )

  const { candidato, analisis, posicion } = data
  const criterios    = (analisis?.detalle_json || []).filter(c => c.criterio?.trim())
  const alertas      = analisis?.alertas_json   || []
  const preguntas    = analisis?.preguntas_json || []
  const tienePeso    = criterios.length > 0 && criterios[0].peso != null
  const esDatoViejo  = !tienePeso && criterios.length > 0 &&
    criterios.every(c => (c.puntaje || 0) <= Math.ceil(100 / criterios.length) + 5)
  const _puntajeDesde = c => c === 'si' ? 90 : c === 'parcial' ? 55 : 15

  const criteriosConAporte = criterios.map(c => {
    const peso    = tienePeso ? (c.peso || 0) : (100 / criterios.length)
    const puntaje = esDatoViejo ? _puntajeDesde(c.cumple) : (c.puntaje || 0)
    return { ...c, peso, puntaje, aporte: parseFloat((peso * puntaje / 100).toFixed(1)) }
  })

  // Siempre calcular desde los criterios (fuente de verdad). 
  // La IA comete errores aritméticos en puntaje_total; los criterios son más confiables.
  const totalCalculado = criteriosConAporte.reduce((s, c) => s + c.aporte, 0)
  const puntajeTotal   = criteriosConAporte.length > 0
    ? parseFloat(totalCalculado.toFixed(1))
    : (analisis?.puntaje_total || 0)

  const tieneError     = analisis?.estado === 'error'
  const mensajeError   = analisis?.error_msg && !analisis.error_msg.startsWith('[PROG:')
    ? analisis.error_msg : 'El análisis de este CV falló.'

  // Nombre: usar el campo nombre, o el nombre del archivo PDF como fallback
  const getNombreDisplay = () => {
    if (candidato.nombre) return candidato.nombre
    if (candidato.archivo_pdf) {
      return candidato.archivo_pdf.split(/[/\\]/).pop().replace(/\.pdf$/i, '').replace(/[-_]/g, ' ')
    }
    return `CV #${candidato.id}`
  }
  const nombreDisplay = getNombreDisplay()

  const initials  = nombreDisplay.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase() || '?'
  const avatarBg  = `hsl(${(candidato.id * 47) % 360}, 55%, ${T.id === 'dark' ? '42%' : '48%'})`
  const esApto        = puntajeTotal >= 70
  const esAptoParcial = puntajeTotal >= 50 && puntajeTotal < 70
  const veredictoColor = scoreColor(puntajeTotal)
  const veredictoLabel = esApto ? 'APTO PARA EL PUESTO' : esAptoParcial ? 'APTO CON RESERVAS' : 'NO APTO PARA EL PUESTO'
  const veredictoIcon  = esApto ? '✅' : esAptoParcial ? '⚠️' : '❌'
  const sorted = criteriosConAporte.length >= 2 ? [...criteriosConAporte].sort((a,b)=>b.puntaje-a.puntaje) : []
  const mejor  = sorted[0]
  const peor   = sorted[sorted.length - 1]

  const alertasAltas = alertas.filter(a => a.nivel === 'alta')

  return (
    <AppLayout>
      <PageContainer size="lg">
        {/* ── Breadcrumb + historial ── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <BackButton onClick={() => navigate(`/resultados/${procesoId}`)}>← Volver al ranking</BackButton>
          <ActionButton color={AC.teal} onClick={() => setShowHistorial(true)} style={{ marginBottom: 16 }}>
            📋 Ver historial
          </ActionButton>
        </div>

        {/* ── Banner re-análisis ── */}
        {reanalizar && (
          <GlassCard tint={AC.blue} style={{ padding: '14px 18px', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <LGSpinner size={20} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: T.t1 }}>Re-análisis en curso…</div>
                <div style={{ fontSize: 11, color: T.t2, marginTop: 2 }}>{progreso}</div>
              </div>
            </div>
          </GlassCard>
        )}

        {/* ── Banner error ── */}
        {tieneError && !reanalizar && (
          <GlassCard tint={AC.red} style={{ padding: '14px 18px', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 22 }}>⚠️</span>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: AC.red }}>Análisis con error</div>
                <div style={{ fontSize: 11, color: T.t2, marginTop: 2 }}>{mensajeError}</div>
              </div>
            </div>
          </GlassCard>
        )}

        {/* ── Alertas altas al tope ── */}
        {alertasAltas.length > 0 && (
          <GlassCard tint={AC.red} style={{ padding: '12px 16px', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 16 }}>🚨</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: AC.red }}>
                {alertasAltas.length} alerta{alertasAltas.length > 1 ? 's' : ''} de prioridad alta detectada{alertasAltas.length > 1 ? 's' : ''}
              </span>
            </div>
            {alertasAltas.map((a, i) => (
              <div key={i} style={{ fontSize: 12, color: T.t2, marginLeft: 26, marginBottom: 2 }}>
                {ALERTA_CFG[a.tipo]?.icon || '⚠️'} {a.descripcion}
              </div>
            ))}
          </GlassCard>
        )}

        {/* ── Aviso datos viejos ── */}
        {esDatoViejo && (
          <GlassCard tint={AC.orange} style={{ padding: '12px 16px', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span>⚡</span>
              <p style={{ margin: 0, fontSize: 12, color: T.t2 }}>
                Análisis anterior — porcentajes estimados.{' '}
                <strong style={{ color: T.t1 }}>Re-analizá para obtener alertas y preguntas.</strong>
              </p>
            </div>
          </GlassCard>
        )}

        {/* ── Header candidato ── */}
        <GlassCard style={{ padding: '20px 22px', marginBottom: 14, borderColor: scoreBorder(puntajeTotal) }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
            <div style={{ width: 60, height: 60, borderRadius: '50%', flexShrink: 0,
              background: avatarBg, color: 'white',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20, fontWeight: 700 }}>
              {initials}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: T.t1, marginBottom: 6 }}>
                {nombreDisplay}
              </div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                {candidato.email    && <span style={{ fontSize: 13, color: T.t2 }}>📧 {candidato.email}</span>}
                {candidato.telefono && <span style={{ fontSize: 13, color: T.t2 }}>📞 {candidato.telefono}</span>}
                <LGBadge color={AC.purple}>🏆 Puesto #{posicion}</LGBadge>
                {alertas.length > 0 && (
                  <LGBadge color={alertasAltas.length > 0 ? AC.red : AC.orange}>
                    {alertasAltas.length > 0 ? '🚨' : '⚠️'} {alertas.length} alerta{alertas.length > 1 ? 's' : ''}
                  </LGBadge>
                )}
              </div>
            </div>
            <div style={{ textAlign: 'center', flexShrink: 0 }}>
              <div style={{ fontSize: 38, fontWeight: 900, fontFamily: 'monospace',
                color: veredictoColor, lineHeight: 1, textShadow: `0 0 20px ${veredictoColor}44` }}>
                {puntajeTotal.toFixed(1)}%
              </div>
              <div style={{ fontSize: 10, color: T.t3, marginTop: 4 }}>Compatibilidad</div>
            </div>
          </div>
        </GlassCard>

        {/* ── Veredicto ── */}
        <GlassCard tint={veredictoColor}
          style={{ padding: '14px 20px', marginBottom: 14, background: scoreBg(puntajeTotal) }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 26, flexShrink: 0 }}>{veredictoIcon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 800, color: veredictoColor }}>{veredictoLabel}</div>
              {analisis?.resumen_ia && (
                <p style={{ margin: '5px 0 0', fontSize: 13, color: T.t2, lineHeight: 1.6 }}>
                  {analisis.resumen_ia}
                </p>
              )}
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: 10, color: T.t3, marginBottom: 3 }}>Modelo IA</div>
              <div style={{ fontSize: 11, fontWeight: 700, color: AC.teal }}>
                {proveedorLabel(analisis?.proveedor_ia)}
              </div>
              <div style={{ marginTop: 10 }}>
                <ActionButton color={AC.orange} disabled={reanalizar} onClick={handleReanalizar}>
                  ↺ Re-analizar
                </ActionButton>
              </div>
            </div>
          </div>
        </GlassCard>

        {/* ── Grid principal ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: 14, alignItems: 'start' }}>

          {/* ── Columna izquierda ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* Evaluación por requisito */}
            <div>
              <SectionLabel>✅ Evaluación por requisito</SectionLabel>
              <GlassCard style={{ padding: '14px 16px' }}>
                {criterios.length === 0
                  ? <p style={{ fontSize: 13, color: T.t3 }}>Sin criterios disponibles.</p>
                  : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {criteriosConAporte.map((c, i) => {
                        const cfg = CUMPLE_CFG[c.cumple] || CUMPLE_CFG.no
                        return (
                          <div key={i} style={{ borderRadius: 12, overflow: 'hidden', border: `1px solid ${cfg.border}` }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                              padding: '9px 13px', background: cfg.bg }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span style={{ fontSize: 15 }}>{cfg.icon}</span>
                                <span style={{ fontSize: 13, fontWeight: 600, color: T.t1 }}>{c.criterio}</span>
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                                {tienePeso && <span style={{ fontSize: 10, color: T.t3 }}>peso {c.peso}%</span>}
                                <span style={{ fontSize: 11, fontWeight: 700, color: cfg.color }}>{cfg.label}</span>
                              </div>
                            </div>
                            <div style={{ padding: '11px 13px', background: T.id === 'claude' ? T.glassHover : 'rgba(0,0,0,0.18)' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                                <span style={{ fontSize: 11, color: T.t3 }}>Cumplimiento</span>
                                <span style={{ fontSize: 13, fontWeight: 800, fontFamily: 'monospace',
                                  color: scoreColor(c.puntaje) }}>{c.puntaje?.toFixed(0)}%</span>
                              </div>
                              <div style={{ height: 5, background: T.t4, borderRadius: 3, overflow: 'hidden', marginBottom: 7 }}>
                                <div style={{ height: '100%', width: `${c.puntaje||0}%`, borderRadius: 3,
                                  background: scoreColor(c.puntaje), boxShadow: `0 0 5px ${scoreColor(c.puntaje)}55`,
                                  transition: 'width 0.6s' }}/>
                              </div>
                              {c.descripcion && (
                                <p style={{ margin: '0 0 5px', fontSize: 12, color: T.t2, lineHeight: 1.55 }}>
                                  {c.descripcion}
                                </p>
                              )}
                              {tienePeso && (
                                <div style={{ fontSize: 11, color: T.t3 }}>
                                  Aporte: <span style={{ fontWeight: 700, color: T.t2 }}>{c.aporte.toFixed(1)} pts</span>
                                  {' '}({c.peso}% × {c.puntaje?.toFixed(0)}%)
                                </div>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
              </GlassCard>
            </div>

            {/* Cálculo del puntaje */}
            {tienePeso && criteriosConAporte.length > 0 && (
              <div>
                <SectionLabel>🧮 Cálculo del puntaje total</SectionLabel>
                <GlassCard tint={AC.teal} style={{ padding: '13px 16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 1, marginBottom: 10 }}>
                    {criteriosConAporte.map((c, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center',
                        justifyContent: 'space-between', padding: '5px 0',
                        borderBottom: `1px solid ${T.divider}`, fontSize: 12 }}>
                        <span style={{ color: T.t2, flex: 1, paddingRight: 8,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.criterio}</span>
                        <span style={{ color: T.t3, flexShrink: 0, fontFamily: 'monospace', fontSize: 11 }}>
                          {c.peso}% × {c.puntaje?.toFixed(0)}% =
                        </span>
                        <span style={{ fontWeight: 800, fontFamily: 'monospace', marginLeft: 8,
                          width: 44, textAlign: 'right', flexShrink: 0, color: scoreColor(c.puntaje) }}>
                          {c.aporte.toFixed(1)}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    paddingTop: 8, borderTop: `2px solid ${AC.teal}33` }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: T.t1 }}>Total</span>
                    <span style={{ fontSize: 22, fontWeight: 900, fontFamily: 'monospace',
                      color: veredictoColor }}>{totalCalculado.toFixed(1)}%</span>
                  </div>
                </GlassCard>
              </div>
            )}

            {/* ── Alertas ── */}
            {alertas.length > 0 && (
              <div>
                <SectionLabel>🚨 Alertas detectadas en el CV</SectionLabel>
                <GlassCard style={{ padding: '13px 16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {alertas.map((a, i) => {
                      const aCfg = ALERTA_CFG[a.tipo] || ALERTA_CFG.verificar
                      const nCfg = NIVEL_CFG[a.nivel] || NIVEL_CFG.media
                      return (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'flex-start', gap: 10,
                          padding: '10px 12px', borderRadius: 11,
                          background: aCfg.color + '0C',
                          border: `1px solid ${aCfg.color}25`,
                        }}>
                          <span style={{ fontSize: 17, flexShrink: 0, marginTop: 1 }}>{aCfg.icon}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                              <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                                letterSpacing: 0.8, color: aCfg.color }}>{a.tipo}</span>
                              <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4,
                                background: nCfg.color + '20', color: nCfg.color, fontWeight: 600 }}>
                                {nCfg.label}
                              </span>
                            </div>
                            <div style={{ fontSize: 12, color: T.t2, lineHeight: 1.5 }}>{a.descripcion}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  {alertas.length === 0 && (
                    <div style={{ fontSize: 12, color: T.t3, textAlign: 'center', padding: '12px 0' }}>
                      ✅ Sin alertas detectadas
                    </div>
                  )}
                </GlassCard>
              </div>
            )}
          </div>

          {/* ── Columna derecha ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* Compatibilidad */}
            {criteriosConAporte.length > 0 && (
              <div>
                <SectionLabel>📊 Compatibilidad por criterio</SectionLabel>
                <GlassCard style={{ padding: '13px 16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
                    {criteriosConAporte.map((c, i) => (
                      <div key={i}>
                        <LabelBar label={c.criterio} value={c.puntaje||0} color={scoreColor(c.puntaje)} T={T}/>
                        {tienePeso && <div style={{ fontSize: 10, color: T.t3, marginTop: 3 }}>Peso: {c.peso}%</div>}
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap',
                    marginTop: 12, paddingTop: 10, borderTop: `1px solid ${T.divider}` }}>
                    {[[AC.green,'≥70% Cumple'],[AC.orange,'50-69% Parcial'],[AC.red,'<50% No cumple']].map(([c,l]) => (
                      <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: c }}/>
                        <span style={{ fontSize: 10, color: T.t3 }}>{l}</span>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              </div>
            )}

            {/* Resumen estadístico */}
            {criteriosConAporte.length > 0 && (() => {
              const sorted2 = criteriosConAporte.length>=2 ? [...criteriosConAporte].sort((a,b)=>b.puntaje-a.puntaje) : []
              return (
                <div>
                  <SectionLabel>📈 Resumen estadístico</SectionLabel>
                  <GlassCard style={{ padding: '13px 16px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8, marginBottom: 12 }}>
                      {[
                        {label:'Cumple',   val:criteriosConAporte.filter(c=>c.cumple==='si').length,      color:AC.green },
                        {label:'Parcial',  val:criteriosConAporte.filter(c=>c.cumple==='parcial').length, color:AC.orange},
                        {label:'No cumple',val:criteriosConAporte.filter(c=>c.cumple==='no').length,      color:AC.red   },
                      ].map(s => (
                        <div key={s.label} style={{ padding: '10px 6px', borderRadius: 10, textAlign: 'center',
                          background: s.color+'12', border: `1px solid ${s.color}25` }}>
                          <div style={{ fontSize: 24, fontWeight: 900, color: s.color }}>{s.val}</div>
                          <div style={{ fontSize: 10, color: T.t3, marginTop: 1 }}>{s.label}</div>
                        </div>
                      ))}
                    </div>
                    {sorted2.length >= 2 && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {[
                          { icon: '💪', label: 'Punto más fuerte', item: sorted2[0], color: AC.green },
                          { icon: sorted2[sorted2.length-1].puntaje>=70?'📊':'📌',
                            label: sorted2[sorted2.length-1].puntaje>=70?'Punto más bajo':'Brecha principal',
                            item: sorted2[sorted2.length-1], color: scoreColor(sorted2[sorted2.length-1].puntaje) },
                        ].map(({icon,label,item,color}) => (
                          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10,
                            padding: '9px 11px', borderRadius: 10,
                            background: color+'0C', border: `1px solid ${color}25` }}>
                            <span style={{ fontSize: 17 }}>{icon}</span>
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontSize: 10, color: T.t3 }}>{label}</div>
                              <div style={{ fontSize: 12, fontWeight: 600, color: T.t1,
                                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.criterio}</div>
                            </div>
                            <span style={{ fontSize: 13, fontWeight: 800, fontFamily: 'monospace', color, flexShrink: 0 }}>
                              {item.puntaje?.toFixed(0)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </GlassCard>
                </div>
              )
            })()}

            {/* Aporte de criterios */}
            {tienePeso && criteriosConAporte.length > 0 && (
              <div>
                <SectionLabel>🎯 Aporte al puntaje total</SectionLabel>
                <GlassCard style={{ padding: '13px 16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
                    {[...criteriosConAporte].sort((a,b)=>b.aporte-a.aporte).map((c,i) => (
                      <LabelBar key={i} label={c.criterio} value={c.aporte} max={c.peso}
                        color={scoreColor(c.puntaje)} rightLabel={`${c.aporte.toFixed(1)}/${c.peso}pts`} T={T}/>
                    ))}
                  </div>
                </GlassCard>
              </div>
            )}

            {/* ── Preguntas de entrevista ── */}
            {preguntas.length > 0 && (
              <div>
                <SectionLabel>💬 Preguntas para la entrevista</SectionLabel>
                <GlassCard style={{ padding: '13px 16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {preguntas.map((p, i) => {
                      const pCfg = PREGUNTA_CFG[p.categoria] || PREGUNTA_CFG.brecha
                      return (
                        <div key={i} style={{
                          padding: '11px 13px', borderRadius: 12,
                          background: pCfg.color + '0C', border: `1px solid ${pCfg.color}28`,
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5 }}>
                            <span style={{ fontSize: 14 }}>{pCfg.icon}</span>
                            <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
                              letterSpacing: 0.8, color: pCfg.color }}>{pCfg.label}</span>
                          </div>
                          <div style={{ fontSize: 13, fontWeight: 500, color: T.t1, lineHeight: 1.55, marginBottom: 5 }}>
                            {p.pregunta}
                          </div>
                          {p.objetivo && (
                            <div style={{ fontSize: 11, color: T.t3 }}>
                              🎯 Objetivo: {p.objetivo}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </GlassCard>
              </div>
            )}

          </div>
        </div>
      </PageContainer>

      {/* ── Modal Historial ── */}
      {showHistorial && (
        <ModalHistorial
          candidatoId={candidatoId}
          nombre={nombreDisplay}
          T={T}
          onClose={() => setShowHistorial(false)}
        />
      )}
    </AppLayout>
  )
}