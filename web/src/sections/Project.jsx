import { DOCS, LIMITS, ROADMAP, STATUS_LABEL, STEPS, TERMS, TRACKS } from '../lib/content'
import { f3 } from '../lib/format'

function Status({ kind }) {
  const icon = {
    done: <path d="M3.2 8.4l3 3 6.6-6.9" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />,
    partial: <><circle cx="8" cy="8" r="5.4" fill="none" stroke="currentColor" strokeWidth="1.8" /><path d="M8 2.6a5.4 5.4 0 0 1 0 10.8z" fill="currentColor" /></>,
    none: <circle cx="8" cy="8" r="5.4" fill="none" stroke="currentColor" strokeWidth="1.8" />,
  }[kind]
  return (
    <span className={`status ${kind}`}>
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">{icon}</svg>
      {STATUS_LABEL[kind]}
    </span>
  )
}

export default function Project({ data }) {
  const { dataset, meta } = data
  const docBase = `${meta.repo}/blob/${meta.docs_ref}/`
  return (
    <section id="project" aria-labelledby="h-project">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow">Project</span>
          <h2 id="h-project">How it works, and how far it has got</h2>
          <p>Four people work in four tracks on one pipeline. This page shows what has been built and, plainly, what has not.</p>
        </div>

        <div className="steps">
          {STEPS.map((s) => (
            <div key={s.n} className="card step">
              <div className="n" aria-hidden="true">{s.n}</div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
              <div className="owner"><Status kind={s.status} /> · {s.owner}</div>
            </div>
          ))}
        </div>

        <div className="card" style={{ marginTop: 18 }}>
          <h3>The data</h3>
          <p className="muted" style={{ marginTop: 6, maxWidth: 820 }}>
            {dataset.source}: {dataset.patients} patients and {dataset.admissions} hospital admissions with {dataset.columns} columns (age, diagnoses, lab results and more). Patients are split
            into {dataset.train} training and {dataset.holdout} held-out admissions, so no patient appears on both sides. {Math.round(dataset.mortality_rate * 100)}% of admissions ended in in-hospital
            death, and the held-out set has only {dataset.holdout_positives} of them. That is why utility scores vary so much between runs.
          </p>
        </div>

        <div className="section-head" style={{ marginTop: 52 }}>
          <h2>Status by track and phase</h2>
        </div>
        <div className="card">
          <div className="tablewrap" style={{ marginTop: 0 }}>
            <table className="road">
              <caption className="sr-only">Progress of each track in each project phase</caption>
              <thead>
                <tr>
                  <th />
                  {TRACKS.map((t) => (
                    <th key={t.id}>
                      {t.name}: {t.role}
                      <span className="small muted" style={{ display: 'block', fontWeight: 400 }}>{t.owner}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROADMAP.map((row) => (
                  <tr key={row.phase}>
                    <td className="phase">
                      {row.phase}
                      <span className="small muted" style={{ display: 'block', fontWeight: 400 }}>{row.weeks}</span>
                    </td>
                    {TRACKS.map((t) => (
                      <td key={t.id}>
                        <Status kind={row.cells[t.id][0]} />
                        {row.cells[t.id][1]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid two" style={{ marginTop: 18 }}>
          <div className="card">
            <h3>What this page does not show</h3>
            <ul className="list" style={{ marginTop: 10 }}>
              {LIMITS.map(([head, text]) => (
                <li key={head}>
                  <b>{head}</b> {text}
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h3>Read more</h3>
            <p className="muted small" style={{ marginTop: 6 }}>Every number on this page is written up, with its method and caveats, in the project documents.</p>
            <ul className="list" style={{ marginTop: 10, listStyle: 'none', padding: 0 }}>
              {DOCS.map(([title, path, desc]) => (
                <li key={path}>
                  <a href={docBase + path}>{title}</a>
                  <span className="small muted" style={{ display: 'block' }}>{desc}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="section-head" style={{ marginTop: 52 }}>
          <h2>Plain-language glossary</h2>
        </div>
        <dl className="terms card">
          {TERMS.map(([term, def]) => (
            <div key={term}>
              <dt>{term}</dt>
              <dd>{def}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
