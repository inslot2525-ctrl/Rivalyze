import React from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { SERIES } from '../api'
import { Card, Stat } from './ui'

const AXIS = { fill: 'var(--color-ink-3)', fontSize: 11 }

function TrendTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-line bg-surface px-3.5 py-2.5 text-xs shadow-lg">
      <p className="mb-1.5 text-ink-3">{label}</p>
      {[...payload].sort((a, b) => b.value - a.value).map((p) => (
        <p key={p.dataKey} className="flex items-center gap-2 py-0.5 text-ink">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="flex-1 pr-4">{p.dataKey}</span>
          <span className="font-mono">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

export function TrendChart({ trends }) {
  if (!trends?.series?.length) return null
  // Colour follows the entity: the target is always series 1, rivals keep their slot.
  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-2xl text-ink">Search demand</h3>
        <a href={trends.link} target="_blank" rel="noreferrer" className="text-xs text-ink-3 underline-offset-4 hover:text-accent hover:underline">
          Open in Google Trends ↗
        </a>
      </div>
      <p className="mt-1 text-sm text-ink-3">Last 12 months on Google's 0–100 interest index, one shared scale.</p>
      <div className="mt-5 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trends.series} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="var(--color-line)" vertical={false} />
            <XAxis dataKey="date" tick={AXIS} tickLine={false} axisLine={{ stroke: 'var(--color-line)' }}
              interval={12} tickFormatter={(d) => d.split(/[\s,–]/)[0] + ' ' + d.slice(-4)} />
            <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={AXIS} tickLine={false} axisLine={false} />
            <Tooltip content={<TrendTooltip />} cursor={{ stroke: 'var(--color-ink-3)', strokeDasharray: '3 3' }} />
            <Legend iconType="plainline" itemSorter={null} wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              formatter={(value) => <span style={{ color: 'var(--color-ink-2)' }}>{value}</span>} />
            {trends.terms.map((term, i) => (
              <Line key={term} type="monotone" dataKey={term} stroke={SERIES[i]} strokeWidth={i === 0 ? 2.5 : 2}
                dot={false} activeDot={{ r: 4, stroke: 'var(--color-surface)', strokeWidth: 2 }} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <table className="mt-5 w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink-3">
            <th className="pb-2 font-normal">Term</th>
            <th className="pb-2 text-right font-normal">12-month average</th>
            <th className="pb-2 text-right font-normal">Last 4 weeks</th>
            <th className="pb-2 text-right font-normal">Change</th>
          </tr>
        </thead>
        <tbody>
          {trends.stats.map((s) => (
            <tr key={s.term} className="border-t border-line">
              <td className="py-2 text-ink">
                <span className="mr-2.5 inline-block h-[3px] w-3.5 rounded-full align-middle" style={{ background: SERIES[trends.terms.indexOf(s.term)] }} />
                {s.term}
              </td>
              <td className="text-right font-mono text-xs text-ink-2">{s.average}</td>
              <td className="text-right font-mono text-xs text-ink-2">{s.recent_average}</td>
              <td className="text-right font-mono text-xs text-ink">
                {s.change_pct == null ? '—' : `${s.change_pct > 0 ? '▲' : s.change_pct < 0 ? '▼' : ''} ${Math.abs(s.change_pct)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

function Bars({ rows, total }) {
  const max = Math.max(...rows.map((r) => r.count), 1)
  return (
    <ul className="space-y-2.5">
      {rows.map((r) => (
        <li key={r.name} className="grid grid-cols-[150px_1fr_24px] items-center gap-3 text-sm" title={`${r.name}: ${r.count} of ${total} postings`}>
          <span className="truncate text-ink-2">{r.name}</span>
          <span className="h-2 rounded-full bg-series-1" style={{ width: `${Math.max((r.count / max) * 100, 3)}%` }} />
          <span className="text-right font-mono text-xs text-ink">{r.count}</span>
        </li>
      ))}
    </ul>
  )
}

export function HiringMix({ hiring, compare, company }) {
  if (!hiring?.sample_size) return null
  const rivals = (compare || []).filter((c) => c.name !== company && c.hiring_sample)
  return (
    <Card>
      <h3 className="font-display text-2xl text-ink">Hiring mix</h3>
      <p className="mb-6 mt-1 text-sm text-ink-3">
        A sample of {hiring.sample_size} live postings from Google Jobs, not a headcount. {hiring.posted_last_7_days} posted
        this week, {Math.round(hiring.remote_share * 100)}% remote.
      </p>
      <Bars rows={hiring.by_function} total={hiring.sample_size} />
      {rivals.map((r) => (
        <div key={r.name} className="mt-7 border-t border-line pt-5">
          <p className="mb-3 text-sm font-medium text-ink">{r.name} <span className="font-normal text-ink-3">· {r.hiring_sample} postings sampled</span></p>
          <Bars rows={r.by_function.slice(0, 4)} total={r.hiring_sample} />
        </div>
      ))}
    </Card>
  )
}

export function SignalNumbers({ metrics }) {
  const { patents, ads, market } = metrics
  const blocks = []
  if (market?.price) {
    blocks.push(['Market', [
      <Stat key="p" label={market.ticker} value={market.price.replace('USD', '$')} note={`${market.change_pct > 0 ? '▲' : '▼'} ${Math.abs(market.change_pct)}% today`} />,
      <Stat key="c" label="Market cap" value={market.market_cap || '—'} />,
      ...(market.financials || []).filter((f) => /^(Revenue|Research)/.test(f.title)).slice(0, 2).map((f) => (
        <Stat key={f.title} label={f.title.replace(' expenses', '')} value={f.value} note={`${f.change} year on year`} />
      )),
    ]])
  }
  if (patents) {
    blocks.push(['Patents', [
      <Stat key="t" label="Matching filings" value={patents.total_matching} />,
      <Stat key="f" label="Filed in the last year" value={patents.filed_last_12_months} note={`of the newest ${patents.newest_shown}`} />,
      <Stat key="l" label="Latest filing" value={patents.latest_filing?.slice(0, 7) || '—'} />,
    ]])
  }
  if (ads) {
    blocks.push(['Ad spend', [
      <Stat key="o" label="Own ad creatives" value={ads.own_creatives} note={ads.by_format.map((f) => `${f.count} ${f.name}`).join(', ')} />,
      <Stat key="n" label="Launched in 30 days" value={ads.launched_last_30_days} />,
    ]])
  }
  if (!blocks.length) return null
  return (
    <Card>
      <div className="grid gap-x-10 gap-y-8 md:grid-cols-3">
        {blocks.map(([title, stats]) => (
          <div key={title}>
            <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-3">{title}</p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-5">{stats}</div>
          </div>
        ))}
      </div>
    </Card>
  )
}
