"""
PROMEOS — Step 7: Multi-org seed (HELIOS + MERIDIAN)
Verifie que le pack MERIDIAN existe, a 3 sites, et est isole de HELIOS.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── A. Pack definition ────────────────────────────────────────────────────────


class TestMeridianPack:
    """Tests sur la definition du pack MERIDIAN dans packs.py."""

    def test_meridian_pack_exists(self):
        from services.demo_seed.packs import get_pack

        pack = get_pack("meridian")
        assert pack is not None

    def test_meridian_pack_visible(self):
        from services.demo_seed.packs import get_pack

        pack = get_pack("meridian")
        assert pack.get("visible") is True

    def test_meridian_org_name(self):
        from services.demo_seed.packs import get_pack

        pack = get_pack("meridian")
        assert pack["org"]["nom"] == "MERIDIAN SAS"

    def test_meridian_org_siren_different_from_helios(self):
        from services.demo_seed.packs import get_pack

        helios = get_pack("helios")
        meridian = get_pack("meridian")
        assert helios["org"]["siren"] != meridian["org"]["siren"]

    def test_meridian_has_3_sites(self):
        from services.demo_seed.packs import get_pack

        pack = get_pack("meridian")
        assert len(pack["sites_explicit"]) == 3

    def test_meridian_site_names(self):
        from services.demo_seed.packs import get_pack

        pack = get_pack("meridian")
        names = [s["nom"] for s in pack["sites_explicit"]]
        assert any("Levallois" in n for n in names)
        assert any("Bordeaux" in n for n in names)
        assert any("Gennevilliers" in n for n in names)

    def test_meridian_has_1_entite(self):
        from services.demo_seed.packs import get_pack

        pack = get_pack("meridian")
        assert len(pack["entites"]) == 1

    def test_meridian_has_contracts(self):
        from services.demo_seed.packs import get_pack

        pack = get_pack("meridian")
        assert len(pack["contracts_spec"]) >= 3

    def test_meridian_in_list_packs(self):
        from services.demo_seed.packs import list_packs

        packs = list_packs()
        keys = [p["key"] for p in packs]
        assert "meridian" in keys

    def test_helios_still_in_list_packs(self):
        from services.demo_seed.packs import list_packs

        packs = list_packs()
        keys = [p["key"] for p in packs]
        assert "helios" in keys


# ── B. Pack isolation ─────────────────────────────────────────────────────────


class TestPackIsolation:
    """Verifie que HELIOS et MERIDIAN sont isoles."""

    def test_different_org_names(self):
        from services.demo_seed.packs import get_pack

        h = get_pack("helios")
        m = get_pack("meridian")
        assert h["org"]["nom"] != m["org"]["nom"]

    def test_no_overlapping_sites(self):
        from services.demo_seed.packs import get_pack

        h_names = {s["nom"] for s in get_pack("helios")["sites_explicit"]}
        m_names = {s["nom"] for s in get_pack("meridian")["sites_explicit"]}
        assert h_names.isdisjoint(m_names)

    def test_no_overlapping_entite_siren(self):
        from services.demo_seed.packs import get_pack

        h_sirens = {e["siren"] for e in get_pack("helios")["entites"]}
        m_sirens = {e["siren"] for e in get_pack("meridian")["entites"]}
        assert h_sirens.isdisjoint(m_sirens)


# ── C. CLI accepts meridian ──────────────────────────────────────────────────


class TestCli:
    """Tests sur le CLI demo_seed."""

    def test_cli_accepts_meridian(self):
        cli_path = os.path.join(
            os.path.dirname(__file__), "..", "services", "demo_seed", "__main__.py"
        )
        source = open(cli_path).read()
        assert "meridian" in source


# ── D. Site specs validity ───────────────────────────────────────────────────


class TestMeridianSiteSpecs:
    """Verifie les specs des 3 sites MERIDIAN."""

    def test_levallois_is_bureau(self):
        from services.demo_seed.packs import get_pack

        sites = get_pack("meridian")["sites_explicit"]
        lev = [s for s in sites if "Levallois" in s["nom"]][0]
        assert lev["type_site"] == "bureau"
        assert lev["surface_m2"] == 2200

    def test_bordeaux_is_bureau(self):
        from services.demo_seed.packs import get_pack

        sites = get_pack("meridian")["sites_explicit"]
        bdx = [s for s in sites if "Bordeaux" in s["nom"]][0]
        assert bdx["type_site"] == "bureau"
        assert bdx["surface_m2"] == 800

    def test_gennevilliers_is_entrepot(self):
        from services.demo_seed.packs import get_pack

        sites = get_pack("meridian")["sites_explicit"]
        gen = [s for s in sites if "Gennevilliers" in s["nom"]][0]
        assert gen["type_site"] == "entrepot"
        assert gen["surface_m2"] == 4500

    def test_all_sites_have_buildings(self):
        from services.demo_seed.packs import get_pack

        for site in get_pack("meridian")["sites_explicit"]:
            assert len(site["buildings"]) >= 1

    def test_all_sites_have_coordinates(self):
        from services.demo_seed.packs import get_pack

        for site in get_pack("meridian")["sites_explicit"]:
            assert site["lat"] is not None
            assert site["lon"] is not None


# ── E. Frontend multi-org support ────────────────────────────────────────────


class TestFrontendMultiOrg:
    """Source-guard: ScopeContext supporte multi-org."""

    def test_scope_context_has_demo_orgs(self):
        ctx_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "frontend",
            "src",
            "contexts",
            "ScopeContext.jsx",
        )
        source = open(ctx_path).read()
        assert "demoOrgs" in source
        assert "applyDemoScope" in source

    def test_scope_context_merges_orgs(self):
        ctx_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "frontend",
            "src",
            "contexts",
            "ScopeContext.jsx",
        )
        source = open(ctx_path).read()
        assert "MOCK_ORGS" in source
        assert "demoOrgs" in source
        # Merges both arrays
        assert "...MOCK_ORGS" in source
