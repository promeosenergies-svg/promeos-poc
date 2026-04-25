"""
Tests simulateur facture annuelle post-ARENH (2026+).

Couvre :
    - décomposition complète (site avec CDC + archetype renseigné)
    - VNU dormant vs actif selon forward (seuil 78 EUR/MWh)
    - capacité RTE estimation unitaire
    - CBAM non applicable conso directe
    - fallback annual_kwh absent → 100 000 kWh + trace
    - cohérence somme composantes vs facture_totale_eur
    - baseline 2024 + delta calculé

Utilise SQLite in-memory + ParameterStore YAML (pas de DB tariff seed requis).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models import (
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    TypeSite,
)
from models.market_models import (
    MktPrice,
    MarketType,
    ProductType,
    PriceZone,
    MarketDataSource,
    Resolution,
)

from services.purchase.cost_simulator_2026 import (
    simulate_annual_cost_2026,
    FALLBACK_FORWARD_EUR_MWH,
    CAPACITE_UNITAIRE_EUR_MWH,
    DEFAULT_ANNUAL_KWH,
    BASELINE_2024_EUR_MWH_FALLBACK,
    VNU_SEUIL_DEFAUT_EUR_MWH,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_org_site(
    db,
    *,
    annual_kwh: float | None = 500_000.0,
    archetype_code: str | None = "COMMERCE_ALIMENTAIRE",
):
    """Helper : org + ej + pf + site minimal pour tests cost simulator."""
    import uuid

    siren = uuid.uuid4().hex[:9].upper()
    org = Organisation(nom=f"Test Corp {siren}", type_client="commerce", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom=f"Test Corp {siren}", siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Test PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site Carrefour Test",
        type=TypeSite.COMMERCE,
        adresse="1 rue Test",
        code_postal="75001",
        ville="Paris",
        surface_m2=2000.0,
        portefeuille_id=pf.id,
        annual_kwh_total=annual_kwh,
        archetype_code=archetype_code,
        naf_code="47.11F",
    )
    db.add(site)
    db.flush()
    return org, site


def _seed_forward(
    db,
    *,
    year: int = 2026,
    price_eur_mwh: float = 62.0,
):
    """Insère un forward baseload FR pour l'année donnée."""
    mp = MktPrice(
        source=MarketDataSource.MANUAL,
        market_type=MarketType.FORWARD_YEAR,
        product_type=ProductType.BASELOAD,
        zone=PriceZone.FR,
        delivery_start=datetime(year, 1, 1, tzinfo=timezone.utc),
        delivery_end=datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        price_eur_mwh=price_eur_mwh,
        resolution=Resolution.P1Y,
        fetched_at=datetime.now(timezone.utc),
    )
    db.add(mp)
    db.flush()
    return mp


# ── Tests ──────────────────────────────────────────────────────────────────


class TestSimulateFacture2026:
    def test_simulate_facture_2026_site_complet(self, db_session):
        """Site CDC 500 MWh + archetype COMMERCE_ALIMENTAIRE → décomposition non-nulle."""
        _, site = _make_org_site(db_session, annual_kwh=500_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        # Structure obligatoire (contrat agent B)
        assert result["site_id"] == str(site.id)
        assert result["year"] == 2026
        assert result["confiance"] == "indicative"
        assert "Post-ARENH" in result["source"]

        # Composantes toutes présentes
        comp = result["composantes"]
        assert set(comp.keys()) == {
            "fourniture_eur",
            "turpe_eur",
            "vnu_eur",
            "capacite_eur",
            "cbam_scope",
            "accise_cta_tva_eur",
        }

        # Fourniture = 500 MWh × 62 EUR/MWh × peakload_mult
        # COMMERCE_ALIMENTAIRE facteur_forme 0.55 → mult = 1 + 0.15 × 0.45 = 1.0675
        expected_fourniture = 500.0 * 62.0 * (1.0 + 0.15 * (1.0 - 0.55))
        assert comp["fourniture_eur"] == pytest.approx(expected_fourniture, rel=1e-3)

        # TURPE et taxes non-nulles (YAML résolu)
        assert comp["turpe_eur"] > 0
        assert comp["accise_cta_tva_eur"] > 0

        # Capacité : 500 MWh × 0.43 EUR/MWh = 215 EUR (aligné billing_engine)
        assert comp["capacite_eur"] == pytest.approx(500.0 * CAPACITE_UNITAIRE_EUR_MWH, rel=1e-3)

        # Énergie annuelle bien reportée
        assert result["energie_annuelle_mwh"] == pytest.approx(500.0, rel=1e-6)

        # Delta vs 2024 non-nul (la facture 2026 ne peut pas être exactement égale)
        assert result["delta_vs_2024_pct"] != 0

    def test_simulate_vnu_dormant_si_prix_bas(self, db_session):
        """Forward 60 EUR/MWh < seuil 78 → vnu_statut='dormant', vnu_eur=0."""
        _, site = _make_org_site(db_session, annual_kwh=300_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=60.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        assert result["hypotheses"]["vnu_statut"] == "dormant"
        assert result["composantes"]["vnu_eur"] == 0.0
        assert result["hypotheses"]["prix_forward_y1_eur_mwh"] == pytest.approx(60.0)

    def test_simulate_vnu_actif_statut_informatif_sans_impact_facture(self, db_session):
        """
        Fix P0 audit Sprint Achat : VNU est une taxe redistributive SUR EDF
        (art. L. 336-1 Code énergie), pas sur le consommateur final. La
        facture client doit rester à 0 même lorsque le statut est "actif" ;
        le risque upside s'expose dans `hypotheses` pour traçabilité.
        """
        _, site = _make_org_site(db_session, annual_kwh=400_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=90.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        # Statut informatif
        assert result["hypotheses"]["vnu_statut"] == "actif"
        # La facture client NE compte PAS le VNU — c'est la correction
        assert result["composantes"]["vnu_eur"] == 0.0
        # Risque upside tracé dans les hypothèses
        assert result["hypotheses"]["vnu_risque_upside_eur_mwh"] > 0
        # Seuil exposé
        assert result["hypotheses"]["vnu_seuil_active_eur_mwh"] == VNU_SEUIL_DEFAUT_EUR_MWH
        # Note pédagogique présente pour auditeur
        assert "taxe redistributive sur EDF" in result["hypotheses"]["vnu_note"]

    def test_simulate_capacite_aligne_billing_engine(self, db_session):
        """Capacité annuelle alignée sur billing_engine/catalog (0.43 EUR/MWh), plein exercice."""
        _, site = _make_org_site(db_session, annual_kwh=1_000_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)
        _seed_forward(db_session, year=2027, price_eur_mwh=62.0)

        result_2026 = simulate_annual_cost_2026(site, db_session, year=2026)
        result_2027 = simulate_annual_cost_2026(site, db_session, year=2027)

        # 1 000 MWh × 0.43 EUR/MWh = 430 EUR, indépendamment de l'année
        expected = 1_000.0 * CAPACITE_UNITAIRE_EUR_MWH
        assert result_2026["composantes"]["capacite_eur"] == pytest.approx(expected, rel=1e-3)
        assert result_2027["composantes"]["capacite_eur"] == pytest.approx(expected, rel=1e-3)
        assert result_2026["hypotheses"]["capacite_unitaire_eur_mwh"] == CAPACITE_UNITAIRE_EUR_MWH
        assert "billing_engine/catalog" in result_2026["hypotheses"]["capacite_source_ref"]

    def test_simulate_cbam_applicable_site_avec_imports(self, db_session):
        """Site avec imports CBAM déclarés → cbam_scope > 0, breakdown exposé."""
        _, site = _make_org_site(db_session, annual_kwh=500_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)
        # Simule un site industriel avec imports hors UE déclarés.
        site.cbam_imports_tonnes = {"acier": 100.0, "aluminium": 5.0}

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        # Exposition CBAM : 100 × 2.0 + 5 × 16.5 = 282.5 tCO2 × 75.36 = 21 289 €
        expected_cbam = (100.0 * 2.0 + 5.0 * 16.5) * 75.36
        assert result["composantes"]["cbam_scope"] == pytest.approx(expected_cbam, rel=1e-3)
        assert result["hypotheses"]["cbam_applicable"] is True
        assert result["hypotheses"]["cbam_total_co2_embedded_t"] == pytest.approx(282.5, rel=1e-3)
        assert len(result["hypotheses"]["cbam_breakdown"]) == 2
        scopes = {b["scope"] for b in result["hypotheses"]["cbam_breakdown"]}
        assert scopes == {"acier", "aluminium"}
        # Trace dans source_calibration
        assert any("cbam_applicable" in t for t in result["hypotheses"]["source_calibration"])

    def test_simulate_cbam_non_applicable(self, db_session):
        """CBAM = 0 EUR + trace documentée dans hypotheses."""
        _, site = _make_org_site(db_session, annual_kwh=500_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        assert result["composantes"]["cbam_scope"] == 0.0
        assert any("cbam_non_applicable" in t for t in result["hypotheses"]["source_calibration"])
        # Note pédagogique pour auditeur
        assert "CBAM" in result["hypotheses"]["cbam_note"]

    def test_simulate_annual_kwh_absent_fallback(self, db_session):
        """Site sans annual_kwh_total → fallback 100 000 kWh + trace."""
        _, site = _make_org_site(db_session, annual_kwh=None)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        # Énergie reportée = 100 MWh
        assert result["energie_annuelle_mwh"] == pytest.approx(DEFAULT_ANNUAL_KWH / 1000.0)
        assert result["hypotheses"]["annual_kwh_resolu"] == DEFAULT_ANNUAL_KWH
        assert "annual_kwh_indisponible_fallback_100000" in result["hypotheses"]["source_calibration"]

    def test_simulate_composantes_somme_coherente(self, db_session):
        """facture_totale_eur == sum(composantes.values()) (tolérance arrondi)."""
        _, site = _make_org_site(db_session, annual_kwh=750_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        somme = sum(result["composantes"].values())
        assert abs(result["facture_totale_eur"] - somme) < 0.5, (
            f"facture_totale={result['facture_totale_eur']} != sum={somme}"
        )

    def test_simulate_baseline_et_delta(self, db_session):
        """
        Baseline 2024 présent, delta comparable HT énergie pure.
        Fix P1 audit : `delta_vs_2024_pct` compare maintenant `fourniture_eur`
        (2026 HT énergie) à `baseline_2024.fourniture_ht_eur` (2024 HT énergie
        ARENH pondéré). Comparaison apples-to-apples, plus "facture TTC vs
        baseline HT" trompeur.
        """
        _, site = _make_org_site(db_session, annual_kwh=500_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        # Baseline = 500 MWh × 80 EUR/MWh × peakload_mult (COMMERCE_ALIMENTAIRE 0.55)
        # mult = 1 + 0.15 × 0.45 = 1.0675 → baseline = 42 700 EUR
        peakload_mult = 1.0 + 0.15 * (1.0 - 0.55)
        expected_baseline = 500.0 * BASELINE_2024_EUR_MWH_FALLBACK * peakload_mult
        assert result["baseline_2024"]["fourniture_ht_eur"] == pytest.approx(expected_baseline, rel=1e-3)
        assert result["baseline_2024"]["prix_moyen_pondere_eur_mwh"] == BASELINE_2024_EUR_MWH_FALLBACK

        # Delta HT énergie = (fourniture_2026 - baseline_2024) / baseline × 100
        # Même multiplier des deux côtés → delta isole le shift ARENH→forward
        expected_delta_ht = (result["composantes"]["fourniture_eur"] - expected_baseline) / expected_baseline * 100.0
        assert result["delta_vs_2024_pct"] == pytest.approx(expected_delta_ht, abs=0.1)
        # Même valeur exposée dans baseline_2024.delta_fourniture_ht_pct
        assert result["baseline_2024"]["delta_fourniture_ht_pct"] == pytest.approx(expected_delta_ht, abs=0.1)

    def test_simulate_forward_absent_fallback_reference_price(self, db_session):
        """Pas de MktPrice seedé → fallback EUR/MWh de référence + trace."""
        _, site = _make_org_site(db_session, annual_kwh=200_000.0)
        # Pas de _seed_forward : query retourne None

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        assert result["hypotheses"]["prix_forward_y1_eur_mwh"] == FALLBACK_FORWARD_EUR_MWH
        assert "forward_indisponible_fallback_reference_price" in result["hypotheses"]["source_calibration"]

    @pytest.mark.parametrize(
        "accise_category, expected_code",
        [
            ("HOUSEHOLD", "ACCISE_ELEC_T1"),
            ("SME", "ACCISE_ELEC"),
            ("HIGH_POWER", "ACCISE_ELEC_HP"),
        ],
    )
    def test_simulate_accise_routing_par_tax_profile(self, db_session, accise_category, expected_code):
        """TaxProfile.accise_category_elec pilote le code ParameterStore accise (T1/T2/HP)."""
        from models import DeliveryPoint, TaxProfile
        from models.enums import AcciseCategoryElec, DeliveryPointEnergyType

        _, site = _make_org_site(db_session, annual_kwh=500_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        pdl = DeliveryPoint(
            site_id=site.id,
            code="12345678901234",
            energy_type=DeliveryPointEnergyType.ELEC,
            grd_code="ENEDIS",
        )
        db_session.add(pdl)
        db_session.flush()
        profile = TaxProfile(
            delivery_point_id=pdl.id,
            accise_category_elec=AcciseCategoryElec[accise_category],
        )
        db_session.add(profile)
        db_session.flush()

        result = simulate_annual_cost_2026(site, db_session, year=2026)
        assert result["hypotheses"]["accise_code_resolu"] == expected_code

    def test_simulate_peakload_multiplier_par_archetype(self, db_session):
        """Un site peaky (bureau 0.30) paie + qu'un site flat (logistique frigo 0.65)."""
        _, bureau = _make_org_site(db_session, annual_kwh=500_000.0, archetype_code="BUREAU_STANDARD")
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        r_bureau = simulate_annual_cost_2026(bureau, db_session, year=2026)
        # BUREAU_STANDARD : facteur_forme 0.30 → mult = 1 + 0.15 × 0.70 = 1.105
        assert r_bureau["hypotheses"]["peakload_multiplier"] == pytest.approx(1.105, rel=1e-3)
        assert r_bureau["hypotheses"]["peak_premium_ratio"] == 0.15

        # Site flat (LOGISTIQUE_FRIGO 0.65) → mult = 1 + 0.15 × 0.35 = 1.0525
        _, logistique = _make_org_site(db_session, annual_kwh=500_000.0, archetype_code="LOGISTIQUE_FRIGO")
        r_log = simulate_annual_cost_2026(logistique, db_session, year=2026)
        assert r_log["hypotheses"]["peakload_multiplier"] == pytest.approx(1.0525, rel=1e-3)

        # Le bureau paie + cher en fourniture que le logistique (même volume, même forward)
        assert r_bureau["composantes"]["fourniture_eur"] > r_log["composantes"]["fourniture_eur"]

        # Delta vs 2024 : multiplier appliqué aux deux côtés → DELTA IDENTIQUE
        # entre archétypes, isolant le shift Post-ARENH (baseline 80 → forward 62).
        assert r_bureau["delta_vs_2024_pct"] == pytest.approx(r_log["delta_vs_2024_pct"], abs=0.1)

    def test_simulate_params_lus_depuis_yaml(self, db_session):
        """Les constantes MVP (baseline, fallback forward, peak_premium) viennent du YAML."""
        from services.purchase.cost_simulator_2026 import _load_simulator_params

        params = _load_simulator_params()
        # Valeurs actuelles dans tarifs_reglementaires.yaml::cost_simulator_2026
        assert params["baseline_eur_mwh"] == pytest.approx(80.0, rel=1e-3)
        assert params["fallback_forward_eur_mwh"] == pytest.approx(68.0, rel=1e-3)
        assert params["peak_premium_ratio"] == pytest.approx(0.15, rel=1e-3)

        # Le service les expose dans hypotheses (traçabilité auditeur)
        _, site = _make_org_site(db_session, annual_kwh=500_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)
        result = simulate_annual_cost_2026(site, db_session, year=2026)
        assert result["hypotheses"]["baseline_2024_eur_mwh"] == pytest.approx(80.0, rel=1e-3)
        assert result["hypotheses"]["peak_premium_ratio"] == pytest.approx(0.15, rel=1e-3)

    def test_simulate_archetype_inconnu_fallback_default(self, db_session):
        """Archetype hors dict → fallback DEFAULT (facteur_forme 0.40, mult 1.09)."""
        _, site = _make_org_site(db_session, annual_kwh=500_000.0, archetype_code="ARCHETYPE_INEXISTANT")
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)
        # DEFAULT facteur_forme 0.40 → mult = 1 + 0.15 × 0.60 = 1.09
        assert result["hypotheses"]["peakload_multiplier"] == pytest.approx(1.09, rel=1e-3)
        assert result["hypotheses"]["facteur_forme"] == 0.40

    def test_simulate_hypotheses_trace_complete(self, db_session):
        """Payload hypotheses contient toutes les clés du contrat agent B."""
        _, site = _make_org_site(db_session, annual_kwh=500_000.0)
        _seed_forward(db_session, year=2026, price_eur_mwh=62.0)

        result = simulate_annual_cost_2026(site, db_session, year=2026)

        required_keys = {
            "prix_forward_y1_eur_mwh",
            "facteur_forme",
            "capacite_unitaire_eur_mwh",
            "vnu_statut",
            "vnu_seuil_active_eur_mwh",
            "archetype",
            "source_calibration",
        }
        assert required_keys.issubset(set(result["hypotheses"].keys()))
        # Archetype renseigné bien propagé
        assert result["hypotheses"]["archetype"] == "COMMERCE_ALIMENTAIRE"
