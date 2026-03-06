import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import toast from 'react-hot-toast'

const NAV_ITEMS = [
  { to: '/dashboard',     icon: '📊', label: 'Dashboard' },
  { to: '/nuevo-analisis', icon: '📁', label: 'Nuevo análisis' },
]

const NAV_ADMIN = [
  { to: '/usuarios', icon: '👥', label: 'Usuarios' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    toast('Sesión cerrada.', { icon: '👋' })
    navigate('/login')
  }

  const initials = user?.nombre_completo
    ?.split(' ')
    .slice(0, 2)
    .map(n => n[0])
    .join('')
    .toUpperCase() || '??'

  const ROL_COLORS = {
    admin:      { color: '#A78BFA', bg: 'rgba(167,139,250,0.12)', label: '👑 Admin' },
    reclutador: { color: '#22D3EE', bg: 'rgba(34,211,238,0.12)',  label: '🔍 Reclutador' },
    supervisor: { color: '#94A3B8', bg: 'rgba(148,163,184,0.1)',  label: '👁 Supervisor' },
  }
  const rolInfo = ROL_COLORS[user?.rol] || ROL_COLORS.supervisor

  return (
    <aside className="flex flex-col h-full"
      style={{ width: 256, background: '#111827', borderRight: '1px solid #2A3A52', flexShrink: 0 }}>

      {/* Logo */}
      <div className="px-5 py-5 flex items-center gap-3" style={{ borderBottom: '1px solid #2A3A52' }}>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, rgba(34,211,238,0.25), rgba(74,222,128,0.15))', border: '1px solid rgba(34,211,238,0.3)' }}>
          🧠
        </div>
        <div>
          <div className="text-sm font-bold text-white">Sistema CV</div>
          <div className="text-xs text-slate-500">RR.HH · IA Local</div>
        </div>
      </div>

      {/* Nav principal */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="text-xs font-bold text-slate-600 uppercase tracking-widest px-3 mb-3">Principal</p>

        {NAV_ITEMS.map(item => (
          <NavLink key={item.to} to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                isActive
                  ? 'text-cyan-400'
                  : 'text-slate-400 hover:text-white hover:bg-[#1A2235]'
              }`
            }
            style={({ isActive }) => isActive ? { background: 'rgba(34,211,238,0.08)' } : {}}
          >
            <span className="text-base w-5 text-center">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}

        {/* Admin section */}
        {user?.rol === 'admin' && (
          <>
            <p className="text-xs font-bold text-slate-600 uppercase tracking-widest px-3 mt-5 mb-3">
              Administración
            </p>
            {NAV_ADMIN.map(item => (
              <NavLink key={item.to} to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                    isActive ? 'text-cyan-400' : 'text-slate-400 hover:text-white hover:bg-[#1A2235]'
                  }`
                }
                style={({ isActive }) => isActive ? { background: 'rgba(34,211,238,0.08)' } : {}}
              >
                <span className="text-base w-5 text-center">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* User info + logout */}
      <div className="px-3 py-4" style={{ borderTop: '1px solid #2A3A52' }}>
        <div className="flex items-center gap-3 px-2 py-2 rounded-xl mb-2">
          <div className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #22D3EE, #4ADE80)', color: '#0A0F1A' }}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-white truncate">{user?.nombre_completo}</div>
            <span className="text-xs px-2 py-0.5 rounded-full font-semibold"
              style={{ background: rolInfo.bg, color: rolInfo.color }}>
              {rolInfo.label}
            </span>
          </div>
        </div>

        <button onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-semibold text-slate-500 hover:text-red-400 hover:bg-[#1A2235] transition-all">
          <span className="text-base">🚪</span>
          Cerrar sesión
        </button>
      </div>
    </aside>
  )
}
