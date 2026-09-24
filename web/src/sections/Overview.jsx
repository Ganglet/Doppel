import StatTile from '../components/StatTile'
import { f3, pval } from '../lib/format'

export default function Overview({ data }) {
  const { results: r, refs, meta, pareto, tests, coverage } = data
  const others = ['independent_marginals', 'gaussian_copula', 'gaussian_copula_shrink025', 'ctgan']
  const worst = others.map((a) => r[a].privacy.worst.mean)
  const lo = Math.min(...worst)
  const hi = Math.max(...worst)
  const onFrontier = Object.values(pareto.frontier).filter(Boolean).length
  const total = Object.keys(pareto.frontier).length
  const copulaJsd = r.gaussian_copula.fidelity.jsd.mean
  const neuralRatio = ((r.ctgan.fidelity.jsd.mean + r.tvae.fidelity.jsd.mean) / 2 / copulaJsd).toFixed(0)

  return (
    <section id="overview" aria-labelledby="h-overview">
      <div className="wrap">
        <div className="hero">
          <div>
            <span className="eyebrow">Project Doppel · Synthetic health-record benchmark</span>
            <h1 id="h-overview">Which synthetic-data generator is realistic, useful and private?</h1>
            <p className="lead">
              Hospitals want to share patient data for research without exposing patients. Doppel tests generators of synthetic records on three
              things at once: how realistic they are, how useful they are for a prediction task, and how much they reveal about the real patients
              they learned from.
            </p>
            <div className="cta">
              <a className="btn primary" href="#compare">Compare the generators</a>
              <a className="btn" href="#tradeoffs">See the trade-offs</a>
            </div>
          </div>
          <div className="card hero-figure">
            <div className="value num">{f3(r.tvae.privacy.worst.mean)}</div>
            <div className="label">Membership-attack score for TVAE</div>
            <p className="muted">
              TVAE is the generator that copies its training data. The attack scores 0.5 when it is guessing and 1.0 when it always wins. The
              other four generators score {f3(lo)} to {f3(hi)}.
            </p>
          </div>
        </div>

        <div className="notice" role="note">
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <circle cx="9" cy="9" r="8" fill="none" stroke="var(--accent)" strokeWidth="1.6" />
            <path d="M9 8v5M9 5.2v.1" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <span>
            <b>Work in progress.</b> Five generator settings are evaluated on {data.dataset.train} training rows. The diffusion model, the third
            planned generator family, is not built yet, so these results are a first comparison and not the final one.
          </span>
        </div>

        <div className="grid four" style={{ marginTop: 26 }}>
          <StatTile label="Evaluation runs" value={meta.runs} note={`5 generators × ${r.tvae.n_seeds} random seeds each`} />
          <StatTile label="Best prediction score" value={f3(r.tvae.utility.tstr_rf.mean)} note={`TVAE. Models trained on real data reach ${f3(refs.trtr_rf)}, so this comes from copying.`} />
          <StatTile label="Closest to the real data" value={f3(copulaJsd)} note={`Copulas and the floor tie. CTGAN and TVAE are about ${neuralRatio}× further away.`} />
          <StatTile label="On the trade-off frontier" value={`${onFrontier} of ${total}`} note="So the data cannot rank the generators." />
        </div>

        <div className="section-head" style={{ marginTop: 56 }}>
          <h2>What we found</h2>
          <p>Three results from the full comparison, each with the numbers behind it.</p>
        </div>
        <div className="grid three">
          <article className="card finding">
            <span className="tag">Privacy</span>
            <h3>TVAE copies its training data, and the attacks catch it</h3>
            <p>
              A generator that memorizes should look leaky, and it does. A weaker attack on four columns misses it entirely, which is why the
              privacy score uses the worst of three attacks.
            </p>
            <div className="evidence">
              Score <b className="num">{f3(r.tvae.privacy.worst.mean)}</b> against <b className="num">{f3(lo)}–{f3(hi)}</b> for the others (
              {pval(tests.tvae_vs_independent_marginals_worst_p)}). Its output sits nearest to only{' '}
              <b>{coverage.tvae.distinct.mean.toFixed(0)} of 94</b> training rows.
            </div>
          </article>
          <article className="card finding">
            <span className="tag">Fidelity</span>
            <h3>CTGAN learned almost nothing at this size</h3>
            <p>
              With 94 training rows, the GAN gets each column's shape wrong and learns no relationships between columns. It performs about like the
              floor that ignores relationships altogether.
            </p>
            <div className="evidence">
              Distance from real data <b className="num">{f3(r.ctgan.fidelity.jsd.mean)}</b> against <b className="num">{f3(copulaJsd)}</b> for the copula.
              Correlation error <b className="num">{f3(r.ctgan.fidelity.corr_diff.mean)}</b> against the floor's{' '}
              <b className="num">{f3(r.independent_marginals.fidelity.corr_diff.mean)}</b>.
            </div>
          </article>
          <article className="card finding">
            <span className="tag">Trade-off</span>
            <h3>A simple statistical model is the best trade-off here</h3>
            <p>
              The copula with less shrinkage predicts about as well as TVAE, stays close to the real data, and leaks less. It does not need
              to copy anything to get there.
            </p>
            <div className="evidence">
              Prediction score <b className="num">{f3(r.gaussian_copula_shrink025.utility.tstr_mean.mean)}</b> vs TVAE{' '}
              <b className="num">{f3(r.tvae.utility.tstr_mean.mean)}</b> ({pval(tests.tvae_vs_shrink025_utility_p)}). Leakage{' '}
              <b className="num">{f3(r.gaussian_copula_shrink025.privacy.worst.mean)}</b> vs{' '}
              <b className="num">{f3(r.tvae.privacy.worst.mean)}</b>.
            </div>
          </article>
        </div>
      </div>
    </section>
  )
}
