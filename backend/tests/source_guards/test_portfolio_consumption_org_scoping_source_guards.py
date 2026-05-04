"""
PROMEOS — Source guard portfolio consumption org-scoping (CWE-284 IDOR mitigation).

Mini-sprint sécurité 2026-05-04 (Phase C clôture) : suite à l'audit security-auditor
Phase 3.4d Sprint C-3 (finding `PROMEOS-SEC-2026-001/002`), les 2 endpoints
`/api/portfolio/consumption/*` ont été corrigés pour appliquer org-scoping strict
via JOIN `Site → Portefeuille → EntiteJuridique → organisation_id`.

Symétrique à `test_meter_endpoints_org_scoping_source_guards.py` (mini-sprint
IDOR meters Sprint C-2 commit 0ec2743a).

Ce source-guard prévient toute régression future :

- SG_PORTFOLIO_ORG_01 : tout handler `@router.*` dans `routes/portfolio.py` DOIT
  appeler `_get_org_id(request, auth, db)` avant la query Site.
- SG_PORTFOLIO_ORG_02 : tout handler DOIT appliquer un filtre
  `EntiteJuridique.organisation_id == org_id` sur la query Site (cohérence cross-pillar).
- SG_PORTFOLIO_ORG_03 : pattern interdit `db.query(Site).filter(Site.actif == True)` SANS
  JOIN ultérieur sur `EntiteJuridique` dans le même bloc.

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
_PORTFOLIO_ROUTE_PATH = _BACKEND_ROOT / "routes" / "portfolio.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_sg_portfolio_org_01_get_org_id_imported():
    """`_get_org_id` (helper org-scoping) doit être importé dans `routes/portfolio.py`."""
    content = _read(_PORTFOLIO_ROUTE_PATH)
    assert "_get_org_id" in content, (
        "Helper _get_org_id absent de routes/portfolio.py — régression sécurité IDOR "
        "(CWE-284 PROMEOS-SEC-2026-001/002) introduite."
    )
    # Doit aussi importer _check_portfolio_belongs_to_org pour valider le query param
    assert "_check_portfolio_belongs_to_org" in content, (
        "Helper _check_portfolio_belongs_to_org absent — query param portefeuille_id "
        "non validé contre l'org courante (IDOR résiduel)."
    )


def test_sg_portfolio_org_02_all_handlers_call_org_check():
    """Tout handler `@router.*` dans portfolio.py DOIT appeler `_get_org_id`."""
    content = _read(_PORTFOLIO_ROUTE_PATH)

    handler_pattern = re.compile(
        r"@router\.(?:get|post|put|delete|patch)\(",
        re.IGNORECASE,
    )
    handler_matches = list(handler_pattern.finditer(content))
    assert handler_matches, (
        "Aucun handler @router détecté dans routes/portfolio.py — test ineffectif. Vérifier le scope du source-guard."
    )

    next_handler_pattern = re.compile(r"\n@router\.", re.IGNORECASE)
    offenders = []
    for match in handler_matches:
        start = match.start()
        next_handler = next_handler_pattern.search(content, match.end())
        end = next_handler.start() if next_handler else len(content)
        handler_body = content[start:end]

        if "_get_org_id" not in handler_body:
            first_line = handler_body.split("\n", 2)[1].strip() if "\n" in handler_body else handler_body[:80]
            offenders.append(first_line)

    assert not offenders, (
        f"Handlers @router dans routes/portfolio.py sans appel _get_org_id "
        f"(IDOR CWE-284 PROMEOS-SEC-2026-001/002) :\n  - "
        + "\n  - ".join(offenders)
        + "\nAjouter `org_id = _get_org_id(request, auth, db)` au début du handler."
    )


def test_sg_portfolio_org_03_site_query_has_organisation_id_filter():
    """Toute requête `db.query(Site).filter(Site.actif == True)` DOIT être suivie
    d'un filtre `EntiteJuridique.organisation_id == org_id` dans le même handler."""
    content = _read(_PORTFOLIO_ROUTE_PATH)

    handler_pattern = re.compile(
        r"@router\.(?:get|post|put|delete|patch)\(",
        re.IGNORECASE,
    )
    handler_matches = list(handler_pattern.finditer(content))
    next_handler_pattern = re.compile(r"\n@router\.", re.IGNORECASE)

    offenders = []
    for match in handler_matches:
        start = match.start()
        next_handler = next_handler_pattern.search(content, match.end())
        end = next_handler.start() if next_handler else len(content)
        handler_body = content[start:end]

        # Si le handler interroge Site, il DOIT appliquer le filtre org via JOIN+EJ.organisation_id
        if "db.query(Site)" in handler_body:
            if "EntiteJuridique.organisation_id" not in handler_body:
                first_line = handler_body.split("\n", 2)[1].strip() if "\n" in handler_body else handler_body[:80]
                offenders.append(first_line)

    assert not offenders, (
        f"Handlers @router dans routes/portfolio.py qui interrogent `db.query(Site)` "
        f"SANS filtre `EntiteJuridique.organisation_id == org_id` (IDOR CWE-284) :\n  - "
        + "\n  - ".join(offenders)
        + "\nAjouter le JOIN cardinal :\n"
        + "  .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)\n"
        + "  .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)\n"
        + "  .filter(EntiteJuridique.organisation_id == org_id)"
    )
