# Demo video script (about 2 minutes 30)

Record at 1400 px wide. Start both servers first. Lines in quotes are what to say.

## 0:00 — The idea (landing page)

"Every competitor tells you a story in its press releases. Rivalyze ignores the story and reads what a company can't hide: what it hires for, what it patents, which ads it buys and what people search about it. All of that comes from SerpApi."

## 0:15 — Live trace (click the Duolingo recorded scan)

Let the replay run. Point at the search rows as they arrive.

"A scan runs in seven stages. It starts with Google autocomplete: whatever people type after 'Duolingo vs' is the rival list. Then jobs, news, trends, patents, the ads transparency centre and finance run in parallel. A critic agent reads the evidence and asks for more searches. You can see every SerpApi call, which engine it used and whether it was cached."

## 0:40 — The headline and the counters

"157 search results became evidence, across nine SerpApi engines. Sixteen claims were checked and all sixteen kept their citations."

## 0:50 — Forecasts

Read the cosmetic-economies forecast. Click receipt `J5`.

"The forecast is that Duolingo launches in-game cosmetics. Here is why: this is the actual job posting, a Gaming Partnerships Producer with cosmetic-economy experience. Every claim opens the search result behind it. Confidence is capped by how many independent signals agree, so a forecast resting on one signal can't go above 55 percent."

## 1:15 — Say vs do

"On the left, what the coverage says. On the right, what the signals show. This one is marked a contradiction."

## 1:30 — Numbers

Scroll to the trend chart and hiring mix.

"These numbers are computed in code from the search data. One Google Trends call puts the company and four rivals on the same scale."

## 1:45 — Ask

Type: "Has Duolingo announced any acquisition in the last month?"

"If the evidence can't answer, the agent searches live through the SerpApi MCP server and cites what it finds."

## 2:05 — Quota and replay

Point at the header counter, then the Method section.

"This was built on a free SerpApi plan, so searches are cached and budgeted. A first scan costs about twelve searches and a repeat costs almost none. The three recorded scans in the repo run with no API key."

## 2:20 — Close

Click Export battlecard, show the Markdown.

"It exports a battlecard, watches a company daily for changes, and runs as an MCP server inside Claude. That's Rivalyze."

## How this maps to the judging criteria

| Criterion | Where it shows |
|---|---|
| Idea strength | Opening line: involuntary signals vs the official story |
| Originality | Say vs do, autocomplete rival discovery, receipts with a grounding check |
| Technical complexity | Seven-stage pipeline, live trace, critic follow-ups, confidence caps, MCP both ways |
| Usefulness | Counter-moves, battlecard export, watchlist |
| Meaningful SerpApi usage | Nine engines, one signal each, every claim tied to a result |
