import { FAMILY_COLOR, Swatch } from '../lib/marks'

// Toggle-to-isolate legend. Colors follow the generator, so hiding one never repaints the others.
export default function Legend({ arms, hidden, onToggle }) {
  return (
    <div className="legend" role="group" aria-label="Generators shown">
      {arms.map((a) => (
        <button key={a.id} aria-pressed={!hidden.has(a.id)} onClick={() => onToggle(a.id)} title="Click to show or hide">
          <Swatch shape={a.marker} color={FAMILY_COLOR[a.family]} />
          {a.label}
        </button>
      ))}
    </div>
  )
}
