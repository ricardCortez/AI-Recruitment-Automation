import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { procesoService, cvsService } from '../services/procesoService'
import { useAnalisis } from '../context/AnalisisContext'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Spinner, PageContainer } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'
import api from '../services/api'

function ProgressBar({ value, cancelado }) {
  const [display, setDisplay] = useState(0)
  const prev = useRef(0)
  useEffect(() => {
    const target = value
    if (target <= prev.current) return
    const steps = 25, step = (target - prev.current) / steps
    let i = 0
    const iv = setInterval(() => {
      i++
      setDisplay(Math.min(prev.current + step * i, target))
      if (i >= steps) { prev.current = target; clearInterval(iv) }
    }, 25)
    return () => clearInterval(iv)
  }, [value])
  const color = cancelado ? '#F87171' : display >= 100 ? '#4ADE80' : '#22D3EE'
  return (
    <div className="w-full rounded-full overflow-hidden" style={{ height: 8, background: '#2A3A52' }}>
      <div className="h-full rounded-full"
        style={{ width: display + '%', background: color,
                 boxShadow: display > 0 && display < 100 ? '0 0 10px ' + color + '60' : 'none' }} />
    </div>
  )
}

function ResourceMonitor({ activo }) {
  const [res, setRes] = useState(null)
  const ref = useRef(null)

  const poll = useCallback(async () => {
    try {
      const r = await api.get('/config/recursos')
      setRes(r.data)
    } catch {}
  }, [])

  useEffect(() => {
    // Llamar inmediatamente al montar o cuando activo cambia a true
    poll()
    if (!activo) return
    ref.current = setInterval(poll, 3000)
    return () => clearInterval(ref.current)
  }, [activo, poll])

  // Reactivar al volver a la vista
  useEffect(() => {
    const onVisible = () => { if (!document.hidden && activo) poll() }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [activo, poll])

  if (!res) return null

  const gpu  = res.gpu
  const usoGPU = gpu?.disponible && gpu?.ollama_en_gpu

  const Bar = ({ pct, color }) => (
    <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: '#2A3A52' }}>
      <div className="h-full rounded-full transition-all duration-700"
        style={{ width: Math.min(pct, 100) + '%', background: color }} />
    </div>
  )

  const Stat = ({ label, value, pct, color, alert }) => (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 w-8 flex-shrink-0">{label}</span>
      <Bar pct={pct} color={alert ? '#F87171' : color} />
      <span className="text-xs font-mono w-10 text-right flex-shrink-0"
        style={{ color: alert ? '#F87171' : color }}>
        {value}
      </span>
    </div>
  )

  return (
    <div className="p-4 rounded-xl mb-4"
      style={{ background: '#0D1520', border: '1px solid #1E2D42' }}>

      {/* Header con indicador GPU */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
          Monitor de recursos
        </span>
        <div className="flex items-center gap-2">
          {gpu?.disponible ? (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full"
              style={{
                background: usoGPU ? 'rgba(74,222,128,0.1)' : 'rgba(250,204,21,0.1)',
                border: '1px solid ' + (usoGPU ? 'rgba(74,222,128,0.3)' : 'rgba(250,204,21,0.3)')
              }}>
              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ background: usoGPU ? '#4ADE80' : '#FACC15' }} />
              <span className="text-xs font-bold"
                style={{ color: usoGPU ? '#4ADE80' : '#FACC15' }}>
                {usoGPU ? 'GPU activa' : 'GPU: sin uso'}
              </span>
            </div>
          ) : (
            <span className="text-xs text-slate-600">Sin GPU NVIDIA</span>
          )}
        </div>
      </div>

      {/* Metricas */}
      <div className="space-y-2">
        <Stat label="CPU"
          pct={res.cpu_pct}
          value={res.cpu_pct + '%'}
          color="#22D3EE"
          alert={res.cpu_pct > 95} />
        <Stat label="RAM"
          pct={res.ram_pct}
          value={res.ram_pct + '%'}
          color="#A78BFA"
          alert={res.ram_pct > 90} />
        {gpu?.disponible && (
          <>
            <Stat label="GPU"
              pct={gpu.gpu_pct}
              value={gpu.gpu_pct + '%'}
              color="#4ADE80"
              alert={false} />
            <Stat label="VRAM"
              pct={gpu.vram_pct}
              value={gpu.vram_pct + '%'}
              color="#FB923C"
              alert={gpu.vram_pct > 90} />
          </>
        )}
      </div>

      {/* Detalle GPU */}
      {gpu?.disponible && (
        <div className="mt-3 pt-3 border-t" style={{ borderColor: '#1E2D42' }}>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-600 truncate">{gpu.nombre}</span>
            <span className="text-xs font-mono text-slate-500">
              {gpu.vram_usada_mb} / {gpu.vram_total_mb} MB VRAM
            </span>
          </div>
          {!usoGPU && gpu.disponible && gpu.mensaje && (
            <div className="mt-2 text-xs text-yellow-400 flex items-start gap-1.5">
              <span className="flex-shrink-0">⚠</span>
              <span>{gpu.mensaje}</span>
            </div>
          )}
          {usoGPU && (
            <div className="mt-2 text-xs text-green-400 flex items-center gap-1.5">
              <span>✓</span>
              <span>Ollama usando {gpu.ollama_vram_mb} MB VRAM — análisis acelerado por GPU</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function OllamaStatus({ status }) {
  if (!status) return null
  const ok = status.ollama_disponible && status.modelo_disponible
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl mb-4"
      style={{ background: ok ? 'rgba(74,222,128,0.06)' : 'rgba(248,113,113,0.06)',
               border: '1px solid ' + (ok ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)') }}>
      <span className="text-lg flex-shrink-0">{ok ? '🟢' : '🔴'}</span>
      <div>
        <div className="font-bold text-sm text-white">
          {ok ? 'Ollama listo · ' + status.modelo_requerido
              : !status.ollama_disponible ? 'Ollama no disponible' : 'Modelo no descargado'}
        </div>
        {!ok && (
          <code className="text-xs font-mono mt-1 text-slate-400 block">
            {!status.ollama_disponible ? 'ollama serve' : 'ollama pull ' + status.modelo_requerido}
          </code>
        )}
      </div>
    </div>
  )
}

function formatTiempo(s) {
  if (!s) return '0:00'
  const m = Math.floor(s / 60), seg = s % 60
  return m + ':' + String(seg).padStart(2, '0')
}

export default function NuevoAnalisis() {
  const navigate = useNavigate()
  const { analisisActivo, iniciarAnalisis, limpiarAnalisis } = useAnalisis()

  const [form, setForm]     = useState({ nombre_puesto: '', requisitos: '' })
  const [files, setFiles]   = useState([])
  const [cancelando, setCancelando] = useState(false)
  const [ollamaStatus, setOllamaStatus] = useState(null)

  useEffect(() => {
    api.get('/cvs/ollama/estado')
      .then(r => setOllamaStatus(r.data))
      .catch(() => setOllamaStatus({ ollama_disponible: false, modelo_disponible: false }))
  }, [])

  const onDrop = useCallback((accepted) => {
    setFiles(prev => {
      // Deduplicar por nombre + tamaño para permitir archivos con mismo nombre pero distinto contenido
      const nuevos = accepted.filter(f =>
        !prev.find(e => e.name === f.name && e.size === f.size)
      )
      const duplicados = accepted.length - nuevos.length
      if (duplicados > 0) toast(`${duplicados} archivo${duplicados > 1 ? 's' : ''} duplicado${duplicados > 1 ? 's' : ''} ignorado${duplicados > 1 ? 's' : ''}.`, { icon: '⚠️' })
      return [...prev, ...nuevos]
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'] }, maxFiles: 20,
  })

  const handleAnalizar = async () => {
    if (!form.nombre_puesto.trim()) return toast.error('Ingresá el nombre del puesto.')
    if (!form.requisitos.trim())    return toast.error('Ingresá los requisitos del puesto.')
    if (files.length === 0)         return toast.error('Agregá al menos un CV en PDF.')
    if (ollamaStatus && !ollamaStatus.ollama_disponible) return toast.error('Ollama no está corriendo.')
    if (ollamaStatus && !ollamaStatus.modelo_disponible) return toast.error('Ejecutá: ollama pull ' + ollamaStatus.modelo_requerido)

    try {
      const { data: proceso } = await procesoService.crear(form)
      const fd = new FormData()
      files.forEach(f => fd.append('files', f))
      await cvsService.subirCVs(proceso.id, fd)
      await cvsService.analizar(proceso.id)
      iniciarAnalisis(proceso.id, files)
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || 'Error al iniciar.')
    }
  }

  const handleCancelar = async () => {
    if (!analisisActivo) return
    if (!confirm('¿Cancelar el análisis? Se detendrá al terminar el CV actual.')) return
    setCancelando(true)
    try {
      await cvsService.cancelar(analisisActivo.procesoId)
      toast('Cancelación solicitada...', { icon: '⛔' })
    } catch {
      toast.error('Error al cancelar.')
    } finally {
      setCancelando(false)
    }
  }

  const inputClass = "w-full px-4 py-3 rounded-xl text-white placeholder-slate-600 text-sm focus:outline-none"
  const inputStyle = { background: '#1A2235', border: '1.5px solid #2A3A52' }

  // ── Vista: Analizando o Listo (desde contexto global) ─────────────────────
  if (analisisActivo) {
    const { paso, progreso, procesoId } = analisisActivo
    const { completado, total, progreso_global, log_actual, items, cancelado, tiempo_s } = progreso

    return (
      <AppLayout>
        <PageContainer size="sm">

          <div className="text-center mb-8">
            {paso === 'analizando' && !cancelado ? (
              <>
                <div className="flex justify-center mb-5"><Spinner size={16} /></div>
                <h2 className="text-2xl font-black text-white mb-2">Analizando CVs con IA local</h2>
                <p className="text-slate-400 text-sm">Sin enviar datos a internet · Podés navegar libremente</p>
              </>
            ) : cancelado ? (
              <>
                <div className="text-5xl mb-4">⛔</div>
                <h2 className="text-2xl font-black text-white mb-2">Análisis cancelado</h2>
                <p className="text-slate-400 text-sm">{completado} de {total} CVs procesados antes de cancelar.</p>
              </>
            ) : (
              <>
                <div className="text-5xl mb-4">✅</div>
                <h2 className="text-2xl font-black text-white mb-2">¡Análisis completado!</h2>
                <p className="text-slate-400 text-sm">
                  {total} CVs procesados en{' '}
                  <span className="font-bold text-white">{formatTiempo(tiempo_s)}</span>
                </p>
              </>
            )}
          </div>

          <Card className="mb-4">
            <div className="flex items-center justify-between mb-4">
              <CardTitle>📊 Progreso</CardTitle>
              <div className="flex items-center gap-3">
                {/* Timer */}
                <span className="text-xs font-mono px-2 py-1 rounded-lg"
                  style={{ background: '#1A2235', color: '#22D3EE', border: '1px solid #2A3A52' }}>
                  ⏱ {formatTiempo(tiempo_s)}
                </span>
                {/* Cancelar */}
                {paso === 'analizando' && !cancelado && (
                  <button onClick={handleCancelar} disabled={cancelando}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all disabled:opacity-50"
                    style={{ background: 'rgba(248,113,113,0.08)', color: '#F87171',
                             border: '1px solid rgba(248,113,113,0.2)' }}
                    onMouseEnter={e => !cancelando && (e.currentTarget.style.background = 'rgba(248,113,113,0.18)')}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(248,113,113,0.08)'}>
                    {cancelando ? '⏳ Cancelando...' : '⛔ Cancelar'}
                  </button>
                )}
              </div>
            </div>

            {/* Barra */}
            <div className="mb-4">
              <div className="flex justify-between text-xs mb-2">
                <span className="text-slate-400">{completado} de {total} CVs procesados</span>
                <span className="font-mono font-bold" style={{ color: cancelado ? '#F87171' : '#22D3EE' }}>
                  {progreso_global}%
                </span>
              </div>
              <ProgressBar value={progreso_global} cancelado={cancelado} />
            </div>

            {/* Log */}
            {log_actual && paso === 'analizando' && !cancelado && (
              <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl mb-4"
                style={{ background: 'rgba(34,211,238,0.05)', border: '1px solid rgba(34,211,238,0.12)' }}>
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse"
                  style={{ background: '#22D3EE', minWidth: 6 }} />
                <span className="text-xs font-mono text-cyan-300">{log_actual}</span>
              </div>
            )}

            {/* Monitor de recursos */}
            <ResourceMonitor activo={paso === 'analizando' && !cancelado} />

            {/* Lista CVs */}
            <div className="space-y-2">
              {items.map((item, i) => {
                const cfg = {
                  completado: { icon: '✓', color: '#4ADE80', bg: 'rgba(74,222,128,0.08)',  label: 'Listo' },
                  error:      { icon: '✕', color: '#F87171', bg: 'rgba(248,113,113,0.08)', label: cancelado ? 'Cancelado' : 'Error' },
                  procesando: { icon: '⟳', color: '#22D3EE', bg: 'rgba(34,211,238,0.08)', label: 'Procesando' },
                  pendiente:  { icon: '○', color: '#475569', bg: 'transparent',            label: 'En espera' },
                }[item.estado]
                return (
                  <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-xl"
                    style={{ background: cfg.bg, border: '1px solid rgba(255,255,255,0.04)' }}>
                    <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                      style={{ background: cfg.color + '18', color: cfg.color }}>
                      <span className={item.estado === 'procesando' ? 'animate-spin inline-block' : ''}>{cfg.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white font-medium truncate">{item.nombre}</div>
                      {item.estado === 'procesando' && log_actual && (
                        <div className="text-xs text-slate-500 truncate mt-0.5">{log_actual}</div>
                      )}
                    </div>
                    <span className="text-xs font-semibold flex-shrink-0" style={{ color: cfg.color }}>{cfg.label}</span>
                  </div>
                )
              })}
            </div>
          </Card>

          {(paso === 'listo' || cancelado) && (
            <div className="flex gap-3">
              {completado > 0 && (
                <button onClick={() => { const id = procesoId; limpiarAnalisis(); navigate('/resultados/' + id) }}
                  className="flex-1 py-3.5 rounded-xl font-black text-sm transition-all"
                  style={{ background: cancelado
                    ? 'linear-gradient(135deg, #F59E0B, #D97706)'
                    : 'linear-gradient(135deg, #22D3EE, #06B6D4)', color: '#0A0F1A' }}
                  onMouseEnter={e => e.currentTarget.style.filter = 'brightness(1.08)'}
                  onMouseLeave={e => e.currentTarget.style.filter = ''}>
                  {cancelado
                    ? 'Ver ' + completado + ' resultado' + (completado !== 1 ? 's parciales' : ' parcial') + ' →'
                    : 'Ver ' + completado + ' resultado' + (completado !== 1 ? 's' : '') + ' →'
                  }
                </button>
              )}
              <button onClick={() => { limpiarAnalisis(); setFiles([]) }}
                className="px-5 py-3.5 rounded-xl font-bold text-sm transition-all"
                style={{ background: '#1A2235', color: '#94A3B8', border: '1px solid #2A3A52' }}
                onMouseEnter={e => e.currentTarget.style.borderColor = '#22D3EE'}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#2A3A52'}>
                🔄 Nuevo análisis
              </button>
            </div>
          )}
        </PageContainer>
      </AppLayout>
    )
  }

  // ── Vista: Formulario ──────────────────────────────────────────────────────
  return (
    <AppLayout>
      <PageContainer size="lg">
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-black text-white tracking-tight">Nuevo proceso de selección</h1>
            <p className="text-slate-400 mt-1">Cargá los CVs y definí el perfil requerido</p>
          </div>
          <button onClick={() => navigate('/configuracion')}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all"
            style={{ background: '#1A2235', color: '#94A3B8', border: '1px solid #2A3A52' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = '#22D3EE'}
            onMouseLeave={e => e.currentTarget.style.borderColor = '#2A3A52'}>
            ⚡ Config IA
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardTitle>📋 Datos del puesto</CardTitle>
            <OllamaStatus status={ollamaStatus} />
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Nombre del puesto</label>
                <input className={inputClass} style={inputStyle}
                  placeholder="ej: Analista de Datos Senior"
                  value={form.nombre_puesto}
                  onChange={e => setForm(f => ({ ...f, nombre_puesto: e.target.value }))}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'} />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Requisitos</label>
                <textarea className={inputClass}
                  style={{ ...inputStyle, resize: 'vertical', minHeight: 200, lineHeight: 1.8 }}
                  placeholder={'- 3 años de experiencia\n- Python y SQL\n- Power BI\n- Inglés intermedio'}
                  value={form.requisitos}
                  onChange={e => setForm(f => ({ ...f, requisitos: e.target.value }))}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'} />
                <p className="text-xs text-slate-600 mt-1.5">Un requisito por línea → mejor análisis.</p>
              </div>
            </div>
          </Card>

          <div className="flex flex-col gap-4">
            <Card className="flex-1">
              <CardTitle>📎 CVs en PDF ({files.length})</CardTitle>
              <div {...getRootProps()} className="rounded-xl p-8 text-center cursor-pointer transition-all mb-4"
                style={{ border: '2px dashed ' + (isDragActive ? '#22D3EE' : '#2A3A52'),
                         background: isDragActive ? 'rgba(34,211,238,0.04)' : 'transparent' }}>
                <input {...getInputProps()} />
                <div className="text-4xl mb-3">{isDragActive ? '📂' : '📁'}</div>
                <div className="font-semibold text-white text-sm mb-1">
                  {isDragActive ? 'Soltá los archivos' : 'Arrastrá los CVs aquí'}
                </div>
                <div className="text-xs text-slate-500">Solo PDF · Máx. 10 MB · Hasta 20 CVs</div>
              </div>
              {files.length > 0 && (
                <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                  {files.map(f => (
                    <div key={f.name} className="flex items-center gap-3 px-3 py-2 rounded-xl"
                      style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
                        style={{ background: 'rgba(248,113,113,0.12)', color: '#F87171' }}>PDF</div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-white truncate">{f.name}</div>
                        <div className="text-xs text-slate-500">{(f.size / 1024).toFixed(0)} KB</div>
                      </div>
                      <button onClick={() => setFiles(prev => prev.filter(x => x.name !== f.name))}
                        className="text-slate-600 hover:text-red-400 transition-all text-sm px-1">✕</button>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <button onClick={handleAnalizar}
              disabled={ollamaStatus && (!ollamaStatus.ollama_disponible || !ollamaStatus.modelo_disponible)}
              className="w-full py-4 rounded-xl font-black text-base transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'linear-gradient(135deg, #22D3EE, #06B6D4)', color: '#0A0F1A' }}
              onMouseEnter={e => !e.currentTarget.disabled && (e.currentTarget.style.filter = 'brightness(1.08)')}
              onMouseLeave={e => e.currentTarget.style.filter = ''}>
              🔍 Analizar {files.length > 0 ? files.length + ' CV' + (files.length !== 1 ? 's' : '') : 'CVs'} con IA Local
            </button>
          </div>
        </div>
      </PageContainer>
    </AppLayout>
  )
}
