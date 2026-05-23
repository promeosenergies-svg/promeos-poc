"""
PROMEOS — Conformité P1 2026-05-23 : tests `evidence_validity_service`.

Vérifie que la durée de validité d'une Evidence est calculée selon la règle
réglementaire parente (heuristique titre) :
- DT/OPERAT/APER : 1 an
- BACS : 3 ans
- SMÉ ISO 50001 : 3 ans
- SMÉ audit énergétique : 4 ans
- BEGES : 3 ans
- Défaut : 90 jours
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest  # noqa: E402

from services.v4.evidence_validity_service import (  # noqa: E402
    DEFAULT_EVIDENCE_VALIDITY_DAYS,
    EVIDENCE_VALIDITY_DAYS_AUDIT_ENERGETIQUE,
    EVIDENCE_VALIDITY_DAYS_BY_RULE,
    _detect_rule_code_from_title,
    compute_default_expires_at,
)


NOW = datetime(2026, 5, 23, 10, 0, 0, tzinfo=timezone.utc)


# ─── _detect_rule_code_from_title ─────────────────────────────────────────


@pytest.mark.parametrize(
    "title,expected_rule",
    [
        ("Décret Tertiaire — Surface tertiaire à compléter", "DT"),
        ("Régulation chauffage (BACS) — Puissance CVC à compléter", "BACS"),
        ("EnR parking / toiture (APER) — Surface de parking à compléter", "APER"),
        ("Audit énergétique (SMÉ) — Effectif de l'organisation à compléter", "SME"),
        ("Bilan GES réglementaire — Effectif de l'organisation à compléter", "BEGES"),
        ("Déclaration OPERAT annuelle 2026", "OPERAT"),
        ("Maintenance préventive CVC", None),  # pas de pattern reconnu
        (None, None),
        ("", None),
    ],
)
def test_detect_rule_code(title, expected_rule):
    assert _detect_rule_code_from_title(title) == expected_rule


# ─── compute_default_expires_at ───────────────────────────────────────────


def test_dt_validity_1_year():
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Décret Tertiaire — Surface tertiaire à compléter",
    )
    assert (expires - NOW).days == EVIDENCE_VALIDITY_DAYS_BY_RULE["DT"]
    assert (expires - NOW).days == 365


def test_bacs_validity_3_years():
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Régulation chauffage (BACS) — Puissance CVC à compléter",
    )
    assert (expires - NOW).days == 365 * 3


def test_aper_validity_1_year():
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="EnR parking / toiture (APER) — Surface de parking à compléter",
    )
    assert (expires - NOW).days == 365


def test_sme_iso_50001_validity_3_years():
    """Certificat ISO 50001 par défaut → 3 ans."""
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Audit énergétique (SMÉ) — Effectif de l'organisation à compléter",
    )
    assert (expires - NOW).days == 365 * 3


def test_sme_audit_energetique_validity_4_years():
    """Rapport audit énergétique (flag) → 4 ans (Loi 2025-391)."""
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Audit énergétique (SMÉ) — Effectif de l'organisation à compléter",
        is_audit_energetique=True,
    )
    assert (expires - NOW).days == EVIDENCE_VALIDITY_DAYS_AUDIT_ENERGETIQUE
    assert (expires - NOW).days == 365 * 4


def test_beges_validity_3_years():
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Bilan GES réglementaire — Effectif de l'organisation à compléter",
    )
    assert (expires - NOW).days == 365 * 3


def test_unknown_title_falls_back_to_90_days():
    """Item non-réglementaire → 90j défaut."""
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Maintenance préventive CVC",
    )
    assert (expires - NOW).days == DEFAULT_EVIDENCE_VALIDITY_DAYS
    assert (expires - NOW).days == 90


def test_null_title_falls_back_to_90_days():
    """Title None → 90j défaut."""
    expires = compute_default_expires_at(uploaded_at=NOW, parent_item_title=None)
    assert (expires - NOW).days == 90


def test_rule_code_override_wins_over_title():
    """`rule_code_override` court-circuite l'heuristique titre."""
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Décret Tertiaire — Surface",  # heuristique = DT (1 an)
        rule_code_override="SME",  # override → SMÉ (3 ans)
    )
    assert (expires - NOW).days == 365 * 3


def test_audit_energetique_flag_only_applies_to_sme():
    """Le flag `is_audit_energetique` ne s'applique que si rule=SME."""
    # Avec DT + flag audit énergétique → reste sur 1 an (le flag est ignoré)
    expires = compute_default_expires_at(
        uploaded_at=NOW,
        parent_item_title="Décret Tertiaire — Surface",
        is_audit_energetique=True,
    )
    assert (expires - NOW).days == 365  # DT 1 an, pas 4 ans
