r"""
PROMEOS — Source guard cross-stack TraceTooltip termId FE↔YAML (Sprint C-5 Phase 5.4, ADR-007 ext).

Anti-régression cardinal post-livraison `coherence_globale.yaml` invariant 5
(`TRACETOOLTIP_TERMID_VALIDITY`, Sprint C-4 Phase 4.1) — implémentation runtime reportée
Sprint C-5 (cf. dette `D-Phase4-1-TraceTooltip-TermId-SG-Cross-Stack-001` P1).

Risque sans ce SG : typo `termId` silencieuse côté FE → tooltip ne s'affiche pas (fallback
enfants seuls), différenciateur R10 perdu sans alerte. UX silencieusement cassée.

Stratégie Option B (BE pytest) :
- Scan `frontend/src/**/*.jsx` depuis Python (path traversal cross-stack)
- Extraction regex `<TraceTooltip\s+termId="([^"]+)"` (forme statique uniquement, dynamique
  type `termId={dynamic}` skippée — non auditable statiquement)
- Test cardinal : 100% match termId FE ⊆ terms.keys() YAML SoT

Allowlist : aucune (tout termId FE statique DOIT exister dans YAML).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
_FRONTEND_SRC = _REPO_ROOT / "frontend" / "src"

# Pattern regex : <TraceTooltip ... termId="VALUE" ...>
# - `\s+` permet des attrs entre `<TraceTooltip` et `termId`
# - `[^"]+` capture le termId (interdiction de quotes imbriquées)
_TERMID_PATTERN = re.compile(r'<TraceTooltip\b[^>]*\btermId="([^"]+)"')


def _scan_frontend_termids() -> dict[str, set[Path]]:
    """Scan FE files, return mapping termId -> set of files where used.

    Inclut .jsx + .js. Skip __tests__ (les tests acceptent des termIds factices
    pour vérifier le composant, pas les vraies invariants doctrinaux).
    """
    if not _FRONTEND_SRC.exists():
        pytest.skip(f"Frontend src absent : {_FRONTEND_SRC}")

    termid_to_files: dict[str, set[Path]] = {}
    for ext in ("*.jsx", "*.js"):
        for fpath in _FRONTEND_SRC.rglob(ext):
            # Skip tests folder (fixtures avec termIds factices)
            if "__tests__" in fpath.parts or "test" in fpath.stem.lower():
                continue
            try:
                content = fpath.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for match in _TERMID_PATTERN.finditer(content):
                termid = match.group(1)
                termid_to_files.setdefault(termid, set()).add(fpath)
    return termid_to_files


def test_sg_tracetooltip_termid_01_all_fe_termids_exist_in_yaml():
    """SG_TRACETOOLTIP_01 (CARDINAL invariant 5) : tous les termId FE statiques
    DOIVENT exister dans `sources_reglementaires.yaml::terms.keys()`.

    Si un FE référence `<TraceTooltip termId="UNKNOWN_TERM">` :
    - le tooltip ne s'affiche pas (fallback enfants seuls)
    - différenciateur R10 (traçabilité légale) perdu silencieusement
    - UX cassée non détectée à la collection

    Ce SG fail-fast bloque le merge si typo détectée.
    """
    from config.regulatory_sources_loader import list_all_term_ids, reload_regulatory_sources

    reload_regulatory_sources()
    yaml_termids = set(list_all_term_ids())
    assert yaml_termids, "YAML sources_reglementaires.yaml ne contient aucun terme — anomalie loader."

    fe_termids_map = _scan_frontend_termids()

    if not fe_termids_map:
        pytest.skip("Aucune utilisation statique de <TraceTooltip termId='...'> détectée — skip SG.")

    fe_termids = set(fe_termids_map.keys())
    missing_in_yaml = fe_termids - yaml_termids

    if missing_in_yaml:
        # Diagnostic : pour chaque termId manquant, lister les fichiers FE
        diag_lines = []
        for termid in sorted(missing_in_yaml):
            files = fe_termids_map[termid]
            files_rel = [str(f.relative_to(_REPO_ROOT)) for f in sorted(files)]
            diag_lines.append(f"  - '{termid}' utilisé dans : {', '.join(files_rel)}")

        pytest.fail(
            f"SG_TRACETOOLTIP_01 FAIL : {len(missing_in_yaml)} termId(s) FE absent(s) du YAML SoT :\n"
            + "\n".join(diag_lines)
            + "\n\nAction : ajouter ces termes à `backend/config/sources_reglementaires.yaml::terms` "
            "OU corriger la typo côté FE.\n"
            "Référence : invariant 5 `TRACETOOLTIP_TERMID_VALIDITY` "
            "dans `backend/config/coherence_globale.yaml`."
        )


def test_sg_tracetooltip_termid_02_at_least_one_termid_used_fe():
    """SG_TRACETOOLTIP_02 : au moins 1 `<TraceTooltip termId='...'>` doit exister
    côté FE (différenciateur R10 effectivement déployé, pas seulement composant
    inutilisé).

    Si le composant TraceTooltip est livré mais 0 usage statique, R10 n'est pas
    réellement appliqué — flag pour vérification.
    """
    fe_termids_map = _scan_frontend_termids()
    assert len(fe_termids_map) >= 1, (
        "SG_TRACETOOLTIP_02 : aucun usage statique <TraceTooltip termId='...'> détecté FE.\n"
        "Différenciateur R10 (traçabilité légale) n'est pas effectivement déployé.\n"
        "Si suppression intentionnelle du composant, retirer aussi ce SG."
    )
