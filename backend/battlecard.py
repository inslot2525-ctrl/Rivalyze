"""Render a scan as a Markdown battlecard that can be pasted into a doc or a CRM."""
import re

CITE = re.compile(r"\[([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)\]")


def _refs(ids: list[str]) -> str:
    return " ".join(f"[{i}]" for i in ids)


def battlecard(report: dict) -> str:
    a, evidence = report["analysis"], report["evidence"]
    used: list[str] = []

    def note(ids):
        for i in ids:
            if i in evidence and i not in used:
                used.append(i)

    out = [f"# {report['company']} — competitive battlecard",
           f"_Scanned {report['created_at'][:10]} by Rivalyze from {report['usage']['evidence_items']} "
           f"search results across {len(report['usage']['engines'])} SerpApi engines._", "",
           f"**{a['one_liner']}**", "", a["summary"], ""]

    out += ["## What they will do next", ""]
    for f in a["forecasts"]:
        note(f["evidence_ids"])
        out += [f"### {f['prediction']}",
                f"- Confidence: **{f['confidence']}%** over {f['horizon']} "
                f"(signals: {', '.join(f['signals'])})",
                f"- Why: {f['rationale']}",
                f"- **Your move:** {f['counter_move']}", ""]

    if a["say_vs_do"]:
        out += ["## What they say vs what they do", "",
                "| Topic | Says | Does | Read |", "|---|---|---|---|"]
        for s in a["say_vs_do"]:
            note(s["says_evidence"] + s["does_evidence"])
            cells = [s["topic"], s["says"], s["does"], f"**{s['verdict']}** — {s['insight']}"]
            out.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
        out.append("")

    out += ["## Tells", ""]
    for t in a["tells"]:
        note(t["evidence_ids"])
        out.append(f"- **{t['headline']}** ({t['signal']}, {t['strength']}) — {t['detail']} "
                   f"{_refs(t['evidence_ids'])}")
    out.append("")

    standing = a.get("standing")
    card = report["metrics"].get("scorecard") or {}
    if standing and (standing.get("ahead") or standing.get("behind") or card.get("rows")):
        out += ["## Where it stands", "", standing["verdict"], ""]
        if card.get("rows"):
            names = [c["name"] for c in report["metrics"]["compare"]]
            out += ["| Measure | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
            for row in card["rows"]:
                by_name = {v["name"]: v["value"] for v in row["values"]}
                cells = [f"**{by_name[n]}{row['unit']}**" if n == row["leader"] else
                         (f"{by_name[n]}{row['unit']}" if n in by_name else "—") for n in names]
                out.append(f"| {row['label']} | " + " | ".join(cells) + " |")
            out.append("")
        for title, side in (("Ahead", "ahead"), ("Behind", "behind")):
            for p in standing.get(side, []):
                note(p["evidence_ids"])
                out.append(f"- **{title}.** {p['point']}")
        out.append("")

    if a["rivals"]:
        out += ["## Against its rivals", ""]
        for r in a["rivals"]:
            note(r["evidence_ids"])
            out.append(f"- **{r['name']}:** {r['edge']}")
        out.append("")

    if a["open_questions"]:
        out += ["## Still unknown", ""] + [f"- {q}" for q in a["open_questions"]] + [""]

    # Anything cited inline in the prose belongs in the source list too.
    for m in CITE.finditer("\n".join(out)):
        note([i.strip() for i in m.group(1).split(",")])

    out += ["## Receipts", ""]
    for i in used:
        e = evidence[i]
        title = e["title"].replace("[", "(").replace("]", ")")
        link = f"[{title}]({e['link']})" if e.get("link") else title
        out.append(f"- **{i}** {link} — `{e['engine']}`" + (f", {e['date']}" if e.get("date") else ""))
    return "\n".join(out) + "\n"
