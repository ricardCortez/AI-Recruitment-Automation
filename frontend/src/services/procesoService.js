import api from './api'

export const userService = {
  listar: ()               => api.get('/users/'),
  crear:  (data)           => api.post('/users/', data),
  editar: (id, data)       => api.put(`/users/${id}`, data),
  resetearClave: (id)      => api.post(`/users/${id}/resetear-clave`),
}

export const procesoService = {
  listar:  ()              => api.get('/procesos/'),
  crear:   (data)          => api.post('/procesos/', data),
  obtener: (id)            => api.get(`/procesos/${id}`),
  ranking: (id)            => api.get(`/procesos/${id}/ranking`),
}

export const cvsService = {
  subirCVs: (procesoId, formData) =>
    api.post(`/cvs/${procesoId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  analizar: (procesoId, forzar = false) =>
    api.post(`/cvs/${procesoId}/analizar?forzar=${forzar}`),
  cancelar:        (procesoId)           => api.post(`/cvs/${procesoId}/cancelar`),
  estado:          (procesoId)           => api.get(`/cvs/${procesoId}/estado`),
  actualizarNombre: (candidatoId, nombre) =>
    api.patch(`/cvs/${candidatoId}/nombre`, { nombre }),
}

export const reportesService = {
  exportarExcel: (procesoId) =>
    api.get(`/reportes/${procesoId}/excel`, { responseType: 'blob' }),
}
