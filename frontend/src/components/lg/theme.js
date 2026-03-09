// ─── Liquid Glass — Design Tokens (macOS Tahoe / iOS 26 style) ──────────────

export const DARK = {
  mode: 'dark',
  appBg:       'linear-gradient(145deg, #0A1628 0%, #160D30 35%, #0C1F12 65%, #1A1206 100%)',
  sidebarBg:   'rgba(10,12,20,0.62)',
  toolbarBg:   'rgba(8,10,18,0.52)',
  glass:       'rgba(255,255,255,0.07)',
  glassHover:  'rgba(255,255,255,0.13)',
  glassActive: 'rgba(255,255,255,0.18)',
  glassBorder: 'rgba(255,255,255,0.13)',
  glassInset:  'inset 0 1px 0 rgba(255,255,255,0.12)',
  t1: 'rgba(255,255,255,0.92)',
  t2: 'rgba(255,255,255,0.55)',
  t3: 'rgba(255,255,255,0.28)',
  t4: 'rgba(255,255,255,0.09)',
  divider: 'rgba(255,255,255,0.07)',
  shadow:   '0 10px 40px rgba(0,0,0,0.50), 0 2px 8px rgba(0,0,0,0.30)',
  shadowSm: '0 4px 16px rgba(0,0,0,0.35)',
  inputBg:     'rgba(255,255,255,0.06)',
  inputBorder: 'rgba(255,255,255,0.13)',
  scrollbar:   'rgba(255,255,255,0.18)',
  orbs: [
    { w:700, h:700, color:'rgba(10,132,255,0.14)',  top:-180, left:-150 },
    { w:500, h:500, color:'rgba(191,90,242,0.11)',  top:80,   right:-100 },
    { w:800, h:800, color:'rgba(48,209,88,0.07)',   bottom:-300, left:'35%' },
  ],
}

export const LIGHT = {
  mode: 'light',
  appBg:       'linear-gradient(145deg, #E6EEF8 0%, #EEE8F6 35%, #E4F2EC 65%, #F8F2E4 100%)',
  sidebarBg:   'rgba(255,255,255,0.58)',
  toolbarBg:   'rgba(248,249,252,0.70)',
  glass:       'rgba(255,255,255,0.62)',
  glassHover:  'rgba(255,255,255,0.80)',
  glassActive: 'rgba(255,255,255,0.92)',
  glassBorder: 'rgba(0,0,0,0.08)',
  glassInset:  'inset 0 1px 0 rgba(255,255,255,0.95)',
  t1: 'rgba(10,10,20,0.90)',
  t2: 'rgba(10,10,20,0.55)',
  t3: 'rgba(10,10,20,0.35)',
  t4: 'rgba(10,10,20,0.07)',
  divider: 'rgba(0,0,0,0.06)',
  shadow:   '0 10px 40px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06)',
  shadowSm: '0 4px 16px rgba(0,0,0,0.08)',
  inputBg:     'rgba(255,255,255,0.80)',
  inputBorder: 'rgba(0,0,0,0.10)',
  scrollbar:   'rgba(0,0,0,0.20)',
  orbs: [
    { w:700, h:700, color:'rgba(10,132,255,0.07)',  top:-180, left:-150 },
    { w:500, h:500, color:'rgba(191,90,242,0.06)',  top:80,   right:-100 },
    { w:800, h:800, color:'rgba(48,209,88,0.04)',   bottom:-300, left:'35%' },
  ],
}

export const AC = {
  blue:   '#0A84FF',
  green:  '#30D158',
  orange: '#FF9F0A',
  red:    '#FF453A',
  purple: '#BF5AF2',
  teal:   '#40CBE0',
  yellow: '#FFD60A',
}

export const blur = (px = 28) => ({
  backdropFilter: `blur(${px}px) saturate(180%)`,
  WebkitBackdropFilter: `blur(${px}px) saturate(180%)`,
})

export const scoreColor = (s) =>
  s >= 80 ? AC.green : s >= 60 ? AC.orange : AC.red
