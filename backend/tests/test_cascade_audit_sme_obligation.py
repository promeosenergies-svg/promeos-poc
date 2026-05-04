"""
PROMEOS — Sprint C-2 Phase 5.2 : Tests cascade AuditEnergetique.conso_annuelle_moy_gwh.

Vérifie le pivot Phase 5.1 (org-scoped, clôture D-Phase6-Cascade-EJ-Sites-001 sous
D-Phase6-Cascade-AuditSme-Org-Sites-001) :
- Helper _recompute_audit_sme_obligation : 3 obligations + 2 seuils inclusifs
- Helper _recompute_organisation_via_coordinator : appel bulk recompute
- Cascade entry "AuditEnergetique.conso_annuelle_moy_gwh" : 2 actions chaînées
- Résilience : audit_sme failure ou organisation_id None ne bloque pas la cascade
- Perf : ordre de grandeur sur l'org demo (HELIOS)

Source légale : loi n°2025-391 du 30/04/2025 (transposition directive UE 2023/1791),
Code de l'énergie art. L.233-1. Seuils 2.75 / 23.6 GWh (audit_sme docstring).
"""

from __future__ import annotations

import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Helpers seuils (unit, MagicMock) ───────────────────────────────────────


def test_obligation_aucune_when_conso_below_2_75_gwh():
    """Conso 1.0 GWh < 2.75 → obligation = AUCUNE."""
    from regops.services.cascade_recompute_service import _recompute_audit_sme_obligation

    audit_sme = MagicMock()
    audit_sme.conso_annuelle_moy_gwh = 1.0
    audit_sme.obligation = "NON_DETERMINE"

    result = _recompute_audit_sme_obligation(audit_sme)
    assert result == "AUCUNE"
    assert audit_sme.obligation == "AUCUNE"


def test_obligation_audit_4ans_when_conso_5_gwh():
    """Conso 5.0 GWh ∈ [2.75, 23.6) → obligation = AUDIT_4ANS."""
    from regops.services.cascade_recompute_service import _recompute_audit_sme_obligation

    audit_sme = MagicMock()
    audit_sme.conso_annuelle_moy_gwh = 5.0
    audit_sme.obligation = "NON_DETERMINE"

    result = _recompute_audit_sme_obligation(audit_sme)
    assert result == "AUDIT_4ANS"
    assert audit_sme.obligation == "AUDIT_4ANS"


def test_obligation_sme_iso50001_when_conso_30_gwh():
    """Conso 30.0 GWh ≥ 23.6 → obligation = SME_ISO50001."""
    from regops.services.cascade_recompute_service import _recompute_audit_sme_obligation

    audit_sme = MagicMock()
    audit_sme.conso_annuelle_moy_gwh = 30.0
    audit_sme.obligation = "AUCUNE"

    result = _recompute_audit_sme_obligation(audit_sme)
    assert result == "SME_ISO50001"
    assert audit_sme.obligation == "SME_ISO50001"


def test_obligation_seuil_2_75_inclusive():
    """Conso = 2.75 GWh exact → AUDIT_4ANS (limite inclusive)."""
    from regops.services.cascade_recompute_service import _recompute_audit_sme_obligation

    audit_sme = MagicMock()
    audit_sme.conso_annuelle_moy_gwh = 2.75
    audit_sme.obligation = "AUCUNE"

    result = _recompute_audit_sme_obligation(audit_sme)
    assert result == "AUDIT_4ANS"


def test_obligation_seuil_23_6_inclusive():
    """Conso = 23.6 GWh exact → SME_ISO50001 (limite inclusive)."""
    from regops.services.cascade_recompute_service import _recompute_audit_sme_obligation

    audit_sme = MagicMock()
    audit_sme.conso_annuelle_moy_gwh = 23.6
    audit_sme.obligation = "AUDIT_4ANS"

    result = _recompute_audit_sme_obligation(audit_sme)
    assert result == "SME_ISO50001"


def test_obligation_none_when_conso_none():
    """Conso None → None retourné, obligation NON modifiée."""
    from regops.services.cascade_recompute_service import _recompute_audit_sme_obligation

    audit_sme = MagicMock()
    audit_sme.conso_annuelle_moy_gwh = None
    audit_sme.obligation = "AUDIT_4ANS"  # valeur initiale préservée

    result = _recompute_audit_sme_obligation(audit_sme)
    assert result is None
    assert audit_sme.obligation == "AUDIT_4ANS"  # inchangée


# ─── Helper recompute_organisation (mock) ───────────────────────────────────


def test_recompute_organisation_via_coordinator_calls_existing_function():
    """_recompute_organisation_via_coordinator → appelle recompute_organisation avec org_id correct."""
    from regops.services import cascade_recompute_service as svc

    audit_sme = MagicMock()
    audit_sme.organisation_id = 999_300
    db = MagicMock()

    with patch(
        "services.compliance_coordinator.recompute_organisation",
        return_value={"organisation_id": 999_300, "sites_recomputed": 7},
    ) as mock_recompute:
        result = svc._recompute_organisation_via_coordinator(audit_sme, db)

    mock_recompute.assert_called_once_with(db, 999_300)
    assert result is not None
    assert "org_id=999300" in result
    assert "sites=7" in result


def test_recompute_organisation_via_coordinator_resilience_on_exception():
    """recompute_organisation raise → None retourné, cascade continue (résilience)."""
    from regops.services import cascade_recompute_service as svc

    audit_sme = MagicMock()
    audit_sme.organisation_id = 999_301
    db = MagicMock()

    with patch(
        "services.compliance_coordinator.recompute_organisation",
        side_effect=RuntimeError("simulated bulk recompute failure"),
    ):
        result = svc._recompute_organisation_via_coordinator(audit_sme, db)

    assert result is None  # cascade pas bloquée


def test_recompute_organisation_via_coordinator_returns_none_when_org_id_missing():
    """audit_sme sans organisation_id → None retourné, recompute_organisation pas appelé."""
    from regops.services import cascade_recompute_service as svc

    audit_sme = MagicMock()
    audit_sme.organisation_id = None
    db = MagicMock()

    with patch("services.compliance_coordinator.recompute_organisation") as mock_recompute:
        result = svc._recompute_organisation_via_coordinator(audit_sme, db)

    mock_recompute.assert_not_called()
    assert result is None


# ─── Cascade entry integration ──────────────────────────────────────────────


def test_cascade_entry_audit_sme_conso_chains_obligation_and_recompute():
    """`AuditEnergetique.conso_annuelle_moy_gwh` → 2 actions (obligation + bulk recompute)."""
    from regops.services.cascade_recompute_service import (
        CASCADE_MAP_MVP_SPRINT_C1,
        cascade_recompute_on_change,
    )

    assert "AuditEnergetique.conso_annuelle_moy_gwh" in CASCADE_MAP_MVP_SPRINT_C1
    callables = CASCADE_MAP_MVP_SPRINT_C1["AuditEnergetique.conso_annuelle_moy_gwh"]
    assert len(callables) == 2

    audit_sme = MagicMock()
    audit_sme.conso_annuelle_moy_gwh = 5.0
    audit_sme.obligation = "AUCUNE"
    audit_sme.organisation_id = 999_310
    audit_sme.id = 42

    db = MagicMock()

    with patch(
        "services.compliance_coordinator.recompute_organisation",
        return_value={"organisation_id": 999_310, "sites_recomputed": 3},
    ):
        result = cascade_recompute_on_change(
            db,
            audit_sme,
            "AuditEnergetique.conso_annuelle_moy_gwh",
            old_value=1.0,
            new_value=5.0,
            persist=False,  # pas de DB commit, pas de log_cascade DB
            org_id=999_310,
        )

    output_fields = {a.output_field for a in result.actions}
    assert "audit_sme_obligation" in output_fields
    assert "compliance_score_all_sites" in output_fields

    # Obligation passée AUCUNE → AUDIT_4ANS via cascade
    assert audit_sme.obligation == "AUDIT_4ANS"


# ─── Anti-cycle smoke ───────────────────────────────────────────────────────


def test_anti_cycle_recompute_organisation_does_not_modify_conso():
    """Anti-cycle : recompute_organisation ne touche pas audit_sme.conso_annuelle_moy_gwh."""
    from regops.services.cascade_recompute_service import _recompute_organisation_via_coordinator

    audit_sme = MagicMock()
    audit_sme.organisation_id = 999_320
    audit_sme.conso_annuelle_moy_gwh = 12.0
    db = MagicMock()

    with patch(
        "services.compliance_coordinator.recompute_organisation",
        return_value={"organisation_id": 999_320, "sites_recomputed": 5},
    ):
        _recompute_organisation_via_coordinator(audit_sme, db)

    # conso_annuelle_moy_gwh NON modifiée par le helper → pas de cycle possible
    assert audit_sme.conso_annuelle_moy_gwh == 12.0


# ─── Perf smoke (ordre de grandeur sur seed HELIOS) ─────────────────────────


def test_perf_recompute_organisation_demo_seed_under_30sec():
    """Smoke perf : recompute_organisation sur l'org HELIOS (≤25 sites typiquement)
    doit aboutir en < 30 sec (cible MVP). Si > 30 sec → tracer dette.

    Test skippé si HELIOS pas seedé (pas d'organisation en DB).
    """
    from database import SessionLocal
    from models import Organisation
    from services.compliance_coordinator import recompute_organisation

    db = SessionLocal()
    try:
        org = db.query(Organisation).first()
        if not org:
            pytest.skip("Aucune Organisation en DB (seed manquant)")

        start = time.perf_counter()
        result = recompute_organisation(db, org.id)
        elapsed = time.perf_counter() - start

        assert result is not None
        assert "sites_recomputed" in result
        # Cible MVP : < 30 sec sur seed démo (HELIOS S ≈ 5-15 sites typiquement).
        # Au-delà → ouvrir D-Sprint-C2-5-Bulk-Recompute-Optim-001 P1 Sprint C-3.
        assert elapsed < 30.0, (
            f"recompute_organisation prend {elapsed:.1f}s sur {result['sites_recomputed']} sites "
            f"(cible <30s MVP). Tracer dette bulk optim."
        )
    finally:
        db.close()
