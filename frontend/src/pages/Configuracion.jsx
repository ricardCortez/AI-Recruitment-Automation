import { useEffect, useRef, useState } from 'react'
import api from '../services/api'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Spinner } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

// ─── Catálogo de modelos con requisitos de hardware ──────────────────────────
const MODELOS = [
  {
    id: 'llama3.1:8b',
    label: 'Llama 3.1 8B',
    tag: 'Rápido',
    tagColor: '#22D3EE',
    desc: 'El más rápido. Bueno para pruebas o equipos con poca RAM.',
    ram_gb: 6, vram_gb: 5,
    ram_optima: 8, vram_optima: 6,
    ctx: 4096, tokens: 1200,
    fortalezas: ['Respuesta rápida', 'Bajo consumo RAM', 'Bueno en inglés'],
    pull: 'ollama pull llama3.1:8b',
  },
  {
    id: 'qwen2.5:7b',
    label: 'Qwen 2.5 7B',
    tag: 'Equilibrado',
    tagColor: '#4ADE80',
    desc: 'Mejor comprensión del español que Llama con el mismo hardware.',
    ram_gb: 6, vram_gb: 5,
    ram_optima: 8, vram_optima: 6,
    ctx: 4096, tokens: 1800,
    fortalezas: ['Mejor en español', 'Mismo hardware que Llama', 'JSON consistente'],
    pull: 'ollama pull qwen2.5:7b',
  },
  {
    id: 'qwen2.5:14b',
    label: 'Qwen 2.5 14B',
    tag: 'Recomendado',
    tagColor: '#A78BFA',
    desc: 'El más preciso para análisis de producción. Necesita >8GB VRAM.',
    ram_gb: 10, vram_gb: 9,
    ram_optima: 12, vram_optima: 10,
    ctx: 4096, tokens: 1200,
    fortalezas: ['Mayor precisión', 'Mejor razonamiento', 'Ideal producción'],
    pull: 'ollama pull qwen2.5:14b',
  },
]

// ─── Sub-componentes ──────────────────────────────────────────────────────────
function RamBar({ usado, total, label, color = '#22D3EE' }) {
  const pct = total > 0 ? Math.min((usado / total) * 100, 100) : 0
  const barColor = pct > 85 ? '#F87171' : pct > 65 ? '#FACC15' : color
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono font-bold" style={{ color: barColor }}>
          {usado.toFixed(1)} / {total.toFixed(1)} GB
        </span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: '#2A3A52' }}>
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: barColor }} />
      </div>
      <div className="text-xs text-slate-600 mt-1">{(total - usado).toFixed(1)} GB disponibles</div>
    </div>
  )
}

function Badge({ ok, labelOk, labelBad }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
      style={{
        background: ok ? 'rgba(74,222,128,0.1)' : 'rgba(248,113,113,0.1)',
        color: ok ? '#4ADE80' : '#F87171',
        border: `1px solid ${ok ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)'}`,
      }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: ok ? '#4ADE80' : '#F87171' }} />
      {ok ? labelOk : labelBad}
    </span>
  )
}

// Panel de compatibilidad de hardware para un modelo seleccionado
function HardwareCheck({ modelo, gpu, ram, dispositivo }) {
  if (!modelo) return null

  const m = MODELOS.find(x => x.id === modelo)
  if (!m) return null

  const ramDisp    = ram.disponible_gb || 0
  const ramTotal   = ram.total_gb || 0
  const vramDisp   = gpu.disponible && gpu.gpus?.length > 0 ? gpu.gpus[0].vram_libre / 1024 : 0
  const vramTotal  = gpu.disponible && gpu.gpus?.length > 0 ? gpu.gpus[0].vram_total / 1024 : 0

  const ramOk      = ramDisp >= m.ram_gb
  const ramOptima  = ramDisp >= m.ram_optima
  const vramOk     = vramDisp >= m.vram_gb
  const vramOptima = vramDisp >= m.vram_optima

  const cpuOk  = ramOk
  const gpuOk  = gpu.disponible && vramOk

  // Recomendacion general
  let recomendacion, recoColor, recoIcon
  if (dispositivo === 'gpu') {
    if (!gpu.disponible) {
      recoIcon = '⚠️'; recoColor = '#F87171'
      recomendacion = 'No tenés GPU NVIDIA disponible. Cambiá a CPU.'
    } else if (!vramOk) {
      recoIcon = '❌'; recoColor = '#F87171'
      recomendacion = `VRAM insuficiente: necesitás ${m.vram_gb} GB, tenés ${vramDisp.toFixed(1)} GB libres.`
    } else if (!vramOptima) {
      recoIcon = '⚠️'; recoColor = '#FACC15'
      recomendacion = `VRAM ajustada: funciona pero para optimo necesitás ${m.vram_optima} GB.`
    } else {
      recoIcon = '✅'; recoColor = '#4ADE80'
      recomendacion = 'GPU con VRAM suficiente. Rendimiento óptimo esperado.'
    }
  } else {
    if (!ramOk) {
      recoIcon = '❌'; recoColor = '#F87171'
      recomendacion = `RAM insuficiente: necesitás ${m.ram_gb} GB libres, tenés ${ramDisp.toFixed(1)} GB.`
    } else if (!ramOptima) {
      recoIcon = '⚠️'; recoColor = '#FACC15'
      recomendacion = `RAM ajustada: funciona pero puede ser lento. Para optimo: ${m.ram_optima} GB.`
    } else {
      recoIcon = '✅'; recoColor = '#4ADE80'
      recomendacion = 'RAM suficiente para CPU. Análisis estable esperado.'
    }
  }

  return (
    <div className="mt-4 rounded-xl overflow-hidden" style={{ border: `1px solid ${recoColor}33` }}>

      {/* Header recomendacion */}
      <div className="px-4 py-3 flex items-start gap-3"
        style={{ background: recoColor + '0D' }}>
        <span className="text-xl flex-shrink-0">{recoIcon}</span>
        <div>
          <div className="text-xs font-bold text-white mb-0.5">Compatibilidad con hardware actual</div>
          <div className="text-xs" style={{ color: recoColor }}>{recomendacion}</div>
        </div>
      </div>

      {/* Grilla de checks */}
      <div className="p-4 grid grid-cols-2 gap-3" style={{ background: '#111827' }}>

        {/* RAM */}
        <div className="p-3 rounded-xl" style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
          <div className="text-xs text-slate-400 mb-2">Memoria RAM</div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-white">{ramDisp.toFixed(1)} / {ramTotal.toFixed(1)} GB</span>
            <Badge ok={ramOk} labelOk="OK" labelBad="Insuf." />
          </div>
          <div className="text-xs text-slate-500">
            Mínimo: <span style={{ color: ramOk ? '#4ADE80' : '#F87171' }}>{m.ram_gb} GB</span>
            {' · '}Óptimo: <span style={{ color: ramOptima ? '#4ADE80' : '#FACC15' }}>{m.ram_optima} GB</span>
          </div>
        </div>

        {/* VRAM */}
        <div className="p-3 rounded-xl" style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
          <div className="text-xs text-slate-400 mb-2">VRAM (GPU)</div>
          {gpu.disponible ? (
            <>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono text-white">{vramDisp.toFixed(1)} / {vramTotal.toFixed(1)} GB</span>
                <Badge ok={vramOk} labelOk="OK" labelBad="Insuf." />
              </div>
              <div className="text-xs text-slate-500">
                Mínimo: <span style={{ color: vramOk ? '#4ADE80' : '#F87171' }}>{m.vram_gb} GB</span>
                {' · '}Óptimo: <span style={{ color: vramOptima ? '#4ADE80' : '#FACC15' }}>{m.vram_optima} GB</span>
              </div>
            </>
          ) : (
            <div className="text-xs text-slate-500 mt-1">Sin GPU NVIDIA detectada</div>
          )}
        </div>

        {/* Tokens (info) */}
        <div className="p-3 rounded-xl" style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
          <div className="text-xs text-slate-400 mb-1">Tokens por análisis</div>
          <div className="text-sm font-black font-mono text-white">{m.tokens}</div>
          <div className="text-xs text-slate-500 mt-0.5">num_predict configurado</div>
        </div>

        {/* Contexto (info) */}
        <div className="p-3 rounded-xl" style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
          <div className="text-xs text-slate-400 mb-1">Contexto (ctx)</div>
          <div className="text-sm font-black font-mono text-white">{m.ctx.toLocaleString()}</div>
          <div className="text-xs text-slate-500 mt-0.5">tokens de ventana</div>
        </div>
      </div>

      {/* Comando de instalacion */}
      <div className="px-4 pb-4" style={{ background: '#111827' }}>
        <div className="text-xs text-slate-500 mb-1.5">Instalar modelo:</div>
        <code className="block px-3 py-2 rounded-lg text-xs font-mono"
          style={{ background: '#0A0F1A', color: '#4ADE80', border: '1px solid #1A2235' }}>
          {m.pull}
        </code>
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────
export default function Configuracion() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [config, setConfig]   = useState(null)
  const [diag, setDiag]       = useState(null)
  const [diagLoading, setDiagLoading] = useState(false)
  const [modelosInstalados, setModelosInstalados] = useState([])
  const [userRol, setUserRol] = useState('')

  const pollingRef = useRef(null)

  const cargar = () => {
    api.get('/config/')
      .then(r => {
        setData(r.data)
        setConfig(r.data.config)
        setModelosInstalados(r.data.modelos_instalados || [])
        if (r.data.user_rol) setUserRol(r.data.user_rol)
      })
      .catch(() => toast.error('Error cargando configuración.'))
      .finally(() => setLoading(false))
  }

  // Refresca solo GPU y RAM sin pisar la config editada por el usuario
  const refrescarHardware = () => {
    api.get('/config/')
      .then(r => {
        setData(prev => prev
          ? { ...prev, gpu: r.data.gpu, ram: r.data.ram, cpu: r.data.cpu,
              ram_suficiente: r.data.ram_suficiente,
              vram_suficiente: r.data.vram_suficiente }
          : r.data)
      })
      .catch(() => {})
  }

  useEffect(() => {
    cargar()
    pollingRef.current = setInterval(refrescarHardware, 5000)
    return () => clearInterval(pollingRef.current)
  }, [])

  const guardar = async () => {
    setSaving(true)
    try {
      await api.post('/config/', config)
      toast.success('Configuración guardada.')
      cargar()
    } catch {
      toast.error('Error guardando configuración.')
    } finally {
      setSaving(false)
    }
  }

  const setDispositivo = (dispositivo) => {
    setConfig(c => ({ ...c, dispositivo, num_gpu: dispositivo === 'gpu' ? 999 : 0 }))
  }

  const setModelo = (modeloId) => {
    setConfig(c => ({ ...c, modelo: modeloId }))
  }

  const ejecutarDiagnostico = async () => {
    setDiagLoading(true)
    setDiag(null)
    try {
      const r = await api.get('/config/diagnostico-gpu')
      setDiag(r.data)
      if (r.data.gpu_activa) toast.success('GPU confirmada en uso.')
      else toast('GPU no detectada activa.', { icon: '⚠️' })
    } catch {
      toast.error('Error ejecutando diagnóstico.')
    } finally {
      setDiagLoading(false)
    }
  }

  if (loading) return (
    <AppLayout>
      <div className="flex justify-center items-center py-32"><Spinner size={12} /></div>
    </AppLayout>
  )

  const { gpu, ram, ram_suficiente, cpu } = data
  const cpuInfo = cpu || { logicos: 4, fisicos: 2, optimo: 2 }
  const ramUsada = ram.total_gb - ram.disponible_gb
  const esSuperAdmin = userRol === 'admin'

  // ── Vista simplificada para roles no-superadmin ─────────────────────────────
  if (!esSuperAdmin) {
    return (
      <AppLayout>
        <div className="p-8 max-w-2xl">
          <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-black text-white tracking-tight">Configuración de IA</h1>
              <p className="text-slate-400 mt-1">Elegí el modelo y tipo de procesamiento</p>
            </div>
            <button onClick={guardar} disabled={saving}
              className="px-5 py-2.5 rounded-xl font-bold text-sm disabled:opacity-60 transition-all"
              style={{ background: '#22D3EE', color: '#0A0F1A' }}
              onMouseEnter={e => !saving && (e.currentTarget.style.filter = 'brightness(1.08)')}
              onMouseLeave={e => e.currentTarget.style.filter = ''}>
              {saving ? 'Guardando...' : '💾 Guardar'}
            </button>
          </div>

          <div className="space-y-5">

            {/* Selector de procesamiento */}
            <Card>
              <CardTitle>🔧 Procesamiento</CardTitle>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { id: 'cpu', icon: '🖥️', label: 'CPU', desc: 'Compatible con todo equipo' },
                  { id: 'gpu', icon: '⚡', label: 'GPU', desc: 'Más rápido si tenés NVIDIA', disabled: !gpu.disponible },
                ].map(op => (
                  <button key={op.id}
                    disabled={op.disabled}
                    onClick={() => !op.disabled && setDispositivo(op.id)}
                    className="p-4 rounded-xl text-left transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: config?.dispositivo === op.id ? 'rgba(34,211,238,0.1)' : '#1A2235',
                      border: `1.5px solid ${config?.dispositivo === op.id ? '#22D3EE' : '#2A3A52'}`,
                    }}>
                    <div className="text-2xl mb-2">{op.icon}</div>
                    <div className="font-bold text-white text-sm">{op.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{op.desc}</div>
                    {op.disabled && <div className="text-xs text-red-400 mt-1">No disponible</div>}
                  </button>
                ))}
              </div>
            </Card>

            {/* Selector de modelo */}
            <Card>
              <CardTitle>🧠 Modelo de IA</CardTitle>
              <div className="space-y-3">
                {MODELOS.map(m => {
                  const activo    = config?.modelo === m.id
                  const instalado = modelosInstalados.some(n =>
                    n.toLowerCase().startsWith(m.id.split(':')[0].toLowerCase())
                  )
                  return (
                    <button key={m.id}
                      onClick={() => setModelo(m.id)}
                      className="w-full p-4 rounded-xl text-left transition-all"
                      style={{
                        background: activo ? `${m.tagColor}0D` : '#1A2235',
                        border: `1.5px solid ${activo ? m.tagColor : '#2A3A52'}`,
                      }}>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-white text-sm">{m.label}</span>
                          <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                            style={{ background: m.tagColor + '18', color: m.tagColor }}>
                            {m.tag}
                          </span>
                          {activo && (
                            <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                              style={{ background: 'rgba(255,255,255,0.07)', color: '#fff' }}>
                              ✓ Activo
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-semibold flex-shrink-0"
                          style={{ color: instalado ? '#4ADE80' : '#94A3B8' }}>
                          {instalado ? '● Instalado' : '○ No instalado'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-2 leading-relaxed">{m.desc}</p>
                    </button>
                  )
                })}
              </div>
            </Card>

            {/* Resumen */}
            <Card style={{ background: 'rgba(34,211,238,0.03)', border: '1px solid rgba(34,211,238,0.15)' }}>
              <CardTitle>📋 Configuración activa</CardTitle>
              <div className="space-y-2">
                {[
                  { label: 'Modelo',      value: config?.modelo },
                  { label: 'Dispositivo', value: config?.dispositivo?.toUpperCase() },
                ].map(item => (
                  <div key={item.label} className="flex justify-between items-center py-1.5"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span className="text-xs text-slate-500">{item.label}</span>
                    <span className="text-xs font-mono font-bold text-white">{item.value}</span>
                  </div>
                ))}
              </div>
            </Card>

          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="p-8 max-w-5xl">
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-black text-white tracking-tight">Configuración de IA</h1>
            <p className="text-slate-400 mt-1">Ajustá el modelo y hardware según tu equipo</p>
          </div>
          <button onClick={guardar} disabled={saving}
            className="px-5 py-2.5 rounded-xl font-bold text-sm disabled:opacity-60 transition-all"
            style={{ background: '#22D3EE', color: '#0A0F1A' }}
            onMouseEnter={e => !saving && (e.currentTarget.style.filter = 'brightness(1.08)')}
            onMouseLeave={e => e.currentTarget.style.filter = ''}>
            {saving ? 'Guardando...' : '💾 Guardar configuración'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ── Columna izquierda: Hardware ──────────────────────────────── */}
          <div className="space-y-4">

            {/* CPU */}
            <Card>
              <CardTitle>🖥️ Procesador (CPU)</CardTitle>
              <div className="grid grid-cols-3 gap-3 mb-3">
                {[
                  { label: 'Núcleos físicos',  value: cpuInfo.fisicos,  color: '#22D3EE' },
                  { label: 'Hilos lógicos',    value: cpuInfo.logicos,  color: '#A78BFA' },
                  { label: 'Hilos óptimos',    value: cpuInfo.optimo,   color: '#4ADE80' },
                ].map(s => (
                  <div key={s.label} className="p-3 rounded-xl text-center"
                    style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                    <div className="text-2xl font-black font-mono" style={{ color: s.color }}>{s.value}</div>
                    <div className="text-xs text-slate-500 mt-0.5 leading-tight">{s.label}</div>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2 p-2 rounded-lg"
                style={{ background: 'rgba(74,222,128,0.05)', border: '1px solid rgba(74,222,128,0.15)' }}>
                <span className="text-sm">✅</span>
                <span className="text-xs text-slate-400">
                  Configuración auto-detectada: usando <strong className="text-white">{cpuInfo.optimo} hilos</strong> de {cpuInfo.logicos} disponibles
                </span>
              </div>
            </Card>

            {/* RAM */}
            <Card>
              <CardTitle>🖥️ Memoria RAM del sistema</CardTitle>
              <RamBar usado={ramUsada} total={ram.total_gb} label="RAM del sistema" color="#22D3EE" />
              <div className="mt-3 flex justify-end">
                <Badge ok={ram_suficiente} labelOk="RAM suficiente" labelBad="RAM insuficiente" />
              </div>
            </Card>

            {/* GPU */}
            <Card>
              <CardTitle>⚡ Tarjeta de video (GPU)</CardTitle>
              {!gpu.disponible ? (
                <div className="flex items-center gap-3 p-4 rounded-xl"
                  style={{ background: 'rgba(148,163,184,0.05)', border: '1px solid #2A3A52' }}>
                  <span className="text-2xl">🖥️</span>
                  <div>
                    <div className="text-sm font-bold text-slate-300">Sin GPU NVIDIA detectada</div>
                    <div className="text-xs text-slate-500 mt-0.5">Solo disponible modo CPU</div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {gpu.gpus.map((g, i) => {
                    const vramUsada  = g.vram_total - g.vram_libre
                    const vramPct    = g.vram_total > 0 ? Math.round((vramUsada / g.vram_total) * 100) : 0
                    const computoColor = g.uso_pct > 60 ? '#4ADE80' : g.uso_pct > 20 ? '#FACC15' : '#94A3B8'
                    return (
                      <div key={i} className="p-4 rounded-xl" style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-bold text-sm text-white">{g.nombre}</div>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-slate-500">
                              VRAM: <span className="font-mono font-bold text-white">{vramPct}%</span>
                            </span>
                            <span className="text-xs text-slate-500">
                              Cómputo: <span className="font-mono font-bold" style={{ color: computoColor }}>{g.uso_pct}%</span>
                            </span>
                          </div>
                        </div>
                        <RamBar
                          usado={vramUsada / 1024}
                          total={g.vram_total / 1024}
                          label="VRAM"
                          color="#4ADE80"
                        />
                      </div>
                    )
                  })}
                </div>
              )}
            </Card>

            {/* Dispositivo */}
            <Card>
              <CardTitle>🔧 Procesamiento</CardTitle>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { id: 'cpu', icon: '🖥️', label: 'CPU', desc: 'Compatible con todo equipo' },
                  { id: 'gpu', icon: '⚡', label: 'GPU', desc: 'Más rápido si tenés NVIDIA', disabled: !gpu.disponible },
                ].map(op => (
                  <button key={op.id}
                    disabled={op.disabled}
                    onClick={() => !op.disabled && setDispositivo(op.id)}
                    className="p-4 rounded-xl text-left transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: config?.dispositivo === op.id ? 'rgba(34,211,238,0.1)' : '#1A2235',
                      border: `1.5px solid ${config?.dispositivo === op.id ? '#22D3EE' : '#2A3A52'}`,
                    }}>
                    <div className="text-2xl mb-2">{op.icon}</div>
                    <div className="font-bold text-white text-sm">{op.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{op.desc}</div>
                    {op.disabled && <div className="text-xs text-red-400 mt-1">No disponible</div>}
                  </button>
                ))}
              </div>

              {config?.dispositivo === 'cpu' && (
                <div className="mt-4">
                  <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                    Threads CPU: {config.num_threads}
                  </label>
                  <input type="range" min={1} max={cpuInfo.logicos} step={1}
                    value={config.num_threads}
                    onChange={e => setConfig(c => ({ ...c, num_threads: parseInt(e.target.value) }))}
                    className="w-full accent-cyan-400" />
                  <div className="flex justify-between text-xs text-slate-600 mt-1">
                    <span>1 (mínimo)</span>
                    <span className="text-cyan-600">{cpuInfo.optimo} (óptimo)</span>
                    <span>{cpuInfo.logicos} (máx)</span>
                  </div>
                  {config.num_threads < cpuInfo.optimo && (
                    <div className="text-xs text-yellow-400 mt-1.5 flex items-center gap-1">
                      ⚠️ Usando menos hilos que el óptimo detectado ({cpuInfo.optimo})
                    </div>
                  )}
                </div>
              )}
            </Card>

            {/* Resumen config activa */}
            <Card style={{ background: 'rgba(34,211,238,0.03)', border: '1px solid rgba(34,211,238,0.15)' }}>
              <CardTitle>📋 Configuración activa</CardTitle>
              <div className="space-y-2">
                {[
                  { label: 'Modelo',        value: config?.modelo },
                  { label: 'Dispositivo',   value: config?.dispositivo?.toUpperCase() },
                  { label: 'Threads CPU',   value: config?.dispositivo === 'cpu' ? `${config?.num_threads} / ${cpuInfo.logicos}` : '—' },
                  { label: 'Núcleos físicos', value: `${cpuInfo.fisicos} cores` },
                  { label: 'RAM disponible', value: `${ram.disponible_gb?.toFixed(1)} GB` },
                ].map(item => (
                  <div key={item.label} className="flex justify-between items-center py-1.5"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span className="text-xs text-slate-500">{item.label}</span>
                    <span className="text-xs font-mono font-bold text-white">{item.value}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* ── Columna derecha: Modelos ──────────────────────────────────── */}
          <div className="space-y-4">
            <Card>
              <CardTitle>🧠 Modelo de IA</CardTitle>
              <div className="space-y-3">
                {MODELOS.map(m => {
                  const activo    = config?.modelo === m.id
                  const instalado = modelosInstalados.some(n =>
                    n.toLowerCase().startsWith(m.id.split(':')[0].toLowerCase())
                  )

                  return (
                    <div key={m.id}>
                      <button
                        onClick={() => setModelo(m.id)}
                        className="w-full p-4 rounded-xl text-left transition-all"
                        style={{
                          background: activo ? `${m.tagColor}0D` : '#1A2235',
                          border: `1.5px solid ${activo ? m.tagColor : '#2A3A52'}`,
                        }}>

                        {/* Header */}
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-white text-sm">{m.label}</span>
                            <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                              style={{ background: m.tagColor + '18', color: m.tagColor }}>
                              {m.tag}
                            </span>
                            {activo && (
                              <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                                style={{ background: 'rgba(255,255,255,0.07)', color: '#fff' }}>
                                ✓ Activo
                              </span>
                            )}
                          </div>
                          <span className="text-xs font-semibold flex-shrink-0"
                            style={{ color: instalado ? '#4ADE80' : '#94A3B8' }}>
                            {instalado ? '● Instalado' : '○ No instalado'}
                          </span>
                        </div>

                        {/* Desc */}
                        <p className="text-xs text-slate-400 mb-3 leading-relaxed">{m.desc}</p>

                        {/* Fortalezas */}
                        <div className="flex flex-wrap gap-1.5 mb-3">
                          {m.fortalezas.map(f => (
                            <span key={f} className="text-xs px-2 py-0.5 rounded-lg"
                              style={{ background: 'rgba(255,255,255,0.04)', color: '#94A3B8', border: '1px solid #2A3A52' }}>
                              {f}
                            </span>
                          ))}
                        </div>

                        {/* Hardware reqs (mini) */}
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-mono text-slate-600">
                            RAM {m.ram_gb}GB · VRAM {m.vram_gb}GB · {m.tokens} tokens
                          </span>
                        </div>
                      </button>

                      {/* Panel de compatibilidad — solo si es el modelo activo/seleccionado */}
                      {activo && (
                        <HardwareCheck
                          modelo={config?.modelo}
                          gpu={gpu}
                          ram={ram}
                          dispositivo={config?.dispositivo}
                        />
                      )}
                    </div>
                  )
                })}
              </div>
            </Card>
          </div>
        </div>

        {/* ── Diagnóstico GPU ───────────────────────────────────────────────── */}
        {config?.dispositivo === 'gpu' && (
          <Card className="mt-6">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <CardTitle>🔬 Diagnóstico de GPU</CardTitle>
              <button onClick={ejecutarDiagnostico} disabled={diagLoading}
                className="px-4 py-2 rounded-xl text-sm font-bold transition-all disabled:opacity-60"
                style={{ background: 'rgba(167,139,250,0.1)', color: '#A78BFA', border: '1px solid rgba(167,139,250,0.25)' }}
                onMouseEnter={e => !diagLoading && (e.currentTarget.style.background = 'rgba(167,139,250,0.18)')}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(167,139,250,0.1)'}>
                {diagLoading ? '⏳ Probando...' : '▶ Probar GPU ahora'}
              </button>
            </div>

            {!diag && !diagLoading && (
              <p className="text-sm text-slate-500">
                Hace click en "Probar GPU ahora" para verificar si Ollama está usando la GPU.
                El test hace una inferencia mínima y verifica VRAM asignada.
              </p>
            )}

            {diagLoading && (
              <div className="flex items-center gap-3 text-slate-400 text-sm">
                <Spinner size={5} /> Ejecutando inferencia de prueba...
              </div>
            )}

            {diag && (
              <div className="space-y-4">
                <div className="flex items-start gap-4 p-4 rounded-xl"
                  style={{
                    background: diag.gpu_activa ? 'rgba(74,222,128,0.06)' : 'rgba(248,113,113,0.06)',
                    border: `1px solid ${diag.gpu_activa ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)'}`,
                  }}>
                  <span className="text-3xl flex-shrink-0">{diag.gpu_activa ? '✅' : '⚠️'}</span>
                  <div>
                    <div className="font-bold text-white mb-1">{diag.mensaje}</div>
                    {diag.pasos_solucion && (
                      <ol className="text-xs text-slate-400 mt-2 space-y-1 list-decimal list-inside">
                        {diag.pasos_solucion.map((p, i) => <li key={i}>{p}</li>)}
                      </ol>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                  {[
                    { label: 'Tiempo respuesta', value: diag.tiempo_respuesta_s + 's', color: '#A78BFA' },
                    { label: 'VRAM asignada',    value: diag.ollama_vram_mb ? diag.ollama_vram_mb + ' MB' : '—', color: diag.gpu_activa ? '#4ADE80' : '#F87171' },
                    { label: 'Dispositivo',      value: diag.dispositivo_config?.toUpperCase(), color: '#22D3EE' },
                  ].map(item => (
                    <div key={item.label} className="p-3 rounded-xl text-center"
                      style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                      <div className="text-lg font-black font-mono mb-1" style={{ color: item.color }}>{item.value}</div>
                      <div className="text-xs text-slate-500">{item.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        )}

      </div>
    </AppLayout>
  )
}
