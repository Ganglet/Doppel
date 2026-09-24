import { useEffect, useLayoutEffect, useRef, useState } from 'react'

export function useData(url) {
  const [state, setState] = useState({ data: null, error: null })
  useEffect(() => {
    let live = true
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => live && setState({ data, error: null }))
      .catch((error) => live && setState({ data: null, error }))
    return () => {
      live = false
    }
  }, [url])
  return state
}

export function useTheme() {
  const read = () => {
    const asked = new URLSearchParams(window.location.search).get('theme')
    if (asked === 'light' || asked === 'dark') return asked
    try {
      return localStorage.getItem('doppel-theme')
    } catch {
      return null
    }
  }
  const [theme, setTheme] = useState(read)
  useEffect(() => {
    const root = document.documentElement
    if (theme) root.setAttribute('data-theme', theme)
    else root.removeAttribute('data-theme')
    try {
      if (theme) localStorage.setItem('doppel-theme', theme)
    } catch {
      /* storage can be blocked; the toggle still works for this visit */
    }
  }, [theme])
  const systemDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches
  const effective = theme || (systemDark() ? 'dark' : 'light')
  return [effective, () => setTheme(effective === 'dark' ? 'light' : 'dark')]
}

export function useSize() {
  const ref = useRef(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setSize({ width: el.clientWidth, height: el.clientHeight })
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, size]
}

export function useScrollSpy(ids) {
  const [active, setActive] = useState(ids[0])
  useEffect(() => {
    const els = ids.map((id) => document.getElementById(id)).filter(Boolean)
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-30% 0px -55% 0px', threshold: [0, 0.2, 0.5] },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [ids])
  return active
}
