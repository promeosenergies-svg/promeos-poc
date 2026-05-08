"""
PROMEOS — Tests cardinaux Phase D-4 Tier 4+ backlog non-cardinal.

Couvre :
- OPERAT_DECLARATION_DEADLINE dynamique (compute_operat_deadline + MONTH_DAY constante)
- StagingBatch.mode strict StagingMode Enum
- OrgEntiteLink.role strict OrgEntiteRole Enum
- 4 ADR-D-02/03/04/05 status ACCEPTED post implémentation

Audit cardinal : audit code-reviewer cumul Phase D-4 (Pilier 6 ADR-016 7e cycle).
"""

from __future__ import annotations

import pytest


# ─── OPERAT deadline dynamique ─────────────────────────────────────────────


def test_phase_d4_t4plus_operat_deadline_dynamic():
    """compute_operat_deadline retourne deadline annuelle 30 septembre N."""
    from doctrine.constants import (
        OPERAT_DECLARATION_DEADLINE_MONTH_DAY,
        compute_operat_deadline,
    )

    assert OPERAT_DECLARATION_DEADLINE_MONTH_DAY == "09-30"
    assert compute_operat_deadline(2026) == "2026-09-30"
    assert compute_operat_deadline(2027) == "2027-09-30"
    assert compute_operat_deadline(2030) == "2030-09-30"


# ─── StagingBatch.mode + OrgEntiteLink.role validators ────────────────────


def test_phase_d4_t4plus_staging_mode_strict():
    """StagingBatch.mode strict StagingMode Enum (express/import/assiste/demo)."""
    from models.patrimoine import StagingBatch
    from models.enums import ImportSourceType

    sb = StagingBatch(source_type=ImportSourceType.CSV)
    for val in ("express", "import", "assiste", "demo"):
        sb.mode = val

    with pytest.raises(ValueError, match="StagingBatch.mode"):
        sb.mode = "rogue_mode"


def test_phase_d4_t4plus_org_entite_link_role_strict():
    """OrgEntiteLink.role strict OrgEntiteRole Enum (proprietaire/gestionnaire/locataire)."""
    from models.patrimoine import OrgEntiteLink

    link = OrgEntiteLink(organisation_id=1, entite_juridique_id=1)
    for val in ("proprietaire", "gestionnaire", "locataire"):
        link.role = val

    with pytest.raises(ValueError, match="OrgEntiteLink.role"):
        link.role = "OWNER"


# ─── ADR-D-02/03/04/05 status ACCEPTED ────────────────────────────────────


def test_phase_d4_t4plus_adrs_accepted():
    """4 ADR-D-XX status ACCEPTED post implémentation Phase D-4."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    adr_dir = repo_root / "docs" / "adr"
    adrs = ["ADR-D-02", "ADR-D-03", "ADR-D-04", "ADR-D-05"]
    for adr in adrs:
        adr_files = list(adr_dir.glob(f"{adr}*.md"))
        assert adr_files, f"ADR {adr} introuvable"
        content = adr_files[0].read_text(encoding="utf-8")
        assert "ACCEPTED" in content, f"{adr} statut non ACCEPTED"
