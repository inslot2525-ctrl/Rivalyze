import React, { useEffect, useMemo, useState } from 'react'
import { SIGNALS } from '../api'
import { EngineChip, signalLabel } from './ui'

// `focus` is one receipt id, a list of ids behind a single claim, or null for everything.
export default function EvidenceDrawer({ evidence, focus, onClose }) {
  const all = useMemo(() => Object.values(evidence), [evidence])
  const focused = useMemo(
    () => (focus ? [focus].flat().map((id) => evidence[id]).filter(Boolean) : []),
    [focus, evidence],
  )
  const [showAll, setShowAll] = useState(focused.length === 0)
  const [signal, setSignal] = useState('all')

  useEffect(() => { setShowAll(focused.length === 0); setSignal('all') }, [focused])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = '' }
  }, [onClose])

  const counts = useMemo(() => all.reduce((acc, e) => ({ ...acc, [e.signal]: (acc[e.signal] || 0) + 1 }), {}), [all])
  const shown = !showAll ? focused : signal === 'all' ? all : all.filter((e) => e.signal === signal)

  return (
    <div className="fixed inset-0 z-30 flex justify-end" role="dialog" aria-modal="true" aria-label="Receipts">
      <button className="flex-1 cursor-default bg-ink/25 backdrop-blur-[2px]" onClick={onClose} aria-label="Close receipts" />
      <aside className="rise flex h-full w-full max-w-lg flex-col bg-bg shadow-2xl">
        <header className="flex items-start justify-between px-7 pb-4 pt-7">
          <div>
            <h2 className="font-display text-3xl text-ink">{showAll ? 'All receipts' : focused.length === 1 ? 'The receipt' : 'The receipts'}</h2>
            <p className="mt-1 text-sm text-ink-3">
              {showAll
                ? `${all.length} search results this scan collected. Claims can only cite these.`
                : 'The search results behind this claim.'}
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded-full p-2 text-xl leading-none text-ink-3 hover:bg-raised hover:text-ink">×</button>
        </header>

        {showAll && (
          <div className="flex flex-wrap gap-1.5 px-7 pb-4">
            {['all', ...Object.keys(SIGNALS).filter((s) => counts[s])].map((s) => (
              <button key={s} onClick={() => setSignal(s)}
                className={`rounded-full px-3 py-1 text-xs transition ${signal === s ? 'bg-ink text-white' : 'bg-raised text-ink-2 hover:text-ink'}`}>
                {s === 'all' ? 'All' : signalLabel(s)} <span className="opacity-60">{s === 'all' ? all.length : counts[s]}</span>
              </button>
            ))}
          </div>
        )}

        <ul className="flex-1 space-y-3 overflow-y-auto px-7 pb-7">
          {shown.map((e) => (
            <li key={e.id} className="rounded-xl border border-line bg-surface p-4">
              <div className="mb-2 flex items-center gap-2 text-xs text-ink-3">
                <span className="font-mono font-medium text-accent">{e.id}</span>
                <span>{signalLabel(e.signal)}</span>
                {e.date && <span>· {e.date}</span>}
                <span className="ml-auto"><EngineChip engine={e.engine} /></span>
              </div>
              {e.link
                ? <a href={e.link} target="_blank" rel="noreferrer" className="font-medium leading-snug text-ink underline decoration-line underline-offset-4 hover:decoration-accent">{e.title} ↗</a>
                : <p className="font-medium leading-snug text-ink">{e.title}</p>}
              {e.snippet && <p className="mt-1.5 line-clamp-4 text-sm leading-relaxed text-ink-2">{e.snippet}</p>}
              <p className="mt-2.5 truncate text-xs text-ink-3" title={e.query}>
                {e.source ? `${e.source} · ` : ''}searched “{e.query}”
              </p>
            </li>
          ))}
        </ul>

        {!showAll && (
          <footer className="border-t border-line px-7 py-4">
            <button onClick={() => setShowAll(true)} className="text-sm font-medium text-accent underline-offset-4 hover:underline">
              Browse all {all.length} receipts →
            </button>
          </footer>
        )}
      </aside>
    </div>
  )
}
