import React, { useEffect, useMemo, useRef, useState } from 'react'
import { SIGNALS } from '../api'
import { EngineChip, SignalTag } from './ui'

export default function EvidenceDrawer({ evidence, focus, onClose }) {
  const [signal, setSignal] = useState('all')
  const focusRef = useRef(null)
  const items = useMemo(() => Object.values(evidence), [evidence])
  const counts = useMemo(() => items.reduce((acc, e) => ({ ...acc, [e.signal]: (acc[e.signal] || 0) + 1 }), {}), [items])

  useEffect(() => {
    if (focus && evidence[focus]) setSignal(evidence[focus].signal)
  }, [focus, evidence])

  useEffect(() => {
    focusRef.current?.scrollIntoView({ block: 'center' })
  }, [focus, signal])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const shown = signal === 'all' ? items : items.filter((e) => e.signal === signal)

  return (
    <div className="fixed inset-0 z-30 flex justify-end" role="dialog" aria-modal="true" aria-label="Receipts">
      <button className="flex-1 cursor-default bg-black/50" onClick={onClose} aria-label="Close receipts" />
      <aside className="flex h-full w-full max-w-xl flex-col border-l border-line bg-bg">
        <header className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <h2 className="font-display text-lg font-semibold text-ink">Receipts</h2>
            <p className="text-xs text-ink-3">{items.length} search results this scan collected. Claims can only cite these.</p>
          </div>
          <button onClick={onClose} className="rounded-lg border border-line px-2.5 py-1 text-sm text-ink-2 hover:text-ink">Close</button>
        </header>
        <div className="flex flex-wrap gap-1.5 border-b border-line px-5 py-3">
          {['all', ...Object.keys(SIGNALS).filter((s) => counts[s])].map((s) => (
            <button key={s} onClick={() => setSignal(s)}
              className={`rounded-full border px-2.5 py-1 text-xs ${signal === s ? 'border-accent bg-accent/15 text-ink' : 'border-line text-ink-3 hover:text-ink'}`}>
              {s === 'all' ? `All ${items.length}` : `${SIGNALS[s].label} ${counts[s]}`}
            </button>
          ))}
        </div>
        <ul className="flex-1 space-y-2 overflow-y-auto px-5 py-4">
          {shown.map((e) => (
            <li key={e.id} ref={e.id === focus ? focusRef : null}
              className={`rounded-lg border p-3 ${e.id === focus ? 'border-accent bg-accent/10' : 'border-line bg-surface'}`}>
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-medium text-accent">{e.id}</span>
                <SignalTag signal={e.signal} />
                <EngineChip engine={e.engine} />
                {e.date && <span className="text-xs text-ink-3">{e.date}</span>}
              </div>
              {e.link
                ? <a href={e.link} target="_blank" rel="noreferrer" className="text-sm font-medium text-ink underline decoration-line underline-offset-2 hover:decoration-accent">{e.title}</a>
                : <p className="text-sm font-medium text-ink">{e.title}</p>}
              {e.snippet && <p className="mt-1 line-clamp-4 text-xs text-ink-2">{e.snippet}</p>}
              <p className="mt-2 text-[11px] text-ink-3">
                {e.subject}{e.source ? ` · ${e.source}` : ''} · query: <span className="font-mono">{e.query}</span>
              </p>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
