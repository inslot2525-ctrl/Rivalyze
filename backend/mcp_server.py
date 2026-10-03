"""Rivalyze as an MCP server, so any MCP client can run competitive scans.

Claude Code:
    claude mcp add rivalyze -- /path/to/backend/.venv/bin/python /path/to/backend/mcp_server.py

Claude Desktop (claude_desktop_config.json):
    {"mcpServers": {"rivalyze": {"command": "/path/to/backend/.venv/bin/python",
                                 "args": ["/path/to/backend/mcp_server.py"]}}}
"""
import asyncio

from mcp.server.mcpserver import MCPServer

import storage
from agents.ask import ask
from agents.pipeline import Scan
from battlecard import battlecard
from models import init_db

server = MCPServer(
    "rivalyze",
    instructions="Competitive intelligence from involuntary signals: what a company hires for, patents, "
                 "advertises and gets searched for, read from SerpApi. Every claim cites the search result "
                 "behind it. A live scan spends up to 15 SerpApi searches; list_demos and get_battlecard "
                 "on a demo spend none.")

_db_ready = asyncio.Lock()
_initialised = False


async def _ensure_db():
    global _initialised
    async with _db_ready:
        if not _initialised:
            await init_db()
            _initialised = True


async def _load(scan: str) -> dict:
    if scan.startswith("demo:"):
        demo = storage.load_demo(scan[5:])
        if not demo:
            raise ValueError(f"No demo named {scan[5:]}")
        return demo["report"]
    await _ensure_db()
    record = await storage.get_scan(scan)
    if not record:
        raise ValueError(f"No scan with id {scan}")
    return record.report


@server.tool()
async def scan_company(company: str, include_rivals: bool = True) -> str:
    """Run a live scan of a company and return its battlecard as Markdown.

    Spends up to 15 SerpApi searches. The first line of the result carries the scan id,
    which the other tools accept.
    """
    await _ensure_db()
    scan = Scan(company, include_rivals=include_rivals)
    report = await storage.save_scan(await scan.run(), scan.events)
    return f"scan_id: {report['id']}\n\n{battlecard(report)}"


@server.tool()
def list_demos() -> list[dict]:
    """List recorded scans that can be read without spending any searches."""
    return [{"scan": f"demo:{d['slug']}", "company": d["company"], "recorded_at": d["recorded_at"],
             "headline": d["one_liner"]} for d in storage.list_demos()]


@server.tool()
async def get_battlecard(scan: str) -> str:
    """Return the Markdown battlecard for a scan id or a demo reference such as 'demo:notion'."""
    return battlecard(await _load(scan))


@server.tool()
async def get_tells(scan: str, signal: str = "") -> list[dict]:
    """Return a scan's tells with the evidence behind each.

    signal optionally filters to one of: hiring, rnd, ads, demand, doubts, ai_view, market, narrative.
    """
    report = await _load(scan)
    out = []
    for tell in report["analysis"]["tells"]:
        if signal and tell["signal"] != signal:
            continue
        out.append({**tell, "evidence": [
            {k: report["evidence"][i].get(k) for k in ("id", "engine", "title", "link", "date")}
            for i in tell["evidence_ids"]]})
    return out


@server.tool()
async def ask_about_scan(scan: str, question: str) -> dict:
    """Ask a follow-up question about a scan. May run up to two live SerpApi searches."""
    return await ask(await _load(scan), question)


if __name__ == "__main__":
    server.run("stdio")
