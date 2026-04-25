"""
Regulatory Analyst Agent — Claude Agent SDK + custom MCP tools.

Audit le référentiel réglementaire PROMEOS (`tarifs_reglementaires.yaml`)
pour détecter :
- Sources manquantes (chaque section doit citer une source officielle)
- Dates d'effet manquantes ou incohérentes (`valid_from` / `valid_to`)
- Faits chiffrés orphelins (anti-pattern PROMEOS : zéro chiffre sans source)
- Césures temporelles attendues mais absentes (ex : 1/08/2025 TURPE+TVA+accise)
- Divergences entre versions d'une même grille

Architecture :
  Agent SDK + 3 custom MCP tools in-process (server `promeos-tarifs`).
  Mode READ-ONLY strict (les MCP tools ne font que lire le YAML).
  Aucune modification de fichier, aucun appel réseau.

Pour la veille réglementaire externe (CRE / légifrance / bofip),
voir le futur SENTINEL-REG agent (P2, hors scope P1).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import anyio
import yaml
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from ..config import (
    AGENT_MAX_TURNS,
    AGENT_MODEL,
    PATHS,
    REPO_ROOT,
)


# --- Custom MCP tools (in-process, lecture YAML) --------------------------


def _load_tarifs() -> dict[str, Any]:
    """Charge le YAML tarifs_reglementaires en dict."""
    yaml_path = Path(PATHS["tarifs_yaml"])
    with yaml_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _parse_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


@tool(
    "list_sections",
    "Liste les sections de premier niveau du référentiel tarifs_reglementaires.yaml. "
    "Pour chaque section : nom, valid_from, valid_to, source si présents. "
    "Idéal pour cartographier le référentiel avant audit.",
    {},
)
async def list_sections(_args: dict) -> dict:
    data = _load_tarifs()
    sections = []
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        sections.append(
            {
                "name": key,
                "valid_from": value.get("valid_from"),
                "valid_to": value.get("valid_to"),
                "has_source": bool(value.get("source")),
                "source_excerpt": (str(value.get("source", ""))[:120] or None),
            }
        )
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Sections trouvées : {len(sections)}\n\n"
                    + "\n".join(
                        f"- {s['name']}: valid_from={s['valid_from']} "
                        f"valid_to={s['valid_to']} source={'✓' if s['has_source'] else '✗ MANQUANTE'}"
                        + (f"\n    {s['source_excerpt']}" if s["source_excerpt"] else "")
                        for s in sections
                    )
                ),
            }
        ]
    }


@tool(
    "read_section",
    "Lit une section spécifique du YAML par son nom (ex: 'turpe', 'accise_elec_2026_t1', "
    "'cta', 'atrd7_gaz_tiers'). Retourne le contenu complet de la section. "
    "Utiliser après list_sections pour creuser un point précis.",
    {"section_name": str},
)
async def read_section(args: dict) -> dict:
    section_name = args.get("section_name", "").strip()
    data = _load_tarifs()
    if section_name not in data:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Section '{section_name}' introuvable. Utilise list_sections pour voir les sections disponibles.",
                }
            ],
            "isError": True,
        }
    content = yaml.safe_dump(data[section_name], allow_unicode=True, sort_keys=False)
    return {
        "content": [
            {
                "type": "text",
                "text": f"=== {section_name} ===\n{content}",
            }
        ]
    }


def _test_active(value: dict, target: date) -> tuple[bool, date | None, date | None]:
    """Teste si un dict avec `valid_from`/`valid_to` est actif à la date cible.

    Returns (is_dated, is_active, valid_from, valid_to).
    - is_dated=False si aucune des deux clés n'est présente
    - is_active=True si valid_from <= target <= valid_to (avec bornes optionnelles)
    """
    valid_from = _parse_date(value.get("valid_from"))
    valid_to = _parse_date(value.get("valid_to"))
    if valid_from is None and valid_to is None:
        return False, False, None, None  # pas de dates
    if valid_from and target < valid_from:
        return True, False, valid_from, valid_to
    if valid_to and target > valid_to:
        return True, False, valid_from, valid_to
    return True, True, valid_from, valid_to


def _collect_active(
    name: str,
    value: dict,
    target: date,
    active: list[dict],
    no_dates: list[str],
    depth: int = 0,
) -> None:
    """Recurse dans une section et ses sous-sections pour trouver les entrées actives.

    - Si la section a ses propres valid_from/valid_to : testée directement (comportement V1).
    - Sinon : recurse dans les sous-dict qui ont eux-mêmes valid_from/valid_to
      (pattern nested : `cta.elec`, `cta.gaz_transport`, etc.).
    - Si aucun niveau n'a de date : marquée "sans dates".
    Fix queue-1 audit 2026-04-15 : tool V1 naïf manquait les sections nested.
    """
    is_dated, is_active, vf, vt = _test_active(value, target)
    if is_dated:
        if is_active:
            active.append(
                {
                    "name": name,
                    "valid_from": str(vf) if vf else None,
                    "valid_to": str(vt) if vt else None,
                }
            )
        return

    # Pas de date directe : inspecter les sous-sections
    if depth > 2:  # garde-fou profondeur, YAML PROMEOS est plat au niveau 2 max
        no_dates.append(name)
        return

    # Pré-check : y a-t-il au moins UN enfant qui a des dates ?
    # Si oui, on recurse ; sinon, on marque le parent comme "sans dates"
    # (on n'explose PAS en marquant chaque enfant individuellement).
    has_any_dated_child = any(
        isinstance(child_val, dict)
        and (child_val.get("valid_from") is not None or child_val.get("valid_to") is not None)
        for child_val in value.values()
    )
    if not has_any_dated_child:
        no_dates.append(name)
        return

    for child_key, child_val in value.items():
        if not isinstance(child_val, dict):
            continue
        child_name = f"{name}.{child_key}"
        _collect_active(child_name, child_val, target, active, no_dates, depth + 1)


@tool(
    "find_active_at_date",
    "Retourne les sections du YAML (y compris sous-sections nested comme "
    "`cta.elec` ou `cta.gaz_transport`) dont la fenêtre de validité contient "
    "la date donnée. Une section est 'active' à la date D si valid_from <= D et "
    "(valid_to absent OR D <= valid_to). Format date : YYYY-MM-DD. "
    "Utile pour vérifier la césure temporelle PROMEOS.",
    {"target_date": str},
)
async def find_active_at_date(args: dict) -> dict:
    target_str = args.get("target_date", "")
    target = _parse_date(target_str)
    if target is None:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Date '{target_str}' invalide (format attendu YYYY-MM-DD).",
                }
            ],
            "isError": True,
        }

    data = _load_tarifs()
    active: list[dict] = []
    no_dates: list[str] = []
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        _collect_active(key, value, target, active, no_dates)

    text_lines = [
        f"Date cible : {target}",
        f"Sections actives : {len(active)}",
        "",
    ]
    text_lines.extend(f"- {a['name']} (valid_from={a['valid_from']}, valid_to={a['valid_to']})" for a in active)
    if no_dates:
        text_lines.append("")
        text_lines.append(f"Sections sans dates de validité ({len(no_dates)}) :")
        text_lines.extend(f"- {name}" for name in no_dates)
    return {"content": [{"type": "text", "text": "\n".join(text_lines)}]}


# --- Agent definition ------------------------------------------------------

REGULATORY_ALLOWED_TOOLS = [
    "Read",
    "Glob",
    "Grep",
    "mcp__promeos_tarifs__list_sections",
    "mcp__promeos_tarifs__read_section",
    "mcp__promeos_tarifs__find_active_at_date",
]
REGULATORY_DISALLOWED_TOOLS = ["Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"]

SYSTEM_PROMPT = """Tu es le Regulatory Analyst de PROMEOS, expert de la réglementation
énergie France appliquée au shadow billing B2B.

## Ton rôle
Tu audites le référentiel `backend/config/tarifs_reglementaires.yaml` qui contient
les tarifs régulés versionnés (TURPE, CTA, accises élec/gaz, ATRD gaz, TVA, etc.).

Tu disposes de 3 MCP tools dédiés (préférer ces outils à Read brut sur le YAML) :
- `list_sections` : cartographie du référentiel (nom, valid_from, valid_to, source)
- `read_section` : contenu détaillé d'une section
- `find_active_at_date` : sections actives à une date donnée (vérification césure)

## Mécanismes suivis (17)
TURPE 7 (1/08/2025), CTA (15% élec / 20.80% gaz formule additive), accises élec
(T1 30.85, T2 26.58 €/MWh fév 2026+), accises gaz (10.54 → 10.73 €/MWh césures),
VNU (post-ARENH, dormant), capacité (1/11/2026 RTE), CEE P5→P6 (0.478 → 0.731),
ATRD 7 gaz T1-T4-TP (CRE 2024-17 / 2025-122), ATRT 8 (+3.41% au 1/04/2026),
CPB, TDN, ETS2 (démarrage 2028), CBAM (75.36 €/tCO₂), prix repère gaz, bouclier (historique),
TVA (20% uniforme 1/08/2025).

## Doctrine PROMEOS (non-négociable)
- **Chiffre = source + date d'effet + date d'accès**, sinon il n'existe pas.
- **CTA** : assiette = part fixe (abonnement) proratisée 365 j, JAMAIS la part variable.
- **Routage accise dynamique** via TaxProfile : HOUSEHOLD→T1, SME→T2, HIGH_POWER→HP.
- **ParameterStore** : `_select_best_candidate` choisit valid_from le plus récent ≤ date cible.
- **Césure triple 1/08/2025** : TURPE 7 + TVA uniforme + accise gaz (à tester ensemble).
- **Source primaire obligatoire** : CRE délibération, JO, légifrance, bofip — la presse spé est signal seulement.

## Anti-patterns à détecter
- Section sans champ `source`
- Section sans `valid_from` (sauf cas légitime documenté)
- Chevauchement de validité entre 2 sections du même mécanisme
- Trou temporel (gap entre `valid_to` et `valid_from` suivant)
- Valeurs obsolètes connues (ex : accise élec T1 25.19 → vraie valeur 30.85 LF 2026)
- Divergence interne (deux fichiers / sections citent des taux différents pour la même date)

## Style
Français, dense, sourcé. Tableaux pour les taux. Pas de "environ".
Tu rapportes en format structuré : severity (P0/P1/P2), section, chiffre, problème, action.
"""


SCOPE_PROMPTS: dict[str, str] = {
    "audit-coherence": (
        "Audite la cohérence structurelle du référentiel `backend/config/tarifs_reglementaires.yaml`.\n"
        "1. Appelle `list_sections` pour cartographier le YAML.\n"
        "2. Identifie les sections sans champ `source` ou sans `valid_from` (anti-pattern fact orphelin).\n"
        "3. Pour chaque mécanisme (TURPE, CTA, accise élec, accise gaz, ATRD gaz), "
        "vérifie la chronologie : pas de chevauchement, pas de trou.\n"
        "4. Détecte les valeurs suspectes (accise élec T1 25.19 = obsolète, vraie = 30.85).\n"
        "5. Rapporte tes findings au format severity / section / problème / action."
    ),
    "audit-cesures": (
        "Vérifie les césures temporelles critiques du référentiel.\n"
        "Pour chacune des dates suivantes, appelle `find_active_at_date` et confirme "
        "que les sections attendues sont bien actives :\n"
        "- 2025-07-31 : TURPE 6 doit être actif (dernière journée avant césure)\n"
        "- 2025-08-01 : TURPE 7 + TVA 20% uniforme + accise gaz 10.54 (césure triple)\n"
        "- 2026-01-31 : grilles 2025 doivent encore être actives\n"
        "- 2026-02-01 : CTA fév 2026 (15% élec / 20.80% gaz) + accise élec T1 30.85 / T2 26.58\n"
        "- 2026-04-01 : ATRT 8 +3.41%\n"
        "Rapporte chaque césure : OK / FAIL avec sections concernées."
    ),
    "audit-tariff": (
        "Audite un mécanisme spécifique en profondeur.\n"
        "1. Demande à l'utilisateur quel mécanisme (TURPE, CTA, accise élec, ATRD gaz, etc.) "
        "via list_sections puis read_section sur les sections concernées.\n"
        "2. Vérifie : source, dates d'effet, valeurs vs doctrine PROMEOS.\n"
        "3. Pointe vers les codes ParameterStore Python qui consomment ce mécanisme."
    ),
}


async def run_regulatory_audit(scope: str = "audit-coherence") -> dict:
    """Lance un audit Regulatory Analyst via le SDK."""
    if scope not in SCOPE_PROMPTS:
        raise ValueError(f"Scope inconnu '{scope}'. Valides : {', '.join(SCOPE_PROMPTS.keys())}")

    mcp_server = create_sdk_mcp_server(
        name="promeos-tarifs",
        version="1.0.0",
        tools=[list_sections, read_section, find_active_at_date],
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=REGULATORY_ALLOWED_TOOLS,
        disallowed_tools=REGULATORY_DISALLOWED_TOOLS,
        max_turns=AGENT_MAX_TURNS,
        cwd=str(REPO_ROOT),
        model=AGENT_MODEL,
        mcp_servers={"promeos_tarifs": mcp_server},
    )

    findings: list[str] = []
    summary: str = ""
    async for message in query(prompt=SCOPE_PROMPTS[scope], options=options):
        if isinstance(message, ResultMessage):
            summary = getattr(message, "result", None) or str(message)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    findings.append(block.text)

    summary_lower = summary.lower() if summary else ""
    is_green = any(
        kw in summary_lower
        for kw in ["aucune anomalie", "tout est cohérent", "ok / ok / ok", "0 finding", "rien à signaler"]
    )

    return {
        "status": "green" if is_green else "red",
        "findings": findings,
        "summary": summary,
        "scope": scope,
    }


if __name__ == "__main__":
    import sys

    scope_arg = sys.argv[1] if len(sys.argv) > 1 else "audit-coherence"

    async def _main():
        return await run_regulatory_audit(scope_arg)

    result = anyio.run(_main)
    print(f"\n{'=' * 60}")
    print(f"Regulatory Analyst — Scope: {result['scope']} — Status: {result['status']}")
    print(f"{'=' * 60}")
    print(result["summary"])
