import ChartCard from '../components/ChartCard'
import DotPlot from '../charts/DotPlot'
import { FAMILY_COLOR, Swatch } from '../lib/marks'
import { f3, pval } from '../lib/format'

const ATTACK_CARDS = [
  { key: 'numeric4', title: '4 columns', sub: 'Age, stay lengths and diagnosis count only.' },
  { key: 'gower', title: 'All columns', sub: 'Distance over every column, including labs and codes.' },
  { key: 'icd9_codes', title: 'ICD-9 codes', sub: 'Overlap between diagnosis-code sets.' },
]
const TARGETS = [
  ['gender', 'Gender'],
  ['first_careunit', 'First care unit'],
  ['age_bucket', 'Age group'],
]

export default function Privacy({ data }) {
  const { arms, results: r, calibration: c, coverage, tests } = data
  const REF = 'var(--c-floor)'

  const attackRows = (key) => [
    { key: 'ceil', label: 'Copy of training rows (ceiling)', short: 'Copy ceiling', shape: 'circle', color: REF, hollow: true, mean: c.auroc.exact_copy[key].mean, sd: c.auroc.exact_copy[key].sd, tip: [['Attack score', f3(c.auroc.exact_copy[key].mean)], ['Meaning', 'Best case for the attacker']] },
    ...arms.map((a) => ({ key: a.id, label: a.label, short: a.short, shape: a.marker, color: FAMILY_COLOR[a.family], mean: c.auroc[a.id][key].mean, sd: c.auroc[a.id][key].sd, tip: [['Attack score (mean)', f3(c.auroc[a.id][key].mean)], ['Spread (± 1 sd)', f3(c.auroc[a.id][key].sd)]] })),
    { key: 'floor', label: 'Unseen real rows (floor)', short: 'Unseen rows', shape: 'circle', color: REF, hollow: true, mean: c.auroc.disjoint_real[key].mean, sd: c.auroc.disjoint_real[key].sd, tip: [['Attack score', f3(c.auroc.disjoint_real[key].mean)], ['Meaning', 'Worst case for the attacker']] },
  ]
  const attackTable = (key, title) => ({
    caption: `Membership attack score, ${title}, mean and spread over 20 seeds`,
    columns: [{ key: 'g', label: 'Generator' }, { key: 'm', label: 'Score', numeric: true }, { key: 's', label: '± 1 sd', numeric: true }],
    rows: attackRows(key).map((row) => ({ g: row.label, m: f3(row.mean), s: f3(row.sd) })),
  })

  const tprRows = (key) => [
    ...arms.map((a) => ({ key: a.id, label: a.label, short: a.short, shape: a.marker, color: FAMILY_COLOR[a.family], mean: c.tpr1[a.id][key].mean, sd: c.tpr1[a.id][key].sd, tip: [['Records found (mean)', f3(c.tpr1[a.id][key].mean)], ['Spread (± 1 sd)', f3(c.tpr1[a.id][key].sd)], ['Times guessing', `${(c.tpr1[a.id][key].mean / 0.01).toFixed(1)}×`]] })),
    { key: 'floor', label: 'Unseen real rows (floor)', short: 'Unseen rows', shape: 'circle', color: REF, hollow: true, mean: c.tpr1.disjoint_real[key].mean, sd: c.tpr1.disjoint_real[key].sd, tip: [['Records found', f3(c.tpr1.disjoint_real[key].mean)]] },
  ]
  const tprTable = (key, title) => ({
    caption: `Share of training records found at 1% false alarms, ${title}`,
    columns: [{ key: 'g', label: 'Generator' }, { key: 'm', label: 'Found', numeric: true }, { key: 's', label: '± 1 sd', numeric: true }],
    rows: tprRows(key).map((row) => ({ g: row.label, m: f3(row.mean), s: f3(row.sd) })),
  })

  const covRows = arms.map((a) => ({ key: a.id, label: a.label, short: a.short, shape: a.marker, color: FAMILY_COLOR[a.family], mean: coverage[a.id].distinct.mean, sd: coverage[a.id].distinct.sd, tip: [['Training rows reached (mean)', coverage[a.id].distinct.mean.toFixed(1)], ['Spread (± 1 sd)', coverage[a.id].distinct.sd.toFixed(1)], ['Most synthetic rows on one', coverage[a.id].max_share.mean.toFixed(1)]] }))
  const covTable = {
    caption: 'Distinct training rows (of 94) that each generator’s synthetic rows are nearest to',
    columns: [{ key: 'g', label: 'Generator' }, { key: 'd', label: 'Rows reached', numeric: true }, { key: 'm', label: 'Most on one row', numeric: true }],
    rows: arms.map((a) => ({ g: a.label, d: coverage[a.id].distinct.mean.toFixed(1), m: coverage[a.id].max_share.mean.toFixed(1) })),
  }

  const tv = c.auroc.tvae
  const oth = ['independent_marginals', 'gaussian_copula', 'gaussian_copula_shrink025', 'ctgan']
  const once = oth.concat('tvae').map((a) => c.auroc[a].codes_once.mean)

  return (
    <section id="privacy" aria-labelledby="h-privacy">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow">Privacy</span>
          <h2 id="h-privacy">Do the privacy attacks actually work?</h2>
          <p>
            A privacy score means little unless the attack has been shown to succeed on a generator that leaks and fail on one that does not. Each
            chart below adds both reference points: a ceiling (a generator that copies its training rows) and a floor (real rows it never saw).
          </p>
        </div>

        <div className="stack">
          <div className="grid three">
            {ATTACK_CARDS.map((a) => (
              <ChartCard
                key={a.key}
                title={a.title}
                subtitle={a.sub}
                better="lower"
                table={attackTable(a.key, a.title)}
                takeaway={
                  a.key === 'numeric4' ? (
                    <><b>Blind to TVAE:</b> {f3(tv.numeric4.mean)}, the same as the floor.</>
                  ) : a.key === 'gower' ? (
                    <><b>Sees TVAE:</b> {f3(tv.gower.mean)} against {f3(c.auroc.ctgan.gower.mean)} to {f3(c.auroc.gaussian_copula_shrink025.gower.mean)}.</>
                  ) : (
                    <><b>Every generator leaks a little here</b>, TVAE most ({f3(tv.icd9_codes.mean)}).</>
                  )
                }
              >
                <DotPlot rows={attackRows(a.key)} domain={[0.4, 1.04]} ticks={[0.5, 0.6, 0.7, 0.8, 0.9, 1]} refs={[{ value: 0.5, label: 'Guessing' }]} label={`Attack score, ${a.title}`} />
              </ChartCard>
            ))}
          </div>

          <div className="grid two">
            <ChartCard
              title="Finding a few records with confidence"
              subtitle="Share of training records identified while wrongly accusing only 1% of unseen ones, using the all-columns attack."
              better="lower"
              table={tprTable('gower', 'all-columns attack')}
              takeaway={
                <>
                  <b>TVAE exposes {(c.tpr1.tvae.gower.mean / 0.01).toFixed(1)}× more records than guessing would</b> ({f3(c.tpr1.tvae.gower.mean)} against 0.010). An average score can hide this, so the
                  low false-alarm rate is reported as well.
                </>
              }
            >
              <DotPlot rows={tprRows('gower')} domain={[0, 0.09]} ticks={[0, 0.02, 0.04, 0.06, 0.08]} refs={[{ value: 0.01, label: 'Guessing 0.01' }]} label="Records found at 1% false alarms" />
            </ChartCard>

            <ChartCard
              title="Why TVAE leaks: it collapses onto a few rows"
              subtitle="How many of the 94 training rows the synthetic rows are nearest to."
              table={covTable}
              takeaway={
                <>
                  <b>TVAE's output sits nearest to only {coverage.tvae.distinct.mean.toFixed(0)} training rows</b> (others {Math.min(...oth.map((a) => coverage[a].distinct.mean)).toFixed(0)} to{' '}
                  {Math.max(...oth.map((a) => coverage[a].distinct.mean)).toFixed(0)}), and up to {coverage.tvae.max_share.mean.toFixed(0)} synthetic rows crowd around a single one.
                </>
              }
            >
              <DotPlot rows={covRows} domain={[20, 55]} ticks={[20, 30, 40, 50]} format={(v) => v.toFixed(0)} label="Training rows reached by each generator" />
            </ChartCard>
          </div>

          <div className="card">
            <h3>Rare diagnosis codes leak through every generator</h3>
            <p className="muted" style={{ marginTop: 6, maxWidth: 780 }}>
              A generator can only emit diagnosis codes it saw in training. A patient with a code that no one else has is therefore easy to spot: if
              the code shows up in the synthetic data, that patient was in the training set. Using only codes seen once, the attack scores{' '}
              <b>{f3(Math.min(...once))} to {f3(Math.max(...once))} for all five generators</b>, against a floor of {f3(c.auroc.disjoint_real.codes_once.mean)}. That includes CTGAN, which learned little else,
              so this is a property of the approach and not of one model.
            </p>
          </div>

          <div className="card">
            <h3>Can an attacker guess a hidden attribute?</h3>
            <p className="muted small" style={{ marginTop: 6, maxWidth: 780 }}>
              Given a patient's other columns, the attacker predicts one attribute. The number is how much better the attacker does on training patients than on unseen
              ones, read against the floor generator that has no relationships to exploit. A gap above the floor means the generator reveals something about its training patients.
            </p>
            <div className="tablewrap">
              <table>
                <caption className="sr-only">Attribute inference member gap by generator and attribute</caption>
                <thead>
                  <tr>
                    <th>Generator</th>
                    {TARGETS.map(([, l]) => (
                      <th key={l} className="n">{l}</th>
                    ))}
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
                      {TARGETS.map(([t]) => {
                        const g = r[a.id].attribute_gap[t]
                        const p = tests[`attr_${a.id}_${t}_p`]
                        const sig = p !== undefined && p < 0.05 && g.mean > 0
                        return (
                          <td key={t} className="n" style={sig ? { fontWeight: 650 } : undefined}>
                            {g.mean.toFixed(3)} ± {g.sd.toFixed(3)}
                            {sig && <span className="small muted" style={{ display: 'block', fontWeight: 400 }}>above the floor, {pval(p)}</span>}
                            {a.id === 'independent_marginals' && <span className="small muted" style={{ display: 'block', fontWeight: 400 }}>the floor</span>}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="takeaway">
              <b>TVAE's gender gap is {(r.tvae.attribute_gap.gender.mean / r.independent_marginals.attribute_gap.gender.mean).toFixed(1)}× the floor's</b>, so the positive control shows up here too. These are 12 uncorrected
              tests on a very small dataset, so treat single p-values with caution.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
