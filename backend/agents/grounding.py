"""No receipt, no claim.

The analyst must cite evidence ids. This module checks every citation against
the evidence the scan actually collected, removes ids that do not exist, drops
claims left with nothing behind them, and caps forecast confidence by how many
independent signals back it.
"""
import re

from agents.schemas import Analysis, EvidenceStore, INVOLUNTARY

# Inline citations such as "[J3, P9]". The model sometimes writes "[METRICS, A1]" too.
INLINE = re.compile(r"\s*\[((?:METRICS|[A-Z]\d+)(?:\s*,\s*(?:METRICS|[A-Z]\d+))*)\]")

# Max confidence a forecast may carry, by number of distinct signals it cites.
CONFIDENCE_CAP = {1: 55, 2: 75}
CONFIDENCE_CAP_MAX = 90


def _valid(ids: list[str], store: EvidenceStore, stats: dict) -> list[str]:
    seen, out = set(), []
    for raw in ids:
        i = raw.strip().strip("[]")
        if i in store.items and i not in seen:
            seen.add(i)
            out.append(i)
        elif i not in store.items:
            stats["citations_removed"] += 1
    return out


def scrub(text: str, store: EvidenceStore) -> str:
    """Remove inline citations like [J3, P9] that point at evidence which does not exist."""
    def fix(m: re.Match) -> str:
        ids = [i.strip() for i in m.group(1).split(",") if i.strip() in store.items]
        return f" [{', '.join(ids)}]" if ids else ""
    return INLINE.sub(fix, text).strip()


def _scrub_all(node, store: EvidenceStore):
    if isinstance(node, str):
        return scrub(node, store)
    if isinstance(node, list):
        return [_scrub_all(n, store) for n in node]
    if isinstance(node, dict):
        return {k: v if k.endswith("evidence") or k in ("evidence_ids", "signals") else _scrub_all(v, store)
                for k, v in node.items()}
    return node


def ground(analysis: Analysis, store: EvidenceStore) -> tuple[dict, dict]:
    """Return (grounded analysis as a dict, stats about what was checked and removed)."""
    stats = {"claims_checked": 0, "claims_dropped": 0, "citations_removed": 0, "confidence_capped": 0}
    out = {"one_liner": analysis.one_liner, "summary": analysis.summary,
           "open_questions": analysis.open_questions,
           "tells": [], "say_vs_do": [], "forecasts": [], "rivals": []}

    for tell in analysis.tells:
        stats["claims_checked"] += 1
        ids = _valid(tell.evidence_ids, store, stats)
        if not ids:
            stats["claims_dropped"] += 1
            continue
        out["tells"].append({**tell.model_dump(), "evidence_ids": ids})

    for item in analysis.say_vs_do:
        stats["claims_checked"] += 1
        says = _valid(item.says_evidence, store, stats)
        does = _valid(item.does_evidence, store, stats)
        # The "does" side has to rest on something the company does not script.
        if not says or not any(store.items[i].signal in INVOLUNTARY for i in does):
            stats["claims_dropped"] += 1
            continue
        out["say_vs_do"].append({**item.model_dump(), "says_evidence": says, "does_evidence": does})

    for fc in analysis.forecasts:
        stats["claims_checked"] += 1
        ids = _valid(fc.evidence_ids, store, stats)
        if not ids:
            stats["claims_dropped"] += 1
            continue
        signals = sorted({store.items[i].signal for i in ids})
        cap = CONFIDENCE_CAP.get(len(signals), CONFIDENCE_CAP_MAX)
        confidence = max(0, min(fc.confidence, cap))
        if confidence < fc.confidence:
            stats["confidence_capped"] += 1
        out["forecasts"].append({**fc.model_dump(), "evidence_ids": ids, "confidence": confidence,
                                 "signals": signals})
    out["forecasts"].sort(key=lambda f: f["confidence"], reverse=True)

    for rival in analysis.rivals:
        stats["claims_checked"] += 1
        ids = _valid(rival.evidence_ids, store, stats)
        if not ids:
            stats["claims_dropped"] += 1
            continue
        out["rivals"].append({**rival.model_dump(), "evidence_ids": ids})

    out["standing"] = {"verdict": analysis.standing}

    return _scrub_all(out, store), stats
