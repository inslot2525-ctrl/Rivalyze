export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options) {
  const res = await fetch(`${API}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return res.json()
}

export const getJSON = (path) => request(path)

export const sendJSON = (path, body, method = 'POST') =>
  request(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const remove = (path) => request(path, { method: 'DELETE' })

// Opens a scan or demo stream. Returns a function that stops it.
export function openStream(path, onEvent, onError) {
  const source = new EventSource(`${API}${path}`)
  let finished = false
  source.onmessage = (message) => {
    const event = JSON.parse(message.data)
    if (event.type === 'report' || event.type === 'error') {
      finished = true
      source.close()
    }
    onEvent(event)
  }
  source.onerror = () => {
    if (finished) return
    source.close()
    onError('Lost the connection to the Rivalyze API. Is the backend running on ' + API + '?')
  }
  return () => { finished = true; source.close() }
}

export const SIGNALS = {
  hiring: { label: 'Hiring', engine: 'google_jobs', blurb: 'what they recruit for' },
  rnd: { label: 'R&D', engine: 'google_patents', blurb: 'what they patent' },
  ads: { label: 'Ad spend', engine: 'google_ads_transparency_center', blurb: 'what they pay to say' },
  demand: { label: 'Demand', engine: 'google_trends', blurb: 'how search interest moves' },
  doubts: { label: 'Doubts', engine: 'google', blurb: 'what people ask about them' },
  ai_view: { label: 'AI view', engine: 'google_ai_mode', blurb: 'how AI answers describe them' },
  market: { label: 'Market', engine: 'google_finance', blurb: 'what the numbers say' },
  narrative: { label: 'Narrative', engine: 'google_news', blurb: 'what the press reports' },
  web: { label: 'Web', engine: 'google', blurb: 'what the web says' },
  rivals: { label: 'Rivals', engine: 'google_autocomplete', blurb: 'who people compare them to' },
}

export const SERIES = ['var(--color-series-1)', 'var(--color-series-2)', 'var(--color-series-3)',
  'var(--color-series-4)', 'var(--color-series-5)']
