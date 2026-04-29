"""
Source-guard Phase 1.4.c — service lever_engine (migration JS → Python).

Sprint refonte cockpit dual sol2 (29/04/2026) — étape 1.4.c : verrouille
le contrat du service Python qui remplace
`frontend/src/models/leverEngineModel.js` (supprimé en parallèle).

Tests adaptés des cas couverts par les tests JS historiques V1+V35+V36+V37
(leverEngineModel.test.js, contractsV35.test.js, contractsV36.test.js,
dataActivationV37.test.js).

CLAUDE.md règle d'or #1 : zero business logic frontend. Ce service
porte désormais la logique du moteur de leviers côté backend.
"""

import pytest
from services.lever_engine_service import (
    ACTIVATION_THRESHOLD,
    TOTAL_ACTIVATION_DIMENSIONS,
    Lever,
    LeverResult,
    compute_actionable_levers,
    is_billing_insights_available,
    is_compliance_available,
    is_purchase_available,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


def make_kpis(**overrides):
    base = {
        "total": 10,
        "conformes": 7,
        "nonConformes": 2,
        "aRisque": 1,
        "risqueTotal": 30000,
    }
    base.update(overrides)
    return base


def make_billing(**overrides):
    base = {
        "total_invoices": 50,
        "total_eur": 500000,
        "total_loss_eur": 8000,
        "invoices_with_anomalies": 5,
    }
    base.update(overrides)
    return base


def make_compliance_signals():
    return {
        "signals": [
            {
                "source": "operat",
                "code": "DT-2030",
                "severity": "critical",
                "due_date": "2030-12-31",
                "proof_expected": "Declaration OPERAT",
            },
            {
                "source": "bacs",
                "code": "BACS-CL1",
                "severity": "high",
                "proof_expected": "Certificat BACS classe A",
            },
            {"source": "decret_tertiaire", "code": "DT-SUIVI", "severity": "medium"},
        ]
    }


def make_billing_insights(**overrides):
    base = {
        "anomalies_count": 8,
        "total_loss_eur": 12000,
        "invoices_impacted": 15,
        "confidence": "high",
        "proof_links": ["invoice-audit-2024-q3.pdf"],
    }
    base.update(overrides)
    return base


def make_purchase_signals(**overrides):
    base = {
        "totalContracts": 5,
        "totalSites": 10,
        "expiringSoonCount": 2,
        "expiringSoonSites": [1, 2],
        "missingContractsCount": 5,
        "coverageContractsPct": 50,
        "estimatedExposureEur": None,
        "isApproximate": True,
    }
    base.update(overrides)
    return base


# ── Constantes ────────────────────────────────────────────────────────────────


class TestConstants:
    def test_activation_threshold_is_3(self):
        assert ACTIVATION_THRESHOLD == 3

    def test_total_dimensions_is_5(self):
        assert TOTAL_ACTIVATION_DIMENSIONS == 5


# ── Helpers signals ────────────────────────────────────────────────────────────


class TestIsComplianceAvailable:
    def test_none_returns_false(self):
        assert is_compliance_available(None) is False

    def test_empty_dict_returns_false(self):
        assert is_compliance_available({}) is False

    def test_empty_signals_returns_false(self):
        assert is_compliance_available({"signals": []}) is False

    def test_with_signals_returns_true(self):
        assert is_compliance_available(make_compliance_signals()) is True

    def test_non_dict_returns_false(self):
        assert is_compliance_available("invalid") is False


class TestIsBillingInsightsAvailable:
    def test_none_returns_false(self):
        assert is_billing_insights_available(None) is False

    def test_zeros_returns_false(self):
        assert is_billing_insights_available({"anomalies_count": 0, "total_loss_eur": 0}) is False

    def test_anomalies_count_triggers(self):
        assert is_billing_insights_available({"anomalies_count": 3, "total_loss_eur": 0}) is True

    def test_loss_triggers(self):
        assert is_billing_insights_available({"anomalies_count": 0, "total_loss_eur": 5000}) is True


class TestIsPurchaseAvailable:
    def test_none_returns_false(self):
        assert is_purchase_available(None) is False

    def test_empty_dict_returns_false(self):
        assert is_purchase_available({}) is False

    def test_with_contracts_returns_true(self):
        assert is_purchase_available(make_purchase_signals()) is True

    def test_zeros_returns_false(self):
        assert is_purchase_available({"totalContracts": 0, "totalSites": 0}) is False


# ── Conformité ─────────────────────────────────────────────────────────────────


class TestConformiteLevers:
    def test_genere_leviers_conformite_quand_non_conformes_et_a_risque(self):
        result = compute_actionable_levers(kpis=make_kpis(), billing_summary={})
        assert result.levers_by_type["conformite"] == 2
        assert result.levers_by_type["facturation"] == 0
        assert result.levers_by_type["optimisation"] == 0
        # V37 data_activation lever fires (1 brique active < threshold 3)
        assert result.levers_by_type["data_activation"] == 1
        assert result.total_levers == 3

    def test_repartit_risque_total_au_prorata(self):
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=2, aRisque=1, risqueTotal=30000),
            billing_summary={},
        )
        nc_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-conf-nc"), None)
        ar_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-conf-ar"), None)
        assert nc_lever is not None
        assert ar_lever is not None
        # 2/(2+1) * 30000 = 20000
        assert nc_lever.impact_eur == 20000
        # 1/(2+1) * 30000 = 10000
        assert ar_lever.impact_eur == 10000

    def test_impact_eur_none_si_risque_total_zero(self):
        result = compute_actionable_levers(kpis=make_kpis(risqueTotal=0), billing_summary={})
        for lv in result.top_levers:
            if lv.lever_type == "conformite":
                assert lv.impact_eur is None

    def test_pas_de_levier_si_zero_non_conformes_zero_a_risque(self):
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={},
        )
        assert result.levers_by_type["conformite"] == 0


# ── Facturation ───────────────────────────────────────────────────────────────


class TestFacturationLevers:
    def test_genere_levier_facturation_quand_anomalies(self):
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary=make_billing(),
        )
        assert result.levers_by_type["facturation"] == 1
        fact_lever = next(lv for lv in result.top_levers if lv.lever_type == "facturation")
        assert fact_lever.impact_eur == 8000

    def test_genere_levier_facturation_via_total_loss_sans_anomalies(self):
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={"total_loss_eur": 5000, "total_eur": 0},
        )
        assert result.levers_by_type["facturation"] == 1
        fact_lever = next(lv for lv in result.top_levers if lv.lever_type == "facturation")
        assert "surcoût" in fact_lever.label

    def test_genere_levier_optimisation_quand_total_eur(self):
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={"total_eur": 200000},
        )
        assert result.levers_by_type["optimisation"] == 1
        optim_lever = next(lv for lv in result.top_levers if lv.lever_type == "optimisation")
        assert optim_lever.impact_eur == 2000


# ── Mix tous types ─────────────────────────────────────────────────────────────


class TestMixLevers:
    def test_genere_conformite_facturation_optimisation_ensemble(self):
        result = compute_actionable_levers(kpis=make_kpis(), billing_summary=make_billing())
        assert result.levers_by_type["conformite"] == 2
        assert result.levers_by_type["facturation"] == 1
        assert result.levers_by_type["optimisation"] == 1
        assert result.total_levers == 4

    def test_estimated_impact_eur_risque_plus_loss(self):
        result = compute_actionable_levers(
            kpis=make_kpis(risqueTotal=30000),
            billing_summary=make_billing(total_loss_eur=8000),
        )
        assert result.estimated_impact_eur == 38000

    def test_top_levers_tries_impact_desc_null_en_dernier(self):
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=2, aRisque=1, risqueTotal=30000),
            billing_summary=make_billing(total_loss_eur=8000, total_eur=500000),
        )
        impacts = [lv.impact_eur for lv in result.top_levers]
        for i in range(len(impacts) - 1):
            a = impacts[i] if impacts[i] is not None else -1
            b = impacts[i + 1] if impacts[i + 1] is not None else -1
            assert a >= b


# ── Cas vide ────────────────────────────────────────────────────────────────────


class TestEmptyLevers:
    def test_retourne_zero_leviers_quand_tout_vide(self):
        result = compute_actionable_levers(kpis={}, billing_summary={})
        assert result.total_levers == 0
        assert result.levers_by_type["conformite"] == 0
        assert result.levers_by_type["facturation"] == 0
        assert result.levers_by_type["optimisation"] == 0
        assert result.estimated_impact_eur == 0
        assert result.top_levers == []

    def test_retourne_zero_leviers_avec_input_none(self):
        result = compute_actionable_levers()
        assert result.total_levers == 0
        assert result.top_levers == []


# ── V35 : enrichissement complianceSignals ────────────────────────────────────


class TestV35ComplianceSignals:
    def test_enrichit_label_conformite_avec_signaux_critiques(self):
        signals = make_compliance_signals()
        result = compute_actionable_levers(kpis=make_kpis(), billing_summary={}, compliance_signals=signals)
        nc_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-conf-nc"), None)
        assert nc_lever is not None
        assert "signal" in nc_lever.label
        assert "critique" in nc_lever.label

    def test_ajoute_proof_hint_depuis_premier_signal(self):
        signals = make_compliance_signals()
        result = compute_actionable_levers(kpis=make_kpis(), billing_summary={}, compliance_signals=signals)
        nc_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-conf-nc"), None)
        assert nc_lever is not None
        assert nc_lever.proof_hint is not None
        assert "OPERAT" in nc_lever.proof_hint

    def test_fallback_sans_compliance_signals(self):
        result = compute_actionable_levers(kpis=make_kpis(), billing_summary=make_billing(), compliance_signals=None)
        assert result.total_levers == 4

    def test_pas_de_crash_avec_compliance_signals_vide(self):
        result = compute_actionable_levers(
            kpis=make_kpis(), billing_summary=make_billing(), compliance_signals={"signals": []}
        )
        assert result.total_levers == 4


# ── V35 : enrichissement billingInsights ──────────────────────────────────────


class TestV35BillingInsights:
    def test_utilise_anomalies_count_billing_insights(self):
        insights = make_billing_insights()
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary=make_billing(invoices_with_anomalies=3),
            billing_insights=insights,
        )
        fact_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-fact-anom"), None)
        assert fact_lever is not None
        # billing_insights.anomalies_count = 8 prime sur billing_summary.invoices_with_anomalies = 3
        assert "8 anomalie" in fact_lever.label

    def test_ajoute_label_confiance_haute(self):
        insights = make_billing_insights()
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary=make_billing(),
            billing_insights=insights,
        )
        fact_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-fact-anom"), None)
        assert fact_lever is not None
        assert "confiance haute" in fact_lever.label

    def test_prend_max_entre_billing_insights_et_summary(self):
        insights = make_billing_insights(anomalies_count=2, total_loss_eur=15000, confidence="medium")
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={"total_loss_eur": 8000, "total_eur": 0},
            billing_insights=insights,
        )
        fact_lever = next((lv for lv in result.top_levers if lv.lever_type == "facturation"), None)
        assert fact_lever is not None
        assert fact_lever.impact_eur == 15000  # max(15000, 8000)

    def test_ajoute_proof_links_depuis_billing_insights(self):
        insights = make_billing_insights()
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary=make_billing(),
            billing_insights=insights,
        )
        fact_lever = next((lv for lv in result.top_levers if lv.lever_type == "facturation"), None)
        assert fact_lever is not None
        assert fact_lever.proof_links is not None
        assert "invoice-audit-2024-q3.pdf" in fact_lever.proof_links


# ── V36 : achat d'énergie ─────────────────────────────────────────────────────


class TestV36AchatLevers:
    def test_genere_lev_achat_renew_quand_expiring_soon(self):
        ps = make_purchase_signals()
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={},
            purchase_signals=ps,
        )
        renew = next((lv for lv in result.top_levers if lv.action_key == "lev-achat-renew"), None)
        assert renew is not None
        assert renew.lever_type == "achat"
        assert "contrat" in renew.label
        assert "énergie" in renew.label
        assert "/achat-energie" in renew.cta_path

    def test_genere_lev_achat_data_quand_missing_contracts(self):
        ps = make_purchase_signals()
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={},
            purchase_signals=ps,
        )
        data = next((lv for lv in result.top_levers if lv.action_key == "lev-achat-data"), None)
        assert data is not None
        assert data.lever_type == "achat"
        assert "sans contrat" in data.label
        assert "/achat-energie" in data.cta_path

    def test_levers_by_type_achat_reflète_compte(self):
        ps = make_purchase_signals()
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={},
            purchase_signals=ps,
        )
        assert result.levers_by_type["achat"] == 2

    def test_impact_eur_null_pour_achat_v1(self):
        ps = make_purchase_signals(estimatedExposureEur=None)
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={},
            purchase_signals=ps,
        )
        for lv in result.top_levers:
            if lv.lever_type == "achat":
                assert lv.impact_eur is None

    def test_pas_de_levers_achat_si_tout_couvert_sans_echeances(self):
        ps = make_purchase_signals(expiringSoonCount=0, expiringSoonSites=[], missingContractsCount=0)
        result = compute_actionable_levers(
            kpis=make_kpis(nonConformes=0, aRisque=0, risqueTotal=0),
            billing_summary={},
            purchase_signals=ps,
        )
        assert result.levers_by_type["achat"] == 0

    def test_fallback_sans_purchase_signals(self):
        result = compute_actionable_levers(kpis=make_kpis(), billing_summary=make_billing(), purchase_signals=None)
        assert result.levers_by_type["achat"] == 0
        assert result.levers_by_type["conformite"] == 2
        assert result.levers_by_type["facturation"] == 1
        assert result.levers_by_type["optimisation"] == 1
        assert result.total_levers == 4


# ── V37 : data_activation ─────────────────────────────────────────────────────


class TestV37DataActivation:
    def test_pas_de_levier_quand_activated_count_superieur_ou_egal_3(self):
        ps = make_purchase_signals()
        result = compute_actionable_levers(
            kpis=make_kpis(couvertureDonnees=80),
            billing_summary=make_billing(),
            purchase_signals=ps,
        )
        da_levers = [lv for lv in result.top_levers if lv.lever_type == "data_activation"]
        # couvertureDonnees=80 → 5 briques actives >= 3
        assert len(da_levers) == 0
        assert result.levers_by_type["data_activation"] == 0

    def test_levier_quand_activated_count_inferieur_3(self):
        result = compute_actionable_levers(
            kpis={
                "total": 5,
                "conformes": 0,
                "nonConformes": 0,
                "aRisque": 0,
                "couvertureDonnees": 0,
                "risqueTotal": 0,
            },
            billing_summary={},
        )
        da_levers = [lv for lv in result.top_levers if lv.lever_type == "data_activation"]
        assert len(da_levers) == 1
        assert da_levers[0].action_key == "lev-data-cover"
        assert da_levers[0].cta_path == "/activation"

    def test_label_indique_nombre_briques_manquantes(self):
        result = compute_actionable_levers(
            kpis={
                "total": 5,
                "conformes": 0,
                "nonConformes": 0,
                "aRisque": 0,
                "couvertureDonnees": 0,
                "risqueTotal": 0,
            },
            billing_summary={},
        )
        lever = next((lv for lv in result.top_levers if lv.lever_type == "data_activation"), None)
        assert lever is not None
        assert "4" in lever.label  # 5 - 1 (patrimoine actif) = 4 briques manquantes
        assert "briques" in lever.label
        assert "manquantes" in lever.label

    def test_pas_de_levier_si_kpis_total_zero(self):
        result = compute_actionable_levers(kpis={"total": 0}, billing_summary={})
        da_levers = [lv for lv in result.top_levers if lv.lever_type == "data_activation"]
        assert len(da_levers) == 0


# ── Compatibilité camelCase legacy ────────────────────────────────────────────


class TestCamelCaseLegacy:
    def test_accepte_non_conformes_camel_case(self):
        result = compute_actionable_levers(
            kpis={"total": 5, "nonConformes": 3, "aRisque": 0, "risqueTotal": 10000},
            billing_summary={},
        )
        nc_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-conf-nc"), None)
        assert nc_lever is not None

    def test_accepte_a_risque_camel_case(self):
        result = compute_actionable_levers(
            kpis={"total": 5, "nonConformes": 0, "aRisque": 2, "risqueTotal": 0},
            billing_summary={},
        )
        ar_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-conf-ar"), None)
        assert ar_lever is not None

    def test_accepte_risque_total_camel_case(self):
        result = compute_actionable_levers(
            kpis={"total": 5, "nonConformes": 2, "aRisque": 1, "risqueTotal": 9000},
            billing_summary={},
        )
        nc_lever = next((lv for lv in result.top_levers if lv.action_key == "lev-conf-nc"), None)
        assert nc_lever is not None
        assert nc_lever.impact_eur == 6000  # round(9000 * 2/3)


# ── to_dict ────────────────────────────────────────────────────────────────────


class TestToDictContracts:
    def test_lever_to_dict_structure(self):
        lv = Lever(
            lever_type="conformite",
            action_key="lev-conf-nc",
            label="Test",
            impact_eur=1000,
            cta_path="/conformite",
        )
        d = lv.to_dict()
        assert d["type"] == "conformite"
        assert d["actionKey"] == "lev-conf-nc"
        assert d["label"] == "Test"
        assert d["impactEur"] == 1000
        assert d["ctaPath"] == "/conformite"

    def test_lever_result_to_dict_structure(self):
        result = compute_actionable_levers(kpis=make_kpis(), billing_summary=make_billing())
        d = result.to_dict()
        assert "totalLevers" in d
        assert "leversByType" in d
        assert "estimatedImpactEur" in d
        assert "topLevers" in d
        assert isinstance(d["topLevers"], list)
