import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { procesoService, reportesService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { useTheme } from '../components/lg/ThemeContext'
import { GlassCard, ScoreRing, ScoreBar, LGSpinner, LGEmpty, ActionButton, PrimaryButton, BackButton, SectionLabel, LGBadge } from '../components/lg/components'
import { AC, scoreColor, blur } from '../components/lg/theme'
import toast from 'react-hot-toast'

const MEDALLAS   = ['🥇', '🥈', '🥉']
const ACCENT_POS = [AC.yellow, '#94A3B8', '#CD7F32']

// ─── Vista comparación cara a cara ────────────────────────────────────────────
function VistaComparacion({ seleccion, ranking, T, onCerrar }) {
  const items = seleccion.map(id => ranking.find(r => r.candidato.id === id)).filter(Boolean)
  if (items.length !== 2) return null

  const [a, b] = items

  // Unificar criterios por nombre
  const cA = a.analisis?.detalle_json || []
  const cB = b.analisis?.detalle_json || []
  const todosNombres = [...new Set([...cA.map(c=>c.criterio), ...cB.map(c=>c.criterio)])]

  const getC = (lista, nombre) => lista.find(c => c.criterio === nombre)

  function Cabecera({ item, color }) {
    const puntaje = item.analisis?.puntaje_total
    const initials = (item.candidato.nombre || '?').split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase()
    const avatarBg = `hsl(${(item.candidato.id * 47) % 360}, 55%, 44%)`
    return (
      <div style={{ textAlign: 'center', padding: '16px 12px', borderBottom: `1px solid ${T.divider}` }}>
        <div style={{ width: 52, height: 52, borderRadius: '50%', margin: '0 auto 10px',
          background: avatarBg, color: 'white',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 17, fontWeight: 700,
          border: `3px solid ${color}40` }}>
          {initials}
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.t1, marginBottom: 4 }}>
          {item.candidato.nombre || `CV #${item.candidato.id}`}
        </div>
        <div style={{ fontSize: 28, fontWeight: 900, fontFamily: 'monospace', color: scoreColor(puntaje||0) }}>
          {puntaje?.toFixed(1) ?? '—'}%
        </div>
        <div style={{ fontSize: 10, color: T.t3 }}>Puesto #{item.posicion}</div>
      </div>
    )
  }

  return (
    <div style={{ marginTop: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <SectionLabel>⚔️ Comparación cara a cara</SectionLabel>
        <ActionButton color={T.t3} onClick={onCerrar} style={{ fontSize: 11, padding: '5px 12px' }}>
          ✕ Cerrar comparación
        </ActionButton>
      </div>

      <GlassCard style={{ overflow: 'hidden' }}>
        {/* Cabeceras */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px 1fr' }}>
          <Cabecera item={a} color={AC.blue} />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 20, color: T.t3, borderBottom: `1px solid ${T.divider}` }}>
            VS
          </div>
          <Cabecera item={b} color={AC.purple} />
        </div>

        {/* Puntaje total */}
        <FilaComparacion
          labelA={`${a.analisis?.puntaje_total?.toFixed(1) ?? '—'}%`}
          labelCentro="Puntaje total"
          labelB={`${b.analisis?.puntaje_total?.toFixed(1) ?? '—'}%`}
          colorA={scoreColor(a.analisis?.puntaje_total || 0)}
          colorB={scoreColor(b.analisis?.puntaje_total || 0)}
          winner={
            (a.analisis?.puntaje_total||0) > (b.analisis?.puntaje_total||0) ? 'a' :
            (b.analisis?.puntaje_total||0) > (a.analisis?.puntaje_total||0) ? 'b' : null
          }
          T={T} bold
        />

        {/* Criterios */}
        {todosNombres.map((nombre, i) => {
          const cA_ = getC(cA, nombre)
          const cB_ = getC(cB, nombre)
          const pA = cA_?.puntaje ?? null
          const pB = cB_?.puntaje ?? null
          const winner = pA != null && pB != null ? (pA > pB ? 'a' : pB > pA ? 'b' : null) : null
          return (
            <FilaComparacion key={i}
              labelA={pA != null ? `${pA.toFixed(0)}%` : '—'}
              labelCentro={nombre}
              labelB={pB != null ? `${pB.toFixed(0)}%` : '—'}
              colorA={pA != null ? scoreColor(pA) : T.t4}
              colorB={pB != null ? scoreColor(pB) : T.t4}
              winner={winner}
              subA={cA_?.cumple}
              subB={cB_?.cumple}
              barA={pA}
              barB={pB}
              T={T}
            />
          )
        })}

        {/* Alertas */}
        <FilaComparacion
          labelA={`${(a.analisis?.alertas_json||[]).length} alerta${(a.analisis?.alertas_json||[]).length !== 1 ? 's' : ''}`}
          labelCentro="Alertas detectadas"
          labelB={`${(b.analisis?.alertas_json||[]).length} alerta${(b.analisis?.alertas_json||[]).length !== 1 ? 's' : ''}`}
          colorA={(a.analisis?.alertas_json||[]).length > 0 ? AC.orange : AC.green}
          colorB={(b.analisis?.alertas_json||[]).length > 0 ? AC.orange : AC.green}
          winner={
            (a.analisis?.alertas_json||[]).length < (b.analisis?.alertas_json||[]).length ? 'a' :
            (b.analisis?.alertas_json||[]).length < (a.analisis?.alertas_json||[]).length ? 'b' : null
          }
          T={T}
        />

        {/* Veredicto */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
          padding: '14px 16px', gap: 10, background: T.t4 }}>
          {[a, b].map((item, idx) => {
            const p = item.analisis?.puntaje_total || 0
            const esApto = p >= 70, esParcial = p >= 50 && p < 70
            const vColor = scoreColor(p)
            const vLabel = esApto ? 'APTO' : esParcial ? 'CON RESERVAS' : 'NO APTO'
            const vIcon  = esApto ? '✅' : esParcial ? '⚠️' : '❌'
            return (
              <div key={idx} style={{ textAlign: 'center', padding: '10px',
                borderRadius: 10, background: vColor + '15', border: `1px solid ${vColor}30` }}>
                <div style={{ fontSize: 20, marginBottom: 4 }}>{vIcon}</div>
                <div style={{ fontSize: 12, fontWeight: 800, color: vColor }}>{vLabel}</div>
              </div>
            )
          })}
        </div>
      </GlassCard>
    </div>
  )
}

const CUMPLE_ICON = { si: '✅', parcial: '⚠️', no: '❌' }

function FilaComparacion({ labelA, labelCentro, labelB, colorA, colorB, winner, subA, subB, barA, barB, T, bold }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px 1fr',
      borderBottom: `1px solid ${T.divider}` }}>
      {/* Candidato A */}
      <div style={{ padding: '10px 14px',
        background: winner === 'a' ? colorA + '0D' : 'transparent',
        borderRight: `1px solid ${T.divider}` }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
          {winner === 'a' && <span style={{ fontSize: 12 }}>⭐</span>}
          <span style={{ fontSize: bold ? 16 : 14, fontWeight: bold ? 800 : 600,
            fontFamily: 'monospace', color: colorA }}>{labelA}</span>
          {subA && <span style={{ fontSize: 13 }}>{CUMPLE_ICON[subA]}</span>}
        </div>
        {barA != null && (
          <div style={{ height: 4, background: T.t4, borderRadius: 2, overflow: 'hidden', marginTop: 5 }}>
            <div style={{ height:'100%', width:`${barA}%`, background: colorA, borderRadius: 2, transition:'width 0.5s' }}/>
          </div>
        )}
      </div>

      {/* Centro */}
      <div style={{ padding: '10px 6px', textAlign: 'center',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        borderRight: `1px solid ${T.divider}` }}>
        <span style={{ fontSize: 11, color: T.t2, fontWeight: bold ? 700 : 400, lineHeight: 1.3 }}>
          {labelCentro}
        </span>
      </div>

      {/* Candidato B */}
      <div style={{ padding: '10px 14px',
        background: winner === 'b' ? colorB + '0D' : 'transparent' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {subB && <span style={{ fontSize: 13 }}>{CUMPLE_ICON[subB]}</span>}
          <span style={{ fontSize: bold ? 16 : 14, fontWeight: bold ? 800 : 600,
            fontFamily: 'monospace', color: colorB }}>{labelB}</span>
          {winner === 'b' && <span style={{ fontSize: 12 }}>⭐</span>}
        </div>
        {barB != null && (
          <div style={{ height: 4, background: T.t4, borderRadius: 2, overflow: 'hidden', marginTop: 5 }}>
            <div style={{ height:'100%', width:`${barB}%`, background: colorB, borderRadius: 2, transition:'width 0.5s' }}/>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────
export default function Resultados() {
  const { procesoId } = useParams()
  const navigate      = useNavigate()
  const theme         = useTheme()
  const { T }         = theme || {}

  if (!T) return null

  const [proceso,    setProceso]    = useState(null)
  const [ranking,    setRanking]    = useState([])
  const [loading,    setLoading]    = useState(true)
  const [exporting,  setExport]     = useState(false)
  const [modoComp,   setModoComp]   = useState(false)   // modo comparación activo
  const [seleccion,  setSeleccion]  = useState([])       // IDs seleccionados (máx 2)

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
      // data ya es Blob (responseType: 'blob' en el servicio)
      const blob = data instanceof Blob
        ? data
        : new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
      const url  = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href  = url
      link.download = `Ranking_${proceso?.nombre_puesto?.replace(/ /g, '_') || 'export'}.xlsx`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      toast.success('Excel descargado.')
    } catch {
      toast.error('Error exportando Excel.')
    } finally {
      setExport(false)
    }
  }

  const toggleSeleccion = (id) => {
    setSeleccion(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id)
      if (prev.length >= 2) { toast('Seleccioná solo 2 candidatos para comparar.', { icon: 'ℹ️' }); return prev }
      return [...prev, id]
    })
  }

  const activarComparacion = () => {
    setModoComp(true)
    setSeleccion([])
  }

  const cerrarComparacion = () => {
    setModoComp(false)
    setSeleccion([])
  }

  if (loading) return (
    <AppLayout>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <LGSpinner size={32} />
      </div>
    </AppLayout>
  )

  const comparacionLista = modoComp && seleccion.length === 2

  return (
    <AppLayout>
      <BackButton onClick={() => navigate('/dashboard')}>← Dashboard</BackButton>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
        marginBottom: 20, flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: T.t1 }}>
            {proceso?.nombre_puesto}
          </h1>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: T.t2 }}>
            {ranking.length} candidato{ranking.length !== 1 ? 's' : ''} · Ordenados por compatibilidad
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {!modoComp ? (
            <ActionButton color={AC.purple} onClick={activarComparacion} style={{ padding: '9px 18px' }}>
              ⚔️ Comparar candidatos
            </ActionButton>
          ) : (
            <ActionButton color={T.t3} onClick={cerrarComparacion} style={{ padding: '9px 18px' }}>
              ✕ Cancelar comparación
            </ActionButton>
          )}
          <ActionButton color={AC.teal} disabled={exporting} onClick={handleExport} style={{ padding: '9px 18px' }}>
            {exporting ? <LGSpinner size={14} /> : '📥'} Exportar Excel
          </ActionButton>
        </div>
      </div>

      {/* ── Banner modo comparación ── */}
      {modoComp && (
        <GlassCard tint={AC.purple} style={{ padding: '12px 16px', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 18 }}>⚔️</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.t1 }}>
                Modo comparación — seleccioná 2 candidatos
              </div>
              <div style={{ fontSize: 11, color: T.t2 }}>
                {seleccion.length === 0 && 'Hacé clic en dos candidatos del ranking para compararlos.'}
                {seleccion.length === 1 && `1 seleccionado — elegí uno más.`}
                {seleccion.length === 2 && `✅ 2 seleccionados — la comparación aparece abajo.`}
              </div>
            </div>
            {seleccion.length === 2 && (
              <ActionButton color={AC.purple} onClick={() => setSeleccion([])}>
                Cambiar selección
              </ActionButton>
            )}
          </div>
        </GlassCard>
      )}

      {/* ── Ranking ── */}
      {ranking.length === 0 ? (
        <GlassCard>
          <LGEmpty icon="⏳" title="Sin resultados aún"
            desc="El análisis puede estar en proceso. Esperá unos segundos y recargá." />
        </GlassCard>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {ranking.map((item) => {
            const puntaje   = item.analisis?.puntaje_total
            const pos       = item.posicion
            const id        = item.candidato.id
            const esSel     = seleccion.includes(id)
            const alertas   = item.analisis?.alertas_json || []
            const alertasAltas = alertas.filter(a => a.nivel === 'alta')
            const avatarBg  = `hsl(${(id * 47) % 360}, 55%, ${T.id === 'dark' ? '42%' : '48%'})`

            const handleClick = () => {
              if (modoComp) { toggleSeleccion(id); return }
              navigate(`/resultados/${procesoId}/candidato/${id}`)
            }

            return (
              <GlassCard
                key={id}
                onClick={handleClick}
                style={{
                  padding: '14px 18px',
                  borderLeft: pos <= 3 ? `3px solid ${ACCENT_POS[pos - 1]}` : undefined,
                  outline: esSel ? `2px solid ${AC.purple}` : 'none',
                  outlineOffset: 2,
                  background: esSel ? AC.purple + '0D' : undefined,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>

                  {/* Posición / checkbox comparación */}
                  <div style={{ width: 36, textAlign: 'center', flexShrink: 0 }}>
                    {modoComp ? (
                      <div style={{
                        width: 24, height: 24, borderRadius: 7, margin: '0 auto',
                        border: `2px solid ${esSel ? AC.purple : T.glassBorder}`,
                        background: esSel ? AC.purple : 'transparent',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 13, color: 'white',
                        ...blur(8),
                      }}>
                        {esSel ? '✓' : ''}
                      </div>
                    ) : pos <= 3 ? (
                      <span style={{ fontSize: 22 }}>{MEDALLAS[pos - 1]}</span>
                    ) : (
                      <span style={{ fontSize: 15, fontWeight: 700, color: T.t3 }}>#{pos}</span>
                    )}
                  </div>

                  {/* Avatar */}
                  <div style={{ width: 42, height: 42, borderRadius: '50%', flexShrink: 0,
                    background: avatarBg, color: 'white',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14, fontWeight: 700 }}>
                    {(item.candidato.nombre || '?').split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase()}
                  </div>

                  {/* Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3, flexWrap: 'wrap' }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: T.t1 }}>
                        {item.candidato.nombre || `CV #${id}`}
                      </div>
                      {alertasAltas.length > 0 && (
                        <LGBadge color={AC.red}>🚨 {alertasAltas.length} alerta{alertasAltas.length>1?'s':''}</LGBadge>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {item.candidato.email    && <span style={{ fontSize: 11, color: T.t3 }}>📧 {item.candidato.email}</span>}
                      {item.candidato.telefono && <span style={{ fontSize: 11, color: T.t3 }}>📞 {item.candidato.telefono}</span>}
                    </div>
                    {puntaje != null && (
                      <div style={{ marginTop: 7 }}>
                        <ScoreBar value={puntaje} height={4} />
                      </div>
                    )}
                  </div>

                  {/* Puntaje */}
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <ScoreRing score={puntaje != null ? Math.round(puntaje) : null} size={46} />
                    <div style={{ fontSize: 10, color: T.t3, marginTop: 3 }}>compatibilidad</div>
                  </div>

                  {!modoComp && <span style={{ fontSize: 18, color: T.t3 }}>›</span>}
                </div>
              </GlassCard>
            )
          })}
        </div>
      )}

      {/* ── Vista comparación ── */}
      {comparacionLista && (
        <VistaComparacion
          seleccion={seleccion}
          ranking={ranking}
          T={T}
          onCerrar={cerrarComparacion}
        />
      )}
    </AppLayout>
  )
}