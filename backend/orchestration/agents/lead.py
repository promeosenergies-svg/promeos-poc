"""
Lead Engineer Agent — Claude Agent SDK (orchestrateur P2).

Dispatche QA Guardian + Regulatory Analyst en séquence et consolide
leurs rapports en un brief unique pour le CTO.

Architecture :
  Le Lead ne fait PAS d'audit direct — il délègue aux agents spécialisés
  via `run_qa_audit` et `run_regulatory_audit` (import direct Python,
  zéro spawn SDK supplémentaire = zéro coût token).
  Il post-traite les résultats structurés ({status, findings, summary})
  et produit un rapport d'exécution compact (findings P0 prioritaires,
  métriques, recommandations).

  Optionnellement (scope `synthesis`), il peut appeler une fois le SDK
  pour faire une synthèse narrative à partir des 2 rapports JSON.

Pour la CI/CD : ce wrapper permet de lancer `lead full` qui enchaîne
QA source-guards + Regulatory audit-cesures en une seule commande,
avec un exit code agrégé (green seulement si les 2 sont green).
"""

from __future__ import annotations

import anyio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from ..config import AGENT_MAX_TURNS, AGENT_MODEL, REPO_ROOT
from .qa_guardian import run_qa_audit
from .regulatory import run_regulatory_audit


LEAD_SYNTHESIS_SYSTEM_PROMPT = """Tu es le Lead Engineer de PROMEOS.

Tu reçois 2 rapports d'audit JSON (QA Guardian + Regulatory Analyst) et
tu produis un brief de 15-25 lignes pour le CTO avec :
1. Top 3 findings P0 (les plus critiques, agrégés des deux rapports)
2. Pattern systémique détecté le cas échéant (doctrine violée, anti-pattern)
3. Prochaines actions recommandées (priorisées)
4. Verdict global (merge ok / bloqueur / besoin triage)

Style : français, dense, tableau ou puces, zéro fluff. Cite fichier:ligne
quand pertinent. Pas de redites des rapports sources.
"""


async def run_lead_audit(scope: str = "full") -> dict:
    """Orchestre QA Guardian + Regulatory Analyst.

    Args:
        scope:
            - "full" : QA source-guards + Regulatory audit-cesures (agrégé)
            - "quick" : QA tests seulement (rapide, pas d'API live Regulatory)
            - "synthesis" : QA source-guards + Regulatory audit-cesures
                            + synthèse narrative SDK (coûte 1 query de plus)

    Returns:
        dict : {status, findings, summary, scope, sub_reports}
    """
    if scope not in {"full", "quick", "synthesis"}:
        raise ValueError(f"Scope inconnu '{scope}'. Valides : full, quick, synthesis")

    sub_reports: dict[str, dict] = {}

    # Étape 1 — QA Guardian
    if scope == "quick":
        qa_result = await run_qa_audit("tests")
    else:
        qa_result = await run_qa_audit("source-guards")
    sub_reports["qa_guardian"] = qa_result

    # Étape 2 — Regulatory (sauf en quick)
    reg_result: dict | None = None
    if scope != "quick":
        reg_result = await run_regulatory_audit("audit-cesures")
        sub_reports["regulatory"] = reg_result

    # Statut agrégé : green seulement si tous verts
    statuses = [qa_result["status"]]
    if reg_result:
        statuses.append(reg_result["status"])
    is_green = all(s == "green" for s in statuses)

    # Synthèse
    lines: list[str] = [
        f"# Lead Engineer — audit {scope}",
        "",
        "## Sous-rapports",
        f"- QA Guardian ({qa_result['scope']}) : **{qa_result['status'].upper()}**",
    ]
    if reg_result:
        lines.append(f"- Regulatory Analyst ({reg_result['scope']}) : **{reg_result['status'].upper()}**")
    lines.extend(["", "## Résumés agrégés", ""])
    lines.append("### QA Guardian")
    lines.append((qa_result.get("summary") or "(aucun résumé)")[:2000])
    if reg_result:
        lines.append("")
        lines.append("### Regulatory Analyst")
        lines.append((reg_result.get("summary") or "(aucun résumé)")[:2000])

    summary_text = "\n".join(lines)

    # Scope "synthesis" : 1 query SDK supplémentaire pour narrative
    synthesis_text: str | None = None
    if scope == "synthesis":
        options = ClaudeAgentOptions(
            system_prompt=LEAD_SYNTHESIS_SYSTEM_PROMPT,
            allowed_tools=[],  # pas d'outils — pure inférence sur les 2 rapports
            disallowed_tools=["Write", "Edit", "MultiEdit", "Bash", "Read", "Glob", "Grep"],
            max_turns=1,
            cwd=str(REPO_ROOT),
            model=AGENT_MODEL,
        )
        prompt_synth = (
            "Voici 2 rapports d'audit PROMEOS :\n\n"
            f"## QA Guardian (status={qa_result['status']})\n{qa_result.get('summary', '')[:3500]}\n\n"
            f"## Regulatory Analyst (status={reg_result['status']})\n{reg_result.get('summary', '')[:3500]}\n\n"
            "Produis un brief CTO de 15-25 lignes : top 3 P0 agrégés, pattern systémique, "
            "actions prioritaires, verdict global."
        )
        synth_parts: list[str] = []
        async for message in query(prompt=prompt_synth, options=options):
            if isinstance(message, ResultMessage):
                synth_parts.append(getattr(message, "result", None) or str(message))
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        synth_parts.append(block.text)
        synthesis_text = "\n".join(synth_parts)
        summary_text += "\n\n## Synthèse CTO (LLM)\n\n" + synthesis_text

    return {
        "status": "green" if is_green else "red",
        "findings": [
            f"QA Guardian: {qa_result['status']}",
            *([f"Regulatory: {reg_result['status']}"] if reg_result else []),
        ],
        "summary": summary_text,
        "scope": scope,
        "sub_reports": sub_reports,
    }


if __name__ == "__main__":
    import sys

    scope_arg = sys.argv[1] if len(sys.argv) > 1 else "full"

    async def _main():
        return await run_lead_audit(scope_arg)

    result = anyio.run(_main)
    print(f"\n{'=' * 60}")
    print(f"Lead Engineer — Scope: {result['scope']} — Status: {result['status']}")
    print(f"{'=' * 60}")
    print(result["summary"])
