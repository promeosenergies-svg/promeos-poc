"""
PROMEOS — Tests cardinaux Phase 8.4 Sprint C-8 Lot 3 — P1 CR+QA+BI fixés.

Couvre :
- D-Audit-C8-Hash-Key-Siret-Redundant-009 P1 CR (déduplication logique _is_hash_key)
- D-Audit-C8-OPERAT-VA-URL-Placeholder-010 P1 CR (URL placeholder JORFTEXT remplacé)
- D-Audit-C8-KPI-Semantic-Renaming-013 P1 BI (KPI renommé `kpi_vnu_dormant_reclaim_eur`)
- D-Audit-C8-Bilan-Lendemain-Drift-011 P1 QA (BILAN claim corrigé)
- D-Audit-C8-Bilan-Comptage-SG-012 P1 QA (BILAN comptage SG/tests corrigé)
"""

from __future__ import annotations

from pathlib import Path


# ─── Fix P1-CR-009 — _is_hash_key déduplication ─────────────────────────────


def test_phase84_lot3_is_hash_key_dedup_no_redundant_logic():
    """Phase 8.4 Lot 3 : `_is_hash_key` utilise UNIQUEMENT `pattern in lk` (sans pattern==lk redondant)."""
    import inspect

    from services.audit_log_service import _is_hash_key

    src = inspect.getsource(_is_hash_key)
    # Anti-pattern : `pattern == lk or pattern in lk` (redondant)
    assert "pattern == lk or pattern in lk" not in src, (
        "Phase 8.4 Lot 3 BLOQUANT CR : redondance logique `pattern == lk or pattern in lk` encore présente"
    )
    # Marqueur dette Lot 3 fix
    assert "D-Audit-C8-Hash-Key-Siret-Redundant-009" in src


def test_phase84_lot3_is_hash_key_still_works_post_dedup():
    """Phase 8.4 Lot 3 : comportement préservé post déduplication (pattern in lk suffit)."""
    from services.audit_log_service import _is_hash_key

    # Cas vrais positifs préservés
    assert _is_hash_key("siret") is True
    assert _is_hash_key("siren") is True
    assert _is_hash_key("prm") is True
    assert _is_hash_key("pce") is True
    assert _is_hash_key("usage_point_id") is True
    assert _is_hash_key("siret_etablissement") is True  # substring conservé
    assert _is_hash_key("user_prm") is True

    # Cas Phase 8.3 anti-régression (code exact match)
    assert _is_hash_key("code") is True
    assert _is_hash_key("period_code") is False  # exact match strict
    assert _is_hash_key("error_code") is False


# ─── Fix P1-CR-010 — URL placeholder ────────────────────────────────────────


def test_phase84_lot3_operat_va_no_xxx_url_placeholder():
    """Phase 8.4 Lot 3 : `operat_valeurs_absolues.yaml` ne contient plus URL placeholder `xxx`."""
    yaml_path = Path(__file__).parent.parent / "config" / "operat_valeurs_absolues.yaml"
    content = yaml_path.read_text(encoding="utf-8")

    # Pas de `JORFTEXTxxx` runtime (commentaires de transition tolérés)
    runtime_lines = [
        line
        for line in content.split("\n")
        if "JORFTEXT" in line and "xxx" in line and not line.lstrip().startswith("#")
    ]
    assert not runtime_lines, "Phase 8.4 Lot 3 BLOQUANT CR : URL placeholder `xxx` runtime résiduel :\n" + "\n".join(
        runtime_lines
    )

    # Marqueur fix présent
    assert "D-Audit-C8-OPERAT-VA-URL-Placeholder-010" in content
    # url_todo cardinal présent (vs URL falsifiée)
    assert "url_todo" in content


# ─── Fix P1-BI-013 — KPI renommage ──────────────────────────────────────────


def test_phase84_lot3_kpi_renamed_vnu_dormant_reclaim_eur(app_client):
    """Phase 8.4 Lot 3 cardinal BI : endpoint expose `kpi_vnu_dormant_reclaim_eur` (sémantique CFO claire)."""
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
        org = Organisation(nom="OrgPhase84Lot3KPI", siren="887840005")
        db.add(org)
        db.flush()
        ej = EntiteJuridique(nom="EJ84Lot3", siren="887840005", organisation_id=org.id)
        db.add(ej)
        db.flush()
        pf = Portefeuille(nom="PF84Lot3", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        site = Site(nom="S84Lot3", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
        db.add(site)
        db.flush()
        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-84Lot3",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        db.add(invoice)
        db.flush()
        db.add(BillAnomaly(invoice_id=invoice.id, code="R19", severity="warning", actual_value=75.0))
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

    # Nouvelle clé cardinale Phase 8.4 Lot 3
    assert "kpi_vnu_dormant_reclaim_eur" in body, (
        "Phase 8.4 Lot 3 BLOQUANT BI : `kpi_vnu_dormant_reclaim_eur` absent (renommage cardinal CFO)"
    )
    assert body["kpi_vnu_dormant_reclaim_eur"] == 75.0

    # Alias rétro-compat conservé (Phase D retrait après wiring frontend)
    assert "kpi_total_economie_potentielle_eur" in body
    assert body["kpi_total_economie_potentielle_eur"] == 75.0


# ─── Fix P1-QA-011 + P1-QA-012 — BILAN corrections ──────────────────────────


def test_phase84_lot3_bilan_lendemain_claim_corrected():
    """Phase 8.4 Lot 3 P1 QA : BILAN_SPRINT_C8 admet drift 'lendemain' vs git timestamps."""
    bilan_path = Path(__file__).parent.parent.parent / "docs" / "audits" / "BILAN_SPRINT_C8_2026_05_07.md"
    content = bilan_path.read_text(encoding="utf-8")

    # Note correction Phase 8.4 audit deep doit être présente
    assert "Phase 8.4 audit deep correction" in content, (
        "Phase 8.4 Lot 3 BLOQUANT QA : note correction 'lendemain drift' manquante BILAN"
    )
    assert "11 min même journée" in content or "11 min" in content


def test_phase84_lot3_bilan_sg_count_corrected():
    """Phase 8.4 Lot 3 P1 QA : BILAN comptage SG corrigé (10 SG Sprint C-8 vs claim 11)."""
    bilan_path = Path(__file__).parent.parent.parent / "docs" / "audits" / "BILAN_SPRINT_C8_2026_05_07.md"
    content = bilan_path.read_text(encoding="utf-8")

    # Comptage corrigé Phase 8.4
    assert "10 SG" in content, "Phase 8.4 Lot 3 : comptage 10 SG Sprint C-8 absent BILAN"
    assert "37 tests Sprint C-8" in content or "37 tests" in content
