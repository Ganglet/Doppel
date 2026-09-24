import { Component, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useData, useScrollSpy, useTheme } from './lib/hooks'
import Overview from './sections/Overview'
import Compare from './sections/Compare'
import Tradeoff from './sections/Tradeoff'
import Privacy from './sections/Privacy'
import Datasets from './sections/Datasets'
import Project from './sections/Project'

const SECTIONS = [
  ['overview', 'Overview'],
  ['compare', 'Compare'],
  ['tradeoffs', 'Trade-offs'],
  ['privacy', 'Privacy'],
  ['data', 'Data'],
  ['project', 'Project'],
]

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--accent)" />
      <circle cx="12" cy="16" r="5" fill="#fff" />
      <circle cx="21" cy="16" r="5" fill="none" stroke="#fff" strokeWidth="2" />
    </svg>
  )
}

function ThemeToggle({ theme, onToggle }) {
  return (
    <button className="icon-btn" onClick={onToggle} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
        {theme === 'dark' ? (
          <path d="M8 1.5a.7.7 0 0 1 .7.7v1.1a.7.7 0 0 1-1.4 0V2.2A.7.7 0 0 1 8 1.5zm0 10.1a.7.7 0 0 1 .7.7v1.1a.7.7 0 0 1-1.4 0v-1.1a.7.7 0 0 1 .7-.7zM2.2 7.3h1.1a.7.7 0 0 1 0 1.4H2.2a.7.7 0 0 1 0-1.4zm10.5 0h1.1a.7.7 0 0 1 0 1.4h-1.1a.7.7 0 0 1 0-1.4zM8 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6z" fill="currentColor" />
        ) : (
          <path d="M6.3 1.6a6.4 6.4 0 1 0 8.1 8.1A5.2 5.2 0 0 1 6.3 1.6z" fill="currentColor" />
        )}
      </svg>
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  )
}

class Guard extends Component {
  state = { error: null }
  static getDerivedStateFromError(error) {
    return { error }
  }
  render() {
    if (this.state.error)
      return (
        <div className="loading" role="alert">
          <div>
            <b>Something went wrong drawing this section.</b>
            <p className="muted small">{String(this.state.error.message)}</p>
          </div>
        </div>
      )
    return this.props.children
  }
}

// A pill that slides to the section you are reading, and keeps that link in view when the nav scrolls on a phone.
function Nav({ active }) {
  const nav = useRef(null)
  const [pill, setPill] = useState(null)
  useLayoutEffect(() => {
    const place = () => {
      const el = nav.current?.querySelector('[aria-current="true"]')
      if (!el) return
      setPill({ x: el.offsetLeft, w: el.offsetWidth })
      const n = nav.current
      n.scrollTo({ left: el.offsetLeft - (n.clientWidth - el.offsetWidth) / 2, behavior: 'smooth' })
    }
    place()
    window.addEventListener('resize', place)
    return () => window.removeEventListener('resize', place)
  }, [active])
  return (
    <nav className="nav" aria-label="Sections" ref={nav}>
      {pill && <span className="nav-pill" aria-hidden="true" style={{ width: pill.w, transform: `translateX(${pill.x}px)` }} />}
      {SECTIONS.map(([id, label]) => (
        <a key={id} href={`#${id}`} aria-current={active === id ? 'true' : undefined}>{label}</a>
      ))}
    </nav>
  )
}

export default function App() {
  const { data, error } = useData(`${import.meta.env.BASE_URL}data/dashboard.json`)
  const [theme, toggleTheme] = useTheme()
  const ids = useMemo(() => SECTIONS.map((s) => s[0]), [])
  const active = useScrollSpy(ids, Boolean(data))

  // The sections only exist once the data has loaded, so a link like /#data has to scroll afterwards.
  useEffect(() => {
    if (data && window.location.hash) document.getElementById(window.location.hash.slice(1))?.scrollIntoView()
  }, [data])

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="top">
        <div className="wrap">
          <a className="brand" href="#overview"><Logo />Doppel</a>
          <Nav active={active} />
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
      </header>

      <main id="main">
        {error && <div className="loading">Could not load the results ({String(error.message)}). Run <code>npm run export-data</code> and reload.</div>}
        {!data && !error && <div className="loading">Loading results…</div>}
        {data && (
          <>
            <Guard><Overview data={data} /></Guard>
            <Guard><Compare data={data} /></Guard>
            <Guard><Tradeoff data={data} /></Guard>
            <Guard><Privacy data={data} /></Guard>
            <Guard><Datasets arms={data.arms} /></Guard>
            <Guard><Project data={data} /></Guard>
          </>
        )}
      </main>

      {data && (
        <footer>
          <div className="wrap">
            <div>
              <b>Project Doppel</b> · a course project (Big Data Analysis)
              <div className="small">Aggregate evaluation metrics only, no patient rows. Code MIT, MIMIC-III-derived data ODbL 1.0.</div>
            </div>
            <div className="small">
              Results exported {meta_date(data.meta.generated_utc)} from commit {data.meta.source_commit}
              <br />
              <a href={data.meta.repo}>github.com/Ganglet/Doppel</a>
            </div>
          </div>
        </footer>
      )}
    </>
  )
}

function meta_date(iso) {
  return new Date(iso).toISOString().slice(0, 10)
}
