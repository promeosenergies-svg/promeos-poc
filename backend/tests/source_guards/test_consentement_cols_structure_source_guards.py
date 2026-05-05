"""
PROMEOS — Source guards structure consentement Org/DP (Sprint C-4 Phase 4.4, ADR-007).

Anti-régression : les 8 colonnes consentement RGPD ajoutées Phase 4.4 (migration
`d4a59f7c8e21`) doivent rester présentes sur les modèles ORM Organisation
+ DeliveryPoint avec le typage RGPD-compliant attendu.

Pré-requis cardinal Phase 4.5 cascade vivante. Si les colonnes sont retirées
silencieusement, ces SG bloquent au commit.

3 source-guards :

- SG_CONSENTEMENT_01 : Organisation a 4 cols consentement (dataconnect_global +
  dataconnect_at + grdf_global + grdf_at) avec types Boolean + DateTime
- SG_CONSENTEMENT_02 : DeliveryPoint a 4 cols consentement local (dataconnect_local
  + dataconnect_local_at + grdf_local + grdf_local_at) avec types correspondants
- SG_CONSENTEMENT_03 : timestamps RGPD utilisent timezone=True (cohérence audit
  trail CNIL — pas de naive datetime)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ORG_MODEL_PATH = _BACKEND_ROOT / "models" / "organisation.py"
_DP_MODEL_PATH = _BACKEND_ROOT / "models" / "patrimoine.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


_ORG_REQUIRED_COLS = [
    "consentement_dataconnect_global",
    "consentement_dataconnect_at",
    "consentement_grdf_global",
    "consentement_grdf_at",
]

_DP_REQUIRED_COLS = [
    "consentement_dataconnect_local",
    "consentement_dataconnect_local_at",
    "consentement_grdf_local",
    "consentement_grdf_local_at",
]


def test_sg_consentement_01_organisation_has_4_consent_cols():
    """SG_CONSENTEMENT_01 : Organisation a les 4 cols consentement déclarées + Column(...)."""
    content = _read(_ORG_MODEL_PATH)

    missing = [col for col in _ORG_REQUIRED_COLS if f"{col} = Column(" not in content]
    assert not missing, (
        f"Cols consentement manquantes dans Organisation : {missing}.\n"
        f"Les 4 cols Phase 4.4 (ADR-007) doivent rester présentes pour Phase 4.5 cascade."
    )

    # Vérifier que dataconnect_global / grdf_global sont Boolean
    for boolean_col in ("consentement_dataconnect_global", "consentement_grdf_global"):
        col_block_match = re.search(
            rf"{boolean_col}\s*=\s*Column\([^)]+\)",
            content,
            re.DOTALL,
        )
        assert col_block_match, f"Bloc Column pour {boolean_col} introuvable"
        assert "Boolean" in col_block_match.group(0), (
            f"{boolean_col} doit être typé Boolean (pas {col_block_match.group(0)})"
        )


def test_sg_consentement_02_delivery_point_has_4_consent_local_cols():
    """SG_CONSENTEMENT_02 : DeliveryPoint a les 4 cols consentement local."""
    content = _read(_DP_MODEL_PATH)

    missing = [col for col in _DP_REQUIRED_COLS if f"{col} = Column(" not in content]
    assert not missing, (
        f"Cols consentement local manquantes dans DeliveryPoint : {missing}.\n"
        f"Les 4 cols Phase 4.4 (ADR-007) sont cardinales pour cascade Phase 4.5."
    )

    # Vérifier que les 2 booléens locaux sont Boolean
    for boolean_col in ("consentement_dataconnect_local", "consentement_grdf_local"):
        col_block_match = re.search(
            rf"{boolean_col}\s*=\s*Column\([^)]+\)",
            content,
            re.DOTALL,
        )
        assert col_block_match, f"Bloc Column pour {boolean_col} introuvable"
        assert "Boolean" in col_block_match.group(0), f"{boolean_col} doit être typé Boolean"


def test_sg_consentement_03_timestamps_use_timezone_true_rgpd_compliant():
    """SG_CONSENTEMENT_03 : timestamps consent doivent être DateTime(timezone=True)
    (cohérence audit trail CNIL — pas de naive datetime).
    """
    org_content = _read(_ORG_MODEL_PATH)
    dp_content = _read(_DP_MODEL_PATH)

    timestamp_cols = [
        ("consentement_dataconnect_at", org_content, "Organisation"),
        ("consentement_grdf_at", org_content, "Organisation"),
        ("consentement_dataconnect_local_at", dp_content, "DeliveryPoint"),
        ("consentement_grdf_local_at", dp_content, "DeliveryPoint"),
    ]

    offenders: list[str] = []
    for col_name, content, model_name in timestamp_cols:
        col_block_match = re.search(
            rf"{col_name}\s*=\s*Column\([\s\S]+?\)",
            content,
        )
        if not col_block_match:
            offenders.append(f"{model_name}.{col_name} : Column block introuvable")
            continue
        block = col_block_match.group(0)
        # Doit contenir DateTime ET timezone=True
        if "DateTime" not in block:
            offenders.append(f"{model_name}.{col_name} : pas de DateTime ({block[:80]})")
            continue
        if "timezone=True" not in block:
            offenders.append(
                f"{model_name}.{col_name} : DateTime sans timezone=True (RGPD audit trail "
                f"requiert timezone-aware) — {block[:120]}"
            )

    assert not offenders, (
        "Timestamps consentement RGPD non timezone-aware (violation CNIL audit trail) :\n  - "
        + "\n  - ".join(offenders)
    )
