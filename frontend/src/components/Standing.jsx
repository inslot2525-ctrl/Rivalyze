import React from 'react'
import { Card, Cited, Eyebrow, ReceiptLink } from './ui'

const ORDINAL = ['1st', '2nd', '3rd', '4th', '5th']

function format(row, value) {
  if (row.unit === '%') return `${value > 0 ? '+' : ''}${value}%`
  return value.toLocaleString()
}

// The target against its rivals on every measure the scan could compute for both.
export function Scorecard({ card, compare, target }) {
  if (!card?.rows?.length) return null
  const names = compare.map((c) => c.name).filter((n) => card.rows.some((r) => r.values.some((v) => v.name === n)))
  const focus = Object.fromEntries(compare.filter((c) => c.top_function).map((c) => [c.name, c.top_function]))
  const employer = Object.fromEntries(compare.filter((c) => c.employer && c.employer !== c.name).map((c) => [c.name, c.employer]))

  return (
    <Card className="overflow-x-auto !p-0">
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="border-b border-line text-left">
            <th className="px-6 py-4 font-normal text-ink-3">Measure</th>
            {names.map((n) => (
              <th key={n} className={`px-4 py-4 text-right align-bottom font-display text-xl font-normal ${n === target ? 'bg-accent-soft text-ink' : 'text-ink-2'}`}>
                {n}
                {employer[n] && <span className="block font-sans text-[11px] text-ink-3" title={`Hiring and patent figures are for ${employer[n]} as a whole`}>by {employer[n]}</span>}
              </th>
            ))}
            <th className="px-6 py-4 text-right font-normal text-ink-3">{target} ranks</th>
          </tr>
        </thead>
        <tbody>
          {card.rows.map((row) => {
            const by = Object.fromEntries(row.values.map((v) => [v.name, v.value]))
            return (
              <tr key={row.key} className="border-b border-line last:border-0">
                <th scope="row" className="px-6 py-4 text-left font-normal">
                  <span className="font-medium text-ink">{row.label}</span>
                  <span className="block text-xs text-ink-3">{row.note}</span>
                </th>
                {names.map((n) => (
                  <td key={n} className={`px-4 py-4 text-right ${n === target ? 'bg-accent-soft' : ''}`}>
                    {by[n] === undefined
                      ? <span className="text-ink-3" title="The scan had no data for this">—</span>
                      : (
                        <span className={n === row.leader ? 'font-semibold text-ink' : 'text-ink-2'}>
                          {format(row, by[n])}
                          {n === row.leader && <span className="ml-1.5 text-[10px] font-semibold uppercase tracking-wide text-accent">lead</span>}
                        </span>
                      )}
                  </td>
                ))}
                <td className="px-6 py-4 text-right text-ink-2">
                  <span className={row.target_rank === 1 ? 'font-semibold text-accent' : ''}>{ORDINAL[row.target_rank - 1]}</span>
                  <span className="text-ink-3"> of {row.of}</span>
                </td>
              </tr>
            )
          })}
          {Object.keys(focus).length > 1 && (
            <tr>
              <th scope="row" className="px-6 py-4 text-left font-normal">
                <span className="font-medium text-ink">Hiring focus</span>
                <span className="block text-xs text-ink-3">most common function in the sample</span>
              </th>
              {names.map((n) => (
                <td key={n} className={`px-4 py-4 text-right text-ink-2 ${n === target ? 'bg-accent-soft' : ''}`}>{focus[n] || <span className="text-ink-3">—</span>}</td>
              ))}
              <td />
            </tr>
          )}
        </tbody>
      </table>
      {Object.keys(employer).length > 0 && (
        <p className="border-t border-line px-6 py-3 text-xs text-ink-3">
          Hiring and patent figures are for the company behind a product ({Object.entries(employer).map(([n, e]) => `${e} for ${n}`).join(', ')}), so they cover more than that product.
        </p>
      )}
    </Card>
  )
}

function Points({ title, tone, points, evidence, onOpen, empty }) {
  return (
    <div>
      <Eyebrow className={tone}>{title}</Eyebrow>
      <ul className="mt-3 space-y-5">
        {points.map((p, i) => (
          <li key={i} className="border-t border-line pt-4">
            <p className="leading-relaxed text-ink"><Cited text={p.point} evidence={evidence} onOpen={onOpen} /></p>
            <ReceiptLink ids={p.evidence_ids} onOpen={onOpen} className="mt-2" />
          </li>
        ))}
        {points.length === 0 && <li className="border-t border-line pt-4 text-sm text-ink-3">{empty}</li>}
      </ul>
    </div>
  )
}

export default function Standing({ report, onOpen }) {
  const { analysis: a, metrics, evidence } = report
  const card = metrics.scorecard
  const standing = a.standing

  return (
    <div className="space-y-10">
      {standing?.verdict && (
        <div className="grid items-start gap-8 md:grid-cols-[1fr_auto]">
          <p className="max-w-3xl font-display text-[28px] leading-snug text-ink">{standing.verdict}</p>
          {card?.measures > 0 && (
            <div className="rounded-2xl bg-accent-soft px-7 py-5 text-center">
              <p className="font-display text-5xl leading-none text-accent">{card.leads}<span className="text-2xl"> of {card.measures}</span></p>
              <p className="mt-2 text-xs text-ink-2">measures where {report.company} leads</p>
            </div>
          )}
        </div>
      )}

      <Scorecard card={card} compare={metrics.compare || []} target={report.query} />

      {standing && (
        <div className="grid gap-10 md:grid-cols-2">
          <Points title={`Where ${report.company} is ahead`} tone="!text-good" points={standing.ahead}
            evidence={evidence} onOpen={onOpen} empty="The evidence showed no clear lead." />
          <Points title="Where a rival is ahead" tone="!text-bad" points={standing.behind}
            evidence={evidence} onOpen={onOpen} empty="The evidence showed no rival clearly ahead." />
        </div>
      )}
    </div>
  )
}
