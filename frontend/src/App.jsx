import React, { useCallback, useEffect, useRef, useState } from 'react'
import { getJSON, openStream } from './api'
import EvidenceDrawer from './components/EvidenceDrawer'
import Landing from './components/Landing'
import Report from './components/Report'
import ScanTrace from './components/ScanTrace'

export default function App() {
  const [view, setView] = useState('landing') // landing | scanning | report
  const [health, setHealth] = useState(null)
  const [usage, setUsage] = useState(null)
  const [demos, setDemos] = useState([])
  const [recent, setRecent] = useState([])
  const [company, setCompany] = useState('')
  const [events, setEvents] = useState([])
  const [replay, setReplay] = useState(false)
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)
  const [drawer, setDrawer] = useState(undefined) // undefined = closed, null = open with no focus
  const [offline, setOffline] = useState(false)
  const stop = useRef(null)

  const refresh = useCallback(() => {
    Promise.all([getJSON('/health'), getJSON('/demos'), getJSON('/scans')])
      .then(([h, d, s]) => { setHealth(h); setDemos(d); setRecent(s); setOffline(false) })
      .catch(() => setOffline(true))
    getJSON('/usage').then(setUsage).catch(() => {})
  }, [])

  useEffect(refresh, [refresh])

  // A report has a shareable address: #/scan/<id> or #/scan/demo:<slug>.
  useEffect(() => {
    const ref = window.location.hash.match(/^#\/scan\/(.+)$/)?.[1]
    const demo = window.location.hash.match(/^#\/demo\/(.+)$/)?.[1]
    if (ref) openScan(decodeURIComponent(ref))
    if (demo) start(`/demos/${demo}/stream`, demo, true)
  }, [])
  useEffect(() => {
    if (view === 'scanning') return
    const hash = view === 'report' && report ? `#/scan/${report.id}` : ''
    if (window.location.hash !== hash) window.history.replaceState(null, '', hash || window.location.pathname)
  }, [view, report])
  useEffect(() => () => stop.current?.(), [])

  const start = (path, name, isReplay) => {
    stop.current?.()
    setCompany(name)
    setEvents([])
    setError(null)
    setReport(null)
    setReplay(isReplay)
    setView('scanning')
    window.scrollTo(0, 0)
    stop.current = openStream(path, (event) => {
      if (event.type === 'report') {
        setReport(event.report)
        setView('report')
        window.scrollTo(0, 0)
        refresh()
      } else if (event.type === 'error') {
        setError(event.message)
      } else {
        setEvents((list) => [...list, event])
      }
    }, setError)
  }

  const home = () => {
    stop.current?.()
    setView('landing')
    setDrawer(undefined)
    refresh()
  }

  const openScan = async (id) => {
    try {
      setReport(await getJSON(`/scans/${encodeURIComponent(id)}`))
      setView('report')
      window.scrollTo(0, 0)
    } catch (e) { setOffline(true) }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <button onClick={home} className="font-display text-lg font-bold tracking-tight text-ink">
            Rivalyze<span className="text-accent">.</span>
          </button>
          <p className="font-mono text-[11px] text-ink-3">
            {usage?.live
              ? `SerpApi ${usage.plan || ''} · ${usage.searches_left ?? '?'} searches left`
              : usage ? 'Replay mode · no SerpApi key' : ''}
          </p>
        </div>
      </header>

      {offline && (
        <p role="alert" className="mx-auto mt-6 max-w-4xl rounded-lg border border-bad/50 bg-bad/10 px-4 py-3 text-sm text-ink">
          Can't reach the Rivalyze API. Start it with <code className="font-mono text-xs">uvicorn main:app --port 8000</code> in <code className="font-mono text-xs">backend/</code>, then reload.
        </p>
      )}

      {view === 'landing' && (
        <Landing demos={demos} health={health} recent={recent}
          onScan={(name, rivals) => start(`/scan/stream?company=${encodeURIComponent(name)}&rivals=${rivals}`, name, false)}
          onDemo={(slug) => start(`/demos/${slug}/stream`, demos.find((d) => d.slug === slug)?.company || slug, true)}
          onOpenScan={openScan} />
      )}
      {view === 'scanning' && (
        <ScanTrace company={company} events={events} error={error} replay={replay} onCancel={home} />
      )}
      {view === 'report' && report && (
        <Report report={report} onOpen={(id) => setDrawer(id)} onNew={home} />
      )}
      {view === 'report' && report && drawer !== undefined && (
        <EvidenceDrawer evidence={report.evidence} focus={drawer} onClose={() => setDrawer(undefined)} />
      )}
    </div>
  )
}
