/**
 * Small hand-rolled SVG charts. No charting dependency — these are simple
 * enough that owning them gives better control over the console's look and
 * keeps the bundle light.
 */

export function Donut({
  segments,
  centerValue,
  centerLabel,
  size = 132,
  thickness = 16,
}: {
  segments: Array<{ label: string; value: number; color: string }>
  centerValue: string
  centerLabel?: string
  size?: number
  thickness?: number
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0) || 1
  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius

  // Each arc's start offset is the sum of the arcs before it — computed without
  // mutation so the render pass stays side-effect free.
  const dashOf = (value: number) => (value / total) * circumference
  const arcs = segments.map((seg, i) => ({
    ...seg,
    dash: dashOf(seg.value),
    offset: segments.slice(0, i).reduce((sum, s) => sum + dashOf(s.value), 0),
  }))

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
      <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-canvas)"
          strokeWidth={thickness}
        />
        {arcs.map((arc) => (
          <circle
            key={arc.label}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={arc.color}
            strokeWidth={thickness}
            strokeDasharray={`${arc.dash} ${circumference - arc.dash}`}
            strokeDashoffset={-arc.offset}
            strokeLinecap="butt"
          />
        ))}
      </g>
      <text
        x="50%"
        y={centerLabel ? '46%' : '52%'}
        textAnchor="middle"
        className="fill-ink-900 font-bold tnum"
        style={{ fontSize: 22 }}
      >
        {centerValue}
      </text>
      {centerLabel && (
        <text
          x="50%"
          y="62%"
          textAnchor="middle"
          className="fill-ink-400"
          style={{ fontSize: 10.5 }}
        >
          {centerLabel}
        </text>
      )}
    </svg>
  )
}

export function Sparkline({
  values,
  width = 96,
  height = 30,
  color = 'var(--color-brand-600)',
}: {
  values: number[]
  width?: number
  height?: number
  color?: string
}) {
  if (values.length < 2) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const step = width / (values.length - 1)
  const points = values
    .map((v, i) => `${i * step},${height - ((v - min) / span) * (height - 4) - 2}`)
    .join(' ')

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-hidden>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.75}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function StackedBars({
  data,
  height = 190,
}: {
  data: Array<{ day: number; auto: number; human: number }>
  height?: number
}) {
  const max = Math.max(...data.map((d) => d.auto + d.human)) || 1
  const barW = 100 / data.length

  return (
    <div className="w-full" style={{ height }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label="Autonomous resolutions versus human interventions over 30 days"
      >
        {[0.25, 0.5, 0.75, 1].map((t) => (
          <line
            key={t}
            x1="0"
            x2="100"
            y1={height - t * (height - 12)}
            y2={height - t * (height - 12)}
            stroke="var(--color-line)"
            strokeWidth={0.5}
            strokeDasharray="1.5 2"
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {data.map((d, i) => {
          const totalH = ((d.auto + d.human) / max) * (height - 12)
          const autoH = (d.auto / max) * (height - 12)
          const x = i * barW + barW * 0.18
          const w = barW * 0.64
          return (
            <g key={d.day}>
              <rect
                x={x}
                y={height - totalH}
                width={w}
                height={Math.max(totalH - autoH - 0.8, 0)}
                fill="var(--color-brand-200)"
                rx={0.6}
              />
              <rect
                x={x}
                y={height - autoH}
                width={w}
                height={autoH}
                fill="var(--color-brand-600)"
                rx={0.6}
              />
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export function MiniRing({
  value,
  label,
  size = 54,
}: {
  value: number
  label: string
  size?: number
}) {
  const r = (size - 7) / 2
  const c = 2 * Math.PI * r
  const dash = value * c
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-canvas)" strokeWidth={5} />
      <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--color-ok-500)"
          strokeWidth={5}
          strokeDasharray={`${dash} ${c - dash}`}
          strokeLinecap="round"
        />
      </g>
      <text
        x="50%"
        y="56%"
        textAnchor="middle"
        className="fill-ink-700 font-bold"
        style={{ fontSize: 12 }}
      >
        {label}
      </text>
    </svg>
  )
}
