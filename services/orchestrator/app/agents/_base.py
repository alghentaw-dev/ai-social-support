

# ─────────────────────────────────────────────────────────────
# File: services/orchestrator/app/agents/_base.py
# ─────────────────────────────────────────────────────────────
from __future__ import annotations
from crewai import Agent
from app.agents.local_llm_adapter import LocalLLMAdapter

# Single LLM adapter reused by all agents
_llm = LocalLLMAdapter()


def make_agent(*, role: str, goal: str, backstory: str, tools=None, max_iter=4) -> Agent:
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=_llm,
        tools=tools or [],
        allow_delegation=False,
        verbose=False,
        max_iter=max_iter,
    )

