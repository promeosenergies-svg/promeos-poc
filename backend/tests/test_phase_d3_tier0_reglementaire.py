"""
PROMEOS — Tests cardinaux Phase D-3 Tier 0 RÉGLEMENTAIRE (audit Sprint Réglementaire 2026-05-07).

Couvre les 5 P0 actionnables sans Légifrance (Option A) :
- P0-REG-001/011 APER décret + commentaire flag escalade Phase D-4
- P0-REG-002 APER échéance 01/07/2026 parkings >10000 m² (constante exposée)
- P0-REG-003 OPERAT 426 sous-catégories (vs mythe "9 typologies")
- P0-REG-007 Doublon BACS_PENALTY/OPERAT_PENALTY (sources distinctes documentées YAML)
- P0-REG-010 VNU mécanisme constantes exposées + flag pending verification

Source : docs/audits/AUDIT_REGLEMENTAIRE_CARDINAL_2026_05_07.md
"""

from __future__ import annotations


# ─── P0-REG-002 — APER échéance 01/07/2026 parkings >10000 m² ──────────────


def test_phase_d3_aper_deadline_large_parking_2026_07_01():
    """P0-REG-002 cardinal : échéance 2026-07-01 parkings >10000 m² exposée."""
    from doctrine.constants import APER_DEADLINE_LARGE_PARKING_DATE, APER_PARKING_LARGE_SURFACE_M2

    assert APER_DEADLINE_LARGE_PARKING_DATE == "2026-07-01"
    assert APER_PARKING_LARGE_SURFACE_M2 == 10000


def test_phase_d3_aper_deadline_small_parking_2028_07_01():
    """P0-REG-002 : échéance 2028-07-01 parkings 1500-10000 m² exposée (correction date 2028-01-01)."""
    from doctrine.constants import APER_DEADLINE_SMALL_PARKING_DATE, APER_PARKING_MIN_SURFACE_M2

    assert APER_DEADLINE_SMALL_PARKING_DATE == "2028-07-01"
    assert APER_PARKING_MIN_SURFACE_M2 == 1500


def test_phase_d3_aper_solar_ratio_50pct():
    """P0-REG-002 : taux minimum solarisation 50% Loi APER art. 40 exposé."""
    from doctrine.constants import APER_SOLAR_RATIO_PCT

    assert APER_SOLAR_RATIO_PCT == 50.0


# ─── P0-REG-003 — OPERAT 426 sous-catégories (vs mythe "9 typologies") ──


def test_phase_d3_operat_annexe_i_426_sous_categories():
    """P0-REG-003 cardinal : 426 sous-catégories Annexe I (PAS 9 typologies)."""
    from doctrine.constants import OPERAT_ANNEXE_I_SOUS_CATEGORIES_COUNT

    assert OPERAT_ANNEXE_I_SOUS_CATEGORIES_COUNT == 426


# ─── P0-REG-007 — Doublon BACS/OPERAT 1500€ sources distinctes documentées ─


def test_phase_d3_bacs_operat_penalty_distinct_sources_yaml():
    """P0-REG-007 : sources distinctes BACS_PENALTY (Décret 2020-887 art. R175-7)
    vs OPERAT_PENALTY (Circulaire DGEC 2024 + Décret 2019-771 art. 6) — documentées YAML."""
    import yaml
    from pathlib import Path

    yaml_path = Path(__file__).resolve().parent.parent / "config" / "sources_reglementaires.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    facts = config.get("terms", {})
    bacs = facts.get("COMPLIANCE_BACS_PENALTY_EUR", {})
    operat = facts.get("COMPLIANCE_OPERAT_PENALTY_EUR", {})

    assert bacs.get("value") == 1500
    assert operat.get("value") == 1500
    # Sources distinctes (Décret 2020-887 vs Circulaire DGEC 2024)
    bacs_label = (bacs.get("source") or {}).get("label", "")
    operat_label = (operat.get("source") or {}).get("label", "")
    assert "2020-887" in bacs_label
    assert ("DGEC" in operat_label) or ("2019-771" in operat_label)


def test_phase_d3_bacs_threshold_70kw_2030_exposed():
    """P0-REG-007 : seuil BACS 70 kW au 01/01/2030 exposé en constante (Décret 2025-1343)."""
    from doctrine.constants import BACS_DEADLINE_EXISTING, BACS_THRESHOLD_KW_EXISTING, BACS_THRESHOLD_KW_INITIAL

    assert BACS_THRESHOLD_KW_INITIAL == 290
    assert BACS_THRESHOLD_KW_EXISTING == 70
    assert BACS_DEADLINE_EXISTING == "2030-01-01"


# ─── P0-REG-010 — VNU mécanisme constantes exposées ────────────────────────


def test_phase_d3_vnu_constantes_exposees():
    """P0-REG-010 cardinal : VNU_DATE_APPLICATION + tarif unitaire + seuils exposés."""
    from doctrine.constants import (
        VNU_DATE_APPLICATION,
        VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH,
        VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH,
        VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH,
    )

    assert VNU_DATE_APPLICATION == "2026-01-01"
    assert VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH == 0.0  # KB confirmé : tarif dormant 2026
    assert VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH == 78.0
    assert VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH == 110.0


def test_phase_d3_vnu_yaml_pending_verification_status():
    """P0-REG-010 : VNU YAML status='pending_source_verification' (transparence
    réglementaire — Décret 2026-55 + CRE 2026-52 à confirmer Phase D-4)."""
    import yaml
    from pathlib import Path

    yaml_path = Path(__file__).resolve().parent.parent / "config" / "sources_reglementaires.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    facts = config.get("terms", {})
    vnu = facts.get("VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH", {})
    assert vnu.get("status") == "pending_source_verification"
    assert vnu.get("confidence") == "low"


# ─── Mirroring constants.py ↔ sources_reglementaires.yaml ──────────────────


def test_phase_d3_mirror_aper_constants_yaml():
    """P0-REG : mirroring constants.py ↔ sources_reglementaires.yaml pour APER."""
    import yaml
    from pathlib import Path

    from doctrine.constants import (
        APER_DEADLINE_LARGE_PARKING_DATE,
        APER_DEADLINE_SMALL_PARKING_DATE,
        APER_PARKING_LARGE_SURFACE_M2,
        APER_PARKING_MIN_SURFACE_M2,
        APER_PENALTY_EUR_PER_M2_PER_YEAR,
        APER_SOLAR_RATIO_PCT,
    )

    yaml_path = Path(__file__).resolve().parent.parent / "config" / "sources_reglementaires.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    facts = config.get("terms", {})
    assert facts["APER_THRESHOLD_M2_SMALL"]["value"] == APER_PARKING_MIN_SURFACE_M2
    assert facts["APER_THRESHOLD_M2_LARGE"]["value"] == APER_PARKING_LARGE_SURFACE_M2
    assert facts["APER_DEADLINE_SMALL"]["value"] == APER_DEADLINE_SMALL_PARKING_DATE
    assert facts["APER_DEADLINE_LARGE"]["value"] == APER_DEADLINE_LARGE_PARKING_DATE
    assert facts["APER_PENALTY_EUR_PER_M2_PER_YEAR"]["value"] == APER_PENALTY_EUR_PER_M2_PER_YEAR
    assert facts["APER_SOLAR_RATIO_PCT"]["value"] == APER_SOLAR_RATIO_PCT


def test_phase_d3_mirror_bacs_constants_yaml():
    """P0-REG : mirroring constants.py ↔ sources_reglementaires.yaml pour BACS."""
    import yaml
    from pathlib import Path

    from doctrine.constants import (
        BACS_PENALTY_EUR,
        BACS_THRESHOLD_KW_EXISTING,
        BACS_THRESHOLD_KW_INITIAL,
    )

    yaml_path = Path(__file__).resolve().parent.parent / "config" / "sources_reglementaires.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    facts = config.get("terms", {})
    assert facts["BACS_THRESHOLD_KW_2025"]["value"] == BACS_THRESHOLD_KW_INITIAL
    assert facts["BACS_THRESHOLD_KW_2030"]["value"] == BACS_THRESHOLD_KW_EXISTING
    assert facts["COMPLIANCE_BACS_PENALTY_EUR"]["value"] == BACS_PENALTY_EUR


# ─── Audit cardinal Phase D-3 Tier 0 livré ─────────────────────────────────


def test_phase_d3_audit_reglementaire_doc_livre():
    """Phase D-3 : doc audit cardinal réglementaire livré + rapport escalade."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    audits = repo_root / "docs" / "audits"
    assert (audits / "AUDIT_REGLEMENTAIRE_CARDINAL_2026_05_07.md").exists()
    assert (audits / "RAPPORT_ESCALADE_HUMAINE_SOURCES_2026_05_07.md").exists()
