import React from 'react'
import { SIGNALS } from '../api'

const CITATION = /\s*\[([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)\]/g

// Renders prose and turns inline citations like [J3, P2] into quiet superscript links.
export function Cited({ text, evidence, onOpen }) {
  if (!text) return null
  const parts = []
  let last = 0
  for (const match of text.matchAll(CITATION)) {
    parts.push(text.slice(last, match.index))
    const ids = match[1].split(',').map((s) => s.trim()).filter((id) => evidence[id])
    if (ids.length) {
      parts.push(
        <sup key={match.index} className="ml-0.5 whitespace-nowrap font-mono text-[10px] font-medium">
          {ids.map((id, i) => (
            <React.Fragment key={id}>
              {i > 0 && <span className="text-ink-3">,</span>}
              <button onClick={() => onOpen(id)} title="Open the search result behind this"
                className="text-accent decoration-accent/40 underline-offset-2 hover:underline">{id}</button>
            </React.Fragment>
          ))}
        </sup>,
      )
    }
    last = match.index + match[0].length
  }
  parts.push(text.slice(last))
  return <>{parts}</>
}

// One link that opens just the receipts behind a claim.
export function ReceiptLink({ ids, onOpen, className = '' }) {
  if (!ids?.length) return null
  return (
    <button onClick={() => onOpen(ids)}
      className={`text-xs font-medium text-accent underline-offset-4 hover:underline ${className}`}>
      {ids.length === 1 ? 'View the receipt' : `View ${ids.length} receipts`} →
    </button>
  )
}

export function Eyebrow({ children, className = '' }) {
  return <p className={`text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-3 ${className}`}>{children}</p>
}

export function signalLabel(signal) {
  return SIGNALS[signal]?.label || signal
}

export function EngineChip({ engine }) {
  return <code className="rounded bg-raised px-1.5 py-0.5 font-mono text-[11px] text-ink-2">{engine}</code>
}

export function Section({ title, hint, children }) {
  return (
    <section className="rise">
      <h2 className="font-display text-3xl text-ink">{title}</h2>
      {hint && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-3">{hint}</p>}
      <div className="mt-6">{children}</div>
    </section>
  )
}

export function Card({ className = '', children }) {
  return <div className={`rounded-2xl border border-line bg-surface p-6 ${className}`}>{children}</div>
}

export function Stat({ label, value, note }) {
  return (
    <div>
      <p className="font-display text-3xl leading-none text-ink">{value}</p>
      <p className="mt-1.5 text-xs text-ink-2">{label}</p>
      {note && <p className="text-xs text-ink-3">{note}</p>}
    </div>
  )
}

export function Button({ children, variant = 'ghost', className = '', ...props }) {
  const styles = {
    primary: 'bg-ink text-white hover:bg-accent',
    ghost: 'border border-line bg-surface text-ink-2 hover:border-ink-3 hover:text-ink',
    quiet: 'text-ink-2 hover:text-ink',
  }
  return (
    <button {...props}
      className={`rounded-full px-4 py-2 text-sm font-medium transition disabled:opacity-40 ${styles[variant]} ${className}`}>
      {children}
    </button>
  )
}
