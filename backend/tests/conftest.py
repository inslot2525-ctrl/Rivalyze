import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from agents.schemas import (Analysis, Critique, EvidenceStore, FollowUp, Forecast, Plan, Rival,  # noqa: E402
                            RivalRead, SayVsDo, Tell)
from serp.client import SerpClient  # noqa: E402
from serp.collectors import Collectors  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def serp():
    """Replay-only client: no API key, so anything not recorded raises instead of spending."""
    return SerpClient(budget=15, cache_dir=FIXTURES, api_key="")


@pytest.fixture
def store():
    return EvidenceStore()


@pytest.fixture
def collect(serp, store):
    return Collectors(serp, store)


class FakeLLM:
    """Returns canned plan, critique and analysis so the pipeline runs offline."""

    def __init__(self, analysis: Analysis):
        self.calls = 0
        self.analysis = analysis

    async def structured(self, system, prompt, schema, temperature=0.3, fast=False):
        self.calls += 1
        if schema is Plan:
            return Plan(official_name="Notion", legal_name="Notion Labs, Inc.",
                        description="Collaborative workspace for docs, wikis and projects.",
                        domain="notion.so", ticker="",
                        news_query='"Notion Labs" OR "Notion workspace" OR "Ivan Zhao"',
                        rivals=[Rival(name="Confluence", employer="Atlassian"),
                                Rival(name="Coda", employer="Coda"),
                                Rival(name="Airtable", employer="Airtable"),
                                Rival(name="ClickUp", employer="ClickUp")])
        if schema is Critique:
            return Critique(gaps=["What users criticise"], follow_ups=[FollowUp(
                kind="ai_mode", query="What are the main criticisms of Notion AI and its pricing?",
                reason="Tests the pricing forecast")])
        return self.analysis


@pytest.fixture
def analysis():
    return Analysis(
        one_liner="Notion is building an enterprise sales motion.",
        summary="Hiring and patents point the same way [J1, P1]. One made-up source [Z9].",
        tells=[
            Tell(signal="hiring", headline="Mobile core hiring", detail="Android roles [J1].",
                 strength="strong", evidence_ids=["J1", "J999"]),
            Tell(signal="rnd", headline="Invented finding", detail="Nothing behind this.",
                 strength="weak", evidence_ids=["X42"]),
        ],
        say_vs_do=[
            SayVsDo(topic="AI", says="All in on AI", says_evidence=["W1"], does="Hiring mobile engineers",
                    does_evidence=["J1"], verdict="tension", insight="Attack mobile performance."),
            SayVsDo(topic="Scripted only", says="Says a thing", says_evidence=["W1"], does="Says it again",
                    does_evidence=["N1"], verdict="consistent", insight="Nothing involuntary here."),
        ],
        forecasts=[
            Forecast(prediction="Rebuilt Android app", rationale="Roles and filings", horizon="3-6 months",
                     confidence=95, evidence_ids=["J1", "P1"], counter_move="Ship offline mode first."),
            Forecast(prediction="Single-signal guess", rationale="One role", horizon="0-3 months",
                     confidence=90, evidence_ids=["J1"], counter_move="Watch."),
        ],
        rivals=[RivalRead(name="Confluence", edge="More deal-desk hiring.", evidence_ids=["T2"])],
        standing="Notion leads on search demand [T1] and trails Confluence on fresh postings [Z9].",
        open_questions=["Pricing changes?"],
    )


@pytest.fixture
def fake_llm(analysis):
    return FakeLLM(analysis)
