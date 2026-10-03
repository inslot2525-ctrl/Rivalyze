import React, { useEffect, useState } from 'react'
import { API, SIGNALS, getJSON, remove, sendJSON } from '../api'
import AskPanel from './AskPanel'
import { HiringMix, SignalNumbers, TrendChart } from './Charts'
import { SearchRow } from './ScanTrace'
import { Button, Card, Cited, Receipts, Section, SignalTag } from './ui'

const VERDICT = {
  consistent: { label: 'Consistent', cls: 'border-good/50 text-good', mark: '=' },
  tension: { label: 'Tension', cls: 'border-warn/50 text-warn', mark: '≠' },
  contradiction: { label: 'Contradiction', cls: 'border-bad/50 text-bad', mark: '✕' },
}
const STRENGTH = { strong: 3, moderate: 2, weak: 1 }

function Forecast({ f, evidence, onOpen }) {
  return (
    <Card className="flex flex-col">
      <div className="mb-3 flex items-center gap-3">
        <div className="relative h-12 w-12 shrink-0" title={`Confidence ${f.confidence}%, capped by how many independent signals agree`}>
          <svg viewBox="0 0 36 36" className="h-12 w-12 -rotate-90">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--color-line)" strokeWidth="3" />
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--color-accent)" strokeWidth="3" strokeLinecap="round"
              strokeDasharray={`${(f.confidence / 100) * 97.4} 97.4`} />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center font-mono text-xs font-medium text-ink">{f.confidence}%</span>
        </div>
        <div className="min-w-0">
          <p className="text-xs text-ink-3">Expected in {f.horizon}</p>
          <p className="text-xs text-ink-3">
            {f.signals.length} {f.signals.length === 1 ? 'signal' : 'signals agree'}: {f.signals.map((s) => SIGNALS[s]?.label || s).join(' + ')}
          </p>
        </div>
      </div>
      <h3 className="font-display text-lg font-semibold leading-snug text-ink">{f.prediction}</h3>
      <p className="mt-2 flex-1 text-sm leading-relaxed text-ink-2"><Cited text={f.rationale} evidence={evidence} onOpen={onOpen} /></p>
      <div className="mt-4 rounded-lg border border-accent/30 bg-accent/5 p-3">
        <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.16em] text-accent">Your move</p>
        <p className="text-sm text-ink">{f.counter_move}</p>
      </div>
      <div className="mt-3"><Receipts ids={f.evidence_ids} onOpen={onOpen} /></div>
    </Card>
  )
}

function SayDo({ s, evidence, onOpen }) {
  const v = VERDICT[s.verdict] || VERDICT.tension
  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium text-ink">{s.topic}</h3>
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${v.cls}`}>{v.mark} {v.label}</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">Says</p>
          <p className="text-sm leading-relaxed text-ink-2"><Cited text={s.says} evidence={evidence} onOpen={onOpen} /></p>
          <div className="mt-2"><Receipts ids={s.says_evidence} onOpen={onOpen} /></div>
        </div>
        <div className="md:border-l md:border-line md:pl-4">
          <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">Does</p>
          <p className="text-sm leading-relaxed text-ink"><Cited text={s.does} evidence={evidence} onOpen={onOpen} /></p>
          <div className="mt-2"><Receipts ids={s.does_evidence} onOpen={onOpen} /></div>
        </div>
      </div>
      <p className="mt-4 border-t border-line pt-3 text-sm text-ink"><span className="text-ink-3">So: </span>{s.insight}</p>
    </Card>
  )
}

function Tell({ t, evidence, onOpen }) {
  return (
    <Card>
      <div className="mb-2 flex items-center justify-between gap-2">
        <SignalTag signal={t.signal} />
        <span className="flex items-center gap-1" title={`${t.strength} signal`}>
          {[1, 2, 3].map((n) => <span key={n} className={`h-1.5 w-4 rounded-full ${n <= STRENGTH[t.strength] ? 'bg-ink-2' : 'bg-line'}`} />)}
          <span className="ml-1 text-xs text-ink-3">{t.strength}</span>
        </span>
      </div>
      <h3 className="font-medium leading-snug text-ink">{t.headline}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-2"><Cited text={t.detail} evidence={evidence} onOpen={onOpen} /></p>
      <div className="mt-3"><Receipts ids={t.evidence_ids} onOpen={onOpen} /></div>
    </Card>
  )
}

function WatchButton({ company, disabled }) {
  const [watched, setWatched] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    getJSON('/monitor').then((list) => setWatched(list.some((m) => m.company === company))).catch(() => setWatched(false))
  }, [company])
  const toggle = async () => {
    setError(null)
    try {
      if (watched) await remove(`/monitor/${encodeURIComponent(company)}`)
      else await sendJSON('/monitor', { company, frequency_hours: 24 })
      setWatched(!watched)
    } catch (e) { setError(e.message) }
  }
  return (
    <Button onClick={toggle} disabled={disabled || watched === null}
      title={disabled ? 'Recorded scans cannot be watched' : watched ? 'Stop the daily rescan' : 'Rescan daily and list what changed'}>
      {error || (watched ? 'Watching daily ✓' : 'Watch daily')}
    </Button>
  )
}

export default function Report({ report, onOpen, onNew }) {
  const a = report.analysis
  const { usage, grounding, metrics, evidence } = report
  const [signal, setSignal] = useState('all')
  const tellSignals = [...new Set(a.tells.map((t) => t.signal))]
  const tells = signal === 'all' ? a.tells : a.tells.filter((t) => t.signal === signal)
  const kept = grounding.claims_checked - grounding.claims_dropped

  return (
    <div className="mx-auto max-w-6xl space-y-12 px-5 pb-24 pt-10">
      <header className="rise">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
              {report.replay ? `Recorded scan · ${report.created_at.slice(0, 10)}` : `Scanned ${new Date(report.created_at).toLocaleString()}`}
            </p>
            <h1 className="font-display text-4xl font-bold text-ink">{report.company}</h1>
            <p className="mt-1 max-w-2xl text-sm text-ink-3">{report.plan.description}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => onOpen(null)}>All {usage.evidence_items} receipts</Button>
            <a href={`${API}/scans/${encodeURIComponent(report.id)}/battlecard.md`} download
              className="rounded-lg border border-line bg-surface px-3.5 py-2 text-sm text-ink-2 transition hover:border-ink-3 hover:text-ink">
              Export battlecard
            </a>
            <WatchButton company={report.company} disabled={report.replay} />
            <Button variant="primary" onClick={onNew}>New scan</Button>
          </div>
        </div>

        <p className="mt-7 max-w-4xl font-display text-2xl font-medium leading-snug text-ink md:text-3xl">{a.one_liner}</p>
        <p className="mt-4 max-w-4xl leading-relaxed text-ink-2"><Cited text={a.summary} evidence={evidence} onOpen={onOpen} /></p>

        <dl className="mt-7 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-4">
          {[
            ['Receipts collected', usage.evidence_items, `from ${usage.engines.length} SerpApi engines`],
            ['Claims that survived', `${kept} of ${grounding.claims_checked}`, `${grounding.citations_removed} bad citations removed`],
            ['Searches', usage.calls.length, `${usage.live_searches} live · ${usage.cache_hits} from cache`],
            ['Time', `${usage.duration_s}s`, `${usage.llm_calls} model calls`],
          ].map(([label, value, note]) => (
            <div key={label} className="bg-surface px-4 py-3">
              <dt className="text-xs text-ink-3">{label}</dt>
              <dd className="font-display text-xl font-semibold text-ink">{value}</dd>
              <dd className="text-xs text-ink-3">{note}</dd>
            </div>
          ))}
        </dl>

        {report.changes?.length > 0 && (
          <div className="mt-5 rounded-xl border border-accent/40 bg-accent/5 p-4">
            <p className="text-sm font-medium text-ink">
              {report.changes.length} changes since the last scan on {report.previous_scan_at.slice(0, 10)}
            </p>
            <ul className="mt-2 space-y-1 text-sm text-ink-2">
              {report.changes.slice(0, 8).map((c, i) => (
                <li key={i}>
                  <span className="mr-2 text-xs text-accent">{c.kind}</span>{c.title}
                  {c.evidence_id && evidence[c.evidence_id] && <Receipts ids={[c.evidence_id]} onOpen={onOpen} />}
                </li>
              ))}
            </ul>
          </div>
        )}
      </header>

      {a.forecasts.length > 0 && (
        <Section eyebrow="Forecast" title="What they will do next"
          hint="Confidence is capped by corroboration: one signal tops out at 55%, two at 75%, three or more at 90%.">
          <div className="grid gap-4 md:grid-cols-2">
            {a.forecasts.map((f, i) => <Forecast key={i} f={f} evidence={evidence} onOpen={onOpen} />)}
          </div>
        </Section>
      )}

      {a.say_vs_do.length > 0 && (
        <Section eyebrow="Say vs do" title="The story against the signals"
          hint="The left side cites press and web results. The right side has to cite something the company does not script.">
          <div className="space-y-4">
            {a.say_vs_do.map((s, i) => <SayDo key={i} s={s} evidence={evidence} onOpen={onOpen} />)}
          </div>
        </Section>
      )}

      <Section eyebrow="Tells" title="What the signals show"
        action={(
          <div className="flex flex-wrap gap-1.5">
            {['all', ...tellSignals].map((s) => (
              <button key={s} onClick={() => setSignal(s)}
                className={`rounded-full border px-2.5 py-1 text-xs ${signal === s ? 'border-accent bg-accent/15 text-ink' : 'border-line text-ink-3 hover:text-ink'}`}>
                {s === 'all' ? 'All' : SIGNALS[s]?.label || s}
              </button>
            ))}
          </div>
        )}>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {tells.map((t, i) => <Tell key={i} t={t} evidence={evidence} onOpen={onOpen} />)}
        </div>
      </Section>

      <Section eyebrow="Numbers" title="The signals, measured" hint="Computed in code from the search results, not estimated by the model.">
        <div className="grid gap-4 lg:grid-cols-2">
          <TrendChart trends={metrics.trends} />
          <HiringMix hiring={metrics.hiring} compare={metrics.compare} company={report.query} />
        </div>
        <div className="mt-4"><SignalNumbers metrics={metrics} /></div>
      </Section>

      {a.rivals.length > 0 && (
        <Section eyebrow="Rivals" title="Against the companies people compare it to"
          hint={`Rivals come from Google autocomplete for "${report.query} vs": ${report.rival_candidates.slice(0, 6).join(', ')}.`}>
          <div className="grid gap-4 md:grid-cols-2">
            {a.rivals.map((r) => (
              <Card key={r.name}>
                <h3 className="font-display text-lg font-semibold text-ink">{r.name}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-2"><Cited text={r.edge} evidence={evidence} onOpen={onOpen} /></p>
                <div className="mt-3"><Receipts ids={r.evidence_ids} onOpen={onOpen} /></div>
              </Card>
            ))}
          </div>
        </Section>
      )}

      <Section eyebrow="Ask" title="Question the scan">
        <AskPanel report={report} onOpen={onOpen} />
      </Section>

      <Section eyebrow="Method" title="How this report was made"
        hint="Every search the agents ran, in order. Cached searches cost nothing.">
        <Card>
          <ul className="divide-y divide-line/60">
            {usage.calls.map((c, i) => <SearchRow key={i} call={c} />)}
          </ul>
          {a.open_questions.length > 0 && (
            <div className="mt-5 border-t border-line pt-4">
              <p className="mb-2 text-sm font-medium text-ink">What the evidence could not settle</p>
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink-2">
                {a.open_questions.map((q, i) => <li key={i}>{q}</li>)}
              </ul>
            </div>
          )}
        </Card>
      </Section>
    </div>
  )
}
