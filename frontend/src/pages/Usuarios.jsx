import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { userService } from '../services/procesoService'
import AppLayout from '../components/layout/AppLayout'
import { Card, Badge, Spinner, EmptyState, PageContainer } from '../components/ui/index.jsx'
import toast from 'react-hot-toast'

const ROL_VARIANT = { admin: 'purple', reclutador: 'cyan', supervisor: 'default' }
const ROL_LABEL   = { admin: '👑 Admin', reclutador: '🔍 Reclutador', supervisor: '👁 Supervisor' }

export default function Usuarios() {
  const navigate = useNavigate()
  const [users, setUsers]   = useState([])
  const [loading, setLoading] = useState(true)

  const cargar = () => {
    userService.listar()
      .then(r => setUsers(r.data))
      .catch(() => toast.error('Error cargando usuarios.'))
      .finally(() => setLoading(false))
  }

  useEffect(cargar, [])

  const toggleActivo = async (user) => {
    try {
      await userService.editar(user.id, { activo: !user.activo })
      toast.success(`Usuario ${user.activo ? 'desactivado' : 'activado'}.`)
      cargar()
    } catch {
      toast.error('Error actualizando usuario.')
    }
  }

  const resetearClave = async (user) => {
    if (!confirm(`¿Resetear la clave de ${user.nombre_completo}?`)) return
    try {
      const { data } = await userService.resetearClave(user.id)
      toast.success(`Clave temporal: ${data.password_temporal}`, { duration: 8000 })
    } catch {
      toast.error('Error reseteando clave.')
    }
  }

  return (
    <AppLayout>
      <PageContainer>

        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-black text-white tracking-tight">Gestión de Usuarios</h1>
            <p className="text-slate-400 mt-1">Controlá accesos, roles y seguridad</p>
          </div>
          <button onClick={() => navigate('/usuarios/nuevo')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all"
            style={{ background: '#22D3EE', color: '#0A0F1A' }}
            onMouseEnter={e => e.currentTarget.style.filter = 'brightness(1.1)'}
            onMouseLeave={e => e.currentTarget.style.filter = ''}>
            + Nuevo usuario
          </button>
        </div>

        <Card>
          {loading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : users.length === 0 ? (
            <EmptyState icon="👥" title="Sin usuarios" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    {['Usuario', 'Nombre', 'Rol', '2FA', 'Estado', 'Último acceso', 'Acciones'].map(h => (
                      <th key={h} className="text-left text-xs font-bold text-slate-600 uppercase tracking-widest pb-4 pr-4 whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#2A3A52]">
                  {users.map(u => (
                    <tr key={u.id} className="group">
                      <td className="py-4 pr-4">
                        <span className="text-sm font-mono text-slate-300">{u.username}</span>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                            style={{ background: `hsl(${u.id * 73 % 360}, 55%, 45%)`, color: 'white' }}>
                            {u.nombre_completo.split(' ').slice(0, 2).map(n => n[0]).join('')}
                          </div>
                          <span className="text-sm text-white font-medium">{u.nombre_completo}</span>
                        </div>
                      </td>
                      <td className="py-4 pr-4">
                        <Badge variant={ROL_VARIANT[u.rol]}>{ROL_LABEL[u.rol]}</Badge>
                      </td>
                      <td className="py-4 pr-4">
                        <Badge variant={u.totp_activo ? 'green' : 'default'}>
                          {u.totp_activo ? '✓ Activo' : '— No'}
                        </Badge>
                      </td>
                      <td className="py-4 pr-4">
                        <Badge variant={u.activo ? 'green' : 'red'}>
                          {u.activo ? 'Activo' : 'Inactivo'}
                        </Badge>
                      </td>
                      <td className="py-4 pr-4">
                        <span className="text-xs text-slate-500">
                          {u.ultimo_acceso
                            ? new Date(u.ultimo_acceso).toLocaleString('es-PE', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
                            : 'Nunca'}
                        </span>
                      </td>
                      <td className="py-4">
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => resetearClave(u)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                            style={{ background: '#1A2235', color: '#94A3B8', border: '1px solid #2A3A52' }}
                            onMouseEnter={e => { e.target.style.borderColor = '#22D3EE'; e.target.style.color = '#22D3EE' }}
                            onMouseLeave={e => { e.target.style.borderColor = '#2A3A52'; e.target.style.color = '#94A3B8' }}>
                            Resetear clave
                          </button>
                          {u.username !== 'admin' && (
                            <button onClick={() => toggleActivo(u)}
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                              style={{ background: '#1A2235', color: u.activo ? '#F87171' : '#4ADE80', border: `1px solid ${u.activo ? 'rgba(248,113,113,0.3)' : 'rgba(74,222,128,0.3)'}` }}>
                              {u.activo ? 'Desactivar' : 'Activar'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </PageContainer>
    </AppLayout>
  )
}
