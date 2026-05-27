"""
PROMEOS — pilotage_summary_service (Usage Steering P0 truth-contract, 2026-05-27).

Service dédié au futur 4ᵉ onglet « Pilotage des usages » dans /usages.
Construit un payload structuré agrégé depuis :
  - consumption_diagnostic (5 détecteurs : hors_horaires, base_load, pointe,
    derive, data_gap) ;
  - usage_service (readiness, top UES, surplus €) ;
  - power_optimization (utilization, overflow) ;
  - cost_by_period (gisement HP→HC) ;

Contrat de sortie figé (brief P0 §C3) :
{
  "insights": [...],
  "opportunities": [...],
  "action_candidates": [...],
  "data_quality": {...},
  "metadata": {...},
}

Chaque `action_candidate` expose :
  - insight_type, site_id, usage_id (si dispo)
  - external_ref = "pilotage:{insight_type}:site:{id}"
  - source_url   = "/usages?tab=pilotage&site={id}"
  - label_fr     (libellé court)
  - recommended_action_fr (action FR)
  - impact_eur (estimé, peut être None)
  - confidence

DOCTRINE :
  §8.1 zéro logique métier FE — le FE rend ce payload sans recalcul.
  §6.2 hub unique — source_url pointe vers /usages?tab=pilotage (PAS de
  nouveau menu ni /usage-steering).
  Brief P0 « chaque chiffre doit avoir source, unité, période, formule,
  confiance ».
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from services.scope_utils import resolve_site_ids


# ─── Pattern external_ref ────────────────────────────────────────────────


def _external_ref(insight_type: str, site_id: int, suffix: Optional[str] = None) -> str:
    """Pattern stable cross-brique pour idempotence Centre d'Action V4.

    Brief P0 C3 : `pilotage:{insight_type}:site:{id}` (optionnel suffix
    pour distinguer occurrences temporelles, ex. pointe:date)."""
    base = f"pilotage:{insight_type}:site:{site_id}"
    return f"{base}:{suffix}" if suffix else base


def _source_url(site_id: int) -> str:
    """URL canonique vers le 4ᵉ tab (futur) — Centre d'Action V4 ouvre ici.

    Note : tant que le tab n'est pas livré, l'utilisateur arrive sur /usages
    avec query string ; le tab `pilotage` sera ajouté en P1 (brief P0 §C3
    contrat figé, pas d'écran fantôme créé en P0)."""
    return f"/usages?tab=pilotage&site={site_id}"


# ─── 1. Insights (raw signals depuis consumption_diagnostic) ─────────────


def _collect_insights(db: Session, site_ids: list[int]) -> list[dict]:
    """Charge les insights ouverts (toutes catégories) pour les sites du scope.

    Retourne un format normalisé pour le pilotage : type, site, impact €,
    confidence. Pas d'écriture, pas d'effet de bord (read-only P0).
    """
    if not site_ids:
        return []
    try:
        from models import ConsumptionInsight  # type: ignore
    except Exception:
        return []

    rows = (
        db.query(ConsumptionInsight)
        .filter(ConsumptionInsight.site_id.in_(site_ids))
        .filter(ConsumptionInsight.insight_status == "open")
        .order_by(ConsumptionInsight.created_at.desc())
        .limit(50)
        .all()
    )
    out: list[dict] = []
    for r in rows:
        # ConsumptionInsight expose `message` (pas `title`). On retombe sur
        # le wording par défaut FR si message vide.
        title = getattr(r, "message", None) or getattr(r, "title", None) or _default_title(r.type)
        out.append(
            {
                "id": r.id,
                "insight_type": r.type,
                "site_id": r.site_id,
                "severity": r.severity,
                "title": title,
                "estimated_loss_eur": float(r.estimated_loss_eur) if r.estimated_loss_eur is not None else None,
                "estimated_loss_kwh": float(r.estimated_loss_kwh) if r.estimated_loss_kwh is not None else None,
                "period_start": r.period_start.isoformat() if r.period_start else None,
                "period_end": r.period_end.isoformat() if r.period_end else None,
                "confidence": _confidence_for(r),
            }
        )
    return out


def _default_title(insight_type: str) -> str:
    return {
        "hors_horaires": "Consommation hors horaires d'occupation",
        "base_load": "Talon de nuit/week-end élevé",
        "pointe": "Pic de puissance atypique",
        "derive": "Dérive de consommation détectée",
        "data_gap": "Lacune de données",
    }.get(insight_type, "Signal de consommation")


def _confidence_for(insight) -> str:
    """Heuristique simple : data_gap → low ; sinon medium (severity-aware)."""
    if insight.type == "data_gap":
        return "low"
    sev = (insight.severity or "").lower()
    if sev in ("critical", "high"):
        return "high"
    if sev in ("medium",):
        return "medium"
    return "low"


# ─── 2. Opportunities (gisements € chiffrés depuis services existants) ───


def _collect_opportunities(db: Session, site_ids: list[int]) -> list[dict]:
    """Agrège les gisements € identifiés par les services existants :
       - shift HP→HC depuis cost_by_period (si gisement_eur > 0)
       - réduction PS depuis power_optimization (si net_savings_eur > 0)

    Read-only : ne déclenche aucun recalcul lourd, lit les snapshots."""
    out: list[dict] = []
    if not site_ids:
        return out

    # Opportunités HP→HC site par site (limit 5 pour éviter latence).
    try:
        from services.cost_by_period_service import compute_cost_by_period

        for sid in site_ids[:5]:
            try:
                cost = compute_cost_by_period(db, sid)
            except Exception:
                continue
            optim = (cost or {}).get("optimization") or {}
            gisement = optim.get("savings_eur")
            if gisement and gisement > 0:
                out.append(
                    {
                        "type": "shift_hp_hc",
                        "site_id": sid,
                        "label_fr": "Décalage charges HP → HC",
                        "estimated_savings_eur": round(float(gisement), 0),
                        "action_fr": optim.get("action") or "Décaler les usages flexibles vers heures creuses",
                        "confidence": "medium",
                    }
                )
    except Exception:
        pass

    # Opportunités optimisation PS (puissance souscrite).
    try:
        from services.power_optimization_service import optimize_subscribed_power

        for sid in site_ids[:5]:
            try:
                po = optimize_subscribed_power(db, sid)
            except Exception:
                continue
            opt = (po or {}).get("optimization") or {}
            net = opt.get("net_savings_eur")
            if net and net > 0:
                out.append(
                    {
                        "type": "reduce_subscribed_power",
                        "site_id": sid,
                        "label_fr": "Réduction de puissance souscrite",
                        "estimated_savings_eur": round(float(net), 0),
                        "action_fr": (
                            f"Passer PS à {opt.get('recommended_ps_kva')} kVA "
                            f"(stratégie : {opt.get('strategy') or 'GTB programmation'})"
                        ),
                        "confidence": "high",
                    }
                )
    except Exception:
        pass

    return out


# ─── 3. Action candidates (insights → ActionCenterItem-ready) ────────────


def _build_action_candidates(insights: list[dict]) -> list[dict]:
    """Convertit chaque insight ouvert en action candidate prête à être
    poussée vers Centre d'Action V4 (P1 endpoint sync à venir).

    Pattern external_ref documenté §C3 brief :
      pilotage:{insight_type}:site:{id}
    """
    candidates: list[dict] = []
    for ins in insights:
        site_id = ins["site_id"]
        itype = ins["insight_type"]
        suffix = None
        if itype == "pointe" and ins.get("period_start"):
            suffix = ins["period_start"][:10]  # date pour distinguer pics
        candidates.append(
            {
                "insight_type": itype,
                "site_id": site_id,
                "usage_id": None,  # P1 si disponible via insight.usage_id
                "external_ref": _external_ref(itype, site_id, suffix),
                "source_url": _source_url(site_id),
                "label_fr": ins["title"],
                "recommended_action_fr": _recommended_action(itype),
                "impact_eur": ins.get("estimated_loss_eur"),
                "severity": ins.get("severity"),
                "confidence": ins["confidence"],
            }
        )
    return candidates


def _recommended_action(insight_type: str) -> str:
    return {
        "hors_horaires": "Programmer la coupure CVC / GTC en dehors des horaires d'occupation",
        "base_load": "Auditer le talon nuit (éclairage, serveurs, veilles) et couper les usages inutiles",
        "pointe": "Délester ou décaler les charges responsables du pic vers les heures creuses",
        "derive": "Vérifier thermostat, équipements non arrêtés, programmation GTB",
        "data_gap": "Complétude données : vérifier connecteur compteur (PRM/PCE)",
    }.get(insight_type, "Examiner le signal et planifier une action ciblée")


# ─── 4. Data quality ────────────────────────────────────────────────────


def _compute_data_quality(insights: list[dict]) -> dict:
    """Score de qualité simple basé sur la proportion de data_gap."""
    if not insights:
        return {
            "score_pct": None,
            "data_gap_count": 0,
            "total_insights": 0,
            "confidence": "low",
        }
    total = len(insights)
    gaps = sum(1 for i in insights if i["insight_type"] == "data_gap")
    score = round(100.0 * (1 - gaps / total), 1) if total else None
    return {
        "score_pct": score,
        "data_gap_count": gaps,
        "total_insights": total,
        "confidence": "high" if gaps / max(total, 1) < 0.2 else "medium",
    }


# ─── Entrée publique ────────────────────────────────────────────────────


def compute_pilotage_summary(
    db: Session,
    org_id: int,
    *,
    entity_id: Optional[int] = None,
    portefeuille_id: Optional[int] = None,
    site_id: Optional[int] = None,
    archetype_code: Optional[str] = None,
) -> dict:
    """Payload Pilotage des usages — contrat figé brief P0 §C3.

    Returns:
        {
            "insights": [...],
            "opportunities": [...],
            "action_candidates": [...],
            "data_quality": {...},
            "metadata": {
                "computed_at": ISO,
                "scope": {...},
                "site_count": N,
            },
        }
    """
    site_ids = resolve_site_ids(
        db,
        org_id,
        entity_id=entity_id,
        portefeuille_id=portefeuille_id,
        site_id=site_id,
        archetype_code=archetype_code,
    )

    insights = _collect_insights(db, site_ids)
    opportunities = _collect_opportunities(db, site_ids)
    action_candidates = _build_action_candidates(insights)
    data_quality = _compute_data_quality(insights)

    return {
        "insights": insights,
        "opportunities": opportunities,
        "action_candidates": action_candidates,
        "data_quality": data_quality,
        "metadata": {
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "site_count": len(site_ids),
            "scope": {
                "org_id": org_id,
                "entity_id": entity_id,
                "portefeuille_id": portefeuille_id,
                "site_id": site_id,
                "archetype_code": archetype_code,
            },
            "truth_contract_note": (
                "Chaque insight expose insight_type/severity/period/confidence. "
                "Chaque opportunity expose estimated_savings_eur + action_fr + confidence. "
                "Chaque action_candidate expose external_ref idempotent pour ActionCenterV4."
            ),
        },
    }
