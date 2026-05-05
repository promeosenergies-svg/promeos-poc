"""cascade_recompute_service — Orchestrateur cascade Sprint C-1 Phase 6.

Sprint C-1 Phase 6 — comble GAP audit Phase B R6 (matrice v1 §8.4).

Détecte automatiquement les recalculs cascadants suite à modification d'un champ
amont (Site / Batiment) et les applique en chaîne :
  - Lookup zone OPERAT (via OperatValeursAbsoluesService — Phase 4)
  - Lookup palier altitude (via OperatValeursAbsoluesService)
  - Recalcul Cabs 2030 + persistance Site.cabs_kwh_m2_an (Option A — D-Phase5-DtBacsAssujetti-Volatile-001)
  - Recalcul compliance score V2 + persistance Site.compliance_score_* (via sync_site_unified_score Phase 5)

Architecture mince : délègue aux services existants, ne duplique aucune logique.

Scope MVP Sprint C-1 = 7 champs initiaux (Site x6 + Batiment x1) ; étendu en
Sprint C-2 Phase 4.2 (+2 Site) puis Phase 5.2 (+1 AuditEnergetique) puis Phase 5.3
(+1 EnergyContract) à 12 champs :
  - Site.code_postal, Site.altitude_m, Site.tertiaire_area_m2,
    Site.parking_area_m2, Site.roof_area_m2, Site.operat_sous_categorie_id,
    Site.surface_m2 (Phase 4.2), Site.annual_kwh_total (Phase 4.2)
  - Batiment.cvc_power_kw
  - AuditEnergetique.conso_annuelle_moy_gwh (Phase 5.2 — pivot org-scoped)
  - EnergyContract.end_date (Phase 5.3 — alerte renouvellement 90j MVP)

2 cascades restantes reportées (cf. tracker dette D-Phase6-Cascade-*) :
  - Org.consentement_dataconnect/grdf → DPs (Sprint C-3)
  - DP.code_fta → profil + Bill Intelligence (Sprint C-3)

Endpoint preview : GET /api/v1/sites/{id}/cascade-impact (dry-run, org-scopé).
Wiring PATCH /api/sites/{id} → cascade_recompute_on_change(persist=True) = Sprint C-2 Phase 3.
Sprint C-2 Phase 4.2 — intensity_kwh_m2_total + intensity_kwh_m2_tertiaire
persistées via cascade (anti-cycle : intensity n'est PAS source de cascade compliance).
Sprint C-2 Phase 5.2 — cascade AuditEnergetique.conso_annuelle_moy_gwh →
obligation (loi 30/04/2025 : 2.75 / 23.6 GWh) + recompute_organisation tous sites.
Sprint C-2 Phase 5.3 — cascade EnergyContract.end_date → alerte 90j MVP
(log + flag idempotence, modèle Alert dédié reporté Sprint C-5).
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
    """Échéance APER (lue depuis SoT YAML `sources_reglementaires.yaml`).

    Sprint C-3 Phase 3.7d audit follow-up — élimination duplication locale
    `date(2026, 7, 1)` / `date(2028, 7, 1)`. SoT canonique :
      - APER_DEADLINE_LARGE = "2026-07-01" (parkings > 10000 m²)
      - APER_DEADLINE_SMALL = "2028-07-01" (parkings 1500-10000 m²)

    Anti-régression : si la loi APER 2023-175 est mise à jour, modifier
    uniquement le YAML — la cascade et le wrapping FE TraceTooltip
    bénéficient automatiquement.
    """
    from config.regulatory_sources_loader import get_term_value

    if not site.parking_area_m2 or site.parking_area_m2 < 1500:
        return None

    deadline_key = "APER_DEADLINE_LARGE" if site.parking_area_m2 > 10000 else "APER_DEADLINE_SMALL"
    iso_str = get_term_value(deadline_key)
    return date.fromisoformat(iso_str) if isinstance(iso_str, str) else iso_str


def _recompute_intensity_total(site) -> Optional[float]:
    """Recalcule intensity_kwh_m2_total (Sprint C-2 Phase 4.2 — matrice §4.4.F #56).

    annual_kwh_total / surface_m2 si données complètes, sinon None.
    Anti-cycle : ne déclenche PAS de cascade vers compliance_score.
    """
    try:
        from services.site_intensity_service import _safe_intensity

        return _safe_intensity(
            getattr(site, "annual_kwh_total", None),
            getattr(site, "surface_m2", None),
        )
    except Exception as e:
        _logger.warning("recompute_intensity_total failed for site %s: %s", getattr(site, "id", None), e)
        return None


def _recompute_intensity_tertiaire(site) -> Optional[float]:
    """Recalcule intensity_kwh_m2_tertiaire (Sprint C-2 Phase 4.2 — doctrine OPERAT/DT).

    annual_kwh_total / tertiaire_area_m2 si données complètes, sinon None.
    Anti-cycle : ne déclenche PAS de cascade vers compliance_score.
    """
    try:
        from services.site_intensity_service import _safe_intensity

        return _safe_intensity(
            getattr(site, "annual_kwh_total", None),
            getattr(site, "tertiaire_area_m2", None),
        )
    except Exception as e:
        _logger.warning("recompute_intensity_tertiaire failed for site %s: %s", getattr(site, "id", None), e)
        return None


# ─── Helpers Phase 5.2 Sprint C-2 — cascade AuditEnergetique → obligation + multi-sites ─────
#
# Source légale : loi n°2025-391 du 30/04/2025 (transposition directive UE 2023/1791),
# Code de l'énergie art. L.233-1 et suivants. Seuils (cf. AuditEnergetique docstring) :
#   ≥ 23.6 GWh/an → SME ISO 50001
#   ≥ 2.75 GWh/an → Audit énergétique 4 ans
#   <  2.75 GWh   → AUCUNE obligation
# Pivot Phase 5.1 (2026-05-04) : org-scoped (FK organisation_id) car audit_sme est
# défini au niveau Organisation, pas EntiteJuridique. La dette originale
# D-Phase6-Cascade-EJ-Sites-001 a été clôturée sous D-Phase6-Cascade-AuditSme-Org-Sites-001.


def _recompute_audit_sme_obligation(audit_sme) -> Optional[str]:
    """Recalcule AuditEnergetique.obligation depuis conso_annuelle_moy_gwh.

    Seuils loi 30/04/2025 lus depuis SoT YAML `sources_reglementaires.yaml`
    (Sprint C-3 Phase 3.7d audit follow-up — élimination de la duplication
    locale qui violait la doctrine "1 SoT par concept" :
      - AUDIT_SME_THRESHOLD_GWH_ISO50001 = 23.6 → "SME_ISO50001"
      - AUDIT_SME_THRESHOLD_GWH_PERIODIC = 2.75 → "AUDIT_4ANS"
      - <  2.75 GWh                              → "AUCUNE"

    Si conso_annuelle_moy_gwh est None → None retourné, obligation NON modifiée
    (pas de transition forcée vers une valeur arbitraire).

    Anti-régression : SG_REG_CONST_03 vérifie cohérence YAML ↔ runtime Python.
    """
    from config.regulatory_sources_loader import get_audit_sme_threshold

    conso_gwh = getattr(audit_sme, "conso_annuelle_moy_gwh", None)
    if conso_gwh is None:
        return None

    seuil_iso50001 = get_audit_sme_threshold("iso50001")
    seuil_audit_4ans = get_audit_sme_threshold("audit_4ans")

    if conso_gwh >= seuil_iso50001:
        new_obligation = "SME_ISO50001"
    elif conso_gwh >= seuil_audit_4ans:
        new_obligation = "AUDIT_4ANS"
    else:
        new_obligation = "AUCUNE"

    audit_sme.obligation = new_obligation
    return new_obligation


def _recompute_organisation_via_coordinator(audit_sme, db: Session) -> Optional[str]:
    """Délègue à compliance_coordinator.recompute_organisation pour bulk recompute.

    audit_sme.organisation_id → tous sites de l'organisation parente.
    Anti-cycle : recompute_organisation calcule compliance_score (lecture intensity / DT /
    BACS / APER) et ne modifie JAMAIS audit_sme.conso_annuelle_moy_gwh.

    Résilience : exception isolée (org_id absent, sites manquants, evaluate_site KO)
    n'arrête pas la cascade — None retourné, action loguée.
    """
    organisation_id = getattr(audit_sme, "organisation_id", None)
    if organisation_id is None:
        return None

    try:
        from services.compliance_coordinator import recompute_organisation

        result = recompute_organisation(db, organisation_id)
        sites_count = result.get("sites_recomputed", 0) if isinstance(result, dict) else 0
        return f"recompute_organisation done (org_id={organisation_id}, sites={sites_count})"
    except Exception as e:
        _logger.warning(
            "recompute_organisation failed for organisation %s: %s",
            organisation_id,
            e,
        )
        return None


# ─── Helpers Phase 5.3 Sprint C-2 — cascade EnergyContract.end_date → alerte 90j ────
#
# Cas B MVP : modèle Alert générique absent (cf. Phase 5.1 audit). Implémentation
# par log structuré stdout + flag idempotence sur le contrat. Report version
# Premium (Alert UI + email notif) Sprint C-5 (Onboarding 3 parcours).
# Source dette : D-Phase6-Cascade-Contract-Renewal-001.

_RENEWAL_ALERT_WINDOW_DAYS = 90
_RENEWAL_ALERT_REPLAY_COOLDOWN_DAYS = 30


def _trigger_renewal_alert(contract, db: Session) -> Optional[str]:
    """Cascade EnergyContract.end_date → log alerte 90j (MVP Sprint C-2 Phase 5.3).

    Skip cases :
    - end_date is None
    - days_to_expiry > 90 (hors fenêtre)
    - days_to_expiry < 0 (déjà expiré)
    - alerte_renouvellement_logged_at < 30j (idempotence anti-spam)

    Sinon : set `contract.alerte_renouvellement_logged_at = now` + log structuré
    `RENEWAL_ALERT_90D` avec contract_id + days_to_expiry + supplier.
    """
    end_date = getattr(contract, "end_date", None)
    if end_date is None:
        return None

    today = date.today()
    days_to_expiry = (end_date - today).days

    if days_to_expiry > _RENEWAL_ALERT_WINDOW_DAYS or days_to_expiry < 0:
        return None

    last_logged = getattr(contract, "alerte_renouvellement_logged_at", None)
    if last_logged:
        last_log_age = (datetime.utcnow() - last_logged).days
        if last_log_age < _RENEWAL_ALERT_REPLAY_COOLDOWN_DAYS:
            return f"alert_already_logged ({last_log_age}d ago)"

    contract.alerte_renouvellement_logged_at = datetime.utcnow()

    _logger.info(
        "RENEWAL_ALERT_90D",
        extra={
            "contract_id": getattr(contract, "id", None),
            "site_id": getattr(contract, "site_id", None),
            "days_to_expiry": days_to_expiry,
            "end_date": end_date.isoformat(),
            "supplier": getattr(contract, "supplier_name", None),
        },
    )
    return f"renewal_alert_logged ({days_to_expiry}d to expiry)"


def _reset_renewal_alert_flag(contract, db: Session) -> str:
    """Reset alerte_renouvellement_logged_at à None — sub-cascade quand end_date modifié.

    Permet la ré-évaluation de la fenêtre 90j à la nouvelle date sans rester
    bloqué par un log précédent. Doit s'exécuter AVANT _trigger_renewal_alert
    dans la chaîne de cascade (sinon l'idempotence skip le re-log immédiat).
    """
    contract.alerte_renouvellement_logged_at = None
    return "flag_reset"


# ─── Helpers Phase 3.6 Sprint C-3 — cascade DeliveryPoint.grd_code → ELD ref + bill_recheck ─
#
# Pivot Phase 3.6 audit (2026-05-04) : la dette originale `D-Phase6-Cascade-DeliveryPoint-Fta-001`
# ciblait `DeliveryPoint.code_fta` qui n'existe pas (le FTA est sur `PowerContract.fta_code`).
# Pivot vers `DeliveryPoint.grd_code` (champ existant, ENEDIS/GRDF/ELD_*/RTE) qui est plus
# pertinent pour la cascade ELD ref (lookup eld_gaz_referentiel.yaml). La cascade
# `PowerContract.fta_code` est tracée comme nouvelle dette `D-Phase3-6-Cascade-PowerContract-FTA-001`
# (Sprint C-4).


def _recompute_eld_metadata_from_grd_code(delivery_point, db: Session) -> Optional[dict]:
    """Cascade DeliveryPoint.grd_code → lookup ELD ref (Phase 3.6 Sprint C-3).

    Retourne dict avec metadata ELD (label, type, perimetre) si grd_code connu
    dans `eld_gaz_referentiel.yaml`. None sinon (ENEDIS/RTE = élec, hors scope ELD gaz).

    Anti-cycle : lecture seule, ne modifie pas le DP.
    """
    grd_code = getattr(delivery_point, "grd_code", None)
    if not grd_code:
        return None

    try:
        from config.eld_gaz_loader import get_eld_by_code, is_known_eld

        if not is_known_eld(grd_code):
            # ENEDIS / RTE / autres GRD élec ne sont pas dans le ref ELD gaz
            # Pas une erreur — comportement attendu.
            return None

        eld = get_eld_by_code(grd_code)
        return {
            "code": eld["code"],
            "label": eld["label"],
            "type": eld["type"],
            "perimetre": eld["perimetre"],
        }
    except Exception as e:
        _logger.warning(
            "eld_metadata lookup failed for DP %s grd_code=%s: %s",
            getattr(delivery_point, "id", None),
            grd_code,
            e,
        )
        return None


def _trigger_bill_recheck(delivery_point, db: Session) -> str:
    """Cascade DeliveryPoint.grd_code → trigger Bill Intelligence recheck cohérence.

    MVP Phase 3.6 : log structuré uniquement (Bill Intelligence module pas
    complet Sprint C-3). Sprint C-4+ : appel service `bill_intelligence.recheck_coherence()`
    pour vérifier Σ conso compteurs ↔ Σ conso contrats post-changement GRD.

    Anti-cycle : log only, pas d'écriture DB.
    """
    grd_code = getattr(delivery_point, "grd_code", None)
    _logger.info(
        "BILL_RECHECK_TRIGGERED",
        extra={
            "delivery_point_id": getattr(delivery_point, "id", None),
            "grd_code": grd_code,
            "site_id": getattr(delivery_point, "site_id", None),
            "phase": "C3.3.6_pivot_grd_code",
            "reason": "DeliveryPoint.grd_code modifié — Bill Intelligence à revérifier",
        },
    )
    return f"bill_recheck_logged for DP {getattr(delivery_point, 'id', None)}"


# ─── Helpers Phase 4.5 Sprint C-4 — cascade Org.consentement_* → DPs (vivante) ──
#
# Phase 4.4 a livré le modèle ORM (8 cols Org+DP). Phase 4.5 ACTIVE la cascade
# que Phase 3.7 Sprint C-3 avait reportée (champs alors inexistants). ADR-007
# implémentation runtime, Option B retenue (effective consent runtime via
# `services/consent_service.get_effective_consent`, pas d'écrasement physique
# du `_local` — RGPD-respectful).
#
# Périmètre cascade :
# - DataConnect (Enedis) : tous DPs élec de l'org (energy_type='elec')
# - GRDF (ADICT) : court-circuit ELD locales — UNIQUEMENT DPs `grd_code='GRDF'`
#   (les 20 ELD locales ont leur propre process consentement, différenciateur
#   PROMEOS RGPD-compliant Sprint C-3 Phase 3.6)


def _propagate_consentement_dataconnect(org, db: Session) -> str:
    """Cascade Org.consentement_dataconnect_global → DPs élec de l'org.

    Option B (Phase 4.5 ADR-007) : pas d'écrasement physique de `dp._local`.
    Retourne un compteur structuré pour audit log + tooltip UI.

    - eligible : DPs sans override local (consultent le global via consent_service)
    - overridden : DPs avec override local (préservé, pas affecté par cascade)
    - skipped : DPs gaz (hors scope DataConnect Enedis)
    """
    new_value = getattr(org, "consentement_dataconnect_global", None)
    if new_value is None:
        return "no_change_global_is_null"

    from models import DeliveryPoint, EntiteJuridique, Portefeuille, Site

    dps = (
        db.query(DeliveryPoint)
        .join(Site, DeliveryPoint.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org.id)
        .all()
    )

    eligible = 0
    overridden = 0
    skipped_gas = 0
    for dp in dps:
        energy_type = getattr(dp, "energy_type", None)
        # energy_type peut être Enum ou str selon contexte
        et_str = energy_type.value if hasattr(energy_type, "value") else energy_type
        if et_str and "gaz" in str(et_str).lower():
            skipped_gas += 1
            continue
        if dp.consentement_dataconnect_local is not None:
            overridden += 1  # Override local préservé (ADR-007)
            continue
        eligible += 1

    _logger.info(
        "CASCADE_CONSENTEMENT_DATACONNECT",
        extra={
            "organisation_id": org.id,
            "new_value": new_value,
            "eligible_dps": eligible,
            "overridden_local": overridden,
            "skipped_gas": skipped_gas,
            "phase": "C4.4.5_consentement_dataconnect_active",
        },
    )
    return f"dataconnect_global={new_value}_eligible={eligible}_overridden={overridden}_skipped_gas={skipped_gas}"


def _propagate_consentement_grdf(org, db: Session) -> str:
    """Cascade Org.consentement_grdf_global → DPs gaz `grd_code='GRDF'` UNIQUEMENT.

    COURT-CIRCUIT ELD LOCALES préservé (différenciateur PROMEOS Sprint C-3 Phase 3.6) :
    les 20 ELD locales (Régaz Bordeaux, GreenAlp Grenoble, R-GDS Strasbourg, etc.) ont
    leur propre process consentement local — la cascade Org.consentement_grdf_global
    NE LES TOUCHE PAS.

    Retourne compteur structuré : eligible / overridden / skipped_eld / skipped_elec.
    """
    new_value = getattr(org, "consentement_grdf_global", None)
    if new_value is None:
        return "no_change_global_is_null"

    from config.eld_gaz_loader import is_grdf
    from models import DeliveryPoint, EntiteJuridique, Portefeuille, Site

    dps = (
        db.query(DeliveryPoint)
        .join(Site, DeliveryPoint.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org.id)
        .all()
    )

    eligible = 0
    overridden = 0
    skipped_eld = 0
    skipped_elec = 0
    for dp in dps:
        energy_type = getattr(dp, "energy_type", None)
        et_str = energy_type.value if hasattr(energy_type, "value") else energy_type
        if not et_str or "gaz" not in str(et_str).lower():
            skipped_elec += 1
            continue
        # Cardinal court-circuit RGPD : seuls les DPs grd_code='GRDF' sont éligibles
        grd_code = getattr(dp, "grd_code", None)
        if not is_grdf(grd_code or ""):
            skipped_eld += 1  # ELD locale (Régaz/GreenAlp/etc.) — process séparé
            continue
        if dp.consentement_grdf_local is not None:
            overridden += 1  # Override local préservé (ADR-007)
            continue
        eligible += 1

    _logger.info(
        "CASCADE_CONSENTEMENT_GRDF",
        extra={
            "organisation_id": org.id,
            "new_value": new_value,
            "eligible_dps": eligible,
            "overridden_local": overridden,
            "skipped_eld_locales": skipped_eld,
            "skipped_elec": skipped_elec,
            "court_circuit_eld_active": True,
            "phase": "C4.4.5_consentement_grdf_active_court_circuit_eld",
        },
    )
    return (
        f"grdf_global={new_value}_eligible={eligible}_overridden={overridden}_"
        f"skipped_eld={skipped_eld}_skipped_elec={skipped_elec}"
    )


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
        # Phase 4.2 — intensity_tertiaire dépend de tertiaire_area_m2
        lambda s, db: ("intensity_kwh_m2_tertiaire", _recompute_intensity_tertiaire(s)),
        lambda s, db: ("compliance_score", _recompute_compliance(s, db)),
    ],
    "Site.surface_m2": [
        # Phase 4.2 — intensity_total dépend de surface_m2 (UI legacy)
        lambda s, db: ("intensity_kwh_m2_total", _recompute_intensity_total(s)),
    ],
    "Site.annual_kwh_total": [
        # Phase 4.2 — annual_kwh impacte les 2 intensités
        lambda s, db: ("intensity_kwh_m2_total", _recompute_intensity_total(s)),
        lambda s, db: ("intensity_kwh_m2_tertiaire", _recompute_intensity_tertiaire(s)),
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
    # Phase 5.2 Sprint C-2 — cascade org-scoped (clôture D-Phase6-Cascade-EJ-Sites-001
    # pivoté sous D-Phase6-Cascade-AuditSme-Org-Sites-001 — cf. tracker dette).
    # Anti-cycle vérifié : recompute_organisation lit compliance et ne modifie pas conso.
    "AuditEnergetique.conso_annuelle_moy_gwh": [
        lambda audit_sme, db: ("audit_sme_obligation", _recompute_audit_sme_obligation(audit_sme)),
        lambda audit_sme, db: (
            "compliance_score_all_sites",
            _recompute_organisation_via_coordinator(audit_sme, db),
        ),
    ],
    # Phase 5.3 Sprint C-2 — cascade contract renewal alerte 90j MVP
    # (clôture D-Phase6-Cascade-Contract-Renewal-001).
    # ⚠️ Ordre critique : reset flag AVANT trigger (sinon idempotence skip le re-log
    # immédiat à la nouvelle date end_date).
    "EnergyContract.end_date": [
        lambda contract, db: (
            "alerte_renouvellement_logged_at_reset",
            _reset_renewal_alert_flag(contract, db),
        ),
        lambda contract, db: ("renewal_alert", _trigger_renewal_alert(contract, db)),
    ],
    # Phase 3.6 Sprint C-3 — cascade ELD ref + bill recheck (clôture
    # D-Phase6-Cascade-DeliveryPoint-Fta-001 pivoté sur DP.grd_code, cf. tracker dette).
    # Pivot pré-build audit : code_fta n'existait pas, grd_code est le champ pertinent ELD.
    "DeliveryPoint.grd_code": [
        lambda dp, db: ("eld_metadata", _recompute_eld_metadata_from_grd_code(dp, db)),
        lambda dp, db: ("bill_recheck", _trigger_bill_recheck(dp, db)),
    ],
    # Phase 4.5 Sprint C-4 — cascade Org consentement vivante (ADR-007 implémentation).
    # Phase 4.4 a livré le modèle ORM (8 cols Org+DP), Phase 4.5 active la cascade
    # que Phase 3.7 Sprint C-3 avait reportée. Option B (effective consent runtime,
    # pas d'écrasement physique des `_local` — RGPD-respectful, override préservé).
    # Court-circuit ELD locales préservé pour cascade GRDF (différenciateur cardinal).
    "Organisation.consentement_dataconnect_global": [
        lambda org, db: ("consentement_dataconnect_propagation", _propagate_consentement_dataconnect(org, db)),
    ],
    "Organisation.consentement_grdf_global": [
        lambda org, db: ("consentement_grdf_propagation", _propagate_consentement_grdf(org, db)),
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
    # Phase 4.2 Sprint C-2 — intensités persistées sur Site
    "intensity_kwh_m2_total",
    "intensity_kwh_m2_tertiaire",
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
