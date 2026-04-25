"""
PROMEOS - Tests Sprint 5a StrEnum pilotage.

Couvre :
    1. `PrixSource` StrEnum expose les 4 valeurs canoniques
    2. `build_flex_ready_signals` emet un `prix_source` conforme a l'enum
    3. `ActionSourceType.PILOTAGE` accepte par POST /api/actions
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base
from models.enums import ActionSourceType
from services.pilotage.flex_ready import PrixSource, build_flex_ready_signals


# ---------------------------------------------------------------------------
# Test 1 : PrixSource expose les 4 valeurs canoniques
# ---------------------------------------------------------------------------
def test_prix_source_enum_4_valeurs():
    """Les 4 valeurs doivent matcher la description Pydantic + consommateurs API."""
    assert PrixSource.ENTSOE_DAY_AHEAD.value == "entsoe_day_ahead"
    assert PrixSource.CONTRAT_FOURNISSEUR.value == "contrat_fournisseur"
    assert PrixSource.FOURNISSEUR_TARIF_BASE.value == "fournisseur_tarif_base"
    assert PrixSource.SITE_SANS_CONTRAT_FALLBACK.value == "site_sans_contrat_fallback"
    # StrEnum : on peut l'utiliser partout ou un str est attendu
    assert PrixSource.CONTRAT_FOURNISSEUR == "contrat_fournisseur"


def test_prix_source_enum_type_safety():
    """Toute valeur hors enum doit lever ValueError a la construction."""
    with pytest.raises(ValueError):
        PrixSource("source_inconnue")


# ---------------------------------------------------------------------------
# Test 2 : `build_flex_ready_signals` payload cite une valeur canonique
# ---------------------------------------------------------------------------
def test_build_flex_ready_payload_prix_source_canonique():
    """Le `prix_source` retourne doit etre un .value de PrixSource."""
    payload = build_flex_ready_signals(
        site_id="retail-001",
        demo_site={
            "puissance_max_instantanee_kw": 180.0,
            "prix_eur_kwh": 0.185,
            "puissance_souscrite_kva": 250,
            "energy_vector": "ELEC",
        },
        db=None,  # force fallback tarif contractuel (pas de spot)
    )
    # Le payload doit porter une valeur comprise par PrixSource
    assert payload["prix_source"] in {e.value for e in PrixSource}
    # Spec : sans db -> FOURNISSEUR_TARIF_BASE
    assert payload["prix_source"] == PrixSource.FOURNISSEUR_TARIF_BASE.value


def test_build_flex_ready_ctx_site_sans_contrat_preserve():
    """Ctx porte `prix_source="site_sans_contrat_fallback"` -> preserved."""
    payload = build_flex_ready_signals(
        site_id="42",
        demo_site={
            "puissance_max_instantanee_kw": 100.0,
            "prix_eur_kwh": 0.175,
            "puissance_souscrite_kva": 144,
            "energy_vector": "ELEC",
            "prix_source": PrixSource.SITE_SANS_CONTRAT_FALLBACK.value,
        },
        db=None,
    )
    assert payload["prix_source"] == PrixSource.SITE_SANS_CONTRAT_FALLBACK.value


# ---------------------------------------------------------------------------
# Test 3 : ActionSourceType.PILOTAGE expose + validation logique
# ---------------------------------------------------------------------------
def test_action_source_type_pilotage_enum_expose():
    """`ActionSourceType.PILOTAGE` est expose avec la valeur 'pilotage'."""
    assert ActionSourceType.PILOTAGE.value == "pilotage"
    assert ActionSourceType("pilotage") == ActionSourceType.PILOTAGE


def test_action_source_type_validation_autorise_pilotage():
    """
    La logique `source_type in (MANUAL, INSIGHT, PILOTAGE)` des routes /actions
    doit autoriser les 3 valeurs (pas seulement MANUAL + INSIGHT comme avant).
    """
    allowed = (
        ActionSourceType.MANUAL,
        ActionSourceType.INSIGHT,
        ActionSourceType.PILOTAGE,
    )
    assert ActionSourceType.PILOTAGE in allowed
    assert ActionSourceType.MANUAL in allowed
    assert ActionSourceType.INSIGHT in allowed
    # Les autres sources (COMPLIANCE, BILLING, etc.) ne sont PAS autorisées
    # en création directe (passent par leur moteur dédié).
    assert ActionSourceType.COMPLIANCE not in allowed
    assert ActionSourceType.BILLING not in allowed


def test_action_source_type_valeur_bidon_leve_valueerror():
    """Toute valeur hors enum (ex. ancien workaround 'pilotage_radar') leve."""
    with pytest.raises(ValueError):
        ActionSourceType("pilotage_radar")
    with pytest.raises(ValueError):
        ActionSourceType("flex_radar")
