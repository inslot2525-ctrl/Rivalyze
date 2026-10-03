import React from 'react'
import { SIGNALS } from '../api'

const CITATION = /\[([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)\]/g

export function Receipt({ id, onOpen }) {
  return (
    <button
      onClick={() => onOpen(id)}
      title="Open the search result behind this claim"
      className="mx-0.5 inline-flex items-center rounded border border-accent/40 bg-accent/10 px-1.5 py-px align-baseline font-mono text-[11px] font-medium text-accent transition-colors hover:bg-accent/25"
    >
      {id}
    </button>
  )
}

// Renders prose and turns inline citations like [J3, P2] into clickable receipts.
export function Cited({ text, evidence, onOpen }) {
  if (!text) return null
  const parts = []
  let last = 0
  for (const match of text.matchAll(CITATION)) {
    parts.push(text.slice(last, match.index))
    match[1].split(',').map((s) => s.trim()).filter((id) => evidence[id]).forEach((id) => {
      parts.push(<Receipt key={`${match.index}-${id}`} id={id} onOpen={onOpen} />)
    })
    last = match.index + match[0].length
  }
  parts.push(text.slice(last))
  return <>{parts}</>
}

export function Receipts({ ids, onOpen }) {
  return (
    <span className="inline-flex flex-wrap gap-y-1">
      {ids.map((id) => <Receipt key={id} id={id} onOpen={onOpen} />)}
    </span>
  )
}

export function SignalTag({ signal }) {
  return (
    <span className="rounded-full border border-line bg-raised px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-2">
      {SIGNALS[signal]?.label || signal}
    </span>
  )
}

export function EngineChip({ engine }) {
  return <code className="rounded bg-raised px-1.5 py-0.5 font-mono text-[11px] text-ink-2">{engine}</code>
}

export function Section({ eyebrow, title, hint, children, action }) {
  return (
    <section className="rise">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          {eyebrow && <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.18em] text-accent">{eyebrow}</p>}
          <h2 className="font-display text-xl font-semibold text-ink">{title}</h2>
          {hint && <p className="mt-1 max-w-2xl text-sm text-ink-3">{hint}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export function Card({ className = '', children }) {
  return <div className={`rounded-xl border border-line bg-surface p-5 ${className}`}>{children}</div>
}

export function Stat({ label, value, note }) {
  return (
    <div>
      <p className="text-xs text-ink-3">{label}</p>
      <p className="font-display text-2xl font-semibold text-ink">{value}</p>
      {note && <p className="text-xs text-ink-3">{note}</p>}
    </div>
  )
}

export function Button({ children, variant = 'ghost', className = '', ...props }) {
  const styles = {
    primary: 'bg-accent text-black hover:brightness-110 font-semibold',
    ghost: 'border border-line bg-surface text-ink-2 hover:border-ink-3 hover:text-ink',
  }
  return (
    <button {...props}
      className={`rounded-lg px-3.5 py-2 text-sm transition disabled:opacity-50 ${styles[variant]} ${className}`}>
      {children}
    </button>
  )
}
