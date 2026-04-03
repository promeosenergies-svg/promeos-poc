"""
Service Audit Energetique / SME.

REGLES CANONIQUES (loi 2025-391, art. L.233-1) :
- Seuil SME     : >= 23 600 000 kWh/an (23.6 GWh)
- Seuil Audit   : >=  2 750 000 kWh/an (2.75 GWh) ET < 23.6 GWh ET pas de SME
- Deadline P1   : 11 octobre 2026 (entreprises existantes)
- Periodicite   : tous les 4 ans
- Delai transm. : 2 mois apres audit/certification
- Conso         : energie finale moyenne 3 ans, tous vecteurs, incl. ENR autoconsommee

Calcul conso : somme kWh de tous les sites de l'entite juridique,
tous vecteurs (elec + gaz + chaleur + fioul...), moyennee sur 3 ans disponibles.
Source unique : consumption_unified_service (SoT).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Seuils reglementaires (loi 2025-391)
SEUIL_SME_KWH = 23_600_000  # 23.6 GWh
SEUIL_AUDIT_KWH = 2_750_000  # 2.75 GWh
DATE_DEADLINE_P1 = date(2026, 10, 11)
PERIODICITE_ANS = 4
DELAI_TRANSMISSION = 2  # mois apres audit


def get_organisation_annual_consumption(
    db: Session,
    organisation_id: int,
    n_years: int = 3,
) -> dict:
    """
    Calcule la consommation annuelle moyenne d'une organisation sur n_years ans.
    Utilise consumption_unified_service.get_portfolio_consumption comme SoT.

    Returns:
        {
            conso_annuelle_moy_kwh: float,
            conso_annuelle_moy_gwh: float,
            periode: str,
            n_annees: int,
            detail_vecteurs: dict,
            confidence: str,
        }
    """
    from services.consumption_unified_service import get_portfolio_consumption

    today = date.today()
    end = today
    start = date(today.year - n_years, today.month, today.day)

    try:
        portfolio = get_portfolio_consumption(db, organisation_id, start, end)
    except Exception as exc:
        logger.warning("Erreur calcul conso org %d: %s", organisation_id, exc)
        portfolio = {"total_kwh": 0, "sites_count": 0, "sites_with_data": 0, "confidence": "none"}

    total_kwh = portfolio.get("total_kwh", 0.0)
    # Moyenne annuelle
    conso_moy_kwh = total_kwh / n_years if n_years > 0 else total_kwh

    return {
        "conso_annuelle_moy_kwh": conso_moy_kwh,
        "conso_annuelle_moy_gwh": conso_moy_kwh / 1_000_000,
        "periode": f"{start.isoformat()} -> {end.isoformat()}",
        "n_annees": n_years,
        "detail_vecteurs": {},
        "confidence": portfolio.get("confidence", "none"),
        "sites_count": portfolio.get("sites_count", 0),
        "sites_with_data": portfolio.get("sites_with_data", 0),
    }


def compute_obligation(conso_annuelle_moy_kwh: float, sme_certifie: bool = False) -> dict:
    """
    Determine l'obligation reglementaire selon la consommation annuelle moyenne.
    """
    if sme_certifie:
        return {
            "obligation": "SME_ISO50001",
            "seuil_applicable": ">= 2.75 GWh (SME certifie -> exonere de l'audit)",
            "description": "SME ISO 50001 certifie -> conforme (recertification triennale)",
            "source_reglementaire": "Loi 2025-391, art. L.233-1",
            "periodicite_ans": None,
        }

    if conso_annuelle_moy_kwh >= SEUIL_SME_KWH:
        return {
            "obligation": "SME_ISO50001",
            "seuil_applicable": ">= 23.6 GWh/an",
            "description": "SME ISO 50001 certifie obligatoire (consommation >= 23.6 GWh/an)",
            "source_reglementaire": "Loi 2025-391, art. L.233-1",
            "periodicite_ans": None,
        }
    elif conso_annuelle_moy_kwh >= SEUIL_AUDIT_KWH:
        conso_gwh = conso_annuelle_moy_kwh / 1_000_000
        return {
            "obligation": "AUDIT_4ANS",
            "seuil_applicable": ">= 2.75 GWh/an et < 23.6 GWh/an",
            "description": f"Audit energetique obligatoire tous les 4 ans (conso = {conso_gwh:.2f} GWh/an)",
            "source_reglementaire": "Loi 2025-391, art. L.233-1",
            "periodicite_ans": PERIODICITE_ANS,
            "deadline_premier_audit": DATE_DEADLINE_P1.isoformat(),
        }
    else:
        conso_gwh = conso_annuelle_moy_kwh / 1_000_000
        return {
            "obligation": "AUCUNE",
            "seuil_applicable": "< 2.75 GWh/an",
            "description": f"Aucune obligation d'audit/SME (conso = {conso_gwh:.2f} GWh/an < 2.75 GWh)",
            "source_reglementaire": "Loi 2025-391, art. L.233-1",
            "periodicite_ans": None,
        }


def compute_statut(audit_record, obligation: str, today: date = None) -> str:
    """
    Determine le statut de conformite Audit/SME.

    Statuts :
    - CONFORME       : audit realise dans les delais, transmission faite
    - A_REALISER     : obligation applicable, aucun audit realise, delai non depasse
    - EN_RETARD      : obligation applicable, delai depasse ou proche (<90 jours)
    - EN_COURS       : auditeur identifie, audit en preparation
    - NON_CONCERNE   : obligation = AUCUNE
    """
    if today is None:
        today = date.today()

    if obligation == "AUCUNE":
        return "NON_CONCERNE"

    if obligation == "SME_ISO50001" and getattr(audit_record, "sme_certifie_iso50001", False):
        return "CONFORME"

    audit_realise = getattr(audit_record, "audit_realise", False)
    if audit_realise:
        transmission = getattr(audit_record, "transmission_realisee", False)
        return "CONFORME" if transmission else "A_REALISER"

    # Audit non realise
    deadline = getattr(audit_record, "date_premier_audit_limite", DATE_DEADLINE_P1) or DATE_DEADLINE_P1
    jours_restants = (deadline - today).days

    if jours_restants < 90:
        return "EN_RETARD"
    if getattr(audit_record, "auditeur_identifie", False):
        return "EN_COURS"
    else:
        return "A_REALISER"


SCORES_AUDIT_SME = {
    "NON_CONCERNE": 1.0,
    "CONFORME": 1.0,
    "EN_COURS": 0.6,
    "A_REALISER": 0.3,
    "EN_RETARD": 0.0,
}


def compute_score_audit_sme(audit_record, obligation: str, statut: str) -> float:
    """Score 0.0 -> 1.0 pour la contribution Audit/SME au scoring RegOps."""
    return SCORES_AUDIT_SME.get(statut, 0.3)


_NOT_PROVIDED = object()


def get_audit_sme_assessment(
    db: Session,
    organisation_id: int,
    today: date = None,
    _prefetched_audit=_NOT_PROVIDED,
) -> dict:
    """
    Evaluation complete Audit/SME pour une organisation.

    Args:
        _prefetched_audit: sentinel-guarded pre-fetched AuditEnergetique record.
            Pass the record or None (no record exists) to skip the DB query.
            Leave default (_NOT_PROVIDED) to let the function query itself.
    """
    from models.audit_sme import AuditEnergetique

    if today is None:
        today = date.today()

    # 1. Recuperer le record audit existant (skip query if pre-fetched)
    if _prefetched_audit is not _NOT_PROVIDED:
        audit = _prefetched_audit
    else:
        audit = db.query(AuditEnergetique).filter_by(organisation_id=organisation_id).first()

    # 2. Calculer la consommation annuelle moyenne (3 ans)
    # Priorite : conso live > conso stockee dans le record audit (seed/manual)
    conso_result = get_organisation_annual_consumption(db, organisation_id, n_years=3)
    conso_moy_kwh = conso_result.get("conso_annuelle_moy_kwh", 0.0)

    # Fallback : si la conso live est nulle ou tres faible mais qu'un record
    # audit existe avec une conso stockee (seed ou saisie manuelle), l'utiliser
    stored_conso = getattr(audit, "conso_annuelle_moy_kwh", None) if audit else None
    if stored_conso and stored_conso > conso_moy_kwh:
        conso_moy_kwh = stored_conso
        conso_result["conso_annuelle_moy_kwh"] = stored_conso
        conso_result["conso_annuelle_moy_gwh"] = stored_conso / 1_000_000
        conso_result["confidence"] = "medium"

    conso_moy_gwh = conso_moy_kwh / 1_000_000

    # 3. Determiner l'obligation
    sme_certifie = getattr(audit, "sme_certifie_iso50001", False) if audit else False
    obligation_info = compute_obligation(conso_moy_kwh, sme_certifie)
    obligation = obligation_info["obligation"]

    # 4. Determiner le statut
    statut = compute_statut(audit, obligation, today)

    # 5. Score
    score = compute_score_audit_sme(audit, obligation, statut)

    # 6. Deadline et jours restants
    deadline = DATE_DEADLINE_P1
    if audit and audit.date_premier_audit_limite:
        deadline = audit.date_premier_audit_limite
    jours_restants = (deadline - today).days if obligation != "AUCUNE" else None

    # 7. Checklist
    checklist = _build_checklist(audit, obligation, statut, jours_restants)

    # 8. Actions recommandees
    actions = _build_actions(obligation, statut, jours_restants, audit)

    return {
        "organisation_id": organisation_id,
        "conso": {
            "annuelle_moy_kwh": round(conso_moy_kwh, 0),
            "annuelle_moy_gwh": round(conso_moy_gwh, 3),
            "periode": conso_result.get("periode"),
            "n_annees": conso_result.get("n_annees", 0),
            "vecteurs": conso_result.get("detail_vecteurs", {}),
        },
        "obligation": obligation,
        "obligation_info": obligation_info,
        "statut": statut,
        "score_audit_sme": round(score, 2),
        "deadline": deadline.isoformat() if deadline else None,
        "jours_restants": jours_restants,
        "urgence": _compute_urgence(obligation, jours_restants),
        "checklist": checklist,
        "actions_recommandees": actions,
        "source": "audit_sme_service",
        "confidence": conso_result.get("confidence", 0.8),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Scoring global RegOps avec Audit/SME ────────────────────────────────────

# CEE exclu tant que evaluateurs non implementes — poids somment a 1.0
WEIGHTS_WITH_AUDIT_SME = {
    "DT": 0.39,
    "BACS": 0.28,
    "APER": 0.17,
    "AUDIT_SME": 0.16,
}

WEIGHTS_WITHOUT_AUDIT_SME = {
    "DT": 0.45,
    "BACS": 0.30,
    "APER": 0.25,
}


def compute_global_score_with_audit_sme(
    score_dt: Optional[float],
    score_bacs: Optional[float],
    score_aper: Optional[float],
    score_audit_sme: Optional[float],
    audit_sme_applicable: bool,
) -> dict:
    """
    Calcule le score global RegOps en tenant compte de l'Audit/SME.

    Regle de redistribution proportionnelle : si un score est None (non applicable),
    son poids est redistribue entre les autres composantes.
    """
    if audit_sme_applicable:
        weights = WEIGHTS_WITH_AUDIT_SME
        scores_raw = {
            "DT": score_dt,
            "BACS": score_bacs,
            "APER": score_aper,
            "AUDIT_SME": score_audit_sme,
        }
    else:
        weights = WEIGHTS_WITHOUT_AUDIT_SME
        scores_raw = {
            "DT": score_dt,
            "BACS": score_bacs,
            "APER": score_aper,
        }

    total_weight_applicable = sum(weights[k] for k, v in scores_raw.items() if v is not None and k in weights)

    score_global = 0.0
    detail = {}

    for component, score in scores_raw.items():
        if component not in weights:
            continue
        if score is None:
            detail[component] = {"score": None, "applicable": False, "poids": 0}
            continue

        poids_redistribue = weights[component] / total_weight_applicable if total_weight_applicable > 0 else 0
        contribution = score * poids_redistribue
        score_global += contribution

        detail[component] = {
            "score": round(score, 3),
            "applicable": True,
            "poids_theorique": weights[component],
            "poids_redistribue": round(poids_redistribue, 3),
            "contribution": round(contribution, 3),
        }

    return {
        "score_global": round(score_global, 3),
        "detail": detail,
        "audit_sme_applicable": audit_sme_applicable,
        "source": "compliance_score_service",
    }


# ── Helpers internes ─────────────────────────────────────────────────────────


def _compute_urgence(obligation: str, jours_restants) -> Optional[str]:
    if obligation == "AUCUNE":
        return None
    if jours_restants is not None and jours_restants < 90:
        return "CRITIQUE"
    if jours_restants is not None and jours_restants < 180:
        return "ELEVEE"
    return "NORMALE"


def _build_checklist(audit, obligation: str, statut: str, jours_restants) -> list:
    """Checklist des prerequis Audit/SME."""
    if obligation == "AUCUNE":
        return [{"critere": "Consommation < 2.75 GWh/an", "ok": True, "note": "Non concerne"}]

    items = [
        {
            "critere": "Consommation moyenne 3 ans >= seuil",
            "ok": True,
            "note": f"Obligation {obligation} confirmee",
            "source": "Loi 2025-391 art. L.233-1",
        },
        {
            "critere": "Auditeur reconnu identifie",
            "ok": getattr(audit, "auditeur_identifie", False),
            "note": "Auditeur qualifie ou accredite COFRAC requis",
            "bloquant": True,
        },
        {
            "critere": "Audit energetique realise",
            "ok": getattr(audit, "audit_realise", False),
            "note": f"Deadline : {DATE_DEADLINE_P1.strftime('%d/%m/%Y')} (J-{jours_restants or '?'})",
            "bloquant": True,
        },
        {
            "critere": "Plan d'action elabore et publie dans le rapport annuel",
            "ok": getattr(audit, "plan_action_publie", False),
            "note": "Justification obligatoire si ROI < 5 ans non mis en oeuvre",
            "bloquant": False,
        },
        {
            "critere": "Transmission electronique a l'administration (< 2 mois)",
            "ok": getattr(audit, "transmission_realisee", False),
            "note": "Dans les 2 mois suivant la realisation",
            "bloquant": False,
        },
    ]

    if obligation == "SME_ISO50001":
        items.insert(
            2,
            {
                "critere": "Certification ISO 50001 obtenue (organisme accredite COFRAC)",
                "ok": getattr(audit, "sme_certifie_iso50001", False),
                "note": "Obligatoire si conso >= 23.6 GWh/an",
                "bloquant": True,
            },
        )

    return items


def _build_actions(obligation, statut, jours_restants, audit) -> list:
    """Actions recommandees selon statut."""
    if obligation == "AUCUNE":
        return []

    actions = []

    if statut in ("A_REALISER", "EN_RETARD") and not getattr(audit, "audit_realise", False):
        urgence = "CRITIQUE" if (jours_restants or 999) < 90 else "HAUTE"
        actions.append(
            {
                "code": "IDENTIFIER_AUDITEUR",
                "label": "Identifier un auditeur reconnu (qualifie ou accredite COFRAC)",
                "urgence": urgence,
                "echeance_jours": min(30, jours_restants or 30),
                "category": "CONFORMITE",
            }
        )
        actions.append(
            {
                "code": "PLANIFIER_AUDIT",
                "label": f"Planifier l'audit energetique avant le {DATE_DEADLINE_P1.strftime('%d/%m/%Y')}",
                "urgence": urgence,
                "echeance_jours": jours_restants or 30,
                "category": "CONFORMITE",
            }
        )

    if statut in ("CONFORME", "EN_COURS") and not getattr(audit, "plan_action_publie", False):
        actions.append(
            {
                "code": "PUBLIER_PLAN_ACTION",
                "label": "Elaborer et publier le plan d'action dans le rapport annuel",
                "urgence": "NORMALE",
                "echeance_jours": 60,
                "category": "CONFORMITE",
            }
        )

    if getattr(audit, "audit_realise", False) and not getattr(audit, "transmission_realisee", False):
        actions.append(
            {
                "code": "TRANSMETTRE_ADMIN",
                "label": "Transmettre le resultat de l'audit a l'administration (delai 2 mois)",
                "urgence": "HAUTE",
                "echeance_jours": 60,
                "category": "CONFORMITE",
            }
        )

    return actions
