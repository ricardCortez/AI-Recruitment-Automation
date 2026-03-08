import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'

import ProtectedRoute  from './components/layout/ProtectedRoute'
import Login           from './pages/Login'
import RecuperarClave  from './pages/RecuperarClave'
import Dashboard       from './pages/Dashboard'
import NuevoAnalisis   from './pages/NuevoAnalisis'
import Resultados      from './pages/Resultados'
import DetalleCandidato from './pages/DetalleCandidato'
import Usuarios        from './pages/Usuarios'
import CrearUsuario    from './pages/CrearUsuario'
import Perfil          from './pages/Perfil'
import Configuracion   from './pages/Configuracion'
import { AnalisisProvider } from './context/AnalisisContext'

export default function App() {
  return (
    <AuthProvider>
      <AnalisisProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: '#1A2235', color: '#F1F5F9', border: '1px solid #2A3A52' },
            success: { iconTheme: { primary: '#4ADE80', secondary: '#0A0F1A' } },
            error:   { iconTheme: { primary: '#F87171', secondary: '#0A0F1A' } },
          }}
        />
        <Routes>
          {/* Públicas */}
          <Route path="/login"          element={<Login />} />
          <Route path="/recuperar-clave" element={<RecuperarClave />} />

          {/* Protegidas */}
          <Route element={<ProtectedRoute />}>
            <Route path="/"                            element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"                   element={<Dashboard />} />
            <Route path="/nuevo-analisis"              element={<NuevoAnalisis />} />
            <Route path="/resultados/:procesoId"       element={<Resultados />} />
            <Route path="/resultados/:procesoId/candidato/:candidatoId" element={<DetalleCandidato />} />
            <Route path="/usuarios"                    element={<Usuarios />} />
            <Route path="/usuarios/nuevo"              element={<CrearUsuario />} />
            <Route path="/perfil"                      element={<Perfil />} />
            <Route path="/configuracion"               element={<Configuracion />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      </AnalisisProvider>
    </AuthProvider>
  )
}
