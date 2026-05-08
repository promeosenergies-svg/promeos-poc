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
    EnergyInvoice,
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


# Phase H4 — Marie DAF cardinal countdown urgency enum.
# Seuils calibrés sur jalons OPERAT (30/09 annuel) + BACS (1/1/2030).
URGENCY_CRITICAL_DAYS = 30
URGENCY_HIGH_DAYS = 90
URGENCY_MEDIUM_DAYS = 180


def _compute_urgency_level(days_remaining: int) -> str:
    """Classe l'urgence d'une deadline pour priorisation visuelle dashboard.

    Phase H4 (Marie DAF) — countdown enum cardinal :
    - CRITICAL : < 30 jours (action immédiate requise)
    - HIGH     : 30-90 jours (préparation deadline imminente)
    - MEDIUM   : 90-180 jours (planification trimestrielle)
    - LOW      : > 180 jours (suivi annuel)
    - OVERDUE  : days_remaining < 0 (deadline dépassée — sanction effective)
    """
    if days_remaining < 0:
        return "OVERDUE"
    if days_remaining < URGENCY_CRITICAL_DAYS:
        return "CRITICAL"
    if days_remaining < URGENCY_HIGH_DAYS:
        return "HIGH"
    if days_remaining < URGENCY_MEDIUM_DAYS:
        return "MEDIUM"
    return "LOW"


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
        "urgency_level": _compute_urgency_level(days),
        "compliant": has_declaration,
        "exposure_eur": 0 if has_declaration else OPERAT_PENALTY_EUR,
        "regulatory_ref": "Décret 2019-771 art. R131-39 CCH",
    }


def _bacs_status(site) -> dict:
    """Statut BACS par site : deadline 1/1/2030 existants + sanction 1 500 €.

    Phase H P1 fix audit : avant utilisait `bacs_classe` qui N'EXISTE PAS
    sur le modèle Site → 100 % sites assujettis sur-exposés. Le vrai champ
    est `Site.statut_bacs` (Enum StatutConformite : CONFORME / A_RISQUE /
    NON_CONFORME).
    """
    from models import StatutConformite

    days = _days_until(BACS_DEADLINE_EXISTING)
    bacs_assujetti = bool(getattr(site, "bacs_assujetti", False))
    statut = getattr(site, "statut_bacs", None)
    # Compliant si statut explicitement CONFORME ; pending si A_RISQUE ; NC si NON_CONFORME
    if statut == StatutConformite.CONFORME:
        bacs_compliant = True
    elif statut == StatutConformite.NON_CONFORME:
        bacs_compliant = False
    else:
        # A_RISQUE ou None → pending (pas de chiffrage faux)
        bacs_compliant = None
    return {
        "framework": "BACS",
        "deadline": BACS_DEADLINE_EXISTING,
        "days_remaining": days,
        "urgency_level": _compute_urgency_level(days),
        "assujetti": bacs_assujetti,
        "compliant": bacs_compliant,
        # Exposition chiffrée uniquement si NC explicite + assujetti.
        # A_RISQUE → exposure_eur=null (pending) + exposure_max_eur exposé.
        "exposure_eur": (
            0 if not bacs_assujetti or bacs_compliant is True else BACS_PENALTY_EUR if bacs_compliant is False else None
        ),
        "exposure_max_eur": BACS_PENALTY_EUR if bacs_assujetti else 0,
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
        "urgency_level": _compute_urgency_level(days),
        "assujetti": aper_assujetti,
        "compliant": aper_compliant,
        "exposure_eur": exposure,
        "regulatory_ref": "Loi 2023-175 art. 40",
    }


def _audit_sme_status(ej, today: Optional[date] = None) -> dict:
    """Statut Audit SMÉ par EJ : déclencheur 2,75/23,6 GWh + deadline 11/10/2026.

    Phase H3 (Marie DAF différenciant ROI) : exemption ISO 50001 actif & valide
    selon Loi DDADUE 2025-391 art. 8 — un EJ certifié SMÉ est dispensé de
    l'obligation Audit SMÉ. Économie ~15 k€/audit × 4 ans = ~60 k€/EJ.
    """
    if today is None:
        today = date.today()
    conso_3y = getattr(ej, "consommation_annuelle_moyenne_3y_gwh", None)
    deadline_iso = AUDIT_SME_DEADLINE_DATE
    days = _days_until(deadline_iso, today)

    # Déclencheur réglementaire : conso ≥ 2,75 GWh
    triggered = conso_3y is not None and conso_3y >= 2.75

    # Phase H3 — Exemption ISO 50001 : actif + certificat non expiré
    iso_50001_actif = bool(getattr(ej, "iso_50001_actif", False))
    iso_validity = getattr(ej, "iso_50001_date_validite", None)
    iso_valid = iso_50001_actif and (iso_validity is None or iso_validity >= today)

    # Triggered effectif : déclenché par conso MAIS exempté si ISO 50001 valide
    obligation_active = triggered and not iso_valid

    return {
        "framework": "AUDIT_SME",
        "deadline": deadline_iso,
        "days_remaining": days,
        "urgency_level": _compute_urgency_level(days),
        "triggered": triggered,
        "iso_50001_actif": iso_50001_actif,
        "iso_50001_valide": iso_valid,
        "exemption_iso_50001": iso_valid,  # alias UI explicite
        "obligation_active": obligation_active,
        "exposure_eur": 0,  # blocage marché public, pas pénalité monétaire directe
        "regulatory_ref": "Loi DDADUE 2025-391 art. 8",
    }


def _dpe_status(site, db: Session) -> dict:
    """Statut DPE par site : étiquette obligatoire annonce loyer L. 134-3-1 CCH.

    Phase H1 (Marie DAF cardinal Control 19,9k€) : framework #5 DPE.
    - Sanction DDPP jusqu'à 15 000 € (art. L. 271-4 CCH) + nullité bail
    - Classes F/G interdits location tertiaire >250 m² (Décret 2020-1610 modifié 2024)
    - Validité 10 ans (`Batiment.dpe_date_validite`)

    Compliance évaluée par site = pire classe parmi tous Batiment.dpe_class du site :
    - Tous DPE classés A-E + non expirés → compliant=True
    - Au moins 1 classé F/G OU date_validite expirée → compliant=False
    - Aucun DPE renseigné → compliant=None (pending data)
    """
    from models.batiment import Batiment

    # Sanction DDPP forfaitaire (art. L. 271-4 CCH — pratique commerciale trompeuse)
    DPE_PENALTY_EUR = 15000

    surface_tertiaire = getattr(site, "tertiaire_area_m2", 0) or 0
    # Assujetti si tertiaire >= 250 m² (seuil annonce loyer L. 134-3-1 CCH)
    dpe_assujetti = surface_tertiaire >= 250

    deadline_iso = "2026-12-31"  # F/G interdits 2025+, échéance vérification annuelle bailleur
    days = _days_until(deadline_iso)

    if not dpe_assujetti:
        return {
            "framework": "DPE",
            "deadline": deadline_iso,
            "days_remaining": days,
            "urgency_level": _compute_urgency_level(days),
            "assujetti": False,
            "compliant": True,
            "exposure_eur": 0,
            "exposure_max_eur": 0,
            "regulatory_ref": "Art. L. 134-3-1 CCH · Décret 2020-1610",
        }

    batiments = not_deleted(db.query(Batiment), Batiment).filter(Batiment.site_id == site.id).all()
    classes = [b.dpe_class for b in batiments if b.dpe_class]
    today = date.today()
    has_expired = any(b.dpe_date_validite and b.dpe_date_validite < today for b in batiments if b.dpe_date_validite)

    if not classes and not has_expired:
        # Aucune donnée DPE renseignée → pending
        compliant = None
        exposure = None
    elif has_expired or any(c in ("F", "G") for c in classes):
        compliant = False
        exposure = DPE_PENALTY_EUR
    else:
        compliant = True
        exposure = 0

    return {
        "framework": "DPE",
        "deadline": deadline_iso,
        "days_remaining": days,
        "urgency_level": _compute_urgency_level(days),
        "assujetti": True,
        "compliant": compliant,
        "exposure_eur": exposure,
        "exposure_max_eur": DPE_PENALTY_EUR,
        "worst_class": max(classes) if classes else None,  # G > A
        "has_expired_dpe": has_expired,
        "regulatory_ref": "Art. L. 134-3-1 CCH · Décret 2020-1610",
    }


def _dt_status(site, today: date) -> dict:
    """Statut DT par site : trajectoire -40 % / 2030 + pénalité 7 500 €."""
    is_tertiaire = bool(getattr(site, "tertiaire_area_m2", None))
    deadline_iso = "2030-12-31"
    days = _days_until(deadline_iso, today)
    return {
        "framework": "DT",
        "deadline": deadline_iso,
        "days_remaining": days,
        "urgency_level": _compute_urgency_level(days),
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
    total_exposure_certain = 0  # NC explicite chiffré
    total_exposure_pending_max = 0  # plafond légal frameworks pending (DT/BACS A_RISQUE)
    pending_frameworks_count = 0
    next_deadline_days: Optional[int] = None
    non_compliant_count = 0

    for site in sites:
        frameworks = [
            _operat_status(site, today),
            _bacs_status(site),
            _aper_status(site),
            _dt_status(site, today),
            _dpe_status(site, db),  # Phase H1 — Marie DAF cardinal framework #5
        ]
        # Phase H P1.2 fix : séparer exposition certaine (NC explicite chiffré) vs
        # pending (DT trajectoire / BACS A_RISQUE) — anti-violation "chiffres fiables"
        # qui sous-estimait silencieusement le total. Permet UI Marie DAF :
        # "X € confirmés · jusqu'à Y € en attente d'évaluation".
        site_exposure_certain = sum(fw["exposure_eur"] for fw in frameworks if fw["exposure_eur"] is not None)
        site_exposure_pending = sum(
            fw.get("exposure_max_eur", 0) or 0
            for fw in frameworks
            if fw["exposure_eur"] is None and (fw.get("exposure_max_eur") or 0) > 0
        )
        total_exposure_certain += site_exposure_certain
        total_exposure_pending_max += site_exposure_pending
        if site_exposure_pending > 0:
            pending_frameworks_count += 1

        # Site NC si au moins 1 framework explicitement non compliant + exposure chiffré > 0.
        # `compliant=None` (pending) n'est PAS comptabilisé NC.
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
                "exposure_certain_eur": site_exposure_certain,
                "exposure_pending_max_eur": site_exposure_pending,
                "is_non_compliant": is_nc,
                "frameworks": frameworks,
            }
        )

    audit_sme_data = [
        {
            "ej_id": ej.id,
            "nom": ej.nom,
            **_audit_sme_status(ej, today),
        }
        for ej in ejs
    ]

    return {
        "headlines": {
            "total_sites": len(sites),
            "non_compliant_count": non_compliant_count,
            # Phase H P1.2 fix : split certain vs pending pour traçabilité comité
            "total_exposure_certain_eur": total_exposure_certain,
            "total_exposure_pending_max_eur": total_exposure_pending_max,
            "pending_frameworks_count": pending_frameworks_count,
            # Backward-compat pour callsites Phase G existants (sera deprécié Phase I)
            "total_exposure_eur": total_exposure_certain + total_exposure_pending_max,
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


def get_contract_price_benchmark(db: Session, org_id: int, *, horizon_days: int = 180) -> dict:
    """Phase H6 — Comparateur prix marché vs prix contractuel (Jean-Marc CFO MVP).

    Pour chaque contrat expirant J-{horizon_days}, compute :
    - Prix moyen contractuel (EUR/MWh) calculé depuis price_ref ou fixed_fee
    - Prix forward marché EUR/MWh (MktPrice baseload calendar Y+1 zone FR)
    - Delta absolu €/MWh + delta_pct + impact économies annuel estimé

    Sans forward marché disponible → benchmark_status='no_market_data' + suggestion fallback.

    Returns:
        dict :
            - total_contracts : nb contrats fenêtre
            - benchmark_status : 'available' / 'no_market_data' / 'partial'
            - market_forward_eur_mwh : prix forward moyen Y+1 si dispo
            - contracts : [{contract_id, prix_contractuel_eur_mwh, delta_eur_mwh,
                            delta_pct, conso_annuelle_mwh, impact_economies_eur_an}]
    """
    from datetime import datetime, timedelta as _td, timezone as _tz

    from models.market_models import MarketType, MktPrice, ProductType

    today = date.today()
    horizon = today + _td(days=horizon_days)

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

    # Forward EPEX/EEX baseload Y+1 — moyenne des prix dans fenêtre 12 mois post-today
    next_year_start = datetime(today.year + 1, 1, 1, tzinfo=_tz.utc)
    next_year_end = datetime(today.year + 1, 12, 31, tzinfo=_tz.utc)
    forward_avg = (
        db.query(MktPrice.price_eur_mwh)
        .filter(
            MktPrice.market_type == MarketType.FORWARD_YEAR,
            MktPrice.product_type == ProductType.BASELOAD,
            MktPrice.delivery_start >= next_year_start,
            MktPrice.delivery_end <= next_year_end,
        )
        .all()
    )
    market_forward = round(sum(row[0] for row in forward_avg) / len(forward_avg), 2) if forward_avg else None

    contracts_data = []
    for c, s in contracts:
        # Prix contractuel : utilise price_ref_eur_per_kwh × 1000 (→ EUR/MWh)
        prix_eur_kwh = getattr(c, "price_ref_eur_per_kwh", None)
        prix_contractuel_mwh = round(prix_eur_kwh * 1000, 2) if prix_eur_kwh else None

        # Conso annuelle estimée (pour chiffrer impact économies)
        conso_annuelle_kwh = (
            db.query(EnergyInvoice.energy_kwh)
            .filter(EnergyInvoice.contract_id == c.id, EnergyInvoice.energy_kwh.isnot(None))
            .all()
        )
        conso_total = sum(row[0] for row in conso_annuelle_kwh) if conso_annuelle_kwh else 0
        conso_annuelle_mwh = round(conso_total / 1000, 1) if conso_total else None

        # Delta vs marché (en € / MWh — convention CFO : positif = surcoût client)
        delta_eur_mwh = None
        delta_pct = None
        impact_eur_an = None
        if prix_contractuel_mwh is not None and market_forward is not None:
            delta_eur_mwh = round(prix_contractuel_mwh - market_forward, 2)
            delta_pct = round((delta_eur_mwh / market_forward) * 100, 2) if market_forward > 0 else None
            if conso_annuelle_mwh:
                impact_eur_an = round(delta_eur_mwh * conso_annuelle_mwh, 0)

        contracts_data.append(
            {
                "contract_id": c.id,
                "supplier_name": c.supplier_name,
                "fournisseur_id": c.fournisseur_id,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "site_id": s.id,
                "site_nom": s.nom,
                "prix_contractuel_eur_mwh": prix_contractuel_mwh,
                "market_forward_eur_mwh": market_forward,
                "delta_eur_mwh": delta_eur_mwh,
                "delta_pct": delta_pct,
                "conso_annuelle_mwh": conso_annuelle_mwh,
                "impact_economies_eur_an": impact_eur_an,
            }
        )

    if market_forward is None:
        status = "no_market_data"
    elif any(c["prix_contractuel_eur_mwh"] is None for c in contracts_data):
        status = "partial"
    else:
        status = "available"

    return {
        "total_contracts": len(contracts_data),
        "horizon_days": horizon_days,
        "benchmark_status": status,
        "market_forward_eur_mwh": market_forward,
        "market_source": "MktPrice FORWARD_YEAR baseload Y+1 zone FR (EPEX/EEX)",
        "contracts": contracts_data,
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
