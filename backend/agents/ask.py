"""Ask Rivalyze: follow-up questions about a finished scan.

The agent answers from the scan's evidence first. When that is not enough it may
run a small number of live searches through the hosted SerpApi MCP server, with
the direct SerpApi client as a fallback if the MCP connection fails.
"""
import json
import re

from google.genai import types
from mcp import Client as McpClient

from agents.llm import LLM
from config import settings
from serp.client import SerpClient

MAX_LIVE_SEARCHES = 2
ENGINES = ["google", "google_news", "google_jobs", "google_patents", "google_ai_mode"]

SYSTEM = """You are Rivalyze, answering a follow-up question about a competitive-intelligence scan.

- Answer from the EVIDENCE first and cite ids inline in square brackets, like [J3] or [P2, N4].
- If the evidence cannot answer the question, call live_search (at most twice). Cite what you find
  from a live search as a markdown link to the source URL.
- If you still cannot answer, say what is missing. Do not guess.
- Be direct: lead with the answer, then the support. Under 180 words unless asked for more.
- Plain text only. No bold, headings, bullets or backticks. Markdown links are the one exception."""

LIVE_SEARCH = types.Tool(function_declarations=[types.FunctionDeclaration(
    name="live_search",
    description="Run a live SerpApi search when the scan's evidence does not answer the question.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "engine": types.Schema(type="STRING", enum=ENGINES,
                                   description="google for web, google_news for recent coverage, "
                                               "google_jobs for postings, google_patents for filings, "
                                               "google_ai_mode for an AI-synthesised answer"),
            "query": types.Schema(type="STRING", description="The search query"),
        },
        required=["engine", "query"]))])


async def _mcp_search(engine: str, query: str) -> str:
    """Search through SerpApi's hosted MCP server (key in the path, as its docs describe)."""
    base = settings.serpapi_mcp_url.rstrip("/")
    url = base[:-len("/mcp")] + f"/{settings.serpapi_api_key}/mcp" if base.endswith("/mcp") else base
    async with McpClient(url, read_timeout_seconds=45) as client:
        result = await client.call_tool("search", {"params": {"engine": engine, "q": query},
                                                   "mode": "compact"})
    return "\n".join(getattr(c, "text", "") for c in result.content)


async def _direct_search(engine: str, query: str) -> str:
    data, _ = await SerpClient(budget=1).search(engine, q=query)
    return json.dumps(data, ensure_ascii=False)


async def live_search(engine: str, query: str) -> tuple[str, str]:
    """Return (result text, route) where route is 'serpapi-mcp' or 'serpapi-direct'."""
    if engine not in ENGINES:
        return f"Unknown engine {engine}", "none"
    if not settings.serpapi_api_key:
        return "Live search is unavailable: no SERPAPI_API_KEY is configured.", "none"
    try:
        return (await _mcp_search(engine, query))[:7000], "serpapi-mcp"
    except Exception:
        try:
            return (await _direct_search(engine, query))[:7000], "serpapi-direct"
        except Exception as e:
            return f"Search failed: {str(e)[:200]}", "none"


def _context(report: dict) -> str:
    metrics = dict(report["metrics"])
    if "trends" in metrics:
        metrics["trends"] = metrics["trends"]["stats"]
    lines = []
    for e in report["evidence"].values():
        bits = [f"[{e['id']}] {e['signal']} | {e['subject']} | {e['title']}", e.get("date"),
                e.get("source"), (e.get("snippet") or "")[:240]]
        lines.append(" | ".join(b for b in bits if b))
    return (f"COMPANY: {report['company']} — {report['plan']['description']}\n"
            f"RIVALS: {', '.join(report['rivals'])}\n\n"
            f"ANALYSIS:\n{json.dumps(report['analysis'], ensure_ascii=False)}\n\n"
            f"METRICS:\n{json.dumps(metrics, ensure_ascii=False)}\n\n"
            f"EVIDENCE:\n" + "\n".join(lines))


async def ask(report: dict, question: str, history: list[dict] | None = None) -> dict:
    llm = LLM()
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM, temperature=0.3, tools=[LIVE_SEARCH],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents = [types.Content(role="user", parts=[types.Part(text=_context(report))]),
                types.Content(role="model", parts=[types.Part(text="I have the scan. What do you want to know?")])]
    for turn in (history or [])[-6:]:
        role = "model" if turn.get("role") == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=str(turn.get("text", ""))[:2000])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=question)]))

    searches: list[dict] = []
    models = [m.strip() for m in settings.gemini_models.split(",") if m.strip()]
    answer = ""
    for _ in range(MAX_LIVE_SEARCHES + 1):
        resp = None
        for model in models:
            try:
                resp = await llm.client.aio.models.generate_content(
                    model=model, contents=contents, config=config)
                break
            except Exception:
                continue
        if resp is None:
            raise RuntimeError("Gemini is unavailable right now. Try again in a moment.")
        calls = resp.function_calls or []
        if not calls or len(searches) >= MAX_LIVE_SEARCHES:
            answer = resp.text or ""
            if answer:
                break
        # Keep the model's own turn (it carries thought signatures), then answer each call.
        contents.append(resp.candidates[0].content)
        parts = []
        for call in calls:
            args = dict(call.args or {})
            if len(searches) >= MAX_LIVE_SEARCHES:
                text, route = "Search limit reached. Answer with what you have.", "none"
            else:
                text, route = await live_search(args.get("engine", "google"), args.get("query", ""))
                searches.append({"engine": args.get("engine"), "query": args.get("query"), "via": route})
            parts.append(types.Part.from_function_response(name=call.name, response={"result": text}))
        contents.append(types.Content(role="user", parts=parts))

    cited = []
    for group in re.findall(r"\[([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)\]", answer):
        for i in (x.strip() for x in group.split(",")):
            if i in report["evidence"] and i not in cited:
                cited.append(i)
    return {"answer": answer.strip() or "I could not produce an answer from the evidence.",
            "citations": cited, "searches": searches}
