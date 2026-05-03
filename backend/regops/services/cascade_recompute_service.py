"""cascade_recompute_service — Orchestrateur cascade Sprint C-1 Phase 6.

Sprint C-1 Phase 6 — comble GAP audit Phase B R6 (matrice v1 §8.4).

Détecte automatiquement les recalculs cascadants suite à modification d'un champ
amont (Site / Batiment) et les applique en chaîne :
  - Lookup zone OPERAT (via OperatValeursAbsoluesService — Phase 4)
  - Lookup palier altitude (via OperatValeursAbsoluesService)
  - Recalcul Cabs 2030 + persistance Site.cabs_kwh_m2_an (Option A — D-Phase5-DtBacsAssujetti-Volatile-001)
  - Recalcul compliance score V2 + persistance Site.compliance_score_* (via sync_site_unified_score Phase 5)

Architecture mince : délègue aux services existants, ne duplique aucune logique.

Scope MVP Sprint C-1 = 7 champs essentiels (Site x6 + Batiment x1) :
  - Site.code_postal, Site.altitude_m, Site.tertiaire_area_m2,
    Site.parking_area_m2, Site.roof_area_m2, Site.operat_sous_categorie_id
  - Batiment.cvc_power_kw

5 cascades reportées (cf. tracker dette technique D-Phase6-Cascade-*) :
  - EJ.consommation_3y → audit_sme + multi-sites compliance (Sprint C-2)
  - Org.consentement_dataconnect/grdf → DPs (Sprint C-3)
  - DP.code_fta → profil + Bill Intelligence (Sprint C-3)
  - Contract.date_fin_validite → alerte 90j (Sprint C-2/C-5)

Endpoint preview : GET /api/v1/sites/{id}/cascade-impact (dry-run, org-scopé).
Wiring PATCH /api/sites/{id} → cascade_recompute_on_change(persist=True) = Sprint C-2.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session


_logger = logging.getLogger(__name__)


# ─── Dataclasses résultat ────────────────────────────────────────────────────


@dataclass
class CascadeAction:
    """Action de recompute déclenchée par modification d'un champ amont."""

    output_field: str
    new_value: Any = None
    error: Optional[str] = None


@dataclass
class CascadeResult:
    """Résultat de cascade pour un champ modifié."""

    entity_type: str
    entity_id: Optional[int]
    field_modified: str
    old_value: Any
    new_value: Any
    actions: list[CascadeAction] = field(default_factory=list)
    persisted: bool = False
    computed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "field_modified": self.field_modified,
            "old_value": _serialize_value(self.old_value),
            "new_value": _serialize_value(self.new_value),
            "actions": [
                {
                    "output_field": a.output_field,
                    "new_value": _serialize_value(a.new_value),
                    "error": a.error,
                }
                for a in self.actions
            ],
            "persisted": self.persisted,
            "computed_at": self.computed_at,
            "errors_count": sum(1 for a in self.actions if a.error),
            "successes_count": sum(1 for a in self.actions if not a.error),
        }


def _serialize_value(v: Any) -> Any:
    """Sérialisation JSON-safe pour API/logs."""
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if v is None or isinstance(v, (str, int, float, bool, list, dict)):
        return v
    return str(v)


# ─── Helpers (réutilisent services Phase 4 + Phase 5) ───────────────────────


def _resolve_zone(site) -> Optional[str]:
    """Résolution code_postal → zone OPERAT (via Phase 4)."""
    if not site.code_postal:
        return None
    try:
        from regops.services.operat_cabs_service import OperatValeursAbsoluesService

        return OperatValeursAbsoluesService.resolve_zone(site.code_postal)
    except Exception as e:
        _logger.warning("resolve_zone failed for %s: %s", site.code_postal, e)
        return None


def _resolve_palier(site) -> Optional[str]:
    """Résolution altitude_m → palier (via Phase 4)."""
    if site.altitude_m is None:
        return None
    try:
        from regops.services.operat_cabs_service import OperatValeursAbsoluesService

        return OperatValeursAbsoluesService.resolve_palier_altitude(site.altitude_m)
    except Exception as e:
        _logger.warning("resolve_palier failed for altitude=%s: %s", site.altitude_m, e)
        return None


def _recompute_cabs(site, db: Session) -> Optional[float]:
    """Recalcule Cabs 2030 pour le site (via Phase 4).

    Retourne None si données incomplètes (code_postal, altitude_m,
    operat_sous_categorie_id ou bâtiments manquants).
    """
    if not site.code_postal or site.altitude_m is None:
        return None
    if not site.operat_sous_categorie_id:
        return None

    # MVP : utiliser sous-catégorie + surface du site (pas multi-bâtiments)
    surface = site.tertiaire_area_m2 or site.surface_m2 or 0
    if surface <= 0:
        return None

    try:
        from regops.services.operat_cabs_service import (
            OperatNonAssujettiError,
            OperatSousCategorieIntrouvableError,
            OperatValeursAbsoluesService,
        )

        result = OperatValeursAbsoluesService().compute_cabs_2030(
            code_postal=site.code_postal,
            altitude_m=site.altitude_m,
            sous_categories_declared=[{"title": site.operat_sous_categorie_id, "surface_m2": surface}],
        )
        return result.get("cabs_2030_kwh_m2_an")
    except (OperatNonAssujettiError, OperatSousCategorieIntrouvableError) as e:
        _logger.info("Cabs non calculable pour site %s: %s", site.id, e)
        return None
    except Exception as e:
        _logger.warning("compute_cabs failed for site %s: %s", site.id, e)
        return None


def _recompute_compliance(site, db: Session) -> Optional[float]:
    """Recalcule + persiste compliance score (via sync_site_unified_score Phase 5).

    Note : utilise `sync_site_unified_score` (pas `compliance_coordinator.recompute_site_full`)
    pour cascade légère. Le coordinator full est plus coûteux (legacy snapshot +
    RegAssessment + score) — pertinent pour PATCH complet, surdimensionné pour cascade
    incrémentale.
    """
    try:
        from services.compliance_score_service import sync_site_unified_score

        result = sync_site_unified_score(db, site.id)
        return result.score  # peut être None pour V2 NON_APPLICABLE
    except Exception as e:
        _logger.warning("recompute_compliance failed for site %s: %s", site.id, e)
        return None


def _resolve_aper_assujetti(site) -> bool:
    """APER assujetti si parking ≥ 1500 m² (Loi 2023-175)."""
    return (site.parking_area_m2 or 0) >= 1500


def _resolve_aper_taille(site) -> Optional[str]:
    """SMALL (1500-10000 m²) ou LARGE (> 10000 m²)."""
    if not site.parking_area_m2 or site.parking_area_m2 < 1500:
        return None
    return "LARGE" if site.parking_area_m2 > 10000 else "SMALL"


def _resolve_aper_deadline(site) -> Optional[date]:
    """Échéance APER : 01/07/2026 (LARGE) ou 01/07/2028 (SMALL)."""
    if not site.parking_area_m2 or site.parking_area_m2 < 1500:
        return None
    if site.parking_area_m2 > 10000:
        return date(2026, 7, 1)
    return date(2028, 7, 1)


# ─── CASCADE_MAP MVP Sprint C-1 (7 champs) ──────────────────────────────────
#
# Chaque entrée est une liste de fonctions cascade qui retournent (output_field, value).
# L'ordre est important : les calculs amont (zone/palier) sont d'abord persistés,
# puis le compliance score (qui peut dépendre de leur valeur).


CASCADE_MAP_MVP_SPRINT_C1: dict[str, list[Callable]] = {
    "Site.code_postal": [
        lambda s, db: ("operat_zone_climatique", _resolve_zone(s)),
        lambda s, db: ("operat_palier_altitude", _resolve_palier(s)),
        lambda s, db: ("cabs_kwh_m2_an", _recompute_cabs(s, db)),
        lambda s, db: ("compliance_score", _recompute_compliance(s, db)),
    ],
    "Site.altitude_m": [
        lambda s, db: ("operat_palier_altitude", _resolve_palier(s)),
        lambda s, db: ("cabs_kwh_m2_an", _recompute_cabs(s, db)),
        lambda s, db: ("compliance_score", _recompute_compliance(s, db)),
    ],
    "Site.tertiaire_area_m2": [
        lambda s, db: ("compliance_score", _recompute_compliance(s, db)),
    ],
    "Site.parking_area_m2": [
        lambda s, db: ("aper_assujetti", _resolve_aper_assujetti(s)),
        lambda s, db: ("aper_categorie_taille", _resolve_aper_taille(s)),
        lambda s, db: ("aper_deadline", _resolve_aper_deadline(s)),
        lambda s, db: ("compliance_score", _recompute_compliance(s, db)),
    ],
    "Site.roof_area_m2": [
        # SOLAR_TOITURE assujettissement → recalc compliance
        lambda s, db: ("compliance_score", _recompute_compliance(s, db)),
    ],
    "Site.operat_sous_categorie_id": [
        lambda s, db: ("cabs_kwh_m2_an", _recompute_cabs(s, db)),
        lambda s, db: ("compliance_score", _recompute_compliance(s, db)),
    ],
    "Batiment.cvc_power_kw": [
        # Bâtiment → recalcule compliance du SITE parent (BACS = Σ cvc bâtiments)
        lambda b, db: ("compliance_score", _recompute_compliance(b.site, db)),
    ],
}


# Champs persistés en colonne directe sur Site (les autres = side-effects via services)
_PERSISTABLE_OUTPUT_FIELDS = {
    "operat_zone_climatique",
    "operat_palier_altitude",
    "cabs_kwh_m2_an",
    "aper_assujetti",
    "aper_categorie_taille",
    "aper_deadline",
}


# ─── API publique ────────────────────────────────────────────────────────────


def cascade_recompute_on_change(
    db: Session,
    entity: Any,
    field_modified: str,
    old_value: Any = None,
    new_value: Any = None,
    *,
    persist: bool = True,
    user_id: Optional[int] = None,
    org_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> CascadeResult:
    """Détection automatique des recalculs cascadants après modification.

    Args:
        db: session SQLAlchemy
        entity: instance modifiée (Site ou Batiment)
        field_modified: ex "Site.code_postal" (format "ClassName.attr")
        old_value, new_value: valeurs avant/après pour audit
        persist: si True, applique les recalculs en DB (commit). Sinon dry-run.
        user_id, org_id, correlation_id, ip_address, user_agent: contexte pour
            audit trail (Sprint C-2 Phase 1.3 — propagés depuis routes/services
            callers vers audit_log_service.log_cascade()).

    Returns:
        CascadeResult avec liste des actions + erreurs éventuelles.

    Résilience : si une cascade plante, les autres continuent. Les erreurs sont
    collectées dans CascadeAction.error. Un échec d'audit log NE BLOQUE PAS la
    cascade (try/except autour de log_cascade).
    """
    cascade_callables = CASCADE_MAP_MVP_SPRINT_C1.get(field_modified, [])
    actions: list[CascadeAction] = []

    for cascade_fn in cascade_callables:
        try:
            output_field, computed_value = cascade_fn(entity, db)
            actions.append(CascadeAction(output_field=output_field, new_value=computed_value))

            # Persister sur l'entité si applicable + persist=True
            # compliance_score n'est PAS dans _PERSISTABLE_OUTPUT_FIELDS car déjà
            # persisté par sync_site_unified_score (Phase 5) en interne.
            if (
                persist
                and computed_value is not None
                and output_field in _PERSISTABLE_OUTPUT_FIELDS
                and hasattr(entity, output_field)
            ):
                setattr(entity, output_field, computed_value)
        except Exception as e:
            actions.append(CascadeAction(output_field="<unknown>", new_value=None, error=str(e)))
            _logger.error(
                "Cascade error on %s → action raised: %s",
                field_modified,
                e,
                exc_info=True,
            )

    if persist:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            actions.append(
                CascadeAction(
                    output_field="<commit>",
                    new_value=None,
                    error=f"DB commit failed: {e}",
                )
            )

    result = CascadeResult(
        entity_type=type(entity).__name__,
        entity_id=getattr(entity, "id", None),
        field_modified=field_modified,
        old_value=old_value,
        new_value=new_value,
        actions=actions,
        persisted=persist,
        computed_at=datetime.utcnow().isoformat(),
    )

    # Audit trail Sprint C-2 Phase 1.3 — wiring vers audit_log_service.log_cascade()
    # ⚠️ Résilience : un échec d'audit log NE BLOQUE PAS la cascade. La fonction
    # de cascade reste fonctionnelle même si la persistance audit échoue (ex:
    # AuditLog table absente, FK invalide, contrainte DB). L'erreur est loggée
    # en warning + fallback sur logger.info structuré (compat backward Phase 6 MVP).
    try:
        from services.audit_log_service import log_cascade

        log_cascade(
            db,
            user_id=user_id,
            org_id=org_id,
            cascade_result=result,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if persist:
            # Commit le log si on est en mode persist (sinon laissé au caller / SAVEPOINT)
            try:
                db.commit()
            except Exception:
                db.rollback()
    except Exception as audit_err:
        # Fallback log structuré stdout — cascade reste fonctionnelle
        _logger.warning(
            "audit_log_service.log_cascade failed for %s: %s — fallback stdout log",
            field_modified,
            audit_err,
            exc_info=True,
        )
        _logger.info(
            "CASCADE_AUDIT_FALLBACK: %s",
            result.to_dict(),
            extra={"cascade_audit": True, "fallback": True},
        )

    return result


def cascade_impact_preview(
    db: Session,
    entity: Any,
    field_modified: str,
    new_value: Any,
    *,
    user_id: Optional[int] = None,
    org_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> CascadeResult:
    """Preview cascade SANS modifier la donnée (dry-run strict via SAVEPOINT).

    Implémentation : encapsule la simulation dans un SAVEPOINT SQLAlchemy
    (`db.begin_nested()`). Toute modification ORM (y compris `db.flush()`
    déclenché par sub-services comme `sync_site_unified_score`) est rollback à
    la fin → DB et session reviennent à l'état initial.

    Sprint C-2 Phase 1.3 : kwargs audit propagés à `cascade_recompute_on_change`.
    Le SAVEPOINT englobe AuditLog créé par `log_cascade` → preview ne persiste
    AUCUN audit log (cohérent avec dry-run sémantique).

    Cela couvre les cas où des sous-services (compliance_coordinator) appellent
    `db.flush()` pendant la cascade — sans rollback explicite, leurs UPDATEs
    pending pollueraient la session courante.
    """
    field_attr = field_modified.split(".")[-1]
    old_value = getattr(entity, field_attr, None)

    savepoint = db.begin_nested()
    try:
        setattr(entity, field_attr, new_value)
        result = cascade_recompute_on_change(
            db,
            entity,
            field_modified,
            old_value,
            new_value,
            persist=False,
            user_id=user_id,
            org_id=org_id,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return result
    finally:
        # Rollback du SAVEPOINT → toute modification ORM/DB pending est annulée
        try:
            savepoint.rollback()
        except Exception:
            pass
        # Refresh entity depuis DB (post-rollback) pour s'assurer que les
        # attributs ORM reflètent la valeur originale persistée
        try:
            db.expire(entity)
        except Exception:
            pass
