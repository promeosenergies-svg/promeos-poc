"""Phase 4.1 — Source-guards persona context (mention italique Option 1.C).

Vérifie :
1. CFO mention contient référence financière (exposition / trajectoire)
2. Owner commerce mention parle € directs (pas de score abstrait)
3. Director ERP mention parle service public ou conseil
4. PERSONA_FOCUS couvre les 7 rôles canoniques
5. Format _format_eur_short avec virgule décimale FR

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 4.1.
"""

from __future__ import annotations

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from services.narrative.persona_context import (
    PERSONA_FOCUS,
    PERSONA_ROLE_LABEL,
    PersonaRole,
    _format_eur_short,
    compose_persona_mention,
    compute_persona_focus_text,
)


# ─── Tests format_eur_short ─────────────────────────────────────────────────


class TestFormatEurShort:
    """Source-guards : format € court avec virgule décimale FR."""

    def test_format_thousands(self):
        # 12700 / 1000 = 12.7 (pas d'arrondi banker)
        assert _format_eur_short(12700) == "12,7 k€"

    def test_format_millions(self):
        assert _format_eur_short(1_500_000) == "1,5 M€"

    def test_format_under_1k(self):
        assert _format_eur_short(450) == "450 €"

    def test_format_none(self):
        assert _format_eur_short(None) == "—"


# ─── Tests compose_persona_mention par rôle ─────────────────────────────────


class TestComposePersonaMention:
    """Source-guards spec Phase 4.1 : mentions persona par rôle."""

    def test_persona_mention_cfo_mentions_pnl(self):
        """Mention CFO contient 'exposition' (P&L proxy) ou 'trajectoire'."""
        mention = compose_persona_mention(
            "Marie",
            PersonaRole.CFO,
            {"exposure_eur": 12700, "compliance_score": 78},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "Marie" in mention
        assert "DAF" in mention
        assert "exposition" in mention.lower()
        assert "12,7 k€" in mention

    def test_persona_mention_owner_commerce_simple_no_jargon(self):
        """Mention propriétaire commerce : € direct, pas de jargon CFO."""
        mention = compose_persona_mention(
            "Hervé",
            PersonaRole.OWNER_COMMERCE,
            {"surcout_eur_mois": 230},
            OrganizationTypology.COMMERCE,
        )
        assert "Hervé" in mention
        assert "propriétaire" in mention
        # Pas de jargon CFO
        assert "exposition" not in mention.lower()
        assert "trajectoire" not in mention.lower()
        # Vocabulaire €/mois
        assert "230 €" in mention
        assert "surcoût" in mention.lower() or "économies" in mention.lower()

    def test_persona_mention_director_erp_service(self):
        """Mention directeur ERP : service public ou conseil."""
        mention = compose_persona_mention(
            "Anne",
            PersonaRole.DIRECTOR_ERP,
            {"compliance_score": 68},
            OrganizationTypology.ERP,
        )
        assert "Anne" in mention
        assert "directeur d'établissement" in mention or "service public" in mention.lower()

    def test_persona_mention_dg_strategy(self):
        """DG : focus stratégie / trajectoire."""
        mention = compose_persona_mention(
            "Pierre",
            PersonaRole.DG,
            {"compliance_score": 80},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "Pierre" in mention
        assert "DG" in mention
        assert "trajectoire" in mention.lower() or "stratégie" in mention.lower()

    def test_persona_mention_energy_manager_mwh(self):
        """Energy manager : focus MWh/an."""
        mention = compose_persona_mention(
            "Karim",
            PersonaRole.ENERGY_MANAGER,
            {"levers_mwh_year": 145},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "Karim" in mention
        assert "Energy Manager" in mention
        assert "145" in mention or "MWh" in mention

    def test_persona_mention_fallback_when_facts_empty(self):
        """Facts vide → fallback focus générique (pas de crash)."""
        mention = compose_persona_mention(
            "Test",
            PersonaRole.CFO,
            {},
            OrganizationTypology.GRAND_GROUPE,
        )
        # Toujours une mention valide
        assert mention.startswith("Pour Test")
        assert "DAF" in mention


# ─── Tests coverage PERSONA enums ───────────────────────────────────────────


class TestPersonaCoverage:
    """Source-guards exhaustivité enum vs mappings."""

    def test_all_personas_have_label(self):
        """Les 7 PersonaRole ont un libellé FR."""
        for role in PersonaRole:
            assert role in PERSONA_ROLE_LABEL, f"{role} sans libellé FR"

    def test_all_personas_have_focus(self):
        """Les 7 PersonaRole ont un focus métier."""
        for role in PersonaRole:
            assert role in PERSONA_FOCUS, f"{role} sans focus métier"

    def test_focus_text_returns_non_empty_for_all_roles(self):
        """compute_persona_focus_text retourne toujours une chaîne non vide."""
        for role in PersonaRole:
            text = compute_persona_focus_text(role, {}, OrganizationTypology.GRAND_GROUPE)
            assert text, f"Focus text vide pour {role}"

    def test_persona_role_values_canonical(self):
        """Valeurs PersonaRole sont stables (utilisées comme str enum)."""
        assert PersonaRole.CFO.value == "cfo"
        assert PersonaRole.OWNER_COMMERCE.value == "owner_commerce"
        assert PersonaRole.DIRECTOR_ERP.value == "director_erp"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
