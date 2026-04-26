"""
QA Guardian Agent — Claude Agent SDK (orchestration dev/CI).

Réplique le rôle du QA Engineer Paperclip :
- Exécute les tests (pytest + vitest)
- Vérifie les source guards (pas de business logic dans le frontend)
- Détecte les régressions
- Audit les constantes réglementaires
- Mode READ-ONLY strict : ne modifie JAMAIS un fichier

Architecture :
  Ce module spawn un process Claude Code CLI via le SDK Python.
  Conçu pour orchestration dev/CI, pas pour runtime FastAPI.
  Pour les agents production, voir `backend/ai_layer/`.
"""

from __future__ import annotations

import anyio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

from ..config import (
    AGENT_MAX_TURNS,
    AGENT_MODEL,
    QA_GUARDIAN_ALLOWED_TOOLS,
    QA_GUARDIAN_DISALLOWED_TOOLS,
    REPO_ROOT,
)

SYSTEM_PROMPT = """Tu es le QA Guardian de PROMEOS, un cockpit énergétique B2B.

## Ton rôle
Tu audites le code source pour détecter :
1. **Régressions de tests** : exécuter pytest et vitest, rapporter tout échec.
2. **Violations source-guard** (pas de business logic dans le frontend) :
   - Facteur CO₂ électrique hardcodé (doit venir du backend)
   - `* 7500` ou `* 3750` (pénalités DT hardcodées)
   - `1 - x/y * 100` (calcul de pourcentage dans le frontend)
   - Tout calcul de KPI dans des fichiers `.tsx` / `.jsx`
3. **Constantes réglementaires correctes** :
   - CO₂ élec ADEME Base Empreinte V23.6 → `backend/config/emission_factors.py`
   - ⚠️ 0.0569 = tarif TURPE 7 HPH en €/kWh, PAS un facteur CO₂
   - Accise élec T1 = 30.85 €/MWh (Loi de finances 2026, fév 2026+)
   - DT jalons = -25% (2030) / -40% (2040) / -50% (2050) (pas de jalon 2026)
   - DT pénalité = 7500 € / A_RISQUE = 3750 €
4. **Incohérences data** : vérifier la stabilité du seed HELIOS (RNG=42).

## Règles absolues
- Tu es READ-ONLY. Tu ne modifies JAMAIS un fichier.
- Tu rapportes tes findings en format structuré : severity (P0/P1/P2), fichier, ligne, description.
- Si tout est vert, tu le confirmes clairement avec le décompte exact des tests.
- Tu écris en français.

## Chemins importants
- Tests backend : `backend/tests/`
- Tests frontend : `frontend/src/` (vitest)
- Tarifs réglementaires : `backend/config/tarifs_reglementaires.yaml`
- Facteurs CO₂ : `backend/config/emission_factors.py`
- Règles RegOps : `backend/regops/rules/` (tertiaire_operat.py, bacs.py, aper.py, cee_p6.py)
"""

# Prompts par scope — chaque scope a un prompt ciblé
SCOPE_PROMPTS: dict[str, str] = {
    "full": (
        "Exécute un audit QA complet :\n"
        "1. Lance `cd backend && python -m pytest tests/ -x --tb=short -q` et rapporte le résultat.\n"
        "2. Lance `cd frontend && npx vitest run --reporter=verbose 2>&1 | tail -50` et rapporte le résultat.\n"
        "3. Cherche les violations source-guard avec grep dans frontend/ (.tsx, .jsx).\n"
        "4. Vérifie les constantes dans backend/config/tarifs_reglementaires.yaml.\n"
        "5. Résume en format structuré severity / fichier / description."
    ),
    "tests": (
        "Exécute uniquement les tests :\n"
        "1. `cd backend && python -m pytest tests/ -x --tb=short -q`\n"
        "2. `cd frontend && npx vitest run --reporter=verbose 2>&1 | tail -50`\n"
        "Rapporte le nombre de tests passés / échoués."
    ),
    "source-guards": (
        "Cherche les violations source-guard dans le frontend (pas de business logic côté FE) :\n"
        "1. Cherche les facteurs CO₂ électriques hardcodés dans frontend/src/ (.tsx, .jsx).\n"
        "2. `grep -rn '\\* 7500' frontend/src/ --include='*.tsx' --include='*.jsx'`\n"
        "3. `grep -rn '\\* 3750' frontend/src/ --include='*.tsx' --include='*.jsx'`\n"
        "4. Cherche les patterns de calcul de KPI dans le frontend.\n"
        "Rapporte chaque violation trouvée avec fichier et numéro de ligne."
    ),
    "constants": (
        "Vérifie les constantes réglementaires :\n"
        "1. Lis `backend/config/tarifs_reglementaires.yaml` et vérifie les valeurs TURPE / CTA / accise.\n"
        "2. Lis `backend/config/emission_factors.py` et confirme le facteur CO₂ élec ADEME.\n"
        "3. Vérifie qu'aucun fichier n'utilise 0.0569 comme facteur CO₂ (c'est un tarif TURPE, pas une émission).\n"
        "4. Vérifie les jalons DT dans `backend/regops/rules/tertiaire_operat.py` (-25% / -40% / -50%)."
    ),
    "seed": (
        "Vérifie la stabilité du seed HELIOS :\n"
        "1. Cherche les fichiers seed (`grep -rn 'HELIOS' backend/ --include='*.py' -l`).\n"
        "2. Vérifie que RNG=42 est utilisé pour la reproductibilité.\n"
        "3. Vérifie que le seed définit les sites attendus (liste canonique).\n"
        "4. Vérifie la cohérence de `ref_year` pour le baseline DT."
    ),
}


async def run_qa_audit(scope: str = "full") -> dict:
    """
    Lance un audit QA via le Claude Agent SDK.

    Args:
        scope: "full" | "tests" | "source-guards" | "constants" | "seed"

    Returns:
        dict avec {status, findings, summary, scope}

    Raises:
        ValueError: scope inconnu.
    """
    if scope not in SCOPE_PROMPTS:
        raise ValueError(f"Scope inconnu '{scope}'. Valides : {', '.join(SCOPE_PROMPTS.keys())}")

    prompt = SCOPE_PROMPTS[scope]
    findings: list[str] = []
    summary: str = ""

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=QA_GUARDIAN_ALLOWED_TOOLS,
        disallowed_tools=QA_GUARDIAN_DISALLOWED_TOOLS,
        max_turns=AGENT_MAX_TURNS,
        cwd=str(REPO_ROOT),
        model=AGENT_MODEL,
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            summary = getattr(message, "result", None) or str(message)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    findings.append(block.text)

    summary_lower = summary.lower() if summary else ""
    is_green = any(
        kw in summary_lower
        for kw in ["0 failed", "all passed", "aucune violation", "tout est vert", "aucune régression"]
    )

    return {
        "status": "green" if is_green else "red",
        "findings": findings,
        "summary": summary,
        "scope": scope,
    }


if __name__ == "__main__":
    import sys

    scope_arg = sys.argv[1] if len(sys.argv) > 1 else "full"

    async def _main():
        return await run_qa_audit(scope_arg)

    result = anyio.run(_main)
    print(f"\n{'=' * 60}")
    print(f"QA Guardian — Scope: {result['scope']} — Status: {result['status']}")
    print(f"{'=' * 60}")
    print(result["summary"])
