"""Phase 9.C — Source-guards i18n infrastructure narrative.

Vérifie l'infrastructure d'internationalisation minimale (FR + EN squelette) :

1. Locale enum (FR par défaut, EN squelette)
2. `t(key, locale, **kwargs)` résout + interpole + fallback FR
3. Clé absente → format `[key]` (signal de bug)
4. Couverture FR : toutes les clés narrative canoniques sont présentes
5. Couverture EN : skeleton MVP (~30%) + fallback automatique sur FR
6. Cohérence cross-locale : pas de placeholder différent FR vs EN

Audit final ticket BL-5 closé Phase 9.C MVP. Migration des composers
vers `t()` reportée V2 (sprint dédié post panel UK).

Ref : sprint narrative-sol2 Phase 9.C.
"""

from __future__ import annotations

import re

import pytest

from services.narrative.i18n import (
    DEFAULT_LOCALE,
    Locale,
    list_keys,
    t,
)


# ─── Locale enum + default ─────────────────────────────────────────────────


class TestLocaleEnum:
    def test_locale_fr_value(self):
        assert Locale.FR.value == "fr"

    def test_locale_en_value(self):
        assert Locale.EN.value == "en"

    def test_default_locale_is_fr(self):
        assert DEFAULT_LOCALE == Locale.FR


# ─── Résolution simple ─────────────────────────────────────────────────────


class TestTBasicResolution:
    def test_t_resolves_fr_default(self):
        """t() sans locale → FR (default)."""
        result = t("stable.grand_groupe")
        assert "patrimoine" in result
        assert "trajectoire" in result

    def test_t_resolves_explicit_fr(self):
        result = t("stable.commerce", Locale.FR)
        assert "activité" in result

    def test_t_resolves_en_skeleton(self):
        """EN skeleton : phrases stables sont traduites."""
        result = t("stable.grand_groupe", Locale.EN)
        assert "portfolio" in result
        assert "patrimoine" not in result


# ─── Fallback automatique FR ───────────────────────────────────────────────


class TestTFallbackFr:
    """Si une clé EN est absente, fallback automatique sur FR."""

    def test_en_fallback_to_fr_for_missing_key(self):
        """`composer.dt_drift.grand_groupe` n'est pas traduit EN MVP →
        fallback automatique sur FR."""
        result_en = t("composer.dt_drift.grand_groupe", Locale.EN)
        result_fr = t("composer.dt_drift.grand_groupe", Locale.FR)
        # EN tombe sur FR (skeleton incomplet)
        assert result_en == result_fr

    def test_unknown_key_returns_bracketed_signal(self):
        """Clé inexistante → `[key]` littéral pour debug."""
        result = t("non.existing.key.xyz")
        assert result == "[non.existing.key.xyz]"


# ─── Interpolation kwargs ──────────────────────────────────────────────────


class TestTInterpolation:
    def test_t_interpolates_simple_var(self):
        result = t("source_suffix", Locale.FR, source="RegOps", confidence="haute")
        assert "RegOps" in result
        assert "haute" in result

    def test_t_safe_on_missing_kwarg(self):
        """Si une variable kwargs manque → retourne template brut (pas crash)."""
        # `source_suffix` template : `(source {source}, confiance {confidence})`
        # On ne passe pas confidence → fallback sur template brut
        result = t("source_suffix", Locale.FR, source="RegOps")
        # Ne crash pas
        assert isinstance(result, str)


# ─── Couverture clés cross-locale ──────────────────────────────────────────


class TestCatalogCoverage:
    """Source-guards : couverture clés essentielles."""

    def test_fr_catalog_has_all_5_stable_typologies(self):
        """FR doit avoir les 5 phrases stables (1 par OrganizationTypology)."""
        for typology_value in (
            "grand_groupe",
            "eti_tertiaire",
            "commerce",
            "erp",
            "unknown",
        ):
            result = t(f"stable.{typology_value}", Locale.FR)
            assert not result.startswith("["), f"Clé `stable.{typology_value}` manquante en FR"

    def test_fr_catalog_has_all_4_event_composers(self):
        """FR doit avoir les composers DT/MAJOR/AUDIT/PURCHASE × {GG,ETI,COMMERCE,ERP}."""
        triggers = ("dt_drift", "major_anomaly", "audit_deadline", "purchase_window")
        typologies = ("grand_groupe", "eti_tertiaire", "commerce", "erp")
        for trigger in triggers:
            for typology in typologies:
                key = f"composer.{trigger}.{typology}"
                result = t(key, Locale.FR)
                assert not result.startswith("["), f"Clé `{key}` manquante en FR (Phase 9.C MVP)"

    def test_fr_catalog_has_role_labels(self):
        """FR catalog couvre rôles persona core."""
        for role in ("dg", "cfo", "director_erp", "owner_commerce", "energy_manager"):
            key = f"role.{role}.default"
            result = t(key, Locale.FR)
            assert not result.startswith("[")

    def test_en_skeleton_has_stable_typologies(self):
        """EN MVP skeleton : 5 phrases stables traduites (audit Marie demande EN démo)."""
        for typology_value in ("grand_groupe", "eti_tertiaire", "commerce", "erp", "unknown"):
            key = f"stable.{typology_value}"
            # Pas de fallback FR : on veut une vraie traduction EN
            from services.narrative.i18n import _CATALOGS

            assert key in _CATALOGS[Locale.EN], f"Clé `{key}` absente EN skeleton"

    def test_en_skeleton_role_cfo_translated(self):
        """role.cfo.default traduit EN (CFO/CEO/CSR essentiels)."""
        result_en = t("role.cfo.default", Locale.EN)
        # EN doit dire "CFO", pas "DAF" français
        assert result_en == "CFO"


class TestCrossLocaleConsistency:
    """Source-guard : placeholders cohérents FR vs EN (sinon interpolation casse)."""

    def test_placeholders_match_fr_en_for_translated_keys(self):
        """Pour chaque clé présente dans EN ET FR, les placeholders {x}
        doivent être identiques (sinon `t(key, EN, kwargs)` plante)."""
        from services.narrative.i18n import _CATALOGS

        fr_catalog = _CATALOGS[Locale.FR]
        en_catalog = _CATALOGS[Locale.EN]

        # Clés présentes dans les deux
        common_keys = set(fr_catalog.keys()) & set(en_catalog.keys())

        placeholder_re = re.compile(r"\{(\w+)\}")
        for key in common_keys:
            fr_placeholders = set(placeholder_re.findall(fr_catalog[key]))
            en_placeholders = set(placeholder_re.findall(en_catalog[key]))
            assert fr_placeholders == en_placeholders, (
                f"Placeholders divergents pour `{key}` : FR={fr_placeholders} vs EN={en_placeholders}"
            )


# ─── List keys (introspection) ─────────────────────────────────────────────


class TestListKeys:
    def test_list_keys_returns_sorted_list(self):
        keys_fr = list_keys(Locale.FR)
        assert isinstance(keys_fr, list)
        assert keys_fr == sorted(keys_fr)
        assert len(keys_fr) > 20  # MVP a ~30+ clés

    def test_list_keys_en_smaller_than_fr_skeleton_phase(self):
        """Phase 9.C MVP : EN skeleton < FR (composers non traduits)."""
        keys_fr = list_keys(Locale.FR)
        keys_en = list_keys(Locale.EN)
        assert len(keys_en) < len(keys_fr), (
            f"Phase 9.C MVP : EN doit être plus petit que FR (skeleton). FR={len(keys_fr)} EN={len(keys_en)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
