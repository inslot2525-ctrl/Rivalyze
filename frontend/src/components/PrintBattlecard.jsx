import React, { useEffect, useMemo } from 'react'
import { API } from '../api'
import { signalLabel } from './ui'

const CITATION = /\s*\[([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)\]/g
const ORDINAL = ['1st', '2nd', '3rd', '4th', '5th']

// On paper a citation cannot be clicked, so it becomes a superscript that points at the receipts list.
function Text({ children, evidence }) {
  if (!children) return null
  const parts = []
  let last = 0
  for (const m of children.matchAll(CITATION)) {
    parts.push(children.slice(last, m.index))
    const ids = m[1].split(',').map((s) => s.trim()).filter((id) => evidence[id])
    if (ids.length) parts.push(<sup key={m.index} className="font-mono text-[8px] text-accent">{ids.join(',')}</sup>)
    last = m.index + m[0].length
  }
  parts.push(children.slice(last))
  return <>{parts}</>
}

function Heading({ children }) {
  return <h2 className="mb-3 mt-9 border-b border-ink pb-1.5 font-display text-2xl text-ink">{children}</h2>
}

function collectIds(report) {
  const a = report.analysis
  const ids = []
  const add = (list) => (list || []).forEach((i) => { if (report.evidence[i] && !ids.includes(i)) ids.push(i) })
  const scan = (text) => { for (const m of (text || '').matchAll(CITATION)) add(m[1].split(',').map((s) => s.trim())) }
  scan(a.summary)
  a.forecasts.forEach((f) => { add(f.evidence_ids); scan(f.rationale) })
  a.say_vs_do.forEach((s) => { add(s.says_evidence); add(s.does_evidence); scan(s.says); scan(s.does) })
  ;[...(a.standing?.ahead || []), ...(a.standing?.behind || [])].forEach((p) => add(p.evidence_ids))
  a.tells.forEach((t) => { add(t.evidence_ids); scan(t.detail) })
  a.rivals.forEach((r) => { add(r.evidence_ids); scan(r.edge) })
  return ids
}

export default function PrintBattlecard({ report, onBack }) {
  const a = report.analysis
  const { evidence, metrics, usage, grounding } = report
  const card = metrics.scorecard
  const names = (metrics.compare || []).map((c) => c.name)
    .filter((n) => card?.rows?.some((r) => r.values.some((v) => v.name === n)))
  const receipts = useMemo(() => collectIds(report), [report])
  const date = new Date(report.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })

  useEffect(() => {
    const previous = document.title
    document.title = `${report.company} battlecard`  // becomes the suggested PDF file name
    return () => { document.title = previous }
  }, [report.company])

  return (
    <div className="bg-raised py-8 print:bg-white print:py-0">
      <div className="mx-auto mb-6 flex max-w-[820px] flex-wrap items-center justify-between gap-3 px-6 print:hidden">
        <button onClick={onBack} className="text-sm font-medium text-ink-2 hover:text-ink">← Back to the report</button>
        <div className="flex items-center gap-4">
          <a href={`${API}/scans/${encodeURIComponent(report.id)}/battlecard.md`} download
            className="text-sm text-ink-3 underline-offset-4 hover:text-ink hover:underline">Download as Markdown</a>
          <button onClick={() => window.print()}
            className="rounded-full bg-ink px-6 py-2.5 text-sm font-medium text-white transition hover:bg-accent">
            Download PDF
          </button>
        </div>
      </div>
      <p className="mx-auto mb-4 max-w-[820px] px-6 text-xs text-ink-3 print:hidden">
        “Download PDF” opens your browser's print dialog. Choose “Save as PDF” as the destination.
      </p>

      <article className="mx-auto max-w-[820px] bg-white px-14 py-12 text-[13px] leading-relaxed text-ink shadow-lg print:max-w-none print:px-0 print:py-0 print:shadow-none">
        <header>
          <p className="flex justify-between text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-3">
            <span>Competitive battlecard</span><span>{date}</span>
          </p>
          <h1 className="mt-3 font-display text-6xl leading-none text-ink">{report.company}</h1>
          <p className="mt-1 text-ink-3">{report.plan.description}</p>
          <p className="mt-5 font-display text-[26px] leading-tight text-ink">{a.one_liner}</p>
          <p className="mt-3 text-ink-2"><Text evidence={evidence}>{a.summary}</Text></p>
        </header>

        {a.forecasts.length > 0 && (
          <section>
            <Heading>What they will do next</Heading>
            {a.forecasts.map((f, i) => (
              <div key={i} className="mb-4 grid break-inside-avoid grid-cols-[64px_1fr] gap-4">
                <div>
                  <p className="font-display text-3xl leading-none text-accent">{f.confidence}%</p>
                  <p className="mt-1 text-[10px] text-ink-3">{f.horizon}</p>
                </div>
                <div>
                  <p className="font-display text-xl leading-tight text-ink">{f.prediction}</p>
                  <p className="mt-1 text-ink-2"><Text evidence={evidence}>{f.rationale}</Text></p>
                  <p className="mt-2 border-l-2 border-accent bg-accent-soft px-3 py-2 text-ink">
                    <strong className="font-semibold">Your move: </strong>{f.counter_move}
                  </p>
                </div>
              </div>
            ))}
          </section>
        )}

        {card?.rows?.length > 0 && (
          <section className="break-inside-avoid">
            <Heading>Where {report.company} stands</Heading>
            {a.standing?.verdict && <p className="mb-3 text-ink-2"><Text evidence={evidence}>{a.standing.verdict}</Text></p>}
            <table className="w-full border-collapse text-[12px]">
              <thead>
                <tr className="border-b border-ink text-left">
                  <th className="py-1.5 pr-2 font-semibold">Measure</th>
                  {names.map((n) => <th key={n} className="px-2 py-1.5 text-right font-semibold">{n}</th>)}
                  <th className="py-1.5 pl-2 text-right font-semibold">Rank</th>
                </tr>
              </thead>
              <tbody>
                {card.rows.map((row) => {
                  const by = Object.fromEntries(row.values.map((v) => [v.name, v.value]))
                  return (
                    <tr key={row.key} className="border-b border-line">
                      <td className="py-1.5 pr-2">{row.label}</td>
                      {names.map((n) => (
                        <td key={n} className={`px-2 py-1.5 text-right ${n === row.leader ? 'font-bold' : ''}`}>
                          {by[n] === undefined ? '—' : `${by[n].toLocaleString()}${row.unit}`}
                        </td>
                      ))}
                      <td className="py-1.5 pl-2 text-right">{ORDINAL[row.target_rank - 1]} of {row.of}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
            <p className="mt-1.5 text-[10px] text-ink-3">The leader on each measure is in bold. A dash means the scan had no comparable data.</p>
          </section>
        )}

        {a.say_vs_do.length > 0 && (
          <section>
            <Heading>What they say against what they do</Heading>
            {a.say_vs_do.map((s, i) => (
              <div key={i} className="mb-4 break-inside-avoid">
                <p className="font-semibold text-ink">{s.topic} <span className="font-normal text-ink-3">· {s.verdict}</span></p>
                <div className="mt-1 grid grid-cols-2 gap-5">
                  <p className="text-ink-2"><strong className="font-semibold text-ink">Says. </strong><Text evidence={evidence}>{s.says}</Text></p>
                  <p className="text-ink-2"><strong className="font-semibold text-ink">Does. </strong><Text evidence={evidence}>{s.does}</Text></p>
                </div>
                <p className="mt-1 italic text-ink">{s.insight}</p>
              </div>
            ))}
          </section>
        )}

        <section>
          <Heading>What the signals show</Heading>
          {a.tells.map((t, i) => (
            <p key={i} className="mb-2.5 break-inside-avoid text-ink-2">
              <strong className="font-semibold text-ink">{t.headline}.</strong>{' '}
              <Text evidence={evidence}>{t.detail}</Text>{' '}
              <span className="text-[10px] uppercase tracking-wide text-ink-3">{signalLabel(t.signal)} · {t.strength}</span>
            </p>
          ))}
        </section>

        {a.rivals.length > 0 && (
          <section>
            <Heading>Rival by rival</Heading>
            {a.rivals.map((r) => (
              <p key={r.name} className="mb-2.5 break-inside-avoid text-ink-2">
                <strong className="font-semibold text-ink">{r.name}. </strong><Text evidence={evidence}>{r.edge}</Text>
              </p>
            ))}
          </section>
        )}

        <section>
          <Heading>Receipts</Heading>
          <p className="mb-2 text-[11px] text-ink-3">
            The search results cited above, out of {usage.evidence_items} collected from {usage.engines.length} SerpApi
            engines. {grounding.claims_checked - grounding.claims_dropped} of {grounding.claims_checked} claims kept their citations.
          </p>
          <ol className="space-y-1 text-[10.5px] leading-snug">
            {receipts.map((id) => {
              const e = evidence[id]
              return (
                <li key={id} className="grid break-inside-avoid grid-cols-[34px_1fr] gap-1">
                  <span className="font-mono text-accent">{id}</span>
                  <span className="text-ink-2">
                    {e.title}{e.date ? ` (${e.date})` : ''} <span className="text-ink-3">· {e.engine}</span>
                    {e.link && <a href={e.link} className="block truncate text-ink-3">{e.link}</a>}
                  </span>
                </li>
              )
            })}
          </ol>
        </section>

        <footer className="mt-8 border-t border-line pt-3 text-[10px] text-ink-3">
          Made with Rivalyze from live SerpApi search data. Forecasts are inferences from public signals; check the receipts.
        </footer>
      </article>
    </div>
  )
}
