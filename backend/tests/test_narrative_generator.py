"""PROMEOS — Tests smoke narrative_generator (Vague 4 EPIC #274).

Ciblé sur les 5 tests smoke + 1 source-guard interne (no hardcodes).
narrative_generator.py = 3308 lignes — on ne teste pas la totalité.

Couvre :
    NG_01 — generate_page_narrative importable (entry point public)
    NG_02 — Narrative dataclass exportée avec champs minimaux
    NG_03 — smoke cockpit_daily HELIOS (page MVP Sprint 1.1)
    NG_04 — NotImplementedError pour page_key inconnue
    NG_05 — DT_PENALTY_EUR importé depuis doctrine (pas de 7500 littéral)
    NG_06 — source-guard interne : aucun hardcode régulatoire dans le source

Ref : services/narrative/narrative_generator.py (3308 lignes).
ADR-001 grammaire Sol industrialisée.
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NG_PATH = os.path.join(_BACKEND_ROOT, "services", "narrative", "narrative_generator.py")


def _read_source() -> str:
    with open(_NG_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


# ── NG_01 — entry point public ───────────────────────────────────────────────


class TestNarrativeGeneratorPublicAPI:
    def test_ng_01_generate_page_narrative_importable(self):
        """NG_01 : generate_page_narrative est importable (entry point public)."""
        from services.narrative.narrative_generator import generate_page_narrative

        assert callable(generate_page_narrative)

    def test_ng_01_signature_stable(self):
        """NG_01 : signature generate_page_narrative(db, page_key, org_id, ...) stable."""
        from services.narrative.narrative_generator import generate_page_narrative

        sig = inspect.signature(generate_page_narrative)
        params = list(sig.parameters.keys())
        assert "db" in params, "paramètre 'db' absent"
        assert "page_key" in params, "paramètre 'page_key' absent"
        assert "org_id" in params, "paramètre 'org_id' absent"


# ── NG_02 — Narrative dataclass ───────────────────────────────────────────────


class TestNarrativeDataclass:
    def test_ng_02_narrative_dataclass_exported(self):
        """NG_02 : Narrative dataclass importable."""
        from services.narrative.narrative_generator import Narrative

        assert Narrative is not None

    def test_ng_02_narrative_has_minimal_fields(self):
        """NG_02 : Narrative expose les champs minimaux : title, kicker, narrative."""
        from services.narrative.narrative_generator import Narrative

        fields = {f.name for f in Narrative.__dataclass_fields__.values()}
        # 'narrative' = texte principal (anciennement narrative_lines dans les designs)
        for required in ("title", "kicker", "narrative"):
            assert required in fields, f"Champ '{required}' manquant dans Narrative"


# ── NG_03 — smoke cockpit_daily HELIOS ───────────────────────────────────────


class TestNarrativeGeneratorSmoke:
    def test_ng_03_smoke_cockpit_daily(self):
        """NG_03 : generate_page_narrative(cockpit_daily) sur HELIOS S ne crashe pas."""
        from database import SessionLocal
        from models import Organisation

        db = SessionLocal()
        try:
            org = db.query(Organisation).first()
            if org is None:
                return  # skip gracieux si DB vide

            from models import Site

            sites_count = db.query(Site).filter(Site.actif.is_(True)).count()

            from services.narrative.narrative_generator import Narrative, generate_page_narrative

            result = generate_page_narrative(
                db=db,
                page_key="cockpit_daily",
                org_id=org.id,
                org_name=org.nom,
                sites_count=sites_count,
                persona="daily",
            )

            assert isinstance(result, Narrative), f"Attendu Narrative, got {type(result)}"
            assert result.title, "title ne doit pas être vide"
            assert result.kicker, "kicker ne doit pas être vide"
            # narrative = str principal (la liste week_cards est dans result.week_cards)
            assert result.narrative is not None, "narrative ne doit pas être None"
        finally:
            db.close()

    def test_ng_03_narrative_is_string(self):
        """NG_03 : narrative est une str (texte principal pré-formaté)."""
        from database import SessionLocal
        from models import Organisation, Site

        db = SessionLocal()
        try:
            org = db.query(Organisation).first()
            if org is None:
                return

            sites_count = db.query(Site).filter(Site.actif.is_(True)).count()

            from services.narrative.narrative_generator import generate_page_narrative

            result = generate_page_narrative(
                db=db,
                page_key="cockpit_daily",
                org_id=org.id,
                org_name=org.nom or "HELIOS",
                sites_count=sites_count,
            )

            assert isinstance(result.narrative, str), f"narrative doit être une str, got {type(result.narrative)}"
        finally:
            db.close()


# ── NG_04 — NotImplementedError page_key inconnue ────────────────────────────


class TestNarrativeGeneratorNotImplemented:
    def test_ng_04_unknown_page_key_raises(self):
        """NG_04 : page_key inconnue lève NotImplementedError (contrat public)."""
        import pytest

        from services.narrative.narrative_generator import generate_page_narrative

        with pytest.raises(NotImplementedError):
            generate_page_narrative(
                db=None,
                page_key="__unknown_vague4_test__",  # type: ignore[arg-type]
                org_id=1,
            )


# ── NG_05 — DT_PENALTY_EUR depuis doctrine ───────────────────────────────────


class TestNarrativeDoctrineImports:
    def test_ng_05_imports_dt_penalty_from_doctrine(self):
        """NG_05 : DT_PENALTY_EUR importé depuis doctrine.constants (SoT canonique)."""
        src = _read_source()
        assert "from doctrine.constants import" in src, "narrative_generator doit importer depuis doctrine.constants"
        assert "DT_PENALTY_EUR" in src, "DT_PENALTY_EUR doit être importé"

    def test_ng_05_dt_penalty_not_literal(self):
        """NG_05 : la valeur 7500 n'est pas assignée directement (=7500) — elle
        vient toujours via DT_PENALTY_EUR."""
        src = _read_source()
        # Strip docstrings pour éviter faux positifs dans les commentaires
        src_clean = re.sub(r'"""[\s\S]*?"""', "", src)
        src_clean = re.sub(r"'''[\s\S]*?'''", "", src_clean)
        # On interdit une assignation directe = 7500 (pas dans une f-string de label)
        assert not re.search(r"(?<![\"'])\s*=\s*7500\b", src_clean), (
            "7500 assigné directement dans narrative_generator — doit venir DT_PENALTY_EUR"
        )


# ── NG_06 — source-guard interne no hardcode ─────────────────────────────────


class TestNarrativeSourceGuard:
    """SG interne : aucun hardcode régulatoire orphelin dans narrative_generator."""

    def test_ng_06_no_hardcoded_co2_factor(self):
        """NG_06 : pas de facteur CO₂ 0.052 hardcodé (doit venir doctrine)."""
        src = _read_source()
        src_clean = re.sub(r'"""[\s\S]*?"""', "", src)
        src_clean = re.sub(r"'''[\s\S]*?'''", "", src_clean)
        # 0.052 comme literal assigné
        assert "= 0.052" not in src_clean, (
            "0.052 (CO2_FACTOR_ELEC) hardcodé dans narrative_generator — utiliser doctrine.constants"
        )

    def test_ng_06_no_hardcoded_accise(self):
        """NG_06 : pas d'accise 0.02658 hardcodée."""
        src = _read_source()
        assert "0.02658" not in src, "0.02658 (accise legacy) hardcodé dans narrative_generator"
