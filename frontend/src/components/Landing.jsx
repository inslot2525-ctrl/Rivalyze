import React, { useState } from 'react'
import { SIGNALS } from '../api'
import { Button, EngineChip } from './ui'

const LEAKS = ['hiring', 'rnd', 'ads', 'demand', 'doubts', 'ai_view']

export default function Landing({ demos, health, recent, onScan, onDemo, onOpenScan }) {
  const [company, setCompany] = useState('')
  const [rivals, setRivals] = useState(true)
  const canScan = health?.live_search && health?.llm

  const submit = (e) => {
    e.preventDefault()
    if (company.trim()) onScan(company.trim(), rivals)
  }

  return (
    <div className="mx-auto max-w-4xl px-5 pb-20 pt-16">
      <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-accent">Competitive intelligence from search data</p>
      <h1 className="font-display text-4xl font-bold leading-tight text-ink md:text-6xl">
        Read what your rivals<br />can't hide.
      </h1>
      <p className="mt-5 max-w-2xl text-lg text-ink-2">
        A company scripts its press releases. It can't script what it hires for, what it patents, which ads it
        buys or what people search about it. Rivalyze reads those signals, compares them with the official
        story, and predicts the next move. Every claim links to the search result behind it.
      </p>

      <form onSubmit={submit} className="mt-9 flex flex-col gap-3 sm:flex-row">
        <input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          maxLength={80}
          placeholder="A competitor's name, e.g. Notion"
          aria-label="Company to scan"
          className="flex-1 rounded-lg border border-line bg-surface px-4 py-3 text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none"
        />
        <Button type="submit" variant="primary" disabled={!company.trim() || !canScan} className="px-6 py-3">
          Scan
        </Button>
      </form>
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-ink-3">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={rivals} onChange={(e) => setRivals(e.target.checked)} className="accent-[var(--color-accent)]" />
          Compare against its closest rivals
        </label>
        <span>A live scan uses at most {health?.scan_budget ?? 15} SerpApi searches. Repeats are served from cache.</span>
      </div>
      {health && !canScan && (
        <p className="mt-3 rounded-lg border border-line bg-surface px-4 py-3 text-sm text-ink-2">
          Live scans are off because {!health.live_search ? 'SERPAPI_API_KEY' : 'GEMINI_API_KEY'} is not set in
          <code className="mx-1 font-mono text-xs">backend/.env</code>. The recorded scans below work without any key.
        </p>
      )}

      {demos.length > 0 && (
        <div className="mt-12">
          <h2 className="font-display text-lg font-semibold text-ink">Recorded scans</h2>
          <p className="mt-1 text-sm text-ink-3">Real scans replayed step by step. They spend no searches.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {demos.map((d) => (
              <button key={d.slug} onClick={() => onDemo(d.slug)}
                className="rounded-xl border border-line bg-surface p-4 text-left transition hover:border-accent/60">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-display text-lg font-semibold text-ink">{d.company}</span>
                  <span className="font-mono text-[11px] text-ink-3">recorded {d.recorded_at.slice(0, 10)}</span>
                </div>
                <p className="mt-1.5 line-clamp-3 text-sm text-ink-2">{d.one_liner}</p>
                <p className="mt-3 text-xs text-ink-3">{d.searches} searches · {d.evidence} pieces of evidence · vs {d.rivals.slice(0, 2).join(', ')}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {recent.length > 0 && (
        <div className="mt-10">
          <h2 className="font-display text-lg font-semibold text-ink">Your recent scans</h2>
          <ul className="mt-3 divide-y divide-line rounded-xl border border-line bg-surface">
            {recent.slice(0, 5).map((s) => (
              <li key={s.id}>
                <button onClick={() => onOpenScan(s.id)} className="flex w-full items-baseline gap-3 px-4 py-3 text-left hover:bg-raised">
                  <span className="w-28 shrink-0 font-medium text-ink">{s.company}</span>
                  <span className="flex-1 truncate text-sm text-ink-3">{s.one_liner}</span>
                  {s.changes > 0 && <span className="shrink-0 text-xs text-accent">{s.changes} changes</span>}
                  <span className="shrink-0 font-mono text-[11px] text-ink-3">{s.created_at.slice(0, 10)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-14">
        <h2 className="font-display text-lg font-semibold text-ink">The signals it reads</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 md:grid-cols-3">
          {LEAKS.map((key) => (
            <div key={key} className="rounded-xl border border-line bg-surface p-4">
              <p className="font-medium text-ink">{SIGNALS[key].label}</p>
              <p className="mb-2 text-sm text-ink-3">{SIGNALS[key].blurb}</p>
              <EngineChip engine={SIGNALS[key].engine} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
