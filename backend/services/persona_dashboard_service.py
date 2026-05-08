"""
PROMEOS — Phase G : services dashboard persona (Marie DAF + Jean-Marc CFO).

Réutilisation cardinale de la plomberie existante pour exposer 2 vues
synthétiques alignées sur les besoins personas Vision v1.3 :

- **Marie DAF** : `build_compliance_dashboard_marie_daf` — vue conformité
  multi-sites avec deadlines countdown + sanctions provisionnées par framework
  (DT/BACS/APER/Audit SMÉ).

- **Jean-Marc CFO** : `build_billing_anomalies_summary_cfo` + `list_expiring_contracts`
  — synthèse anomalies factures + alertes fin contrat J-180.

Toutes les fonctions prennent `org_id` (résolu via `resolve_org_id` côté route)
et retournent des dicts JSON-serializable. Pattern Phase E IDOR cardinal.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from doctrine.constants import (
    APER_DEADLINE_LARGE_PARKING_DATE,
    APER_DEADLINE_SMALL_PARKING_DATE,
    APER_PARKING_LARGE_SURFACE_M2,
    APER_PENALTY_EUR_PER_M2_PER_YEAR,
    APER_SOLAR_RATIO_PCT,
    AUDIT_SME_DEADLINE_DATE,
    BACS_DEADLINE_EXISTING,
    BACS_PENALTY_EUR,
    DT_PENALTY_EUR,
    OPERAT_PENALTY_EUR,
    compute_operat_deadline,
)
from models import (
    EnergyContract,
    EntiteJuridique,
    Portefeuille,
    Site,
    not_deleted,
)
from models.bill_anomaly import BillAnomaly


# ─── Marie DAF — Compliance dashboard multi-sites ─────────────────────────────


def _days_until(target_iso: str, today: Optional[date] = None) -> int:
    """Jours restants jusqu'à une deadline ISO (négatif si dépassée)."""
    if today is None:
        today = date.today()
    target = date.fromisoformat(target_iso)
    return (target - today).days


def _operat_status(site, today: date) -> dict:
    """Statut OPERAT par site : deadline annuelle 30/09 + sanction si non déclaré."""
    deadline_iso = compute_operat_deadline(today.year)
    days = _days_until(deadline_iso, today)
    has_declaration = bool(getattr(site, "operat_status", None)) and str(site.operat_status) not in (
        "OperatStatus.NOT_STARTED",
        "NOT_STARTED",
    )
    return {
        "framework": "OPERAT",
        "deadline": deadline_iso,
        "days_remaining": days,
        "compliant": has_declaration,
        "exposure_eur": 0 if has_declaration else OPERAT_PENALTY_EUR,
        "regulatory_ref": "Décret 2019-771 art. R131-39 CCH",
    }


def _bacs_status(site) -> dict:
    """Statut BACS par site : deadline 1/1/2030 existants + sanction 1 500 €.

    Phase G P1 fix code-reviewer : `bool(getattr(...)) in ("A", "B")` était un bug
    logique (bool→True/False jamais dans tuple strings) → toujours `compliant=False`
    → sur-exposition systématique. Comparaison directe sur la valeur brute.
    """
    days = _days_until(BACS_DEADLINE_EXISTING)
    bacs_assujetti = bool(getattr(site, "bacs_assujetti", False))
    bacs_classe = getattr(site, "bacs_classe", None)
    bacs_compliant = bacs_classe in ("A", "B")
    return {
        "framework": "BACS",
        "deadline": BACS_DEADLINE_EXISTING,
        "days_remaining": days,
        "assujetti": bacs_assujetti,
        "compliant": bacs_compliant,
        "exposure_eur": 0 if (not bacs_assujetti or bacs_compliant) else BACS_PENALTY_EUR,
        "regulatory_ref": "Décret 2020-887 art. R175-7",
    }


def _aper_status(site) -> dict:
    """Statut APER par site : deadline selon catégorie taille parking + sanction surface-based.

    Phase G P1 fix code-reviewer : seuils SoT canoniques `doctrine.constants`
    APER_PARKING_LARGE_SURFACE_M2 + APER_SOLAR_RATIO_PCT (anti-hardcode Pilier 13).
    """
    surface_parking = getattr(site, "parking_area_m2", 0) or 0
    aper_assujetti = bool(getattr(site, "aper_assujetti", False))
    parking_solar_pct = getattr(site, "parking_solar_pct_engaged", 0) or 0
    deadline_iso = (
        APER_DEADLINE_LARGE_PARKING_DATE
        if surface_parking > APER_PARKING_LARGE_SURFACE_M2
        else APER_DEADLINE_SMALL_PARKING_DATE
    )
    days = _days_until(deadline_iso)
    aper_compliant = parking_solar_pct >= APER_SOLAR_RATIO_PCT
    # Sanction = surface non couverte × pénalité €/m²/an (ratio cible Loi APER)
    if not aper_assujetti or aper_compliant:
        exposure = 0
    else:
        uncovered = max(0, surface_parking * (1 - parking_solar_pct / 100))
        exposure = round(uncovered * APER_PENALTY_EUR_PER_M2_PER_YEAR)
    return {
        "framework": "APER",
        "deadline": deadline_iso,
        "days_remaining": days,
        "assujetti": aper_assujetti,
        "compliant": aper_compliant,
        "exposure_eur": exposure,
        "regulatory_ref": "Loi 2023-175 art. 40",
    }


def _audit_sme_status(ej) -> dict:
    """Statut Audit SMÉ par EJ : déclencheur 2,75/23,6 GWh + deadline 11/10/2026."""
    conso_3y = getattr(ej, "consommation_annuelle_moyenne_3y_gwh", None)
    deadline_iso = AUDIT_SME_DEADLINE_DATE
    days = _days_until(deadline_iso)
    # Déclencheur : conso >= 2,75 GWh (PME) ou >= 23,6 GWh (grandes ent.)
    triggered = conso_3y is not None and conso_3y >= 2.75
    # Pas de pénalité chiffrable côté PROMEOS (sanction = blocage marché public)
    return {
        "framework": "AUDIT_SME",
        "deadline": deadline_iso,
        "days_remaining": days,
        "triggered": triggered,
        "exposure_eur": 0,  # blocage marché public, pas pénalité monétaire directe
        "regulatory_ref": "Loi DDADUE 2025-391 art. 8",
    }


def _dt_status(site, today: date) -> dict:
    """Statut DT par site : trajectoire -40 % / 2030 + pénalité 7 500 €.

    Phase G P1 fix code-reviewer : `compliant` était hardcodé `False` →
    sur-exposition systématique violation règle "chiffres fiables/vérifiables".
    Désormais `null` si trajectoire pas calculée + flag `needs_trajectory_data`,
    `exposure_eur=null` aussi (pas de chiffrage faux). Le calcul réel exige
    `/api/cockpit/trajectory` côté frontend pour comparer projection vs cible.
    """
    is_tertiaire = bool(getattr(site, "tertiaire_area_m2", None))
    deadline_iso = "2030-12-31"
    days = _days_until(deadline_iso, today)
    return {
        "framework": "DT",
        "deadline": deadline_iso,
        "days_remaining": days,
        "assujetti": is_tertiaire,
        "compliant": None,  # Trajectoire non calculée ici — voir /api/cockpit/trajectory
        "needs_trajectory_data": is_tertiaire,
        "exposure_eur": None if is_tertiaire else 0,  # pas de chiffrage faux
        "exposure_max_eur": DT_PENALTY_EUR if is_tertiaire else 0,  # plafond légal
        "regulatory_ref": "Décret 2019-771",
    }


def build_compliance_dashboard_marie_daf(db: Session, org_id: int) -> dict:
    """Construit le dashboard conformité multi-sites pour persona Marie DAF.

    Réutilise plomberie existante (Site/EJ models + doctrine constants) et
    expose une vue synthétique cardinale : pour chaque site, statut des 4
    frameworks (DT/BACS/APER/OPERAT) + déclencheur Audit SMÉ par EJ.

    Returns:
        dict :
            - headlines : {total_sites, total_exposure_eur, next_deadline,
                           non_compliant_count}
            - sites : [{site_id, nom, score, frameworks: [...]}]
            - audit_sme : [{ej_id, nom, triggered, deadline, days_remaining}]
    """
    today = date.today()

    sites = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif.is_(True))
        .all()
    )
    ejs = (
        not_deleted(db.query(EntiteJuridique), EntiteJuridique).filter(EntiteJuridique.organisation_id == org_id).all()
    )

    sites_data: list[dict] = []
    total_exposure = 0
    next_deadline_days: Optional[int] = None
    non_compliant_count = 0

    for site in sites:
        frameworks = [
            _operat_status(site, today),
            _bacs_status(site),
            _aper_status(site),
            _dt_status(site, today),
        ]
        # Phase G P1 fix : `exposure_eur` peut être None (DT trajectoire pas calculée) —
        # on agrège uniquement les expositions chiffrées non-null.
        site_exposure = sum(fw["exposure_eur"] or 0 for fw in frameworks)
        total_exposure += site_exposure

        # Site NC si au moins 1 framework explicitement non compliant + exposure > 0.
        # `compliant=None` (DT pending) n'est PAS comptabilisé NC ici.
        is_nc = any(fw.get("compliant") is False and (fw["exposure_eur"] or 0) > 0 for fw in frameworks)
        if is_nc:
            non_compliant_count += 1

        # Track prochain deadline (< 365 jours, frameworks assujettis uniquement)
        for fw in frameworks:
            if fw.get("assujetti", True) and 0 <= fw["days_remaining"] < 365:
                if next_deadline_days is None or fw["days_remaining"] < next_deadline_days:
                    next_deadline_days = fw["days_remaining"]

        sites_data.append(
            {
                "site_id": site.id,
                "nom": site.nom,
                "exposure_eur": site_exposure,
                "is_non_compliant": is_nc,
                "frameworks": frameworks,
            }
        )

    audit_sme_data = [
        {
            "ej_id": ej.id,
            "nom": ej.nom,
            **_audit_sme_status(ej),
        }
        for ej in ejs
    ]

    return {
        "headlines": {
            "total_sites": len(sites),
            "non_compliant_count": non_compliant_count,
            "total_exposure_eur": total_exposure,
            "next_deadline_days": next_deadline_days,
        },
        "sites": sites_data,
        "audit_sme": audit_sme_data,
    }


# ─── Jean-Marc CFO — Anomalies factures + alertes fin contrat ────────────────


def _extract_anomaly_montant(anomaly: BillAnomaly) -> float:
    """Extrait montant_eur depuis details_json (clé `montant_anomalie_eur` ou `montant_eur`).

    BillAnomaly n'a pas de colonne montant directe — l'info est portée par
    details_json (JSON contextuel). Pour le ranking top_5, on dérive du JSON.
    """
    details = getattr(anomaly, "details_json", None) or {}
    if isinstance(details, dict):
        for key in ("montant_anomalie_eur", "montant_eur", "savings_eur"):
            v = details.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
    return 0.0


def build_billing_anomalies_summary_cfo(db: Session, org_id: int) -> dict:
    """Synthèse anomalies factures pour persona Jean-Marc CFO.

    Returns:
        dict :
            - total_open : nb anomalies ouvertes (resolved_at IS NULL)
            - total_montant_anomalie_eur : montant cumul (depuis details_json)
            - by_severity : {critical: N, warning: N, info: N}
            - top_5 : les 5 anomalies les plus impactantes (montant)
    """
    from models import EnergyInvoice

    anomalies = (
        db.query(BillAnomaly)
        .join(EnergyInvoice, EnergyInvoice.id == BillAnomaly.invoice_id)
        .join(Site, Site.id == EnergyInvoice.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            BillAnomaly.resolved_at.is_(None),  # OPEN = non résolue
        )
        .all()
    )

    by_severity = {"critical": 0, "warning": 0, "info": 0}
    for a in anomalies:
        sev = (a.severity or "").lower()
        if sev in by_severity:
            by_severity[sev] += 1

    montants = [(a, _extract_anomaly_montant(a)) for a in anomalies]
    total_montant = sum(m for _, m in montants)

    top_5_sorted = sorted(montants, key=lambda x: x[1], reverse=True)[:5]
    top_5_data = [
        {
            "anomaly_id": a.id,
            "invoice_id": a.invoice_id,
            "code": a.code,
            "severity": a.severity,
            "montant_eur": montant,
            "detected_at": a.detected_at.isoformat() if a.detected_at else None,
        }
        for a, montant in top_5_sorted
    ]

    return {
        "total_open": len(anomalies),
        "total_montant_anomalie_eur": round(total_montant, 2),
        "by_severity": by_severity,
        "top_5": top_5_data,
    }


def list_expiring_contracts(db: Session, org_id: int, *, horizon_days: int = 180) -> dict:
    """Liste les contrats expirant dans `horizon_days` (défaut J-180 cardinal CFO).

    Returns:
        dict :
            - total_expiring : nb contrats fenêtre
            - contracts : [{contract_id, supplier_name, fournisseur_id, end_date,
                           days_remaining, site_id, site_nom}]
    """
    today = date.today()
    horizon = today + timedelta(days=horizon_days)

    contracts = (
        db.query(EnergyContract, Site)
        .join(Site, Site.id == EnergyContract.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            EnergyContract.end_date.isnot(None),
            EnergyContract.end_date >= today,
            EnergyContract.end_date <= horizon,
        )
        .order_by(EnergyContract.end_date.asc())
        .all()
    )

    contracts_data = [
        {
            "contract_id": c.id,
            "supplier_name": c.supplier_name,
            "fournisseur_id": c.fournisseur_id,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "days_remaining": (c.end_date - today).days,
            "site_id": s.id,
            "site_nom": s.nom,
            "auto_renew": bool(getattr(c, "auto_renew", False)),
        }
        for c, s in contracts
    ]

    return {
        "total_expiring": len(contracts_data),
        "horizon_days": horizon_days,
        "contracts": contracts_data,
    }
