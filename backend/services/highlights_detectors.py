"""
PROMEOS — services/highlights_detectors.py (ADR-022 F.20a).

Détecteurs réels de findings pour le Top 3 highlights cockpit jour.
Remplace les mocks de `cockpit_highlights_service._collect_*_findings`
par des appels aux vrais services existants :

  - detect_ems_staleness_findings(db, org_id) : âge max MeterReading par site
  - detect_compliance_findings(db, org_id)    : compliance_score_service
                                                + scores < 50 par framework
  - detect_billing_findings(db, org_id)       : bill_intelligence
                                                anomalies factures récentes

Chaque détecteur retourne une liste de `regops.priority_scoring.Finding`
qui sera scorée puis intégrée au Top 3 doctrinal.

Doctrine ADR-022 §Highlights Top 3 + collecteurs cross-domain.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import MeterReading, Site
from regops.priority_scoring import Domain, Finding, Scope, Severity
from services.scope_utils import sites_for_org_query

logger = logging.getLogger(__name__)


# ── EMS staleness ───────────────────────────────────────────────────────────


# Seuils âge dernière mesure :
EMS_STALENESS_WARN_HOURS = 24  # > 24h sans mesure = HIGH severity
EMS_STALENESS_CRIT_HOURS = 72  # > 72h sans mesure = CRITICAL


def detect_ems_staleness_findings(
    db: Session,
    org_id: Optional[int],
    today: Optional[date] = None,
) -> list[Finding]:
    """Détecte les sites dont la dernière mesure EMS est trop ancienne.

    Pour chaque site du scope, calcule max(MeterReading.timestamp) parmi
    tous ses compteurs. Si l'âge dépasse les seuils, génère une Finding
    de domaine PLATFORM_HEALTH.

    Returns:
        Liste de Finding (potentiellement vide).
    """
    today_dt = datetime.combine(today or datetime.utcnow().date(), datetime.min.time())
    findings: list[Finding] = []

    sites = sites_for_org_query(db, org_id).all()
    for site in sites:
        # max timestamp parmi compteurs du site
        from services.ems.timeseries_service import get_site_meter_ids
        from models.energy_models import EnergyVector

        meter_ids = get_site_meter_ids(db, site.id, EnergyVector.ELECTRICITY)
        if not meter_ids:
            continue
        last_ts = db.query(func.max(MeterReading.timestamp)).filter(MeterReading.meter_id.in_(meter_ids)).scalar()
        if last_ts is None:
            continue

        age_hours = (today_dt - last_ts).total_seconds() / 3600
        if age_hours < EMS_STALENESS_WARN_HOURS:
            continue

        # Détermine la sévérité.
        severity = Severity.CRITICAL if age_hours >= EMS_STALENESS_CRIT_HOURS else Severity.HIGH
        days_label = int(age_hours / 24)
        evidence = (
            f"Dernière mesure il y a {days_label} jours · synchronisation"
            f" interrompue · recalcul conformité bloqué tant que la connexion"
            f" n'est pas rétablie."
        )

        findings.append(
            Finding(
                severity=severity,
                domain=Domain.PLATFORM_HEALTH,
                scope_level=Scope.SITE,
                impact_eur_year=None,
                deadline_date=None,
                finding_id=f"hl-ems-staleness-{site.id}",
                title="Connecteur EMS à vérifier avant recalcul de conformité",
                site_id=site.id,
                site_name=site.nom,
                evidence=evidence,
                category_label="Donnée EMS",
                impact_label="—",
                invitation_verb="vérifier",
                invitation_object="le connecteur",
                invitation_href=f"/connectors?site_id={site.id}",
            )
        )

    return findings


# ── Compliance findings ─────────────────────────────────────────────────────


# Mapping framework → contexte d'affichage (titre + invitation + impact estimé).
_FRAMEWORK_CONTEXT: dict[str, dict] = {
    "tertiaire_operat": {
        "title_template": "Écart de conformité à qualifier — Décret tertiaire",
        "evidence_template": (
            "Trajectoire -40 % à l'horizon 2030 non tenable sans plan d'action. Preuve OPERAT à reconstituer."
        ),
        "category": "Conformité Décret tertiaire",
        "impact_label_template": "{eur:.1f} k€/an",
        "impact_eur_default": 3_800,
        "deadline": date(2030, 12, 31),
        "invitation_verb": "voir",
        "invitation_object": "la preuve",
    },
    "bacs": {
        "title_template": "Revue BACS recommandée — puissance CVC à confirmer",
        "evidence_template": (
            "Site > 1 000 m², seuil BACS 2027 applicable. Puissance CVC à confirmer pour qualifier l'obligation."
        ),
        "category": "Conformité BACS",
        "impact_label_template": "2027",
        "impact_eur_default": None,
        "deadline": date(2027, 1, 1),
        "invitation_verb": "programmer",
        "invitation_object": "la revue",
    },
    "aper": {
        "title_template": "APER non-conforme — installation parkings solaires",
        "evidence_template": (
            "Parking > 1 500 m² soumis à obligation APER (loi 2023-175)."
            " Pas d'ombrière PV ou couverture végétalisée déclarée."
        ),
        "category": "Conformité APER",
        "impact_label_template": "20k€/an",
        "impact_eur_default": 20_000,
        "deadline": date(2028, 7, 1),
        "invitation_verb": "voir",
        "invitation_object": "la preuve",
    },
    "audit_sme": {
        "title_template": "Audit énergétique ISO 50001 absent",
        "evidence_template": (
            "Site > 50 GWh/an ou groupe > 250 ETP : audit énergétique"
            " réglementaire obligatoire tous les 4 ans. Aucun audit valide"
            " enregistré."
        ),
        "category": "Audit énergétique",
        "impact_label_template": "Sanction ADEME",
        "impact_eur_default": 50_000,
        "deadline": date(2026, 12, 31),
        "invitation_verb": "programmer",
        "invitation_object": "l'audit",
    },
    "solar_toiture": {
        "title_template": "Solarisation toiture — loi APER applicable",
        "evidence_template": (
            "Toiture > 500 m² soumise à obligation de couverture solaire ou"
            " végétalisée (loi APER art. 43). Pas d'installation déclarée."
        ),
        "category": "APER toiture",
        "impact_label_template": "—",
        "impact_eur_default": None,
        "deadline": date(2028, 7, 1),
        "invitation_verb": "voir",
        "invitation_object": "la preuve",
    },
}


def detect_compliance_findings(
    db: Session,
    org_id: Optional[int],
) -> list[Finding]:
    """Détecte les findings de conformité réelles via compliance_score_service.

    Pour chaque site, calcule le score compliance V2 adaptatif et génère
    une Finding pour chaque framework dont le score < 50 (= non-conforme
    ou à risque significatif).

    Returns:
        Liste de Finding (potentiellement vide si tous les sites conformes).
    """
    from services.compliance_score_service import compute_site_compliance_score

    findings: list[Finding] = []
    sites = sites_for_org_query(db, org_id).all()

    for site in sites:
        try:
            result = compute_site_compliance_score(db, site.id)
        except Exception as exc:
            logger.debug("compliance score failed for site %s: %s", site.id, exc)
            continue

        for framework in result.breakdown:
            if not framework.available or framework.score >= 50:
                continue

            ctx = _FRAMEWORK_CONTEXT.get(framework.framework)
            if ctx is None:
                continue  # framework non documenté → skip

            # Sévérité dépend de l'écart au score plein.
            if framework.score == 0:
                severity = Severity.HIGH
            elif framework.score < 30:
                severity = Severity.MEDIUM
            else:
                severity = Severity.MEDIUM

            impact_eur = ctx["impact_eur_default"]
            impact_label = (
                ctx["impact_label_template"].format(eur=impact_eur / 1000)
                if impact_eur and "{eur" in ctx["impact_label_template"]
                else ctx["impact_label_template"]
            )

            findings.append(
                Finding(
                    severity=severity,
                    domain=Domain.COMPLIANCE,
                    scope_level=Scope.SITE,
                    impact_eur_year=float(impact_eur) if impact_eur else None,
                    deadline_date=ctx["deadline"],
                    finding_id=f"hl-{framework.framework}-{site.id}",
                    title=ctx["title_template"],
                    site_id=site.id,
                    site_name=site.nom,
                    evidence=ctx["evidence_template"],
                    category_label=ctx["category"],
                    impact_label=impact_label,
                    invitation_verb=ctx["invitation_verb"],
                    invitation_object=ctx["invitation_object"],
                    invitation_href=f"/compliance/sites/{site.id}",
                )
            )

    return findings


# ── Billing findings ────────────────────────────────────────────────────────


def detect_billing_findings(
    db: Session,
    org_id: Optional[int],
    lookback_days: int = 90,
) -> list[Finding]:
    """Détecte les anomalies de facture récentes via bill_intelligence.

    F.20a v1 : retourne [] pour le moment (le service
    `bill_intelligence.anomaly_detector.detect_anomalies_for_invoice`
    requiert un invoice_id, donc à wirer après identification des factures
    récentes du scope). Phase F.21 ajoutera la collecte multi-invoice.

    Returns:
        Liste vide pour l'instant — sera populée F.21.
    """
    return []
