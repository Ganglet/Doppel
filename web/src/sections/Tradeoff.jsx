import { useState } from 'react'
import ChartCard from '../components/ChartCard'
import SegmentedControl from '../components/SegmentedControl'
import Legend from '../components/Legend'
import ScatterPlot from '../charts/ScatterPlot'
import Heatmap from '../charts/Heatmap'
import { FAMILY_COLOR, Swatch } from '../lib/marks'
import { f2, f3 } from '../lib/format'

const METRICS = {
  privacy: { label: 'Privacy leakage: attack score', short: 'leakage', better: 'lower', get: (r) => r.privacy.worst, domain: [0.6, 0.72], ticks: [0.6, 0.64, 0.68, 0.72] },
  utility: { label: 'Utility: prediction score', short: 'utility', better: 'higher', get: (r) => r.utility.tstr_mean, domain: [0.3, 0.9], ticks: [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9] },
  fidelity: { label: 'Fidelity: distance from real data', short: 'distance', better: 'lower', get: (r) => r.fidelity.jsd, domain: [0, 0.13], ticks: [0, 0.03, 0.06, 0.09, 0.12] },
}
const OPTIONS = [
  { value: 'privacy', label: 'Privacy' },
  { value: 'utility', label: 'Utility' },
  { value: 'fidelity', label: 'Fidelity' },
]
const COLS = [
  ['main', 'Main axes'],
  ['+ correlation axis', '+ Correlation'],
  ['utility = LR only', 'Utility: logistic'],
  ['utility = RF only', 'Utility: forest'],
  ['privacy = 4 numeric', 'Privacy: 4 columns'],
  ['privacy = Gower', 'Privacy: all columns'],
  ['privacy = ICD-9 codes', 'Privacy: ICD-9'],
  ['no utility axis', 'No utility axis'],
]

export default function Tradeoff({ data }) {
  const [xKey, setX] = useState('privacy')
  const [yKey, setY] = useState('utility')
  const [hidden, setHidden] = useState(new Set())
  const { arms, results: r, pareto } = data

  const pick = (setter, other, otherSetter) => (v) => {
    setter(v)
    if (v === other) otherSetter(OPTIONS.find((o) => o.value !== v && o.value !== other)?.value ?? OPTIONS.find((o) => o.value !== v).value)
  }
  const toggle = (id) =>
    setHidden((h) => {
      const n = new Set(h)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })

  const X = METRICS[xKey]
  const Y = METRICS[yKey]
  const third = OPTIONS.find((o) => o.value !== xKey && o.value !== yKey).value
  const T = METRICS[third]
  const points = arms
    .filter((a) => !hidden.has(a.id))
    .map((a) => {
      const x = X.get(r[a.id])
      const y = Y.get(r[a.id])
      const t = T.get(r[a.id])
      return {
        key: a.id, label: a.label, short: a.short, shape: a.marker, color: FAMILY_COLOR[a.family],
        x: x.mean, y: y.mean, xsd: x.sd, ysd: y.sd,
        tip: [[`${X.short} (mean ± sd)`, `${f3(x.mean)} ± ${f3(x.sd)}`], [`${Y.short} (mean ± sd)`, `${f3(y.mean)} ± ${f3(y.sd)}`], [`${T.short}`, f3(t.mean)]],
      }
    })

  const freq = pareto.frontier_freq
  const allOn = Object.values(pareto.frontier).every(Boolean)
  const sens = pareto.sensitivity
  const tvNoUtil = sens['no utility axis'].tvae
  const tvWeak = sens['privacy = 4 numeric'].tvae

  const table = {
    caption: 'Position of each generator on the chosen measures, mean ± one standard deviation over 20 seeds',
    columns: [
      { key: 'g', label: 'Generator' },
      { key: 'x', label: X.label, numeric: true },
      { key: 'y', label: Y.label, numeric: true },
    ],
    rows: arms.map((a) => ({
      g: (
        <span className="namecell">
          <Swatch shape={a.marker} color={FAMILY_COLOR[a.family]} />
          {a.label}
        </span>
      ),
      x: `${f3(X.get(r[a.id]).mean)} ± ${f3(X.get(r[a.id]).sd)}`,
      y: `${f3(Y.get(r[a.id]).mean)} ± ${f3(Y.get(r[a.id]).sd)}`,
    })),
  }

  return (
    <section id="tradeoffs" aria-labelledby="h-trade">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow">Trade-offs</span>
          <h2 id="h-trade">Is any generator simply the best?</h2>
          <p>
            No generator wins on realism, usefulness and privacy at once. Pick two measures to see the trade-off, and use the legend to hide a
            generator without changing anyone else's color.
          </p>
        </div>

        <div className="filters">
          <SegmentedControl label="Horizontal" value={xKey} onChange={pick(setX, yKey, setY)} options={OPTIONS} />
          <SegmentedControl label="Vertical" value={yKey} onChange={pick(setY, xKey, setX)} options={OPTIONS} />
        </div>

        <div className="stack">
          <ChartCard
            title={`${Y.label.split(':')[0]} against ${X.label.split(':')[0].toLowerCase()}`}
            subtitle="Each point is a generator, with whiskers for one standard deviation across 20 seeds. Color is the generator family and shape is the individual generator."
            table={table}
            legend={<Legend arms={arms} hidden={hidden} onToggle={toggle} />}
            takeaway={
              <>
                <b>Nothing sits in the best corner.</b> TVAE buys utility with leakage and distance from the real data; CTGAN and the floor leak least but predict least; the copulas sit in between.
              </>
            }
          >
            <ScatterPlot
              points={points}
              label={`${Y.label} against ${X.label}`}
              xAxis={{ domain: X.domain, ticks: X.ticks, format: f2, label: `${X.label} (${X.better} is better)`, better: X.better, short: X.short }}
              yAxis={{ domain: Y.domain, ticks: Y.ticks, format: f2, label: `${Y.label} (${Y.better} is better)`, better: Y.better, short: Y.short }}
            />
          </ChartCard>

          <div className="grid two">
            <div className="card">
              <h3>What the frontier says</h3>
              <p className="muted small" style={{ marginTop: 6 }}>
                A generator is on the frontier if no other one is at least as good on all three measures and better on one.{' '}
                {allOn ? 'All five are on it.' : 'Not every generator is on it.'} The share below is how often each stays on the frontier when the 20 seeds are resampled.
              </p>
              <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Generator</th>
                      <th className="n">On the frontier</th>
                      <th className="n">Share of resamples</th>
                    </tr>
                  </thead>
                  <tbody>
                    {arms.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <span className="namecell">
                            <Swatch shape={a.marker} color={FAMILY_COLOR[a.family]} />
                            {a.label}
                          </span>
                        </td>
                        <td className="n">{pareto.frontier[a.id] ? 'Yes' : 'No'}</td>
                        <td className="n">{Math.round(freq[a.id] * 100)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="takeaway">
                <b>When every generator is on the frontier, it does not rank them.</b> It only shows which way each one trades.
              </p>
            </div>

            <div className="card">
              <h3>How robust is that?</h3>
              <p className="muted small" style={{ marginTop: 6 }}>
                The frontier depends on which measures count. Each row below recomputes it with one change; darker means the generator stays on it more often.
              </p>
              <div style={{ marginTop: 12 }}>
                <Heatmap
                  caption="Share of resamples in which each generator is on the frontier, under eight choices of measures"
                  rows={COLS.map(([k, l]) => ({ key: k, label: l }))}
                  cols={arms.map((a) => ({ key: a.id, label: a.short, shape: a.marker, color: FAMILY_COLOR[a.family] }))}
                  value={(row, col) => sens[row][col]}
                  format={(v) => v.toFixed(2)}
                />
              </div>
              <p className="takeaway">
                <b>TVAE's place rests on utility alone:</b> without that measure it is on the frontier {Math.round(tvNoUtil * 100)}% of the time. With the weak 4-column attack as
                the privacy measure it looks safest, at {Math.round(tvWeak * 100)}%.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
