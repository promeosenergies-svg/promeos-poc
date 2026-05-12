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
    lookback_days: int = 180,
) -> list[Finding]:
    """Détecte les anomalies de facture récentes via bill_intelligence.

    Phase F.21 — wire complet : itère sur les factures récentes du scope
    (≤ lookback_days) et lance `detect_anomalies_for_invoice` pour chacune.
    Aggrège les anomalies critical/high par site et génère 1 Finding par
    site avec l'anomalie la plus grave (dédup naturelle).

    Codes anomalies billing les plus fréquents HELIOS :
      - R27 : écart conso facturée vs mesurée > 10 %
      - R29 : facture sans certificat de mesure
      - R31 : régularisation TURPE oubliée

    Returns:
        Liste de Finding (1 max par site avec anomalie billing).
    """
    from models import EnergyInvoice
    from services.bill_intelligence.anomaly_detector import (
        detect_anomalies_for_invoice,
    )

    site_ids = [s.id for s in sites_for_org_query(db, org_id).all()]
    if not site_ids:
        return []

    # Mapping severity bill_intelligence → Severity priority_scoring
    bill_severity_map = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
    }

    # Description anomaly code → texte lisible
    bill_code_messages = {
        "R27": "écart consommation facturée vs mesurée > 10 %",
        "R29": "facture sans certificat de mesure",
        "R31": "régularisation TURPE oubliée",
    }

    today = datetime.utcnow().date()
    cutoff = today - timedelta(days=lookback_days)

    # 1 Finding max par site (l'anomalie la plus grave).
    by_site: dict[int, dict] = {}

    invoices = (
        db.query(EnergyInvoice)
        .filter(
            EnergyInvoice.site_id.in_(site_ids),
            EnergyInvoice.period_end >= cutoff,
        )
        .all()
    )

    for invoice in invoices:
        try:
            anomalies = detect_anomalies_for_invoice(invoice, db)
        except Exception as exc:
            logger.debug("bill_intel failed for invoice %s: %s", invoice.id, exc)
            continue
        for a in anomalies:
            severity = bill_severity_map.get(str(a.severity).lower(), Severity.MEDIUM)
            # On garde la plus grave par site.
            prev = by_site.get(invoice.site_id)
            if prev is None or _severity_rank(severity) > _severity_rank(prev["severity"]):
                by_site[invoice.site_id] = {
                    "severity": severity,
                    "code": a.code,
                    "invoice_id": invoice.id,
                    "estimated_loss_eur": getattr(a, "estimated_loss_eur", None) or 0,
                }

    findings: list[Finding] = []
    sites = {s.id: s for s in sites_for_org_query(db, org_id).all()}
    for site_id, anomaly in by_site.items():
        site = sites.get(site_id)
        if site is None:
            continue
        code = anomaly["code"]
        msg = bill_code_messages.get(code, f"anomalie facture {code}")
        impact_eur = anomaly["estimated_loss_eur"]
        impact_label = f"{int(round(impact_eur))} €/an" if impact_eur and impact_eur > 0 else "à vérifier"

        findings.append(
            Finding(
                severity=anomaly["severity"],
                domain=Domain.FINANCIAL,
                scope_level=Scope.SITE,
                impact_eur_year=float(impact_eur) if impact_eur else None,
                deadline_date=None,
                finding_id=f"hl-billing-{code.lower()}-{site_id}",
                title=f"Anomalie facture {code} — {msg}",
                site_id=site_id,
                site_name=site.nom,
                evidence=(
                    f"Détection automatique sur facture #{anomaly['invoice_id']}"
                    f" : {msg}. Action : vérifier le certificat de mesure"
                    f" et lancer un reclaim si nécessaire."
                ),
                category_label="Facture · Anomalie",
                impact_label=impact_label,
                invitation_verb="vérifier",
                invitation_object="la facture",
                invitation_href=f"/billing/anomalies?site_id={site_id}",
            )
        )

    return findings


def _severity_rank(sev: Severity) -> int:
    """Ordre numérique pour comparer 2 sévérités."""
    return {Severity.CRITICAL: 4, Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1}.get(sev, 0)
