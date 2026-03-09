import { useState } from 'react'
import { useTheme } from './ThemeContext'
import { blur, scoreColor, AC } from './theme'

// ─── GlassCard ────────────────────────────────────────────────────────────────
export function GlassCard({ children, style = {}, onClick, tint, blurPx = 22 }) {
  const { T } = useTheme()
  const [hov, setHov] = useState(false)
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov && onClick ? T.glassHover : T.glass,
        border: `1px solid ${tint ? tint + '30' : T.glassBorder}`,
        borderRadius: 16,
        boxShadow: T.shadow,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.18s ease',
        transform: hov && onClick ? 'translateY(-1px)' : 'none',
        ...blur(blurPx),
        ...style,
      }}
    >
      {children}
    </div>
  )
}

// ─── GlassRow (sidebar nav, listas) ──────────────────────────────────────────
export function GlassRow({ children, active, onClick, style = {} }) {
  const { T } = useTheme()
  const [hov, setHov] = useState(false)
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 11px', borderRadius: 10,
        cursor: onClick ? 'pointer' : 'default',
        background: active ? T.glassActive : hov ? T.glassHover : 'transparent',
        border: active ? `1px solid ${T.glassBorder}` : '1px solid transparent',
        boxShadow: active ? T.glassInset : 'none',
        transition: 'all 0.14s ease',
        ...blur(16),
        ...style,
      }}
    >
      {children}
    </div>
  )
}

// ─── Badge ────────────────────────────────────────────────────────────────────
export function LGBadge({ color = AC.blue, children }) {
  return (
    <span style={{
      fontSize: 10, padding: '2px 8px', borderRadius: 6, fontWeight: 600,
      background: color + '22', color, border: `1px solid ${color}30`,
      lineHeight: 1.6, display: 'inline-flex', alignItems: 'center',
    }}>
      {children}
    </span>
  )
}

// ─── ScoreRing ────────────────────────────────────────────────────────────────
export function ScoreRing({ score, size = 44 }) {
  const r = (size - 5) / 2
  const circ = 2 * Math.PI * r
  const fill = score != null ? Math.min(score, 100) / 100 * circ : 0
  const color = score != null ? scoreColor(score) : AC.teal
  const { T } = useTheme()
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={T.t4} strokeWidth={4}/>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={4}
        strokeDasharray={`${fill} ${circ}`} strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ filter: `drop-shadow(0 0 3px ${color}88)`, transition: 'stroke-dasharray 0.5s' }}/>
      <text x={size/2} y={size/2+1} textAnchor="middle" dominantBaseline="middle"
        fill={color} fontSize={size * 0.265} fontWeight={700} fontFamily="inherit">
        {score != null ? Math.round(score) : '—'}
      </text>
    </svg>
  )
}

// ─── ScoreBar ─────────────────────────────────────────────────────────────────
export function ScoreBar({ value, height = 5, style = {} }) {
  const { T } = useTheme()
  const color = scoreColor(value)
  return (
    <div style={{ height, background: T.t4, borderRadius: height, overflow: 'hidden', ...style }}>
      <div style={{ height: '100%', width: `${Math.min(value || 0, 100)}%`, borderRadius: height,
        background: `linear-gradient(90deg, ${color}, ${color}cc)`,
        boxShadow: `0 0 6px ${color}55`, transition: 'width 0.6s ease' }}/>
    </div>
  )
}

// ─── ProgressBar (genérica) ───────────────────────────────────────────────────
export function LGProgressBar({ pct, color = AC.blue, height = 5 }) {
  const { T } = useTheme()
  return (
    <div style={{ height, background: T.t4, borderRadius: height, overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${Math.min(pct || 0, 100)}%`, borderRadius: height,
        background: `linear-gradient(90deg, ${color}, ${color}bb)`,
        boxShadow: `0 0 6px ${color}44`, transition: 'width 0.6s ease' }}/>
    </div>
  )
}

// ─── Spinner ──────────────────────────────────────────────────────────────────
export function LGSpinner({ size = 22 }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      border: `2px solid rgba(128,128,128,0.18)`,
      borderTopColor: AC.blue,
      animation: 'lgspin 0.7s linear infinite',
      flexShrink: 0,
    }}/>
  )
}

// ─── SectionLabel ─────────────────────────────────────────────────────────────
export function SectionLabel({ children, style = {} }) {
  const { T } = useTheme()
  return (
    <div style={{ fontSize: 10, color: T.t3, letterSpacing: 1.2,
      textTransform: 'uppercase', fontWeight: 600, marginBottom: 10, ...style }}>
      {children}
    </div>
  )
}

// ─── ActionButton (outline coloreado) ────────────────────────────────────────
export function ActionButton({ color = AC.blue, onClick, disabled, children, style = {} }) {
  const [hov, setHov] = useState(false)
  return (
    <button
      onClick={onClick} disabled={disabled}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: '7px 14px', borderRadius: 10,
        border: `1px solid ${color}40`,
        background: hov && !disabled ? color + '28' : color + '16',
        color, fontSize: 12, fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.45 : 1,
        fontFamily: 'inherit', transition: 'all 0.14s',
        ...blur(14), ...style,
      }}
    >
      {children}
    </button>
  )
}

// ─── PrimaryButton ────────────────────────────────────────────────────────────
export function PrimaryButton({ onClick, disabled, children, style = {}, size = 'md' }) {
  const [hov, setHov] = useState(false)
  const pad = size === 'sm' ? '7px 16px' : size === 'lg' ? '13px 28px' : '9px 20px'
  return (
    <button
      onClick={onClick} disabled={disabled}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: pad, borderRadius: 11, border: 'none',
        background: hov && !disabled
          ? 'linear-gradient(135deg, #1C92FF, #0A84FF)'
          : 'linear-gradient(135deg, #0A84FF, #006EE0)',
        color: 'white', fontSize: size === 'sm' ? 12 : 13, fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        boxShadow: `0 4px 18px ${AC.blue}44`,
        fontFamily: 'inherit', transition: 'all 0.14s',
        ...style,
      }}
    >
      {children}
    </button>
  )
}

// ─── BackButton ───────────────────────────────────────────────────────────────
export function BackButton({ onClick, children = '← Volver' }) {
  const { T } = useTheme()
  const [hov, setHov] = useState(false)
  return (
    <button onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: 'none', border: 'none', cursor: 'pointer', padding: 0,
        fontSize: 12, color: hov ? T.t1 : T.t3, fontFamily: 'inherit',
        display: 'flex', alignItems: 'center', gap: 4, transition: 'color 0.15s',
        marginBottom: 16,
      }}
    >
      {children}
    </button>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────────
export function LGEmpty({ icon, title, desc, action }) {
  const { T } = useTheme()
  return (
    <div style={{ textAlign: 'center', padding: '52px 24px', color: T.t3 }}>
      <div style={{ fontSize: 40, marginBottom: 14 }}>{icon}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: T.t2, marginBottom: 6 }}>{title}</div>
      {desc && <div style={{ fontSize: 13, marginBottom: 20, color: T.t3 }}>{desc}</div>}
      {action}
    </div>
  )
}

// ─── CSS global ───────────────────────────────────────────────────────────────
export const LG_CSS = `
  @keyframes lgspin { to { transform: rotate(360deg) } }
  * { box-sizing: border-box; }
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(128,128,128,0.25); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(128,128,128,0.40); }
`
