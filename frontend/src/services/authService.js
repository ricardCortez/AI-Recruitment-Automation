import api from './api'

export const authService = {
  login: (username, password) =>
    api.post('/auth/login', { username, password }),

  cambiarClave: (password_actual, password_nueva) =>
    api.post('/auth/cambiar-clave', { password_actual, password_nueva }),

  recuperarConCodigo: (username, recovery_code, nueva_password) =>
    api.post('/auth/recuperar/codigo', { username, recovery_code, nueva_password }),

  recuperarConTotp: (username, totp_code, nueva_password) =>
    api.post('/auth/recuperar/totp', { username, totp_code, nueva_password }),

  getTotpSetup: () =>
    api.get('/auth/totp/setup'),

  confirmarTotp: (totp_code) =>
    api.post('/auth/totp/confirmar', { totp_code }),

  getMe: () =>
    api.get('/auth/me'),
}
