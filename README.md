# Rivalyze ⚡
### Know your competition before your morning coffee.

Rivalyze is an AI-powered competitive intelligence agent that turns a company name into a structured market brief — in seconds. It runs 8 parallel searches across the web, news, finance, jobs, shopping, maps, images, and video, then synthesizes everything into a clean, actionable dashboard.

No manual research. No tab juggling. Just intelligence.

---

## What it does

Type a company name. Get back:

- 📰 **Recent moves** — latest news, press, and announcements
- 💰 **Market signals** — stock price, financials, market cap
- 🛒 **Pricing landscape** — product listings and price benchmarks
- 👷 **Hiring pulse** — open roles as a proxy for growth or contraction
- 🗺️ **Physical footprint** — office locations and local presence
- 🎥 **Brand presence** — top YouTube content and video signals
- 🖼️ **Visual identity** — image search signals from across the web
- ⚠️ **Risks & opportunities** — AI-synthesized from all of the above

---

## How it works

```
You type: "OpenAI"
             │
             ▼
    Rivalyze Orchestrator (Claude)
             │
    ┌────────┼────────┐──────────┬──────────┬──────────┬──────────┐
    ▼        ▼        ▼          ▼          ▼          ▼          ▼
  Web     News    Shopping    Finance     Jobs      Maps      Videos
 Agent   Agent    Agent       Agent      Agent     Agent      Agent
    └────────┴────────┘──────────┴──────────┴──────────┴──────────┘
             │
             ▼
    Claude synthesizes all results
             │
             ▼
    Structured intelligence dashboard
```

8 parallel search agents. One coherent brief.

---

## Tech stack

| Layer | Technology |
|---|---|
| AI Orchestration | Claude (`claude-sonnet-4-6`) via Anthropic API |
| Search Intelligence | SerpApi — 8 engines via `serpapi-search-tools` |
| Backend | FastAPI (Python) |
| Frontend | React + Tailwind CSS |

---

## SerpApi engines used

| Engine | Signal |
|---|---|
| `web_search` | General company overview and background |
| `news_search` | Recent announcements and media coverage |
| `shopping_search` | Product pricing and marketplace presence |
| `videos_search` | YouTube brand and content signals |
| `maps_search` | Physical office presence and local reviews |
| `images_search` | Visual brand signals across the web |
| `google_jobs` | Hiring volume as growth/contraction indicator |
| `google_finance` | Stock price, market cap, and financials |

---

## Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+
- SerpApi account → [get your key](https://serpapi.com/manage-api-key)
- Anthropic account → [get your key](https://console.anthropic.com)

### Install

```bash
git clone https://github.com/yourhandle/rivalyze
cd rivalyze

# Backend
pip install fastapi uvicorn anthropic "serpapi-search-tools"

# Frontend
cd frontend && npm install
```

### Configure

```bash
export SERPAPI_API_KEY="your-serpapi-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Run

```bash
# Terminal 1 — backend
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5173` and search for any company.

---

## Project structure

```
rivalyze/
├── main.py              # FastAPI app + Claude agent loop
├── agents/
│   ├── orchestrator.py  # Claude tool-use orchestration
│   └── tools.py         # SerpApi tool registrations
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── SearchBar.jsx
│   │   │   ├── SummaryCard.jsx
│   │   │   ├── NewsPanel.jsx
│   │   │   ├── FinancePanel.jsx
│   │   │   ├── JobsPanel.jsx
│   │   │   ├── PricingPanel.jsx
│   │   │   ├── RiskOpportunity.jsx
│   │   │   └── VideosPanel.jsx
│   │   └── main.jsx
│   └── package.json
└── README.md
```

---

## Demo companies

Try these for a strong demo — each produces a visually distinct brief:

| Company | Why it's a good demo |
|---|---|
| `Tesla` | High news volume, rich finance data, polarized sentiment |
| `OpenAI` | Rapid recent moves, strong job signals, competitive landscape |
| `Peloton` | Declining hiring, risk signals, recovery opportunity story |
| `Nvidia` | Finance data shines, acquisition signals, supply chain news |

---

## License

MIT
