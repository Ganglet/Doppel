import { useState } from 'react'

export function TableView({ caption, columns, rows }) {
  return (
    <div className="tablewrap">
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" className={c.numeric ? 'n' : undefined}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.key} className={c.numeric ? 'n' : undefined}>
                  {r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// A chart with its title, a "which way is better" chip, the table-view twin, and one plain-language takeaway.
export default function ChartCard({ title, subtitle, better, table, takeaway, legend, children }) {
  const [view, setView] = useState('chart')
  return (
    <figure className="card" style={{ margin: 0 }}>
      <div className="chart-head">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="sub">{subtitle}</p>}
        </div>
        <div className="chart-tools">
          {better && <span className="chip">{better === 'lower' ? '↓ Lower is better' : '↑ Higher is better'}</span>}
          {table && (
            <button className="tbtn" aria-pressed={view === 'table'} onClick={() => setView(view === 'chart' ? 'table' : 'chart')}>
              {view === 'chart' ? 'Show table' : 'Show chart'}
            </button>
          )}
        </div>
      </div>
      <div className="chart-body">{view === 'chart' || !table ? children : <TableView {...table} />}</div>
      {view === 'chart' && legend}
      {takeaway && <p className="takeaway">{takeaway}</p>}
    </figure>
  )
}
