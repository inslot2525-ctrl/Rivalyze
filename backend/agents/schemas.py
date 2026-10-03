"""Data shapes shared by the collectors, the agents and the API."""
from collections import Counter
from typing import Literal, Optional

from pydantic import BaseModel, Field

Signal = Literal["hiring", "narrative", "demand", "rnd", "ads", "market", "doubts",
                 "ai_view", "web", "rivals"]

# One-letter id prefix per signal, so a citation like "J3" is readable on its own.
PREFIX = {"hiring": "J", "narrative": "N", "demand": "T", "rnd": "P", "ads": "A",
          "market": "F", "doubts": "Q", "ai_view": "I", "web": "W", "rivals": "S"}

# Signals a company does not script. Everything else is closer to its own narrative.
INVOLUNTARY = {"hiring", "demand", "rnd", "ads", "doubts", "ai_view", "market"}


class Evidence(BaseModel):
    id: str
    signal: Signal
    subject: str
    engine: str
    query: str
    title: str
    link: Optional[str] = None
    snippet: str = ""
    source: str = ""
    date: str = ""
    extra: dict = Field(default_factory=dict)

    def digest(self) -> str:
        """One line for the LLM: enough to reason from, short enough to fit many."""
        bits = [f"[{self.id}] {self.signal} | {self.subject} | {self.title}"]
        if self.date:
            bits.append(self.date)
        if self.source:
            bits.append(self.source)
        if self.snippet:
            bits.append(self.snippet[:260])
        return " | ".join(bits)


class EvidenceStore:
    """Hands out stable ids and keeps every piece of evidence a scan has gathered."""

    def __init__(self):
        self.items: dict[str, Evidence] = {}
        self._count: Counter = Counter()

    def add(self, signal: str, **fields) -> Evidence:
        prefix = PREFIX[signal]
        self._count[prefix] += 1
        ev = Evidence(id=f"{prefix}{self._count[prefix]}", signal=signal, **fields)
        self.items[ev.id] = ev
        return ev

    def by_signal(self, signal: str, subject: Optional[str] = None) -> list[Evidence]:
        return [e for e in self.items.values()
                if e.signal == signal and (subject is None or e.subject == subject)]

    def digest(self) -> str:
        return "\n".join(e.digest() for e in self.items.values())


# ---- LLM outputs -----------------------------------------------------------

class Rival(BaseModel):
    name: str = Field(description="Product or brand name people search for, e.g. 'Confluence'")
    employer: str = Field(description="Company that hires for it, e.g. 'Atlassian'. Same as name if identical.")


class Plan(BaseModel):
    official_name: str = Field(description="Name people search for, e.g. 'Notion'")
    legal_name: str = Field(description="Legal entity that would own patents, e.g. 'Notion Labs'")
    description: str = Field(description="One sentence: what the company sells and to whom")
    domain: str = Field(description="Primary website domain without protocol, or empty")
    ticker: str = Field(description="Google Finance symbol like 'TSLA:NASDAQ' if publicly traded, else empty")
    news_query: str = Field(description="Google News query that returns news about this company only, "
                                        "disambiguated if the name is a common word")
    rivals: list[Rival] = Field(description="Direct competitors, most important first")


class FollowUp(BaseModel):
    kind: Literal["ads", "finance", "ai_mode", "jobs", "news", "web", "patents"]
    query: str = Field(description="Search query. For 'ads' the company domain, for 'finance' the ticker.")
    reason: str = Field(description="What gap in the evidence this search closes")


class Critique(BaseModel):
    gaps: list[str] = Field(description="What the evidence so far cannot answer")
    follow_ups: list[FollowUp]


class Tell(BaseModel):
    signal: Signal
    headline: str = Field(description="The finding in under 12 words")
    detail: str = Field(description="2 sentences: what the evidence shows and what it implies")
    strength: Literal["strong", "moderate", "weak"]
    evidence_ids: list[str]


class SayVsDo(BaseModel):
    topic: str
    says: str = Field(description="What the company or its press coverage claims")
    says_evidence: list[str]
    does: str = Field(description="What hiring, patents, ads, demand or market data actually show")
    does_evidence: list[str]
    verdict: Literal["consistent", "tension", "contradiction"]
    insight: str = Field(description="One sentence a competitor could act on")


class Forecast(BaseModel):
    prediction: str = Field(description="A specific move the company is likely to make")
    rationale: str
    horizon: Literal["0-3 months", "3-6 months", "6-12 months"]
    confidence: int = Field(description="0-100")
    evidence_ids: list[str]
    counter_move: str = Field(description="What a competitor should do about it now")


class RivalRead(BaseModel):
    name: str
    edge: str = Field(description="Where this rival is ahead of or behind the target, from the evidence")
    evidence_ids: list[str]


class Analysis(BaseModel):
    one_liner: str = Field(description="The single most important thing the signals reveal")
    summary: str = Field(description="3-4 sentence executive read")
    tells: list[Tell]
    say_vs_do: list[SayVsDo]
    forecasts: list[Forecast]
    rivals: list[RivalRead]
    standing: str = Field(description="Two sentences: where the target stands among its rivals and why, "
                                      "consistent with METRICS.scorecard")
    open_questions: list[str] = Field(description="What the evidence could not settle")
