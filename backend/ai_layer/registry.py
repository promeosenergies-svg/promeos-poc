"""
PROMEOS AI - Registry des agents
"""

from typing import Dict
from .agents import regops_explainer, regops_recommender, data_quality_agent, reg_change_agent, exec_brief_agent


_AGENTS = {}


def _register_all():
    if _AGENTS:
        return

    _AGENTS["regops_explainer"] = regops_explainer.run
    _AGENTS["regops_recommender"] = regops_recommender.run
    _AGENTS["data_quality_agent"] = data_quality_agent.run
    _AGENTS["reg_change_agent"] = reg_change_agent.run
    _AGENTS["exec_brief_agent"] = exec_brief_agent.run


def run_agent(name: str, db, **kwargs):
    """Execute un agent IA."""
    _register_all()
    agent_func = _AGENTS.get(name)
    if not agent_func:
        raise ValueError(f"Agent {name} not found")
    return agent_func(db, **kwargs)
