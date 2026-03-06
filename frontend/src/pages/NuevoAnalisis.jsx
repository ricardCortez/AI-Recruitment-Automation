import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { procesoService, cvsService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Spinner } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

export default function NuevoAnalisis() {
  const navigate = useNavigate()

  const [form, setForm]       = useState({ nombre_puesto: '', requisitos: '' })
  const [files, setFiles]     = useState([])
  const [paso, setPaso]       = useState('form') // 'form' | 'analizando' | 'listo'
  const [progreso, setProgreso] = useState({ completado: 0, total: 0, items: [] })
  const [procesoId, setProcesoId] = useState(null)

  // Dropzone
  const onDrop = useCallback((accepted) => {
    const nuevos = accepted.filter(f => !files.find(e => e.name === f.name))
    setFiles(prev => [...prev, ...nuevos])
  }, [files])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 20,
  })

  const quitarArchivo = (name) => setFiles(prev => prev.filter(f => f.name !== name))

  const handleAnalizar = async () => {
    if (!form.nombre_puesto.trim()) return toast.error('Ingresá el nombre del puesto.')
    if (!form.requisitos.trim())   return toast.error('Ingresá los requisitos del puesto.')
    if (files.length === 0)        return toast.error('Agregá al menos un CV en PDF.')

    try {
      setPaso('analizando')
      setProgreso({ completado: 0, total: files.length, items: files.map(f => ({ nombre: f.name, estado: 'pendiente' })) })

      // 1. Crear proceso
      const { data: proceso } = await procesoService.crear(form)
      setProcesoId(proceso.id)

      // 2. Subir PDFs
      const fd = new FormData()
      files.forEach(f => fd.append('files', f))
      await cvsService.subirCVs(proceso.id, fd)

      // 3. Disparar análisis
      await cvsService.analizar(proceso.id)

      // 4. Polling del estado
      await pollEstado(proceso.id)

    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al iniciar el análisis.')
      setPaso('form')
    }
  }

  const pollEstado = async (id) => {
    const MAX_INTENTOS = 120
    let intentos = 0

    const check = async () => {
      try {
        const { data } = await cvsService.estado(id)
        setProgreso(prev => ({
          ...prev,
          completado: data.completado,
          total: data.total,
          items: prev.items.map((item, i) => ({
            ...item,
            estado: i < data.completado ? 'completado'
                  : i === data.completado ? 'procesando'
                  : 'pendiente',
          }))
        }))

        if (data.listo) {
          setPaso('listo')
          return
        }

        intentos++
        if (intentos < MAX_INTENTOS) {
          setTimeout(check, 2000)
        } else {
          toast.error('El análisis tardó demasiado. Revisá los resultados manualmente.')
          setPaso('listo')
        }
      } catch {
        setTimeout(check, 3000)
      }
    }
    await check()
  }

  const inputClass = "w-full px-4 py-3 rounded-xl text-white placeholder-slate-600 text-sm focus:outline-none"
  const inputStyle = { background: '#1A2235', border: '1.5px solid #2A3A52' }

  // ── Vista: Analizando ─────────────────────────────────────────────────
  if (paso === 'analizando' || paso === 'listo') {
    return (
      <AppLayout>
        <div className="p-8 max-w-2xl mx-auto">
          <div className="text-center mb-8">
            {paso === 'analizando' ? (
              <>
                <div className="flex justify-center mb-5">
                  <Spinner size={16} />
                </div>
                <h2 className="text-2xl font-black text-white mb-2">Analizando CVs con IA local</h2>
                <p className="text-slate-400 text-sm">
                  Ollama · Llama 3.1 8B · Sin enviar datos a internet
                </p>
              </>
            ) : (
              <>
                <div className="text-6xl mb-4">✅</div>
                <h2 className="text-2xl font-black text-white mb-2">¡Análisis completado!</h2>
                <p className="text-slate-400 text-sm">Todos los CVs fueron procesados.</p>
              </>
            )}
          </div>

          <Card className="mb-6">
            <CardTitle>📄 Progreso por CV</CardTitle>

            {/* Barra general */}
            <div className="mb-5">
              <div className="flex justify-between text-xs text-slate-400 mb-2">
                <span>{progreso.completado} de {progreso.total} completados</span>
                <span>{Math.round((progreso.completado / Math.max(progreso.total, 1)) * 100)}%</span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: '#2A3A52' }}>
                <div className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${(progreso.completado / Math.max(progreso.total, 1)) * 100}%`, background: '#22D3EE' }} />
              </div>
            </div>

            {/* Lista */}
            <div className="space-y-2">
              {progreso.items.map((item, i) => (
                <div key={i} className="flex items-center gap-3 py-2.5 px-3 rounded-xl"
                  style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                  <div className="w-7 h-7 rounded-full flex items-center justify-center text-sm flex-shrink-0"
                    style={{
                      background: item.estado === 'completado' ? 'rgba(74,222,128,0.15)'
                                : item.estado === 'procesando' ? 'rgba(34,211,238,0.15)'
                                : '#1F2D42',
                      color: item.estado === 'completado' ? '#4ADE80'
                           : item.estado === 'procesando' ? '#22D3EE'
                           : '#475569',
                    }}>
                    {item.estado === 'completado' ? '✓'
                   : item.estado === 'procesando' ? <span className="animate-pulse">⟳</span>
                   : '○'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-white truncate font-medium">{item.nombre}</div>
                  </div>
                  <span className="text-xs font-semibold flex-shrink-0"
                    style={{ color: item.estado === 'completado' ? '#4ADE80' : item.estado === 'procesando' ? '#22D3EE' : '#475569' }}>
                    {item.estado === 'completado' ? 'Listo'
                   : item.estado === 'procesando' ? 'Procesando...'
                   : 'En espera'}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {paso === 'listo' && (
            <button onClick={() => navigate(`/resultados/${procesoId}`)}
              className="w-full py-4 rounded-xl font-black text-base transition-all"
              style={{ background: '#22D3EE', color: '#0A0F1A' }}>
              Ver ranking de candidatos →
            </button>
          )}
        </div>
      </AppLayout>
    )
  }

  // ── Vista: Formulario ─────────────────────────────────────────────────
  return (
    <AppLayout>
      <div className="p-8 max-w-5xl">

        <div className="mb-8">
          <h1 className="text-3xl font-black text-white tracking-tight">Nuevo proceso de selección</h1>
          <p className="text-slate-400 mt-1">Cargá los CVs y definí el perfil requerido</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Columna izquierda — Datos del puesto */}
          <Card>
            <CardTitle>📋 Datos del puesto</CardTitle>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                  Nombre del puesto
                </label>
                <input className={inputClass} style={inputStyle}
                  placeholder="ej: Analista de Datos Senior"
                  value={form.nombre_puesto}
                  onChange={e => setForm(f => ({ ...f, nombre_puesto: e.target.value }))}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'} />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                  Requisitos del perfil
                </label>
                <textarea className={inputClass} style={{ ...inputStyle, resize: 'vertical', minHeight: 200, lineHeight: 1.7 }}
                  placeholder={"Ej:\n- 3 años de experiencia en análisis de datos\n- Dominio de Python y SQL\n- Power BI o Tableau\n- Inglés intermedio"}
                  value={form.requisitos}
                  onChange={e => setForm(f => ({ ...f, requisitos: e.target.value }))}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'} />
                <p className="text-xs text-slate-600 mt-1.5">
                  Escribí un requisito por línea para mejor análisis.
                </p>
              </div>
            </div>
          </Card>

          {/* Columna derecha — Archivos */}
          <div className="flex flex-col gap-4">
            <Card className="flex-1">
              <CardTitle>📎 CVs en PDF</CardTitle>

              {/* Dropzone */}
              <div {...getRootProps()}
                className="rounded-xl p-8 text-center cursor-pointer transition-all"
                style={{
                  border: `2px dashed ${isDragActive ? '#22D3EE' : '#2A3A52'}`,
                  background: isDragActive ? 'rgba(34,211,238,0.04)' : 'rgba(255,255,255,0.01)',
                }}>
                <input {...getInputProps()} />
                <div className="text-4xl mb-3">📂</div>
                <div className="font-semibold text-white text-sm mb-1">
                  {isDragActive ? 'Soltá los archivos acá' : 'Arrastrá los CVs aquí'}
                </div>
                <div className="text-xs text-slate-500">o hacé clic para seleccionar · Solo PDF · Máx. 10 MB c/u</div>
              </div>

              {/* Lista de archivos */}
              {files.length > 0 && (
                <div className="mt-4 space-y-2">
                  {files.map(f => (
                    <div key={f.name} className="flex items-center gap-3 px-3 py-2.5 rounded-xl"
                      style={{ background: '#1A2235', border: '1px solid #2A3A52' }}>
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
                        style={{ background: 'rgba(248,113,113,0.12)', color: '#F87171' }}>
                        PDF
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">{f.name}</div>
                        <div className="text-xs text-slate-500">{(f.size / 1024).toFixed(0)} KB</div>
                      </div>
                      <button onClick={() => quitarArchivo(f.name)}
                        className="w-6 h-6 rounded-full flex items-center justify-center text-slate-600 hover:text-red-400 hover:bg-red-400/10 transition-all text-sm flex-shrink-0">
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Botón analizar */}
            <button onClick={handleAnalizar}
              className="w-full py-4 rounded-xl font-black text-base transition-all flex items-center justify-center gap-3"
              style={{ background: 'linear-gradient(135deg, #22D3EE, #06B6D4)', color: '#0A0F1A' }}
              onMouseEnter={e => e.currentTarget.style.filter = 'brightness(1.08) saturate(1.1)'}
              onMouseLeave={e => e.currentTarget.style.filter = ''}>
              🔍 Analizar {files.length > 0 ? `${files.length} CV${files.length !== 1 ? 's' : ''}` : 'CVs'} con IA Local
            </button>
          </div>

        </div>
      </div>
    </AppLayout>
  )
}
