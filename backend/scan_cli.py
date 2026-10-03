"""Run a scan from the terminal.

    python scan_cli.py "Notion"              print the trace and a summary
    python scan_cli.py "Notion" --save-demo  also record it as a replayable demo
"""
import asyncio
import json
import re
import sys

from agents.pipeline import Scan
from config import settings


async def main(company: str, save_demo: bool):
    async def show(event: dict):
        if event["type"] == "search":
            tag = "cache" if event["cached"] else "LIVE "
            print(f"  [{tag}] {event['engine']:<32} {event['results']:>3} results  {event['query'][:60]}")
        elif event["type"] == "stage":
            print(f"\n== {event['stage']}: {event['text']}")
        elif event["type"] != "report":
            print("  ", json.dumps({k: v for k, v in event.items() if k not in ("type", "t")},
                                   ensure_ascii=False)[:600])

    scan = Scan(company, emit=show)
    report = await scan.run()
    a = report["analysis"]
    print("\n" + "=" * 78 + f"\n{report['company']}: {a['one_liner']}\n\n{a['summary']}\n")
    for t in a["tells"]:
        print(f"TELL [{t['signal']}/{t['strength']}] {t['headline']}  {t['evidence_ids']}\n     {t['detail']}")
    for s in a["say_vs_do"]:
        print(f"\nSAY/DO [{s['verdict']}] {s['topic']}\n  says: {s['says']} {s['says_evidence']}\n"
              f"  does: {s['does']} {s['does_evidence']}\n  -> {s['insight']}")
    for f in a["forecasts"]:
        print(f"\nFORECAST {f['confidence']}% ({f['horizon']}, {'+'.join(f['signals'])}) {f['prediction']} "
              f"{f['evidence_ids']}\n  why: {f['rationale']}\n  counter: {f['counter_move']}")
    for r in a["rivals"]:
        print(f"\nRIVAL {r['name']}: {r['edge']} {r['evidence_ids']}")
    print("\nGROUNDING", report["grounding"])
    print("USAGE", {k: v for k, v in report["usage"].items() if k != "calls"})

    if save_demo:
        slug = re.sub(r"[^a-z0-9]+", "-", report["company"].lower()).strip("-")
        settings.demos_dir.mkdir(exist_ok=True)
        path = settings.demos_dir / f"{slug}.json"
        path.write_text(json.dumps({"slug": slug, "report": report, "events": scan.events},
                                   ensure_ascii=False), encoding="utf-8")
        print(f"Saved demo to {path}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    asyncio.run(main(args[0], "--save-demo" in sys.argv))
