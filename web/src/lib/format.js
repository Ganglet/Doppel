export const f2 = (x) => x.toFixed(2)
export const f3 = (x) => x.toFixed(3)
export const f4 = (x) => x.toFixed(4)
export const pm = (m, d = 3) => `${m.mean.toFixed(d)} ± ${m.sd.toFixed(d)}`
export const pval = (p) => (p < 0.0001 ? 'p < 0.0001' : `p = ${p < 0.01 ? p.toFixed(4) : p.toFixed(3)}`)
export const times = (a, b) => (a / b).toFixed(1)

// Nice tick values for a domain, at most `count` of them.
export function niceTicks(min, max, count = 5) {
  const span = max - min
  const raw = span / Math.max(1, count - 1)
  const mag = Math.pow(10, Math.floor(Math.log10(raw)))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || mag * 10
  const start = Math.ceil(min / step - 1e-9) * step
  const out = []
  for (let v = start; v <= max + 1e-9; v += step) out.push(Math.round(v / step) * step)
  return out
}
