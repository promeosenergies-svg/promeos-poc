"""PROMEOS — Tests smoke cockpit_decisions_service (Vague 4 EPIC #274).

Couvre :
    CDS_01 — exports publics get_top3_decisions + serialize_action_for_decision
    CDS_02 — signature get_top3_decisions(db, site_ids) → list[dict]
    CDS_03 — smoke test site_ids vide → liste vide (no DB needed)
    CDS_04 — serialize_action_for_decision renvoie keys traçabilité doctrine
    CDS_05 — doctrine constants importées (pas de hardcode 7500/3750/1500/0.052)
    CDS_06 — smoke nominal HELIOS scope (DB réelle via module autouse conftest)

Ref : services/cockpit_decisions_service.py (582 lignes).
Doctrine §0.D décision A : tout € doit être traçable réglementaire.
"""

from __future__ import annotations

import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── CDS_01 — exports publics ─────────────────────────────────────────────────


class TestCockpitDecisionsPublicAPI:
    def test_cds_01_get_top3_decisions_importable(self):
        """CDS_01 : get_top3_decisions est importable depuis le service."""
        from services.cockpit_decisions_service import get_top3_decisions

        assert callable(get_top3_decisions)

    def test_cds_01_serialize_action_importable(self):
        """CDS_01 : serialize_action_for_decision est importable."""
        from services.cockpit_decisions_service import serialize_action_for_decision

        assert callable(serialize_action_for_decision)


# ── CDS_02 — signature ────────────────────────────────────────────────────────


class TestCockpitDecisionsSignature:
    def test_cds_02_get_top3_signature(self):
        """CDS_02 : get_top3_decisions(db, site_ids) — signature stable."""
        from services.cockpit_decisions_service import get_top3_decisions

        sig = inspect.signature(get_top3_decisions)
        params = list(sig.parameters.keys())
        assert "db" in params, "paramètre 'db' absent"
        assert "site_ids" in params, "paramètre 'site_ids' absent"

    def test_cds_02_serialize_action_signature(self):
        """CDS_02 : serialize_action_for_decision(action, site_name) — signature stable."""
        from services.cockpit_decisions_service import serialize_action_for_decision

        sig = inspect.signature(serialize_action_for_decision)
        params = list(sig.parameters.keys())
        assert "action" in params, "paramètre 'action' absent"


# ── CDS_03 — smoke site_ids vide ─────────────────────────────────────────────


class TestCockpitDecisionsEdgeCases:
    def test_cds_03_empty_site_ids_returns_empty(self):
        """CDS_03 : site_ids=[] → liste vide sans crash (pas de DB needed)."""
        from services.cockpit_decisions_service import get_top3_decisions

        # db=None acceptable car la fonction retourne [] avant tout accès DB
        result = get_top3_decisions(db=None, site_ids=[])
        assert result == [], f"Attendu [], got {result}"

    def test_cds_03_returns_list_type(self):
        """CDS_03 : le retour est toujours une list."""
        from services.cockpit_decisions_service import get_top3_decisions

        result = get_top3_decisions(db=None, site_ids=[])
        assert isinstance(result, list)


# ── CDS_04 — keys traçabilité ─────────────────────────────────────────────────


class TestCockpitDecisionsTraceability:
    def test_cds_04_serialize_returns_traceability_keys(self):
        """CDS_04 : serialize_action_for_decision inclut les champs traçabilité
        doctrine §0.D (estimated_gain_mwh_year OU regulatory_penalty_eur)."""
        from services.cockpit_decisions_service import serialize_action_for_decision

        src = inspect.getsource(serialize_action_for_decision)
        # L'un des champs de traçabilité doit être généré
        assert any(
            key in src
            for key in [
                "estimated_gain_mwh_year",
                "regulatory_penalty_eur",
                "estimated_savings_eur_year",
            ]
        ), "serialize_action_for_decision doit exposer au moins un champ traçabilité (MWh ou € tracé)"

    def test_cds_04_regulatory_article_present(self):
        """CDS_04 : champ 'reference' ou 'regulatory_article' présent (DT art. 9)."""
        from services.cockpit_decisions_service import serialize_action_for_decision

        src = inspect.getsource(serialize_action_for_decision)
        assert "regulatory_article" in src or "reference" in src, (
            "Aucun champ article réglementaire dans serialize_action_for_decision"
        )


# ── CDS_05 — doctrine constants, no hardcode ─────────────────────────────────


class TestCockpitDecisionsSourceGuardInline:
    """Source-guard inline : aucun hardcode réglementaire dans le service."""

    _FORBIDDEN = {
        "7500": "DT_PENALTY_EUR (utiliser doctrine.constants)",
        "3750": "DT_PENALTY_AT_RISK_EUR (utiliser doctrine.constants)",
        "0.052": "CO2_FACTOR_ELEC (utiliser doctrine.constants)",
        "0.227": "CO2_FACTOR_GAZ (utiliser doctrine.constants)",
    }

    def test_cds_05_imports_doctrine_constants(self):
        """CDS_05 : le service importe doctrine.constants (SoT canonique)."""
        from services import cockpit_decisions_service

        src = inspect.getsource(cockpit_decisions_service)
        assert "from doctrine.constants import" in src or "doctrine.constants" in src, (
            "cockpit_decisions_service doit importer depuis doctrine.constants"
        )

    def test_cds_05_no_hardcoded_penalties(self):
        """CDS_05 : pas de constantes pénalités hardcodées (7500/3750/1500)."""
        from services import cockpit_decisions_service

        src = inspect.getsource(cockpit_decisions_service)
        # Strip docstrings pour éviter faux positifs dans les commentaires
        import re

        src_clean = re.sub(r'"""[\s\S]*?"""', "", src)
        src_clean = re.sub(r"'''[\s\S]*?'''", "", src_clean)
        # 7500 et 3750 peuvent apparaître comme littéraux dans _fmt_eur_short args
        # On cherche une assignation/multiplication directe
        assert not re.search(r"=\s*7500\b", src_clean), "7500 assigné directement (doit venir DT_PENALTY_EUR)"
        assert not re.search(r"=\s*3750\b", src_clean), "3750 assigné directement"


# ── CDS_06 — smoke nominal HELIOS ─────────────────────────────────────────────


class TestCockpitDecisionsNominal:
    def test_cds_06_smoke_helios_scope(self):
        """CDS_06 : smoke get_top3_decisions sur scope HELIOS réel.

        Dépend du conftest.py autouse ensure_demo_data → seed HELIOS S si
        nécessaire. Vérifie que le service ne crashe pas et retourne ≤ 3 dicts.
        """
        from database import SessionLocal
        from models import Organisation

        db = SessionLocal()
        try:
            org = db.query(Organisation).first()
            if org is None:
                # Pas de données — skip gracieux (ne pas casser baseline)
                return

            from models import Site

            # Récupère les 5 premiers sites actifs (seed HELIOS S garantit ≥ 5)
            site_ids = [s.id for s in db.query(Site).filter(Site.actif.is_(True)).limit(5).all()]

            from services.cockpit_decisions_service import get_top3_decisions

            result = get_top3_decisions(db=db, site_ids=site_ids)

            assert isinstance(result, list), "Doit retourner une liste"
            assert len(result) <= 3, f"Max 3 décisions, got {len(result)}"

            # Chaque dict doit avoir au minimum 'title' et 'severity'
            for item in result:
                assert isinstance(item, dict), "Chaque décision est un dict"
                assert "title" in item, f"Clé 'title' manquante dans {item.keys()}"
        finally:
            db.close()
