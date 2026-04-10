"""
PROMEOS — Service Contrats V2 (Cadre + Annexes).
CRUD + heritage + coherence + KPIs + import CSV.
"""

import csv
import io
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from models.billing_models import EnergyContract
from models.contract_v2_models import (
    ContractAnnexe,
    ContractEvent,
    ContractPricing,
    ContratCadre,
    VolumeCommitment,
)
from models.enums import BillingEnergyType, ContractStatus
from schemas.contract_v2_schemas import (
    AnnexeCreateSchema,
    AnnexeUpdateSchema,
    CadreCreateSchema,
    CadreUpdateSchema,
    PricingLineSchema,
)
from services.contrat_coherence import (
    resolve_pricing,
    validate_contrat as coherence_check,
)

logger = logging.getLogger(__name__)

# Poids typiques par poste tarifaire (source: profils Enedis C5/C4)
# Utilises pour le prix moyen pondere dans les KPIs cadre.
PERIOD_WEIGHTS = {
    "BASE": 1.0,
    "HP": 0.62,
    "HC": 0.38,
    "HPH": 0.25,
    "HCH": 0.15,
    "HPB": 0.37,
    "HCB": 0.23,
    "POINTE": 0.02,
}

# Classification des lignes de facture B2B par composante
SUPPLY_TYPES = frozenset({"SUPPLY", "ENERGY", "FOURNITURE"})
NETWORK_TYPES = frozenset({"NETWORK", "TURPE", "ACHEMINEMENT", "TRANSPORT"})
TAX_TYPES = frozenset({"TAX", "ACCISE", "CTA", "CSPE", "TVA", "CAPACITY"})


# ============================================================
# CRUD CADRE
# ============================================================


def list_cadres(
    db: Session,
    org_id: int,
    *,
    status: Optional[str] = None,
    energy_type: Optional[str] = None,
    supplier: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Liste contrats cadre + annexes avec KPIs, union V2 ContratCadre + legacy EnergyContract."""
    from models import EntiteJuridique

    results: List[Dict[str, Any]] = []

    # ── V2: ContratCadre (nouveau data model, Phase 1) ──────────────
    v2_q = (
        db.query(ContratCadre)
        .options(
            joinedload(ContratCadre.annexes).joinedload(ContractAnnexe.site),
            joinedload(ContratCadre.annexes).joinedload(ContractAnnexe.volume_commitment),
        )
        .filter(ContratCadre.org_id == org_id)
        .filter(ContratCadre.deleted_at.is_(None))
    )
    if status:
        try:
            v2_q = v2_q.filter(ContratCadre.statut == ContractStatus(status.upper()))
        except ValueError:
            pass
    if energy_type:
        try:
            v2_q = v2_q.filter(ContratCadre.energie == BillingEnergyType(energy_type))
        except ValueError:
            pass
    if supplier:
        v2_q = v2_q.filter(ContratCadre.fournisseur.ilike(f"%{supplier}%"))
    if search:
        pattern = f"%{search}%"
        v2_q = v2_q.filter(
            ContratCadre.fournisseur.ilike(pattern)
            | ContratCadre.reference_fournisseur.ilike(pattern)
            | ContratCadre.reference.ilike(pattern)
            | ContratCadre.notes.ilike(pattern)
        )
    results.extend(_serialize_v2_cadre(c) for c in v2_q.all())

    # ── Legacy: EnergyContract.is_cadre (backward compat) ───────────
    legacy_q = (
        db.query(EnergyContract)
        .options(
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.site),
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.volume_commitment),
            joinedload(EnergyContract.pricing_lines),
        )
        .filter(EnergyContract.is_cadre == True)  # noqa: E712
    )
    ej_ids = [ej.id for ej in db.query(EntiteJuridique.id).filter(EntiteJuridique.organisation_id == org_id).all()]
    if ej_ids:
        legacy_q = legacy_q.filter(EnergyContract.entite_juridique_id.in_(ej_ids))
    if status:
        legacy_q = legacy_q.filter(EnergyContract.contract_status == status)
    if energy_type:
        legacy_q = legacy_q.filter(EnergyContract.energy_type == energy_type)
    if supplier:
        legacy_q = legacy_q.filter(EnergyContract.supplier_name.ilike(f"%{supplier}%"))
    if search:
        pattern = f"%{search}%"
        legacy_q = legacy_q.filter(
            EnergyContract.supplier_name.ilike(pattern)
            | EnergyContract.reference_fournisseur.ilike(pattern)
            | EnergyContract.notes.ilike(pattern)
        )
    results.extend(_serialize_cadre(c) for c in legacy_q.all())

    return results


def get_cadre(
    db: Session,
    cadre_id: int,
    *,
    source: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Cadre complet + annexes + pricing + events.

    Tries V2 ContratCadre first (Phase 1), falls back to legacy EnergyContract.
    Pass source="v2" or source="legacy" to force a specific table when IDs
    collide between the two tables.
    """
    # ── V2 ContratCadre (nouveau data model, Phase 1) ────────────────
    if source in (None, "v2"):
        v2 = (
            db.query(ContratCadre)
            .options(
                joinedload(ContratCadre.annexes).joinedload(ContractAnnexe.site),
                joinedload(ContratCadre.annexes).joinedload(ContractAnnexe.volume_commitment),
                joinedload(ContratCadre.annexes).joinedload(ContractAnnexe.pricing_overrides),
            )
            .filter(ContratCadre.id == cadre_id, ContratCadre.deleted_at.is_(None))
            .first()
        )
        if v2:
            result = _serialize_v2_cadre(v2)
            result["events"] = []  # V2 ContratCadre has no events relationship yet
            result["coherence"] = []  # coherence_check expects legacy EnergyContract
            return result
        if source == "v2":
            return None

    # ── Legacy EnergyContract.is_cadre=True ──────────────────────────
    c = (
        db.query(EnergyContract)
        .options(
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.site),
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.volume_commitment),
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.pricing_overrides),
            joinedload(EnergyContract.pricing_lines),
            joinedload(EnergyContract.events),
        )
        .filter(EnergyContract.id == cadre_id, EnergyContract.is_cadre == True)  # noqa: E712
        .first()
    )
    if not c:
        return None
    result = _serialize_cadre(c)
    result["events"] = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_date": str(e.event_date) if e.event_date else None,
            "description": e.description,
        }
        for e in sorted(c.events, key=lambda x: x.event_date or date.min)
    ]
    result["coherence"] = coherence_check(db, cadre_id)
    return result


def create_cadre(db: Session, data: CadreCreateSchema) -> Dict[str, Any]:
    """Cree cadre + N annexes + pricing + events CREATION auto."""
    # Determine site_id reference (1er annexe)
    ref_site_id = data.annexes[0].site_id

    contract = EnergyContract(
        site_id=ref_site_id,
        energy_type=BillingEnergyType(data.energy_type),
        supplier_name=data.supplier_name,
        start_date=data.start_date,
        end_date=data.end_date,
        reference_fournisseur=data.contract_ref,
        auto_renew=data.tacit_renewal,
        notice_period_days=data.notice_period_months * 30,
        offer_indexation=data.pricing_model,
        contract_status=ContractStatus.ACTIVE
        if data.start_date <= date.today() <= data.end_date
        else ContractStatus.DRAFT,
        is_cadre=True,
        contract_type=data.contract_type,
        entite_juridique_id=data.entite_juridique_id,
        notice_period_months=data.notice_period_months,
        is_green=data.is_green,
        green_percentage=data.green_percentage,
        segment_enedis=data.segment_enedis,
        annual_consumption_kwh=data.annual_consumption_kwh,
        indexation_formula=data.indexation_formula,
        indexation_reference=data.indexation_reference,
        indexation_spread_eur_mwh=data.indexation_spread_eur_mwh,
        price_revision_clause=data.price_revision_clause,
        price_cap_eur_mwh=data.price_cap_eur_mwh,
        price_floor_eur_mwh=data.price_floor_eur_mwh,
        notes=data.notes,
    )
    db.add(contract)
    db.flush()  # Get contract.id

    # Pricing cadre
    for pl in data.pricing:
        db.add(
            ContractPricing(
                contract_id=contract.id,
                period_code=pl.period_code,
                season=pl.season,
                unit_price_eur_kwh=pl.unit_price_eur_kwh,
                subscription_eur_month=pl.subscription_eur_month,
            )
        )

    # Annexes
    for ax_data in data.annexes:
        annexe = ContractAnnexe(
            contrat_cadre_id=contract.id,
            site_id=ax_data.site_id,
            delivery_point_id=ax_data.delivery_point_id,
            annexe_ref=ax_data.annexe_ref,
            tariff_option=ax_data.tariff_option,
            subscribed_power_kva=ax_data.subscribed_power_kva,
            segment_enedis=ax_data.segment_enedis,
            has_price_override=ax_data.has_price_override,
            status=ContractStatus.ACTIVE,
        )
        db.add(annexe)
        db.flush()

        # Pricing override
        if ax_data.has_price_override and ax_data.pricing_overrides:
            for pl in ax_data.pricing_overrides:
                db.add(
                    ContractPricing(
                        annexe_id=annexe.id,
                        period_code=pl.period_code,
                        season=pl.season,
                        unit_price_eur_kwh=pl.unit_price_eur_kwh,
                        subscription_eur_month=pl.subscription_eur_month,
                    )
                )

        # Volume commitment
        if ax_data.volume_commitment:
            vc = ax_data.volume_commitment
            db.add(
                VolumeCommitment(
                    annexe_id=annexe.id,
                    annual_kwh=vc.annual_kwh,
                    tolerance_pct_up=vc.tolerance_pct_up,
                    tolerance_pct_down=vc.tolerance_pct_down,
                    penalty_eur_kwh_above=vc.penalty_eur_kwh_above,
                    penalty_eur_kwh_below=vc.penalty_eur_kwh_below,
                )
            )

    # Event CREATION auto
    db.add(
        ContractEvent(
            contract_id=contract.id,
            event_type="CREATION",
            event_date=date.today(),
            description=f"Creation cadre {data.supplier_name} — {len(data.annexes)} annexe(s)",
        )
    )

    db.commit()
    db.refresh(contract)
    return get_cadre(db, contract.id)


def update_cadre(db: Session, cadre_id: int, data: CadreUpdateSchema) -> Optional[Dict[str, Any]]:
    """MAJ partielle cadre."""
    contract = (
        db.query(EnergyContract)
        .filter(EnergyContract.id == cadre_id, EnergyContract.is_cadre == True)  # noqa: E712
        .first()
    )
    if not contract:
        return None

    update_fields = data.model_dump(exclude_unset=True)

    # Map schema fields to model fields
    field_map = {
        "supplier_name": "supplier_name",
        "contract_ref": "reference_fournisseur",
        "pricing_model": "offer_indexation",
        "start_date": "start_date",
        "end_date": "end_date",
        "tacit_renewal": "auto_renew",
        "notice_period_months": "notice_period_months",
        "is_green": "is_green",
        "green_percentage": "green_percentage",
        "notes": "notes",
        # V2.1 — champs metier
        "segment_enedis": "segment_enedis",
        "annual_consumption_kwh": "annual_consumption_kwh",
        "indexation_formula": "indexation_formula",
        "indexation_reference": "indexation_reference",
        "indexation_spread_eur_mwh": "indexation_spread_eur_mwh",
        "price_revision_clause": "price_revision_clause",
        "price_cap_eur_mwh": "price_cap_eur_mwh",
        "price_floor_eur_mwh": "price_floor_eur_mwh",
    }

    for schema_field, model_field in field_map.items():
        if schema_field in update_fields and schema_field != "pricing":
            setattr(contract, model_field, update_fields[schema_field])

    # Update pricing if provided
    if "pricing" in update_fields and update_fields["pricing"] is not None:
        # Remove old cadre pricing
        db.query(ContractPricing).filter(ContractPricing.contract_id == cadre_id).delete()
        for pl in update_fields["pricing"]:
            db.add(
                ContractPricing(
                    contract_id=cadre_id,
                    period_code=pl["period_code"],
                    season=pl["season"],
                    unit_price_eur_kwh=pl.get("unit_price_eur_kwh"),
                    subscription_eur_month=pl.get("subscription_eur_month"),
                )
            )

    # Refresh status
    contract.contract_status = compute_status(contract)

    db.commit()
    return get_cadre(db, cadre_id)


def delete_cadre(db: Session, cadre_id: int) -> bool:
    """Soft-delete cadre (cascade: annexes + pricing + volume + events)."""
    contract = (
        db.query(EnergyContract)
        .filter(EnergyContract.id == cadre_id, EnergyContract.is_cadre == True)  # noqa: E712
        .first()
    )
    if not contract:
        return False

    contract.contract_status = ContractStatus.TERMINATED
    # Soft-delete annexes
    for annexe in contract.annexes:
        if hasattr(annexe, "soft_delete"):
            annexe.soft_delete(reason="cadre deleted")
    db.commit()
    return True


# ============================================================
# CRUD ANNEXES
# ============================================================


def get_annexe(db: Session, annexe_id: int) -> Optional[Dict[str, Any]]:
    """Annexe + resolved pricing (merge cadre + override)."""
    annexe = (
        db.query(ContractAnnexe)
        .options(
            joinedload(ContractAnnexe.contrat_cadre).joinedload(EnergyContract.pricing_lines),
            joinedload(ContractAnnexe.pricing_overrides),
            joinedload(ContractAnnexe.volume_commitment),
            joinedload(ContractAnnexe.site),
        )
        .filter(ContractAnnexe.id == annexe_id, ContractAnnexe.deleted_at.is_(None))
        .first()
    )
    if not annexe:
        return None
    return _serialize_annexe(annexe)


def create_annexe(db: Session, cadre_id: int, data: AnnexeCreateSchema) -> Optional[Dict[str, Any]]:
    """Ajoute annexe a un cadre existant."""
    cadre = (
        db.query(EnergyContract)
        .filter(EnergyContract.id == cadre_id, EnergyContract.is_cadre == True)  # noqa: E712
        .first()
    )
    if not cadre:
        return None

    annexe = ContractAnnexe(
        contrat_cadre_id=cadre_id,
        site_id=data.site_id,
        delivery_point_id=data.delivery_point_id,
        annexe_ref=data.annexe_ref,
        tariff_option=data.tariff_option,
        subscribed_power_kva=data.subscribed_power_kva,
        segment_enedis=data.segment_enedis,
        has_price_override=data.has_price_override,
        status=ContractStatus.ACTIVE,
    )
    db.add(annexe)
    db.flush()

    if data.has_price_override and data.pricing_overrides:
        for pl in data.pricing_overrides:
            db.add(
                ContractPricing(
                    annexe_id=annexe.id,
                    period_code=pl.period_code,
                    season=pl.season,
                    unit_price_eur_kwh=pl.unit_price_eur_kwh,
                    subscription_eur_month=pl.subscription_eur_month,
                )
            )

    if data.volume_commitment:
        vc = data.volume_commitment
        db.add(
            VolumeCommitment(
                annexe_id=annexe.id,
                annual_kwh=vc.annual_kwh,
                tolerance_pct_up=vc.tolerance_pct_up,
                tolerance_pct_down=vc.tolerance_pct_down,
                penalty_eur_kwh_above=vc.penalty_eur_kwh_above,
                penalty_eur_kwh_below=vc.penalty_eur_kwh_below,
            )
        )

    db.commit()
    return get_annexe(db, annexe.id)


def update_annexe(db: Session, annexe_id: int, data: AnnexeUpdateSchema) -> Optional[Dict[str, Any]]:
    """MAJ annexe. Toggle has_price_override."""
    annexe = (
        db.query(ContractAnnexe).filter(ContractAnnexe.id == annexe_id, ContractAnnexe.deleted_at.is_(None)).first()
    )
    if not annexe:
        return None

    update_fields = data.model_dump(exclude_unset=True)

    simple_fields = [
        "delivery_point_id",
        "annexe_ref",
        "tariff_option",
        "subscribed_power_kva",
        "segment_enedis",
        "has_price_override",
        "override_pricing_model",
        "start_date_override",
        "end_date_override",
    ]
    for f in simple_fields:
        if f in update_fields:
            setattr(annexe, f, update_fields[f])

    # Update pricing overrides if provided
    if "pricing_overrides" in update_fields and update_fields["pricing_overrides"] is not None:
        db.query(ContractPricing).filter(ContractPricing.annexe_id == annexe_id).delete()
        for pl in update_fields["pricing_overrides"]:
            db.add(
                ContractPricing(
                    annexe_id=annexe_id,
                    period_code=pl["period_code"],
                    season=pl["season"],
                    unit_price_eur_kwh=pl.get("unit_price_eur_kwh"),
                    subscription_eur_month=pl.get("subscription_eur_month"),
                )
            )

    # Update volume commitment
    if "volume_commitment" in update_fields:
        vc_data = update_fields["volume_commitment"]
        existing_vc = db.query(VolumeCommitment).filter(VolumeCommitment.annexe_id == annexe_id).first()
        if vc_data is None and existing_vc:
            db.delete(existing_vc)
        elif vc_data:
            if existing_vc:
                for k, v in vc_data.items():
                    setattr(existing_vc, k, v)
            else:
                db.add(VolumeCommitment(annexe_id=annexe_id, **vc_data))

    db.commit()
    return get_annexe(db, annexe_id)


def delete_annexe(db: Session, annexe_id: int) -> bool:
    """Soft-delete annexe + pricing override + volume."""
    annexe = (
        db.query(ContractAnnexe).filter(ContractAnnexe.id == annexe_id, ContractAnnexe.deleted_at.is_(None)).first()
    )
    if not annexe:
        return False
    if hasattr(annexe, "soft_delete"):
        annexe.soft_delete(reason="deleted by user")
    db.commit()
    return True


# ============================================================
# HERITAGE (resolve_pricing delegue a contrat_coherence.py)
# ============================================================


def resolve_dates(annexe: ContractAnnexe) -> Dict[str, Optional[date]]:
    """start/end effectifs: override si renseignes, sinon cadre."""
    cadre = annexe.contrat_cadre
    return {
        "start_date": annexe.start_date_override or (cadre.start_date if cadre else None),
        "end_date": annexe.end_date_override or (cadre.end_date if cadre else None),
    }


# ============================================================
# STATUS ENGINE
# ============================================================


def compute_status(contract_or_annexe) -> ContractStatus:
    """DRAFT si dates manquantes, ACTIVE si en cours, EXPIRING si <90j, EXPIRED si passe."""
    start = getattr(contract_or_annexe, "start_date_override", None) or getattr(contract_or_annexe, "start_date", None)
    end = getattr(contract_or_annexe, "end_date_override", None) or getattr(contract_or_annexe, "end_date", None)

    if not start or not end:
        return ContractStatus.DRAFT

    today = date.today()
    if today > end:
        return ContractStatus.EXPIRED
    if today >= start and (end - today).days <= 90:
        return ContractStatus.EXPIRING
    if today >= start:
        return ContractStatus.ACTIVE
    return ContractStatus.DRAFT


def refresh_all_statuses(db: Session, org_id: int) -> int:
    """Batch: recalcule tous les statuts cadre + annexes."""
    cadres = list_cadres(db, org_id)
    count = 0
    for c_data in cadres:
        contract = db.query(EnergyContract).get(c_data["id"])
        if contract:
            new_status = compute_status(contract)
            if contract.contract_status != new_status:
                contract.contract_status = new_status
                count += 1
    db.commit()
    return count


# ============================================================
# KPIs
# ============================================================


def compute_cadre_kpis(db: Session, cadre: EnergyContract) -> Dict[str, Any]:
    """KPIs pour un cadre avec prix moyen pondere par volume."""
    annexes = [a for a in cadre.annexes if a.deleted_at is None]
    total_vol = sum((float(a.volume_commitment.annual_kwh) if a.volume_commitment else 0) for a in annexes)

    # Prix moyen pondere : chaque ligne pricing contribue proportionnellement
    # Cast Decimal → float for arithmetic with PERIOD_WEIGHTS (floats)
    weighted_sum = 0.0
    weight_total = 0.0
    for p in cadre.pricing_lines:
        if p.unit_price_eur_kwh:
            w = PERIOD_WEIGHTS.get(p.period_code, 0.25)
            weighted_sum += float(p.unit_price_eur_kwh) * w
            weight_total += w
    avg_price = (weighted_sum / weight_total) if weight_total else 0

    # Budget = prix moyen pondere * volume total
    budget = avg_price * total_vol if avg_price and total_vol else 0

    # Fallback: si pas de pricing lines, utiliser annual_consumption_kwh du cadre
    if not total_vol and cadre.annual_consumption_kwh:
        total_vol = float(cadre.annual_consumption_kwh)

    days_to_expiry = (cadre.end_date - date.today()).days if cadre.end_date else None

    return {
        "avg_price_eur_mwh": round(avg_price * 1000, 2),
        "total_volume_mwh": round(total_vol / 1000, 2) if total_vol else 0,
        "budget_eur": round(budget, 0),
        "days_to_expiry": days_to_expiry,
        "nb_annexes": len(annexes),
        "coherence_count": len(coherence_check(db, cadre.id)),
    }


def compute_portfolio_kpis(db: Session, org_id: int) -> Dict[str, Any]:
    """KPIs portefeuille: total_cadres, active, expiring, volume, budget, shadow_gap."""
    cadres_data = list_cadres(db, org_id)
    total = len(cadres_data)
    active = sum(1 for c in cadres_data if c.get("status") == "active")
    expiring = sum(1 for c in cadres_data if c.get("status") == "expiring")
    total_vol = sum(c.get("total_volume_mwh", 0) for c in cadres_data)
    total_budget = sum(c.get("budget_eur", 0) for c in cadres_data)

    return {
        "total_cadres": total,
        "active_cadres": active,
        "expiring_90d": expiring,
        "total_volume_mwh": round(total_vol, 2),
        "total_budget_eur": round(total_budget, 0),
        "total_shadow_gap_eur": 0,  # Placeholder — requires invoice data
    }


# ============================================================
# SHADOW BILLING BRIDGE
# ============================================================


def compute_shadow_gap(db: Session, annexe_id: int) -> Dict[str, Any]:
    """Ecart shadow billing pour une annexe — decompose par composante facture."""
    from models.billing_models import EnergyInvoice, EnergyInvoiceLine

    annexe = (
        db.query(ContractAnnexe)
        .options(
            joinedload(ContractAnnexe.contrat_cadre).joinedload(EnergyContract.pricing_lines),
            joinedload(ContractAnnexe.pricing_overrides),
        )
        .filter(ContractAnnexe.id == annexe_id)
        .first()
    )
    if not annexe:
        return {"error": "Annexe non trouvee"}

    pricing = resolve_pricing(db, annexe)
    if not pricing:
        return {"total_gap_eur": 0, "detail": [], "note": "Pas de pricing"}

    invoices = db.query(EnergyInvoice).filter(EnergyInvoice.site_id == annexe.site_id).all()

    total_gap = 0
    total_supply_gap = 0
    details = []

    for inv in invoices:
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()

        inv_supply = 0
        inv_network = 0
        inv_tax = 0
        inv_other = 0
        shadow_supply = 0

        for line in lines:
            lt = (line.line_type or "").upper()
            amount = line.amount_eur or 0
            if lt in SUPPLY_TYPES:
                inv_supply += amount
                # Shadow : match par period_code
                for p in pricing:
                    pc = p.get("period_code", "")
                    if line.qty and p.get("unit_price_eur_kwh"):
                        if not pc or pc == (getattr(line, "period_code", None) or ""):
                            shadow_supply += float(line.qty) * float(p["unit_price_eur_kwh"])
                            break
            elif lt in NETWORK_TYPES:
                inv_network += amount
            elif lt in TAX_TYPES:
                inv_tax += amount
            else:
                inv_other += amount

        supply_gap = inv_supply - shadow_supply if shadow_supply else 0
        total_gap += supply_gap
        total_supply_gap += supply_gap

        if inv.total_eur:
            details.append(
                {
                    "invoice_id": inv.id,
                    "invoice_ref": inv.invoice_number,
                    "invoice_total_eur": round(inv.total_eur, 2),
                    "decomposition": {
                        "fourniture_facturee": round(inv_supply, 2),
                        "fourniture_shadow": round(shadow_supply, 2),
                        "ecart_fourniture": round(supply_gap, 2),
                        "acheminement": round(inv_network, 2),
                        "taxes_contributions": round(inv_tax, 2),
                        "autres": round(inv_other, 2),
                    },
                }
            )

    return {
        "annexe_id": annexe_id,
        "total_gap_eur": round(total_gap, 2),
        "supply_gap_eur": round(total_supply_gap, 2),
        "invoices_checked": len(invoices),
        "note": "Ecart calcule sur la composante fourniture uniquement. Acheminement et taxes affiches a titre informatif.",
        "detail": details,
    }


# ============================================================
# IMPORT CSV
# ============================================================


def import_csv(db: Session, org_id: int, file_content: str) -> Dict[str, Any]:
    """Import CSV multi-lignes. Auto-groupement: meme supplier+ref → 1 cadre + N annexes."""
    reader = csv.DictReader(io.StringIO(file_content))

    groups = {}  # (supplier, ref) → list of rows
    warnings = []
    errors = []

    for i, row in enumerate(reader):
        supplier = row.get("supplier", "").strip()
        ref = row.get("contract_ref", "").strip()
        if not supplier:
            errors.append(f"Ligne {i + 2}: fournisseur manquant")
            continue
        key = (supplier, ref or f"_auto_{i}")
        groups.setdefault(key, []).append(row)

    cadres_created = 0
    annexes_created = 0

    for (supplier, ref), rows in groups.items():
        first = rows[0]
        try:
            energy = first.get("energy_type", "elec").strip().lower()
            start = date.fromisoformat(first.get("start_date", ""))
            end = date.fromisoformat(first.get("end_date", ""))
        except (ValueError, TypeError) as e:
            errors.append(f"Cadre {supplier}/{ref}: dates invalides — {e}")
            continue

        annexes_data = []
        for row in rows:
            site_id = row.get("site_id")
            if not site_id:
                warnings.append(f"Ligne sans site_id pour {supplier}/{ref}")
                continue
            annexes_data.append(
                AnnexeCreateSchema(
                    site_id=int(site_id),
                    annexe_ref=row.get("annexe_ref"),
                    subscribed_power_kva=float(row["subscribed_power_kva"])
                    if row.get("subscribed_power_kva")
                    else None,
                    tariff_option=row.get("tariff_option"),
                    segment_enedis=row.get("segment_enedis"),
                )
            )

        if not annexes_data:
            errors.append(f"Cadre {supplier}/{ref}: aucune annexe valide")
            continue

        data = CadreCreateSchema(
            supplier_name=supplier,
            energy_type=energy,
            contract_ref=ref if not ref.startswith("_auto_") else None,
            contract_type="CADRE" if len(annexes_data) > 1 else "UNIQUE",
            start_date=start,
            end_date=end,
            annexes=annexes_data,
        )
        create_cadre(db, data)
        cadres_created += 1
        annexes_created += len(annexes_data)

    return {
        "cadres_created": cadres_created,
        "annexes_created": annexes_created,
        "warnings": warnings,
        "errors": errors,
    }


# ============================================================
# SERIALIZERS
# ============================================================


def get_site_active_contract(db: Session, site_id: int) -> Optional[Dict[str, Any]]:
    """Return the active contract annexe (+ cadre info) for a given site."""
    today = date.today()
    annexe = (
        db.query(ContractAnnexe)
        .options(
            joinedload(ContractAnnexe.contrat_cadre).joinedload(EnergyContract.pricing_lines),
            joinedload(ContractAnnexe.pricing_overrides),
            joinedload(ContractAnnexe.volume_commitment),
            joinedload(ContractAnnexe.site),
        )
        .join(EnergyContract, ContractAnnexe.contrat_cadre_id == EnergyContract.id)
        .filter(
            ContractAnnexe.site_id == site_id,
            ContractAnnexe.deleted_at.is_(None),
            EnergyContract.is_cadre == True,  # noqa: E712
            EnergyContract.start_date <= today,
            EnergyContract.end_date >= today,
        )
        .order_by(EnergyContract.end_date.desc())
        .first()
    )
    if not annexe:
        return None
    return _serialize_annexe(annexe)


def list_expiring(db: Session, org_id: int, *, days: int = 90) -> List[Dict[str, Any]]:
    """List cadre contracts expiring within N days for an org."""
    from models import EntiteJuridique

    today = date.today()
    horizon = today + timedelta(days=days)

    ej_ids = [ej.id for ej in db.query(EntiteJuridique.id).filter(EntiteJuridique.organisation_id == org_id).all()]

    q = (
        db.query(EnergyContract)
        .options(
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.site),
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.volume_commitment),
            joinedload(EnergyContract.pricing_lines),
        )
        .filter(
            EnergyContract.is_cadre == True,  # noqa: E712
            EnergyContract.end_date >= today,
            EnergyContract.end_date <= horizon,
        )
    )
    if ej_ids:
        q = q.filter(EnergyContract.entite_juridique_id.in_(ej_ids))

    cadres = q.order_by(EnergyContract.end_date.asc()).all()
    return [_serialize_cadre(c) for c in cadres]


def get_cadre_for_org(db: Session, cadre_id: int, org_id: int) -> Optional[Dict[str, Any]]:
    """Cadre complet, scoped to org. Returns None if not found or not in org.

    Org matching via entite_juridique_id OR via annexe site chain.
    """
    from models import EntiteJuridique, Site, Portefeuille
    from sqlalchemy import or_

    ej_ids = [ej.id for ej in db.query(EntiteJuridique.id).filter(EntiteJuridique.organisation_id == org_id).all()]

    # Site IDs belonging to this org (for cadres without EJ link)
    site_ids = [
        s.id
        for s in db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    c = (
        db.query(EnergyContract)
        .options(
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.site),
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.volume_commitment),
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.pricing_overrides),
            joinedload(EnergyContract.pricing_lines),
            joinedload(EnergyContract.events),
        )
        .filter(
            EnergyContract.id == cadre_id,
            EnergyContract.is_cadre == True,  # noqa: E712
        )
    )

    # Scope: EJ match OR reference site belongs to org
    org_filters = []
    if ej_ids:
        org_filters.append(EnergyContract.entite_juridique_id.in_(ej_ids))
    if site_ids:
        org_filters.append(EnergyContract.site_id.in_(site_ids))
    if org_filters:
        c = c.filter(or_(*org_filters))

    c = c.first()
    if not c:
        return None
    result = _serialize_cadre(c)
    result["events"] = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "event_date": str(e.event_date) if e.event_date else None,
            "description": e.description,
        }
        for e in sorted(c.events, key=lambda x: x.event_date or date.min)
    ]
    result["coherence"] = coherence_check(db, cadre_id)
    return result


def _serialize_v2_cadre(c: ContratCadre) -> Dict[str, Any]:
    """Serialize a V2 ContratCadre into the same envelope as legacy _serialize_cadre.

    V2 cadres have flat price columns (prix_hp_eur_kwh, prix_hc_eur_kwh,
    prix_base_eur_kwh) and a denormalized poids_hp / poids_hc split. The
    weighted-average price is computed from these flat columns so the UI can
    display a single EUR/MWh figure consistent with legacy cadres.
    """
    annexes = [a for a in c.annexes if a.deleted_at is None]
    total_vol_kwh = sum(
        float(a.volume_engage_kwh or 0) + (float(a.volume_commitment.annual_kwh) if a.volume_commitment else 0)
        for a in annexes
    )
    total_vol_mwh = round(total_vol_kwh / 1000, 2)

    # Weighted average from flat V2 columns
    prix_base = float(c.prix_base_eur_kwh) if c.prix_base_eur_kwh is not None else None
    prix_hp = float(c.prix_hp_eur_kwh) if c.prix_hp_eur_kwh is not None else None
    prix_hc = float(c.prix_hc_eur_kwh) if c.prix_hc_eur_kwh is not None else None
    if prix_base is not None:
        avg_price = prix_base
    elif prix_hp is not None and prix_hc is not None:
        hp_w = float(c.poids_hp or 62.0) / 100.0
        hc_w = float(c.poids_hc or 38.0) / 100.0
        avg_price = prix_hp * hp_w + prix_hc * hc_w
    else:
        avg_price = 0
    avg_price_mwh = round(avg_price * 1000, 2)

    days_to_expiry = (c.date_fin - date.today()).days if c.date_fin else None
    statut_val = c.statut.value if c.statut else None

    pricing: List[Dict[str, Any]] = []
    if prix_base is not None:
        pricing.append(
            {"period_code": "BASE", "season": "ANNUEL", "unit_price_eur_kwh": prix_base, "subscription_eur_month": None}
        )
    if prix_hp is not None:
        pricing.append(
            {"period_code": "HP", "season": "ANNUEL", "unit_price_eur_kwh": prix_hp, "subscription_eur_month": None}
        )
    if prix_hc is not None:
        pricing.append(
            {"period_code": "HC", "season": "ANNUEL", "unit_price_eur_kwh": prix_hc, "subscription_eur_month": None}
        )

    return {
        "id": c.id,
        "source": "v2",
        "supplier_name": c.fournisseur,
        "contract_ref": c.reference_fournisseur or c.reference,
        "energy_type": c.energie.value if c.energie else None,
        "contract_type": "CADRE",
        "pricing_model": c.type_prix.value if c.type_prix else None,
        "start_date": str(c.date_debut) if c.date_debut else None,
        "end_date": str(c.date_fin) if c.date_fin else None,
        "status": statut_val,
        "days_to_expiry": days_to_expiry,
        "tacit_renewal": c.auto_renew,
        "notice_period_months": c.notice_period_months,
        "is_green": c.is_green,
        "green_percentage": c.green_percentage,
        "segment_enedis": None,
        "indexation_formula": None,
        "indexation_reference": c.indexation_reference,
        "price_revision_clause": None,
        "notes": c.notes,
        "entite_juridique_id": c.entite_juridique_id,
        "nb_annexes": len(annexes),
        "total_volume_mwh": total_vol_mwh,
        "avg_price_eur_mwh": avg_price_mwh,
        "budget_eur": round(avg_price * total_vol_kwh, 0) if avg_price and total_vol_kwh else 0,
        "pricing": pricing,
        "annexes": [_serialize_annexe_summary(a) for a in annexes],
    }


def _serialize_cadre(c: EnergyContract) -> Dict[str, Any]:
    """Serialize cadre + stats."""
    annexes = [a for a in c.annexes if a.deleted_at is None]
    total_vol = sum(
        (float(a.volume_commitment.annual_kwh) / 1000 if a.volume_commitment else 0) for a in annexes
    )

    # Prix moyen pondere (meme formule que compute_cadre_kpis)
    # Cast Decimal → float: unit_price_eur_kwh is Numeric(18,6), PERIOD_WEIGHTS floats
    weighted_sum = 0.0
    weight_total = 0.0
    for p in c.pricing_lines:
        if p.unit_price_eur_kwh:
            w = PERIOD_WEIGHTS.get(p.period_code, 0.25)
            weighted_sum += float(p.unit_price_eur_kwh) * w
            weight_total += w
    avg_price = (weighted_sum / weight_total) if weight_total else 0
    avg_price_mwh = round(avg_price * 1000, 2)

    # Fallback volume
    if not total_vol and c.annual_consumption_kwh:
        total_vol = float(c.annual_consumption_kwh) / 1000

    days_to_expiry = (c.end_date - date.today()).days if c.end_date else None
    status_val = c.contract_status.value if c.contract_status else compute_status(c).value

    return {
        "id": c.id,
        "supplier_name": c.supplier_name,
        "contract_ref": c.reference_fournisseur,
        "energy_type": c.energy_type.value if c.energy_type else None,
        "contract_type": c.contract_type or "UNIQUE",
        "pricing_model": c.offer_indexation.value if c.offer_indexation else None,
        "start_date": str(c.start_date) if c.start_date else None,
        "end_date": str(c.end_date) if c.end_date else None,
        "status": status_val,
        "days_to_expiry": days_to_expiry,
        "tacit_renewal": c.auto_renew,
        "notice_period_months": c.notice_period_months,
        "is_green": c.is_green,
        "green_percentage": c.green_percentage,
        "segment_enedis": c.segment_enedis,
        "indexation_formula": c.indexation_formula,
        "indexation_reference": c.indexation_reference,
        "price_revision_clause": c.price_revision_clause,
        "notes": c.notes,
        "entite_juridique_id": c.entite_juridique_id,
        "nb_annexes": len(annexes),
        "total_volume_mwh": round(total_vol, 2),
        "avg_price_eur_mwh": avg_price_mwh,
        "budget_eur": round(avg_price * total_vol * 1000, 0) if avg_price and total_vol else 0,
        "pricing": [
            {
                "period_code": p.period_code,
                "season": p.season,
                "unit_price_eur_kwh": float(p.unit_price_eur_kwh) if p.unit_price_eur_kwh is not None else None,
                "subscription_eur_month": float(p.subscription_eur_month)
                if p.subscription_eur_month is not None
                else None,
            }
            for p in c.pricing_lines
        ],
        "annexes": [_serialize_annexe_summary(a) for a in annexes],
    }


def _serialize_annexe_summary(a: ContractAnnexe) -> Dict[str, Any]:
    """Serialize annexe (summary for cadre list)."""
    dates = resolve_dates(a)
    return {
        "id": a.id,
        "site_id": a.site_id,
        "site_name": a.site.nom if a.site else None,
        "annexe_ref": a.annexe_ref,
        "tariff_option": a.tariff_option.value if a.tariff_option else None,
        "subscribed_power_kva": a.subscribed_power_kva,
        "segment_enedis": a.segment_enedis,
        "has_price_override": a.has_price_override,
        "status": a.status.value if a.status else "active",
        "start_date": str(dates["start_date"]) if dates["start_date"] else None,
        "end_date": str(dates["end_date"]) if dates["end_date"] else None,
        "volume_mwh": round(float(a.volume_commitment.annual_kwh) / 1000, 2) if a.volume_commitment else None,
    }


def _serialize_annexe(a: ContractAnnexe) -> Dict[str, Any]:
    """Serialize annexe with resolved pricing."""
    summary = _serialize_annexe_summary(a)
    summary["cadre_id"] = a.contrat_cadre_id
    summary["cadre_ref"] = a.contrat_cadre.reference_fournisseur if a.contrat_cadre else None
    summary["cadre_supplier"] = a.contrat_cadre.supplier_name if a.contrat_cadre else None
    summary["delivery_point_id"] = a.delivery_point_id
    summary["resolved_pricing"] = resolve_pricing(None, a)  # db not needed, annexe is loaded
    summary["volume_commitment"] = None
    if a.volume_commitment:
        vc = a.volume_commitment
        summary["volume_commitment"] = {
            "annual_kwh": vc.annual_kwh,
            "tolerance_pct_up": vc.tolerance_pct_up,
            "tolerance_pct_down": vc.tolerance_pct_down,
            "penalty_eur_kwh_above": vc.penalty_eur_kwh_above,
            "penalty_eur_kwh_below": vc.penalty_eur_kwh_below,
        }
    return summary
