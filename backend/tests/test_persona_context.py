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
        """Mention CFO contient 'exposition' (P&L proxy) ou 'trajectoire'.

        Phase 8.B : Marie + CFO + GRAND_GROUPE → 'Directrice Financière'
        (féminisé + context GG vs 'DAF' par défaut). Le test vérifie
        désormais le rôle financier de manière flexible (DAF | Directrice).
        """
        mention = compose_persona_mention(
            "Marie",
            PersonaRole.CFO,
            {"exposure_eur": 12700, "compliance_score": 78},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "Marie" in mention
        # Phase 8.B : flexibilité — DAF (ETI) ou Directeur/Directrice Financier·ère (GG)
        assert "DAF" in mention or "Financier" in mention or "Financière" in mention
        # Phase 4.bis3 audit P2 : pas de .lower() sur la mention (préserve sigles)
        assert "exposition" in mention
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
        # Toujours une mention valide (Phase 8.B : GG → "Directeur Financier")
        assert mention.startswith("Pour Test")
        assert "Financier" in mention or "DAF" in mention


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


# ─── Phase 4.bis3 — Corrections audit CX ───────────────────────────────────


class TestPhase4bis3NewRoles:
    """Audit gap stratégique : ENERGY_BUYER + CSR_MANAGER ajoutés."""

    def test_energy_buyer_role_exists(self):
        assert PersonaRole.ENERGY_BUYER.value == "energy_buyer"
        assert PersonaRole.ENERGY_BUYER in PERSONA_ROLE_LABEL
        assert PERSONA_ROLE_LABEL[PersonaRole.ENERGY_BUYER] == "acheteur énergie"

    def test_csr_manager_role_exists(self):
        assert PersonaRole.CSR_MANAGER.value == "csr_manager"
        assert PERSONA_ROLE_LABEL[PersonaRole.CSR_MANAGER] == "responsable RSE"

    def test_energy_buyer_mention_focuses_eur_mwh(self):
        """ENERGY_BUYER avec avg_price_eur_mwh → 'prix moyen X €/MWh'."""
        mention = compose_persona_mention(
            "Lucas",
            PersonaRole.ENERGY_BUYER,
            {"avg_price_eur_mwh": 87.5},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "Lucas" in mention
        assert "acheteur énergie" in mention
        assert "88 €/MWh" in mention or "87 €/MWh" in mention

    def test_csr_manager_mention_focuses_co2(self):
        """CSR_MANAGER avec emissions_tco2e → 'émissions X tCO₂e'."""
        mention = compose_persona_mention(
            "Inès",
            PersonaRole.CSR_MANAGER,
            {"emissions_tco2e": 1245},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "Inès" in mention
        assert "responsable RSE" in mention
        assert "1245 tCO₂e" in mention or "1 245 tCO₂e" in mention
        assert "scope" in mention.lower()


class TestPhase4bis3TypologyAwareCommerce:
    """Audit Hervé : OWNER_COMMERCE clinique → typology-aware via NAF."""

    def test_owner_commerce_with_naf_4724z_uses_boulanger(self):
        """NAF 4724Z (boulangerie) → libellé 'boulanger', pas 'propriétaire'."""
        mention = compose_persona_mention(
            "Hervé",
            PersonaRole.OWNER_COMMERCE,
            {"surcout_eur_mois": 230},
            OrganizationTypology.COMMERCE,
            naf_code="4724Z",
        )
        assert "Hervé" in mention
        assert "boulanger" in mention
        assert "propriétaire" not in mention  # remplacé par métier réel
        assert "230 €" in mention

    def test_owner_commerce_with_naf_5610a_uses_restaurateur(self):
        """NAF 5610A (restaurant) → libellé 'restaurateur'."""
        mention = compose_persona_mention(
            "Sophie",
            PersonaRole.OWNER_COMMERCE,
            {"surcout_eur_mois": 450},
            OrganizationTypology.COMMERCE,
            naf_code="5610A",
        )
        assert "restaurateur" in mention

    def test_owner_commerce_with_naf_5510z_uses_hotelier(self):
        """NAF 5510Z (hôtel) → libellé 'hôtelier'."""
        mention = compose_persona_mention(
            "Marc",
            PersonaRole.OWNER_COMMERCE,
            {},
            OrganizationTypology.COMMERCE,
            naf_code="5510Z",
        )
        assert "hôtelier" in mention

    def test_owner_commerce_without_naf_falls_back_proprietaire(self):
        """NAF absent → fallback 'propriétaire' (rétrocompat)."""
        mention = compose_persona_mention(
            "Test",
            PersonaRole.OWNER_COMMERCE,
            {},
            OrganizationTypology.COMMERCE,
        )
        assert "propriétaire" in mention

    def test_cfo_role_unchanged_by_naf_code(self):
        """NAF code n'affecte pas CFO/DG/etc — uniquement OWNER_COMMERCE."""
        mention = compose_persona_mention(
            "Marie",
            PersonaRole.CFO,
            {"exposure_eur": 10000},
            OrganizationTypology.GRAND_GROUPE,
            naf_code="4724Z",  # ignoré pour CFO
        )
        # Phase 8.B : Marie + GG → "Directrice Financière" (féminisé), pas "DAF"
        assert "Financier" in mention or "Financière" in mention or "DAF" in mention
        assert "boulanger" not in mention


# ─── Phase 8.B — Féminisation + DAF/CFO context-aware ─────────────────────


class TestPhase8bFeminisation:
    """Audit final P1 : féminisation rôles + libellé GG CFO context-aware."""

    def test_anne_directrice_etablissement(self):
        """Anne (prénom féminin) + DIRECTOR_ERP → 'directrice d'établissement'."""
        mention = compose_persona_mention(
            "Anne",
            PersonaRole.DIRECTOR_ERP,
            {"compliance_score": 64},
            OrganizationTypology.ERP,
        )
        assert "directrice d'établissement" in mention
        assert "directeur d'établissement" not in mention

    def test_paul_directeur_etablissement(self):
        """Paul (prénom masculin) + DIRECTOR_ERP → 'directeur d'établissement'."""
        mention = compose_persona_mention(
            "Paul",
            PersonaRole.DIRECTOR_ERP,
            {"compliance_score": 64},
            OrganizationTypology.ERP,
        )
        assert "directeur d'établissement" in mention

    def test_pierre_keeps_masculine_despite_e_ending(self):
        """Pierre (masculin malgré -e) → masculin (exception explicite)."""
        mention = compose_persona_mention(
            "Pierre",
            PersonaRole.DIRECTOR_ERP,
            {"compliance_score": 64},
            OrganizationTypology.ERP,
        )
        assert "directeur d'établissement" in mention

    def test_jean_marc_cfo_grand_groupe_uses_directeur_financier(self):
        """Jean-Marc + CFO + GRAND_GROUPE → 'Directeur Financier' (audit final CX)."""
        mention = compose_persona_mention(
            "Jean-Marc",
            PersonaRole.CFO,
            {"exposure_eur": 156700, "compliance_score": 68},
            OrganizationTypology.GRAND_GROUPE,
        )
        # Audit final : "DAF" pour grand groupe coté grince → "Directeur Financier"
        assert "Directeur Financier" in mention
        # Vérifier qu'on n'utilise PAS le label par défaut "DAF" (avec espace mot)
        assert "DAF :" not in mention

    def test_marie_cfo_grand_groupe_uses_directrice_financiere(self):
        """Marie + CFO + GRAND_GROUPE → 'Directrice Financière' (féminisé)."""
        mention = compose_persona_mention(
            "Marie",
            PersonaRole.CFO,
            {"exposure_eur": 42000, "compliance_score": 76},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "Directrice Financière" in mention

    def test_inès_csr_manager_no_change(self):
        """CSR_MANAGER 'responsable RSE' déjà épicène — pas de changement."""
        mention = compose_persona_mention(
            "Inès",
            PersonaRole.CSR_MANAGER,
            {"emissions_tco2e": 1245},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "responsable RSE" in mention

    def test_lucas_energy_buyer_default(self):
        """Lucas (masculin) + ENERGY_BUYER → 'acheteur énergie'."""
        mention = compose_persona_mention(
            "Lucas",
            PersonaRole.ENERGY_BUYER,
            {"avg_price_eur_mwh": 87.5},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "acheteur énergie" in mention

    def test_sophie_energy_buyer_feminine(self):
        """Sophie (féminin) + ENERGY_BUYER → 'acheteuse énergie' (Phase 8.B)."""
        mention = compose_persona_mention(
            "Sophie",
            PersonaRole.ENERGY_BUYER,
            {"avg_price_eur_mwh": 87.5},
            OrganizationTypology.GRAND_GROUPE,
        )
        assert "acheteuse énergie" in mention


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
