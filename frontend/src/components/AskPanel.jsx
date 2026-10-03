import React, { useState } from 'react'
import { sendJSON } from '../api'
import { Button, Card, Cited, EngineChip } from './ui'

const LINK = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g

// Answers mix receipt citations with markdown links to live search results.
function Answer({ text, evidence, onOpen }) {
  const parts = []
  let last = 0
  for (const m of text.matchAll(LINK)) {
    parts.push(<Cited key={`t${m.index}`} text={text.slice(last, m.index)} evidence={evidence} onOpen={onOpen} />)
    parts.push(<a key={`a${m.index}`} href={m[2]} target="_blank" rel="noreferrer" className="underline decoration-accent underline-offset-2">{m[1]}</a>)
    last = m.index + m[0].length
  }
  parts.push(<Cited key="end" text={text.slice(last)} evidence={evidence} onOpen={onOpen} />)
  return <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{parts}</p>
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
    'Has anything about pricing changed recently?',
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
    <Card>
      <div className="space-y-5">
        {turns.map((t, i) => (
          <div key={i} className="rise">
            <p className="mb-1.5 text-sm font-medium text-ink-2">{t.question}</p>
            <Answer text={t.answer} evidence={report.evidence} onOpen={onOpen} />
            {t.searches.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-3">
                <span>Searched live:</span>
                {t.searches.map((s, j) => (
                  <span key={j} className="inline-flex items-center gap-1.5">
                    <EngineChip engine={s.engine} /> {s.query}
                    <span className="text-accent">{s.via === 'serpapi-mcp' ? 'via SerpApi MCP' : s.via === 'serpapi-direct' ? 'via SerpApi' : ''}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <p className="blink text-sm text-ink-3">Reading the receipts…</p>}
        {error && <p role="alert" className="text-sm text-bad">{error}</p>}
      </div>

      {turns.length === 0 && !busy && (
        <div className="mb-3 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button key={s} onClick={() => submit(s)}
              className="rounded-full border border-line px-3 py-1.5 text-xs text-ink-2 hover:border-ink-3 hover:text-ink">{s}</button>
          ))}
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); submit(question) }} className={`flex gap-2 ${turns.length || busy ? 'mt-5' : ''}`}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500} disabled={busy}
          placeholder="Ask about this scan" aria-label="Ask a follow-up question"
          className="flex-1 rounded-lg border border-line bg-bg px-3.5 py-2 text-sm text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none" />
        <Button type="submit" variant="primary" disabled={busy || !question.trim()}>Ask</Button>
      </form>
      <p className="mt-2 text-xs text-ink-3">
        Answers come from this scan's receipts. If they fall short, the agent may run up to two live searches through the SerpApi MCP server.
      </p>
    </Card>
  )
}
