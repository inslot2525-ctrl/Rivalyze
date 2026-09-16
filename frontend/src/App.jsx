import React, { useState, useEffect, useRef } from 'react'

const API = 'http://localhost:8000'

function SentimentBadge({ sentiment, reason }) {
  const cfg = {
    positive: { bg: 'bg-emerald-900/50', text: 'text-emerald-400', border: 'border-emerald-700', dot: 'bg-emerald-400', label: 'Positive' },
    negative: { bg: 'bg-red-900/50',     text: 'text-red-400',     border: 'border-red-700',     dot: 'bg-red-400',     label: 'Negative' },
    neutral:  { bg: 'bg-slate-800',      text: 'text-slate-300',   border: 'border-slate-600',   dot: 'bg-slate-400',   label: 'Neutral'  },
  }
  const c = cfg[sentiment] || cfg.neutral
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${c.bg} ${c.text} ${c.border}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot} pulse-dot`}></span>
      {c.label} — {reason}
    </div>
  )
}

function Card({ title, icon, children, className = '' }) {
  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-2xl p-5 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-lg">{icon}</span>
        <h3 className="brand-font font-semibold text-slate-200 text-sm tracking-wide uppercase">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function Skeleton({ h = 'h-4', w = 'w-full', className = '' }) {
  return <div className={`skeleton rounded-lg ${h} ${w} ${className}`}></div>
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-3">
        <Skeleton h="h-6" w="w-48" />
        <Skeleton h="h-4" />
        <Skeleton h="h-4" w="w-4/5" />
        <Skeleton h="h-8" w="w-64" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
            <Skeleton h="h-4" w="w-32" />
            <Skeleton h="h-3" />
            <Skeleton h="h-3" w="w-3/4" />
            <Skeleton h="h-3" w="w-2/3" />
          </div>
        ))}
      </div>
    </div>
  )
}

function Dashboard({ data, searchHistory, onExportPDF, onFollowup, onAddMonitor }) {
  const hiringColor = {
    growing:     'text-emerald-400',
    stable:      'text-yellow-400',
    contracting: 'text-red-400',
  }

  // Handle comparative view
  if (data.comparative_summary) {
    return <ComparativeDashboard data={data} onExportPDF={onExportPDF} />
  }

  return (
    <div className="space-y-6">
      {/* Summary Header with Actions */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl p-6">
        <div className="flex items-start justify-between flex-wrap gap-3 mb-3">
          <h2 className="brand-font text-2xl font-bold text-white">{data.company}</h2>
          <div className="flex items-center gap-2">
            <SentimentBadge sentiment={data.sentiment} reason={data.sentiment_reason} />
            <button onClick={onExportPDF} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors">📄 Export PDF</button>
            <button onClick={onAddMonitor} className="px-3 py-1.5 bg-brand-500 hover:bg-brand-600 border border-brand-500 rounded-lg text-sm text-white transition-colors">🔔 Monitor</button>
          </div>
        </div>
        <p className="text-slate-300 leading-relaxed mb-3">{data.summary}</p>
        <p className="text-slate-400 text-sm italic">{data.market_position}</p>
        {data.top_sources?.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {data.top_sources.map((s, i) => (
              <span key={i} className="text-xs bg-slate-800 border border-slate-700 text-slate-400 px-2 py-1 rounded-full">{s}</span>
            ))}
          </div>
        )}
      </div>

      {/* Follow-up Q&A Panel */}
      <FollowupPanel brief={data} searchHistory={searchHistory} onAsk={onFollowup} />

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

        {/* Finance */}
        <Card title="Market Data" icon="💰">
          {data.finance?.price ? (
            <div className="space-y-2">
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold brand-font text-white">{data.finance.price}</span>
                <span className={`text-sm mb-1 ${data.finance.change?.startsWith('-') ? 'text-red-400' : 'text-emerald-400'}`}>
                  {data.finance.change}
                </span>
              </div>
              {data.finance.stock_symbol && <p className="text-slate-500 text-xs">{data.finance.stock_symbol}</p>}
              {data.finance.market_cap && (
                <p className="text-slate-400 text-sm">Market Cap: <span className="text-white font-medium">{data.finance.market_cap}</span></p>
              )}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">No public market data found</p>
          )}
        </Card>

        {/* Hiring */}
        <Card title="Hiring Signal" icon="👷">
          <div className="space-y-3">
            <span className={`text-lg font-bold brand-font capitalize ${hiringColor[data.hiring?.signal] || 'text-slate-300'}`}>
              {data.hiring?.signal || 'Unknown'}
            </span>
            <p className="text-slate-400 text-sm">{data.hiring?.reason}</p>
            <div className="space-y-1">
              {data.hiring?.sample_roles?.map((role, i) => (
                <div key={i} className="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded-lg">{role}</div>
              ))}
            </div>
          </div>
        </Card>

        {/* Locations */}
        <Card title="Physical Presence" icon="🗺️">
          {data.locations?.length > 0 ? (
            <ul className="space-y-1">
              {data.locations.slice(0, 6).map((loc, i) => (
                <li key={i} className="text-slate-300 text-sm flex items-center gap-2">
                  <span className="text-slate-600">—</span>{loc}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">No location data found</p>
          )}
        </Card>

        {/* News */}
        <Card title="Recent Moves" icon="📰" className="md:col-span-2">
          {data.recent_moves?.length > 0 ? (
            <div className="space-y-3">
              {data.recent_moves.slice(0, 5).map((item, i) => (
                <div key={i} className="border-l-2 border-brand-500 pl-3">
                  <p className="text-slate-200 text-sm font-medium">{item.title}</p>
                  <p className="text-slate-500 text-xs mt-0.5">{item.source} · {item.snippet}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">No recent news found</p>
          )}
        </Card>

        {/* Pricing */}
        <Card title="Pricing Signals" icon="🛒">
          {data.pricing?.length > 0 ? (
            <div className="space-y-2">
              {data.pricing.slice(0, 5).map((item, i) => (
                <div key={i} className="flex justify-between items-center text-sm">
                  <span className="text-slate-300 truncate max-w-[60%]">{item.product}</span>
                  <span className="text-emerald-400 font-semibold brand-font">{item.price}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">No pricing data found</p>
          )}
        </Card>

        {/* Risks */}
        <Card title="Risks" icon="⚠️">
          {data.risks?.length > 0 ? (
            <ul className="space-y-2">
              {data.risks.map((r, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="text-red-500 mt-0.5 shrink-0">▸</span>
                  <span className="text-slate-300">{r}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">No risk signals detected</p>
          )}
        </Card>

        {/* Opportunities */}
        <Card title="Opportunities" icon="🚀">
          {data.opportunities?.length > 0 ? (
            <ul className="space-y-2">
              {data.opportunities.map((o, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="text-emerald-500 mt-0.5 shrink-0">▸</span>
                  <span className="text-slate-300">{o}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">No opportunity signals detected</p>
          )}
        </Card>

        {/* Videos */}
        <Card title="Video Presence" icon="🎥">
          {data.key_videos?.length > 0 ? (
            <div className="space-y-3">
              {data.key_videos.slice(0, 3).map((v, i) => (
                <div key={i}>
                  <a href={v.url} target="_blank" rel="noreferrer"
                    className="text-brand-500 hover:text-brand-400 text-sm font-medium line-clamp-2 block">
                    {v.title}
                  </a>
                  <p className="text-slate-500 text-xs mt-0.5">{v.channel}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">No video data found</p>
          )}
        </Card>

      </div>
    </div>
  )
}

function ComparativeDashboard({ data, onExportPDF }) {
  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl p-6">
        <div className="flex items-start justify-between flex-wrap gap-3 mb-3">
          <h2 className="brand-font text-2xl font-bold text-white">Comparative Analysis: {data.primary_company}</h2>
          <button onClick={onExportPDF} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors">📄 Export PDF</button>
        </div>
        <p className="text-slate-300 leading-relaxed mb-3">{data.comparative_summary}</p>
        <p className="text-slate-400 text-sm italic">Market Leader: {data.market_leader}</p>
        <div className="flex flex-wrap gap-2 mt-4">
          {data.competitors.map((c, i) => (
            <span key={i} className="text-xs bg-brand-900/50 border border-brand-700 text-brand-400 px-2 py-1 rounded-full">{c}</span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(data.individual_briefs || {}).map(([company, brief]) => (
          <Card key={company} title={company} icon="🏢" className="md:col-span-2 lg:col-span-1">
            <p className="text-slate-300 text-sm mb-3">{brief.summary}</p>
            <SentimentBadge sentiment={brief.sentiment} reason={brief.sentiment_reason} />
            <div className="mt-3 space-y-1">
              <p className="text-slate-400 text-xs">Market: {brief.market_position}</p>
              {brief.finance?.price && (
                <p className="text-slate-400 text-xs">Stock: {brief.finance.price} ({brief.finance.change})</p>
              )}
              <div className="flex gap-1 flex-wrap mt-2">
                {(brief.differentiators?.[company] || []).slice(0, 2).map((d, i) => (
                  <span key={i} className="text-xs bg-emerald-900/30 text-emerald-400 px-2 py-0.5 rounded">{d}</span>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card title="Shared Risks" icon="⚠️" className="md:col-span-2">
        <ul className="space-y-2">
          {data.shared_risks?.map((r, i) => (
            <li key={i} className="flex gap-2 text-sm"><span className="text-red-500">▸</span><span className="text-slate-300">{r}</span></li>
          ))}
        </ul>
      </Card>
      <Card title="Shared Opportunities" icon="🚀" className="md:col-span-2">
        <ul className="space-y-2">
          {data.shared_opportunities?.map((o, i) => (
            <li key={i} className="flex gap-2 text-sm"><span className="text-emerald-500">▸</span><span className="text-slate-300">{o}</span></li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

function FollowupPanel({ brief, searchHistory, onAsk }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestions] = useState([
    "Why is sentiment negative?",
    "What's their biggest risk right now?",
    "Who are their main competitors?",
    "What's driving their hiring signal?",
    "Any recent acquisitions?",
    "What's their pricing strategy?",
  ])

  const handleAsk = async (q) => {
    if (!q.trim() || loading) return
    setLoading(true)
    setQuestion(q)
    try {
      const res = await fetch(`${API}/followup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brief, question: q, search_history: searchHistory }),
      })
      const data = await res.json()
      setAnswer(data.answer || 'No answer available')
    } catch (e) {
      setAnswer('Error getting answer')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Ask Rivalyze" icon="💬" className="md:col-span-2 lg:col-span-3">
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => handleAsk(s)} disabled={loading}
              className="text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1 rounded-full transition-colors disabled:opacity-50">
              {s}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk(question)}
            placeholder="Ask a follow-up question..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 text-sm"
            disabled={loading}
          />
          <button onClick={() => handleAsk(question)} disabled={loading || !question.trim()}
            className="bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white px-4 py-2 rounded-xl font-medium text-sm transition-colors whitespace-nowrap">
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </div>
        {answer && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
            {answer}
          </div>
        )}
      </div>
    </Card>
  )
}

function MonitorPanel({ onRefresh }) {
  const [monitors, setMonitors] = useState([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [newCompany, setNewCompany] = useState('')

  useEffect(() => { fetchMonitors() }, [onRefresh])

  const fetchMonitors = async () => {
    try {
      const res = await fetch(`${API}/monitor`)
      setMonitors(await res.json())
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const addMonitor = async () => {
    if (!newCompany.trim()) return
    try {
      await fetch(`${API}/monitor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company: newCompany, frequency_hours: 24 }),
      })
      setNewCompany('')
      fetchMonitors()
      onRefresh()
    } catch (e) { alert('Failed to add monitor') }
  }

  const toggleMonitor = async (company, isActive) => {
    try {
      await fetch(`${API}/monitor/${company}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive }),
      })
      fetchMonitors()
    } catch (e) { alert('Failed to update') }
  }

  const removeMonitor = async (company) => {
    if (!confirm(`Stop monitoring ${company}?`)) return
    try {
      await fetch(`${API}/monitor/${company}`, { method: 'DELETE' })
      fetchMonitors()
    } catch (e) { alert('Failed to remove') }
  }

  return (
    <Card title="Monitored Companies" icon="🔔" className="md:col-span-2 lg:col-span-3">
      <div className="space-y-4">
        <div className="flex gap-2">
          <input
            value={newCompany}
            onChange={(e) => setNewCompany(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addMonitor()}
            placeholder="Add company to monitor..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 text-sm"
          />
          <button onClick={addMonitor} className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-xl font-medium text-sm transition-colors">Add</button>
        </div>

        {loading ? (
          <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} h="h-12" />)}</div>
        ) : monitors.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-4">No companies monitored. Add one above to get alerts on changes.</p>
        ) : (
          <div className="space-y-2">
            {monitors.map(m => (
              <div key={m.company} className="flex items-center justify-between p-3 bg-slate-800/50 border border-slate-700 rounded-xl">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-white">{m.company}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${m.is_active ? 'bg-emerald-900/30 text-emerald-400' : 'bg-slate-700 text-slate-400'}`}>
                    {m.is_active ? 'Active' : 'Paused'}
                  </span>
                  <span className="text-xs text-slate-500">Every {m.frequency_hours}h</span>
                  {m.last_run && <span className="text-xs text-slate-500">Last: {new Date(m.last_run).toLocaleDateString()}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggleMonitor(m.company, m.is_active)}
                    className="text-xs px-2 py-1 border rounded transition-colors"
                    style={m.is_active ? {borderColor: 'theme(colors.emerald.700)', color: 'theme(colors.emerald.400)'} : {borderColor: 'theme(colors.slate.600)', color: 'theme(colors.slate.400)'}}>
                    {m.is_active ? 'Pause' : 'Resume'}
                  </button>
                  <button onClick={() => removeMonitor(m.company)} className="text-xs px-2 py-1 text-red-400 hover:text-red-300 border border-red-700 rounded transition-colors">Remove</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

function AlertsPanel({ company }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!company) return
    fetch(`${API}/alerts/${company}`)
      .then(r => r.json())
      .then(setAlerts)
      .finally(() => setLoading(false))
  }, [company])

  if (!company) return null

  return (
    <Card title="Change Alerts" icon="🚨" className="md:col-span-2 lg:col-span-3">
      {loading ? (
        <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} h="h-10" />)}</div>
      ) : alerts.length === 0 ? (
        <p className="text-slate-500 text-sm">No alerts yet. Changes will appear here after monitoring runs.</p>
      ) : (
        <div className="space-y-2">
          {alerts.map((a, i) => (
            <div key={i} className="p-3 bg-slate-800/50 border border-slate-700 rounded-xl">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-white">{a.type}</p>
                  <p className="text-xs text-slate-400">{a.field}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  a.severity === 'high' ? 'bg-red-900/30 text-red-400' :
                  a.severity === 'medium' ? 'bg-yellow-900/30 text-yellow-400' :
                  'bg-slate-700 text-slate-400'
                }`}>{a.severity}</span>
              </div>
              <div className="flex gap-4 mt-2 text-sm">
                <span className="text-red-400">Was: {a.old}</span>
                <span className="text-emerald-400">Now: {a.new}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{new Date(a.created_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

export default function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState(null)
  const [searchHistory, setSearchHistory] = useState([])
  const [error, setError] = useState(null)
  const [loadingMsg, setMsg] = useState('')
  const [view, setView] = useState('single') // 'single' | 'comparative'
  const [monitorRefresh, setMonitorRefresh] = useState(0)

  const MESSAGES = [
    'Initializing agentic analysis...',
    'Scanning web sources...',
    'Pulling latest news...',
    'Checking market data...',
    'Analyzing job signals...',
    'Searching product listings...',
    'Mapping physical presence...',
    'Reviewing video presence...',
    'Synthesizing intelligence brief...',
  ]

  const analyze = async (comparative = false) => {
    if (!query.trim()) return
    setLoading(true)
    setData(null)
    setSearchHistory([])
    setError(null)

    let i = 0
    setMsg(MESSAGES[0])
    const timer = setInterval(() => {
      i = (i + 1) % MESSAGES.length
      setMsg(MESSAGES[i])
    }, 2000)

    try {
      const res = await fetch(`${API}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company: query, comparative }),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const result = await res.json()
      setData(result)
      setSearchHistory(result._search_history || [])
    } catch (e) {
      setError(e.message)
    } finally {
      clearInterval(timer)
      setLoading(false)
    }
  }

  const handleFollowup = async (question) => {
    // Handled by FollowupPanel
  }

  const handleExportPDF = async () => {
    if (!data) return
    try {
      const res = await fetch(`${API}/export/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${data.company || 'rivalyze'}_brief.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) { alert('Export failed') }
  }

  const handleAddMonitor = async () => {
    if (!data) return
    try {
      await fetch(`${API}/monitor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company: data.company, frequency_hours: 24 }),
      })
      setMonitorRefresh(r => r + 1)
      alert(`Now monitoring ${data.company}. You'll get alerts on significant changes.`)
    } catch (e) { alert('Failed to start monitoring') }
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚡</span>
            <span className="brand-font font-bold text-xl text-white tracking-tight">Rivalyze</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-500 text-xs hidden md:block">
              Agentic Intelligence · SerpApi + Groq Llama 3
            </span>
            <div className="flex gap-1 border border-slate-700 rounded-lg p-1 bg-slate-900">
              <button onClick={() => { setView('single'); analyze(false) }} disabled={loading}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${view === 'single' ? 'bg-brand-500 text-white' : 'text-slate-400 hover:text-white'}`}>
                Single
              </button>
              <button onClick={() => { setView('comparative'); analyze(true) }} disabled={loading}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${view === 'comparative' ? 'bg-brand-500 text-white' : 'text-slate-400 hover:text-white'}`}>
                Comparative
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">

        {!data && !loading && (
          <div className="text-center mb-12">
            <h1 className="brand-font text-4xl md:text-5xl font-bold text-white mb-4 leading-tight">
              Know your competition<br />
              <span className="text-brand-500">before your morning coffee.</span>
            </h1>
            <p className="text-slate-400 text-lg max-w-xl mx-auto">
              Type a company name. Get a full intelligence brief — news, financials,
              hiring signals, pricing, and risk analysis — in seconds.
            </p>
          </div>
        )}

        <div className="flex gap-3 mb-8 max-w-2xl mx-auto">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && analyze(view === 'comparative')}
            placeholder="e.g. Tesla, OpenAI, Notion..."
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-5 py-3.5 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm"
            disabled={loading}
          />
          <button
            onClick={() => analyze(view === 'comparative')}
            disabled={loading || !query.trim()}
            className="bg-brand-500 hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3.5 rounded-xl font-semibold text-sm transition-colors brand-font whitespace-nowrap"
          >
            {loading ? 'Analyzing...' : view === 'comparative' ? 'Compare →' : 'Analyze →'}
          </button>
        </div>

        {!data && !loading && (
          <div className="flex flex-wrap justify-center gap-2 mb-12">
            {['Tesla', 'OpenAI', 'Notion', 'Nvidia', 'Peloton'].map(c => (
              <button key={c} onClick={() => setQuery(c)}
                className="text-sm text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded-full transition-colors">
                {c}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="mb-8">
            <div className="flex items-center justify-center gap-3 mb-6">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-2 h-2 bg-brand-500 rounded-full pulse-dot"
                    style={{ animationDelay: `${i * 0.2}s` }}></div>
                ))}
              </div>
              <span className="text-slate-400 text-sm">{loadingMsg}</span>
            </div>
            <DashboardSkeleton />
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-700 rounded-xl p-4 text-red-400 text-sm mb-6">
            ⚠ {error} — Make sure the backend is running on port 8000.
          </div>
        )}

        {data && !loading && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <p className="text-slate-500 text-sm">
                Intelligence brief for <span className="text-white font-medium">{data.primary_company || data.company}</span>
                {view === 'comparative' && data.competitors && (
                  <> vs <span className="text-brand-400">{data.competitors.join(', ')}</span></>
                )}
              </p>
              <button onClick={() => { setData(null); setQuery(''); setSearchHistory([]) }}
                className="text-slate-500 hover:text-white text-sm border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded-lg transition-colors">
                ← New search
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <Dashboard
                  data={data}
                  searchHistory={searchHistory}
                  onExportPDF={handleExportPDF}
                  onFollowup={handleFollowup}
                  onAddMonitor={handleAddMonitor}
                />
                <AlertsPanel company={data.primary_company || data.company} />
              </div>
              <div className="space-y-6">
                <MonitorPanel onRefresh={monitorRefresh} />
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  )
}