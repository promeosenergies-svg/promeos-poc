"""
PROMEOS — Tests cardinaux Phase 8.1 Sprint C-8 — Lot REGOPS (3 P1 fixes).

Couvre :
- D-Sprint-C7-Scoring-OPERAT-S-CE-M2-Migration-001 P1 ARCH (ADR-020 Option C hybride)
- D-Sprint-C7-CGU-Referentiel-Central-001 P1 (référentiel central)
- D-Audit-Phase7-KPI-Mutation-Coherence-003 P1 CR (KPI canonique cross-vues)
"""

from __future__ import annotations


# ─── Fix 1 — ADR-020 Scoring OPERAT migration s_ce_m2 ───────────────────────


def test_phase81_resolve_surface_for_operat_export_uses_s_ce_m2_when_present():
    """Phase 8.1 cardinal ADR-020 Option C : helper privilégie s_ce_m2 quand renseigné."""
    from regops.operat_export_helpers import resolve_surface_for_operat_export

    class _FakeSite:
        s_ce_m2 = 1500.0
        tertiaire_area_m2 = 1200.0

    surface, label = resolve_surface_for_operat_export(_FakeSite())
    assert surface == 1500.0, "Phase 8.1 BLOQUANT : s_ce_m2 doit être utilisé en priorité"
    assert "art. 2-j" in label or "Surface CE" in label


def test_phase81_resolve_surface_falls_back_to_tertiaire_when_s_ce_null():
    """Phase 8.1 : fallback sur tertiaire_area_m2 si s_ce_m2 NULL (rétro-compat absolue)."""
    from regops.operat_export_helpers import resolve_surface_for_operat_export

    class _FakeSiteLegacy:
        s_ce_m2 = None
        tertiaire_area_m2 = 1200.0

    surface, label = resolve_surface_for_operat_export(_FakeSiteLegacy())
    assert surface == 1200.0
    assert "legacy" in label.lower() or "tertiaire" in label.lower()


def test_phase81_is_operat_v2_ready_returns_true_only_with_s_ce_m2():
    """Phase 8.1 : is_operat_v2_ready True UNIQUEMENT si s_ce_m2 explicite > 0."""
    from regops.operat_export_helpers import is_operat_v2_ready

    class _FakeSiteReady:
        s_ce_m2 = 1500.0

    class _FakeSiteLegacy:
        s_ce_m2 = None
        tertiaire_area_m2 = 1200.0

    assert is_operat_v2_ready(_FakeSiteReady()) is True
    assert is_operat_v2_ready(_FakeSiteLegacy()) is False


def test_phase81_data_quality_specs_includes_s_ce_m2_optional():
    """Phase 8.1 ADR-020 : data_quality_specs DT inclut s_ce_m2 dans 'optional'."""
    from regops.data_quality_specs import DATA_QUALITY_SPECS

    operat_spec = DATA_QUALITY_SPECS["tertiaire_operat"]
    assert "s_ce_m2" in operat_spec["optional"], (
        "Phase 8.1 BLOQUANT : s_ce_m2 doit être dans optional (ADR-020 Option C hybride)"
    )
    # Cardinal anti-régression : tertiaire_area_m2 reste critical (scoring SoT)
    assert "tertiaire_area_m2" in operat_spec["critical"], (
        "Phase 8.1 RÉGRESSION : tertiaire_area_m2 doit rester critical (scoring SoT inchangé)"
    )


# ─── Fix 2 — CGU referentiel central ────────────────────────────────────────


def test_phase81_cgu_referentiel_yaml_loads_versions():
    """Phase 8.1 cardinal : YAML cgu_referentiel.yaml chargeable + versions présentes."""
    from services.cgu_service import _load_cgu_referentiel, reload_cgu_referentiel

    reload_cgu_referentiel()
    config = _load_cgu_referentiel()

    assert "versions" in config
    assert len(config["versions"]) >= 2
    # Au moins 1 version 'actuel'
    actuel = [v for v in config["versions"] if v.get("statut") == "actuel"]
    assert len(actuel) >= 1


def test_phase81_get_current_cgu_version_returns_actuel():
    """Phase 8.1 : get_current_cgu_version retourne version 'actuel'."""
    from services.cgu_service import get_current_cgu_version

    current = get_current_cgu_version()
    assert current is not None
    assert isinstance(current, str)


def test_phase81_is_valid_cgu_version_accepts_known_versions():
    """Phase 8.1 : is_valid_cgu_version True pour 1.0 / 2.0 / 2.1.0 (rétro-compat tests)."""
    from services.cgu_service import is_valid_cgu_version

    for v in ("1.0", "2.0", "2.1.0", "0.9"):
        assert is_valid_cgu_version(v), f"Version {v} doit être acceptée (référentiel central)"


def test_phase81_is_valid_cgu_version_rejects_unknown():
    """Phase 8.1 cardinal CNIL : versions inconnues rejetées (preuve d'origine forte)."""
    from services.cgu_service import is_valid_cgu_version

    assert not is_valid_cgu_version("99.99.99")
    assert not is_valid_cgu_version("forged-version")
    assert not is_valid_cgu_version(None)
    assert not is_valid_cgu_version("")


def test_phase81_patch_org_consentement_rejects_unknown_cgu_version(app_client):
    """Phase 8.1 cardinal : PATCH endpoint refuse cgu_version hors référentiel central."""
    from models import Organisation

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhase81", siren="887780001", actif=True)
        db.add(org)
        db.commit()
        org_id = org.id
    finally:
        db.close()

    resp = client.patch(
        f"/api/organisations/{org_id}/consentement",
        json={"consentement_dataconnect_global": True, "cgu_version": "FORGED-99.99"},
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 422, (
        f"Phase 8.1 BLOQUANT : cgu_version forgée doit retourner 422 (validation pydantic), got {resp.status_code}"
    )


# ─── Fix 3 — KPI mutation cardinal bill_intelligence.py ─────────────────────


def test_phase81_kpi_total_economie_canonique_independant_filtres_user(app_client):
    """Phase 8.1 cardinal CR-003 : KPI calculé sur org_scope_q (vs base_q user-filtered).

    Avant fix : si filtre `code=R20`, base_q ne contient que R20 → KPI R19 = 0 trompeur.
    Après fix : KPI calculé indépendamment des filtres user → toujours canonique cross-vues.
    """
    from datetime import date

    from models import (
        BillAnomaly,
        EnergyInvoice,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhase81KPI", siren="887781111")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ81KPI", siren="887781111", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF81KPI", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S81KPI", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()
        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-81KPI",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        db.add(invoice)
        db.flush()
        # 1 R19 actionnable (resolved_at=None) avec actual_value=100
        db.add(BillAnomaly(invoice_id=invoice.id, code="R19", severity="warning", actual_value=100.0))
        # 1 R20 (sera filtré par user code=R20 query)
        db.add(BillAnomaly(invoice_id=invoice.id, code="R20", severity="critical", actual_value=15.0))
        db.commit()
        org_id = org.id
    finally:
        db.close()

    # Cas 1 : filtre user code=R20 → KPI canonique R19 = 100 (indépendant filtre user)
    resp = client.get(
        "/api/bill-intelligence/anomalies?code=R20",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["kpi_total_economie_potentielle_eur"] == 100.0, (
        "Phase 8.1 BLOQUANT KPI mutation : KPI doit rester canonique 100€ R19 même quand filtre code=R20"
    )

    # Cas 2 : pas de filtre → KPI identique (cross-vues stable)
    resp2 = client.get(
        "/api/bill-intelligence/anomalies",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["kpi_total_economie_potentielle_eur"] == 100.0


def test_phase81_kpi_excludes_resolved_r19(app_client):
    """Phase 8.1 enrichissement bill-intelligence audit : KPI exclut anomalies résolues."""
    from datetime import date, datetime, timezone

    from models import (
        BillAnomaly,
        EnergyInvoice,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org = Organisation(nom="OrgPhase81Resolved", siren="887781222")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ81Resolved", siren="887781222", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF81Resolved", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S81Resolved", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()
        invoice1 = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-81Res-1",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        invoice2 = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-81Res-2",
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
        )
        db.add_all([invoice1, invoice2])
        db.flush()
        # 1 R19 actionnable (invoice 1)
        db.add(BillAnomaly(invoice_id=invoice1.id, code="R19", severity="warning", actual_value=50.0))
        # 1 R19 résolue (invoice 2) — doit être exclue du KPI (UNIQUE invoice_id+code Phase 5.8 G3)
        db.add(
            BillAnomaly(
                invoice_id=invoice2.id,
                code="R19",
                severity="warning",
                actual_value=200.0,
                resolved_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        org_id = org.id
    finally:
        db.close()

    resp = client.get(
        "/api/bill-intelligence/anomalies",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    # KPI = 50 (actionnable) seulement, pas 250 (cumul résolue + actionnable)
    assert body["kpi_total_economie_potentielle_eur"] == 50.0, (
        "Phase 8.1 enrichissement : KPI doit exclure résolues (=montant restant à reclaim CFO)"
    )
