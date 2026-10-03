import React from 'react'
import { SIGNALS } from '../api'
import { Button, EngineChip } from './ui'

const STAGES = [
  ['scout', 'Scout', 'Who is this, and who do people compare it to?'],
  ['plan', 'Plan', 'Resolve the company, its rivals and the right queries'],
  ['collect', 'Collect', 'Pull the signals in parallel'],
  ['critique', 'Critique', 'Find the gaps in the evidence'],
  ['followup', 'Follow up', 'Run the searches the critic asked for'],
  ['analyse', 'Analyse', 'Read the evidence for tells and forecasts'],
  ['ground', 'Ground', 'Delete any claim without a receipt'],
]

export function SearchRow({ call }) {
  return (
    <li className="rise flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 text-sm">
      <EngineChip engine={call.engine} />
      <span className="min-w-0 flex-1 truncate text-ink-2" title={call.query}>{call.query}</span>
      <span className="text-xs text-ink-3">{call.results} results</span>
      <span className={`w-16 text-right font-mono text-[11px] ${call.cached ? 'text-ink-3' : 'text-accent'}`}>
        {call.cached ? 'cached' : `${call.ms} ms`}
      </span>
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
  const notes = events.filter((e) => e.type === 'note')
  const live = searches.filter((s) => !s.cached).length

  return (
    <div className="mx-auto max-w-5xl px-5 pb-20 pt-10">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
            {replay ? 'Replaying a recorded scan' : 'Live scan'}
          </p>
          <h1 className="font-display text-3xl font-bold text-ink">{plan?.company || company}</h1>
          {plan && <p className="mt-1 max-w-2xl text-sm text-ink-2">{plan.description}</p>}
        </div>
        <Button onClick={onCancel}>Cancel</Button>
      </div>

      {error && (
        <div role="alert" className="mb-6 rounded-xl border border-bad/50 bg-bad/10 p-4 text-sm text-ink">
          <p className="font-medium">The scan stopped.</p>
          <p className="mt-1 text-ink-2">{error}</p>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-[250px_1fr]">
        <ol className="space-y-1">
          {STAGES.map(([key, label, blurb], i) => {
            const state = i < reached ? 'done' : i === reached && !error ? 'active' : 'todo'
            return (
              <li key={key} className={`rounded-lg px-3 py-2 ${state === 'active' ? 'bg-surface' : ''}`}>
                <div className="flex items-center gap-2.5">
                  <span className={`h-2 w-2 rounded-full ${state === 'done' ? 'bg-good' : state === 'active' ? 'blink bg-accent' : 'bg-line'}`} />
                  <span className={`text-sm font-medium ${state === 'todo' ? 'text-ink-3' : 'text-ink'}`}>{label}</span>
                  {state === 'done' && <span className="text-xs text-ink-3">done</span>}
                </div>
                {state === 'active' && <p className="mt-1 pl-[18px] text-xs text-ink-3">{blurb}</p>}
              </li>
            )
          })}
        </ol>

        <div className="space-y-4">
          {plan?.rivals?.length > 0 && (
            <div className="rise rounded-xl border border-line bg-surface p-4">
              <p className="text-xs text-ink-3">Rivals, from what people type after "{company} vs"</p>
              <p className="mt-1 text-sm text-ink">{plan.rivals.join(' · ')}</p>
            </div>
          )}

          <div className="rounded-xl border border-line bg-surface p-4">
            <div className="flex items-baseline justify-between">
              <p className="text-sm font-medium text-ink">SerpApi searches</p>
              <p className="font-mono text-[11px] text-ink-3">{searches.length} run · {live} live · {searches.length - live} cached</p>
            </div>
            <ul className="mt-2 divide-y divide-line/60">
              {searches.map((s, i) => <SearchRow key={i} call={s} />)}
              {searches.length === 0 && <li className="py-2 text-sm text-ink-3">Waiting for the first search…</li>}
            </ul>
          </div>

          {critique && (
            <div className="rise rounded-xl border border-line bg-surface p-4">
              <p className="text-sm font-medium text-ink">The critic found gaps</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-2">
                {critique.gaps.map((g, i) => <li key={i}>{g}</li>)}
              </ul>
              {critique.follow_ups.length > 0 && (
                <div className="mt-3 space-y-2">
                  {critique.follow_ups.map((f, i) => (
                    <p key={i} className="text-sm text-ink-3">
                      <span className="mr-2 rounded bg-raised px-1.5 py-0.5 font-mono text-[11px] text-accent">{SIGNALS[f.kind]?.label || f.kind}</span>
                      {f.reason}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}

          {notes.map((n, i) => <p key={i} className="text-xs text-ink-3">{n.text}</p>)}

          {grounding && (
            <div className="rise rounded-xl border border-line bg-surface p-4 text-sm text-ink-2">
              Checked {grounding.claims_checked} claims against their receipts: {grounding.claims_dropped} dropped,
              {' '}{grounding.citations_removed} bad citations removed, {grounding.confidence_capped} confidence scores capped.
            </div>
          )}

          {stage === 'analyse' && !error && (
            <p className="blink text-sm text-ink-3">The analyst is reading the evidence. This is the slow step, usually 20 to 40 seconds.</p>
          )}
        </div>
      </div>
    </div>
  )
}
