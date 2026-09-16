import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from groq import Groq
from dotenv import load_dotenv
from agents.tools import TOOL_MAP, TOOL_DEFINITIONS

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama3-70b-8192"

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


class AgenticOrchestrator:
    def __init__(self, company: str, context: Optional[Dict] = None):
        self.company = company
        self.context = context or {}
        self.search_history: List[Dict] = []
        self.brief: Optional[Dict] = None

    async def run_agentic_analysis(self) -> Dict:
        """Run iterative agentic loop: decide next search based on findings."""
        system_prompt = f"""You are Rivalyze, an elite competitive intelligence analyst.
Analyze {self.company} by iteratively calling search tools.
Decide each next search based on what you've learned so far.
After sufficient data, synthesize into this EXACT JSON:
{BRIEF_SCHEMA}
Return ONLY valid JSON when done."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Begin analysis of {self.company}. Start with the most important searches."}
        ]

        max_iterations = 10
        for iteration in range(max_iterations):
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=2048,
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)
                    fn = TOOL_MAP.get(fn_name)
                    if fn:
                        result = fn(**fn_args)
                        self.search_history.append({
                            "tool": fn_name,
                            "args": fn_args,
                            "result": result[:2000] if len(result) > 2000 else result
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result[:2000] if len(result) > 2000 else result
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: Unknown tool {fn_name}"
                        })
            else:
                # No tool calls - synthesis complete
                raw = (msg.content or "").strip()
                if raw.startswith("```"):
                    lines = raw.split("\n")
                    lines = [l for l in lines if not l.startswith("```")]
                    raw = "\n".join(lines)
                try:
                    self.brief = json.loads(raw)
                    self.brief["_search_history"] = self.search_history
                    return self.brief
                except json.JSONDecodeError:
                    # Force one more iteration to get valid JSON
                    messages.append({"role": "user", "content": "Return ONLY the JSON object. No explanation."})
                    continue

        # Fallback if max iterations reached
        return await self._fallback_synthesis()

    async def _fallback_synthesis(self) -> Dict:
        """Final synthesis attempt with all collected data."""
        user_msg = f"Synthesize all search data for {self.company} into the required JSON:\n\n"
        for entry in self.search_history:
            user_msg += f"=== {entry['tool'].upper()} ===\n{entry['result']}\n\n"

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"Output ONLY valid JSON matching this schema: {BRIEF_SCHEMA}"},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines)
        return json.loads(raw)


async def discover_competitors(company: str) -> List[str]:
    """Identify top 3-5 competitors for a company."""
    result = TOOL_MAP["competitor_search"](company)
    prompt = f"""From this search data, identify the top 3-5 direct competitors for {company}.
Return ONLY a JSON array of competitor names: ["Competitor1", "Competitor2", ...]"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Output ONLY a JSON array of competitor names."},
            {"role": "user", "content": f"Search data:\n{result}\n\n{prompt}"},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines)
    try:
        competitors = json.loads(raw)
        return competitors[:5] if isinstance(competitors, list) else []
    except:
        return []


async def run_comparative_analysis(company: str) -> Dict:
    """Run full analysis on company + competitors, produce comparative brief."""
    competitors = await discover_competitors(company)
    all_companies = [company] + competitors

    briefs = {}
    for c in all_companies:
        orchestrator = AgenticOrchestrator(c)
        briefs[c] = await orchestrator.run_agentic_analysis()

    # Generate comparative synthesis
    comp_prompt = f"""You are Rivalyze. Create a COMPARATIVE intelligence brief for {company} vs its competitors.
Input: individual briefs for each company.
Output JSON with this structure:
{{
  "primary_company": "{company}",
  "competitors": {json.dumps(competitors)},
  "comparative_summary": "string — 2-3 sentences comparing market positions",
  "market_leader": "string — which company leads and why",
  "differentiators": {{"company": ["unique strength"]}},
  "shared_risks": ["string"],
  "shared_opportunities": ["string"],
  "individual_briefs": {json.dumps({k: v for k, v in briefs.items()})}
}}
Return ONLY valid JSON."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Output ONLY valid JSON."},
            {"role": "user", "content": comp_prompt},
        ],
        temperature=0.3,
        max_tokens=3072,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(lines)
    return json.loads(raw)


async def answer_followup(brief: Dict, question: str, search_history: List[Dict]) -> str:
    """Answer follow-up question using brief + search history as context."""
    context = f"Intelligence Brief:\n{json.dumps(brief, indent=2)}\n\nSearch History:\n"
    for entry in search_history[-5:]:
        context += f"=== {entry['tool'].upper()} ===\n{entry['result']}\n\n"

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are Rivalyze. Answer the user's question using ONLY the provided intelligence brief and search data. Be concise, cite sources. If info not available, say so."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def generate_pdf(brief: Dict) -> bytes:
    """Generate PDF report from brief."""
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
            x = self.get_x()
            self.cell(8, 5, chr(8226))
            self.multi_cell(0, 5, text)
            self.ln(1)

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Executive Summary
    pdf.section_title("Executive Summary")
    pdf.body_text(brief.get("summary", "N/A"))
    pdf.body_text(f"Market Position: {brief.get('market_position', 'N/A')}")

    # Sentiment
    pdf.section_title("Sentiment Analysis")
    sentiment = brief.get("sentiment", "neutral")
    pdf.body_text(f"Overall: {sentiment.capitalize()} — {brief.get('sentiment_reason', 'N/A')}")

    # Recent Moves
    pdf.section_title("Recent Moves")
    for move in brief.get("recent_moves", [])[:5]:
        pdf.bullet(f"{move.get('title', '')} — {move.get('source', '')}: {move.get('snippet', '')}")

    # Pricing
    pdf.section_title("Pricing Signals")
    for item in brief.get("pricing", [])[:5]:
        pdf.bullet(f"{item.get('product', '')}: {item.get('price', '')} ({item.get('source', '')})")

    # Finance
    pdf.section_title("Market Data")
    fin = brief.get("finance", {})
    if fin.get("price"):
        pdf.body_text(f"Stock: {fin.get('stock_symbol', 'N/A')} — {fin.get('price', '')} ({fin.get('change', '')})")
        pdf.body_text(f"Market Cap: {fin.get('market_cap', 'N/A')}")
    else:
        pdf.body_text("No public market data available.")

    # Hiring
    pdf.section_title("Hiring Signal")
    hiring = brief.get("hiring", {})
    pdf.body_text(f"Signal: {hiring.get('signal', 'Unknown').capitalize()} — {hiring.get('reason', 'N/A')}")
    for role in hiring.get("sample_roles", [])[:3]:
        pdf.bullet(role)

    # Locations
    pdf.section_title("Physical Presence")
    for loc in brief.get("locations", [])[:6]:
        pdf.bullet(loc)

    # Videos
    pdf.section_title("Video Presence")
    for vid in brief.get("key_videos", [])[:3]:
        pdf.bullet(f"{vid.get('title', '')} — {vid.get('channel', '')} ({vid.get('url', '')})")

    # Risks
    pdf.section_title("Risks")
    for r in brief.get("risks", []):
        pdf.bullet(r)

    # Opportunities
    pdf.section_title("Opportunities")
    for o in brief.get("opportunities", []):
        pdf.bullet(o)

    # Top Sources
    pdf.section_title("Top Sources")
    pdf.body_text(", ".join(brief.get("top_sources", [])))

    return pdf.output(dest="S").encode("latin-1")


async def run_agent(company: str) -> Dict:
    """Main entry: agentic analysis for single company."""
    orchestrator = AgenticOrchestrator(company)
    return await orchestrator.run_agentic_analysis()


async def run_comparative(company: str) -> Dict:
    """Main entry: comparative analysis with competitors."""
    return await run_comparative_analysis(company)