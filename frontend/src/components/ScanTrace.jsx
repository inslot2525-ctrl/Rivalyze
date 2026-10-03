import React from 'react'
import { Button, EngineChip, Eyebrow } from './ui'

const STAGES = [
  ['scout', 'Scout', 'Finding the company and who people compare it to'],
  ['plan', 'Plan', 'Choosing rivals and the right queries'],
  ['collect', 'Collect', 'Pulling the signals in parallel'],
  ['critique', 'Critique', 'Looking for gaps in the evidence'],
  ['followup', 'Follow up', 'Running the searches the critic asked for'],
  ['analyse', 'Analyse', 'Reading the evidence. This is the slow step, 20 to 40 seconds'],
  ['ground', 'Verify', 'Deleting any claim without a receipt'],
]

export function SearchRow({ call }) {
  return (
    <li className="rise flex items-center gap-3 py-2.5 text-sm">
      <EngineChip engine={call.engine} />
      <span className="min-w-0 flex-1 truncate text-ink-2" title={call.query}>{call.query}</span>
      <span className="hidden text-xs text-ink-3 sm:inline">{call.results} results</span>
      <span className="w-14 text-right text-xs text-ink-3">{call.cached ? 'cached' : `${(call.ms / 1000).toFixed(1)}s`}</span>
    </li>
  )
}

export default function ScanTrace({ company, events, error, replay, onCancel }) {
  const stage = [...events].reverse().find((e) => e.type === 'stage')?.stage
  const reached = STAGES.findIndex(([key]) => key === stage)
  const searches = events.filter((e) => e.type === 'search')
  const plan = events.find((e) => e.type === 'plan')
  const critique = events.find((e) => e.type === 'critique')
  const grounding = events.find((e) => e.type === 'grounding')
  const current = STAGES[reached]

  return (
    <div className="mx-auto max-w-3xl px-6 pb-28 pt-16">
      <div className="text-center">
        <Eyebrow>{replay ? 'Replaying a recorded scan' : 'Scanning'}</Eyebrow>
        <h1 className="mt-2 font-display text-6xl capitalize text-ink">{plan?.company || company}</h1>
        {!error && current && <p className="blink mt-3 text-ink-2">{current[2]}…</p>}
      </div>

      {error && (
        <div role="alert" className="mt-8 rounded-2xl border border-bad/30 bg-bad/5 p-5 text-center">
          <p className="font-medium text-ink">The scan stopped</p>
          <p className="mt-1 text-sm text-ink-2">{error}</p>
        </div>
      )}

      <ol className="mt-10 flex items-center justify-between gap-1" aria-label="Scan progress">
        {STAGES.map(([key, label], i) => {
          const done = i < reached
          const active = i === reached && !error
          return (
            <li key={key} className="flex flex-1 flex-col items-center gap-2">
              <span className={`h-1 w-full rounded-full transition-colors ${done ? 'bg-accent' : active ? 'blink bg-accent' : 'bg-line'}`} />
              <span className={`text-xs ${done || active ? 'font-medium text-ink' : 'text-ink-3'}`}>{label}</span>
            </li>
          )
        })}
      </ol>

      <div className="mt-12 space-y-10">
        {plan?.rivals?.length > 0 && (
          <div className="rise">
            <Eyebrow>Rivals, from what people type after "{company} vs"</Eyebrow>
            <p className="mt-2 font-display text-2xl text-ink">{plan.rivals.join(' · ')}</p>
          </div>
        )}

        <div>
          <div className="flex items-baseline justify-between">
            <Eyebrow>SerpApi searches</Eyebrow>
            <p className="text-xs text-ink-3">
              {searches.length} run · {searches.filter((s) => s.cached).length} from cache
            </p>
          </div>
          <ul className="mt-2 divide-y divide-line border-y border-line">
            {searches.map((s, i) => <SearchRow key={i} call={s} />)}
            {searches.length === 0 && <li className="py-3 text-sm text-ink-3">Waiting for the first search…</li>}
          </ul>
        </div>

        {critique && (
          <div className="rise">
            <Eyebrow>The critic asked for more</Eyebrow>
            <ul className="mt-3 space-y-2.5">
              {critique.follow_ups.map((f, i) => (
                <li key={i} className="border-l-2 border-accent pl-4 text-sm leading-relaxed text-ink-2">{f.reason}</li>
              ))}
              {critique.follow_ups.length === 0 && <li className="text-sm text-ink-3">Nothing more was needed.</li>}
            </ul>
          </div>
        )}

        {grounding && (
          <p className="rise text-sm text-ink-2">
            Verified {grounding.claims_checked} claims against their receipts. {grounding.claims_dropped} dropped.
          </p>
        )}
      </div>

      <div className="mt-12 text-center">
        <Button variant="quiet" onClick={onCancel}>{error ? 'Back' : 'Cancel'}</Button>
      </div>
    </div>
  )
}
