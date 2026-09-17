import os
import json
import asyncio
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from agents.tools import TOOL_MAP, TOOL_DEFINITIONS

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-1.5-flash"

# Convert TOOL_DEFINITIONS to Gemini's function declaration format
GEMINI_TOOLS = []
for tool_def in TOOL_DEFINITIONS:
    fn = tool_def["function"]
    GEMINI_TOOLS.append({
        "function_declarations": [{
            "name": fn["name"],
            "description": fn["description"],
            "parameters": fn["parameters"]
        }]
    })

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
        self.model = genai.GenerativeModel(MODEL, tools=GEMINI_TOOLS)

    async def run_agentic_analysis(self) -> Dict:
        """Run iterative agentic loop: decide next search based on findings."""
        system_prompt = f"""You are Rivalyze, an elite competitive intelligence analyst.
Analyze {self.company} by calling search tools (maximum 4 calls total).
After gathering data, synthesize into this EXACT JSON:
{BRIEF_SCHEMA}
Return ONLY valid JSON when done — no markdown, no explanation."""

        chat = self.model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["Understood. I'll begin the analysis."]},
            {"role": "user", "parts": [f"Begin analysis of {self.company}. Start with the most important searches."]}
        ])

        MAX_TOOL_CALLS = 4
        tool_calls_made = 0
        max_iterations = 8

        for iteration in range(max_iterations):
            if tool_calls_made >= MAX_TOOL_CALLS:
                response = await chat.send_message_async(
                    "You have gathered enough data. Now synthesize everything into the required JSON. Return ONLY valid JSON, no markdown, no explanation.",
                    generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=2048)
                )
                raw = self._clean_json(response.text or "")
                try:
                    self.brief = json.loads(raw)
                    self.brief["_search_history"] = self.search_history
                    return self.brief
                except json.JSONDecodeError:
                    return await self._fallback_synthesis()

            response = await chat.send_message_async(
                "Continue analysis. Call the next most relevant search tool.",
                generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=2048)
            )

            # Check for function calls in response
            function_calls = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)

            if function_calls and tool_calls_made < MAX_TOOL_CALLS:
                for fc in function_calls:
                    fn_name = fc.name
                    fn_args = dict(fc.args)
                    fn = TOOL_MAP.get(fn_name)
                    if fn:
                        result = fn(**fn_args)
                        trimmed = result[:1500] if len(result) > 1500 else result
                        self.search_history.append({
                            "tool": fn_name,
                            "args": fn_args,
                            "result": trimmed,
                        })
                        # Send function response back
                        await chat.send_message_async(
                            genai.protos.Part(function_response=genai.protos.FunctionResponse(
                                name=fn_name,
                                response={"result": trimmed}
                            ))
                        )
                    tool_calls_made += 1
            else:
                # No function calls - parse synthesis
                raw = self._clean_json(response.text or "")
                try:
                    self.brief = json.loads(raw)
                    self.brief["_search_history"] = self.search_history
                    return self.brief
                except json.JSONDecodeError:
                    # Ask again for valid JSON
                    await chat.send_message_async("Return ONLY the JSON object. No explanation, no markdown.")
                    continue

        return await self._fallback_synthesis()

    def _clean_json(self, text: str) -> str:
        """Strip markdown fences and clean up."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)
        return text.strip()

    async def _fallback_synthesis(self) -> Dict:
        """Final synthesis attempt with all collected data."""
        user_msg = f"Synthesize all search data for {self.company} into the required JSON:\n\n"
        for entry in self.search_history:
            user_msg += f"=== {entry['tool'].upper()} ===\n{entry['result']}\n\n"

        model = genai.GenerativeModel(MODEL)
        response = await model.generate_content_async(
            f"Output ONLY valid JSON matching this schema: {BRIEF_SCHEMA}\n\n{user_msg}",
            generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=2048)
        )
        raw = self._clean_json(response.text or "")
        return json.loads(raw)


async def discover_competitors(company: str) -> List[str]:
    """Identify top 3-5 competitors for a company."""
    result = TOOL_MAP["competitor_search"](company)
    prompt = f"""From this search data, identify the top 3-5 direct competitors for {company}.
Return ONLY a JSON array of competitor names: ["Competitor1", "Competitor2", ...]"""

    model = genai.GenerativeModel(MODEL)
    response = await model.generate_content_async(
        f"Search data:\n{result}\n\n{prompt}",
        generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=512)
    )
    raw = response.text.strip()
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

    model = genai.GenerativeModel(MODEL)
    response = await model.generate_content_async(
        comp_prompt,
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=3072)
    )
    raw = response.text.strip()
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

    model = genai.GenerativeModel(MODEL)
    response = await model.generate_content_async(
        f"You are Rivalyze. Answer the user's question using ONLY the provided intelligence brief and search data. Be concise, cite sources. If info not available, say so.\n\nContext:\n{context}\n\nQuestion: {question}",
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=1024)
    )
    return response.text.strip()


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

    pdf.section_title("Executive Summary")
    pdf.body_text(brief.get("summary", "N/A"))
    pdf.body_text(f"Market Position: {brief.get('market_position', 'N/A')}")

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


async def run_agent(company: str) -> Dict:
    """Main entry: agentic analysis for single company."""
    orchestrator = AgenticOrchestrator(company)
    return await orchestrator.run_agentic_analysis()


async def run_comparative(company: str) -> Dict:
    """Main entry: comparative analysis with competitors."""
    return await run_comparative_analysis(company)