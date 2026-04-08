"""
PROMEOS — Service de reprogrammation HC Enedis.

Orchestre le traitement des fichiers PHOTO HC :
  1. Parse le CSV PHOTO (via photo_hc parser)
  2. Met à jour les DeliveryPoint (champs hc_reprog_*)
  3. Crée/met à jour les TOUSchedule pour les PRM reprogrammés
  4. Génère des alertes pour les changements détectés

Sources :
  - CRE délibération n°2025-78 (TURPE 7)
  - CRE délibération n°2026-33 (levée gel HC 11-14h hiver)
  - Enedis spécification PHOTO HC v2.1
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from data_ingestion.enedis.parsers.photo_hc import (
    ParsedPhotoFile,
    ParsedPhotoRow,
    PhotoType,
    parse_photo_hc,
)
from models.enums import HcReprogPhase, HcReprogStatus
from models.patrimoine import DeliveryPoint
from models.tou_schedule import TOUSchedule

logger = logging.getLogger(__name__)


# ─── Mapping codes HC → fenêtres horaires ──────────────────────────────────
# Catalogue Enedis des codes HC avec les fenêtres correspondantes.
# Source : grille Enedis codes plages HC (interne, reconstituée à partir
# des fichiers PHOTO réels et de la documentation Enedis SGE).
#
# Format : {"start": "HH:MM", "end": "HH:MM", "period": "HC|HCH|HCB"}
# Les fenêtres HC font toujours 8h/jour (contrainte CRE).

HC_CODE_WINDOWS: Dict[str, List[Dict[str, str]]] = {
    # Phase 1 — non saisonnalisé (8h HC nuit)
    "HC01": [{"start": "22:00", "end": "06:00", "period": "HC", "day_types": ["weekday", "weekend", "holiday"]}],
    "HC02": [{"start": "23:00", "end": "07:00", "period": "HC", "day_types": ["weekday", "weekend", "holiday"]}],
    "HC03": [{"start": "00:00", "end": "08:00", "period": "HC", "day_types": ["weekday", "weekend", "holiday"]}],
    "HC04": [{"start": "01:00", "end": "09:00", "period": "HC", "day_types": ["weekday", "weekend", "holiday"]}],
    "HC05": [{"start": "02:00", "end": "10:00", "period": "HC", "day_types": ["weekday", "weekend", "holiday"]}],
    # Phase 2 — saisonnalisé hiver (8h HC nuit)
    "HCH01": [{"start": "23:00", "end": "07:00", "period": "HCH", "day_types": ["weekday", "weekend", "holiday"]}],
    "HCH02": [{"start": "22:00", "end": "06:00", "period": "HCH", "day_types": ["weekday", "weekend", "holiday"]}],
    # Phase 2 — saisonnalisé été (5h nuit + 3h méridienne = 8h)
    "HCB01": [
        {"start": "01:00", "end": "06:00", "period": "HCB", "day_types": ["weekday", "weekend", "holiday"]},
        {"start": "12:00", "end": "15:00", "period": "HCB", "day_types": ["weekday", "weekend", "holiday"]},
    ],
    "HCB02": [
        {"start": "02:00", "end": "07:00", "period": "HCB", "day_types": ["weekday", "weekend", "holiday"]},
        {"start": "13:00", "end": "16:00", "period": "HCB", "day_types": ["weekday", "weekend", "holiday"]},
    ],
}


def _code_to_windows(code: Optional[str]) -> Optional[List[Dict]]:
    """Résout un code HC Enedis en fenêtres horaires."""
    if not code:
        return None
    return HC_CODE_WINDOWS.get(code.upper().strip())


# ─── Traitement fichier PHOTO ──────────────────────────────────────────────


def process_photo_file(
    db: Session,
    csv_content: str | bytes,
    filename: str = "",
) -> Dict[str, Any]:
    """Traite un fichier PHOTO HC complet.

    1. Parse le CSV
    2. Met à jour les DeliveryPoint existants
    3. Crée/met à jour les TOUSchedule
    4. Retourne un rapport de traitement

    Returns:
        {
            "photo_type": "M-6" | "M-2" | "CR-M",
            "total_rows": int,
            "prms_matched": int,
            "prms_not_found": int,
            "schedules_created": int,
            "schedules_updated": int,
            "alerts": [...],
            "is_phase2": bool,
        }
    """
    parsed = parse_photo_hc(csv_content, filename)

    prms_matched = 0
    prms_not_found = 0
    schedules_created = 0
    schedules_updated = 0
    alerts: List[Dict[str, Any]] = []

    # Batch-load all DeliveryPoints for PRMs in the file (avoid N+1)
    all_prms = parsed.prm_list
    dp_map: Dict[str, DeliveryPoint] = {}
    if all_prms:
        dps = db.query(DeliveryPoint).filter(DeliveryPoint.code.in_(all_prms)).all()
        dp_map = {dp.code: dp for dp in dps}

    # Batch-load active reprog schedules for matched sites
    matched_site_ids = {dp.site_id for dp in dp_map.values()}
    sched_by_site: Dict[int, TOUSchedule] = {}
    if matched_site_ids:
        active_scheds = (
            db.query(TOUSchedule)
            .filter(
                TOUSchedule.site_id.in_(matched_site_ids),
                TOUSchedule.source == "reprog_hc",
                TOUSchedule.is_active.is_(True),
            )
            .all()
        )
        sched_by_site = {s.site_id: s for s in active_scheds}

    for row in parsed.rows:
        dp = dp_map.get(row.prm)
        if not dp:
            prms_not_found += 1
            continue

        prms_matched += 1

        # Déterminer la phase
        phase = HcReprogPhase.PHASE_2 if row.is_seasonal else HcReprogPhase.PHASE_1

        # Mettre à jour le DeliveryPoint
        old_status = dp.hc_reprog_status
        _update_delivery_point(dp, row, parsed.photo_type, phase)

        # Créer/mettre à jour le TOUSchedule si on a les codes cibles
        sched_result = _upsert_tou_schedule(db, dp, row, parsed.photo_type, sched_by_site)
        if sched_result == "created":
            schedules_created += 1
        elif sched_result == "updated":
            schedules_updated += 1

        # Générer les alertes
        alert = _build_alert(dp, row, parsed.photo_type, old_status)
        if alert:
            alerts.append(alert)

    db.flush()

    return {
        "photo_type": parsed.photo_type.value,
        "total_rows": parsed.total_prms,
        "prms_matched": prms_matched,
        "prms_not_found": prms_not_found,
        "schedules_created": schedules_created,
        "schedules_updated": schedules_updated,
        "alerts": alerts,
        "is_phase2": parsed.is_phase2,
    }


def _update_delivery_point(
    dp: DeliveryPoint,
    row: ParsedPhotoRow,
    photo_type: PhotoType,
    phase: HcReprogPhase,
) -> None:
    """Met à jour les champs hc_reprog_* du DeliveryPoint."""
    dp.hc_reprog_phase = phase
    dp.hc_code_actuel = row.code_hc_actuel or dp.hc_code_actuel
    dp.hc_libelle_actuel = row.libelle_hc_actuel or dp.hc_libelle_actuel

    if photo_type == PhotoType.M6:
        dp.hc_reprog_status = HcReprogStatus.A_TRAITER
        dp.hc_reprog_date_prevue = _parse_date(row.date_prevue)
        dp.hc_code_futur = row.code_hc_cible
        dp.hc_libelle_futur = row.libelle_hc_cible

    elif photo_type == PhotoType.M2:
        dp.hc_reprog_status = HcReprogStatus.A_TRAITER
        dp.hc_reprog_date_prevue = _parse_date(row.date_prevue) or dp.hc_reprog_date_prevue
        dp.hc_code_futur = row.code_hc_cible or dp.hc_code_futur
        dp.hc_libelle_futur = row.libelle_hc_cible or dp.hc_libelle_futur

    elif photo_type == PhotoType.CRM:
        statut_map = {
            "TRAITE": HcReprogStatus.TRAITE,
            "ABANDON": HcReprogStatus.ABANDON,
            "EN_COURS": HcReprogStatus.EN_COURS,
        }
        dp.hc_reprog_status = statut_map.get((row.statut or "").upper(), HcReprogStatus.EN_COURS)
        dp.hc_reprog_date_effective = _parse_date(row.date_effective)

    # Phase 2: saisonnalisation
    if row.is_seasonal:
        dp.hc_saisonnalise = True
        dp.hc_code_futur_hiver = row.code_hc_cible_sh
        dp.hc_code_futur_ete = row.code_hc_cible_sb


def _upsert_tou_schedule(
    db: Session,
    dp: DeliveryPoint,
    row: ParsedPhotoRow,
    photo_type: PhotoType,
    sched_by_site: Optional[Dict[int, TOUSchedule]] = None,
) -> Optional[str]:
    """Crée ou met à jour le TOUSchedule du PRM.

    Args:
        sched_by_site: Pre-fetched active reprog schedules keyed by site_id
                       (avoids N+1 queries).

    Returns: "created", "updated", or None
    """
    # Résoudre les fenêtres HC cibles
    if row.is_seasonal:
        windows_hiver = _code_to_windows(row.code_hc_cible_sh)
        windows_ete = _code_to_windows(row.code_hc_cible_sb)
        if not windows_hiver and not windows_ete:
            return None
    else:
        windows = _code_to_windows(row.code_hc_cible)
        if not windows:
            return None
        windows_hiver = windows
        windows_ete = None

    # Déterminer la date d'effet
    effective_date = _parse_date(row.date_effective) or _parse_date(row.date_prevue)
    if not effective_date:
        effective_date = date.today()

    # Chercher un TOUSchedule existant (pre-fetched or query fallback)
    existing = (sched_by_site or {}).get(dp.site_id)
    if existing is None and sched_by_site is None:
        existing = (
            db.query(TOUSchedule)
            .filter(
                TOUSchedule.site_id == dp.site_id,
                TOUSchedule.source == "reprog_hc",
                TOUSchedule.is_active.is_(True),
            )
            .first()
        )

    if existing:
        # Si CR-M TRAITE : mettre à jour les fenêtres et la date effective
        if photo_type == PhotoType.CRM and (row.statut or "").upper() == "TRAITE":
            existing.windows_json = json.dumps(windows_hiver, ensure_ascii=False)
            existing.windows_ete_json = json.dumps(windows_ete, ensure_ascii=False) if windows_ete else None
            existing.is_seasonal = row.is_seasonal
            existing.effective_from = effective_date
            existing.source_ref = f"CR-M {row.prm} {effective_date}"
            dp.tou_schedule_id = existing.id
            return "updated"
        # M-6 / M-2 : on ne change pas un schedule actif, juste le DP
        return None

    # Créer un nouveau TOUSchedule
    schedule = TOUSchedule(
        site_id=dp.site_id,
        name=f"Reprog HC {'Phase 2' if row.is_seasonal else 'Phase 1'} — PRM {row.prm[-4:]}",
        effective_from=effective_date,
        effective_to=None,
        is_active=photo_type == PhotoType.CRM and (row.statut or "").upper() == "TRAITE",
        is_seasonal=row.is_seasonal,
        windows_json=json.dumps(windows_hiver, ensure_ascii=False),
        windows_ete_json=json.dumps(windows_ete, ensure_ascii=False) if windows_ete else None,
        source="reprog_hc",
        source_ref=f"{photo_type.value} {row.prm} {effective_date}",
    )
    db.add(schedule)
    db.flush()  # Get ID
    dp.tou_schedule_id = schedule.id
    return "created"


def _build_alert(
    dp: DeliveryPoint,
    row: ParsedPhotoRow,
    photo_type: PhotoType,
    old_status: Optional[HcReprogStatus],
) -> Optional[Dict[str, Any]]:
    """Construit une alerte de reprogrammation HC si pertinent."""
    # Alerte sur CR-M avec changement de statut
    if photo_type == PhotoType.CRM:
        new_status = (row.statut or "").upper()
        if new_status == "TRAITE":
            return {
                "type": "hc_reprog_completed",
                "prm": row.prm,
                "site_id": dp.site_id,
                "message": f"PRM {row.prm} : reprogrammation HC terminée. "
                f"Nouvelles plages effectives depuis le {row.date_effective}.",
                "severity": "info",
                "date_effective": row.date_effective,
                "is_seasonal": row.is_seasonal,
            }
        elif new_status == "ABANDON":
            return {
                "type": "hc_reprog_failed",
                "prm": row.prm,
                "site_id": dp.site_id,
                "message": f"PRM {row.prm} : reprogrammation HC abandonnée après 30 jours.",
                "severity": "warning",
            }

    # Alerte sur M-6 : première notification
    if photo_type == PhotoType.M6 and old_status is None:
        return {
            "type": "hc_reprog_planned",
            "prm": row.prm,
            "site_id": dp.site_id,
            "message": f"PRM {row.prm} : reprogrammation HC prévue le {row.date_prevue}. "
            f"Plages actuelles : {row.code_hc_actuel} → cible : {row.code_hc_cible or 'saisonnalisé'}.",
            "severity": "info",
            "date_prevue": row.date_prevue,
        }

    return None


def emit_reprog_alerts(
    db: Session,
    org_id: int,
    alerts: List[Dict[str, Any]],
) -> int:
    """Émet les alertes HC dans le système de notification PROMEOS.

    Returns: nombre d'alertes créées.
    """
    from models.notification import NotificationEvent
    from models.enums import NotificationStatus

    created = 0
    for alert in alerts:
        existing = (
            db.query(NotificationEvent)
            .filter(
                NotificationEvent.org_id == org_id,
                NotificationEvent.source_type == "hc_reprog",
                NotificationEvent.source_key == f"reprog_{alert['prm']}",
            )
            .first()
        )
        if existing:
            existing.message = alert["message"]
            existing.severity = alert["severity"]
            continue

        event = NotificationEvent(
            org_id=org_id,
            site_id=alert.get("site_id"),
            source_type="hc_reprog",
            source_id=alert.get("prm"),
            source_key=f"reprog_{alert['prm']}",
            severity=alert["severity"],
            title=f"Reprogrammation HC — {alert['type'].replace('_', ' ').title()}",
            message=alert["message"],
            status=NotificationStatus.NEW,
        )
        db.add(event)
        created += 1

    return created


def _parse_date(s: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD ou DD/MM/YYYY en date."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
