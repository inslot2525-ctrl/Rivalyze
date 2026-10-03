import React, { useEffect, useState } from 'react'
import { API, getJSON, remove, sendJSON } from '../api'
import AskPanel from './AskPanel'
import { HiringMix, SignalNumbers, TrendChart } from './Charts'
import { SearchRow } from './ScanTrace'
import { Button, Card, Cited, Eyebrow, ReceiptLink, Section, signalLabel } from './ui'

const VERDICT = {
  consistent: { label: 'Consistent', cls: 'bg-good/10 text-good' },
  tension: { label: 'Tension', cls: 'bg-warn/10 text-warn' },
  contradiction: { label: 'Contradiction', cls: 'bg-bad/10 text-bad' },
}

function Forecast({ f, evidence, onOpen }) {
  return (
    <article className="grid gap-x-8 gap-y-5 py-8 first:pt-0 last:pb-0 md:grid-cols-[96px_1fr_280px]">
      <div title="Capped by how many independent signals agree">
        <p className="font-display text-5xl leading-none text-accent">{f.confidence}<span className="text-2xl">%</span></p>
        <p className="mt-1.5 text-xs text-ink-3">confidence</p>
      </div>
      <div>
        <h3 className="font-display text-[28px] leading-tight text-ink">{f.prediction}</h3>
        <p className="mt-3 leading-relaxed text-ink-2"><Cited text={f.rationale} evidence={evidence} onOpen={onOpen} /></p>
        <p className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-3">
          <span>Within {f.horizon}</span>
          <span>{f.signals.map(signalLabel).join(' + ')}</span>
          <ReceiptLink ids={f.evidence_ids} onOpen={onOpen} />
        </p>
      </div>
      <div className="self-start rounded-xl bg-accent-soft p-5">
        <Eyebrow className="!text-accent">Your move</Eyebrow>
        <p className="mt-2 text-sm leading-relaxed text-ink">{f.counter_move}</p>
      </div>
    </article>
  )
}

function SayDo({ s, evidence, onOpen }) {
  const v = VERDICT[s.verdict] || VERDICT.tension
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-display text-2xl text-ink">{s.topic}</h3>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${v.cls}`}>{v.label}</span>
      </div>
      <div className="mt-5 grid gap-6 md:grid-cols-2 md:gap-0">
        <div className="md:pr-8">
          <Eyebrow>They say</Eyebrow>
          <p className="mt-2 leading-relaxed text-ink-2"><Cited text={s.says} evidence={evidence} onOpen={onOpen} /></p>
          <ReceiptLink ids={s.says_evidence} onOpen={onOpen} className="mt-3" />
        </div>
        <div className="md:border-l md:border-line md:pl-8">
          <Eyebrow>They do</Eyebrow>
          <p className="mt-2 leading-relaxed text-ink"><Cited text={s.does} evidence={evidence} onOpen={onOpen} /></p>
          <ReceiptLink ids={s.does_evidence} onOpen={onOpen} className="mt-3" />
        </div>
      </div>
      <p className="mt-6 border-t border-line pt-5 font-display text-xl leading-snug text-ink">{s.insight}</p>
    </Card>
  )
}

function Tell({ t, evidence, onOpen }) {
  return (
    <article className="border-t border-line pt-5">
      <Eyebrow>{signalLabel(t.signal)} · {t.strength}</Eyebrow>
      <h3 className="mt-2 font-display text-2xl leading-tight text-ink">{t.headline}</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink-2"><Cited text={t.detail} evidence={evidence} onOpen={onOpen} /></p>
      <ReceiptLink ids={t.evidence_ids} onOpen={onOpen} className="mt-3" />
    </article>
  )
}

function WatchButton({ company, disabled }) {
  const [watched, setWatched] = useState(null)
  useEffect(() => {
    getJSON('/monitor').then((list) => setWatched(list.some((m) => m.company === company))).catch(() => setWatched(false))
  }, [company])
  const toggle = async () => {
    try {
      if (watched) await remove(`/monitor/${encodeURIComponent(company)}`)
      else await sendJSON('/monitor', { company, frequency_hours: 24 })
      setWatched(!watched)
    } catch { /* leave the button as it was */ }
  }
  if (disabled) return null
  return (
    <Button onClick={toggle} disabled={watched === null}
      title={watched ? 'Stop the daily rescan' : 'Rescan daily and list what changed'}>
      {watched ? 'Watching ✓' : 'Watch daily'}
    </Button>
  )
}

export default function Report({ report, onOpen, onNew }) {
  const a = report.analysis
  const { usage, grounding, metrics, evidence } = report
  const [tab, setTab] = useState(new URLSearchParams(window.location.search).get('tab') || 'brief')
  const kept = grounding.claims_checked - grounding.claims_dropped
  const tabs = [
    ['brief', 'Next moves'],
    ['signals', 'Signals'],
    ...(a.rivals.length ? [['rivals', 'Rivals']] : []),
    ['ask', 'Ask'],
    ['sources', 'Sources'],
  ]
  const pick = (key) => { setTab(key); document.getElementById('tabs')?.scrollIntoView({ block: 'start' }) }

  return (
    <div className="mx-auto max-w-5xl px-6 pb-28">
      <header className="rise pt-14">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Eyebrow>
            {report.replay ? 'Recorded scan' : 'Scan'} · {new Date(report.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}
          </Eyebrow>
          <div className="flex flex-wrap gap-2">
            <a href={`${API}/scans/${encodeURIComponent(report.id)}/battlecard.md`} download
              className="rounded-full border border-line bg-surface px-4 py-2 text-sm font-medium text-ink-2 transition hover:border-ink-3 hover:text-ink">
              Export battlecard
            </a>
            <WatchButton company={report.company} disabled={report.replay} />
            <Button variant="primary" onClick={onNew}>New scan</Button>
          </div>
        </div>

        <h1 className="mt-8 font-display text-7xl leading-none text-ink">{report.company}</h1>
        <p className="mt-6 max-w-4xl font-display text-[34px] leading-[1.15] text-ink">{a.one_liner}</p>
        <p className="mt-6 max-w-3xl text-lg leading-relaxed text-ink-2"><Cited text={a.summary} evidence={evidence} onOpen={onOpen} /></p>

        <p className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-ink-3">
          <span><strong className="font-semibold text-ink">{usage.evidence_items}</strong> receipts from {usage.engines.length} SerpApi engines</span>
          <span><strong className="font-semibold text-ink">{kept} of {grounding.claims_checked}</strong> claims verified</span>
          <span><strong className="font-semibold text-ink">{usage.calls.length}</strong> searches</span>
          <button onClick={() => onOpen(null)} className="font-medium text-accent underline-offset-4 hover:underline">Browse the receipts →</button>
        </p>

        {report.changes?.length > 0 && (
          <div className="mt-8 rounded-2xl bg-accent-soft p-6">
            <Eyebrow className="!text-accent">{report.changes.length} changes since {new Date(report.previous_scan_at).toLocaleDateString()}</Eyebrow>
            <ul className="mt-3 space-y-1.5 text-sm text-ink">
              {report.changes.slice(0, 6).map((c, i) => (
                <li key={i}><span className="text-ink-3">{c.kind}:</span> {c.title}</li>
              ))}
            </ul>
          </div>
        )}
      </header>

      <nav id="tabs" aria-label="Report sections" className="sticky top-[57px] z-10 -mx-6 mt-12 scroll-mt-[57px] border-b border-line bg-bg/90 px-6 backdrop-blur">
        <div className="flex gap-7 overflow-x-auto">
          {tabs.map(([key, label]) => (
            <button key={key} onClick={() => pick(key)} aria-current={tab === key ? 'page' : undefined}
              className={`-mb-px whitespace-nowrap border-b-2 py-3.5 text-sm font-medium transition ${tab === key ? 'border-ink text-ink' : 'border-transparent text-ink-3 hover:text-ink'}`}>
              {label}
            </button>
          ))}
        </div>
      </nav>

      <div className="mt-12 space-y-20" key={tab}>
        {tab === 'brief' && (
          <>
            <Section title="What they will do next"
              hint="Confidence is capped by corroboration: one signal tops out at 55%, two at 75%, three or more at 90%.">
              <div className="divide-y divide-line">
                {a.forecasts.map((f, i) => <Forecast key={i} f={f} evidence={evidence} onOpen={onOpen} />)}
              </div>
            </Section>
            {a.say_vs_do.length > 0 && (
              <Section title="The story against the signals"
                hint="What the coverage claims, next to what hiring, patents, ads and demand show.">
                <div className="space-y-5">
                  {a.say_vs_do.map((s, i) => <SayDo key={i} s={s} evidence={evidence} onOpen={onOpen} />)}
                </div>
              </Section>
            )}
          </>
        )}

        {tab === 'signals' && (
          <>
            <Section title="What the signals show">
              <div className="grid gap-x-12 gap-y-9 md:grid-cols-2">
                {a.tells.map((t, i) => <Tell key={i} t={t} evidence={evidence} onOpen={onOpen} />)}
              </div>
            </Section>
            <Section title="The signals, measured" hint="Computed in code from the search results, not estimated by the model.">
              <div className="space-y-5">
                <SignalNumbers metrics={metrics} />
                <div className="grid items-start gap-5 lg:grid-cols-2">
                  <TrendChart trends={metrics.trends} />
                  <HiringMix hiring={metrics.hiring} compare={metrics.compare} company={report.query} />
                </div>
              </div>
            </Section>
          </>
        )}

        {tab === 'rivals' && (
          <Section title="Against its rivals"
            hint={`Chosen from what people type after “${report.query} vs” in Google: ${report.rival_candidates.slice(0, 6).join(', ')}.`}>
            <div className="grid gap-5 md:grid-cols-2">
              {a.rivals.map((r) => (
                <Card key={r.name}>
                  <h3 className="font-display text-3xl text-ink">{r.name}</h3>
                  <p className="mt-3 leading-relaxed text-ink-2"><Cited text={r.edge} evidence={evidence} onOpen={onOpen} /></p>
                  <ReceiptLink ids={r.evidence_ids} onOpen={onOpen} className="mt-4" />
                </Card>
              ))}
            </div>
            <div className="mt-5"><TrendChart trends={metrics.trends} /></div>
          </Section>
        )}

        {tab === 'ask' && (
          <Section title="Question the scan">
            <AskPanel report={report} onOpen={onOpen} />
          </Section>
        )}

        {tab === 'sources' && (
          <>
            <Section title="How this report was made"
              hint={`Every search the agents ran, in order. ${usage.live_searches} were live and ${usage.cache_hits} came from cache. The scan took ${usage.duration_s} seconds and ${usage.llm_calls} model calls.`}>
              <ul className="divide-y divide-line border-y border-line">
                {usage.calls.map((c, i) => <SearchRow key={i} call={c} />)}
              </ul>
              <div className="mt-6"><Button onClick={() => onOpen(null)}>Browse all {usage.evidence_items} receipts</Button></div>
            </Section>
            {a.open_questions.length > 0 && (
              <Section title="What the evidence could not settle">
                <ul className="max-w-3xl space-y-3">
                  {a.open_questions.map((q, i) => <li key={i} className="border-l-2 border-line pl-4 leading-relaxed text-ink-2">{q}</li>)}
                </ul>
              </Section>
            )}
          </>
        )}
      </div>
    </div>
  )
}
