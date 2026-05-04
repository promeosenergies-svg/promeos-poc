"""
PROMEOS — Source guard meter endpoints org-scoping (CWE-639 IDOR mitigation).

Mini-sprint sécurité 2026-05-04 : suite à l'audit security-auditor Phase 4.5d
Sprint C-2 (finding High `PROMEOS-SEC-2026-041`), les 3 endpoints meter du
module patrimoine ont été corrigés pour appliquer org-scoping via
`_load_meter_with_org_check`.

Ce source-guard prévient toute régression future :
- SG_METER_ORG_01 : tout handler @router.* sur `/meters/{meter_id}` DOIT appeler
  `_load_meter_with_org_check(db, meter_id, org_id)` avant l'opération métier.
- SG_METER_ORG_02 : helper `_load_meter_with_org_check` doit exister dans
  `routes/patrimoine/_helpers.py` avec la signature attendue.
- SG_METER_ORG_03 : pattern interdit `@router.<verb>("/meters/{meter_id}/...")`
  sans `_load_meter_with_org_check` dans le corps du handler.

Pattern repo : readFileSync + regex (env Python).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SITES_ROUTE_PATH = _BACKEND_ROOT / "routes" / "patrimoine" / "sites.py"
_HELPERS_PATH = _BACKEND_ROOT / "routes" / "patrimoine" / "_helpers.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_sg_meter_org_01_helper_exists_with_correct_signature():
    """Helper `_load_meter_with_org_check(db, meter_id, org_id)` doit exister."""
    content = _read(_HELPERS_PATH)
    assert "def _load_meter_with_org_check(" in content, (
        "Helper _load_meter_with_org_check absent de routes/patrimoine/_helpers.py — "
        "régression sécurité IDOR (CWE-639) introduite."
    )
    # Signature : (db: Session, meter_id: int, org_id: int)
    assert re.search(
        r"def\s+_load_meter_with_org_check\s*\(\s*db\s*:\s*Session\s*,\s*meter_id\s*:\s*int\s*,\s*org_id\s*:\s*int",
        content,
    ), "Signature _load_meter_with_org_check incorrecte (attendu: db, meter_id, org_id)."
    # Doit retourner 404 fail-closed
    assert "status_code=404" in content or "status_code=404" in content, (
        "Helper doit raise HTTPException(404) si meter ∉ org."
    )


def test_sg_meter_org_02_helper_uses_join_chain_to_organisation():
    """Helper doit JOIN Site → Portefeuille → EJ → Organisation pour scoping."""
    content = _read(_HELPERS_PATH)
    # Extraire le bloc du helper pour vérifier le pattern JOIN
    match = re.search(
        r"def\s+_load_meter_with_org_check\([^)]+\)[^:]*:[\s\S]+?(?=\ndef\s|\Z)",
        content,
    )
    assert match, "Bloc fonction _load_meter_with_org_check introuvable."
    body = match.group(0)
    assert ".join(Site," in body, "JOIN Site manquant."
    assert ".join(Portefeuille," in body, "JOIN Portefeuille manquant."
    assert ".join(EntiteJuridique," in body, "JOIN EntiteJuridique manquant."
    assert "EntiteJuridique.organisation_id == org_id" in body, (
        "Filtre organisation_id manquant — IDOR résiduel possible."
    )


def test_sg_meter_org_03_all_meter_handlers_call_org_check():
    """Tout handler @router.* `/meters/{meter_id}` doit appeler _load_meter_with_org_check."""
    content = _read(_SITES_ROUTE_PATH)

    # Pattern : @router.<verb>("...meters/{meter_id}...")
    handler_pattern = re.compile(
        r'@router\.(?:get|post|put|delete|patch)\(\s*"[^"]*meters/\{meter_id\}[^"]*"',
        re.IGNORECASE,
    )
    handler_matches = list(handler_pattern.finditer(content))
    assert handler_matches, (
        "Aucun handler @router /meters/{meter_id} détecté dans sites.py — "
        "test ineffectif. Vérifier le scope du source-guard."
    )

    # Pour chaque handler trouvé, extraire son corps (jusqu'au prochain @router ou EOF)
    # et vérifier qu'il appelle _load_meter_with_org_check.
    next_handler_pattern = re.compile(r"\n@router\.", re.IGNORECASE)

    offenders = []
    for match in handler_matches:
        start = match.start()
        # Trouver la fin du handler (prochain @router OU fin du fichier)
        next_handler = next_handler_pattern.search(content, match.end())
        end = next_handler.start() if next_handler else len(content)
        handler_body = content[start:end]

        if "_load_meter_with_org_check" not in handler_body:
            # Extraire la première ligne (le décorateur) pour identifier le handler offender
            first_line = handler_body.split("\n", 1)[0]
            offenders.append(first_line.strip())

    assert not offenders, (
        f"Handlers @router /meters/{{meter_id}} sans appel _load_meter_with_org_check "
        f"(IDOR CWE-639) :\n  - " + "\n  - ".join(offenders) + "\n"
        f"Ajouter `_load_meter_with_org_check(db, meter_id, org_id)` après "
        f"`org_id = _get_org_id(request, auth, db)`."
    )
