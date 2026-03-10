import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { authService } from '../services/authService'
import AppLayout from '../components/layout/AppLayout'
import { Card, CardTitle, Badge, PageContainer } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

// ── Sección: Cambiar contraseña ───────────────────────────────────────────────
function CambiarClave() {
  const [form, setForm]   = useState({ password_actual: '', password_nueva: '', confirmar: '' })
  const [loading, setLoading] = useState(false)
  const [show, setShow]   = useState({ actual: false, nueva: false, confirmar: false })

  const f = k => e => setForm(p => ({ ...p, [k]: e.target.value }))
  const toggleShow = k => setShow(p => ({ ...p, [k]: !p[k] }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password_nueva.length < 8) return toast.error('La nueva contraseña debe tener al menos 8 caracteres.')
    if (form.password_nueva !== form.confirmar) return toast.error('Las contraseñas nuevas no coinciden.')
    setLoading(true)
    try {
      await authService.cambiarClave(form.password_actual, form.password_nueva)
      toast.success('Contraseña actualizada correctamente.')
      setForm({ password_actual: '', password_nueva: '', confirmar: '' })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cambiar la contraseña.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = { background: '#1A2235', border: '1.5px solid #2A3A52' }
  const inputClass = "w-full px-4 py-3 rounded-xl text-white placeholder-slate-600 text-sm focus:outline-none pr-11"

  const PasswordField = ({ label, field }) => (
    <div>
      <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">{label}</label>
      <div className="relative">
        <input
          type={show[field] ? 'text' : 'password'}
          className={inputClass}
          style={inputStyle}
          placeholder="••••••••"
          value={form[field]}
          onChange={f(field)}
          onFocus={e => e.target.style.borderColor = '#22D3EE'}
          onBlur={e => e.target.style.borderColor = '#2A3A52'}
        />
        <button type="button" onClick={() => toggleShow(field)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors">
          {show[field] ? '🙈' : '👁️'}
        </button>
      </div>
    </div>
  )

  return (
    <Card>
      <CardTitle>🔒 Cambiar contraseña</CardTitle>
      <form onSubmit={handleSubmit} className="space-y-4">
        <PasswordField label="Contraseña actual"  field="password_actual" />
        <PasswordField label="Nueva contraseña"   field="password_nueva" />
        <PasswordField label="Confirmar nueva"     field="confirmar" />

        {/* Indicador de fortaleza */}
        {form.password_nueva && (
          <div>
            <div className="flex gap-1 mb-1">
              {[1,2,3,4].map(i => {
                const fuerza = [
                  form.password_nueva.length >= 8,
                  /[A-Z]/.test(form.password_nueva),
                  /[0-9]/.test(form.password_nueva),
                  /[^A-Za-z0-9]/.test(form.password_nueva),
                ]
                const activos = fuerza.filter(Boolean).length
                return (
                  <div key={i} className="h-1 flex-1 rounded-full transition-all"
                    style={{ background: i <= activos
                      ? activos <= 1 ? '#F87171' : activos <= 2 ? '#FACC15' : activos <= 3 ? '#4ADE80' : '#22D3EE'
                      : '#2A3A52' }} />
                )
              })}
            </div>
            <p className="text-xs text-slate-500">Incluí mayúsculas, números y símbolos para mayor seguridad.</p>
          </div>
        )}

        <button type="submit" disabled={loading}
          className="w-full py-3 rounded-xl font-bold text-sm disabled:opacity-60 mt-2 transition-all"
          style={{ background: '#22D3EE', color: '#0A0F1A' }}
          onMouseEnter={e => !loading && (e.currentTarget.style.filter = 'brightness(1.08)')}
          onMouseLeave={e => e.currentTarget.style.filter = ''}>
          {loading ? 'Actualizando...' : 'Actualizar contraseña →'}
        </button>
      </form>
    </Card>
  )
}

// ── Sección: Google Authenticator 2FA ─────────────────────────────────────────
function Configurar2FA({ user }) {
  const [qr, setQr]             = useState(null)
  const [secret, setSecret]     = useState('')
  const [codigo, setCodigo]     = useState('')
  const [loading, setLoading]   = useState(false)
  const [qrLoading, setQrLoading] = useState(false)
  const [activo, setActivo]     = useState(user?.totp_activo || false)

  const generarQR = async () => {
    setQrLoading(true)
    try {
      const { data } = await authService.getTotpSetup()
      setQr(data.qr_base64)
      setSecret(data.secret)
    } catch {
      toast.error('Error generando el QR.')
    } finally {
      setQrLoading(false)
    }
  }

  const confirmar = async () => {
    if (codigo.length !== 6) return toast.error('Ingresá el código de 6 dígitos.')
    setLoading(true)
    try {
      await authService.confirmarTotp(codigo)
      setActivo(true)
      setQr(null)
      setCodigo('')
      toast.success('Google Authenticator activado correctamente.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Código incorrecto. Verificá la hora de tu dispositivo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardTitle>📱 Google Authenticator (2FA)</CardTitle>

      {/* Estado actual */}
      <div className="flex items-center justify-between p-4 rounded-xl mb-5"
        style={{ background: activo ? 'rgba(74,222,128,0.06)' : 'rgba(248,113,113,0.06)',
                 border: `1px solid ${activo ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)'}` }}>
        <div>
          <div className="font-bold text-sm text-white mb-0.5">
            {activo ? '✅ Autenticación de dos factores activa' : '❌ Autenticación de dos factores inactiva'}
          </div>
          <div className="text-xs text-slate-400">
            {activo
              ? 'Tu cuenta está protegida con Google Authenticator.'
              : 'Activá el 2FA para mayor seguridad en tu cuenta.'}
          </div>
        </div>
        <Badge variant={activo ? 'green' : 'red'}>{activo ? 'Activo' : 'Inactivo'}</Badge>
      </div>

      {!activo && !qr && (
        <>
          {/* Instrucciones */}
          <div className="space-y-3 mb-5">
            {[
              { n: '1', text: 'Instalá Google Authenticator en tu celular (Android o iOS).' },
              { n: '2', text: 'Hacé clic en "Generar QR" para obtener tu código de vinculación.' },
              { n: '3', text: 'Escaneá el QR desde la app y confirmá con el código de 6 dígitos.' },
            ].map(s => (
              <div key={s.n} className="flex items-start gap-3 text-sm text-slate-400">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5"
                  style={{ background: 'rgba(34,211,238,0.12)', color: '#22D3EE', border: '1px solid rgba(34,211,238,0.25)' }}>
                  {s.n}
                </div>
                {s.text}
              </div>
            ))}
          </div>

          <button onClick={generarQR} disabled={qrLoading}
            className="w-full py-3 rounded-xl font-bold text-sm disabled:opacity-60 transition-all"
            style={{ background: 'rgba(34,211,238,0.1)', color: '#22D3EE', border: '1px solid rgba(34,211,238,0.3)' }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(34,211,238,0.18)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(34,211,238,0.1)'}>
            {qrLoading ? 'Generando...' : '📲 Generar QR'}
          </button>
        </>
      )}

      {/* QR generado → escanear y confirmar */}
      {!activo && qr && (
        <div className="space-y-5">
          <div className="flex flex-col items-center gap-3">
            <div className="p-4 rounded-2xl bg-white">
              <img src={`data:image/png;base64,${qr}`} alt="QR Google Authenticator" className="w-44 h-44" />
            </div>
            <p className="text-xs text-slate-400 text-center max-w-xs">
              Escaneá este QR con Google Authenticator. Si no podés escanearlo, ingresá la clave manual:
            </p>
            <div className="px-4 py-2 rounded-xl text-xs font-mono tracking-widest"
              style={{ background: '#0A0F1A', color: '#22D3EE', border: '1px solid #2A3A52' }}>
              {secret}
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
              Código de verificación (6 dígitos)
            </label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              value={codigo}
              onChange={e => setCodigo(e.target.value.replace(/\D/g, ''))}
              className="w-full text-center py-3 rounded-xl text-white text-2xl font-bold tracking-widest focus:outline-none"
              style={{ background: '#1A2235', border: '1.5px solid #2A3A52', fontFamily: 'monospace',
                       borderColor: codigo.length === 6 ? '#22D3EE' : '#2A3A52' }}
            />
          </div>

          <div className="flex gap-3">
            <button onClick={confirmar} disabled={loading || codigo.length !== 6}
              className="flex-1 py-3 rounded-xl font-bold text-sm disabled:opacity-40 transition-all"
              style={{ background: '#22D3EE', color: '#0A0F1A' }}>
              {loading ? 'Verificando...' : '✓ Confirmar y activar'}
            </button>
            <button onClick={() => { setQr(null); setCodigo('') }}
              className="px-4 py-3 rounded-xl font-bold text-sm transition-all"
              style={{ background: '#1A2235', color: '#94A3B8', border: '1px solid #2A3A52' }}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Ya activo */}
      {activo && (
        <div className="text-center py-4">
          <div className="text-4xl mb-3">🛡️</div>
          <p className="text-sm text-slate-400">
            Tu cuenta está protegida. Cada vez que inicies sesión, podés usar el código de Google Authenticator para recuperar el acceso.
          </p>
        </div>
      )}
    </Card>
  )
}

// ── Página principal de Perfil ────────────────────────────────────────────────
export default function Perfil() {
  const { user } = useAuth()

  const ROL_CFG = {
    admin:      { label: '👑 Administrador', color: '#A78BFA', bg: 'rgba(167,139,250,0.1)',  border: 'rgba(167,139,250,0.25)' },
    reclutador: { label: '🔍 Reclutador',   color: '#22D3EE', bg: 'rgba(34,211,238,0.1)',   border: 'rgba(34,211,238,0.25)'  },
    supervisor: { label: '👁 Supervisor',   color: '#94A3B8', bg: 'rgba(148,163,184,0.08)', border: 'rgba(148,163,184,0.2)'  },
  }
  const rol = ROL_CFG[user?.rol] || ROL_CFG.supervisor
  const initials = user?.nombre_completo?.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase() || '??'

  return (
    <AppLayout>
      <PageContainer size="lg">

        <div className="mb-8">
          <h1 className="text-3xl font-black text-white tracking-tight">Mi perfil</h1>
          <p className="text-slate-400 mt-1">Seguridad y configuración de tu cuenta</p>
        </div>

        {/* Card de identidad */}
        <Card className="mb-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-black flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #22D3EE, #4ADE80)', color: '#0A0F1A' }}>
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xl font-black text-white mb-1">{user?.nombre_completo}</div>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-mono text-slate-400">@{user?.username}</span>
                <span className="px-3 py-1 rounded-full text-xs font-bold"
                  style={{ background: rol.bg, color: rol.color, border: `1px solid ${rol.border}` }}>
                  {rol.label}
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* Grid: Cambiar clave + 2FA */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CambiarClave />
          <Configurar2FA user={user} />
        </div>

      </PageContainer>
    </AppLayout>
  )
}
