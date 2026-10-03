import React, { useState } from 'react'
import { SIGNALS } from '../api'
import { Button, Eyebrow } from './ui'

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
    <div className="mx-auto max-w-5xl px-6 pb-28">
      <div className="mx-auto max-w-3xl pt-20 text-center md:pt-28">
        <h1 className="font-display text-6xl leading-[1.02] text-ink md:text-8xl">
          Read what your rivals <em className="text-accent">can't hide.</em>
        </h1>
        <p className="mx-auto mt-7 max-w-xl text-lg leading-relaxed text-ink-2">
          Companies script their press releases. They can't script what they hire for, patent or advertise.
          Rivalyze reads those signals and tells you their next move.
        </p>

        <form onSubmit={submit}
          className="mx-auto mt-10 flex max-w-xl items-center gap-2 rounded-full border border-line bg-surface p-1.5 pl-6 shadow-[0_8px_30px_-12px_rgba(23,25,29,0.18)] focus-within:border-ink-3">
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            maxLength={80}
            placeholder="Enter a competitor, e.g. Figma"
            aria-label="Company to scan"
            className="min-w-0 flex-1 bg-transparent py-2 text-base text-ink placeholder:text-ink-3 focus:outline-none"
          />
          <Button type="submit" variant="primary" disabled={!company.trim() || !canScan} className="px-6 py-2.5">
            Scan
          </Button>
        </form>
        <label className="mt-4 inline-flex items-center gap-2 text-sm text-ink-3">
          <input type="checkbox" checked={rivals} onChange={(e) => setRivals(e.target.checked)} className="accent-[var(--color-accent)]" />
          Compare against its closest rivals
        </label>
        {health && !canScan && (
          <p className="mx-auto mt-4 max-w-xl text-sm text-ink-3">
            Live scans need {!health.live_search ? 'SERPAPI_API_KEY' : 'GEMINI_API_KEY'} in backend/.env. The recorded scans below work without any key.
          </p>
        )}
      </div>

      {demos.length > 0 && (
        <div className="mt-24">
          <Eyebrow className="text-center">See a finished scan</Eyebrow>
          <div className="mt-6 grid gap-5 md:grid-cols-3">
            {demos.map((d) => (
              <button key={d.slug} onClick={() => onDemo(d.slug)}
                className="group flex flex-col rounded-2xl border border-line bg-surface p-6 text-left transition hover:-translate-y-0.5 hover:border-ink-3 hover:shadow-[0_12px_30px_-16px_rgba(23,25,29,0.25)]">
                <span className="font-display text-3xl text-ink">{d.company}</span>
                <p className="mt-3 line-clamp-4 flex-1 text-sm leading-relaxed text-ink-2">{d.one_liner}</p>
                <span className="mt-5 text-xs font-medium text-accent">
                  Replay the scan <span className="inline-block transition group-hover:translate-x-0.5">→</span>
                </span>
              </button>
            ))}
          </div>
          <p className="mt-4 text-center text-xs text-ink-3">Real scans, replayed. They use no searches and need no API key.</p>
        </div>
      )}

      {recent.length > 0 && (
        <div className="mx-auto mt-20 max-w-3xl">
          <Eyebrow>Your recent scans</Eyebrow>
          <ul className="mt-3 divide-y divide-line border-y border-line">
            {recent.slice(0, 5).map((s) => (
              <li key={s.id}>
                <button onClick={() => onOpenScan(s.id)} className="group flex w-full items-baseline gap-4 py-3.5 text-left">
                  <span className="w-28 shrink-0 font-medium text-ink group-hover:text-accent">{s.company}</span>
                  <span className="flex-1 truncate text-sm text-ink-3">{s.one_liner}</span>
                  {s.changes > 0 && <span className="shrink-0 text-xs font-medium text-accent">{s.changes} new</span>}
                  <span className="shrink-0 text-xs text-ink-3">{new Date(s.created_at).toLocaleDateString()}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mx-auto mt-24 max-w-3xl">
        <Eyebrow className="text-center">Six signals, straight from SerpApi</Eyebrow>
        <dl className="mt-6 grid gap-x-10 gap-y-6 sm:grid-cols-2 md:grid-cols-3">
          {LEAKS.map((key) => (
            <div key={key} className="border-t border-line pt-3">
              <dt className="font-display text-2xl text-ink">{SIGNALS[key].label}</dt>
              <dd className="mt-0.5 text-sm text-ink-2">{SIGNALS[key].blurb[0].toUpperCase() + SIGNALS[key].blurb.slice(1)}</dd>
              <dd className="mt-1.5 font-mono text-[11px] text-ink-3">{SIGNALS[key].engine}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  )
}
