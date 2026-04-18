"""
PROMEOS — Simulateur facture annuelle prévisionnelle post-ARENH (2026+).

Répond à la question "combien coûtera ma facture énergie en 2026 / 2027 ?"
avec une décomposition par composante réglementaire post-ARENH :
    - fourniture (forward baseload × CDC annuel)
    - TURPE 7 (part fixe + variable)
    - VNU (statut informatif : dormant/actif selon seuil CRE ; facture client
      = 0 dans les 2 cas — upside tracé dans `hypotheses.vnu_risque_upside_*`)
    - mécanisme capacité RTE (enchères PL-4/PL-1 centralisées nov. 2026)
    - CBAM scope (non applicable à la conso élec directe — documenté)
    - taxes agrégées (accise + CTA + TVA)

Ce moteur ne remplace PAS `strategy_recommender.recommend_purchase_strategy`
(lequel produit une composition fixe/indexé/spot/PPA). Il répond à une
question différente : **chiffrage annuel décomposé** pour budget 2026+.

Doctrine :
- MVP indicatif, confiance = "indicative"
- Fallbacks défensifs traçables (clé `source_calibration`)
- Jamais "flex" standalone dans les strings exposées (doctrine wording)
- Réutilise `ParameterStore` (billing_engine), `resolve_archetype` (flex),
  `load_yaml_section` (tarifs_reglementaires.yaml)

Sources :
- Post-ARENH au 01/01/2026 (art. L. 336-1 Code énergie, Loi souveraineté
  énergétique 2023-491)
- TURPE 7 CRE délibération 2025-78 (1/08/2025, brochure Enedis p.13-14)
- VNU : Décret 2026-55 + CRE 2026-52 (tarif unitaire 2026 = 0 €/MWh ;
  seuils activation 78 / 110 €/MWh)
- Capacité RTE : Décret 2025-1441 + Arrêté 18/03/2026 (mécanisme centralisé
  Y-4 / Y-1, démarrage 01/11/2026)
- Accise / CTA / TVA : tarifs_reglementaires.yaml versionnés
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from services.billing_engine.parameter_store import ParameterStore
from utils.parameter_store_base import load_yaml_section, paris_today

logger = logging.getLogger(__name__)


# ── Constantes MVP ───────────────────────────────────────────────────────────
# Hypothèses produit dédiées post-ARENH 2026+. Versionnables plus tard via
# ParameterStore, volontairement centralisées ici pour le MVP.

DEFAULT_ANNUAL_KWH = 100_000.0  # Fallback si site sans conso
DEFAULT_ARCHETYPE = "BUREAU_STANDARD"

# Mécanisme capacité RTE — aligné sur `billing_engine/catalog.py::CAPACITE_ELEC`
# (enchère 06/03/2025 : 3.15 EUR/MW × coeff obligation 1.2 / 8760h ≈ 0.43 EUR/MWh).
# Le mécanisme centralisé acheteur unique nov. 2026 conserve la même valeur
# placeholder (CAPACITE_ELEC_NOV2026) — pas de discontinuité tarifaire modélisée.
# Source unique de vérité : `billing_engine/catalog.py` ligne 879.
CAPACITE_UNITAIRE_EUR_MWH = 0.43

# Seuil VNU par défaut (fallback hardcodé si YAML indisponible).
# Valeur canonique dans `tarifs_reglementaires.yaml::vnu.seuil_1_eur_mwh`.
VNU_SEUIL_DEFAUT_EUR_MWH = 78.0

# Fallbacks hardcodés — constantes YAML canoniques dans `cost_simulator_2026`
# section de `tarifs_reglementaires.yaml`. Valeurs ici uniquement pour tenir
# les tests en mode stand-alone (YAML manquant) + exposer une cible de
# compatibilité stable à la BC.
FALLBACK_FORWARD_EUR_MWH = 68.0  # YAML: cost_simulator_2026.fallback_forward_eur_mwh
BASELINE_2024_EUR_MWH_FALLBACK = 80.0  # YAML: cost_simulator_2026.baseline_eur_mwh
VNU_IMPACT_MVP_EUR_MWH_FALLBACK = 2.0  # YAML: vnu.impact_upside_mvp_eur_mwh
PEAK_PREMIUM_RATIO_FALLBACK = 0.15  # YAML: cost_simulator_2026.peak_premium_ratio

# Facteur de forme typique par archétype (E_an / (P_max × 8760h)).
# Aligné sur les 8 archétypes canoniques `ARCHETYPE_CALIBRATION_2024`
# (`services/pilotage/constants.py`). Purement indicatif — tracé dans
# `hypotheses.facteur_forme` pour audit, non utilisé dans le calcul MVP.
ARCHETYPE_FACTEUR_FORME = {
    "BUREAU_STANDARD": 0.30,
    "COMMERCE_ALIMENTAIRE": 0.55,
    "COMMERCE_SPECIALISE": 0.35,
    "LOGISTIQUE_FRIGO": 0.65,
    "ENSEIGNEMENT": 0.25,
    "SANTE": 0.60,
    "HOTELLERIE": 0.45,
    "INDUSTRIE_LEGERE": 0.50,
    "DEFAULT": 0.40,
}

# Alias historique utilisé par `test_achat_cost_simulator_2026.py`. Valeur
# effective toujours lue depuis YAML via `_load_simulator_params`.
BASELINE_2024_EUR_MWH = BASELINE_2024_EUR_MWH_FALLBACK

# Segment TURPE par défaut (C4_BT = tertiaire moyen, majoritaire dans portefeuille PME).
# Si `Meter.tariff_type` renseigne C5 / C3, on bascule.
DEFAULT_TURPE_SEGMENT = "C4_BT"

# TURPE 7 fixe — valeurs CRE canoniques (`billing_engine/catalog.py::TURPE7_RATES`,
# délib. CRE 2025-78 p.13-16, entrée en vigueur 01/08/2025).
#
# Note : le YAML `config/tarifs_reglementaires.yaml` `turpe.segments.*.gestion_eur_mois`
# diverge sensiblement du catalog CRE (C5 221.76 €/an YAML vs 16.80 €/an catalog ;
# C4 367.20 vs 217.80). Investigation séparée requise pour trancher si YAML =
# calibration empirique ou erreur. Cost simulator source = catalog CRE pour
# auditabilité client.
TURPE_FIXE_PROFILES = {
    "C5_BT": {
        "gestion_eur_an": 16.80,  # CRE TURPE 7 BT≤36kVA CG CU (brochure p.16)
        "comptage_eur_an": 22.00,  # CC bimestrielle Linky (p.16)
        "soutirage_moyen_eur_kva_an": 10.11,  # b CU4 (p.17)
        "p_souscrite_min_kva": 9.0,
    },
    "C4_BT": {
        "gestion_eur_an": 217.80,  # CRE TURPE 7 BT>36kVA CG CU (brochure p.13)
        "comptage_eur_an": 283.27,  # CC mensuelle (p.13)
        "soutirage_moyen_eur_kva_an": 15.03,  # Moyenne b CU HPH/HCH/HPB/HCB (p.14)
        "p_souscrite_min_kva": 36.0,
    },
    "C3_HTA": {
        "gestion_eur_an": 435.72,  # CRE TURPE 7 HTA CG CU (brochure p.9)
        "comptage_eur_an": 283.27,  # CC HTA (alignement p.9)
        "soutirage_moyen_eur_kva_an": 3.5,  # HTA b_i significativement plus bas
        "p_souscrite_min_kva": 250.0,
    },
}


# ── Helpers internes ─────────────────────────────────────────────────────────


def _resolve_forward_y1(db: Session, year: int, fallback_eur_mwh: float) -> tuple[float, str]:
    """
    Cherche un forward baseload FR année `year` dans `mkt_prices`.

    Retourne (prix_eur_mwh, trace). La trace est la clé à ajouter dans
    `source_calibration` si on a dû tomber sur le fallback YAML-versionné.
    """
    try:
        from models.market_models import (
            MktPrice,
            MarketType,
            ProductType,
            PriceZone,
        )

        start_year = datetime(year, 1, 1)
        end_year = datetime(year, 12, 31, 23, 59, 59)
        price = (
            db.query(func.avg(MktPrice.price_eur_mwh))
            .filter(
                MktPrice.market_type == MarketType.FORWARD_YEAR,
                MktPrice.product_type == ProductType.BASELOAD,
                MktPrice.zone == PriceZone.FR,
                MktPrice.delivery_start >= start_year,
                MktPrice.delivery_start <= end_year,
            )
            .scalar()
        )
        if price is not None and price > 0:
            return float(price), ""
    except Exception as exc:
        logger.debug("cost_simulator_2026: forward lookup failed: %s", exc)

    return fallback_eur_mwh, "forward_indisponible_fallback_reference_price"


def _resolve_archetype_safe(db: Session, site) -> tuple[str, Optional[str]]:
    """
    Résolution archétype tolérante (service sous test sans KB / sans meter).

    Retourne (archetype_code, trace). Trace non-vide = fallback déclenché.
    """
    # 1. Si site.archetype_code renseigné, priorité absolue (plus rapide,
    #    et évite d'ouvrir les services kb_service/flex en cascade dans
    #    des tests qui ne seedent ni Meter ni KBService.).
    try:
        code = getattr(site, "archetype_code", None)
        if code:
            return str(code), None
    except Exception:
        pass

    try:
        from services.flex.archetype_resolver import resolve_archetype

        code = resolve_archetype(db, site)
        if code and code != "DEFAULT":
            return code, None
        return DEFAULT_ARCHETYPE, "archetype_inconnu_fallback_BUREAU_STANDARD"
    except Exception as exc:
        logger.debug("cost_simulator_2026: archetype resolver failed: %s", exc)
        return DEFAULT_ARCHETYPE, "archetype_inconnu_fallback_BUREAU_STANDARD"


def _resolve_annual_kwh(site) -> tuple[float, Optional[str]]:
    """Récupère annual_kwh_total ou fallback 100 000 kWh avec trace."""
    try:
        value = getattr(site, "annual_kwh_total", None)
    except Exception:
        value = None
    if value and value > 0:
        return float(value), None
    return DEFAULT_ANNUAL_KWH, "annual_kwh_indisponible_fallback_100000"


def _resolve_turpe_segment(db: Session, site) -> str:
    """Détecte le segment TURPE (C5 / C4 / C3) via Meter.tariff_type si dispo."""
    try:
        from models.energy_models import Meter

        meter = db.query(Meter).filter(Meter.site_id == site.id).first()
        if meter and meter.tariff_type:
            tt = meter.tariff_type.upper()
            if "C5" in tt:
                return "C5_BT"
            if "C3" in tt or "HTA" in tt:
                return "C3_HTA"
            if "C4" in tt:
                return "C4_BT"
    except Exception as exc:
        logger.debug("cost_simulator_2026: meter lookup failed: %s", exc)
    return DEFAULT_TURPE_SEGMENT


def _safe_param(
    store: ParameterStore,
    code: str,
    at_date: date,
    default: float,
) -> tuple[float, bool]:
    """
    Résout un paramètre ParameterStore avec fallback hardcodé.

    Retourne (valeur, fallback_utilise).
    """
    try:
        res = store.get(code, at_date=at_date)
        if res.source == "missing":
            return default, True
        return float(res.value), False
    except Exception as exc:
        logger.debug("cost_simulator_2026: param %s failed: %s", code, exc)
        return default, True


def _resolve_accise_code(site) -> str:
    """Route accise vers T1/T2/HP via le helper canonique V113.

    `DeliveryPoint.tax_profiles` est la backref plurielle SQLAlchemy (un PDL
    peut avoir plusieurs profils historisés via `valid_from`/`valid_to`) — on
    prend le premier trouvé, ce qui est suffisant pour MVP indicatif.
    """
    from services.billing_shadow_v2 import _accise_code_for_category

    tp = None
    try:
        for dp in getattr(site, "delivery_points", None) or []:
            profiles = getattr(dp, "tax_profiles", None) or []
            if profiles:
                tp = profiles[0]
                break
    except Exception as exc:
        logger.debug("cost_simulator_2026: tax_profile lookup failed: %s", exc)
    return _accise_code_for_category("elec", tp)


def _resolve_vnu_seuil() -> tuple[float, Optional[str], float]:
    """Extrait seuil + impact upside VNU depuis `tarifs_reglementaires.yaml::vnu`.

    Retourne `(seuil_eur_mwh, source_ref, impact_upside_eur_mwh)`. Fallback
    hardcodé si YAML absent — warning loggé pour visibilité prod.
    """
    try:
        vnu = load_yaml_section("vnu") or {}
        seuil = float(vnu.get("seuil_1_eur_mwh", VNU_SEUIL_DEFAUT_EUR_MWH))
        impact = float(vnu.get("impact_upside_mvp_eur_mwh", VNU_IMPACT_MVP_EUR_MWH_FALLBACK))
        return seuil, vnu.get("source"), impact
    except Exception as exc:
        logger.warning("cost_simulator_2026: vnu lookup failed (fallback hardcoded): %s", exc)
    return VNU_SEUIL_DEFAUT_EUR_MWH, None, VNU_IMPACT_MVP_EUR_MWH_FALLBACK


def _load_simulator_params() -> dict[str, float]:
    """Charge les paramètres MVP versionnés depuis YAML.

    `tarifs_reglementaires.yaml::cost_simulator_2026` fournit `baseline_eur_mwh`,
    `fallback_forward_eur_mwh`, `peak_premium_ratio`. Fallback hardcodé en cas
    d'indisponibilité (test en mémoire sans fichier YAML).
    """
    try:
        section = load_yaml_section("cost_simulator_2026") or {}
        return {
            "baseline_eur_mwh": float(section.get("baseline_eur_mwh", BASELINE_2024_EUR_MWH_FALLBACK)),
            "fallback_forward_eur_mwh": float(section.get("fallback_forward_eur_mwh", FALLBACK_FORWARD_EUR_MWH)),
            "peak_premium_ratio": float(section.get("peak_premium_ratio", PEAK_PREMIUM_RATIO_FALLBACK)),
        }
    except Exception as exc:
        logger.warning("cost_simulator_2026: simulator params lookup failed (fallback hardcoded): %s", exc)
    return {
        "baseline_eur_mwh": BASELINE_2024_EUR_MWH_FALLBACK,
        "fallback_forward_eur_mwh": FALLBACK_FORWARD_EUR_MWH,
        "peak_premium_ratio": PEAK_PREMIUM_RATIO_FALLBACK,
    }


# ── Interface publique ──────────────────────────────────────────────────────


def simulate_annual_cost_2026(
    site,
    db: Session,
    year: int = 2026,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Simule la facture annuelle prévisionnelle post-ARENH décomposée par
    composante réglementaire 2026+.

    Args
    ----
    site  : models.Site (SQLAlchemy ORM)
    db    : Session — SQLite in-memory OK (tests) ou postgres (prod)
    year  : 2026 | 2027 (prévisionnel — un seul CAL+1 à la fois)
    now   : injection horloge (tests) — sinon `paris_today()`

    Returns
    -------
    dict — structure exacte, cf. docstring au sommet + contrat agent B.
    """
    at_date = (now.date() if isinstance(now, datetime) else None) or paris_today()

    # 0. Chargement des constantes MVP versionnées (YAML).
    sim_params = _load_simulator_params()
    baseline_eur_mwh = sim_params["baseline_eur_mwh"]
    peak_premium_ratio = sim_params["peak_premium_ratio"]
    fallback_forward = sim_params["fallback_forward_eur_mwh"]

    # 1. Normalisation inputs site
    annual_kwh, trace_kwh = _resolve_annual_kwh(site)
    annual_mwh = annual_kwh / 1000.0
    archetype, trace_arch = _resolve_archetype_safe(db, site)
    facteur_forme = ARCHETYPE_FACTEUR_FORME.get(archetype, ARCHETYPE_FACTEUR_FORME["DEFAULT"])
    turpe_segment = _resolve_turpe_segment(db, site)

    traces: list[str] = []
    if trace_kwh:
        traces.append(trace_kwh)
    if trace_arch:
        traces.append(trace_arch)

    # 2. ParameterStore (YAML + DB)
    store = ParameterStore(db=db)

    # 3. Fourniture énergie — forward Y+1 baseload × CDC annuel + premium peakload
    # Un site peaky (faible facteur de forme, ex. bureau 0.30) consomme
    # majoritairement en HP → prix pondéré ~10-15 % au-dessus du baseload. Un
    # site flat (facteur 0.65+, logistique frigo) reste proche du baseload.
    # Multiplicateur MVP : `1 + peak_premium × (1 - facteur_forme)` avec
    # `peak_premium = 0.15` calibré sur spread HP/HC tertiaire 2024 (CRE T4).
    forward_y1, trace_fwd = _resolve_forward_y1(db, year, fallback_forward)
    if trace_fwd:
        traces.append(trace_fwd)
    peakload_multiplier = 1.0 + peak_premium_ratio * (1.0 - facteur_forme)
    fourniture_eur = annual_mwh * forward_y1 * peakload_multiplier

    # 4. TURPE 7 (part fixe + variable)
    # Part variable via ParameterStore (YAML aligné catalog sur ce code).
    turpe_energie_code = f"TURPE_ENERGIE_{turpe_segment}"
    turpe_energie_eur_kwh, fb_energie = _safe_param(store, turpe_energie_code, at_date, 0.0390)
    if fb_energie:
        traces.append("turpe_parameterstore_indisponible_fallback_default")

    turpe_variable_eur = annual_kwh * turpe_energie_eur_kwh
    # Part fixe complète = gestion + comptage + soutirage (puissance souscrite)
    # — valeurs CRE canoniques via TURPE_FIXE_PROFILES (pas YAML, divergent du
    # catalog sur `gestion_eur_mois`). L'ancien MVP (gestion seule via YAML)
    # sous-estimait la part fixe d'un facteur 8 sur C4_BT, faisant chuter la
    # CTA du même ratio (CTA = 15% × part fixe).
    turpe_profile = TURPE_FIXE_PROFILES.get(turpe_segment, TURPE_FIXE_PROFILES[DEFAULT_TURPE_SEGMENT])
    # P_souscrite estimée via le facteur de charge de l'archétype ; plancher
    # segment (9 kVA C5, 36 kVA C4, 250 kVA HTA) pour éviter un minimum
    # irréaliste sur un site à faible conso.
    p_souscrite_kva = max(
        turpe_profile["p_souscrite_min_kva"],
        annual_kwh / (8760.0 * max(facteur_forme, 0.15)),
    )
    turpe_gestion_annuel_eur = turpe_profile["gestion_eur_an"]
    turpe_gestion_eur_mois = turpe_gestion_annuel_eur / 12.0
    turpe_comptage_eur = turpe_profile["comptage_eur_an"]
    turpe_soutirage_eur = p_souscrite_kva * turpe_profile["soutirage_moyen_eur_kva_an"]
    turpe_fixe_eur = turpe_gestion_annuel_eur + turpe_comptage_eur + turpe_soutirage_eur
    turpe_eur = turpe_variable_eur + turpe_fixe_eur

    # 5. VNU — statut informatif uniquement, NE PAS additionner à la facture client
    # Correction post-audit Sprint Achat MVP (findings agents SDK) : le VNU est une
    # taxe redistributive SUR EDF (art. L. 336-1 Code énergie), pas sur le
    # consommateur final. L'additionner à la facture client comme auparavant
    # gonflait artificiellement le total de ~2 EUR/MWh quand "actif". On expose
    # désormais le statut + risque upside dans `hypotheses`, facture toujours = 0.
    vnu_seuil, vnu_source_ref, vnu_impact = _resolve_vnu_seuil()
    vnu_statut = "dormant" if forward_y1 < vnu_seuil else "actif"
    vnu_eur = 0.0
    vnu_risque_upside_eur_mwh = vnu_impact if vnu_statut == "actif" else 0.0

    # 6. Mécanisme capacité RTE — plein exercice annuel.
    # Cohérence avec `billing_engine/catalog.py` : le basculement mécanisme
    # décentralisé → acheteur unique centralisé (01/11/2026) conserve la même
    # valeur placeholder (CAPACITE_ELEC_NOV2026). Un acheteur en 2026 paie les
    # deux mécanismes sur leurs fenêtres respectives, les coûts sont amortis
    # sur l'année entière via le fournisseur (Jan-Oct) puis via RTE (Nov-Déc).
    capacite_eur = annual_mwh * CAPACITE_UNITAIRE_EUR_MWH

    # 7. CBAM — non applicable à la conso élec directe (documenté)
    cbam_scope = 0.0
    traces.append("cbam_non_applicable_conso_directe")

    # 8. Taxes : accise + CTA + TVA
    # Fix P0 audit post-Sprint : lire `tax_profile.accise_category_elec` (V113 TaxProfile)
    # depuis le premier DeliveryPoint du site si présent, router sur T1/T2/HP.
    # Fallback T2 (PME standard) sinon — préserve le comportement historique.
    accise_code = _resolve_accise_code(site)
    accise_eur_kwh, fb_accise = _safe_param(
        store,
        accise_code,
        at_date,
        0.02658,  # LFI 2026 fallback sur T2
    )
    cta_rate, _ = _safe_param(store, "CTA_ELEC_DIST_RATE", at_date, 0.15)
    tva_rate, _ = _safe_param(store, "TVA_NORMALE", at_date, 0.20)
    if fb_accise:
        traces.append("accise_parameterstore_indisponible_fallback_default")

    accise_eur = annual_kwh * accise_eur_kwh
    cta_eur = turpe_fixe_eur * cta_rate  # CTA = % du TURPE fixe HT
    # TVA 20% sur toutes composantes HT (post-01/08/2025 LFI 2025)
    base_tva = fourniture_eur + turpe_eur + vnu_eur + capacite_eur + accise_eur + cta_eur
    tva_eur = base_tva * tva_rate
    accise_cta_tva_eur = accise_eur + cta_eur + tva_eur

    # 9. Total
    composantes = {
        "fourniture_eur": round(fourniture_eur, 2),
        "turpe_eur": round(turpe_eur, 2),
        "vnu_eur": round(vnu_eur, 2),
        "capacite_eur": round(capacite_eur, 2),
        "cbam_scope": round(cbam_scope, 2),
        "accise_cta_tva_eur": round(accise_cta_tva_eur, 2),
    }
    facture_totale_eur = round(sum(composantes.values()), 2)

    # 10. Baseline 2024 + delta — comparaison apples-to-apples
    # Fix P1 audit : ancien code comparait `facture_totale` (TTC TURPE+taxes)
    # à `baseline_2024 = annual_mwh × 80` (HT énergie pure) → delta faussement
    # favorable de +30-40 pts. Désormais on compare l'énergie pure HT 2024 vs
    # 2026, plus pertinent pour un acheteur (ce qu'il peut influencer par son
    # choix de contrat). Les taxes/TURPE ne varient pas significativement.
    #
    # Le même peakload_multiplier est appliqué à la baseline 2024 : un site
    # peaky en 2024 subissait déjà la pointe HP/HC sur son complément spot,
    # donc comparer fourniture 2026 (profilée) à baseline 2024 flat donnerait
    # un delta archetype-biaisé trompeur. Avec le multiplier commun, le delta
    # isole le shift Post-ARENH (ARENH 42 × 50% + spot → forward 100%).
    baseline_2024_fourniture_eur = round(annual_mwh * baseline_eur_mwh * peakload_multiplier, 2)
    delta_fourniture_ht_pct = (
        round(
            (fourniture_eur - baseline_2024_fourniture_eur) / baseline_2024_fourniture_eur * 100.0,
            2,
        )
        if baseline_2024_fourniture_eur > 0
        else 0.0
    )
    # Delta "vs 2024" de l'API : désormais cadré HT énergie (comparable).
    delta_vs_2024_pct = delta_fourniture_ht_pct

    # 11. Hypothèses + traces
    hypotheses = {
        "prix_forward_y1_eur_mwh": round(forward_y1, 2),
        "facteur_forme": facteur_forme,
        "peakload_multiplier": round(peakload_multiplier, 4),
        "peak_premium_ratio": peak_premium_ratio,
        "capacite_unitaire_eur_mwh": CAPACITE_UNITAIRE_EUR_MWH,
        "capacite_source_ref": "billing_engine/catalog.py::CAPACITE_ELEC (0.43 EUR/MWh)",
        "vnu_statut": vnu_statut,
        "vnu_seuil_active_eur_mwh": vnu_seuil,
        "vnu_source_ref": vnu_source_ref,
        "vnu_note": (
            "VNU = taxe redistributive sur EDF (art. L. 336-1 Code énergie), "
            "pas sur le consommateur final. Facture client = 0, même si 'actif'."
        ),
        "vnu_risque_upside_eur_mwh": vnu_risque_upside_eur_mwh,
        "archetype": archetype,
        "turpe_segment": turpe_segment,
        "turpe_energie_eur_kwh": round(turpe_energie_eur_kwh, 5),
        "turpe_gestion_eur_mois": round(turpe_gestion_eur_mois, 2),
        "turpe_comptage_eur_an": round(turpe_comptage_eur, 2),
        "turpe_soutirage_eur_an": round(turpe_soutirage_eur, 2),
        "p_souscrite_kva_estimee": round(p_souscrite_kva, 1),
        "accise_code_resolu": accise_code,
        "accise_eur_kwh": round(accise_eur_kwh, 5),
        "cta_rate": cta_rate,
        "tva_rate": tva_rate,
        "baseline_2024_eur_mwh": baseline_eur_mwh,
        "comparabilite_baseline": (
            "delta_vs_2024_pct cadré HT énergie pure (fourniture uniquement), "
            "même peakload_multiplier appliqué aux deux côtés pour isoler le "
            "shift Post-ARENH (baseload 80 → forward Y+1). TURPE / accise / "
            "CTA / TVA absents du baseline pour éviter la comparaison TTC vs HT."
        ),
        "annual_kwh_resolu": annual_kwh,
        "cbam_note": "CBAM non applicable à la conso électrique directe (s'applique aux importations de biens carbonés, pas à l'acheminement). Inclus pour traçabilité auditeur.",
        "source_calibration": traces,
    }

    baseline_2024 = {
        "fourniture_ht_eur": baseline_2024_fourniture_eur,
        "prix_moyen_pondere_eur_mwh": baseline_eur_mwh,
        "methode": (
            "ARENH 42 EUR/MWh × 50 % + complément spot moyen 2024 pondéré "
            "par peakload_multiplier de l'archétype (simplification MVP). "
            "HT énergie uniquement pour comparaison apples-to-apples avec "
            "`composantes.fourniture_eur` 2026."
        ),
        "delta_fourniture_ht_pct": delta_fourniture_ht_pct,
    }

    return {
        "site_id": str(getattr(site, "id", "")),
        "year": year,
        "facture_totale_eur": facture_totale_eur,
        "energie_annuelle_mwh": round(annual_mwh, 3),
        "composantes": composantes,
        "hypotheses": hypotheses,
        "baseline_2024": baseline_2024,
        "delta_vs_2024_pct": delta_vs_2024_pct,
        "confiance": "indicative",
        "source": "Post-ARENH 01/01/2026 + TURPE 7 + VNU CRE + RTE mécanisme capacité PL-4/PL-1 Nov 2026",
    }
