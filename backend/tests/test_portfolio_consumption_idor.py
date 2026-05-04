"""
PROMEOS — Mini-sprint sécurité IDOR Portfolio Consumption (CWE-284) — fix 2026-05-04.

Vérifie que les 2 endpoints portfolio consumption sont org-scopés :
- GET /api/portfolio/consumption/summary
- GET /api/portfolio/consumption/sites

Avant le fix : `q = db.query(Site).filter(Site.actif == True)` SANS filtre
`EntiteJuridique.organisation_id == org_id`. Tout user authentifié pouvait
récupérer les KPIs agrégés et top-sites de TOUTE organisation via
`portefeuille_id` ou `site_ids` query param.

Après le fix : JOIN Site → Portefeuille → EntiteJuridique → org_id strict +
`_check_portfolio_belongs_to_org` sur le query param `portefeuille_id`.

Couverture (4 tests cross-org + 2 tests own-org) :
- test_summary_cross_org_portefeuille_returns_403
- test_sites_cross_org_portefeuille_returns_403
- test_summary_cross_org_site_ids_silently_filtered
- test_sites_cross_org_site_ids_silently_filtered
- test_summary_own_org_succeeds (DEMO_MODE → org HELIOS)
- test_sites_own_org_succeeds (DEMO_MODE → org HELIOS)

Symétrique à `test_meters_endpoints_org_scoping_idor.py` (mini-sprint IDOR meters
Sprint C-2 commit 0ec2743a). PROMEOS-SEC-2026-001 + PROMEOS-SEC-2026-002.
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture
def foreign_portefeuille():
    """Crée un Portefeuille dans une org SÉPARÉE de la demo HELIOS courante.

    Le portefeuille_id retourné doit être inaccessible depuis l'org HELIOS
    (résolue par DEMO_MODE / DemoState). Cleanup ordre inverse en teardown.
    """
    from database import SessionLocal
    from models import EntiteJuridique, Organisation, Portefeuille, Site

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    created_ids: dict = {}

    try:
        org = Organisation(
            nom=f"Foreign Org Portfolio IDOR {suffix}",
            siren=f"77800{suffix[:4]}",
        )
        db.add(org)
        db.flush()
        created_ids["org"] = org.id

        ej = EntiteJuridique(
            nom=f"Foreign EJ Portfolio IDOR {suffix}",
            siren=f"77800{suffix[:4]}",
            organisation_id=org.id,
        )
        db.add(ej)
        db.flush()
        created_ids["ej"] = ej.id

        pf = Portefeuille(
            nom=f"Foreign PF Portfolio IDOR {suffix}",
            entite_juridique_id=ej.id,
        )
        db.add(pf)
        db.flush()
        created_ids["pf"] = pf.id

        site = Site(
            nom=f"Foreign Site Portfolio IDOR {suffix}",
            type="bureau",
            portefeuille_id=pf.id,
            actif=True,
        )
        db.add(site)
        db.flush()
        created_ids["site"] = site.id

        db.commit()
        yield {"portefeuille_id": pf.id, "site_id": site.id}
    finally:
        try:
            for cls, key in [
                (Site, "site"),
                (Portefeuille, "pf"),
                (EntiteJuridique, "ej"),
                (Organisation, "org"),
            ]:
                if key in created_ids:
                    obj = db.query(cls).filter(cls.id == created_ids[key]).first()
                    if obj:
                        db.delete(obj)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


# ─── 4 tests cross-org → IDOR bloqué ────────────────────────────────────────


def test_summary_cross_org_portefeuille_returns_403(client, foreign_portefeuille):
    """SG_PORTFOLIO_IDOR_01 : portefeuille_id d'autre org sur /summary → 403."""
    resp = client.get(
        "/api/portfolio/consumption/summary",
        params={"portefeuille_id": foreign_portefeuille["portefeuille_id"]},
    )
    assert resp.status_code == 403, (
        f"IDOR non bloqué : GET summary cross-org renvoie {resp.status_code} au lieu de 403. Body: {resp.text}"
    )


def test_sites_cross_org_portefeuille_returns_403(client, foreign_portefeuille):
    """SG_PORTFOLIO_IDOR_02 : portefeuille_id d'autre org sur /sites → 403."""
    resp = client.get(
        "/api/portfolio/consumption/sites",
        params={"portefeuille_id": foreign_portefeuille["portefeuille_id"]},
    )
    assert resp.status_code == 403, (
        f"IDOR non bloqué : GET sites cross-org renvoie {resp.status_code} au lieu de 403. Body: {resp.text}"
    )


def test_summary_cross_org_site_ids_silently_filtered(client, foreign_portefeuille):
    """SG_PORTFOLIO_IDOR_03 : site_ids cross-org silently filtered (JOIN org-scope = pas leak).

    Aucun site cross-org ne doit apparaître dans la réponse, et la couverture
    sites_total ne doit pas inclure les sites étrangers.
    """
    resp = client.get(
        "/api/portfolio/consumption/summary",
        params={"site_ids": str(foreign_portefeuille["site_id"])},
    )
    assert resp.status_code == 200, (
        f"GET summary site_ids cross-org devrait être OK (silent filter), code={resp.status_code}"
    )
    data = resp.json()
    # Site cross-org doit être filtré silencieusement (JOIN org-scope vide)
    assert data["coverage"]["sites_total"] == 0, (
        f"Cross-org site leak : sites_total={data['coverage']['sites_total']} (devait être 0). "
        f"Vérifier que le JOIN EntiteJuridique.organisation_id filtre bien."
    )


def test_sites_cross_org_site_ids_silently_filtered(client, foreign_portefeuille):
    """SG_PORTFOLIO_IDOR_04 : site_ids cross-org silently filtered sur /sites."""
    resp = client.get(
        "/api/portfolio/consumption/sites",
        params={"site_ids": str(foreign_portefeuille["site_id"])},
    )
    assert resp.status_code == 200, (
        f"GET sites site_ids cross-org devrait être OK (silent filter), code={resp.status_code}"
    )
    data = resp.json()
    foreign_ids = {foreign_portefeuille["site_id"]}
    leaked = [r for r in data["rows"] if r["site_id"] in foreign_ids]
    assert not leaked, (
        f"Cross-org site leak : {len(leaked)} sites étrangers retournés. "
        f"Site IDs étrangers : {foreign_ids}, rows : {[r['site_id'] for r in data['rows']]}"
    )


# ─── 2 tests own-org → succès non-régression DEMO_MODE ──────────────────────


def test_summary_own_org_succeeds(client):
    """SG_PORTFOLIO_IDOR_05 : DEMO_MODE résout org HELIOS → /summary 200."""
    resp = client.get(
        "/api/portfolio/consumption/summary",
        params={"from": "2025-01-01", "to": "2025-12-31"},
    )
    assert resp.status_code == 200, f"GET summary DEMO_MODE devrait réussir, code={resp.status_code} body={resp.text}"
    data = resp.json()
    assert "totals" in data
    assert "coverage" in data


def test_sites_own_org_succeeds(client):
    """SG_PORTFOLIO_IDOR_06 : DEMO_MODE résout org HELIOS → /sites 200 (non-régression)."""
    resp = client.get(
        "/api/portfolio/consumption/sites",
        params={"from": "2025-01-01", "to": "2025-12-31"},
    )
    assert resp.status_code == 200, f"GET sites DEMO_MODE devrait réussir, code={resp.status_code} body={resp.text}"
    data = resp.json()
    assert "rows" in data
    assert "total" in data
