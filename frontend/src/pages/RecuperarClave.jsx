import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authService } from '../services/authService'
import toast from 'react-hot-toast'

const METODOS = [
  {
    id: 'admin',
    icon: '👑',
    titulo: 'Reset por Administrador',
    desc: 'El administrador genera una contraseña temporal desde su panel.',
    color: '#A78BFA',
    bg: 'rgba(167,139,250,0.08)',
    border: 'rgba(167,139,250,0.3)',
  },
  {
    id: 'codigo',
    icon: '🔑',
    titulo: 'Código de Recuperación',
    desc: 'Usá el código de 12 caracteres que recibiste al crear tu cuenta.',
    color: '#FACC15',
    bg: 'rgba(250,204,21,0.08)',
    border: 'rgba(250,204,21,0.3)',
  },
  {
    id: 'totp',
    icon: '📱',
    titulo: 'Google Authenticator',
    desc: 'Ingresá el código de 6 dígitos que muestra la app en tu celular.',
    color: '#22D3EE',
    bg: 'rgba(34,211,238,0.08)',
    border: 'rgba(34,211,238,0.3)',
  },
]

export default function RecuperarClave() {
  const [metodo, setMetodo]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [exito, setExito]         = useState(false)
  const [form, setForm] = useState({
    username: '', recovery_code: '', totp_code: '', nueva_password: '',
  })

  const f = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (metodo === 'codigo') {
        await authService.recuperarConCodigo(form.username, form.recovery_code, form.nueva_password)
      } else if (metodo === 'totp') {
        await authService.recuperarConTotp(form.username, form.totp_code, form.nueva_password)
      }
      setExito(true)
      toast.success('Contraseña restablecida correctamente.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al restablecer la contraseña.')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = "w-full px-4 py-3 rounded-xl text-white placeholder-slate-600 text-sm focus:outline-none"
  const inputStyle = { background: '#1A2235', border: '1.5px solid #2A3A52' }

  return (
    <div className="min-h-screen bg-[#0A0F1A] flex items-center justify-center px-4"
      style={{ background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(250,204,21,0.05) 0%, transparent 60%), #0A0F1A' }}>

      <div className="w-full max-w-lg">

        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-4"
            style={{ background: 'rgba(250,204,21,0.1)', border: '1px solid rgba(250,204,21,0.3)' }}>
            <span className="text-xl">🔓</span>
          </div>
          <h1 className="text-xl font-bold text-white">Recuperar acceso</h1>
          <p className="text-sm text-slate-500 mt-1">Sin internet ni correo electrónico</p>
        </div>

        <div className="rounded-2xl p-8" style={{ background: '#111827', border: '1px solid #2A3A52' }}>

          {exito ? (
            <div className="text-center py-6">
              <div className="text-5xl mb-4">✅</div>
              <h3 className="text-lg font-bold text-white mb-2">Contraseña restablecida</h3>
              <p className="text-sm text-slate-400 mb-6">Deberás cambiarla al ingresar por primera vez.</p>
              <Link to="/login"
                className="px-6 py-3 rounded-xl font-bold text-sm"
                style={{ background: '#22D3EE', color: '#0A0F1A' }}>
                Ir al login →
              </Link>
            </div>
          ) : (
            <>
              {/* Usuario siempre visible */}
              <div className="mb-5">
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Tu usuario</label>
                <input className={inputClass} style={inputStyle} placeholder="nombre.apellido"
                  value={form.username} onChange={f('username')} />
              </div>

              {/* Selector de método */}
              {!metodo ? (
                <>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Elegí un método</p>
                  <div className="space-y-3">
                    {METODOS.map(m => (
                      <button key={m.id} onClick={() => m.id !== 'admin' && setMetodo(m.id)}
                        className="w-full flex items-start gap-4 p-4 rounded-xl text-left transition-all"
                        style={{ background: m.bg, border: `1.5px solid ${m.border}`, opacity: m.id === 'admin' ? 0.5 : 1 }}>
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-xl"
                          style={{ background: `${m.bg}`, border: `1px solid ${m.border}` }}>
                          {m.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-bold text-sm" style={{ color: m.color }}>{m.titulo}</div>
                          <div className="text-xs text-slate-400 mt-1">{m.desc}</div>
                          {m.id === 'admin' && (
                            <div className="text-xs mt-1" style={{ color: m.color }}>Contactá al administrador directamente.</div>
                          )}
                        </div>
                        {m.id !== 'admin' && <span className="text-slate-600 text-lg mt-1">→</span>}
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <button type="button" onClick={() => setMetodo(null)}
                    className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 mb-2 transition-colors">
                    ← Cambiar método
                  </button>

                  {metodo === 'codigo' && (
                    <div>
                      <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                        Código de recuperación
                      </label>
                      <input className={inputClass} placeholder="XXXX-XXXX-XXXX"
                        value={form.recovery_code} onChange={f('recovery_code')}
                        style={{ ...inputStyle, fontFamily: 'monospace', letterSpacing: '0.15em', fontSize: '16px' }} />
                    </div>
                  )}

                  {metodo === 'totp' && (
                    <div>
                      <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                        Código Google Authenticator
                      </label>
                    <input className={inputClass} placeholder="000000"
                        maxLength={6} value={form.totp_code} onChange={f('totp_code')}
                        style={{ ...inputStyle, fontFamily: 'monospace', letterSpacing: '0.4em', fontSize: '22px', textAlign: 'center' }} />
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                      Nueva contraseña
                    </label>
                    <input type="password" className={inputClass} style={inputStyle}
                      placeholder="Mínimo 8 caracteres"
                      value={form.nueva_password} onChange={f('nueva_password')} />
                  </div>

                  <button type="submit" disabled={loading}
                    className="w-full py-3 rounded-xl font-bold text-sm disabled:opacity-60 mt-2"
                    style={{ background: '#22D3EE', color: '#0A0F1A' }}>
                    {loading ? 'Procesando...' : 'Restablecer contraseña →'}
                  </button>
                </form>
              )}

              <div className="mt-5 pt-4 flex justify-center" style={{ borderTop: '1px solid #2A3A52' }}>
                <Link to="/login" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                  ← Volver al login
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
