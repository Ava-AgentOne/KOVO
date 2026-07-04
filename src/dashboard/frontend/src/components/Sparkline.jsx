// Tiny inline SVG sparkline — no chart library (v2.1 Mission Control).
export default function Sparkline({ data, height = 28, className = 'text-brand-500' }) {
  if (!data || data.length < 2) return null
  const w = 100
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - 2 - ((v - min) / range) * (height - 4)
    return [x, y]
  })
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const area = `0,${height} ${line} ${w},${height}`
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className={`w-full ${className}`} style={{ height }} preserveAspectRatio="none" aria-hidden="true">
      <polygon points={area} fill="currentColor" opacity="0.12" />
      <polyline points={line} fill="none" stroke="currentColor" strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  )
}
