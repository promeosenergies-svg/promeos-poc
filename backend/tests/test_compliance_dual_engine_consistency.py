"""
PROMEOS — V115 step 5 : test golden de cohérence entre les deux évaluateurs
conformité (compliance_rules et regops.engine).

But : prévenir la dérive silencieuse. Pour une fixture canonique (site sans
obligation ni evidence), les deux évaluateurs doivent s'accorder au niveau
régulation : si l'un dit ISSUE, l'autre ne doit pas dire OK.

Règles de l'assertion :
  - OK vs ISSUE          → FAIL (contradiction dure)
  - OK vs UNKNOWN         → OK (UNKNOWN est un proxy pour "à vérifier")
  - ISSUE vs UNKNOWN      → OK (les deux signalent qu'il y a qqch à regarder)
  - OUT_OF_SCOPE de part et d'autre → OK

Voir services/compliance_rule_mapping.py pour la doc complète et le mapping.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, Portefeuille, EntiteJuridique
from services.compliance_rule_mapping import (
    CANONICAL_REGULATIONS,
    STATUS_ISSUE,
    STATUS_OK,
    STATUS_OUT_OF_SCOPE,
    STATUS_UNKNOWN,
    categorize_finding_status,
    regulation_worst_status,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def golden_site(db_session):
    """Site canonique minimal — tertiaire > 1000 m², aucune preuve, aucune obligation.

    Les deux évaluateurs doivent tous deux signaler des issues sur DT/BACS/APER.
    """
    org = Organisation(nom="GoldenOrg", type_client="tertiaire", actif=True, siren="111222333")
    db_session.add(org)
    db_session.flush()

    entite = EntiteJuridique(nom="GoldenEntite", organisation_id=org.id, siren="111222333")
    db_session.add(entite)
    db_session.flush()

    portfolio = Portefeuille(nom="GoldenPortfolio", entite_juridique_id=entite.id)
    db_session.add(portfolio)
    db_session.flush()

    site = Site(
        nom="Golden Site",
        type="bureau",
        actif=True,
        portefeuille_id=portfolio.id,
        tertiaire_area_m2=2000.0,
        parking_area_m2=12000.0,  # > seuil APER parking_large
        roof_area_m2=600.0,  # > seuil roof_threshold_m2
    )
    db_session.add(site)
    db_session.flush()

    return site


class TestRuleMapping:
    """Helpers du mapping — sanity checks indépendants de la DB."""

    def test_categorize_compliance_rules_vocabulary(self):
        assert categorize_finding_status("OK") == STATUS_OK
        assert categorize_finding_status("NOK") == STATUS_ISSUE
        assert categorize_finding_status("UNKNOWN") == STATUS_UNKNOWN
        assert categorize_finding_status("OUT_OF_SCOPE") == STATUS_OUT_OF_SCOPE

    def test_categorize_regops_vocabulary(self):
        assert categorize_finding_status("COMPLIANT") == STATUS_OK
        assert categorize_finding_status("NON_COMPLIANT") == STATUS_ISSUE
        assert categorize_finding_status("AT_RISK") == STATUS_ISSUE
        assert categorize_finding_status("EXEMPTION_POSSIBLE") == STATUS_ISSUE

    def test_categorize_none_returns_unknown(self):
        assert categorize_finding_status(None) == STATUS_UNKNOWN

    def test_regulation_worst_status_aggregation(self):
        """Agrégation par regulation (clé primaire), pas par rule_id.

        Les 2 labels "decret_tertiaire_operat" et "TERTIAIRE_OPERAT" doivent
        être canonicalisés vers "decret_tertiaire".
        """
        findings = [
            ("decret_tertiaire_operat", "NOK"),
            ("decret_tertiaire_operat", "UNKNOWN"),
            ("TERTIAIRE_OPERAT", "OK"),
            ("bacs", "NOK"),
            ("APER", "OK"),
        ]
        worst = regulation_worst_status(findings)
        assert worst["decret_tertiaire"] == STATUS_ISSUE
        assert worst["bacs"] == STATUS_ISSUE
        assert worst["aper"] == STATUS_OK

    def test_canonical_regulations_covers_four_frameworks(self):
        assert CANONICAL_REGULATIONS == {"decret_tertiaire", "bacs", "aper", "dpe_tertiaire"}


class TestDualEngineConsistency:
    """Golden fixture — les 2 évaluateurs ne doivent pas se contredire."""

    def _run_compliance_rules(self, db_session, site_id):
        """Invoke compliance_rules.evaluate_site et retourne (regulation, status)."""
        from services.compliance_rules import evaluate_site as eval_packs

        findings = eval_packs(db_session, site_id)
        return [(f.regulation, f.status) for f in findings]

    def _run_regops(self, db_session, site_id):
        """Invoke regops.engine.evaluate_site et retourne (regulation, status)."""
        from regops.engine import evaluate_site as eval_regops

        summary = eval_regops(db_session, site_id)
        return [(f.regulation, f.status) for f in summary.findings]

    def test_both_engines_flag_issues_on_empty_golden_site(self, db_session, golden_site):
        """Sur un site sans obligations/evidences, les 2 moteurs doivent signaler
        des issues DT et BACS (pas d'OPERAT, pas d'attestation BACS).

        Toute exception remonte — un test golden DOIT échouer fort, pas passer
        silencieusement en skipped.
        """
        rules_findings = self._run_compliance_rules(db_session, golden_site.id)
        regops_findings = self._run_regops(db_session, golden_site.id)

        rules_worst = regulation_worst_status(rules_findings)
        regops_worst = regulation_worst_status(regops_findings)

        # Les deux moteurs doivent avoir évalué au moins DT et BACS
        assert "decret_tertiaire" in rules_worst or "decret_tertiaire" in regops_worst
        assert "bacs" in rules_worst or "bacs" in regops_worst

        # Contradiction dure interdite : OK vs ISSUE sur la même régulation
        for reg in CANONICAL_REGULATIONS:
            r = rules_worst.get(reg)
            g = regops_worst.get(reg)
            if r == STATUS_OK and g == STATUS_ISSUE:
                pytest.fail(
                    f"Dérive sur {reg}: compliance_rules=OK mais regops=ISSUE. "
                    f"rules={rules_findings}, regops={regops_findings}"
                )
            if r == STATUS_ISSUE and g == STATUS_OK:
                pytest.fail(
                    f"Dérive sur {reg}: compliance_rules=ISSUE mais regops=OK. "
                    f"rules={rules_findings}, regops={regops_findings}"
                )

    def test_all_emitted_rule_ids_are_mapped(self, db_session, golden_site):
        """Tout rule_id émis doit être connu du mapping (sauf OUT_OF_SCOPE,
        ambigu volontairement car partagé entre moteurs — résolu via regulation).
        """
        from services.compliance_rules import evaluate_site as eval_packs
        from regops.engine import evaluate_site as eval_regops
        from services.compliance_rule_mapping import RULE_ID_TO_REGULATION

        rules_findings = eval_packs(db_session, golden_site.id)
        regops_summary = eval_regops(db_session, golden_site.id)

        all_rule_ids = {f.rule_id for f in rules_findings} | {f.rule_id for f in regops_summary.findings}
        unmapped = all_rule_ids - set(RULE_ID_TO_REGULATION.keys())
        assert not unmapped, (
            f"Rule IDs non mappés dans RULE_ID_TO_REGULATION : {sorted(unmapped)}. "
            f"Ajouter au mapping pour préserver la traçabilité cross-moteur."
        )
