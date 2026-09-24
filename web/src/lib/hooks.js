import { useEffect, useLayoutEffect, useRef, useState } from 'react'

export function useData(url) {
  const [state, setState] = useState({ data: null, error: null })
  useEffect(() => {
    if (!url) return
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

// The section being read is the last one whose top has passed 35% of the way down the window. Sections only
// exist once the data has loaded, so this waits for `ready` before it starts listening.
export function useScrollSpy(ids, ready) {
  const [active, setActive] = useState(ids[0])
  useEffect(() => {
    if (!ready) return
    let frame = 0
    const update = () => {
      frame = 0
      const line = window.innerHeight * 0.35
      const atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4
      let current = ids[0]
      for (const id of ids) {
        const el = document.getElementById(id)
        if (el && el.getBoundingClientRect().top <= line) current = id
      }
      setActive(atEnd ? ids[ids.length - 1] : current)
    }
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [ids, ready])
  return active
}
