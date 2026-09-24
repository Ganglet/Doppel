import { Swatch } from '../lib/marks'

// Tooltip anchored to a point inside a relatively positioned chart box. Values lead, names follow.
export default function Tip({ x, y, boxWidth, title, shape, color, rows }) {
  const flip = x > boxWidth * 0.55
  const style = flip ? { left: x - 16, top: y, transform: 'translate(-100%, -50%)' } : { left: x + 16, top: y, transform: 'translate(0, -50%)' }
  return (
    <div className="tip" style={style} role="status">
      <div className="t">
        {shape && <Swatch shape={shape} color={color} />}
        <span>{title}</span>
      </div>
      {rows.map((r) => (
        <div className="row" key={r[0]}>
          <span>{r[0]}</span>
          <b className="num">{r[1]}</b>
        </div>
      ))}
    </div>
  )
}
