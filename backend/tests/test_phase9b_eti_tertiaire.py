"""Phase 9.B — Source-guards typologie ETI_TERTIAIRE.

Vérifie l'ajout V2 de la typologie ETI_TERTIAIRE (audit Marie midmarket) :

1. Enum `OrganizationTypology.ETI_TERTIAIRE` existe
2. Bascule GG → ETI_TERTIAIRE selon seuils taille (≤ 30 sites OU ≤ 100k m²)
3. lexical_templates ETI_TERTIAIRE défini (12 clés canoniques)
4. SENTENCE_STABLE_TEMPLATES ETI_TERTIAIRE défini (avec "parc" pas "patrimoine")
5. Composers ETI_TERTIAIRE : DT_drift / MAJOR_ANOMALY / AUDIT_DEADLINE / PURCHASE_WINDOW
6. MASKED_TRIGGERS_BY_TYPOLOGY[ETI_TERTIAIRE] = set() (tous triggers actifs)

Audit final ticket BL-3 closé. Marie ETI tertiaire midmarket reçoit désormais
sa propre voix (parc / DAF / comité de direction) au lieu de tomber sur
GRAND_GROUPE (patrimoine / CODIR).

Ref : audit final 2026-05-01 + Phase 9.B.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import MASKED_TRIGGERS_BY_TYPOLOGY
from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)
from services.narrative.lexical_templates import LEXICAL_TEMPLATES
from services.narrative.sentence_composer import (
    SENTENCE_STABLE_TEMPLATES,
    compose_audit_deadline_sentence,
    compose_dt_drift_sentence,
    compose_major_anomaly_sentence,
    compose_purchase_window_sentence,
)
from services.narrative.typology_resolver import (
    ETI_TERTIAIRE_MAX_SITES,
    ETI_TERTIAIRE_MAX_SURFACE_M2,
    _typology_dominant_for_sites,
)


# ─── Enum membership ────────────────────────────────────────────────────────


class TestEnumExtension:
    def test_eti_tertiaire_in_enum(self):
        assert OrganizationTypology.ETI_TERTIAIRE.value == "eti_tertiaire"

    def test_enum_has_6_typologies(self):
        """Phase 9.B + 11.C : 6 typologies (GG / ETI / COMMERCE / ERP / INDUSTRIE / UNKNOWN)."""
        assert len(list(OrganizationTypology)) == 6


# ─── Threshold logic ───────────────────────────────────────────────────────


def _mock_site(naf: str, surface: float):
    return SimpleNamespace(nom=f"Site {naf}", naf_code=naf, surface_m2=surface)


class TestEtiThreshold:
    """Source-guards seuils ETI_TERTIAIRE_MAX_SITES + ETI_TERTIAIRE_MAX_SURFACE_M2."""

    def test_eti_threshold_constants_exposed(self):
        assert ETI_TERTIAIRE_MAX_SITES == 30
        assert ETI_TERTIAIRE_MAX_SURFACE_M2 == 100_000.0

    def test_marie_eti_5_sites_35k_m2(self):
        """Marie audit : 5 sites bureaux 35k m² → ETI_TERTIAIRE (non GG)."""
        sites = [_mock_site("6820B", 7000)] * 5  # 5 sites, 35k m²
        result = _typology_dominant_for_sites(sites, scope_label="marie")
        assert result == OrganizationTypology.ETI_TERTIAIRE

    def test_helios_15_sites_under_threshold_eti(self):
        """HELIOS-like 15 sites 35k m² → ETI (≤ 30 sites + ≤ 100k m²)."""
        sites = [_mock_site("6820B", 2333)] * 15
        result = _typology_dominant_for_sites(sites, scope_label="helios")
        assert result == OrganizationTypology.ETI_TERTIAIRE

    def test_grand_groupe_50_sites_125k_above_both_thresholds(self):
        """50 sites > 30 ET 125k m² > 100k → GRAND_GROUPE (les 2 dépassés OR)."""
        sites = [_mock_site("6820B", 2500)] * 50  # 50 sites × 2500 = 125k m²
        result = _typology_dominant_for_sites(sites, scope_label="grand_groupe")
        assert result == OrganizationTypology.GRAND_GROUPE

    def test_eti_35_sites_40k_surface_below_one_threshold(self):
        """Phase 9.B.bis (mini-audit P1) : 35 sites > 30 MAIS 40k m² < 100k
        → ETI_TERTIAIRE (la condition OR : surface sous seuil suffit).

        Avant correction AND : ce cas restait GG (sites > 30). Après OR :
        bascule ETI car surface modeste = ETI midmarket.
        """
        sites = [_mock_site("6820B", 1143)] * 35  # 35 sites × 1143 ≈ 40k m²
        result = _typology_dominant_for_sites(sites, scope_label="eti_31_50")
        assert result == OrganizationTypology.ETI_TERTIAIRE

    def test_grand_groupe_huge_surface_only_1_site(self):
        """1 site 200k m² > 100k → GG car surface dépasse, malgré 1 site < 30.

        Note : avec OR (sites ≤ 30 OU surface ≤ 100k), 1 site ≤ 30 donc
        bascule ETI. Pour rester GG, il faut les 2 dépassés. Donc 1 site
        200k m² → ETI (1 ≤ 30). C'est le test d'origine qui a changé de
        signification avec OR — adapter pour vérifier le cas réel GG.
        """
        # Cas réel GG : 100 sites × 5k m² = 500k m² (sites > 30 ET surface > 100k)
        sites = [_mock_site("6820B", 5000)] * 100
        result = _typology_dominant_for_sites(sites, scope_label="huge")
        assert result == OrganizationTypology.GRAND_GROUPE

    def test_commerce_unaffected_by_eti_threshold(self):
        """COMMERCE pas affecté par seuils ETI (s'applique uniquement à GG)."""
        sites = [_mock_site("4724Z", 100)]  # boulangerie 100 m²
        result = _typology_dominant_for_sites(sites, scope_label="boulanger")
        assert result == OrganizationTypology.COMMERCE

    def test_erp_unaffected_by_eti_threshold(self):
        sites = [_mock_site("8510Z", 800)]
        result = _typology_dominant_for_sites(sites, scope_label="ecole")
        assert result == OrganizationTypology.ERP


# ─── Lexical templates ─────────────────────────────────────────────────────


class TestLexicalTemplatesEti:
    """ETI_TERTIAIRE templates : 'parc' au lieu de 'patrimoine', DAF pas CODIR."""

    def test_eti_tertiaire_in_lexical_templates(self):
        assert OrganizationTypology.ETI_TERTIAIRE in LEXICAL_TEMPLATES

    def test_eti_uses_parc_not_patrimoine(self):
        templates = LEXICAL_TEMPLATES[OrganizationTypology.ETI_TERTIAIRE]
        assert templates["scope_singular"] == "votre parc"
        assert "patrimoine" not in str(templates).lower()

    def test_eti_no_codir(self):
        templates = LEXICAL_TEMPLATES[OrganizationTypology.ETI_TERTIAIRE]
        for value in templates.values():
            if isinstance(value, str):
                assert "CODIR" not in value, f"ETI_TERTIAIRE ne doit pas contenir CODIR : {value!r}"

    def test_eti_uses_daf(self):
        templates = LEXICAL_TEMPLATES[OrganizationTypology.ETI_TERTIAIRE]
        assert templates["owner_term"] == "DAF"

    def test_eti_lecture_seconds_intermediate(self):
        """ETI = 90s (entre GG 180 et COMMERCE 60)."""
        templates = LEXICAL_TEMPLATES[OrganizationTypology.ETI_TERTIAIRE]
        assert templates["avg_lecture_seconds"] == 90


# ─── Stable sentences ──────────────────────────────────────────────────────


class TestStableSentenceEti:
    def test_eti_stable_uses_parc(self):
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.ETI_TERTIAIRE]
        assert "parc" in sentence
        assert "patrimoine" not in sentence

    def test_eti_stable_no_codir(self):
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.ETI_TERTIAIRE]
        assert "CODIR" not in sentence

    def test_eti_stable_has_focus_action(self):
        """Phase 8.C : stable doit avoir 'Focus prochain ...' (action implicite)."""
        sentence = SENTENCE_STABLE_TEMPLATES[OrganizationTypology.ETI_TERTIAIRE]
        assert "Focus" in sentence


# ─── Composers ETI ─────────────────────────────────────────────────────────


def _make_event(event_type: str, title: str = "Test"):
    return SolEventCard(
        id=f"{event_type}:test",
        event_type=event_type,
        severity="warning",
        title=title,
        narrative="Test",
        impact=EventImpact(value=10.0, unit="%", period="week"),
        source=EventSource(
            system="RegOps",
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=[1, 2]),
    )


class TestComposersEti:
    def test_dt_drift_eti_uses_parc(self):
        event = _make_event("consumption_drift")
        sentence = compose_dt_drift_sentence(event, OrganizationTypology.ETI_TERTIAIRE)
        assert "parc" in sentence
        assert "patrimoine" not in sentence
        assert "Décret Tertiaire" in sentence

    def test_major_anomaly_eti_uses_parc(self):
        event = _make_event("billing_anomaly", "Surfacturation TURPE")
        sentence = compose_major_anomaly_sentence(event, OrganizationTypology.ETI_TERTIAIRE)
        assert "parc" in sentence
        assert "TURPE" in sentence  # sigle préservé

    def test_audit_deadline_eti_uses_parc(self):
        event = _make_event("compliance_deadline", "OPERAT 30/09")
        sentence = compose_audit_deadline_sentence(event, OrganizationTypology.ETI_TERTIAIRE)
        assert "parc" in sentence
        assert "OPERAT" in sentence

    def test_purchase_window_eti_uses_parc(self):
        event = _make_event("contract_renewal", "Renégociation")
        sentence = compose_purchase_window_sentence(event, OrganizationTypology.ETI_TERTIAIRE)
        assert "parc" in sentence


# ─── Triggers masqués ──────────────────────────────────────────────────────


class TestMaskedTriggersEti:
    def test_eti_no_triggers_masked(self):
        """ETI_TERTIAIRE = audience expert-praticien → tous triggers actifs."""
        assert MASKED_TRIGGERS_BY_TYPOLOGY[OrganizationTypology.ETI_TERTIAIRE] == set()


# ─── Phase 9.B.bis — Source-guard enum coverage (mini-audit P2) ──────────


class TestEnumCoverageGuard:
    """Source-guard : tous les membres OrganizationTypology doivent être
    présents dans MASKED_TRIGGERS_BY_TYPOLOGY + LEXICAL_TEMPLATES +
    SENTENCE_STABLE_TEMPLATES. Empêche un futur ajout d'enum d'introduire
    un KeyError silencieux.
    """

    def test_masked_triggers_covers_all_enum_members(self):
        assert set(MASKED_TRIGGERS_BY_TYPOLOGY) == set(OrganizationTypology), (
            "Tous les OrganizationTypology doivent avoir une entrée "
            "dans MASKED_TRIGGERS_BY_TYPOLOGY (anti-KeyError runtime)."
        )

    def test_lexical_templates_covers_all_enum_members(self):
        assert set(LEXICAL_TEMPLATES) == set(OrganizationTypology), (
            "Tous les OrganizationTypology doivent avoir une entrée dans LEXICAL_TEMPLATES."
        )

    def test_stable_sentences_covers_all_enum_members(self):
        assert set(SENTENCE_STABLE_TEMPLATES) == set(OrganizationTypology), (
            "Tous les OrganizationTypology doivent avoir une entrée dans SENTENCE_STABLE_TEMPLATES."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
