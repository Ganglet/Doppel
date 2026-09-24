import { useState } from 'react'
import { Swatch } from '../lib/marks'

// Heatmap on one sequential hue: the cell mixes the accent hue into the surface, darker means larger.
// rows: [{ key, label, shape, color }], cols: [{ key, label }], value(rowKey, colKey) in 0..1.
export default function Heatmap({ rows, cols, value, format, caption }) {
  const [focus, setFocus] = useState(null)
  return (
    <div>
      <div className="heatscroll">
        <div
          className="heat"
          role="table"
          aria-label={caption}
          style={{ gridTemplateColumns: `minmax(80px, 190px) repeat(${cols.length}, minmax(40px, 1fr))`, minWidth: 80 + cols.length * 42 }}
        >
          <div className="hh" role="columnheader" />
          {cols.map((c) => (
            <div key={c.key} className="hh" role="columnheader">
              {c.shape && <Swatch shape={c.shape} color={c.color} />}
              {c.label}
            </div>
          ))}
          {rows.map((r) => (
            <div key={r.key} style={{ display: 'contents' }} role="row">
              <div className="hr" role="rowheader">
                {r.shape && <Swatch shape={r.shape} color={r.color} />}
                {r.label}
              </div>
              {cols.map((c) => {
                const v = value(r.key, c.key)
                const id = `${r.key}|${c.key}`
                return (
                  <div
                    key={c.key}
                    className="hc"
                    role="cell"
                    tabIndex={0}
                    aria-label={`${r.label}, ${c.label}: ${format(v)}`}
                    title={`${r.label} - ${c.label}: ${format(v)}`}
                    onFocus={() => setFocus(id)}
                    onBlur={() => setFocus(null)}
                    style={{
                      background: `color-mix(in srgb, var(--c-blue) ${Math.round(v * 100)}%, var(--surface-2))`,
                      color: v >= 0.6 ? '#0b0b0b' : 'var(--ink)',
                      outline: focus === id ? '2px solid var(--ink)' : undefined,
                      outlineOffset: -2,
                    }}
                  >
                    {format(v)}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="scale" aria-hidden="true">
        <span>0</span>
        <i />
        <span>1 = on the frontier in every resample</span>
      </div>
    </div>
  )
}
