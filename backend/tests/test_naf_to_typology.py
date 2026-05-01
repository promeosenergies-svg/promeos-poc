"""Phase 1.1 — Source-guards mapping NAF → typologie organisationnelle.

Vérifie que les 4 cas canoniques sont mappés correctement + le fallback
UNKNOWN ne lève jamais d'exception (robustesse contre NAF mal formés).

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.1.
"""

from __future__ import annotations

import pytest

from doctrine.naf_to_typology import (
    NAF_PREFIX_TO_TYPOLOGY,
    OrganizationTypology,
    resolve_typology,
)


class TestNafToTypology:
    """4 source-guards canoniques + couverture mapping."""

    def test_naf_to_typology_grand_groupe(self):
        """NAF 6420Z (holdings) → GRAND_GROUPE."""
        assert resolve_typology("6420Z") == OrganizationTypology.GRAND_GROUPE
        assert resolve_typology("7010Z") == OrganizationTypology.GRAND_GROUPE  # sièges sociaux
        assert resolve_typology("6810Z") == OrganizationTypology.GRAND_GROUPE  # foncières

    def test_naf_to_typology_commerce(self):
        """NAF 4724Z (boulangerie) → COMMERCE."""
        assert resolve_typology("4724Z") == OrganizationTypology.COMMERCE
        assert resolve_typology("4711F") == OrganizationTypology.COMMERCE  # supermarché
        assert resolve_typology("5630Z") == OrganizationTypology.COMMERCE  # restaurant
        assert resolve_typology("5510Z") == OrganizationTypology.COMMERCE  # hôtel privé

    def test_naf_to_typology_erp(self):
        """NAF 8510Z (école) → ERP."""
        assert resolve_typology("8510Z") == OrganizationTypology.ERP
        assert resolve_typology("8730A") == OrganizationTypology.ERP  # EHPAD
        assert resolve_typology("8610Z") == OrganizationTypology.ERP  # hôpital
        assert resolve_typology("9101Z") == OrganizationTypology.ERP  # bibliothèque

    def test_naf_to_typology_unknown_fallback(self):
        """NAF inconnu / None / vide → UNKNOWN (jamais d'exception).

        Robustesse : la narrative doit toujours pouvoir se construire,
        même si le NAF de l'entité est manquant ou mal formé.
        """
        assert resolve_typology(None) == OrganizationTypology.UNKNOWN
        assert resolve_typology("") == OrganizationTypology.UNKNOWN
        assert resolve_typology("Z") == OrganizationTypology.UNKNOWN  # 1 char
        assert resolve_typology("ZZZZZ") == OrganizationTypology.UNKNOWN  # NAF inexistant
        assert resolve_typology("0111Z") == OrganizationTypology.UNKNOWN  # agriculture (hors MVP)
        assert resolve_typology("2410Z") == OrganizationTypology.UNKNOWN  # sidérurgie (hors MVP)

    # ── Couverture mapping ────────────────────────────────────────────────

    def test_mapping_no_overlap(self):
        """Chaque préfixe NAF mappe vers une seule typologie (pas de collision)."""
        # Le mapping étant un dict, les collisions sont impossibles by-design.
        # On vérifie juste la non-vacuité et l'unicité des clés.
        assert len(NAF_PREFIX_TO_TYPOLOGY) >= 20
        prefixes = list(NAF_PREFIX_TO_TYPOLOGY.keys())
        assert len(prefixes) == len(set(prefixes))

    def test_all_prefixes_2_chars(self):
        """Tous les préfixes mappés font exactement 2 caractères."""
        for prefix in NAF_PREFIX_TO_TYPOLOGY:
            assert len(prefix) == 2, f"Préfixe {prefix!r} doit faire 2 chars (NAF rév 2)"

    def test_all_typologies_have_at_least_one_prefix(self):
        """Chaque typologie MVP est représentée par ≥ 1 préfixe NAF."""
        used_typologies = set(NAF_PREFIX_TO_TYPOLOGY.values())
        assert OrganizationTypology.GRAND_GROUPE in used_typologies
        assert OrganizationTypology.COMMERCE in used_typologies
        assert OrganizationTypology.ERP in used_typologies
        # UNKNOWN n'est jamais dans le mapping (c'est un fallback)
        assert OrganizationTypology.UNKNOWN not in used_typologies

    def test_helios_sites_typology(self):
        """Les 5 sites HELIOS seedés sont correctement classifiés.

        - Siège HELIOS Paris (NAF 6820B) → GRAND_GROUPE (immobilier 68)
        - Bureau Régional Lyon (NAF 6820B) → GRAND_GROUPE
        - Entrepôt Toulouse (NAF 5210B) → UNKNOWN (entreposage 52, hors MVP)
        - Hôtel HELIOS Nice (NAF 5510Z) → COMMERCE (hôtellerie privée)
        - École Jules Ferry Marseille (NAF 8520Z) → ERP (enseignement 85)
        """
        assert resolve_typology("6820B") == OrganizationTypology.GRAND_GROUPE
        assert resolve_typology("5210B") == OrganizationTypology.UNKNOWN
        assert resolve_typology("5510Z") == OrganizationTypology.COMMERCE
        assert resolve_typology("8520Z") == OrganizationTypology.ERP


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
