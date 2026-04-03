"""
Tests du module Audit Energetique / SME.
Source reglementaire : Loi n 2025-391 du 30 avril 2025
"""

import pytest
from datetime import date

from services.audit_sme_service import (
    compute_obligation,
    compute_statut,
    compute_score_audit_sme,
    compute_global_score_with_audit_sme,
    SEUIL_SME_KWH,
    SEUIL_AUDIT_KWH,
    DATE_DEADLINE_P1,
    PERIODICITE_ANS,
)


# ── Seuils reglementaires immuables ─────────────────────────────────────────


class TestSeuilsReglementaires:
    """Verifie les seuils canoniques de la loi 2025-391."""

    def test_seuil_audit_est_2_75_gwh(self):
        assert SEUIL_AUDIT_KWH == 2_750_000

    def test_seuil_sme_est_23_6_gwh(self):
        assert SEUIL_SME_KWH == 23_600_000

    def test_deadline_premier_audit(self):
        assert DATE_DEADLINE_P1 == date(2026, 10, 11)

    def test_periodicite_4_ans(self):
        assert PERIODICITE_ANS == 4


# ── compute_obligation ──────────────────────────────────────────────────────


class TestComputeObligation:
    def test_sous_seuil_aucune_obligation(self):
        result = compute_obligation(2_000_000)
        assert result["obligation"] == "AUCUNE"

    def test_entre_seuils_audit_4_ans(self):
        result = compute_obligation(5_000_000)
        assert result["obligation"] == "AUDIT_4ANS"
        assert result["periodicite_ans"] == 4
        assert "2026-10-11" in result["deadline_premier_audit"]

    def test_au_dessus_seuil_sme(self):
        result = compute_obligation(30_000_000)
        assert result["obligation"] == "SME_ISO50001"

    def test_exactement_au_seuil_audit(self):
        result = compute_obligation(SEUIL_AUDIT_KWH)
        assert result["obligation"] == "AUDIT_4ANS"

    def test_exactement_au_seuil_sme(self):
        result = compute_obligation(SEUIL_SME_KWH)
        assert result["obligation"] == "SME_ISO50001"

    def test_sme_certifie_exonere_audit(self):
        result = compute_obligation(5_000_000, sme_certifie=True)
        assert result["obligation"] == "SME_ISO50001"

    def test_source_reglementaire_presente(self):
        for conso in [1_000_000, 5_000_000, 30_000_000]:
            result = compute_obligation(conso)
            assert "Loi 2025-391" in result["source_reglementaire"]


# ── compute_statut ──────────────────────────────────────────────────────────


class _MockAudit:
    def __init__(self, **kw):
        self.audit_realise = kw.get("audit_realise", False)
        self.auditeur_identifie = kw.get("auditeur_identifie", False)
        self.transmission_realisee = kw.get("transmission_realisee", False)
        self.sme_certifie_iso50001 = kw.get("sme_certifie_iso50001", False)
        self.date_premier_audit_limite = kw.get("date_premier_audit_limite", date(2026, 10, 11))


class TestComputeStatut:
    def test_non_concerne_si_aucune_obligation(self):
        assert compute_statut(None, "AUCUNE", date(2026, 1, 1)) == "NON_CONCERNE"

    def test_en_retard_si_deadline_depassee(self):
        mock = _MockAudit()
        assert compute_statut(mock, "AUDIT_4ANS", date(2026, 12, 1)) == "EN_RETARD"

    def test_en_retard_si_moins_de_90_jours(self):
        mock = _MockAudit()
        assert compute_statut(mock, "AUDIT_4ANS", date(2026, 8, 12)) == "EN_RETARD"

    def test_a_realiser_si_loin_de_deadline(self):
        mock = _MockAudit()
        assert compute_statut(mock, "AUDIT_4ANS", date(2026, 3, 25)) == "A_REALISER"

    def test_en_cours_si_auditeur_identifie(self):
        mock = _MockAudit(auditeur_identifie=True)
        assert compute_statut(mock, "AUDIT_4ANS", date(2026, 4, 1)) == "EN_COURS"

    def test_conforme_sme_certifie(self):
        mock = _MockAudit(sme_certifie_iso50001=True)
        assert compute_statut(mock, "SME_ISO50001", date(2026, 4, 1)) == "CONFORME"

    def test_conforme_audit_realise_et_transmis(self):
        mock = _MockAudit(audit_realise=True, transmission_realisee=True)
        assert compute_statut(mock, "AUDIT_4ANS", date(2026, 4, 1)) == "CONFORME"

    def test_a_realiser_audit_realise_sans_transmission(self):
        mock = _MockAudit(audit_realise=True, transmission_realisee=False)
        assert compute_statut(mock, "AUDIT_4ANS", date(2026, 4, 1)) == "A_REALISER"


class TestBuildActions:
    """Verifie la coherence des actions recommandees."""

    def test_audit_realise_sans_transmission_pas_d_action_planifier(self):
        """Audit fait mais transmission manquante -> seulement TRANSMETTRE, pas PLANIFIER."""
        from services.audit_sme_service import _build_actions

        mock = _MockAudit(audit_realise=True, transmission_realisee=False)
        actions = _build_actions("AUDIT_4ANS", "A_REALISER", 192, mock)
        codes = [a["code"] for a in actions]
        assert "TRANSMETTRE_ADMIN" in codes
        assert "IDENTIFIER_AUDITEUR" not in codes
        assert "PLANIFIER_AUDIT" not in codes

    def test_audit_non_realise_propose_planifier(self):
        """Audit non fait -> propose identifier auditeur + planifier."""
        from services.audit_sme_service import _build_actions

        mock = _MockAudit()
        actions = _build_actions("AUDIT_4ANS", "A_REALISER", 192, mock)
        codes = [a["code"] for a in actions]
        assert "IDENTIFIER_AUDITEUR" in codes
        assert "PLANIFIER_AUDIT" in codes


# ── compute_score_audit_sme ─────────────────────────────────────────────────


class TestScoreAuditSme:
    def test_score_non_concerne_est_1(self):
        assert compute_score_audit_sme(None, "AUCUNE", "NON_CONCERNE") == 1.0

    def test_score_conforme_est_1(self):
        assert compute_score_audit_sme(None, "AUDIT_4ANS", "CONFORME") == 1.0

    def test_score_en_retard_est_0(self):
        assert compute_score_audit_sme(None, "AUDIT_4ANS", "EN_RETARD") == 0.0

    def test_score_a_realiser_est_0_3(self):
        assert compute_score_audit_sme(None, "AUDIT_4ANS", "A_REALISER") == 0.3

    def test_score_en_cours_est_0_6(self):
        assert compute_score_audit_sme(None, "AUDIT_4ANS", "EN_COURS") == 0.6


# ── compute_global_score_with_audit_sme ─────────────────────────────────────


class TestIntegrationRegOpsScoring:
    def test_poids_audit_sme_applicable(self):
        result = compute_global_score_with_audit_sme(
            score_dt=0.8,
            score_bacs=0.7,
            score_aper=0.6,
            score_audit_sme=0.3,
            audit_sme_applicable=True,
        )
        assert "AUDIT_SME" in result["detail"]
        assert result["detail"]["AUDIT_SME"]["applicable"] is True
        assert result["audit_sme_applicable"] is True

    def test_poids_audit_sme_non_applicable_inchange(self):
        """Sans Audit/SME, poids DT=45% BACS=30% APER=25% inchanges."""
        result = compute_global_score_with_audit_sme(
            score_dt=0.8,
            score_bacs=0.7,
            score_aper=0.6,
            score_audit_sme=None,
            audit_sme_applicable=False,
        )
        expected = 0.8 * 0.45 + 0.7 * 0.30 + 0.6 * 0.25
        assert abs(result["score_global"] - expected) < 0.01

    def test_score_global_somme_poids_1(self):
        """Verifie que les poids redistribues somment a 1."""
        result = compute_global_score_with_audit_sme(
            score_dt=1.0,
            score_bacs=1.0,
            score_aper=1.0,
            score_audit_sme=1.0,
            audit_sme_applicable=True,
        )
        # Tous a 1.0 => global = 1.0
        assert abs(result["score_global"] - 1.0) < 0.01

    def test_score_global_mixed_values(self):
        """Avec des scores mixtes, le global est la moyenne ponderee correcte."""
        result = compute_global_score_with_audit_sme(
            score_dt=0.8,
            score_bacs=0.7,
            score_aper=0.6,
            score_audit_sme=0.3,
            audit_sme_applicable=True,
        )
        # Poids: DT=0.39 BACS=0.28 APER=0.17 AUDIT_SME=0.16 (somme=1.0)
        expected = 0.8 * 0.39 + 0.7 * 0.28 + 0.6 * 0.17 + 0.3 * 0.16
        assert abs(result["score_global"] - expected) < 0.01

    def test_redistribution_composante_absente(self):
        """Si une composante est None, son poids est redistribue."""
        result = compute_global_score_with_audit_sme(
            score_dt=1.0,
            score_bacs=None,
            score_aper=1.0,
            score_audit_sme=1.0,
            audit_sme_applicable=True,
        )
        # Tous les scores presents = 1.0, donc global = 1.0
        assert abs(result["score_global"] - 1.0) < 0.01
        assert result["detail"]["BACS"]["applicable"] is False
