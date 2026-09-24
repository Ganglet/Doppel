import { useEffect, useMemo, useState } from 'react'
import { useData } from '../lib/hooks'
import StatTile from '../components/StatTile'
import { FAMILY_COLOR, Swatch } from '../lib/marks'

const PREVIEW_ROWS = 20
const BASE = import.meta.env.BASE_URL

function cell(v) {
  if (v === null) return <span className="nil">—</span>
  if (typeof v === 'boolean') return v ? 'True' : 'False'
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(Math.round(v * 1000) / 1000)
  return v.length > 26 ? <span title={v}>{v.slice(0, 25)}…</span> : v
}

function toCsv(columns, rows) {
  const esc = (v) => {
    if (v === null) return ''
    if (typeof v === 'boolean') return v ? 'True' : 'False'
    const s = String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  return [columns.map((c) => esc(c.name)).join(','), ...rows.map((r) => r.map(esc).join(','))].join('\n')
}

function download(name, columns, rows) {
  const url = URL.createObjectURL(new Blob([toCsv(columns, rows)], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

export default function Datasets({ arms }) {
  const index = useData(`${BASE}data/datasets/index.json`)
  const [arm, setArm] = useState(null)
  const [seed, setSeed] = useState(null)
  const [all, setAll] = useState(false)
  const [find, setFind] = useState('')

  const list = index.data?.arms
  useEffect(() => {
    if (list?.length && !arm) {
      setArm(list[list.length - 1].id)
      setSeed(list[list.length - 1].seeds[0])
    }
  }, [list, arm])

  const current = list?.find((a) => a.id === arm)
  const table = useData(arm && seed != null ? `${BASE}data/datasets/${arm}_seed${seed}.json` : null)
  const t = arm && seed != null ? table.data : null
  const meta = arms.find((a) => a.id === arm)

  const pickArm = (id) => {
    const next = list.find((a) => a.id === id)
    setArm(id)
    setSeed(next.seeds.includes(seed) ? seed : next.seeds[0])
    setAll(false)
  }
  const shown = t ? (all ? t.rows : t.rows.slice(0, PREVIEW_ROWS)) : []
  const cols = useMemo(() => (t ? t.columns.filter((c) => c.name.toLowerCase().includes(find.trim().toLowerCase())) : []), [t, find])
  const m = t?.manifest

  return (
    <section id="data" aria-labelledby="h-data">
      <div className="wrap">
        <div className="section-head">
          <span className="eyebrow">Data</span>
          <h2 id="h-data">Look at the synthetic records</h2>
          <p>
            Pick a generator and a random seed to see the table it produced, with its column types and the record of how it was made. This is the same
            view as the Streamlit dashboard, for all five generators.
          </p>
        </div>

        {index.error && (
          <div className="notice" role="note">
            <span>
              <b>The dataset tables are not in the repository.</b> They are generated files, so they are left out of git. Generate the evaluation datasets,
              then run <code>npm run export-data</code> in <code>web/</code> and reload.
            </span>
          </div>
        )}
        {!index.error && !list && <div className="loading small">Loading datasets…</div>}

        {list && current && (
          <>
            <div className="filters">
              <label className="field">
                <span>Generator</span>
                <select className="select" value={arm} onChange={(e) => pickArm(e.target.value)}>
                  {list.map((a) => (
                    <option key={a.id} value={a.id}>{a.label}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Random seed</span>
                <select className="select" value={seed} onChange={(e) => { setSeed(Number(e.target.value)); setAll(false) }}>
                  {current.seeds.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>
              {meta && (
                <span className="field pick-note">
                  <Swatch shape={meta.marker} color={FAMILY_COLOR[meta.family]} />
                  <span className="small muted">{meta.family_label}</span>
                </span>
              )}
            </div>

            {table.error && <div className="loading small" role="alert">Could not load this dataset ({String(table.error.message)}).</div>}
            {!t && !table.error && <div className="loading small">Loading table…</div>}

            {t && (
              <div className="stack">
                <div className="grid three">
                  <StatTile label="Rows" value={t.n_rows} note="One synthetic hospital admission per row." />
                  <StatTile label="Columns" value={t.n_cols} note="Same 56 columns as the real cleaned table." />
                  <StatTile label="Missing values" value={t.missing} note="Empty cells across the whole table." />
                </div>

                <figure className="card" style={{ margin: 0 }}>
                  <div className="chart-head">
                    <div>
                      <h3>Dataset preview</h3>
                      <p className="sub">
                        {all ? `All ${t.n_rows} rows` : `First ${Math.min(PREVIEW_ROWS, t.n_rows)} of ${t.n_rows} rows`} of <span className="num">{t.file}</span>. Scroll sideways for more columns.
                      </p>
                    </div>
                    <div className="chart-tools">
                      {t.n_rows > PREVIEW_ROWS && (
                        <button className="tbtn" onClick={() => setAll(!all)}>{all ? `Show first ${PREVIEW_ROWS}` : `Show all ${t.n_rows}`}</button>
                      )}
                      <button className="tbtn" onClick={() => download(t.file, t.columns, t.rows)}>Download CSV</button>
                    </div>
                  </div>
                  <div className="sheet" tabIndex={0} role="region" aria-label={`Rows of ${t.file}, scrollable`}>
                    <table>
                      <thead>
                        <tr>
                          <th scope="col" className="n rownum">#</th>
                          {t.columns.map((c) => (
                            <th key={c.name} scope="col">{c.name}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {shown.map((r, i) => (
                          <tr key={i}>
                            <td className="n rownum">{i}</td>
                            {r.map((v, j) => (
                              <td key={j} className={typeof v === 'number' ? 'n' : undefined}>{cell(v)}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </figure>

                <div className="grid two">
                  <div className="card">
                    <h3>Column information</h3>
                    <p className="muted small" style={{ marginTop: 4 }}>The type of each column and how many values are missing.</p>
                    <input className="search" type="search" placeholder="Find a column" aria-label="Find a column" value={find} onChange={(e) => setFind(e.target.value)} />
                    <div className="sheet short" tabIndex={0} role="region" aria-label="Column information, scrollable">
                      <table>
                        <thead>
                          <tr>
                            <th scope="col">Column</th>
                            <th scope="col">Data type</th>
                            <th scope="col" className="n">Missing</th>
                          </tr>
                        </thead>
                        <tbody>
                          {cols.map((c) => (
                            <tr key={c.name}>
                              <td>{c.name}</td>
                              <td className="muted">{c.dtype}</td>
                              <td className="n">{c.missing}</td>
                            </tr>
                          ))}
                          {cols.length === 0 && (
                            <tr><td colSpan="3" className="muted">No column matches “{find}”.</td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="card">
                    <h3>Generator manifest</h3>
                    <p className="muted small" style={{ marginTop: 4 }}>The record the generator wrote about this run.</p>
                    {m ? (
                      <>
                        <dl className="kv">
                          <div><dt>Generator</dt><dd>{m.generator_name} {m.generator_version}</dd></div>
                          <div><dt>Seed</dt><dd className="num">{m.seed}</dd></div>
                          <div><dt>Records written</dt><dd className="num">{m.num_records}</dd></div>
                          <div><dt>Trained on</dt><dd className="num">{m.train_rows} rows</dd></div>
                          <div><dt>Created</dt><dd className="num">{String(m.created_utc).slice(0, 19).replace('T', ' ')} UTC</dd></div>
                          <div><dt>Code version</dt><dd className="num">{m.git_commit}</dd></div>
                        </dl>
                        <details className="raw">
                          <summary>Show the full manifest</summary>
                          <pre>{JSON.stringify(m, null, 2)}</pre>
                        </details>
                      </>
                    ) : (
                      <p className="muted small" style={{ marginTop: 10 }}>No manifest file was found for this dataset.</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
