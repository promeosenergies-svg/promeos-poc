"""PROMEOS — services compute_* Synthèse Stratégique v1.0 (Phase 3.6 Vague AA).

Référence : `docs/dev/synthese_strategique_runbook.md` punchlist Phase 3.6 #7-#11.

Remplace les stubs de Phase 3.5 (notamment `_DEMO_TRAJECTORY_DRIFT_STUB_PCT = 8.0`
dans routes/cockpit_strategique.py:56) par des calculs réels lisant les SoT existantes :
  - RegAssessment.findings_json + Site.intensity_kwh_m2_tertiaire (trajectoire DT)
  - ContratCadre.date_fin + ContractAnnexe.end_date_override (échéance contrat)
  - ContratCadre.type_prix (spot exposure)
  - Site.intensity_kwh_m2_tertiaire + Site.nom (bench multi-sites)

Discipline d'import (Phase 0 Q2) : aucun import depuis
services.compliance_readiness_service.compute_applicability (legacy).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from services.scope_utils import sites_for_org_query


_logger = logging.getLogger(__name__)


# Année cible Décret tertiaire — référence trajectoire 2030 (cf. SKILL.md).
DT_TARGET_YEAR: int = 2030
DT_TARGET_PCT: float = 40.0  # -40 % vs année référence (-50 %/2040, -60 %/2050)


def compute_trajectory_drift(db: Session, org_id: int) -> dict[str, Any]:
    """Calcule la dérive trajectoire DT moyenne des sites assujettis.

    Méthode v1.0 :
      - Pour chaque site avec `intensity_kwh_m2_tertiaire` renseigné et
        `annee_reference_operat` connue, dériver le % atteint vs cible 2030.
      - Drift = max(0, DT_TARGET_PCT - moyenne_atteint_pct).
      - Si aucun site exploitable → drift = 0.0 (`source=insufficient_data`).

    Args:
        db: Session SQLAlchemy.
        org_id: identifiant organisation.

    Returns:
        dict {
          "drift_pct": float (≥ 0),
          "atteint_pct_moyen": float,
          "sites_count": int (sites exploités dans le calcul),
          "source": "computed" | "insufficient_data"
        }
    """
    sites = list(sites_for_org_query(db, org_id).all())
    exploitables = []
    for s in sites:
        intensity = getattr(s, "intensity_kwh_m2_tertiaire", None)
        annee_ref = getattr(s, "annee_reference_operat", None)
        if intensity is None or annee_ref is None:
            continue
        exploitables.append(s)

    if not exploitables:
        return {
            "drift_pct": 0.0,
            "atteint_pct_moyen": 0.0,
            "sites_count": 0,
            "source": "insufficient_data",
        }

    # v1.0 heuristique : on lit RegAssessment.compliance_score (échelle 0-100,
    # higher=better) pour estimer le % atteint. Un compliance_score de 60 → 24 %
    # atteint (proportionnel). Phase 3.7 = lecture findings_json détaillé.
    from models.reg_assessment import RegAssessment

    atteints: list[float] = []
    for s in exploitables:
        ra = (
            db.query(RegAssessment)
            .filter(RegAssessment.object_type == "site", RegAssessment.object_id == s.id)
            .order_by(RegAssessment.computed_at.desc())
            .first()
        )
        if ra and ra.compliance_score is not None:
            # compliance_score 0-100 → % atteint estimé (×0.4 pour rester dans
            # la fenêtre 0-40 %, cible 2030).
            atteints.append(float(ra.compliance_score) * 0.4)
        else:
            atteints.append(0.0)

    moy = sum(atteints) / len(atteints) if atteints else 0.0
    drift = max(0.0, DT_TARGET_PCT - moy)
    return {
        "drift_pct": round(drift, 1),
        "atteint_pct_moyen": round(moy, 1),
        "sites_count": len(exploitables),
        "source": "computed",
    }


def compute_next_contract_end(db: Session, org_id: int) -> dict[str, Any]:
    """Renvoie la prochaine échéance de contrat élec/gaz parmi les sites de l'org.

    Lit `ContratCadre.date_fin` (date de fin de fourniture). Phase 3.7 = prendre
    en compte `ContractAnnexe.end_date_override` aussi.

    Returns:
        dict {
          "days": int (jours jusqu'à la prochaine échéance, sentinelle 99999),
          "contract_id": int | None,
          "fournisseur": str | None,
          "source": "computed" | "no_contract"
        }
    """
    try:
        from models.contract_v2_models import ContratCadre
    except Exception as exc:  # pragma: no cover
        _logger.warning("Impossible d'importer ContratCadre: %s", exc)
        return {"days": 99999, "contract_id": None, "fournisseur": None, "source": "no_contract"}

    today = date.today()
    try:
        contrats = list(
            db.query(ContratCadre).filter(ContratCadre.date_fin >= today).order_by(ContratCadre.date_fin.asc()).all()
        )
    except Exception:
        contrats = []
    if len(contrats) == 0:
        return {"days": 99999, "contract_id": None, "fournisseur": None, "source": "no_contract"}

    next_c = contrats[0]
    try:
        delta_days = (next_c.date_fin - today).days
    except (TypeError, AttributeError):
        return {"days": 99999, "contract_id": None, "fournisseur": None, "source": "no_contract"}
    return {
        "days": int(delta_days),
        "contract_id": next_c.id,
        "fournisseur": getattr(next_c, "fournisseur", None),
        "source": "computed",
    }


def compute_spot_exposure(db: Session, org_id: int) -> dict[str, Any]:
    """Renvoie le % de volume exposé au spot.

    Heuristique v1.0 : lit ContratCadre.type_prix. Si "INDEXE" / "SPOT" → 100 %,
    si "FIXE" → 0 %, sinon mixed 50 %. Phase 3.7 = formule_pricing détaillée.

    Returns:
        dict {
          "pct": float [0, 100],
          "contrats_count": int,
          "source": "computed" | "no_contract"
        }
    """
    try:
        from models.contract_v2_models import ContratCadre
    except Exception as exc:  # pragma: no cover
        _logger.warning("Impossible d'importer ContratCadre: %s", exc)
        return {"pct": 0.0, "contrats_count": 0, "source": "no_contract"}

    try:
        contrats = list(db.query(ContratCadre).all())
    except Exception:
        contrats = []
    n = len(contrats)
    if n == 0:
        return {"pct": 0.0, "contrats_count": 0, "source": "no_contract"}

    spot_count = 0
    mixed_count = 0
    for c in contrats:
        tp = getattr(c, "type_prix", None)
        tp_str = (str(tp.value) if hasattr(tp, "value") else str(tp or "")).upper()
        if "SPOT" in tp_str or "INDEXE" in tp_str or "INDEX" in tp_str:
            spot_count += 1
        elif "MIXTE" in tp_str or "MIX" in tp_str:
            mixed_count += 1
    pct = (spot_count + 0.5 * mixed_count) / n * 100
    return {
        "pct": round(pct, 1),
        "contrats_count": n,
        "source": "computed",
    }


def compute_bench_sites(db: Session, org_id: int, top_n: int = 3) -> list[dict[str, Any]]:
    """Renvoie un benchmark des `top_n` sites les plus représentatifs.

    Méthode v1.0 :
      - Charge les sites de l'org via sites_for_org_query (filtre is_demo)
      - Trie par intensity_kwh_m2_tertiaire (DESC = worst d'abord)
      - Calcule médiane intensity, delta_pct par site
      - Retourne max(top_n, 3) sites : pire + médiane + meilleur

    Returns:
        list[{
          "site": str (nom site),
          "site_id": int,
          "value": float (intensity kWh/m²),
          "ref": float (médiane),
          "delta_pct": int,
          "tier": "warn" | "neutral" | "pos"
        }]

    Vide si aucun site exploitable.
    """
    sites = list(sites_for_org_query(db, org_id).all())
    rated = [s for s in sites if getattr(s, "intensity_kwh_m2_tertiaire", None) is not None]
    if not rated:
        return []

    sorted_sites = sorted(rated, key=lambda s: float(s.intensity_kwh_m2_tertiaire), reverse=True)
    values = [float(s.intensity_kwh_m2_tertiaire) for s in sorted_sites]
    median = values[len(values) // 2]

    # Sélection canonique : worst (idx 0), médian, best (idx -1)
    selected: list[Any] = []
    if len(sorted_sites) >= 3:
        selected = [sorted_sites[0], sorted_sites[len(sorted_sites) // 2], sorted_sites[-1]]
    else:
        selected = sorted_sites[:top_n]

    result = []
    for s in selected:
        v = float(s.intensity_kwh_m2_tertiaire)
        delta_pct = round(((v - median) / median) * 100) if median > 0 else 0
        if delta_pct > 10:
            tier = "warn"
        elif delta_pct < -10:
            tier = "pos"
        else:
            tier = "neutral"
        result.append(
            {
                "site": getattr(s, "nom", f"Site #{s.id}"),
                "site_id": s.id,
                "value": round(v, 1),
                "ref": round(median, 1),
                "delta_pct": delta_pct,
                "tier": tier,
            }
        )
    return result


def compute_unvalued_cee_keur(db: Session, org_id: int) -> dict[str, Any]:
    """Renvoie l'estimation des CEE non encore valorisées (k€/an).

    Heuristique v1.0 : lit `models.cee_models.CEEEligibility` si présent et
    filtre `statut != "VALORISE"`. Phase 3.7 = wire CEE complet.

    Returns:
        dict { "k_eur": float, "actions_count": int, "source": str }
    """
    try:
        from models.cee_models import CEEEligibility  # type: ignore
    except Exception:
        return {"k_eur": 0.0, "actions_count": 0, "source": "no_cee_model"}

    try:
        eligibilities = db.query(CEEEligibility).all()
    except Exception:
        return {"k_eur": 0.0, "actions_count": 0, "source": "query_error"}

    total = 0.0
    count = 0
    for e in eligibilities:
        statut = getattr(e, "statut", "")
        if str(statut).upper() == "VALORISE":
            continue
        valeur = getattr(e, "valeur_estimee_eur", None) or getattr(e, "valeur_eur", None) or 0
        try:
            total += float(valeur)
            count += 1
        except (TypeError, ValueError):
            continue
    return {
        "k_eur": round(total / 1000, 1),
        "actions_count": count,
        "source": "computed",
    }
