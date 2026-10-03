import React, { useState } from 'react'
import { sendJSON } from '../api'
import { Button, Cited } from './ui'

const LINK = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g

// Answers mix receipt citations with markdown links to live search results.
function Answer({ text, evidence, onOpen }) {
  const clean = text.replace(/\*\*|`/g, '')
  const parts = []
  let last = 0
  for (const m of clean.matchAll(LINK)) {
    parts.push(<Cited key={`t${m.index}`} text={clean.slice(last, m.index)} evidence={evidence} onOpen={onOpen} />)
    parts.push(<a key={`a${m.index}`} href={m[2]} target="_blank" rel="noreferrer" className="text-accent underline underline-offset-4">{m[1]} ↗</a>)
    last = m.index + m[0].length
  }
  parts.push(<Cited key="end" text={clean.slice(last)} evidence={evidence} onOpen={onOpen} />)
  return <p className="whitespace-pre-wrap leading-relaxed text-ink">{parts}</p>
}

export default function AskPanel({ report, onOpen }) {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const rival = report.rivals[0]
  const suggestions = [
    `What should I do this week to counter ${report.company}?`,
    'Which forecast has the weakest evidence?',
    rival ? `Where is ${rival} ahead of ${report.company}?` : 'What are customers most unsure about?',
  ]

  const submit = async (q) => {
    if (!q.trim() || busy) return
    setBusy(true)
    setError(null)
    setQuestion('')
    const history = turns.flatMap((t) => [{ role: 'user', text: t.question }, { role: 'assistant', text: t.answer }])
    try {
      const res = await sendJSON('/ask', { scan: report.id, question: q.trim(), history })
      setTurns((t) => [...t, { question: q.trim(), ...res }])
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <form onSubmit={(e) => { e.preventDefault(); submit(question) }}
        className="flex items-center gap-2 rounded-full border border-line bg-surface p-1.5 pl-6 focus-within:border-ink-3">
        <input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500} disabled={busy}
          placeholder={`Ask anything about ${report.company}`} aria-label="Ask a follow-up question"
          className="min-w-0 flex-1 bg-transparent py-2 text-ink placeholder:text-ink-3 focus:outline-none" />
        <Button type="submit" variant="primary" disabled={busy || !question.trim()}>Ask</Button>
      </form>

      {turns.length === 0 && !busy && (
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {suggestions.map((s) => (
            <button key={s} onClick={() => submit(s)}
              className="rounded-full bg-raised px-3.5 py-1.5 text-sm text-ink-2 transition hover:bg-accent-soft hover:text-ink">{s}</button>
          ))}
        </div>
      )}

      <div className="mt-10 space-y-10">
        {[...turns].reverse().map((t, i) => (
          <div key={turns.length - i} className="rise">
            <p className="font-display text-2xl text-ink">{t.question}</p>
            <div className="mt-3"><Answer text={t.answer} evidence={report.evidence} onOpen={onOpen} /></div>
            {t.searches.length > 0 && (
              <p className="mt-3 text-xs text-ink-3">
                Searched live{t.searches.some((s) => s.via === 'serpapi-mcp') ? ' through the SerpApi MCP server' : ' with SerpApi'}:
                {' '}{t.searches.map((s) => `“${s.query}”`).join(', ')}
              </p>
            )}
          </div>
        ))}
        {busy && <p className="blink text-ink-3">Reading the receipts…</p>}
        {error && <p role="alert" className="text-sm text-bad">{error}</p>}
      </div>

      <p className="mt-10 text-center text-xs text-ink-3">
        Answers come from this scan's receipts. When they fall short, the agent may run up to two live searches through the SerpApi MCP server.
      </p>
    </div>
  )
}
