import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [form, setForm]       = useState({ username: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [showPass, setShowPass] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.username || !form.password) {
      toast.error('Completá usuario y contraseña.')
      return
    }
    setLoading(true)
    try {
      const data = await login(form.username, form.password)
      if (data.debe_cambiar_clave) {
        toast('Debés cambiar tu contraseña.', { icon: '🔑' })
      }
      navigate('/dashboard')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Error al iniciar sesión.'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0A0F1A] flex items-center justify-center px-4"
      style={{ background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(34,211,238,0.07) 0%, transparent 60%), #0A0F1A' }}>

      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-4"
            style={{ background: 'linear-gradient(135deg, rgba(34,211,238,0.2), rgba(74,222,128,0.15))', border: '1px solid rgba(34,211,238,0.3)' }}>
            <span className="text-2xl">🧠</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Sistema CV</h1>
          <p className="text-sm text-slate-500 mt-1">Análisis automatizado de candidatos</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl p-8" style={{ background: '#111827', border: '1px solid #2A3A52' }}>

          <div className="mb-6">
            <h2 className="text-xl font-bold text-white">Bienvenido</h2>
            <p className="text-sm text-slate-400 mt-1">Ingresá con tus credenciales para continuar</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Usuario */}
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                Usuario
              </label>
              <input
                type="text"
                autoComplete="username"
                placeholder="nombre.apellido"
                value={form.username}
                onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                className="w-full px-4 py-3 rounded-xl text-white placeholder-slate-600 text-sm focus:outline-none transition-colors"
                style={{ background: '#1A2235', border: '1.5px solid #2A3A52' }}
                onFocus={e => e.target.style.borderColor = '#22D3EE'}
                onBlur={e => e.target.style.borderColor = '#2A3A52'}
              />
            </div>

            {/* Contraseña */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                  Contraseña
                </label>
                <Link to="/recuperar-clave"
                  className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">
                  ¿Olvidaste tu clave?
                </Link>
              </div>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  className="w-full px-4 py-3 rounded-xl text-white placeholder-slate-600 text-sm focus:outline-none transition-colors pr-11"
                  style={{ background: '#1A2235', border: '1.5px solid #2A3A52' }}
                  onFocus={e => e.target.style.borderColor = '#22D3EE'}
                  onBlur={e => e.target.style.borderColor = '#2A3A52'}
                />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors text-lg">
                  {showPass ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {/* Botón */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl font-bold text-sm tracking-wide transition-all mt-2 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ background: loading ? '#155e75' : '#22D3EE', color: '#0A0F1A' }}
              onMouseEnter={e => !loading && (e.target.style.filter = 'brightness(1.1)')}
              onMouseLeave={e => e.target.style.filter = ''}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-[#0A0F1A] border-t-transparent rounded-full animate-spin" />
                  Ingresando...
                </span>
              ) : 'Ingresar al sistema →'}
            </button>

          </form>

          {/* Roles */}
          <div className="mt-6 pt-5" style={{ borderTop: '1px solid #2A3A52' }}>
            <p className="text-xs text-slate-600 text-center mb-3 uppercase tracking-widest font-bold">Roles del sistema</p>
            <div className="flex gap-2 justify-center flex-wrap">
              {[
                { label: '👑 Administrador', color: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.25)', text: '#A78BFA' },
                { label: '🔍 Reclutador',   color: 'rgba(34,211,238,0.12)',  border: 'rgba(34,211,238,0.25)',  text: '#22D3EE' },
                { label: '👁 Supervisor',   color: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)',  text: '#94A3B8' },
              ].map(r => (
                <span key={r.label} className="px-3 py-1 rounded-full text-xs font-semibold"
                  style={{ background: r.color, border: `1px solid ${r.border}`, color: r.text }}>
                  {r.label}
                </span>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  )
}
