// Badge de rol / estado
export function Badge({ children, variant = 'default' }) {
  const variants = {
    default: { bg: 'rgba(148,163,184,0.1)', color: '#94A3B8', border: 'rgba(148,163,184,0.2)' },
    cyan:    { bg: 'rgba(34,211,238,0.1)',  color: '#22D3EE', border: 'rgba(34,211,238,0.25)' },
    green:   { bg: 'rgba(74,222,128,0.1)',  color: '#4ADE80', border: 'rgba(74,222,128,0.25)' },
    yellow:  { bg: 'rgba(250,204,21,0.1)',  color: '#FACC15', border: 'rgba(250,204,21,0.25)' },
    red:     { bg: 'rgba(248,113,113,0.1)', color: '#F87171', border: 'rgba(248,113,113,0.25)' },
    purple:  { bg: 'rgba(167,139,250,0.1)', color: '#A78BFA', border: 'rgba(167,139,250,0.25)' },
  }
  const s = variants[variant] || variants.default
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
      {children}
    </span>
  )
}

// Card contenedor
export function Card({ children, className = '', style = {} }) {
  return (
    <div className={`rounded-2xl p-6 ${className}`}
      style={{ background: '#111827', border: '1px solid #2A3A52', ...style }}>
      {children}
    </div>
  )
}

// Título de sección dentro de card
export function CardTitle({ children }) {
  return (
    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
      {children}
    </p>
  )
}

// Barra de puntaje de compatibilidad
export function ScoreBar({ value, height = 6 }) {
  const color = value >= 70 ? '#4ADE80' : value >= 50 ? '#FACC15' : '#F87171'
  return (
    <div className="w-full rounded-full overflow-hidden" style={{ height, background: '#2A3A52' }}>
      <div className="h-full rounded-full transition-all duration-700"
        style={{ width: `${value}%`, background: color }} />
    </div>
  )
}

// Número de puntaje grande
export function ScoreNumber({ value, size = 'md' }) {
  const color = value >= 70 ? '#4ADE80' : value >= 50 ? '#FACC15' : '#F87171'
  const sz = size === 'lg' ? 'text-5xl' : size === 'sm' ? 'text-xl' : 'text-3xl'
  return (
    <span className={`${sz} font-black`} style={{ color, fontFamily: 'monospace' }}>
      {value?.toFixed(0)}%
    </span>
  )
}

// Spinner de carga
export function Spinner({ size = 8 }) {
  return (
    <div className={`w-${size} h-${size} border-4 rounded-full animate-spin`}
      style={{ borderColor: '#2A3A52', borderTopColor: '#22D3EE' }} />
  )
}

// Estado vacío
export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      {description && <p className="text-sm text-slate-400 max-w-sm mb-6">{description}</p>}
      {action}
    </div>
  )
}
