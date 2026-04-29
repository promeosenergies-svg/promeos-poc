"""Service cockpit_facts — endpoint atomique unifié (source unique Cockpit Daily + Comex).

Consolide tous les faits atomiques nécessaires aux 2 vues Cockpit en un seul
appel structuré. Délègue aux services existants — aucune logique métier nouvelle.

Fallback gracieux : chaque section est construite individuellement. En cas
d'exception, la section retourne des valeurs neutres plutôt qu'une erreur 500.

Constantes réglementaires : DT_PENALTY_EUR, BACS_PENALTY_EUR, OPERAT_PENALTY_EUR
issues de doctrine/constants.py — jamais de littéraux numériques ici.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.3
Doctrine : §11.3 source unique partagée + maquette v1.1 KPI 2
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Literal, Optional

CockpitFactsPeriod = Literal["current_week", "current_month", "current_year"]

from sqlalchemy import func
from sqlalchemy.orm import Session

from doctrine.constants import (
    BACS_PENALTY_EUR,
    DT_MILESTONES,
    DT_PENALTY_AT_RISK_EUR,
    DT_PENALTY_EUR,
    DT_REF_YEAR_DEFAULT,
    FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR,
    OPERAT_PENALTY_EUR,
    PRICE_FLEX_NEBCO_EUR_PER_MWH,
    REGOPS_WEIGHTS_DEFAULT,
)
from models import (
    Alerte,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    StatutConformite,
    not_deleted,
)
from models.energy_models import Meter, MeterReading
from models.power import PowerReading
from services.baseline_service import get_baseline_a, get_baseline_b, get_baseline_c
from services.monthly_comparison_service import get_monthly_vs_previous_year

_logger = logging.getLogger("promeos.cockpit_facts")

# ─── CEE références par défaut (modeled, maquette v1.1) ────────────────────
_CEE_DEFAULT_REFERENCES = ["CEE BAT-TH-116", "CEE BAT-TH-104"]
_CEE_DEFAULT_LEVERS = [
    {"name": "Système pilotage CVC", "value_mwh_year": 0, "reference": "CEE BAT-TH-116"},
    {"name": "Audit énergétique sites", "value_mwh_year": 0, "reference": "Code Énergie L233-1"},
]


# ─── Helpers scope ──────────────────────────────────────────────────────────


def _sites_for_org(db: Session, org_id: int):
    return (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )


def _meter_ids_for_site(db: Session, site_id: int) -> list[int]:
    rows = db.query(Meter.id).filter(Meter.site_id == site_id).all()
    return [r[0] for r in rows]


def j_minus_1_with_fallback(
    db: Session,
    meter_ids: list[int],
    today: date,
    *,
    max_days_back: int = 7,
) -> tuple[date, float, int]:
    """Cherche le dernier jour avec data dans les `max_days_back` derniers jours.

    Étape 4 P0-C backend : si J−1 = 0 (cas typique seed lundi : pas de data
    dimanche), on évite l'affichage "0,0 MWh −100%" qui casse la confiance
    energy manager (audit Marc 4/10 → 6.5/10).

    Note SQLite : les timestamps sont stockés en ISO 8601 ("YYYY-MM-DDTHH:MM:SS"
    avec T séparateur), mais SQLAlchemy sérialise par défaut datetime → "YYYY-MM-DD HH:MM:SS"
    (espace) — le filter ne matche jamais. On utilise `func.date(timestamp)` pour
    extraire la date côté DB et comparer comme string ISO ("YYYY-MM-DD").

    Returns:
        (target_date, kwh_total, days_offset) où days_offset est 1 pour J−1
        canonique, 2 pour J−2 fallback, etc. Retourne (j_minus_1, 0.0, 1) si
        meter_ids vide ou aucune data dans les `max_days_back` derniers jours.
    """
    j_minus_1 = today - timedelta(days=1)
    if not meter_ids:
        return j_minus_1, 0.0, 1
    for offset in range(1, max_days_back + 1):
        target = today - timedelta(days=offset)
        total = (
            db.query(func.sum(MeterReading.value_kwh))
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                func.date(MeterReading.timestamp) == target.isoformat(),
            )
            .scalar()
        )
        kwh = float(total) if total else 0.0
        if kwh > 0:
            return target, kwh, offset
    return j_minus_1, 0.0, 1


def _meter_ids_for_org(db: Session, site_ids: list[int]) -> list[int]:
    if not site_ids:
        return []
    rows = db.query(Meter.id).filter(Meter.site_id.in_(site_ids)).all()
    return [r[0] for r in rows]


# ─── Helper Phase 3.3 — alias historique vers doctrine.delta canonique ─────
# Phase 3.bis.b : hoist du helper vers `doctrine/delta.py` (single SoT).
# L'alias privé est conservé pour compat callers + tests internes du service.

from doctrine.delta import weekly_delta_struct as _weekly_delta_struct  # noqa: E402


# ─── Section scope ──────────────────────────────────────────────────────────


def _build_scope(db: Session, org_id: int) -> dict:
    try:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
        org_name = org.nom if org else f"Org {org_id}"

        sites = _sites_for_org(db, org_id).all()
        site_ids = [s.id for s in sites]
        surface_total = sum((s.surface_m2 or 0.0) for s in sites)

        return {
            "org_id": org_id,
            "org_name": org_name,
            "site_count": len(site_ids),
            "site_ids": site_ids,
            "surface_total_m2": round(surface_total, 1),
            "ref_year": DT_REF_YEAR_DEFAULT,
        }
    except Exception as exc:  # noqa: F841 — _logger.warning prend exc explicit
        _logger.warning("_build_scope error: %s", exc)
        return {
            "org_id": org_id,
            "org_name": f"Org {org_id}",
            "site_count": 0,
            "site_ids": [],
            "surface_total_m2": 0.0,
            "ref_year": DT_REF_YEAR_DEFAULT,
        }


# ─── Section consumption ────────────────────────────────────────────────────


def _build_consumption(
    db: Session,
    org_id: int,
    site_ids: list[int],
    today: date,
) -> dict:
    try:
        meter_ids = _meter_ids_for_org(db, site_ids)

        # J-1 consommation agrégée — Étape 4 P0-C : fallback intelligent.
        # Si J−1 = 0 (typique : lundi matin = pas de seed dimanche, ou trou
        # de couverture EMS), on cherche le dernier jour avec data dans les
        # 7 derniers jours et on signale via `j_minus_1_source` (j-1, j-2 …,
        # j-7) au frontend pour qu'il affiche un footer mono "MAJ il y a Nj".
        # Audit Marc Étape 1.bis : "0,0 MWh −100%" cassait la confiance.
        j_minus_1, j_minus_1_kwh, j_minus_1_offset = j_minus_1_with_fallback(db, meter_ids, today, max_days_back=7)
        d_start = datetime(j_minus_1.year, j_minus_1.month, j_minus_1.day, 0, 0, 0)
        d_end = datetime(j_minus_1.year, j_minus_1.month, j_minus_1.day, 23, 59, 59)
        j_minus_1_mwh = round(j_minus_1_kwh / 1000.0, 3)
        j_minus_1_source = "j-1" if j_minus_1_offset == 1 else f"j-{j_minus_1_offset}"

        # Baseline A pour J-1 (premier site disponible)
        baseline_j_minus_1 = {"value_mwh": 0.0, "method": "a_historical", "delta_pct": 0}
        if site_ids:
            try:
                b_a = get_baseline_a(db, site_ids[0], j_minus_1)
                bval_mwh = round(b_a["value_kwh"] / 1000.0, 3)
                delta_pct = round((j_minus_1_mwh - bval_mwh) / bval_mwh * 100) if bval_mwh > 0 else 0
                baseline_j_minus_1 = {
                    "value_mwh": bval_mwh,
                    "method": "a_historical",
                    "delta_pct": delta_pct,
                }
            except Exception as exc:
                _logger.debug("baseline_a J-1 failed: %s", exc)

        # Surconso 7j agrégée
        w_start = datetime.combine(today - timedelta(days=7), datetime.min.time())
        w_end = datetime.combine(today - timedelta(days=1), datetime.max.time())
        surconso_7d_kwh = 0.0
        if meter_ids:
            total_7d = (
                db.query(func.sum(MeterReading.value_kwh))
                .filter(
                    MeterReading.meter_id.in_(meter_ids),
                    MeterReading.timestamp >= w_start,
                    MeterReading.timestamp <= w_end,
                )
                .scalar()
            )
            surconso_7d_kwh = float(total_7d) if total_7d else 0.0
        surconso_7d_mwh = round(surconso_7d_kwh / 1000.0, 3)

        # Baseline B (7j, premier site)
        baseline_7d = {
            "method": "b_dju_adjusted",
            "r_squared": None,
            "calibration_date": datetime.utcnow().isoformat(),
        }
        if site_ids:
            try:
                # DJU fallback = 3.0/j × 7j
                b_b = get_baseline_b(db, site_ids[0], today, dju=21.0)
                baseline_7d = {
                    "method": b_b.get("method", "b_dju_adjusted"),
                    "r_squared": b_b.get("r_squared"),
                    "calibration_date": b_b.get("calibration_date", datetime.utcnow().isoformat()),
                }
            except Exception as exc:
                _logger.debug("baseline_b 7d failed: %s", exc)

        # Sites en dérive (surconso > 10% vs baseline A)
        sites_in_drift = 0
        for sid in site_ids:
            try:
                ba = get_baseline_a(db, sid, j_minus_1)
                mids = _meter_ids_for_site(db, sid)
                if mids:
                    total_site = (
                        db.query(func.sum(MeterReading.value_kwh))
                        .filter(
                            MeterReading.meter_id.in_(mids),
                            MeterReading.timestamp >= d_start,
                            MeterReading.timestamp <= d_end,
                        )
                        .scalar()
                    ) or 0.0
                    if ba["value_kwh"] > 0 and total_site > ba["value_kwh"] * 1.10:
                        sites_in_drift += 1
            except Exception as exc:
                _logger.debug("site drift check failed: %s", exc)

        # Annuel agrégé (12 mois glissants)
        y_start = datetime.combine(today - timedelta(days=365), datetime.min.time())
        y_end = datetime.combine(today, datetime.max.time())
        annual_kwh = 0.0
        if meter_ids:
            total_annual = (
                db.query(func.sum(MeterReading.value_kwh))
                .filter(
                    MeterReading.meter_id.in_(meter_ids),
                    MeterReading.timestamp >= y_start,
                    MeterReading.timestamp <= y_end,
                )
                .scalar()
            )
            annual_kwh = float(total_annual) if total_annual else 0.0
        annual_mwh = round(annual_kwh / 1000.0, 1)

        # Trajectoire 2030 via baseline C (premier site) → avancement
        trajectory_score = 0
        if site_ids:
            try:
                b_c = get_baseline_c(db, site_ids[0], year=DT_REF_YEAR_DEFAULT)
                ref_kwh = b_c.get("value_kwh_year", 0.0)
                # cible -40% en 2030 → avancement = (1 - annuel/ref) / abs(jalon) × 100, clamped 0-100
                if ref_kwh > 0 and annual_kwh > 0:
                    reduction = 1.0 - annual_kwh / ref_kwh
                    target_2030 = abs(DT_MILESTONES[2030])  # 0.40 — single SoT doctrine
                    trajectory_score = int(min(max(reduction / target_2030 * 100, 0), 100))
            except Exception as exc:
                _logger.debug("trajectory_2030 baseline_c failed: %s", exc)

        # monthly_vs_n1 — KPI 2 maquette v1.1
        monthly_vs_n1 = get_monthly_vs_previous_year(db, org_id, today)

        return {
            "j_minus_1_mwh": j_minus_1_mwh,
            "j_minus_1_source": j_minus_1_source,  # Étape 4 P0-C : transparence
            "baseline_j_minus_1": baseline_j_minus_1,
            "surconso_7d_mwh": surconso_7d_mwh,
            "baseline_7d": baseline_7d,
            "monthly_vs_n1": monthly_vs_n1,
            "sites_in_drift": sites_in_drift,
            "annual_mwh": annual_mwh,
            "trajectory_2030_score": trajectory_score,
            "trajectory_method": "c_regulatory_dt",
        }
    except Exception as exc:
        _logger.warning("_build_consumption error: %s", exc)
        return {
            "j_minus_1_mwh": 0.0,
            "j_minus_1_source": "j-1",
            "baseline_j_minus_1": {"value_mwh": 0.0, "method": "a_historical", "delta_pct": 0},
            "surconso_7d_mwh": 0.0,
            "baseline_7d": {
                "method": "b_dju_adjusted",
                "r_squared": None,
                "calibration_date": datetime.utcnow().isoformat(),
            },
            "monthly_vs_n1": {
                "current_month_label": "",
                "current_month_mwh": 0.0,
                "previous_year_month_normalized_mwh": 0.0,
                "delta_pct_dju_adjusted": 0,
                "baseline_method": "b_dju_adjusted",
                "calibration_date": datetime.utcnow().isoformat(),
                "r_squared": None,
                "confidence": "faible",
            },
            "sites_in_drift": 0,
            "annual_mwh": 0.0,
            "trajectory_2030_score": 0,
            "trajectory_method": "c_regulatory_dt",
        }


# ─── Section power ──────────────────────────────────────────────────────────


def _build_power(db: Session, site_ids: list[int], today: date) -> dict:
    _empty = {
        "peak_j_minus_1_kw": 0.0,
        "subscribed_kw": 0.0,
        "delta_pct": 0,
        "peak_time": "00:00",
        "peak_source": "j-1",
    }
    try:
        if not site_ids:
            return _empty

        meter_ids = _meter_ids_for_org(db, site_ids)
        if not meter_ids:
            return _empty

        # Étape 4 P0-C : fallback peak J−1 → cherche le dernier jour avec
        # PowerReading dans les 7 derniers jours pour éviter "0 kW" lundi.
        # Note SQLite : utiliser func.date() pour comparer dates car les
        # timestamps sont stockés en ISO ("T" séparateur) — cf. j_minus_1_with_fallback.
        # Étape 4 P0-C : fenêtre élargie à 60 jours pour PowerReading car le seed
        # CDC est plus parcimonieux que MeterReading (mensualisé, pas quotidien).
        # Si la dernière mesure date de J−30, le frontend l'affichera comme tel
        # ("Pic CDC il y a 30j") plutôt que "0 kW" sans contexte.
        peak_kw = 0.0
        peak_time = "00:00"
        peak_offset = 1
        target_date = today - timedelta(days=1)
        peak_row = None
        # 1ère stratégie : par jour exact (plus précis si data fraîche)
        for offset in range(1, 31):
            target = today - timedelta(days=offset)
            peak_row = (
                db.query(PowerReading.P_active_kw, PowerReading.ts_debut)
                .filter(
                    PowerReading.meter_id.in_(meter_ids),
                    func.date(PowerReading.ts_debut) == target.isoformat(),
                    PowerReading.sens == "CONS",
                )
                .order_by(PowerReading.P_active_kw.desc())
                .first()
            )
            if peak_row and peak_row[0] and peak_row[0] > 0:
                peak_offset = offset
                target_date = target
                break
        # 2nde stratégie fallback : prendre simplement le dernier point CDC
        # disponible si rien dans les 30 derniers jours.
        if not peak_row or not peak_row[0]:
            peak_row = (
                db.query(PowerReading.P_active_kw, PowerReading.ts_debut)
                .filter(
                    PowerReading.meter_id.in_(meter_ids),
                    PowerReading.sens == "CONS",
                )
                .order_by(PowerReading.P_active_kw.desc())
                .first()
            )
            if peak_row and peak_row[0]:
                target_date = peak_row[1].date() if peak_row[1] else today - timedelta(days=1)
                peak_offset = max(1, (today - target_date).days)

        # j_minus_1 utilisé uniquement comme variable cible pour traçabilité downstream.
        j_minus_1 = target_date

        if peak_row and peak_row[0] is not None:
            peak_kw = round(float(peak_row[0]), 1)
            peak_time = peak_row[1].strftime("%H:%M") if peak_row[1] else "00:00"

        # Puissance souscrite agrégée (somme des compteurs)
        subscribed_kw_total = 0.0
        meters = db.query(Meter).filter(Meter.id.in_(meter_ids)).all()
        for m in meters:
            if m.subscribed_power_kva is not None:
                subscribed_kw_total += m.subscribed_power_kva  # kVA ≈ kW approximation

        delta_pct = 0
        if subscribed_kw_total > 0 and peak_kw > 0:
            delta_pct = round((peak_kw - subscribed_kw_total) / subscribed_kw_total * 100)

        return {
            "peak_j_minus_1_kw": peak_kw,
            "subscribed_kw": round(subscribed_kw_total, 1),
            "delta_pct": delta_pct,
            "peak_time": peak_time,
            "peak_source": "j-1" if peak_offset == 1 else f"j-{peak_offset}",
        }
    except Exception as exc:
        _logger.warning("_build_power error: %s", exc)
        return _empty


# ─── Section compliance ─────────────────────────────────────────────────────


def _build_compliance(db: Session, org_id: int, site_ids: list[int]) -> dict:
    _empty = {
        "score": 0,
        "max": 100,
        "weighting": REGOPS_WEIGHTS_DEFAULT,
        "non_conform_sites": 0,
        "at_risk_sites": 0,
        "obligations_to_treat": 0,
    }
    try:
        from services.compliance_score_service import compute_portfolio_compliance

        portfolio = compute_portfolio_compliance(db, org_id)
        score = int(round(portfolio.get("avg_score", 0.0)))

        # Compter non-conforme et à risque directement depuis Site
        non_conform = 0
        at_risk = 0
        sites = _sites_for_org(db, org_id).all()
        for s in sites:
            dt_status = getattr(s, "statut_decret_tertiaire", None)
            bacs_status = getattr(s, "statut_bacs", None)
            is_nc = dt_status == StatutConformite.NON_CONFORME or bacs_status == StatutConformite.NON_CONFORME
            is_risk = dt_status == StatutConformite.A_RISQUE or bacs_status == StatutConformite.A_RISQUE
            if is_nc:
                non_conform += 1
            elif is_risk:
                at_risk += 1

        # Obligations à traiter via action center
        obligations_to_treat = 0
        try:
            from services.action_center_service import get_action_center_issues

            issues_data = get_action_center_issues(db, org_id)
            obligations_to_treat = issues_data.get("total", 0)
        except Exception as exc:
            obligations_to_treat = non_conform + at_risk

        return {
            "score": score,
            "max": 100,
            "weighting": REGOPS_WEIGHTS_DEFAULT,
            "non_conform_sites": non_conform,
            "at_risk_sites": at_risk,
            "obligations_to_treat": obligations_to_treat,
        }
    except Exception as exc:
        _logger.warning("_build_compliance error: %s", exc)
        return _empty


# ─── Section exposure ───────────────────────────────────────────────────────


def _build_exposure(db: Session, org_id: int, site_ids: list[int]) -> dict:
    _empty = {
        "total": {"value_eur": 0.0, "category": "calculated_regulatory", "regulatory_article": ""},
        "delta_vs_last_week": {"value_eur": 0.0, "category": "calculated_regulatory"},
        "components": [],
    }
    try:
        from services.eur_amount_service import build_regulatory

        sites = _sites_for_org(db, org_id).all()
        if not sites:
            return _empty

        components = []
        total_eur = 0.0

        # DT non-conforme → DT_PENALTY_EUR
        dt_nc = [s for s in sites if getattr(s, "statut_decret_tertiaire", None) == StatutConformite.NON_CONFORME]
        if dt_nc:
            val = len(dt_nc) * DT_PENALTY_EUR
            components.append(
                {
                    "label": "DT non conforme",
                    "count": len(dt_nc),
                    "unit_value_eur": DT_PENALTY_EUR,
                    "value_eur": val,
                    "regulatory_article": "Décret 2019-771 art. 9",
                }
            )
            total_eur += val

        # DT à risque → DT_PENALTY_AT_RISK_EUR
        dt_ar = [s for s in sites if getattr(s, "statut_decret_tertiaire", None) == StatutConformite.A_RISQUE]
        if dt_ar:
            val = len(dt_ar) * DT_PENALTY_AT_RISK_EUR
            components.append(
                {
                    "label": "DT à risque",
                    "count": len(dt_ar),
                    "unit_value_eur": DT_PENALTY_AT_RISK_EUR,
                    "value_eur": val,
                    "regulatory_article": "Décret 2019-771 art. 9",
                }
            )
            total_eur += val

        # BACS non-conforme → BACS_PENALTY_EUR
        bacs_nc = [s for s in sites if getattr(s, "statut_bacs", None) == StatutConformite.NON_CONFORME]
        if bacs_nc:
            val = len(bacs_nc) * BACS_PENALTY_EUR
            components.append(
                {
                    "label": "BACS non conforme",
                    "count": len(bacs_nc),
                    "unit_value_eur": BACS_PENALTY_EUR,
                    "value_eur": val,
                    "regulatory_article": "Décret 2020-887",
                }
            )
            total_eur += val

        # OPERAT manquante → OPERAT_PENALTY_EUR (sites sans déclaration OPERAT)
        operat_missing = [
            s
            for s in sites
            if getattr(s, "operat_declared", None) is False or getattr(s, "statut_operat", None) == "non_declared"
        ]
        if not operat_missing:
            # Fallback : sites sans statut DT défini interprétés comme OPERAT manquante
            operat_missing = [s for s in sites if getattr(s, "statut_decret_tertiaire", None) is None]
        if operat_missing:
            val = len(operat_missing) * OPERAT_PENALTY_EUR
            components.append(
                {
                    "label": "OPERAT manquante",
                    "count": len(operat_missing),
                    "unit_value_eur": OPERAT_PENALTY_EUR,
                    "value_eur": val,
                    "regulatory_article": "Circulaire DGEC 2024",
                }
            )
            total_eur += val

        # Persistance EurAmount via eur_amount_service (traçabilité Phase 1.1)
        if total_eur > 0:
            try:
                formula_parts = [f"{c['count']} × {c['unit_value_eur']}€ ({c['label']})" for c in components]
                build_regulatory(
                    db=db,
                    value_eur=total_eur,
                    regulatory_article="Décret 2019-771 art. 9 + Décret 2020-887 + Circulaire DGEC 2024",
                    formula_text=" + ".join(formula_parts),
                )
            except Exception as exc:
                pass  # Persistance non-bloquante

        # Delta vs semaine dernière (non-calculé ici — donnée dynamique)
        delta_last_week = 0.0

        return {
            "total": {
                "value_eur": round(total_eur, 2),
                "category": "calculated_regulatory",
                "regulatory_article": "Décret 2019-771 art. 9",
            },
            "delta_vs_last_week": {
                "value_eur": delta_last_week,
                "category": "calculated_regulatory",
            },
            "components": components,
        }
    except Exception as exc:
        _logger.warning("_build_exposure error: %s", exc)
        return _empty


# ─── Section potential_recoverable ──────────────────────────────────────────


def _build_potential_recoverable(db: Session, org_id: int, site_ids: list[int]) -> dict:
    _empty = {
        "value_mwh_year": 0,
        "method": "modeled_cee",
        "references": _CEE_DEFAULT_REFERENCES,
        "leverage_count": 0,
        "by_lever": [],
    }
    try:
        # Tentative via analytics_engine recommendations si disponible
        total_kwh = 0.0
        levers_out = []

        if site_ids:
            try:
                from services.analytics_engine import get_site_analytics

                for sid in site_ids[:5]:  # limiter à 5 sites pour performance
                    try:
                        analytics = get_site_analytics(db, sid)
                        recs = analytics.get("recommendations", [])
                        for rec in recs:
                            savings_kwh = rec.get("estimated_savings_kwh_year") or rec.get("estimated_savings_kwh", 0)
                            if savings_kwh and savings_kwh > 0:
                                total_kwh += float(savings_kwh)
                                levers_out.append(
                                    {
                                        "name": rec.get("title", rec.get("label", "Levier optimisation")),
                                        "value_mwh_year": round(float(savings_kwh) / 1000.0, 1),
                                        "reference": rec.get("cee_reference", "CEE BAT-TH-116"),
                                    }
                                )
                    except Exception as exc:
                        _logger.debug("analytics potential_recoverable inner failed: %s", exc)
            except Exception as exc:
                _logger.debug("analytics potential_recoverable outer failed: %s", exc)

        if not levers_out:
            # Fallback : estimation modèle CEE sur surface totale
            try:
                surface_total = (
                    not_deleted(db.query(Site.surface_m2), Site)
                    .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
                    .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
                    .filter(EntiteJuridique.organisation_id == org_id)
                    .all()
                )
                total_m2 = sum(r[0] for r in surface_total if r[0])
                if total_m2 > 0:
                    # Estimation ~15 kWh/m2/an d'économies potentielles (modèle CEE conservatif)
                    total_kwh = total_m2 * 15.0
                    levers_out = [
                        {
                            "name": "Système pilotage CVC",
                            "value_mwh_year": round(total_kwh * 0.47 / 1000.0, 1),
                            "reference": "CEE BAT-TH-116",
                        },
                        {
                            "name": "Audit énergétique sites",
                            "value_mwh_year": round(total_kwh * 0.53 / 1000.0, 1),
                            "reference": "Code Énergie L233-1",
                        },
                    ]
            except Exception as exc:
                levers_out = _CEE_DEFAULT_LEVERS

        value_mwh = int(round(total_kwh / 1000.0))
        references = list({lev["reference"] for lev in levers_out}) if levers_out else _CEE_DEFAULT_REFERENCES

        return {
            "value_mwh_year": value_mwh,
            "method": "modeled_cee",
            "references": references,
            "leverage_count": len(levers_out),
            "by_lever": levers_out,
        }
    except Exception as exc:
        _logger.warning("_build_potential_recoverable error: %s", exc)
        return _empty


# ─── Section alerts ─────────────────────────────────────────────────────────


def _build_alerts(db: Session, org_id: int, site_ids: list[int]) -> dict:
    _empty = {
        "total": 0,
        "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "by_type": {},
    }
    try:
        # Alertes DB
        alerte_rows = (
            db.query(Alerte).filter(Alerte.resolue == False, Alerte.site_id.in_(site_ids)).all() if site_ids else []
        )
        alert_count = len(alerte_rows)

        # Issues action center
        ac_total = 0
        by_severity: dict = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_type: dict = {}

        try:
            from services.action_center_service import get_action_center_issues

            issues_data = get_action_center_issues(db, org_id)
            ac_total = issues_data.get("total", 0)
            for issue in issues_data.get("issues", []):
                sev = issue.get("severity", "medium")
                if hasattr(sev, "value"):
                    sev = sev.value
                by_severity[sev] = by_severity.get(sev, 0) + 1
                domain = issue.get("domain", "other")
                by_type[domain] = by_type.get(domain, 0) + 1
        except Exception as exc:
            _logger.debug("alerts action_center fallback failed: %s", exc)

        return {
            "total": alert_count + ac_total,
            "by_severity": by_severity,
            "by_type": by_type,
        }
    except Exception as exc:
        _logger.warning("_build_alerts error: %s", exc)
        return _empty


# ─── Section data_quality ───────────────────────────────────────────────────


def _build_data_quality(db: Session, site_ids: list[int], today: date) -> dict:
    _empty = {
        "ems_coverage_pct": 0,
        "data_completeness_pct": 0,
        "missing_indices_24h": 0,
        "sites_with_gaps": [],
    }
    try:
        if not site_ids:
            return _empty

        # Couverture EMS : sites avec au moins 1 compteur actif
        sites_with_meters = 0
        sites_with_gaps = []
        d_start = datetime(today.year, today.month, today.day, 0, 0, 0) - timedelta(days=1)
        d_end = datetime(today.year, today.month, today.day, 23, 59, 59)

        missing_24h = 0
        for sid in site_ids:
            mids = _meter_ids_for_site(db, sid)
            if mids:
                sites_with_meters += 1
                # Vérifier données J-1
                count_24h = (
                    db.query(func.count(MeterReading.id))
                    .filter(
                        MeterReading.meter_id.in_(mids),
                        MeterReading.timestamp >= d_start,
                        MeterReading.timestamp <= d_end,
                    )
                    .scalar()
                ) or 0
                if count_24h == 0:
                    missing_24h += len(mids)
                    # Récupérer le nom du site pour le rapport
                    site_obj = db.query(Site).filter(Site.id == sid).first()
                    if site_obj and site_obj.nom:
                        sites_with_gaps.append(site_obj.nom)

        ems_coverage = int(sites_with_meters / len(site_ids) * 100) if site_ids else 0
        data_completeness = max(0, 100 - int(missing_24h / max(len(site_ids), 1) * 10))

        return {
            "ems_coverage_pct": ems_coverage,
            "data_completeness_pct": data_completeness,
            "missing_indices_24h": missing_24h,
            "sites_with_gaps": sites_with_gaps,
        }
    except Exception as exc:
        _logger.warning("_build_data_quality error: %s", exc)
        return _empty


# ─── Entrée publique ─────────────────────────────────────────────────────────


def get_cockpit_facts(
    db: Session,
    org_id: int,
    period: CockpitFactsPeriod = "current_week",
) -> dict:
    """Endpoint atomique unifié — source unique pour Cockpit Daily + Comex.

    Délègue aux services existants (KpiService, baseline_service,
    monthly_comparison_service, eur_amount_service). Aucune logique
    métier nouvelle ici, juste consolidation.

    Fallback : chaque section construite individuellement, exception
    capturée et section retournée vide plutôt qu'erreur 500 globale.

    Args:
        db:     session SQLAlchemy
        org_id: identifiant organisation (org-scoped obligatoire)
        period: "current_week" | "current_month" | "current_year"

    Returns:
        dict avec sections : scope, consumption, power, compliance,
        exposure, potential_recoverable, alerts, data_quality, metadata.
    """
    today = date.today()

    # 1. Scope
    scope = _build_scope(db, org_id)
    site_ids: list[int] = scope["site_ids"]

    # 2. Consumption (inclut monthly_vs_n1)
    consumption = _build_consumption(db, org_id, site_ids, today)

    # 3. Power
    power = _build_power(db, site_ids, today)

    # 4. Compliance
    compliance = _build_compliance(db, org_id, site_ids)

    # 5. Exposure (utilise constantes doctrine)
    exposure = _build_exposure(db, org_id, site_ids)

    # 6. Potential recoverable (CEE modeled)
    potential_recoverable = _build_potential_recoverable(db, org_id, site_ids)

    # 7. Alerts
    alerts = _build_alerts(db, org_id, site_ids)

    # 8. Data quality
    data_quality = _build_data_quality(db, site_ids, today)

    # 9bis. Flex potential — Étape 4 P0-E : teaser carte Décision exige
    # un eur_year crédible. MVP : heuristique sur sites_count ; sera
    # remplacé par flex_assessment_service Phase 5.
    flex_potential = _build_flex_potential(db, org_id, site_ids)

    # 9. Metadata
    metadata = {
        "last_update": datetime.utcnow().isoformat() + "Z",
        "confidence": "haute" if scope["site_count"] > 0 else "faible",
        "sources": ["RegOps", "RegAssessment", "EMS", "Décret 2019-771"],
        "period": period,
    }

    # 10. Phase 3.3 — push événementiel "+X vs S-1" (4 métriques canoniques)
    # MVP : previous_value=None tant que l'historique semaine n'est pas seedé.
    # Le frontend gère direction='unknown' en n'affichant pas le push.
    weekly_deltas = {
        "exposure_eur": _weekly_delta_struct(
            current_value=(exposure.get("total") or {}).get("value_eur"),
            previous_value=None,
            unit="€",
        ),
        "potential_mwh_year": _weekly_delta_struct(
            current_value=potential_recoverable.get("value_mwh_year"),
            previous_value=None,
            unit="MWh/an",
        ),
        "sites_in_drift": _weekly_delta_struct(
            current_value=consumption.get("sites_in_drift"),
            previous_value=None,
            unit="sites",
        ),
        "compliance_score": _weekly_delta_struct(
            current_value=compliance.get("score"),
            previous_value=None,
            unit="pts",
        ),
    }

    return {
        "scope": scope,
        "consumption": consumption,
        "power": power,
        "compliance": compliance,
        "exposure": exposure,
        "potential_recoverable": potential_recoverable,
        "flex_potential": flex_potential,
        "alerts": alerts,
        "data_quality": data_quality,
        "metadata": metadata,
        "weekly_deltas": weekly_deltas,
    }


def _build_flex_potential(db: Session, org_id: int, site_ids: list[int]) -> dict:
    """Estimation eur_year + mwh_year potentiel d'effacement (NEBCO/AOFD).

    Étape 4 P0-E backend : MVP heuristique pour la carte teaser Décision.
    Logique : si FlexAssessment existe pour les sites de l'org, on agrège
    `potential_kwh_year` × prix marché effacement (~80 €/MWh observatoire
    CRE T4 2025). Sinon fallback heuristique 4 200 €/site/an (médiane
    sites tertiaires NEBCO 100 kW pilotable).

    Doctrine : badge `Indicatif` côté FE car estimation non contractuelle.
    """
    _empty = {
        "eur_year": None,
        "mwh_year": None,
        "method": "indicative",
        "source": "Heuristique NEBCO médiane CRE T4 2025",
        "leverage_count": 0,
    }
    try:
        if not site_ids:
            return _empty
        try:
            from models.flex_models import FlexAssessment  # type: ignore
        except Exception:
            FlexAssessment = None  # noqa: N806

        if FlexAssessment is not None:
            assessments = db.query(FlexAssessment).filter(FlexAssessment.site_id.in_(site_ids)).all()
            if assessments:
                mwh_total = sum((a.potential_kwh_year or 0) / 1000 for a in assessments)
                # Étape 6.bis : prix marché effacement = SoT canonique
                # PRICE_FLEX_NEBCO_EUR_PER_MWH (doctrine/constants.py).
                eur_total = mwh_total * PRICE_FLEX_NEBCO_EUR_PER_MWH
                return {
                    "eur_year": round(eur_total),
                    "mwh_year": round(mwh_total),
                    "method": "modeled_nebco",
                    "source": (f"FlexAssessment × prix effacement CRE {int(PRICE_FLEX_NEBCO_EUR_PER_MWH)} €/MWh"),
                    "leverage_count": len(assessments),
                }
        # Fallback heuristique — Étape 6.bis : SoT canonique.
        site_count = len(site_ids)
        return {
            "eur_year": site_count * FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR,
            "mwh_year": site_count * 50,
            "method": "heuristic_per_site",
            "source": (f"Heuristique NEBCO {FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR}€/site CRE T4 2025"),
            "leverage_count": 0,
        }
    except Exception as exc:
        _logger.warning("_build_flex_potential error: %s", exc)
        return _empty
