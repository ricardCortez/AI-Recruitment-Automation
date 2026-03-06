import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute() {
  const { user, token, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0F1A] flex items-center justify-content-center">
        <div className="w-10 h-10 border-4 border-[#2A3A52] border-t-cyan-400 rounded-full animate-spin" />
      </div>
    )
  }

  if (!token || !user) return <Navigate to="/login" replace />

  return <Outlet />
}
