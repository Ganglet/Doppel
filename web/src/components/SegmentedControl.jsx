import { useRef } from 'react'

export default function SegmentedControl({ label, value, onChange, options }) {
  const refs = useRef([])
  const onKey = (e, i) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    e.preventDefault()
    const next = (i + (e.key === 'ArrowRight' ? 1 : options.length - 1)) % options.length
    onChange(options[next].value)
    refs.current[next]?.focus()
  }
  return (
    <div className="field">
      <span id={`seg-${label}`}>{label}</span>
      <div className="seg" role="radiogroup" aria-labelledby={`seg-${label}`}>
        {options.map((o, i) => (
          <button
            key={o.value}
            ref={(el) => (refs.current[i] = el)}
            role="radio"
            aria-checked={o.value === value}
            tabIndex={o.value === value ? 0 : -1}
            onClick={() => onChange(o.value)}
            onKeyDown={(e) => onKey(e, i)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}
