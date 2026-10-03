import React from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { SERIES } from '../api'
import { Card, Stat } from './ui'

const AXIS = { fill: 'var(--color-ink-3)', fontSize: 11 }

function TrendTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-line bg-raised px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 text-ink-3">{label}</p>
      {[...payload].sort((a, b) => b.value - a.value).map((p) => (
        <p key={p.dataKey} className="flex items-center gap-2 text-ink">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="flex-1">{p.dataKey}</span>
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
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium text-ink">Search demand, last 12 months</h3>
        <a href={trends.link} target="_blank" rel="noreferrer" className="text-xs text-ink-3 underline hover:text-ink">
          Open in Google Trends
        </a>
      </div>
      <p className="mb-3 text-xs text-ink-3">Google's 0–100 interest index, all terms on one shared scale.</p>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trends.series} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="var(--color-line)" vertical={false} />
            <XAxis dataKey="date" tick={AXIS} tickLine={false} axisLine={{ stroke: 'var(--color-line)' }}
              interval={12} tickFormatter={(d) => d.split(/[\s,–]/)[0] + ' ' + d.slice(-4)} />
            <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={AXIS} tickLine={false} axisLine={false} />
            <Tooltip content={<TrendTooltip />} cursor={{ stroke: 'var(--color-ink-3)', strokeDasharray: '3 3' }} />
            <Legend iconType="plainline" itemSorter={null} wrapperStyle={{ fontSize: 12, color: 'var(--color-ink-2)' }}
              formatter={(value) => <span style={{ color: 'var(--color-ink-2)' }}>{value}</span>} />
            {trends.terms.map((term, i) => (
              <Line key={term} type="monotone" dataKey={term} stroke={SERIES[i]} strokeWidth={i === 0 ? 2.5 : 2}
                dot={false} activeDot={{ r: 4, stroke: 'var(--color-surface)', strokeWidth: 2 }} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <table className="mt-4 w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink-3">
            <th className="pb-1 font-normal">Term</th>
            <th className="pb-1 text-right font-normal">12-mo average</th>
            <th className="pb-1 text-right font-normal">Last 4 weeks</th>
            <th className="pb-1 text-right font-normal">Change</th>
          </tr>
        </thead>
        <tbody>
          {trends.stats.map((s, i) => (
            <tr key={s.term} className="border-t border-line/60">
              <td className="py-1.5 text-ink">
                <span className="mr-2 inline-block h-0.5 w-3 align-middle" style={{ background: SERIES[trends.terms.indexOf(s.term)] }} />
                {s.term}
              </td>
              <td className="text-right font-mono text-ink-2">{s.average}</td>
              <td className="text-right font-mono text-ink-2">{s.recent_average}</td>
              <td className="text-right font-mono text-ink">{s.change_pct > 0 ? '▲' : s.change_pct < 0 ? '▼' : ''} {Math.abs(s.change_pct)}%</td>
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
    <ul className="space-y-1.5">
      {rows.map((r) => (
        <li key={r.name} className="grid grid-cols-[130px_1fr_28px] items-center gap-2 text-sm" title={`${r.name}: ${r.count} of ${total} postings`}>
          <span className="truncate text-ink-2">{r.name}</span>
          <span className="h-2.5 rounded-r bg-series-1" style={{ width: `${(r.count / max) * 100}%` }} />
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
      <h3 className="font-medium text-ink">Hiring mix</h3>
      <p className="mb-4 text-xs text-ink-3">
        A sample of {hiring.sample_size} live postings from Google Jobs, not a headcount. {hiring.posted_last_7_days} posted
        in the last 7 days, {Math.round(hiring.remote_share * 100)}% remote.
      </p>
      <Bars rows={hiring.by_function} total={hiring.sample_size} />
      {hiring.by_location?.length > 0 && (
        <p className="mt-4 text-xs text-ink-3">
          Where: {hiring.by_location.map((l) => `${l.name} (${l.count})`).join(' · ')}
        </p>
      )}
      {rivals.map((r) => (
        <div key={r.name} className="mt-5 border-t border-line pt-4">
          <p className="mb-2 text-sm text-ink">{r.name} <span className="text-xs text-ink-3">· {r.hiring_sample} postings sampled, {r.posted_last_7_days} in the last 7 days</span></p>
          <Bars rows={r.by_function.slice(0, 4)} total={r.hiring_sample} />
        </div>
      ))}
    </Card>
  )
}

export function SignalNumbers({ metrics }) {
  const { news, patents, ads, market } = metrics
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {patents && (
        <Card>
          <h3 className="mb-3 font-medium text-ink">Patents</h3>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Matching filings" value={patents.total_matching} />
            <Stat label="Filed in last 12 mo" value={patents.filed_last_12_months} note={`of the newest ${patents.newest_shown}`} />
            <Stat label="Latest filing" value={patents.latest_filing?.slice(0, 7) || '—'} />
          </div>
          {patents.top_classes?.length > 0 && (
            <p className="mt-3 text-xs text-ink-3">Top classes: {patents.top_classes.slice(0, 4).map((c) => `${c.code} ${c.share}%`).join(' · ')}</p>
          )}
        </Card>
      )}
      {ads && (
        <Card>
          <h3 className="mb-3 font-medium text-ink">Ad spend</h3>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Own creatives" value={ads.own_creatives} />
            <Stat label="Launched in 30 days" value={ads.launched_last_30_days} />
            <Stat label="Other advertisers" value={ads.other_advertisers_on_domain} note="pointing at the domain" />
          </div>
          <p className="mt-3 text-xs text-ink-3">
            {ads.by_format.map((f) => `${f.count} ${f.name}`).join(' · ')}
            {ads.by_advertiser?.length > 0 && ` — bought by ${ads.by_advertiser.map((a) => a.name).join(', ')}`}
          </p>
        </Card>
      )}
      {news && news.last_30_days >= 5 && (
        <Card>
          <h3 className="mb-3 font-medium text-ink">News velocity</h3>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Last 7 days" value={news.last_7_days} />
            <Stat label="7 days before" value={news.previous_7_days} />
            <Stat label="Last 30 days" value={news.last_30_days} />
          </div>
          <p className="mt-3 text-xs text-ink-3">Most coverage from {news.top_sources.slice(0, 3).map((s) => s.name).join(', ')}</p>
        </Card>
      )}
      {market?.price && (
        <Card>
          <h3 className="mb-3 font-medium text-ink">Market</h3>
          <div className="grid grid-cols-3 gap-3">
            <Stat label={market.ticker} value={market.price} note={`${market.change_pct > 0 ? '▲' : '▼'} ${Math.abs(market.change_pct)}% today`} />
            <Stat label="Market cap" value={market.market_cap || '—'} />
            <Stat label="P/E" value={market.pe || '—'} />
          </div>
          {market.financials && (
            <p className="mt-3 text-xs text-ink-3">
              {market.financials.slice(0, 3).map((f) => `${f.title} ${f.value} (${f.change})`).join(' · ')}
            </p>
          )}
        </Card>
      )}
    </div>
  )
}
