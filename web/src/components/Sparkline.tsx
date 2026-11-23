import { DOWN, UP } from './chartTheme'

/** Small trend line (pure SVG, no chart library). Green when the last value is at or above the first, red otherwise. */
export function Sparkline({ data, width = 120, height = 36, positive, label }: { data: number[]; width?: number; height?: number; positive?: boolean; label?: string }) {
  if (!data || data.length < 2) return <svg width={width} height={height} aria-hidden />
  const min = Math.min(...data), max = Math.max(...data), span = max - min || 1
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - 3 - ((v - min) / span) * (height - 6)}`).join(' ')
  const up = positive ?? data[data.length - 1] >= data[0]
  const color = up ? UP : DOWN
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible"
      {...(label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true })}>
      <defs>
        <linearGradient id={`sg-${up}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" /><stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${height} ${pts} ${width},${height}`} fill={`url(#sg-${up})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
