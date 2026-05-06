"""
PROMEOS — Tests cardinaux Phase 7.7 Sprint C-7 Lot C — EnergyInvoice TVA + VNU cleanup.

Couvre 1 P1 + 2 P2 dettes Sprint C-7 :
- D-Sprint-C7-EnergyInvoice-TVA-Rate-Field-001 P1 — colonne tva_rate Numeric(5,4)
- D-Sprint-C7-VNU-Terminologie-Cleanup-001 P2 — terminologie cardinale uniformisée
- D-Sprint-C7-Consent-Helper-Deduplication-001 P2 → reporté (nécessite refactoring scope plus large)
"""

from __future__ import annotations

from decimal import Decimal


def test_phase77_lot_c_energy_invoice_has_tva_rate_column():
    """Phase 7.7 Lot C cardinal : EnergyInvoice.tva_rate présent (Numeric(5,4))."""
    from sqlalchemy import inspect

    from models.billing_models import EnergyInvoice

    mapper = inspect(EnergyInvoice)
    columns = {c.name: c for c in mapper.columns}

    assert "tva_rate" in columns, (
        "Phase 7.7 Lot C BLOQUANT : EnergyInvoice.tva_rate absent.\n"
        "Migration Alembic 12e (a7da3ed8aeb4) doit avoir ajouté la colonne."
    )
    col = columns["tva_rate"]
    assert col.nullable is True, "tva_rate doit être nullable (backward-compat)"


def test_phase77_lot_c_tva_rate_accepts_canonical_values():
    """Phase 7.7 Lot C : tva_rate stocke 5.5%, 10%, 20% en décimal Numeric(5,4)."""
    from models.billing_models import EnergyInvoice

    # Smoke-test : créer instance avec tva_rate ne lève pas
    inv1 = EnergyInvoice(
        site_id=1,
        invoice_number="TEST-TVA-1",
        tva_rate=Decimal("0.0550"),  # TVA 5.5%
    )
    inv2 = EnergyInvoice(
        site_id=1,
        invoice_number="TEST-TVA-2",
        tva_rate=Decimal("0.2000"),  # TVA 20%
    )
    assert inv1.tva_rate == Decimal("0.0550")
    assert inv2.tva_rate == Decimal("0.2000")


# ─── VNU terminologie cleanup ───────────────────────────────────────────────


def test_phase77_lot_c_vnu_acronym_canonical_terminology():
    """Phase 7.7 Lot C : doctrine.acronyms VNU = 'Versement pour Non-Usage' (pas 'Nucléaire Universel')."""
    from doctrine.acronyms import ACRONYM_TO_NARRATIVE

    assert ACRONYM_TO_NARRATIVE["VNU"] == "Versement pour Non-Usage", (
        f"Phase 7.7 Lot C BLOQUANT : VNU expansion incorrecte : {ACRONYM_TO_NARRATIVE['VNU']}.\n"
        "Terminologie cardinale : 'Versement pour Non-Usage' (art. L.336-2 Code énergie post-ARENH).\n"
        "Pas 'Versement Nucléaire Universel' (terme erroné)."
    )


def test_phase77_lot_c_vnu_terminology_no_residual_in_orchestrator():
    """Phase 7.7 Lot C : demo_seed/orchestrator.py 'Nucléaire Universel' éliminé."""
    from pathlib import Path

    orch_path = Path(__file__).parent.parent / "services" / "demo_seed" / "orchestrator.py"
    content = orch_path.read_text(encoding="utf-8")

    assert "Versement Nucléaire Universel" not in content, (
        "Phase 7.7 Lot C : terminologie 'Versement Nucléaire Universel' présente "
        "dans orchestrator.py (doit être 'Versement pour Non-Usage')."
    )


def test_phase77_lot_c_vnu_terminology_no_residual_in_gen_seed_completion():
    """Phase 7.7 Lot C : demo_seed/gen_seed_completion.py 'Nucléaire Universel' éliminé."""
    from pathlib import Path

    path = Path(__file__).parent.parent / "services" / "demo_seed" / "gen_seed_completion.py"
    content = path.read_text(encoding="utf-8")

    assert "Versement Nucléaire Universel" not in content, (
        "Phase 7.7 Lot C : terminologie 'Versement Nucléaire Universel' présente dans gen_seed_completion.py."
    )


def test_phase77_lot_c_vnu_terminology_no_residual_in_market_window_detector():
    """Phase 7.7 Lot C : event_bus market_window_detector terminologie OK."""
    from pathlib import Path

    path = Path(__file__).parent.parent / "services" / "event_bus" / "detectors" / "market_window_detector.py"
    content = path.read_text(encoding="utf-8")

    assert "Versement Nucléaire Universel" not in content, (
        "Phase 7.7 Lot C : terminologie 'Versement Nucléaire Universel' présente "
        "dans market_window_detector.py docstring."
    )
