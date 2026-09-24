import { useState } from 'react'
import { useSize } from '../lib/hooks'
import { Marker } from '../lib/marks'
import Tip from '../components/Tip'

const OFFSETS = [
  [13, -11, 'start'],
  [13, 17, 'start'],
  [-13, -11, 'end'],
  [-13, 17, 'end'],
  [0, -17, 'middle'],
  [0, 27, 'middle'],
]

// Scatter with a mean point per generator and +/- one sd whiskers on both axes. Color = generator family,
// shape = the individual generator, and crowded points may go unlabeled and are named by the legend and tooltip.
// points: [{ key, label, short, shape, color, x, y, xsd, ysd, tip }]
export default function ScatterPlot({ points, xAxis, yAxis, label }) {
  const [box, { width }] = useSize()
  const [hover, setHover] = useState(null)
  const compact = width < 520
  const H = Math.round(Math.min(500, Math.max(350, width * 0.62)))
  const m = { l: compact ? 54 : 68, r: 24, t: 22, b: 58 }
  const iw = Math.max(50, width - m.l - m.r)
  const ih = H - m.t - m.b
  const [xa, xb] = xAxis.domain
  const [ya, yb] = yAxis.domain
  const sx = (v) => m.l + ((Math.min(Math.max(v, xa), xb) - xa) / (xb - xa)) * iw
  const sy = (v) => m.t + ih - ((Math.min(Math.max(v, ya), yb) - ya) / (yb - ya)) * ih

  const pts = points.map((p) => ({ ...p, cx: sx(p.x), cy: sy(p.y) }))

  // Greedy direct-label placement that avoids other markers and labels.
  const boxes = []
  const labels = pts.map((p) => {
    if (width < 480) return null // phone: the legend and tooltip name the points
    const text = compact ? p.short : p.label
    const w = text.length * 6.6
    let chosen = null
    for (const [dx, dy, anchor] of OFFSETS) {
      const x1 = anchor === 'start' ? p.cx + dx : anchor === 'end' ? p.cx + dx - w : p.cx - w / 2
      const b = { x1, x2: x1 + w, y1: p.cy + dy - 11, y2: p.cy + dy + 3 }
      const inside = b.x1 >= m.l - 4 && b.x2 <= width - 4 && b.y1 >= m.t - 8 && b.y2 <= m.t + ih + 4
      const clash =
        boxes.some((o) => b.x1 < o.x2 && b.x2 > o.x1 && b.y1 < o.y2 && b.y2 > o.y1) ||
        pts.some((q) => q !== p && q.cx > b.x1 - 9 && q.cx < b.x2 + 9 && q.cy > b.y1 - 9 && q.cy < b.y2 + 9)
      if (inside && !clash) {
        chosen = { b, dx, dy, anchor }
        break
      }
    }
    // A crowded point goes unlabeled rather than colliding; the legend and tooltip still name it.
    if (!chosen) return null
    boxes.push(chosen.b)
    return { key: p.key, text, x: p.cx + chosen.dx, y: p.cy + chosen.dy, anchor: chosen.anchor }
  })

  // Which corner is best, from each axis' direction.
  const bestLeft = xAxis.better === 'lower'
  const bestTop = yAxis.better === 'higher'
  const hint = { x: bestLeft ? m.l + 10 : m.l + iw - 10, y: bestTop ? m.t + 18 : m.t + ih - 10, anchor: bestLeft ? 'start' : 'end' }
  const arrow = `${bestTop ? (bestLeft ? '↖' : '↗') : bestLeft ? '↙' : '↘'}`

  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect()
    const px = e.clientX - r.left
    const py = e.clientY - r.top
    let best = null
    let bd = 46 * 46
    pts.forEach((p) => {
      const d = (p.cx - px) ** 2 + (p.cy - py) ** 2
      if (d < bd) {
        bd = d
        best = p.key
      }
    })
    setHover(best)
  }
  const active = pts.find((p) => p.key === hover)

  return (
    <div ref={box} style={{ position: 'relative' }}>
      {width > 0 && (
        <svg className="svgchart" width={width} height={H} role="group" aria-label={label} onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
          {xAxis.ticks.map((t) => (
            <g key={`x${t}`}>
              <line x1={sx(t)} x2={sx(t)} y1={m.t} y2={m.t + ih} stroke="var(--grid)" strokeWidth="1" />
              <text x={sx(t)} y={m.t + ih + 18} textAnchor="middle" fontSize="11" fill="var(--muted)" className="num">
                {xAxis.format(t)}
              </text>
            </g>
          ))}
          {yAxis.ticks.map((t) => (
            <g key={`y${t}`}>
              <line x1={m.l} x2={m.l + iw} y1={sy(t)} y2={sy(t)} stroke="var(--grid)" strokeWidth="1" />
              <text x={m.l - 10} y={sy(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)" className="num">
                {yAxis.format(t)}
              </text>
            </g>
          ))}
          <line x1={m.l} x2={m.l + iw} y1={m.t + ih} y2={m.t + ih} stroke="var(--base)" />
          <line x1={m.l} x2={m.l} y1={m.t} y2={m.t + ih} stroke="var(--base)" />
          <text x={m.l + iw / 2} y={H - 10} textAnchor="middle" fontSize="12.5" fontWeight="600" fill="var(--ink-2)">
            {xAxis.label}
          </text>
          <text transform={`translate(15 ${m.t + ih / 2}) rotate(-90)`} textAnchor="middle" fontSize="12.5" fontWeight="600" fill="var(--ink-2)">
            {yAxis.label}
          </text>
          <text x={hint.x} y={hint.y} textAnchor={hint.anchor} fontSize="12" fill="var(--muted)" fontWeight="600">
            {bestLeft ? `${arrow} best corner` : `best corner ${arrow}`}
          </text>

          {pts.map((p) => (
            <g key={`w${p.key}`} stroke={p.color} strokeWidth="2" strokeLinecap="round" opacity={hover && hover !== p.key ? 0.25 : 0.55}>
              {p.xsd > 0 && (
                <>
                  <line x1={sx(p.x - p.xsd)} x2={sx(p.x + p.xsd)} y1={p.cy} y2={p.cy} />
                  <line x1={sx(p.x - p.xsd)} x2={sx(p.x - p.xsd)} y1={p.cy - 4} y2={p.cy + 4} />
                  <line x1={sx(p.x + p.xsd)} x2={sx(p.x + p.xsd)} y1={p.cy - 4} y2={p.cy + 4} />
                </>
              )}
              {p.ysd > 0 && (
                <>
                  <line x1={p.cx} x2={p.cx} y1={sy(p.y - p.ysd)} y2={sy(p.y + p.ysd)} />
                  <line x1={p.cx - 4} x2={p.cx + 4} y1={sy(p.y - p.ysd)} y2={sy(p.y - p.ysd)} />
                  <line x1={p.cx - 4} x2={p.cx + 4} y1={sy(p.y + p.ysd)} y2={sy(p.y + p.ysd)} />
                </>
              )}
            </g>
          ))}
          {pts.map((p) => (
            <g key={p.key} opacity={hover && hover !== p.key ? 0.55 : 1}>
              <Marker shape={p.shape} x={p.cx} y={p.cy} r={hover === p.key ? 8 : 7} color={p.color} />
            </g>
          ))}
          {labels.filter(Boolean).map((l) => (
            <text key={l.key} x={l.x} y={l.y} textAnchor={l.anchor} fontSize="12.5" fontWeight="600" fill="var(--ink)">
              {l.text}
            </text>
          ))}
          {pts.map((p) => (
            <circle
              key={`h${p.key}`}
              cx={p.cx}
              cy={p.cy}
              r="17"
              fill="transparent"
              tabIndex={0}
              role="img"
              aria-label={`${p.label}: ${xAxis.short} ${xAxis.format(p.x)}, ${yAxis.short} ${yAxis.format(p.y)}`}
              onFocus={() => setHover(p.key)}
              onBlur={() => setHover(null)}
              style={{ outline: 'none' }}
            />
          ))}
        </svg>
      )}
      {active && <Tip x={active.cx} y={active.cy} boxWidth={width} title={active.label} shape={active.shape} color={active.color} rows={active.tip} />}
    </div>
  )
}
