import { useState } from 'react'
import ChartCard from '../components/ChartCard'
import SegmentedControl from '../components/SegmentedControl'
import DotPlot from '../charts/DotPlot'
import { FAMILY_COLOR, Swatch } from '../lib/marks'
import { f3 } from '../lib/format'

const UTILITY = [
  { value: 'tstr_rf', label: 'Random forest' },
  { value: 'tstr_lr', label: 'Logistic regression' },
]
const ATTACKS = [
  { value: 'worst', label: 'Worst case' },
  { value: 'gower', label: 'All columns' },
  { value: 'codes', label: 'ICD-9 codes' },
  { value: 'numeric4', label: '4 columns' },
]
const ATTACK_NAME = { worst: 'worst case of three attacks', gower: 'the all-columns attack', codes: 'the ICD-9 code attack', numeric4: 'the 4-column attack' }

const tableFor = (arms, rows, caption, valueLabel) => ({
  caption,
  columns: [
    { key: 'g', label: 'Generator' },
    { key: 'm', label: valueLabel, numeric: true },
    { key: 's', label: 'Spread (± 1 sd)', numeric: true },
  ],
  rows: arms.map((a, i) => ({
    g: (
      <span className="namecell">
        <Swatch shape={a.marker} color={FAMILY_COLOR[a.family]} />
        {a.label}
      </span>
    ),
    m: f3(rows[i].mean),
    s: f3(rows[i].sd),
  })),
})

export default function Compare({ data }) {
  const [util, setUtil] = useState('tstr_rf')
  const [attack, setAttack] = useState('worst')
  const { arms, results: r, refs } = data

  const armRow = (a, m, tip) => ({ key: a.id, label: a.label, short: a.short, shape: a.marker, color: FAMILY_COLOR[a.family], mean: m.mean, sd: m.sd, tip })

  const fid = arms.map((a) => r[a.id].fidelity.jsd)
  const fidRows = arms.map((a, i) => armRow(a, fid[i], [['Distance (mean)', f3(fid[i].mean)], ['Spread (± 1 sd)', f3(fid[i].sd)], ['Correlation error', f3(r[a.id].fidelity.corr_diff.mean)]]))

  const ceiling = util === 'tstr_rf' ? refs.trtr_rf : refs.trtr_lr
  const ut = arms.map((a) => r[a.id].utility[util])
  const utRows = arms.map((a, i) => armRow(a, ut[i], [['Score (mean)', f3(ut[i].mean)], ['Spread (± 1 sd)', f3(ut[i].sd)], ['Gap to real-data ceiling', f3(ceiling - ut[i].mean)]]))

  const pr = arms.map((a) => r[a.id].privacy[attack])
  const prRows = arms.map((a, i) => armRow(a, pr[i], [['Attack score (mean)', f3(pr[i].mean)], ['Spread (± 1 sd)', f3(pr[i].sd)], ['Above guessing (0.5)', f3(pr[i].mean - 0.5)]]))

  const neuralJsd = (r.ctgan.fidelity.jsd.mean + r.tvae.fidelity.jsd.mean) / 2
  const copJsd = r.gaussian_copula.fidelity.jsd.mean
  const tv = r.tvae.privacy[attack].mean
  const rest = ['independent_marginals', 'gaussian_copula', 'gaussian_copula_shrink025', 'ctgan'].map((a) => r[a].privacy[attack].mean)
  const tvLowest = tv < Math.min(...rest)

  return (
    <section id="compare" aria-labelledby="h-compare">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow">Compare</span>
          <h2 id="h-compare">How do the generators compare?</h2>
          <p>
            Each dot is the average over {r.tvae.n_seeds} runs, and the whisker shows how much the runs varied. Where whiskers overlap, the
            difference could be chance.
          </p>
        </div>

        <div className="filters">
          <SegmentedControl label="Prediction model" value={util} onChange={setUtil} options={UTILITY} />
          <SegmentedControl label="Privacy attack" value={attack} onChange={setAttack} options={ATTACKS} />
        </div>

        <div className="stack">
          <ChartCard
            title="Fidelity: how close to the real data"
            subtitle="Average distance between each column's real and synthetic distribution."
            better="lower"
            table={tableFor(arms, fid, 'Fidelity distance, mean and spread over 20 seeds', 'Distance')}
            takeaway={
              <>
                <b>CTGAN and TVAE are about {(neuralRatio(neuralJsd, copJsd))}× further from the real data</b> than the copulas ({f3(r.ctgan.fidelity.jsd.mean)} and{' '}
                {f3(r.tvae.fidelity.jsd.mean)} against {f3(copJsd)}). The floor ties with the copulas because it copies each column exactly.
              </>
            }
          >
            <DotPlot rows={fidRows} domain={[0, 0.13]} ticks={[0, 0.03, 0.06, 0.09, 0.12]} label="Fidelity distance by generator" />
          </ChartCard>

          <ChartCard
            title="Utility: how well a model trained on it predicts"
            subtitle="Train on synthetic data, test on real held-out patients, predicting in-hospital death."
            better="higher"
            table={tableFor(arms, ut, `Prediction score (AUROC, ${util === 'tstr_rf' ? 'random forest' : 'logistic regression'}), mean and spread over 20 seeds`, 'AUROC')}
            takeaway={
              <>
                <b>TVAE reaches the real-data ceiling ({f3(ceiling)})</b>, but only because it copies training rows, as the privacy charts below show. The spread between runs
                (up to {f3(Math.max(...ut.map((u) => u.sd)))}) is bigger than most gaps between the other generators.
              </>
            }
          >
            <DotPlot
              rows={utRows}
              domain={[0.3, 0.95]}
              ticks={[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]}
              refs={[
                { value: 0.5, label: 'Guessing 0.5' },
                { value: ceiling, label: 'Real-data ceiling' },
              ]}
              label="Prediction score by generator"
            />
          </ChartCard>

          <ChartCard
            title="Privacy: how much the attack learns"
            subtitle={`Attacker guesses which real records trained the generator, using ${ATTACK_NAME[attack]}.`}
            better="lower"
            table={tableFor(arms, pr, `Membership attack score (${ATTACK_NAME[attack]}), mean and spread over 20 seeds`, 'Attack score')}
            takeaway={
              tvLowest ? (
                <>
                  <b>This attack cannot see the leak:</b> it scores TVAE at {f3(tv)}, the lowest of any generator, even though TVAE copies its training data. Switch to
                  "Worst case" to see it.
                </>
              ) : (
                <>
                  <b>TVAE leaks most</b> ({f3(tv)} against {f3(Math.min(...rest))} to {f3(Math.max(...rest))}). A score of 0.5 means the attacker is only guessing; 0.65 is the
                  protocol's fail line.
                </>
              )
            }
          >
            <DotPlot
              rows={prRows}
              domain={[0.45, 0.75]}
              ticks={[0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75]}
              refs={[
                { value: 0.5, label: 'Guessing 0.5' },
                { value: refs.fail_line, label: 'Fail line 0.65' },
              ]}
              label="Membership attack score by generator"
            />
          </ChartCard>
        </div>
      </div>
    </section>
  )
}

function neuralRatio(neural, copula) {
  return (neural / copula).toFixed(0)
}
