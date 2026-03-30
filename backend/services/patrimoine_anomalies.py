"""
PROMEOS — Patrimoine Anomalies Service (V58)

8 règles de contrôle d'intégrité P0 sur les données patrimoine.
Les anomalies sont calculées à la demande (pas de table persistée — D4).

Score de complétude (D7) :
    score = max(0, 100 - Σ penalty)
    CRITICAL → -30, HIGH → -15, MEDIUM → -7, LOW → -3

Chaque Anomaly expose :
    code, severity, title_fr, detail_fr, evidence, cta:{label,to}, fix_hint_fr
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models import (
    Site,
    Batiment,
    Usage,
    Compteur,
    DeliveryPoint,
    EnergyContract,
    not_deleted,
)
from services.patrimoine_snapshot import SURFACE_MISMATCH_TOLERANCE


# ── Score penalties ───────────────────────────────────────────────────────────

_PENALTY: Dict[str, int] = {
    "CRITICAL": 30,
    "HIGH": 15,
    "MEDIUM": 7,
    "LOW": 3,
}


def _anomaly(
    code: str,
    severity: str,
    title_fr: str,
    detail_fr: str,
    evidence: Dict[str, Any],
    cta_label: str,
    cta_to: str,
    fix_hint_fr: str,
) -> Dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "title_fr": title_fr,
        "detail_fr": detail_fr,
        "evidence": evidence,
        "cta": {"label": cta_label, "to": cta_to},
        "fix_hint_fr": fix_hint_fr,
    }


# ── Règles P0 ─────────────────────────────────────────────────────────────────


def _rule_surface_missing(
    site: Site,
    batiments: List[Batiment],
) -> Optional[Dict[str, Any]]:
    """SURFACE_MISSING : surface totale inconnue (SoT)."""
    if batiments:
        sot = sum(b.surface_m2 or 0.0 for b in batiments)
        if sot > 0:
            return None
        # Bâtiments présents mais toutes surfaces à None/0
        return _anomaly(
            code="SURFACE_MISSING",
            severity="HIGH",
            title_fr="Surface bâtiments inconnue",
            detail_fr=(f"{len(batiments)} bâtiment(s) présent(s) mais aucune surface renseignée."),
            evidence={"nb_batiments": len(batiments), "surface_sot_m2": 0},
            cta_label="Éditer les bâtiments",
            cta_to="/patrimoine",
            fix_hint_fr="Renseignez la surface (m²) de chaque bâtiment.",
        )
    else:
        # Pas de bâtiments : fallback sur site.surface_m2
        if site.surface_m2 and site.surface_m2 > 0:
            return None
        return _anomaly(
            code="SURFACE_MISSING",
            severity="HIGH",
            title_fr="Surface totale inconnue",
            detail_fr="La surface du site n'est pas renseignée et aucun bâtiment n'est défini.",
            evidence={"site_id": site.id, "surface_site_m2": site.surface_m2},
            cta_label="Éditer le site",
            cta_to="/patrimoine",
            fix_hint_fr="Renseignez la surface (m²) du site ou ajoutez des bâtiments avec leur surface.",
        )


def _rule_surface_mismatch(
    site: Site,
    batiments: List[Batiment],
) -> Optional[Dict[str, Any]]:
    """SURFACE_MISMATCH : écart entre site.surface_m2 et ∑ bâtiments > tolérance."""
    if not batiments or not site.surface_m2 or site.surface_m2 <= 0:
        return None
    sum_bat = sum(b.surface_m2 or 0.0 for b in batiments)
    if sum_bat <= 0:
        return None
    ecart_pct = abs(sum_bat - site.surface_m2) / site.surface_m2
    if ecart_pct <= SURFACE_MISMATCH_TOLERANCE:
        return None
    return _anomaly(
        code="SURFACE_MISMATCH",
        severity="MEDIUM",
        title_fr="Écart de surface détecté",
        detail_fr=(
            f"Surface site : {site.surface_m2:.0f} m² · "
            f"∑ bâtiments : {sum_bat:.0f} m² · "
            f"Écart : {ecart_pct * 100:.1f} % (tolérance : {SURFACE_MISMATCH_TOLERANCE * 100:.0f} %)."
        ),
        evidence={
            "surface_site_m2": site.surface_m2,
            "surface_batiments_sum_m2": round(sum_bat, 1),
            "ecart_pct": round(ecart_pct * 100, 1),
        },
        cta_label="Voir les bâtiments",
        cta_to="/patrimoine",
        fix_hint_fr=("Mettez à jour la surface du site ou des bâtiments pour réduire l'écart."),
    )


def _rule_building_missing(batiments: List[Batiment], site: Site) -> Optional[Dict[str, Any]]:
    """BUILDING_MISSING : 0 bâtiment enregistré."""
    if batiments:
        return None
    return _anomaly(
        code="BUILDING_MISSING",
        severity="MEDIUM",
        title_fr="Aucun bâtiment défini",
        detail_fr="Ce site n'a aucun bâtiment enregistré. La surface réglementaire ne peut pas être calculée.",
        evidence={"site_id": site.id, "nb_batiments": 0},
        cta_label="Créer un bâtiment",
        cta_to="/patrimoine",
        fix_hint_fr="Ajoutez au moins un bâtiment avec sa surface et son usage.",
    )


def _rule_building_usage_missing(batiments: List[Batiment], usages_by_bat: Dict[int, List]) -> List[Dict[str, Any]]:
    """BUILDING_USAGE_MISSING : bâtiment sans usage défini."""
    anomalies = []
    for b in batiments:
        if not usages_by_bat.get(b.id):
            anomalies.append(
                _anomaly(
                    code="BUILDING_USAGE_MISSING",
                    severity="LOW",
                    title_fr=f'Usage manquant — bâtiment "{b.nom}"',
                    detail_fr=f'Le bâtiment "{b.nom}" (id={b.id}) n\'a aucun usage énergétique défini.',
                    evidence={"batiment_id": b.id, "batiment_nom": b.nom},
                    cta_label="Éditer le bâtiment",
                    cta_to="/patrimoine",
                    fix_hint_fr="Associez un usage (bureaux, commerce, industrie…) à ce bâtiment.",
                )
            )
    return anomalies


def _rule_meter_no_delivery_point(compteurs: List[Compteur]) -> List[Dict[str, Any]]:
    """METER_NO_DELIVERY_POINT : compteur sans delivery_point_id."""
    anomalies = []
    for c in compteurs:
        if c.delivery_point_id is None:
            anomalies.append(
                _anomaly(
                    code="METER_NO_DELIVERY_POINT",
                    severity="MEDIUM",
                    title_fr=f"Compteur sans point de livraison — {c.numero_serie or c.id}",
                    detail_fr=(
                        f"Le compteur {c.numero_serie or f'id={c.id}'} "
                        f"({c.type.value if c.type else '?'}) "
                        f"n'est pas associé à un point de livraison (PRM/PCE)."
                    ),
                    evidence={"compteur_id": c.id, "numero_serie": c.numero_serie},
                    cta_label="Éditer le compteur",
                    cta_to="/patrimoine",
                    fix_hint_fr="Associez un point de livraison (PRM pour l'électricité, PCE pour le gaz).",
                )
            )
    return anomalies


def _rule_contract_date_invalid(contracts: List[EnergyContract]) -> List[Dict[str, Any]]:
    """CONTRACT_DATE_INVALID : start_date >= end_date (quand les deux sont présentes)."""
    anomalies = []
    for c in contracts:
        if c.start_date and c.end_date and c.start_date >= c.end_date:
            anomalies.append(
                _anomaly(
                    code="CONTRACT_DATE_INVALID",
                    severity="HIGH",
                    title_fr=f"Dates de contrat invalides — {c.supplier_name}",
                    detail_fr=(
                        f"Contrat {c.supplier_name} ({c.energy_type.value if c.energy_type else '?'}) : "
                        f"date de début ({c.start_date}) ≥ date de fin ({c.end_date})."
                    ),
                    evidence={
                        "contract_id": c.id,
                        "supplier_name": c.supplier_name,
                        "start_date": c.start_date.isoformat(),
                        "end_date": c.end_date.isoformat(),
                    },
                    cta_label="Éditer le contrat",
                    cta_to="/patrimoine",
                    fix_hint_fr="Corrigez les dates : la date de début doit être antérieure à la date de fin.",
                )
            )
    return anomalies


def _rule_contract_overlap(contracts: List[EnergyContract]) -> List[Dict[str, Any]]:
    """CONTRACT_OVERLAP_SITE : chevauchement de contrats pour la même énergie sur ce site."""
    anomalies = []
    # Grouper par energy_type
    by_type: Dict[str, List[EnergyContract]] = {}
    for c in contracts:
        key = c.energy_type.value if c.energy_type else "__unknown__"
        by_type.setdefault(key, []).append(c)

    reported_pairs: set = set()
    for energy_type, group in by_type.items():
        # Seulement les contrats avec les deux dates valides
        dated = [
            (c, c.start_date, c.end_date) for c in group if c.start_date and c.end_date and c.start_date < c.end_date
        ]
        for i, (c1, s1, e1) in enumerate(dated):
            for c2, s2, e2 in dated[i + 1 :]:
                # Chevauchement : s1 < e2 AND s2 < e1
                if s1 < e2 and s2 < e1:
                    pair_key = (min(c1.id, c2.id), max(c1.id, c2.id))
                    if pair_key in reported_pairs:
                        continue
                    reported_pairs.add(pair_key)
                    anomalies.append(
                        _anomaly(
                            code="CONTRACT_OVERLAP_SITE",
                            severity="HIGH",
                            title_fr=f"Chevauchement de contrats {energy_type.upper()}",
                            detail_fr=(
                                f"Contrats {c1.supplier_name} ({s1}→{e1}) et "
                                f"{c2.supplier_name} ({s2}→{e2}) se chevauchent "
                                f"pour l'énergie {energy_type}."
                            ),
                            evidence={
                                "contract_id_1": c1.id,
                                "contract_id_2": c2.id,
                                "energy_type": energy_type,
                                "supplier_1": c1.supplier_name,
                                "supplier_2": c2.supplier_name,
                            },
                            cta_label="Voir les contrats",
                            cta_to="/patrimoine",
                            fix_hint_fr="Corrigez les dates de fin/début pour supprimer le chevauchement.",
                        )
                    )
    return anomalies


def _rule_orphans_detected(
    site: Site,
    batiments: List[Batiment],
    compteurs: List[Compteur],
    delivery_points: List[DeliveryPoint],
) -> Optional[Dict[str, Any]]:
    """ORPHANS_DETECTED : site archivé (actif=False) avec des enfants encore actifs."""
    if site.actif:
        return None  # site actif → pas d'orphelins
    orphan_details = []
    if batiments:
        orphan_details.append(f"{len(batiments)} bâtiment(s)")
    if compteurs:
        orphan_details.append(f"{len(compteurs)} compteur(s) actif(s)")
    if delivery_points:
        orphan_details.append(f"{len(delivery_points)} point(s) de livraison")
    if not orphan_details:
        return None
    return _anomaly(
        code="ORPHANS_DETECTED",
        severity="CRITICAL",
        title_fr="Données orphelines détectées",
        detail_fr=(f"Le site est archivé (inactif) mais contient encore : {', '.join(orphan_details)}."),
        evidence={
            "site_id": site.id,
            "site_actif": site.actif,
            "nb_batiments": len(batiments),
            "nb_compteurs_actifs": len(compteurs),
            "nb_delivery_points": len(delivery_points),
        },
        cta_label="Audit / nettoyage",
        cta_to="/patrimoine",
        fix_hint_fr=(
            "Archivez ou supprimez les enregistrements liés, ou restaurez le site si l'archivage était une erreur."
        ),
    )


def _rule_tertiaire_surface_exceeds_total(site: Site) -> Optional[Dict[str, Any]]:
    """TERTIAIRE_SURFACE_EXCEEDS_TOTAL : surface tertiaire > surface totale (+5% tolérance)."""
    if not site.tertiaire_area_m2 or not site.surface_m2 or site.surface_m2 == 0:
        return None
    if site.tertiaire_area_m2 <= site.surface_m2 * 1.05:
        return None
    ecart_pct = round((site.tertiaire_area_m2 / site.surface_m2 - 1) * 100, 1)
    return _anomaly(
        code="TERTIAIRE_SURFACE_EXCEEDS_TOTAL",
        severity="HIGH",
        title_fr="Surface tertiaire supérieure à la surface totale",
        detail_fr=f"Tertiaire : {site.tertiaire_area_m2} m² · Total : {site.surface_m2} m² · Écart : {ecart_pct} %",
        evidence={
            "tertiaire_area_m2": site.tertiaire_area_m2,
            "surface_m2": site.surface_m2,
            "ecart_pct": ecart_pct,
        },
        cta_label="Corriger les surfaces",
        cta_to="/patrimoine",
        fix_hint_fr="Vérifiez la cohérence entre surface tertiaire assujettie et surface totale du site.",
    )


# ── Fonction principale ───────────────────────────────────────────────────────


def compute_site_anomalies(site_id: int, db: Session) -> Dict[str, Any]:
    """
    Calcule toutes les anomalies P0 pour un site donné.
    Pré-condition : le site existe et appartient à l'org (vérifié par l'appelant).

    Retourne :
        {
            "site_id": int,
            "anomalies": [...],
            "completude_score": int (0-100),
            "nb_anomalies": int,
            "computed_at": str (ISO 8601),
        }
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if site is None:
        return {
            "site_id": site_id,
            "anomalies": [],
            "completude_score": 0,
            "nb_anomalies": 0,
            "computed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat() + "Z",
        }

    # Batch queries — zéro N+1
    batiments: List[Batiment] = db.query(Batiment).filter(Batiment.site_id == site_id, not_deleted(Batiment)).all()
    bat_ids = [b.id for b in batiments]
    usages_by_bat: Dict[int, List] = {}
    if bat_ids:
        usages = db.query(Usage).filter(Usage.batiment_id.in_(bat_ids)).all()
        for u in usages:
            usages_by_bat.setdefault(u.batiment_id, []).append(u)

    compteurs: List[Compteur] = db.query(Compteur).filter(Compteur.site_id == site_id, not_deleted(Compteur)).all()
    delivery_points: List[DeliveryPoint] = (
        db.query(DeliveryPoint).filter(DeliveryPoint.site_id == site_id, not_deleted(DeliveryPoint)).all()
    )
    contracts: List[EnergyContract] = db.query(EnergyContract).filter(EnergyContract.site_id == site_id).all()

    # ── Appliquer les règles ──────────────────────────────────────────────────
    anomalies: List[Dict[str, Any]] = []

    r = _rule_surface_missing(site, batiments)
    if r:
        anomalies.append(r)

    r = _rule_surface_mismatch(site, batiments)
    if r:
        anomalies.append(r)

    r = _rule_building_missing(batiments, site)
    if r:
        anomalies.append(r)

    anomalies.extend(_rule_building_usage_missing(batiments, usages_by_bat))
    anomalies.extend(_rule_meter_no_delivery_point(compteurs))
    anomalies.extend(_rule_contract_date_invalid(contracts))
    anomalies.extend(_rule_contract_overlap(contracts))

    r = _rule_orphans_detected(site, batiments, compteurs, delivery_points)
    if r:
        anomalies.append(r)

    r = _rule_tertiaire_surface_exceeds_total(site)
    if r:
        anomalies.append(r)

    # ── Score (D7) ────────────────────────────────────────────────────────────
    penalty = sum(_PENALTY.get(a["severity"], 0) for a in anomalies)
    score = max(0, 100 - penalty)

    # Trier : CRITICAL → HIGH → MEDIUM → LOW
    _order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    anomalies.sort(key=lambda a: _order.get(a["severity"], 99))

    from datetime import datetime, timezone

    return {
        "site_id": site_id,
        "anomalies": anomalies,
        "completude_score": score,
        "nb_anomalies": len(anomalies),
        "computed_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
