import os
import json
import concurrent.futures
import google.generativeai as genai
from dotenv import load_dotenv
from agents.tools import TOOL_MAP

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.5-flash-lite"

BRIEF_SCHEMA = """{
  "company": "string — official company name",
  "summary": "string — 2-3 sentence executive brief",
  "sentiment": "positive | neutral | negative",
  "sentiment_reason": "string — one sentence explaining sentiment",
  "market_position": "string — one sentence on competitive standing",
  "recent_moves": [{"title": "string", "source": "string", "snippet": "string"}],
  "pricing": [{"product": "string", "price": "string", "source": "string"}],
  "finance": {"stock_symbol": "string|null", "price": "string|null", "change": "string|null", "market_cap": "string|null"},
  "hiring": {"signal": "growing|stable|contracting", "reason": "string", "sample_roles": ["string"]},
  "locations": ["string — city, country"],
  "key_videos": [{"title": "string", "channel": "string", "url": "string"}],
  "top_sources": ["domain.com"],
  "risks": ["string"],
  "opportunities": ["string"]
}"""

SYSTEM_PROMPT = f"""You are Rivalyze, an elite competitive intelligence analyst.
Synthesize all search data into this EXACT JSON structure:
{BRIEF_SCHEMA}
Return ONLY valid JSON — no markdown, no explanation, nothing else."""


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)
    return text.strip()


def compute_rivalry_score(brief: dict) -> dict:
    """
    Rule-based scoring — no LLM call needed.
    Each dimension 0-20, total 0-100.
    """
    scores = {}

    # Hiring velocity (0-20)
    hiring = brief.get("hiring", {})
    signal = hiring.get("signal", "stable")
    roles = len(hiring.get("sample_roles", []))
    if roles:
        scores["hiring_velocity"] = min({"growing": 20, "stable": 12, "contracting": 4}.get(signal, 10) * min(roles / 3, 1), 20)
    else:
        scores["hiring_velocity"] = {"growing": 15, "stable": 10, "contracting": 3}.get(signal, 8)

    # News momentum (0-20)
    moves = brief.get("recent_moves", [])
    scores["news_momentum"] = min(len(moves) * 4, 20)

    # Pricing aggression (0-20)
    pricing = brief.get("pricing", [])
    scores["pricing_aggression"] = min(len(pricing) * 5, 20)

    # Brand reach (0-20)
    videos = brief.get("key_videos", [])
    scores["brand_reach"] = min(len(videos) * 7, 20)

    # Web authority (0-20)
    sources = brief.get("top_sources", [])
    scores["web_authority"] = min(len(sources) * 4, 20)

    scores["total"] = sum(scores.values())
    return scores


def run_agent(company: str) -> dict:
    """Run 8 SerpApi searches in parallel, then synthesize with Gemini."""
    
    # All 8 engines now active - each maps to a rivalry axis
    ACTIVE_TOOLS = [
        "web_search",       # → web_authority
        "news_search",      # → news_momentum
        "finance_search",   # → finance data
        "jobs_search",      # → hiring_velocity
        "shopping_search",  # → pricing_aggression
        "videos_search",    # → brand_reach
        "maps_search",      # → locations
        "images_search",    # → visual signals
    ]

    search_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(TOOL_MAP[name], company): name for name in ACTIVE_TOOLS}
        for future in concurrent.futures.as_completed(futures, timeout=35):
            tool_name = futures[future]
            try:
                search_results[tool_name] = future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                search_results[tool_name] = json.dumps({"error": "Search timeout (30s)"})
            except Exception as e:
                search_results[tool_name] = json.dumps({"error": str(e)})

    user_message = f"Analyze this company: {company}\n\nSearch data collected:\n\n"
    for tool_name, result in search_results.items():
        user_message += f"=== {tool_name.upper()} ===\n{result}\n\n"
    user_message += "\nNow synthesize all of the above into the required JSON structure."

    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(
        [SYSTEM_PROMPT, user_message],
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=2048)
    )
    raw = _clean_json(response.text or "")
    brief = json.loads(raw)
    brief["rivalry_score"] = compute_rivalry_score(brief)
    return brief


async def discover_competitors(company: str) -> list:
    result = TOOL_MAP["competitor_search"](company)
    prompt = f"""From this search data, identify the top 3-5 direct competitors for {company}.
Return ONLY a JSON array of competitor names: ["Competitor1", "Competitor2", ...]"""
    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=512)
    )
    raw = _clean_json(response.text or "")
    try:
        competitors = json.loads(raw)
        return competitors[:5] if isinstance(competitors, list) else []
    except:
        return []


async def run_comparative(company: str) -> dict:
    competitors = await discover_competitors(company)
    all_companies = [company] + competitors

    # Run all analyses in parallel
    briefs = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(run_agent, c): c for c in all_companies}
        for future in concurrent.futures.as_completed(futures):
            c = futures[future]
            try:
                briefs[c] = future.result()
            except Exception as e:
                briefs[c] = {"company": c, "error": str(e)}

    # Generate rivalry verdict
    verdict = generate_verdict(briefs)

    comp_prompt = f"""You are Rivalyze. Create a COMPARATIVE intelligence brief for {company} vs its competitors.
Input: individual briefs for each company.
Output JSON with this structure:
{{
  "primary_company": "{company}",
  "competitors": {json.dumps(competitors)},
  "comparative_summary": "string — 2-3 sentences comparing market positions",
  "market_leader": "string — which company leads and why",
  "verdict": {json.dumps(verdict)},
  "differentiators": {{"company": ["unique strength"]}},
  "shared_risks": ["string"],
  "shared_opportunities": ["string"],
  "individual_briefs": {json.dumps({k: v for k, v in briefs.items()})}
}}
Return ONLY valid JSON."""

    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(
        comp_prompt,
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=3072)
    )
    raw = _clean_json(response.text or "")
    result = json.loads(raw)
    result["verdict"] = verdict
    return result


def generate_verdict(briefs: dict) -> str:
    """Single Gemini call for analyst verdict."""
    valid_briefs = {k: v for k, v in briefs.items() if "error" not in v}
    if not valid_briefs:
        return "Insufficient data for verdict."

    scores = {b["company"]: b.get("rivalry_score", {}).get("total", 0) for b in valid_briefs.values()}
    winner = max(scores, key=scores.get)
    winner_brief = valid_briefs[winner]

    prompt = f"""
Rivalry scores: {scores}
Winner: {winner} ({scores[winner]}/100)

Winner details:
- Hiring: {winner_brief.get('hiring', {}).get('signal', 'N/A')} — {winner_brief.get('hiring', {}).get('reason', 'N/A')}
- Recent moves: {len(winner_brief.get('recent_moves', []))} items
- Sentiment: {winner_brief.get('sentiment', 'N/A')}

All companies: {list(valid_briefs.keys())}

Write a 2-sentence analyst verdict: who is winning competitively RIGHT NOW and the single most important reason why.
Be specific. Name the winner. State the evidence from the data above.
"""

    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=512)
    )
    return response.text.strip()


async def answer_followup(brief: dict, question: str, search_history: list) -> str:
    context = f"Intelligence Brief:\n{json.dumps(brief, indent=2)}\n\nSearch History:\n"
    for entry in search_history[-5:]:
        context += f"=== {entry['tool'].upper()} ===\n{entry['result']}\n\n"
    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(
        f"You are Rivalyze. Answer the user's question using ONLY the provided intelligence brief and search data. Be concise, cite sources. If info not available, say so.\n\nContext:\n{context}\n\nQuestion: {question}",
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=1024)
    )
    return response.text.strip()


def generate_pdf(brief: dict) -> bytes:
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(79, 110, 247)
            self.cell(0, 10, "Rivalyze Intelligence Brief", ln=True, align="C")
            self.set_font("Helvetica", "", 10)
            self.set_text_color(100)
            self.cell(0, 6, f"Company: {brief.get('company', 'Unknown')}", ln=True, align="C")
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(128)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

        def section_title(self, title):
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(79, 110, 247)
            self.cell(0, 8, title, ln=True)
            self.set_draw_color(79, 110, 247)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)

        def body_text(self, text):
            self.set_font("Helvetica", "", 10)
            self.set_text_color(30)
            self.multi_cell(0, 5, text)
            self.ln(2)

        def bullet(self, text):
            self.set_font("Helvetica", "", 10)
            self.set_text_color(30)
            self.cell(8, 5, chr(8226))
            self.multi_cell(0, 5, text)
            self.ln(1)

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.section_title("Executive Summary")
    pdf.body_text(brief.get("summary", "N/A"))
    pdf.body_text(f"Market Position: {brief.get('market_position', 'N/A')}")

    # Rivalry Score in PDF
    rs = brief.get("rivalry_score", {})
    if rs:
        pdf.section_title("Rivalry Score")
        pdf.body_text(f"Total: {rs.get('total', 0)}/100")
        for axis in ["hiring_velocity", "news_momentum", "pricing_aggression", "brand_reach", "web_authority"]:
            pdf.body_text(f"  {axis.replace('_', ' ').title()}: {rs.get(axis, 0)}/20")

    pdf.section_title("Sentiment Analysis")
    sentiment = brief.get("sentiment", "neutral")
    pdf.body_text(f"Overall: {sentiment.capitalize()} — {brief.get('sentiment_reason', 'N/A')}")

    pdf.section_title("Recent Moves")
    for move in brief.get("recent_moves", [])[:5]:
        pdf.bullet(f"{move.get('title', '')} — {move.get('source', '')}: {move.get('snippet', '')}")

    pdf.section_title("Pricing Signals")
    for item in brief.get("pricing", [])[:5]:
        pdf.bullet(f"{item.get('product', '')}: {item.get('price', '')} ({item.get('source', '')})")

    pdf.section_title("Market Data")
    fin = brief.get("finance", {})
    if fin.get("price"):
        pdf.body_text(f"Stock: {fin.get('stock_symbol', 'N/A')} — {fin.get('price', '')} ({fin.get('change', '')})")
        pdf.body_text(f"Market Cap: {fin.get('market_cap', 'N/A')}")
    else:
        pdf.body_text("No public market data available.")

    pdf.section_title("Hiring Signal")
    hiring = brief.get("hiring", {})
    pdf.body_text(f"Signal: {hiring.get('signal', 'Unknown').capitalize()} — {hiring.get('reason', 'N/A')}")
    for role in hiring.get("sample_roles", [])[:3]:
        pdf.bullet(role)

    pdf.section_title("Physical Presence")
    for loc in brief.get("locations", [])[:6]:
        pdf.bullet(loc)

    pdf.section_title("Video Presence")
    for vid in brief.get("key_videos", [])[:3]:
        pdf.bullet(f"{vid.get('title', '')} — {vid.get('channel', '')} ({vid.get('url', '')})")

    pdf.section_title("Risks")
    for r in brief.get("risks", []):
        pdf.bullet(r)

    pdf.section_title("Opportunities")
    for o in brief.get("opportunities", []):
        pdf.bullet(o)

    pdf.section_title("Top Sources")
    pdf.body_text(", ".join(brief.get("top_sources", [])))

    return pdf.output(dest="S").encode("latin-1")