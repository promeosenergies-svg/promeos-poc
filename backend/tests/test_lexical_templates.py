"""Phase 1.3 — Source-guards templates lexicaux par typologie.

Vérifie :
1. Templates GRAND_GROUPE contiennent "patrimoine"
2. Templates COMMERCE contiennent "{activity}" (substituable)
3. Templates ERP contiennent "établissement"
4. Templates COMMERCE ne contiennent JAMAIS "CODIR"
5. Templates COMMERCE ne contiennent JAMAIS "patrimoine"
6. Templates ERP ne contiennent JAMAIS "CODIR"
7. `get_activity_name` retourne les bons noms métier
8. `render_scope_singular` interpole correctement {activity}

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.3.
"""

from __future__ import annotations

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from services.narrative.lexical_templates import (
    LEXICAL_TEMPLATES,
    NAF_TO_ACTIVITY_NAME,
    get_activity_name,
    get_template,
    render_scope_singular,
)


class TestLexicalTemplatesGrandGroupe:
    """Source-guards templates GRAND_GROUPE."""

    def test_lexical_template_grand_groupe_uses_patrimoine(self):
        """Templates GRAND_GROUPE mentionnent 'patrimoine'."""
        scope = get_template(OrganizationTypology.GRAND_GROUPE, "scope_singular")
        assert "patrimoine" in scope, f"GRAND_GROUPE scope_singular doit mentionner 'patrimoine', trouvé : {scope!r}"

    def test_lexical_template_grand_groupe_uses_codir(self):
        """Templates GRAND_GROUPE utilisent 'CODIR' comme decision_short."""
        decision_short = get_template(OrganizationTypology.GRAND_GROUPE, "decision_short")
        assert decision_short == "CODIR"

    def test_lexical_template_grand_groupe_no_eleves(self):
        """Templates GRAND_GROUPE ne contiennent jamais 'élèves'/'résidents'/'usagers'."""
        templates = LEXICAL_TEMPLATES[OrganizationTypology.GRAND_GROUPE]
        for key, value in templates.items():
            if isinstance(value, str):
                lower = value.lower()
                assert "élèves" not in lower, f"GRAND_GROUPE.{key}={value!r} ne doit pas contenir 'élèves'"
                assert "résidents" not in lower, f"GRAND_GROUPE.{key}={value!r} ne doit pas contenir 'résidents'"
                assert "usagers" not in lower, f"GRAND_GROUPE.{key}={value!r} ne doit pas contenir 'usagers'"


class TestLexicalTemplatesCommerce:
    """Source-guards templates COMMERCE — interdiction stricte CODIR/patrimoine."""

    def test_lexical_template_commerce_uses_activity(self):
        """Template COMMERCE contient '{activity}' (substituable)."""
        scope = get_template(OrganizationTypology.COMMERCE, "scope_singular")
        assert "{activity}" in scope, (
            f"COMMERCE scope_singular doit contenir '{{activity}}' substituable, trouvé : {scope!r}"
        )

    def test_lexical_template_commerce_no_codir(self):
        """Template COMMERCE ne contient JAMAIS 'CODIR' (concept ETI/ETI privé)."""
        templates = LEXICAL_TEMPLATES[OrganizationTypology.COMMERCE]
        for key, value in templates.items():
            if isinstance(value, str):
                assert "CODIR" not in value, (
                    f"COMMERCE.{key}={value!r} ne doit JAMAIS contenir 'CODIR' "
                    f"(concept incompatible avec un commerçant indépendant)"
                )

    def test_lexical_template_commerce_no_patrimoine(self):
        """Template COMMERCE ne contient JAMAIS 'patrimoine'."""
        templates = LEXICAL_TEMPLATES[OrganizationTypology.COMMERCE]
        for key, value in templates.items():
            if isinstance(value, str):
                assert "patrimoine" not in value.lower(), (
                    f"COMMERCE.{key}={value!r} ne doit JAMAIS contenir 'patrimoine' "
                    f"(vocabulaire ETI tertiaire incompatible avec commerçant)"
                )

    def test_lexical_template_commerce_uses_proprietaire(self):
        """Template COMMERCE utilise 'propriétaire' comme owner_term."""
        owner = get_template(OrganizationTypology.COMMERCE, "owner_term")
        assert owner == "propriétaire"

    def test_lexical_template_commerce_audience_pedagogique(self):
        """Template COMMERCE registre 'pédagogique' (vs expert pour GG)."""
        audience = get_template(OrganizationTypology.COMMERCE, "regulatory_audience")
        assert "pédagogique" in audience


class TestLexicalTemplatesERP:
    """Source-guards templates ERP — pas de CODIR, vocabulaire service public."""

    def test_lexical_template_erp_uses_etablissement(self):
        """Template ERP contient 'établissement'."""
        scope = get_template(OrganizationTypology.ERP, "scope_singular")
        assert "établissement" in scope, f"ERP scope_singular doit contenir 'établissement', trouvé : {scope!r}"

    def test_lexical_template_erp_no_codir(self):
        """Template ERP ne contient JAMAIS 'CODIR' (utilise 'comité de direction')."""
        templates = LEXICAL_TEMPLATES[OrganizationTypology.ERP]
        for key, value in templates.items():
            if isinstance(value, str):
                assert "CODIR" not in value, (
                    f"ERP.{key}={value!r} ne doit JAMAIS contenir 'CODIR' "
                    f"(ERP utilise 'comité de direction' ou 'conseil d'administration')"
                )

    def test_lexical_template_erp_no_patrimoine(self):
        """Template ERP ne contient JAMAIS 'patrimoine' (concept GG privé)."""
        templates = LEXICAL_TEMPLATES[OrganizationTypology.ERP]
        for key, value in templates.items():
            if isinstance(value, str):
                assert "patrimoine" not in value.lower(), f"ERP.{key}={value!r} ne doit JAMAIS contenir 'patrimoine'"

    def test_lexical_template_erp_decision_body(self):
        """Template ERP utilise 'conseil d'administration' ou 'comité de direction'."""
        decision_body = get_template(OrganizationTypology.ERP, "decision_body")
        assert "conseil" in decision_body or "comité" in decision_body


class TestActivityName:
    """Source-guards mapping NAF → nom métier (Commerce)."""

    def test_get_activity_name_boulangerie(self):
        assert get_activity_name("4724Z") == "boulangerie"

    def test_get_activity_name_supermarche(self):
        assert get_activity_name("4711E") == "supermarché"
        assert get_activity_name("4711F") == "hypermarché"

    def test_get_activity_name_hotel(self):
        assert get_activity_name("5510Z") == "hôtel"

    def test_get_activity_name_restaurant(self):
        assert get_activity_name("5610A") == "restaurant"

    def test_get_activity_name_pharmacie(self):
        assert get_activity_name("4773Z") == "pharmacie"

    def test_get_activity_name_unknown_naf_fallback(self):
        """NAF non mappé → fallback 'magasin'."""
        assert get_activity_name("ZZZZZ") == "magasin"
        assert get_activity_name(None) == "magasin"
        assert get_activity_name("") == "magasin"

    def test_get_activity_name_custom_fallback(self):
        """Fallback personnalisable."""
        assert get_activity_name(None, fallback="commerce") == "commerce"


class TestRenderScopeSingular:
    """Source-guards interpolation `{activity}` dans scope_singular."""

    def test_render_scope_singular_commerce_boulangerie(self):
        """COMMERCE + NAF 4724Z → 'votre boulangerie'."""
        result = render_scope_singular(OrganizationTypology.COMMERCE, "4724Z")
        assert result == "votre boulangerie"

    def test_render_scope_singular_commerce_hotel(self):
        """COMMERCE + NAF 5510Z → 'votre hôtel'."""
        result = render_scope_singular(OrganizationTypology.COMMERCE, "5510Z")
        assert result == "votre hôtel"

    def test_render_scope_singular_grand_groupe_no_interpolation(self):
        """GRAND_GROUPE → 'votre patrimoine' (pas d'interpolation)."""
        result = render_scope_singular(OrganizationTypology.GRAND_GROUPE, "6420Z")
        assert result == "votre patrimoine"
        # NAF None ne change rien
        assert render_scope_singular(OrganizationTypology.GRAND_GROUPE, None) == "votre patrimoine"

    def test_render_scope_singular_erp_no_interpolation(self):
        """ERP → 'votre établissement' (pas d'interpolation)."""
        result = render_scope_singular(OrganizationTypology.ERP, "8510Z")
        assert result == "votre établissement"

    def test_render_scope_singular_unknown_fallback(self):
        """UNKNOWN → 'votre périmètre' (template fallback)."""
        result = render_scope_singular(OrganizationTypology.UNKNOWN, None)
        assert result == "votre périmètre"

    def test_render_scope_singular_commerce_unknown_naf_fallback(self):
        """COMMERCE + NAF inconnu → 'votre magasin' (fallback activity)."""
        result = render_scope_singular(OrganizationTypology.COMMERCE, "ZZZZZ")
        assert result == "votre magasin"


class TestTemplateCoverage:
    """Couverture mapping et clés canoniques."""

    def test_all_typologies_have_templates(self):
        """Les 4 membres OrganizationTypology ont un template défini."""
        for typology in OrganizationTypology:
            assert typology in LEXICAL_TEMPLATES, f"{typology} doit avoir un template"

    def test_all_templates_have_canonical_keys(self):
        """Tous les templates exposent les 12 clés canoniques."""
        canonical_keys = {
            "scope_singular",
            "scope_plural",
            "decision_body",
            "decision_short",
            "owner_term",
            "owner_alt_term",
            "structural_term",
            "structural_term_alt",
            "regulatory_audience",
            "avg_lecture_seconds",
            "improvement_term",
            "degradation_term",
        }
        for typology, template in LEXICAL_TEMPLATES.items():
            missing = canonical_keys - set(template.keys())
            assert not missing, f"{typology} manque les clés : {missing}"

    def test_get_template_fallback_safe(self):
        """get_template avec clé inconnue → fallback safe (chaîne vide)."""
        assert get_template(OrganizationTypology.GRAND_GROUPE, "key_inexistante") == ""
        assert get_template(OrganizationTypology.GRAND_GROUPE, "key_inexistante", fallback="X") == "X"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
