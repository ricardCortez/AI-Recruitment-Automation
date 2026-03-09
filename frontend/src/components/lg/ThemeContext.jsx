import { createContext, useContext, useState } from 'react'
import { DARK, LIGHT } from './theme'

const ThemeCtx = createContext(null)

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => {
    try { return localStorage.getItem('rrhh-theme') !== 'light' }
    catch { return true }
  })

  const toggle = () => setIsDark(d => {
    const next = !d
    try { localStorage.setItem('rrhh-theme', next ? 'dark' : 'light') } catch {}
    return next
  })

  return (
    <ThemeCtx.Provider value={{ T: isDark ? DARK : LIGHT, isDark, toggle }}>
      {children}
    </ThemeCtx.Provider>
  )
}

export const useTheme = () => useContext(ThemeCtx)
