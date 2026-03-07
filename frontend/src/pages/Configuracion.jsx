import { useEffect, useState } from 'react'
import api from '../services/api'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Spinner } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

const MODELOS = [
  {
    id: 'llama3.1:8b', label: 'Llama 3.1 8B', ram: 6, vram: 6,
    desc: 'El más rápido de los tres. Bueno para pruebas o equipos con poca RAM.',
    tag: 'Rápido',  tagColor: '#22D3EE',
    fortalezas: ['Respuesta rápida', 'Bajo consumo de RAM', 'Bueno en inglés'],
  },
  {
    id: 'qwen2.5:7b',  label: 'Qwen 2.5 7B',  ram: 6, vram: 6,
    desc: 'Mejor comprensión del español que Llama con el mismo hardware.',
    tag: 'Equilibrado', tagColor: '#4ADE80',
    fortalezas: ['Mejor en español', 'Mismo hardware que Llama', 'JSON más consistente'],
  },
  {
    id: 'qwen2.5:14b', label: 'Qwen 2.5 14B', ram: 10, vram: 10,
    desc: 'El más preciso de los tres. Recomendado para análisis de producción.',
    tag: 'Recomendado', tagColor: '#A78BFA',
    fortalezas: ['Mayor precisión', 'Mejor razonamiento', 'Ideal para producción'],
  },
]

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
      <div className="text-xs text-slate-600 mt-1">
        {(total - usado).toFixed(1)} GB disponibles
      </div>
    </div>
  )
}

function StatusBadge({ ok, labelOk, labelBad }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
      style={{ background: ok ? 'rgba(74,222,128,0.1)' : 'rgba(248,113,113,0.1)',
               color: ok ? '#4ADE80' : '#F87171',
               border: `1px solid ${ok ? 'rgba(74,222,128,0.25)' : 'rgba(248,113,113,0.25)'}` }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: ok ? '#4ADE80' : '#F87171' }} />
      {ok ? labelOk : labelBad}
    </span>
  )
}

export default function Configuracion() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [config, setConfig]   = useState(null)

  const [diag, setDiag]       = useState(null)
  const [diagLoading, setDiagLoading] = useState(false)

  const ejecutarDiagnostico = async () => {
    setDiagLoading(true)
    setDiag(null)
    try {
      const r = await api.get('/config/diagnostico-gpu')
      setDiag(r.data)
      if (r.data.gpu_activa) toast.success('GPU confirmada en uso.')
      else toast('GPU no detectada activa. Ver recomendaciones.', { icon: '⚠️' })
    } catch {
      toast.error('Error ejecutando diagnóstico.')
    } finally {
      setDiagLoading(false)
    }
  }

  const [modelosInstalados, setModelosInstalados] = useState([])

  const cargar = () => {
    api.get('/config/')
      .then(r => {
        setData(r.data)
        setConfig(r.data.config)
        setModelosInstalados(r.data.modelos_instalados || [])
      })
      .catch(() => toast.error('Error cargando configuración.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [])

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
    setConfig(c => ({
      ...c,
      dispositivo,
      num_gpu: dispositivo === 'gpu' ? -1 : 0,
    }))
  }

  if (loading) return (
    <AppLayout>
      <div className="flex justify-center items-center py-32"><Spinner size={12} /></div>
    </AppLayout>
  )

  const { gpu, ram, req_modelo, ram_suficiente, vram_suficiente } = data
  const ramUsada = ram.total_gb - ram.disponible_gb

  return (
    <AppLayout>
      <div className="p-8 max-w-4xl">
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-black text-white tracking-tight">Configuración de IA</h1>
            <p className="text-slate-400 mt-1">Ajustá el hardware y modelo según tu equipo</p>
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

          {/* Columna izquierda — Hardware */}
          <div className="space-y-4">

            {/* RAM del sistema */}
            <Card>
              <CardTitle>🖥️ Memoria RAM del sistema</CardTitle>
              <RamBar
                usado={ramUsada}
                total={ram.total_gb}
                label="RAM del sistema"
                color="#22D3EE"
              />
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-slate-400">
                  Modelo actual requiere ~{req_modelo.ram_gb} GB
                </span>
                <StatusBadge ok={ram_suficiente} labelOk="RAM suficiente" labelBad="RAM insuficiente" />
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
                    const vramUsada = g.vram_total - g.vram_libre
                    const vramPct   = (vramUsada / g.vram_total) * 100
                    const vramColor = vramPct > 85 ? '#F87171' : vramPct > 65 ? '#FACC15' : '#4ADE80'
                    return (
                      <div key={i} className="p-4 rounded-xl" style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                        <div className="flex items-center justify-between mb-3">
                          <div className="font-bold text-sm text-white">{g.nombre}</div>
                          <span className="text-xs font-mono" style={{ color: '#4ADE80' }}>{g.uso_pct}% uso</span>
                        </div>
                        <RamBar
                          usado={vramUsada / 1024}
                          total={g.vram_total / 1024}
                          label="VRAM"
                          color="#4ADE80"
                        />
                        <div className="mt-2 flex items-center justify-between">
                          <span className="text-xs text-slate-500">
                            Requiere ~{req_modelo.vram_gb} GB VRAM
                          </span>
                          <StatusBadge ok={vramPct < 80} labelOk="VRAM OK" labelBad="VRAM alta" />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </Card>

            {/* Dispositivo CPU / GPU */}
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
                  <input type="range" min={1} max={16} step={1}
                    value={config.num_threads}
                    onChange={e => setConfig(c => ({ ...c, num_threads: parseInt(e.target.value) }))}
                    className="w-full accent-cyan-400" />
                  <div className="flex justify-between text-xs text-slate-600 mt-1">
                    <span>1 (lento)</span><span>8</span><span>16 (máx)</span>
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Columna derecha — Modelo */}
          <div className="space-y-4">
            <Card>
              <CardTitle>🧠 Modelo de IA</CardTitle>
              <div className="space-y-3">
                {MODELOS.map(m => {
                  const activo     = config?.modelo === m.id
                  const instalado  = modelosInstalados.some(n => n.startsWith(m.id.split(':')[0]))
                  const suficiente = ram.total_gb >= m.ram

                  return (
                    <button key={m.id}
                      onClick={() => instalado && setConfig(c => ({ ...c, modelo: m.id }))}
                      className="w-full p-4 rounded-xl text-left transition-all"
                      style={{
                        background: activo ? `${m.tagColor}0D` : '#1A2235',
                        border: `1.5px solid ${activo ? m.tagColor : '#2A3A52'}`,
                        opacity: instalado ? 1 : 0.5,
                        cursor: instalado ? 'pointer' : 'not-allowed',
                      }}>

                      {/* Header del modelo */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-white text-sm">{m.label}</span>
                          <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                            style={{ background: `${m.tagColor}18`, color: m.tagColor }}>
                            {m.tag}
                          </span>
                          {activo && (
                            <span className="text-xs px-2 py-0.5 rounded-full font-bold"
                              style={{ background: 'rgba(255,255,255,0.06)', color: '#fff' }}>
                              ✓ Activo
                            </span>
                          )}
                        </div>
                        {/* Estado de instalación */}
                        <span className="text-xs font-semibold flex-shrink-0 ml-2"
                          style={{ color: instalado ? '#4ADE80' : '#F87171' }}>
                          {instalado ? '● Instalado' : '○ No instalado'}
                        </span>
                      </div>

                      {/* Descripción */}
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

                      {/* RAM + advertencia */}
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-slate-600">
                          RAM: {m.ram} GB · VRAM: {m.vram} GB
                        </span>
                        {!suficiente && instalado && (
                          <span className="text-xs font-bold" style={{ color: '#FACC15' }}>
                            ⚠ RAM ajustada
                          </span>
                        )}
                        {!instalado && (
                          <code className="text-xs font-mono" style={{ color: '#94A3B8' }}>
                            ollama pull {m.id}
                          </code>
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            </Card>

            {/* Resumen de config actual */}
            <Card style={{ background: 'rgba(34,211,238,0.03)', border: '1px solid rgba(34,211,238,0.15)' }}>
              <CardTitle>📋 Configuración activa</CardTitle>
              <div className="space-y-2.5">
                {[
                  { label: 'Modelo',        value: config?.modelo },
                  { label: 'Dispositivo',   value: config?.dispositivo?.toUpperCase() },
                  { label: 'Threads CPU',   value: config?.dispositivo === 'cpu' ? config?.num_threads : '—' },
                  { label: 'Capas GPU',     value: config?.dispositivo === 'gpu' ? 'Todas (-1)' : '—' },
                  { label: 'RAM disponible', value: `${ram.disponible_gb.toFixed(1)} GB` },
                ].map(item => (
                  <div key={item.label} className="flex justify-between items-center py-2"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <span className="text-xs text-slate-500">{item.label}</span>
                    <span className="text-xs font-mono font-bold text-white">{item.value}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

        </div>

        {/* Panel diagnóstico GPU */}
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
                Hacé click en "Probar GPU ahora" para verificar si Ollama realmente está usando la GPU.
                El test hace una inferencia mínima y mide el uso de GPU antes y después.
              </p>
            )}

            {diagLoading && (
              <div className="flex items-center gap-3 text-slate-400 text-sm">
                <Spinner size={5} /> Ejecutando inferencia de prueba, esperá unos segundos...
              </div>
            )}

            {diag && (
              <div className="space-y-4">
                {/* Resultado principal */}
                <div className="flex items-start gap-4 p-4 rounded-xl"
                  style={{ background: diag.gpu_activa ? 'rgba(74,222,128,0.06)' : 'rgba(248,113,113,0.06)',
                           border: `1px solid ${diag.gpu_activa ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)'}` }}>
                  <span className="text-3xl flex-shrink-0">{diag.gpu_activa ? '✅' : '⚠️'}</span>
                  <div>
                    <div className="font-bold text-white mb-1">{diag.mensaje}</div>
                    {diag.solucion && (
                      <div className="text-xs text-slate-400 mt-2 leading-relaxed">
                        <strong className="text-yellow-400">Pasos para habilitar GPU:</strong>
                        <br />{diag.solucion}
                      </div>
                    )}
                  </div>
                </div>

                {/* Métricas */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  {[
                    { label: 'Dispositivo config', value: diag.dispositivo_config?.toUpperCase(), color: '#22D3EE' },
                    { label: 'Tiempo respuesta',   value: `${diag.tiempo_respuesta_s}s`,          color: '#A78BFA' },
                    { label: 'GPU uso antes',      value: `${diag.gpu_uso_antes_pct}%`,            color: '#94A3B8' },
                    { label: 'GPU uso durante',    value: `${diag.gpu_uso_despues_pct}%`,          color: diag.gpu_activa ? '#4ADE80' : '#F87171' },
                  ].map(m => (
                    <div key={m.label} className="p-3 rounded-xl text-center"
                      style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                      <div className="text-lg font-black font-mono mb-1" style={{ color: m.color }}>{m.value}</div>
                      <div className="text-xs text-slate-500">{m.label}</div>
                    </div>
                  ))}
                </div>

                {/* Tip CUDA */}
                {!diag.gpu_activa && (
                  <div className="p-4 rounded-xl text-xs leading-relaxed"
                    style={{ background: 'rgba(250,204,21,0.05)', border: '1px solid rgba(250,204,21,0.15)', color: '#FCD34D' }}>
                    <strong>¿Cómo verificar manualmente?</strong> Mientras corre un análisis, abrí una nueva terminal y ejecutá:
                    <code className="block mt-2 p-2 rounded-lg bg-black/30 font-mono text-green-400">
                      nvidia-smi
                    </code>
                    Si Ollama usa GPU, vas a ver el proceso "ollama_llama_s" en la lista con VRAM asignada.
                  </div>
                )}
              </div>
            )}
          </Card>
        )}

      </div>
    </AppLayout>
  )
}
