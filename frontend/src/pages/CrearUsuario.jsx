import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { userService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

export default function CrearUsuario() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', nombre_completo: '', password: '', rol: 'reclutador' })
  const [loading, setLoading]   = useState(false)
  const [resultado, setResultado] = useState(null) // datos del usuario creado

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.username || !form.nombre_completo || !form.password) {
      return toast.error('Completá todos los campos.')
    }
    setLoading(true)
    try {
      const { data } = await userService.crear(form)
      setResultado(data)
      toast.success('Usuario creado correctamente.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error creando usuario.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = "w-full px-4 py-3 rounded-xl text-white placeholder-slate-600 text-sm focus:outline-none"
  const inputStyle = { background: '#1A2235', border: '1.5px solid #2A3A52' }

  // ── Vista: Usuario creado ─────────────────────────────────────────────
  if (resultado) {
    return (
      <AppLayout>
        <div className="p-8 max-w-2xl">
          <div className="text-center mb-6">
            <div className="text-5xl mb-3">✅</div>
            <h2 className="text-2xl font-black text-white">Usuario creado</h2>
            <p className="text-slate-400 mt-1 text-sm">Guardá esta información — no se vuelve a mostrar</p>
          </div>

          <Card className="mb-4" style={{ border: '1px solid rgba(250,204,21,0.3)', background: 'rgba(250,204,21,0.03)' }}>
            <CardTitle>🔑 Código de recuperación único</CardTitle>
            <p className="text-xs text-slate-400 mb-3">
              El usuario debe guardar este código. Sirve para recuperar el acceso sin internet.
            </p>
            <div className="text-center py-3 px-4 rounded-xl text-2xl font-bold tracking-widest"
              style={{ background: '#0A0F1A', border: '1px solid #2A3A52', fontFamily: 'monospace', color: '#FACC15' }}>
              {resultado.recovery_code}
            </div>
          </Card>

          <Card className="mb-6">
            <CardTitle>📱 Google Authenticator (2FA)</CardTitle>
            <p className="text-xs text-slate-400 mb-4">
              El usuario escanea este QR con Google Authenticator para activar el 2FA.
            </p>
            <div className="flex justify-center">
              <div className="p-4 rounded-xl bg-white">
                <img src={`data:image/png;base64,${resultado.totp_qr_base64}`}
                  alt="QR Google Authenticator" className="w-40 h-40" />
              </div>
            </div>
            <p className="text-xs text-slate-500 text-center mt-3">
              Opcional: el usuario puede activarlo cuando quiera desde su perfil.
            </p>
          </Card>

          <div className="flex gap-3">
            <button onClick={() => navigate('/usuarios')}
              className="flex-1 py-3 rounded-xl font-bold text-sm"
              style={{ background: '#22D3EE', color: '#0A0F1A' }}>
              ← Volver a usuarios
            </button>
            <button onClick={() => { setResultado(null); setForm({ username: '', nombre_completo: '', password: '', rol: 'reclutador' }) }}
              className="px-5 py-3 rounded-xl font-bold text-sm"
              style={{ background: '#1A2235', color: '#94A3B8', border: '1px solid #2A3A52' }}>
              Crear otro
            </button>
          </div>
        </div>
      </AppLayout>
    )
  }

  // ── Vista: Formulario ─────────────────────────────────────────────────
  return (
    <AppLayout>
      <div className="p-8 max-w-xl">

        <button onClick={() => navigate('/usuarios')}
          className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-5 transition-colors">
          ← Volver a usuarios
        </button>

        <h1 className="text-3xl font-black text-white tracking-tight mb-1">Crear usuario</h1>
        <p className="text-slate-400 text-sm mb-8">El usuario deberá cambiar su contraseña al primer ingreso.</p>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-5">

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Nombre completo</label>
                <input className={inputClass} style={inputStyle} placeholder="Ana Flores"
                  value={form.nombre_completo} onChange={f('nombre_completo')}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'} />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Usuario</label>
                <input className={inputClass} style={inputStyle} placeholder="a.flores"
                  value={form.username} onChange={f('username')}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'} />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Rol</label>
                <select className={inputClass} style={{ ...inputStyle, cursor: 'pointer', appearance: 'none' }}
                  value={form.rol} onChange={f('rol')}>
                  <option value="reclutador">🔍 Reclutador</option>
                  <option value="supervisor">👁 Supervisor</option>
                  <option value="admin">👑 Administrador</option>
                </select>
              </div>

              <div className="col-span-2">
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Contraseña temporal</label>
                <input type="text" className={inputClass} style={inputStyle} placeholder="Mínimo 8 caracteres"
                  value={form.password} onChange={f('password')}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'} />
                <p className="text-xs text-slate-600 mt-1.5">⚠️ Deberá cambiarla en el primer ingreso.</p>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl font-bold text-sm disabled:opacity-60 mt-2"
              style={{ background: '#22D3EE', color: '#0A0F1A' }}>
              {loading ? 'Creando...' : 'Crear usuario →'}
            </button>
          </form>
        </Card>
      </div>
    </AppLayout>
  )
}
