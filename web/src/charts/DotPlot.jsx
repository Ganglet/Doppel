import { useState } from 'react'
import { useSize } from '../lib/hooks'
import { Marker } from '../lib/marks'
import { f3 } from '../lib/format'
import Tip from '../components/Tip'

// Horizontal dot plot: one row per generator, a dot at the mean and a whisker for one standard deviation
// across seeds. Comparing positions on a shared scale needs no zero baseline, so the axis can zoom in.
// rows: [{ key, label, short, shape, color, hollow, mean, sd, tip: [[name, value], ...] }]
export default function DotPlot({ rows, domain, ticks, refs = [], format = f3, label }) {
  const [box, { width }] = useSize()
  const [hover, setHover] = useState(null)
  const compact = width < 540
  const narrow = width < 400
  const rowH = narrow ? 62 : 46
  const top = 34
  const bottom = 30
  // On a phone the label sits on its own line above the dot so the plot keeps the full width.
  const labelW = narrow ? 0 : compact ? 96 : 206
  const valueW = narrow ? 0 : 58
  const x0 = narrow ? 14 : labelW + 12
  const x1 = narrow ? width - 14 : Math.max(x0 + 80, width - valueW - 12)
  const H = top + rows.length * rowH + bottom
  const [a, b] = domain
  const sx = (v) => x0 + ((Math.min(Math.max(v, a), b) - a) / (b - a)) * (x1 - x0)
  const plotBottom = top + rows.length * rowH

  // Stagger reference labels that would collide.
  const sortedRefs = [...refs].sort((p, q) => p.value - q.value)
  let lastX = -1e9
  let lift = 0
  const refLabels = sortedRefs.map((r) => {
    const x = sx(r.value)
    lift = x - lastX < 92 ? (lift + 1) % 2 : 0
    lastX = x
    return { ...r, x, y: top - 10 - lift * 13 }
  })

  // Thin tick labels when the plot is narrow so they never run together.
  const shown = new Set()
  let prevX = -1e9
  ticks.forEach((t) => {
    if (sx(t) - prevX >= 46) {
      shown.add(t)
      prevX = sx(t)
    }
  })

  const active = hover != null ? rows[hover] : null
  return (
    <div ref={box} style={{ position: 'relative' }}>
      {width > 0 && (
        <svg className="svgchart" width={width} height={H} role="group" aria-label={label}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={sx(t)} x2={sx(t)} y1={top - 4} y2={plotBottom} stroke="var(--grid)" strokeWidth="1" />
              {shown.has(t) && (
                <text x={sx(t)} y={H - 8} textAnchor="middle" fontSize="11" fill="var(--muted)" className="num">
                  {format(t)}
                </text>
              )}
            </g>
          ))}
          <line x1={x0} x2={x1} y1={plotBottom} y2={plotBottom} stroke="var(--base)" strokeWidth="1" />
          {refLabels.map((r) => (
            <g key={r.label}>
              <line x1={r.x} x2={r.x} y1={r.y + 4} y2={plotBottom} stroke="var(--ink-2)" strokeWidth="1" opacity="0.55" />
              <text x={r.x} y={r.y} textAnchor="middle" fontSize="11" fill="var(--ink-2)">
                {r.label}
              </text>
            </g>
          ))}
          {rows.map((r, i) => {
            const y = narrow ? top + i * rowH + 42 : top + i * rowH + rowH / 2
            const ly = narrow ? top + i * rowH + 18 : y
            const lo = sx(r.mean - r.sd)
            const hi = sx(r.mean + r.sd)
            return (
              <g
                key={r.key}
                tabIndex={0}
                role="img"
                aria-label={`${r.label}: ${format(r.mean)}, plus or minus ${format(r.sd)}`}
                onPointerEnter={() => setHover(i)}
                onPointerLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                style={{ outline: 'none' }}
              >
                <rect x="0" y={top + i * rowH} width={width} height={rowH} fill={hover === i ? 'var(--surface-2)' : 'transparent'} rx="8" opacity="0.7" />
                <Marker shape={r.shape} x={8} y={ly} r={5} color={r.color} ring={false} hollow={r.hollow} />
                <text x={24} y={ly + 4.5} fontSize="13" fill="var(--ink-2)">
                  {compact && !narrow ? r.short : r.label}
                </text>
                {r.sd > 0 && (
                  <g stroke={r.color} strokeWidth="2" strokeLinecap="round" opacity="0.6">
                    <line x1={lo} x2={hi} y1={y} y2={y} />
                    <line x1={lo} x2={lo} y1={y - 5} y2={y + 5} />
                    <line x1={hi} x2={hi} y1={y - 5} y2={y + 5} />
                  </g>
                )}
                <Marker shape={r.shape} x={sx(r.mean)} y={y} r={6} color={r.color} hollow={r.hollow} />
                <text x={width} y={ly + 4.5} textAnchor="end" fontSize="13" fontWeight="650" fill="var(--ink)" className="num">
                  {format(r.mean)}
                </text>
              </g>
            )
          })}
        </svg>
      )}
      {active && (
        <Tip x={sx(active.mean)} y={top + hover * rowH + (narrow ? 42 : rowH / 2)} boxWidth={width} title={active.label} shape={active.shape} color={active.color} rows={active.tip} />
      )}
    </div>
  )
}
