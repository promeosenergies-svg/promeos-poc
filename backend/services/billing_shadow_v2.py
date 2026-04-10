"""
PROMEOS — Shadow Billing V2 (V68 → V111 regulated_tariffs bridge)
Décomposition 5 composantes : fourniture_ht, reseau_ht, taxes_ht, abonnement_ht, tva.

Architecture tarifs (ordre de priorité) :
1. regulated_tariffs (DB versionnée par date) — si db fourni
2. tarifs_reglementaires.yaml (YAML référentiel) — via tarif_loader
3. Constantes hardcodées à jour (dernier recours)

Sources réglementaires :
- TURPE 7 : CRE Délibération n°2025-78, depuis 1er août 2025
- CSPE : Loi de finances 2026 — 26.58 EUR/MWh PME (fév 2026+)
- CTA : 15% distribution depuis février 2026, 5% transport ≥50kV (CRE 2026-14)
- TVA : 20% uniforme depuis août 2025 (suppression 5.5% sur abo/CTA)

Relation avec price_decomposition_service.py :
- PriceDecompositionService = construire un prix théorique (simulation d'offres)
- shadow_billing_v2 = reconstituer une facture existante (audit)
- Les deux utilisent regulated_tariffs comme source de tarifs
"""

import logging
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

# ── Backward-compatible module-level constants (V68 tests import these) ──
# Values loaded from tarif_loader (YAML referentiel) with hardcoded last resort
try:
    from config.tarif_loader import (
        get_turpe_moyen_kwh as _turpe,
        get_atrd_kwh as _atrd,
        get_atrt_kwh as _atrt,
        get_accise_kwh as _accise,
        get_tva_normale as _tva,
    )

    TURPE_EUR_KWH_ELEC = _turpe("C5_BT")
    ATRD_EUR_KWH_GAZ = _atrd()
    ATRT_EUR_KWH_GAZ = _atrt()
    CSPE_EUR_KWH_ELEC = _accise("elec")
    TICGN_EUR_KWH_GAZ = _accise("gaz")
    TVA_RATE_20 = _tva()
except Exception:
    TURPE_EUR_KWH_ELEC = 0.0453
    ATRD_EUR_KWH_GAZ = 0.025
    ATRT_EUR_KWH_GAZ = 0.012
    CSPE_EUR_KWH_ELEC = 0.02658
    try:
        from services.billing_engine.catalog import get_rate
        from datetime import date as _d

        _ticgn_rate = get_rate("TICGN", _d.today())
        TICGN_EUR_KWH_GAZ = _ticgn_rate["rate"] if _ticgn_rate else 0.01073
    except Exception:
        TICGN_EUR_KWH_GAZ = 0.01073
    TVA_RATE_20 = 0.20


# ── Fallback from YAML referentiel (tarifs_reglementaires.yaml) ───────
def _load_fallback() -> dict:
    """Load fallback rates from YAML referentiel, with hardcoded last resort."""
    try:
        from config.tarif_loader import (
            get_turpe_moyen_kwh,
            get_turpe_gestion_mois,
            get_atrd_kwh,
            get_atrt_kwh,
            get_accise_kwh,
            get_tva_normale,
            get_tva_reduite,
            get_prix_reference,
        )

        result = {
            "ATRD_GAZ": get_atrd_kwh(),
            "ATRT_GAZ": get_atrt_kwh(),
            "ACCISE_ELEC": get_accise_kwh("elec"),
            "ACCISE_GAZ": get_accise_kwh("gaz"),
            "TVA_NORMALE": get_tva_normale(),
            "TVA_REDUITE": get_tva_reduite(),
            "DEFAULT_PRICE_ELEC": get_prix_reference("elec"),
            "DEFAULT_PRICE_GAZ": get_prix_reference("gaz"),
        }
        for seg in ("C5_BT", "C4_BT", "C3_HTA"):
            try:
                result[f"TURPE_ENERGIE_{seg}"] = get_turpe_moyen_kwh(seg)
                result[f"TURPE_GESTION_{seg}"] = get_turpe_gestion_mois(seg)
            except Exception:
                pass
        return result
    except Exception:
        # Dernier recours — valeurs TURPE 7 / CSPE 2026 / CTA 15% (CRE 2026-14)
        return {
            "TURPE_ENERGIE_C5_BT": 0.0453,
            "TURPE_GESTION_C5_BT": 18.48,
            "TURPE_ENERGIE_C4_BT": 0.0390,
            "TURPE_GESTION_C4_BT": 30.60,
            "TURPE_ENERGIE_C3_HTA": 0.0260,
            "TURPE_GESTION_C3_HTA": 58.44,
            "ATRD_GAZ": 0.025,
            "ATRT_GAZ": 0.012,
            "ACCISE_ELEC": 0.02658,
            "ACCISE_GAZ": 0.01637,
            "TVA_NORMALE": 0.20,
            "TVA_REDUITE": 0.20,  # Supprimée depuis août 2025 — TVA 20% uniforme
            "DEFAULT_PRICE_ELEC": 0.068,
            "DEFAULT_PRICE_GAZ": 0.045,
        }


_FALLBACK = _load_fallback()

# ── Mapping codes shadow → (TariffType, TariffComponent) pour la DB ──
_DB_TARIFF_MAP = {
    "TURPE_ENERGIE_C5_BT": ("TURPE", "TURPE_SOUTIRAGE_HPB"),  # weighted avg via _resolve_turpe_from_db
    "TURPE_ENERGIE_C4_BT": ("TURPE", "TURPE_SOUTIRAGE_HPB"),
    "TURPE_ENERGIE_C3_HTA": ("TURPE", "TURPE_SOUTIRAGE_HPB"),
    "ACCISE_ELEC": ("CSPE", "CSPE_C4"),
    "ACCISE_GAZ": None,  # Pas encore en DB
    "TVA_NORMALE": ("TVA", "TVA_NORMAL"),
    "TVA_REDUITE": ("TVA", "TVA_REDUIT"),
}


def _resolve_from_db(db, code: str, at_date=None) -> float | None:
    """Tente de résoudre un tarif depuis regulated_tariffs (DB versionnée)."""
    if db is None:
        return None
    try:
        from models.market_models import TariffType, TariffComponent
        from services.market_tariff_loader import get_current_tariff

        mapping = _DB_TARIFF_MAP.get(code)
        if mapping is None:
            return None

        tt = TariffType(mapping[0])
        tc = TariffComponent(mapping[1])

        if at_date and isinstance(at_date, date) and not isinstance(at_date, datetime):
            at_date = datetime(at_date.year, at_date.month, at_date.day, tzinfo=timezone.utc)

        tariff = get_current_tariff(db, tt, tc, at_date)
        if tariff is None:
            return None

        # Convertir EUR/MWh → EUR/kWh si nécessaire (DB stocke en EUR/MWh pour TURPE/CSPE)
        if tariff.unit in ("EUR_MWH", "EUR/MWh") and code.startswith(("TURPE_ENERGIE", "ACCISE")):
            return tariff.value / 1000.0
        # PCT → ratio pour TVA
        if tariff.unit == "PCT":
            return tariff.value / 100.0
        return tariff.value
    except Exception as e:
        logger.debug(f"DB tariff lookup failed for {code}: {e}")
        return None


def _resolve_turpe_from_db(db, segment: str, at_date=None) -> float | None:
    """Résout le TURPE énergie moyen pondéré depuis les composantes DB par segment."""
    if db is None:
        return None
    try:
        from models.market_models import TariffType, TariffComponent
        from services.market_tariff_loader import get_current_tariff

        if at_date and isinstance(at_date, date) and not isinstance(at_date, datetime):
            at_date = datetime(at_date.year, at_date.month, at_date.day, tzinfo=timezone.utc)

        # Pondérations type par segment (profil consommation simplifié)
        weights = {
            "C5_BT": {"HPB": 0.60, "HCB": 0.40},
            "C4_BT": {"HPH": 0.20, "HCH": 0.15, "HPB": 0.40, "HCB": 0.25},
            "C3_HTA": {"HPH": 0.18, "HCH": 0.12, "HPB": 0.42, "HCB": 0.28},
        }
        w = weights.get(segment, weights["C4_BT"])

        total = 0.0
        found_any = False
        for plage, weight in w.items():
            comp_name = f"TURPE_SOUTIRAGE_{plage}"
            tariff = get_current_tariff(db, TariffType.TURPE, TariffComponent(comp_name), at_date)
            if tariff:
                total += (tariff.value / 1000.0) * weight  # EUR/MWh → EUR/kWh
                found_any = True

        return total if found_any else None
    except Exception as e:
        logger.debug(f"TURPE DB weighted lookup failed: {e}")
        return None


def _safe_rate(code: str, at_date=None, db=None) -> float:
    """
    Résout un tarif : ParameterStore (DB → YAML versionné) → cascade legacy.

    Versioning temporel par `at_date`. Retour en EUR/kWh (ou ratio pour
    TVA/CTA). V112 : le chemin prioritaire est ParameterStore (source
    unique de vérité versionnée par date d'effet).

    Ordre de résolution :
    1. ParameterStore — DB regulated_tariffs → YAML tarifs_reglementaires
    2. Cascade legacy (rétrocompat) : regulated_tariffs direct → tax_catalog →
       _FALLBACK module-level
    """
    try:
        from services.billing_engine.parameter_store import ParameterStore, default_store

        store = default_store() if db is None else ParameterStore(db=db)
        res = store.get(code, at_date=at_date)
        if res.source in ("db", "yaml"):
            return res.value
    except Exception as exc:
        logger.debug("ParameterStore lookup failed for %s: %s", code, exc)

    # Legacy cascade — rétrocompat pour les codes non couverts par ParameterStore
    if db is not None:
        if code.startswith("TURPE_ENERGIE_"):
            segment = code.replace("TURPE_ENERGIE_", "")
            db_val = _resolve_turpe_from_db(db, segment, at_date)
            if db_val is not None:
                return db_val
        else:
            db_val = _resolve_from_db(db, code, at_date)
            if db_val is not None:
                return db_val

    try:
        from app.referential.tax_catalog_service import get_rate

        return get_rate(code, at_date)
    except Exception:
        pass

    return _FALLBACK.get(code, 0.0)


def _safe_trace(code: str, at_date=None) -> dict:
    """Get audit trace from catalog (returns {} on failure)."""
    try:
        from app.referential.tax_catalog_service import trace

        return trace(code, at_date)
    except Exception:
        return {}


def _has_db_tariffs(db) -> bool:
    """Vérifie si la DB contient des tarifs réglementés."""
    if db is None:
        return False
    try:
        from models.market_models import RegulatedTariff

        return db.query(RegulatedTariff).limit(1).first() is not None
    except Exception:
        return False


def shadow_billing_v2(invoice, lines: list, contract, db=None) -> dict:
    """
    Calcule la facture attendue sur 5 composantes avec TVA per-composante.

    Components:
      fourniture_ht : kwh x price_ref                       (TVA 20 %)
      reseau_ht     : kwh x TURPE énergie                   (TVA 20 %)
      taxes_ht      : kwh x accise                           (TVA 20 %)
      abonnement_ht : (TURPE gestion + fixed_fee) x prorata  (TVA 20 % depuis août 2025)

    Args:
        invoice:  EnergyInvoice (energy_kwh, total_eur, period_start, period_end)
        lines:    liste d'EnergyInvoiceLine (line_type, amount_eur)
        contract: EnergyContract ou None
        db:       Session SQLAlchemy (optionnel — active le bridge regulated_tariffs)

    Returns:
        dict avec expected_* + actual_* + delta_* + components[] + totals{} + meta
    """
    kwh = invoice.energy_kwh or 0.0
    is_elec = (contract.energy_type.value == "elec") if contract else True

    # Date de la facture pour le versionnement temporel des tarifs
    at_date = getattr(invoice, "period_start", None)

    # ── Reference price ──────────────────────────────────────────────
    has_contract_price = contract and contract.price_ref_eur_per_kwh
    price_ref = (
        contract.price_ref_eur_per_kwh
        if has_contract_price
        else _safe_rate("DEFAULT_PRICE_ELEC" if is_elec else "DEFAULT_PRICE_GAZ", at_date, db)
    )
    price_source = f"contract:{contract.id}" if has_contract_price else "catalog_default"

    # ── Prorata factor (days in period / 30) ─────────────────────────
    p_start = getattr(invoice, "period_start", None)
    p_end = getattr(invoice, "period_end", None)
    if p_start and p_end:
        days_in_period = max((p_end - p_start).days, 1)
    else:
        days_in_period = 30
    prorata_factor = days_in_period / 30.0

    # ── TVA rates ────────────────────────────────────────────────────
    tva_normal = _safe_rate("TVA_NORMALE", at_date, db)
    # TVA réduite supprimée depuis août 2025 — vérification temporelle
    tva_reduit = _safe_rate("TVA_REDUITE", at_date, db)
    # Post août 2025 : TVA uniforme 20% (suppression 5.5% sur abo/CTA)
    if at_date:
        ref_date = at_date if isinstance(at_date, date) else at_date.date() if hasattr(at_date, "date") else None
        if ref_date and ref_date >= date(2025, 8, 1):
            tva_reduit = tva_normal

    # ── Segment TURPE depuis puissance souscrite du contrat ──────────
    segment = _resolve_segment(contract)

    # ── Component rates (DB versionnée → YAML → hardcodé) ────────────
    if is_elec:
        turpe_energie = _safe_rate(f"TURPE_ENERGIE_{segment}", at_date, db)
        turpe_gestion = _safe_rate(f"TURPE_GESTION_{segment}", at_date, db)
        accise = _safe_rate("ACCISE_ELEC", at_date, db)
    else:
        turpe_energie = _safe_rate("ATRD_GAZ", at_date, db) + _safe_rate("ATRT_GAZ", at_date, db)
        turpe_gestion = 0.0
        accise = _safe_rate("ACCISE_GAZ", at_date, db)

    # ── Expected HT components ───────────────────────────────────────
    exp_fourniture = kwh * price_ref
    exp_reseau = kwh * turpe_energie
    exp_taxes = kwh * accise

    # Abonnement: TURPE gestion (monthly, prorated) + contract fixed fee
    fixed_fee = getattr(contract, "fixed_fee_eur_per_month", None) or 0
    exp_abo = (turpe_gestion + fixed_fee) * prorata_factor

    # ── TVA per-component ────────────────────────────────────────────
    tva_fourniture = exp_fourniture * tva_normal
    tva_reseau = exp_reseau * tva_normal
    tva_taxes = exp_taxes * tva_normal
    tva_abo = exp_abo * tva_reduit

    exp_tva = tva_fourniture + tva_reseau + tva_taxes + tva_abo
    exp_ht = exp_fourniture + exp_reseau + exp_taxes + exp_abo
    exp_ttc = exp_ht + exp_tva

    # ── Actual (from invoice lines) ──────────────────────────────────
    act_fourniture = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "energy")
    act_reseau = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "network")
    act_taxes = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "tax")
    act_ttc = invoice.total_eur or 0.0

    # ── Deltas ───────────────────────────────────────────────────────
    delta_fourniture = act_fourniture - exp_fourniture
    delta_reseau = act_reseau - exp_reseau
    delta_taxes = act_taxes - exp_taxes
    delta_ttc = act_ttc - exp_ttc
    delta_pct = (delta_ttc / exp_ttc * 100) if exp_ttc else 0.0

    # ── Tariff source traceability ───────────────────────────────────
    tariff_source = "regulated_tariffs" if _has_db_tariffs(db) else "fallback"

    # ── Structured breakdown ─────────────────────────────────────────
    components = [
        {
            "code": "fourniture",
            "label": "Fourniture d'énergie",
            "ht": round(exp_fourniture, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_fourniture, 2),
            "ttc": round(exp_fourniture + tva_fourniture, 2),
            "qty": kwh,
            "unit_rate": round(price_ref, 4),
            "unit": "EUR/kWh",
            "source": price_source,
        },
        {
            "code": "reseau",
            "label": "Réseau (TURPE)" if is_elec else "Réseau (ATRD+ATRT)",
            "ht": round(exp_reseau, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_reseau, 2),
            "ttc": round(exp_reseau + tva_reseau, 2),
            "qty": kwh,
            "unit_rate": round(turpe_energie, 4),
            "unit": "EUR/kWh",
        },
        {
            "code": "taxes",
            "label": "Accise électricité (TIEE)" if is_elec else "Accise gaz (TICGN)",
            "ht": round(exp_taxes, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_taxes, 2),
            "ttc": round(exp_taxes + tva_taxes, 2),
            "qty": kwh,
            "unit_rate": round(accise, 4),
            "unit": "EUR/kWh",
        },
        {
            "code": "abonnement",
            "label": "Abonnement & gestion",
            "ht": round(exp_abo, 2),
            "tva_rate": tva_reduit,
            "tva": round(tva_abo, 2),
            "ttc": round(exp_abo + tva_abo, 2),
            "qty": round(prorata_factor, 4),
            "unit_rate": round(turpe_gestion + fixed_fee, 2),
            "unit": "EUR/mois",
        },
    ]

    totals = {
        "ht": round(exp_ht, 2),
        "tva": round(exp_tva, 2),
        "ttc": round(exp_ttc, 2),
    }

    # ── Catalog audit trace ────────────────────────────────────────────
    catalog_trace = [
        _safe_trace(f"TURPE_ENERGIE_{segment}" if is_elec else "ATRD_GAZ", at_date),
        _safe_trace("ACCISE_ELEC" if is_elec else "ACCISE_GAZ", at_date),
        _safe_trace("TVA_NORMALE", at_date),
        _safe_trace("TVA_REDUITE", at_date),
    ]
    if is_elec:
        catalog_trace.append(_safe_trace(f"TURPE_GESTION_{segment}", at_date))
    catalog_trace = [t for t in catalog_trace if t]

    # ── Diagnostics ─────────────────────────────────────────────────
    has_lines = len(lines) > 0
    line_types = {l.line_type.value for l in lines} if has_lines else set()
    missing_fields = []
    if exp_reseau > 0 and act_reseau == 0 and "network" not in line_types:
        missing_fields.append("network_lines")
    if exp_taxes > 0 and act_taxes == 0 and "tax" not in line_types:
        missing_fields.append("tax_lines")
    if act_fourniture == 0 and "energy" not in line_types and has_lines:
        missing_fields.append("energy_lines")

    assumptions = []
    if has_contract_price:
        cid = getattr(contract, "id", "?")
        assumptions.append(f"Prix fourniture : contrat #{cid}")
    else:
        assumptions.append("Prix fourniture : référentiel PROMEOS (pas de contrat)")
    if is_elec:
        assumptions.append(f"Réseau : TURPE {segment} (profil simplifié)")
    else:
        assumptions.append("Réseau : ATRD+ATRT (profil simplifié)")
    assumptions.append(f"Source tarifs : {tariff_source}")

    if has_contract_price and has_lines and len(line_types) >= 2:
        confidence = "medium"
    elif has_contract_price or (has_lines and len(line_types) >= 2):
        confidence = "medium"
    else:
        confidence = "low"

    diagnostics = {
        "missing_fields": missing_fields,
        "assumptions": assumptions,
        "confidence": confidence,
    }

    # ── Calc version tag (V112) ──────────────────────────────────────
    calc_version = "v2_parameter_store"

    # ── Backward-compatible flat fields + structured breakdown ───────
    return {
        # Flat fields (backward compat for R13/R14)
        "expected_fourniture_ht": round(exp_fourniture, 2),
        "expected_reseau_ht": round(exp_reseau, 2),
        "expected_taxes_ht": round(exp_taxes, 2),
        "expected_abo_ht": round(exp_abo, 2),
        "expected_tva": round(exp_tva, 2),
        "expected_ttc": round(exp_ttc, 2),
        "actual_fourniture_ht": round(act_fourniture, 2),
        "actual_reseau_ht": round(act_reseau, 2),
        "actual_taxes_ht": round(act_taxes, 2),
        "actual_ttc": round(act_ttc, 2),
        "delta_fourniture": round(delta_fourniture, 2),
        "delta_reseau": round(delta_reseau, 2),
        "delta_taxes": round(delta_taxes, 2),
        "delta_ttc": round(delta_ttc, 2),
        "delta_pct": round(delta_pct, 2),
        # Meta
        "energy_type": "ELEC" if is_elec else "GAZ",
        "kwh": kwh,
        "price_ref": round(price_ref, 4),
        "prorata_factor": round(prorata_factor, 4),
        "days_in_period": days_in_period,
        "method": "shadow_v2_catalog",
        "segment": segment,
        "price_source": price_source,
        "tariff_source": tariff_source,
        "calc_version": calc_version,
        # Structured (new)
        "components": components,
        "totals": totals,
        # Phase 2: audit trail + diagnostics
        "catalog_trace": catalog_trace,
        "diagnostics": diagnostics,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Step 28 — Shadow Breakdown par composante (fourniture / TURPE / taxes / TVA)
# ══════════════════════════════════════════════════════════════════════════════


def _resolve_segment(contract, site=None) -> str:
    """Résout le segment TURPE depuis la puissance souscrite du contrat/site."""
    kva = getattr(contract, "subscribed_power_kva", None) or 0
    if kva > 250:
        return "C3_HTA"
    elif kva > 36:
        return "C4_BT"
    return "C5_BT"


def _component_status(gap_pct):
    """Statut d'une composante selon l'écart en %."""
    if gap_pct is None:
        return "ok"
    if abs(gap_pct) > 15:
        return "alert"
    if abs(gap_pct) > 5:
        return "warn"
    return "ok"


def _build_breakdown_component(
    name,
    label,
    expected,
    invoice_val,
    methodology,
    detail,
    *,
    status_override=None,
    status_message=None,
    formula=None,
    source_ref=None,
    prorata_display=None,
):
    """Construit un composant de breakdown avec gap, statut et métadonnées enrichies."""
    if expected is None:
        return {
            "name": name,
            "label": label,
            "expected_eur": None,
            "invoice_eur": round(invoice_val, 2) if invoice_val is not None else None,
            "gap_eur": None,
            "gap_pct": None,
            "status": status_override or "missing_price",
            "status_message": status_message or "Prix non disponible — contrat ou catalogue requis",
            "methodology": methodology,
            "detail": detail,
            "formula": formula,
            "source_ref": source_ref,
            "prorata_display": prorata_display,
        }
    gap = (invoice_val - expected) if invoice_val is not None else None
    gap_pct = (gap / expected * 100) if gap is not None and expected > 0 else None
    if status_override:
        computed_status = status_override
    elif invoice_val is None:
        computed_status = "missing_invoice_detail"
    else:
        computed_status = _component_status(gap_pct)
    return {
        "name": name,
        "label": label,
        "expected_eur": round(expected, 2),
        "invoice_eur": round(invoice_val, 2) if invoice_val is not None else None,
        "gap_eur": round(gap, 2) if gap is not None else None,
        "gap_pct": round(gap_pct, 1) if gap_pct is not None else None,
        "status": computed_status,
        "status_message": status_message,
        "methodology": methodology,
        "detail": detail,
        "formula": formula,
        "source_ref": source_ref,
        "prorata_display": prorata_display,
    }


def _extract_invoice_component(lines, component_name):
    """Extrait un montant depuis les InvoiceLines par type/label."""
    if not lines:
        return None
    mapping = {
        "fourniture": ["energy"],
        "turpe": ["network"],
        "taxes": ["tax"],
        "abonnement": ["other"],
    }
    # "abonnement" uses line_type=other which is shared with TVA lines,
    # so we filter by label keywords to avoid including TVA.
    _label_filter = {
        "abonnement": ["abonnement", "souscription", "subscription", "gestion"],
    }
    line_types = mapping.get(component_name, [])
    labels_required = _label_filter.get(component_name)
    total = 0
    found = False
    for line in lines:
        lt = getattr(line, "line_type", None)
        lt_val = lt.value if hasattr(lt, "value") else str(lt or "")
        if lt_val in line_types:
            if labels_required:
                line_label = (getattr(line, "label", "") or "").lower()
                if not any(kw in line_label for kw in labels_required):
                    continue
            total += getattr(line, "amount_eur", 0) or 0
            found = True
    return total if found else None


def _extract_pdl_prm(invoice, site=None) -> str | None:
    """Extrait le PDL/PRM depuis raw_json ou le site."""
    import json as _json

    raw = getattr(invoice, "raw_json", None)
    if raw:
        try:
            data = _json.loads(raw)
            prm = data.get("pdl_prm") or data.get("pdl") or data.get("prm")
            if prm:
                return str(prm)
        except Exception:
            pass
    if site:
        prm = getattr(site, "pdl", None) or getattr(site, "prm", None) or getattr(site, "pdl_prm", None)
        if prm:
            return str(prm)
    return None


def _compute_reconstitution_meta(components: list) -> dict:
    """Calcule le statut de reconstitution et le niveau de confiance."""
    total = len(components)
    missing_price = [c for c in components if c.get("status") == "missing_price"]
    missing_labels = [c["label"] for c in missing_price]
    total_facture = sum(c.get("invoice_eur") or 0 for c in components)
    missing_facture = sum(c.get("invoice_eur") or 0 for c in missing_price)
    missing_pct_value = (
        (missing_facture / total_facture * 100) if total_facture > 0 else (len(missing_price) / max(total, 1) * 100)
    )
    if len(missing_price) == 0:
        reconstitution_status = "complete"
        reconstitution_label = "Reconstitution complète"
    elif missing_pct_value > 50:
        reconstitution_status = "minimal"
        reconstitution_label = (
            f"Reconstitution minimale — {len(missing_price)}/{total} composantes "
            f"non reconstituables ({missing_pct_value:.0f}% du montant)"
        )
    else:
        reconstitution_status = "partial"
        s = "s" if len(missing_price) > 1 else ""
        reconstitution_label = f"Reconstitution partielle — {len(missing_price)} composante{s} non reconstituable{s}"

    if len(missing_price) == 0:
        confidence = "elevee"
    elif missing_pct_value <= 15:
        confidence = "moyenne"
    elif missing_pct_value <= 50:
        confidence = "faible"
    else:
        confidence = "tres_faible"

    confidence_label_map = {"elevee": "Élevée", "moyenne": "Moyenne", "faible": "Faible", "tres_faible": "Très faible"}
    rationale_map = {
        "elevee": "Toutes les composantes sont reconstituées avec des tarifs sourcés",
        "moyenne": f"{len(missing_price)} composante(s) manquante(s) représentant {missing_pct_value:.0f}% du montant",
        "faible": f"{len(missing_price)} composante(s) manquante(s) représentant {missing_pct_value:.0f}% du montant — résultat peu fiable",
        "tres_faible": f"La majorité du montant ({missing_pct_value:.0f}%) n'est pas reconstituable — résultat non exploitable",
    }
    return {
        "reconstitution_status": reconstitution_status,
        "reconstitution_label": reconstitution_label,
        "missing_components": missing_labels,
        "confidence": confidence,
        "confidence_label": confidence_label_map[confidence],
        "confidence_rationale": rationale_map[confidence],
    }


def compute_shadow_breakdown(db, invoice, site=None, contract=None) -> dict:
    """
    Calcul shadow décomposé par composante avec écart et statut.
    Enrichit shadow_billing_v2 avec CTA, segment dynamique, et comparaison
    par composante (fourniture / TURPE / taxes / TVA).

    Args:
        db: session SQLAlchemy
        invoice: EnergyInvoice
        site: Site (optionnel)
        contract: EnergyContract (optionnel, résolu depuis invoice si absent)

    Returns:
        dict avec components[], total_*, confidence, tarif_version, segment
    """
    from config.tarif_loader import get_tarif_version
    from services.billing_engine.bricks.cta import compute_cta
    from services.billing_engine.parameter_store import ParameterStore, default_store

    # Résoudre contrat si non fourni
    if contract is None and invoice.contract_id:
        try:
            from models.billing_models import EnergyContract

            contract = db.query(EnergyContract).filter(EnergyContract.id == invoice.contract_id).first()
        except Exception:
            pass

    # Résoudre site si non fourni
    if site is None and invoice.site_id:
        try:
            from models.energy_models import Site

            site = db.query(Site).filter(Site.id == invoice.site_id).first()
        except Exception:
            pass

    # Lignes de la facture
    try:
        from models.billing_models import EnergyInvoiceLine

        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == invoice.id).all()
    except Exception:
        lines = []

    # Appeler shadow_billing_v2 pour le calcul de base (avec bridge DB)
    v2 = shadow_billing_v2(invoice, lines, contract, db=db)

    # Segment TURPE dynamique
    segment = _resolve_segment(contract, site)
    is_elec = v2["energy_type"] == "ELEC"

    # ── Enrichir avec CTA ──────────────────────────────────────────────
    kwh = v2["kwh"]
    turpe_gestion = _safe_rate(f"TURPE_GESTION_{segment}") if is_elec else 0
    p_start = getattr(invoice, "period_start", None)
    p_end = getattr(invoice, "period_end", None)
    if p_start and p_end:
        period_days = max((p_end - p_start).days, 1)
    else:
        period_days = 30
    prorata = period_days / 365.0

    # ── CTA : calcul réel via brique dédiée (V112) ────────────────────
    # Assiette = part fixe annuelle (TURPE gestion mensuel × 12 pour élec).
    # Le prorata sur 365 jours est appliqué dans compute_cta.
    _at_date = p_start or date.today()
    _cta_store = default_store() if db is None else ParameterStore(db=db)
    _cta_annual_fixed = (turpe_gestion * 12.0) if is_elec else 0.0
    _cta_result = compute_cta(
        store=_cta_store,
        energy="elec" if is_elec else "gaz",
        network_level="distribution",
        fixed_component_annual_eur=_cta_annual_fixed,
        period_days=period_days,
        at_date=_at_date,
    )
    cta_taux = _cta_result.rate
    cta_eur = _cta_result.amount_ht

    # Accise
    accise_rate = v2["components"][2]["unit_rate"]  # taxes component rate
    taxes_energy = kwh * accise_rate
    taxes_expected = taxes_energy + cta_eur

    # ── Extraire montants facturés par composante ──────────────────────
    fourniture_invoice = _extract_invoice_component(lines, "fourniture")
    turpe_invoice = _extract_invoice_component(lines, "turpe")
    taxes_invoice = _extract_invoice_component(lines, "taxes")
    abonnement_invoice = _extract_invoice_component(lines, "abonnement")

    # TVA : différence TTC - HT si on a le TTC
    exp_ht = v2["totals"]["ht"]
    exp_tva = v2["totals"]["tva"]
    act_ttc = v2["actual_ttc"]
    act_ht_sum = sum(x for x in [fourniture_invoice, turpe_invoice, taxes_invoice, abonnement_invoice] if x is not None)
    tva_invoice = (act_ttc - act_ht_sum) if act_ttc and act_ht_sum > 0 else None

    # ── Identification facture (P0.1) ────────────────────────────────
    supplier_name = getattr(contract, "supplier_name", None) if contract else None
    puissance_kva = getattr(contract, "subscribed_power_kva", None) if contract else None
    pdl_prm = _extract_pdl_prm(invoice, site)
    site_name = getattr(site, "nom", None) or getattr(site, "name", None) if site else None

    # ── Construire les composantes avec gap/status ─────────────────────
    price_ref = v2["price_ref"]
    price_source = v2["price_source"]
    taxe_label = "Accise élec" if is_elec else "TICGN"
    fourniture_is_missing = price_source == "catalog_default"

    # Abonnement prorata lisible (P1.3)
    fixed_fee = getattr(contract, "fixed_fee_eur_per_month", None) or 0
    abo_monthly = turpe_gestion + fixed_fee
    abo_expected = v2["expected_abo_ht"]
    abo_formula = f"{abo_monthly:.2f} €/mois × {period_days}/365 jours = {abo_expected:.2f} € HT"

    components = [
        _build_breakdown_component(
            "fourniture",
            "Fourniture d'énergie",
            None if fourniture_is_missing else v2["expected_fourniture_ht"],
            fourniture_invoice,
            f"{kwh:.0f} kWh × {price_ref:.4f} EUR/kWh",
            {"kwh": kwh, "price_kwh": price_ref, "source": price_source},
            status_override="missing_price" if fourniture_is_missing else None,
            status_message="Prix de fourniture non disponible — contrat ou offre requis"
            if fourniture_is_missing
            else None,
            formula=None
            if fourniture_is_missing
            else f"{kwh:,.0f} kWh × {price_ref:.4f} €/kWh = {v2['expected_fourniture_ht']:,.2f} € HT".replace(",", " "),
            source_ref=f"Contrat #{contract.id}" if contract and not fourniture_is_missing else None,
        ),
        _build_breakdown_component(
            "turpe",
            "Acheminement (TURPE)",
            v2["expected_reseau_ht"],
            turpe_invoice,
            f"Segment {segment} — {v2['components'][1]['unit_rate']:.4f} EUR/kWh",
            {"segment": segment, "rate_kwh": v2["components"][1]["unit_rate"]},
            formula=f"{kwh:,.0f} kWh × {v2['components'][1]['unit_rate']:.4f} €/kWh = {v2['expected_reseau_ht']:,.2f} € HT".replace(
                ",", " "
            ),
            source_ref=f"CRE TURPE 7 {segment}",
        ),
        _build_breakdown_component(
            "taxes",
            f"Taxes ({taxe_label} + CTA)",
            round(taxes_expected, 2),
            taxes_invoice,
            f"{taxe_label}: {kwh:.0f} kWh × {accise_rate:.5f} EUR/kWh + CTA: {cta_eur:.2f} EUR",
            {"taxe_energy": round(taxes_energy, 2), "cta": round(cta_eur, 2), "cta_taux_pct": round(cta_taux * 100, 2)},
            formula=f"{taxe_label}: {kwh:,.0f} kWh × {accise_rate:.5f} €/kWh = {taxes_energy:,.2f} € + CTA: {cta_eur:,.2f} € = {taxes_expected:,.2f} € HT".replace(
                ",", " "
            ),
            source_ref="Loi de finances 2026 (accise) + CRE (CTA)",
        ),
        _build_breakdown_component(
            "tva",
            "TVA",
            exp_tva,
            tva_invoice,
            "TVA 20% uniforme (depuis août 2025)",
            {
                "tva_reduit": round(v2["components"][3]["tva"], 2),
                "tva_normal": round(exp_tva - v2["components"][3]["tva"], 2),
            },
            status_message="TVA non détaillée sur cette facture" if tva_invoice is None and act_ttc else None,
            formula=f"TVA 20% sur {exp_ht:,.2f} € HT = {exp_tva:,.2f} €".replace(",", " "),
        ),
        _build_breakdown_component(
            "abonnement",
            "Abonnement & gestion",
            abo_expected,
            abonnement_invoice,
            "TURPE gestion + abonnement proratisé",
            {"turpe_gestion": turpe_gestion, "fixed_fee": fixed_fee},
            formula=abo_formula,
            source_ref=f"CRE TURPE 7 gestion {segment}",
            prorata_display=f"{period_days}/365 jours",
        ),
    ]

    # CEE implicite (P1.4) — informatif si ELEC
    if is_elec:
        cee_rate = 0.005
        cee_estimate = kwh * cee_rate
        components.append(
            _build_breakdown_component(
                "cee_implicite",
                "CEE (coût implicite, inclus dans fourniture)",
                None,
                None,
                "Estimation PROMEOS du coût CEE implicite",
                {"cee_rate": cee_rate, "kwh": kwh},
                status_override="informational",
                status_message=f"Estimé à {cee_estimate:,.2f} € — inclus dans le prix de fourniture, non facturé séparément".replace(
                    ",", " "
                ),
                formula=f"{kwh:,.0f} kWh × {cee_rate} €/kWh = {cee_estimate:,.2f} € (estimation PROMEOS)".replace(
                    ",", " "
                ),
                source_ref="CEE P5 implicite ~5 €/MWh",
            )
        )

    # Reconstitution meta (P0.3/P0.4)
    recon_meta = _compute_reconstitution_meta(components)
    total_expected_ht_r = sum(
        c["expected_eur"] for c in components if c["expected_eur"] is not None and c.get("status") != "informational"
    )
    total_invoice_ht = act_ht_sum if act_ht_sum > 0 else (act_ttc or 0)
    hypotheses = list(v2["diagnostics"].get("assumptions", []))

    try:
        tarif_version = get_tarif_version()
    except Exception:
        tarif_version = "unknown"

    tariff_source = v2.get("tariff_source", "fallback")

    return {
        # IDENTIFICATION FACTURE (P0.1)
        "invoice_id": invoice.id,
        "invoice_number": getattr(invoice, "invoice_number", None),
        "period_start": str(p_start) if p_start else None,
        "period_end": str(p_end) if p_end else None,
        "period_days": period_days,
        "pdl_prm": pdl_prm,
        "supplier": supplier_name,
        "segment": segment,
        "puissance_kva": puissance_kva,
        "kwh_total": kwh,
        "energy_type": v2["energy_type"],
        "site_name": site_name,
        # RECONSTITUTION META (P0.3/P0.4)
        "reconstitution_status": recon_meta["reconstitution_status"],
        "reconstitution_label": recon_meta["reconstitution_label"],
        "missing_components": recon_meta["missing_components"],
        "confidence": recon_meta["confidence"],
        "confidence_label": recon_meta["confidence_label"],
        "confidence_rationale": recon_meta["confidence_rationale"],
        # TOTAUX
        "total_expected_ht": round(total_expected_ht_r, 2),
        "total_expected_ht_label": f"{total_expected_ht_r:,.2f} € HT".replace(",", " ")
        if recon_meta["reconstitution_status"] == "complete"
        else f"{total_expected_ht_r:,.2f} € HT (partiel)".replace(",", " "),
        "total_expected_ttc": round(v2["expected_ttc"], 2),
        "total_invoice_ht": round(total_invoice_ht, 2),
        "total_invoice_ttc": round(act_ttc, 2) if act_ttc else None,
        "total_gap_eur": round(total_invoice_ht - total_expected_ht_r, 2)
        if recon_meta["reconstitution_status"] == "complete"
        else None,
        "total_gap_pct": round((total_invoice_ht - total_expected_ht_r) / total_expected_ht_r * 100, 2)
        if recon_meta["reconstitution_status"] == "complete" and total_expected_ht_r > 0
        else None,
        "total_gap_label": "Non calculable — reconstitution partielle"
        if recon_meta["reconstitution_status"] != "complete"
        else None,
        # COMPOSANTES + META
        "components": components,
        "hypotheses": hypotheses,
        "expert": {
            "engine": "shadow_billing_v1",
            "catalog": tarif_version,
            "segment": segment,
            "method": v2.get("method", "shadow_v2_catalog"),
            "prix_ref_kwh": price_ref,
            "source_prix": price_source,
            "tariff_source": tariff_source,
        },
        # BENCHMARK ANALYSIS (IPE réel vs ADEME)
        "benchmark_analysis": _compute_benchmark_for_shadow(site, kwh, price_ref, period_days),
        # BACKWARD COMPAT
        "tarif_version": tarif_version,
        "kwh": kwh,
        "days_in_period": period_days,
        "tariff_source": tariff_source,
    }


def _compute_benchmark_for_shadow(site, kwh, price_ref, period_days):
    """Injecte l'analyse benchmark dans le shadow billing."""
    if not site:
        return None
    surface = getattr(site, "surface_m2", 0) or 0
    type_site = getattr(site, "type", "bureau")
    if hasattr(type_site, "value"):
        type_site = type_site.value
    if surface <= 0 or kwh <= 0:
        return None
    # Toujours annualiser (gère année bissextile et factures multi-périodes)
    annual_kwh = kwh * 365 / max(period_days, 1) if period_days and period_days != 365 else kwh
    try:
        from services.benchmark_analysis import compute_benchmark_analysis

        return compute_benchmark_analysis(type_site, surface, annual_kwh, price_ref)
    except Exception:
        return None
