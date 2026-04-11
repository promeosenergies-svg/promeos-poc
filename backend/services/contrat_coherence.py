"""
PROMEOS — Coherence Contrat V2 : validate_contrat() + resolve_pricing()
Source de verite unique pour les 16 regles R1-R16 et la cascade de prix.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from models.billing_models import EnergyContract
from models.contract_v2_models import ContractAnnexe, ContractPricing
from models.enums import BillingEnergyType

logger = logging.getLogger(__name__)

# Seuils prix fourniture HT marche B2B France (EUR/kWh)
PRICE_THRESHOLD_ELEC = 0.25  # Forward Y+1 ~80-120 EUR/MWh
PRICE_THRESHOLD_GAZ = 0.10  # PEG ~30-50 EUR/MWh

# Poids HP/HC standard (source: profils Enedis C5)
DEFAULT_POIDS_HP = 62.0
DEFAULT_POIDS_HC = 38.0

# Fournisseurs CRE agrees (liste non exhaustive, top 50 B2B France)
FOURNISSEURS_CRE = frozenset(
    {
        "edf",
        "edf entreprises",
        "engie",
        "totalenergies",
        "total energies",
        "eni",
        "vattenfall",
        "alpiq",
        "axpo",
        "ekwateur",
        "mint energie",
        "ilek",
        "planete oui",
        "mega energie",
        "happ-e",
        "wekiwi",
        "greenyellow",
        "barry",
        "elmy",
        "octopus energy",
        "urban solar",
        "primeo energie",
        "gazel energie",
        "iberdrola",
        "endesa",
        "solvay energy",
        "direct energie",
        "butagaz",
        "sowee",
        "energem",
        "geg",
        "es energies strasbourg",
        "electricite de provence",
        "energies du santerre",
        "volterres",
        "hydroption",
        "ohm energie",
        "energie d ici",
        "lucia energie",
        "yeli",
        "plum energie",
        "alterna",
        "proxelia",
        "energies de loire",
        "save",
        "dyneff",
        "antargaz",
        "vitogaz",
        "primagaz",
    }
)


def validate_contrat(db: Session, cadre_id: int) -> List[Dict[str, str]]:
    """16 regles de coherence (R1-R16). Retourne list[{rule_id, level, message}].

    R1  — Dates obligatoires et coherentes (debut < fin)
    R2  — Duree contractuelle raisonnable (1 mois - 72 mois)
    R3  — Fournisseur reconnu CRE
    R4  — Minimum 1 annexe site
    R5  — Coherence cadre/annexe (annexe rattachee au bon cadre)
    R6  — Chevauchement PDL sur meme periode
    R7  — Prix HP > HC (fourniture HT standard)
    R8  — Poids HP + HC = 100%
    R9  — Coherence energie / PRM / PCE
    R10 — Puissance souscrite / segment
    R11 — Plage dates annexe dans plage cadre
    R12 — ARENH post-VNU (fin 2025)
    R13 — Accise / tier coherent (segment dependant)
    R14 — Volume engage vs volume reel (tolerance)
    R15 — Option tarifaire / segment compatible
    R16 — Expiration et couverture
    """
    contract = (
        db.query(EnergyContract)
        .options(
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.pricing_overrides),
            joinedload(EnergyContract.annexes).joinedload(ContractAnnexe.volume_commitment),
            joinedload(EnergyContract.pricing_lines),
        )
        .filter(EnergyContract.id == cadre_id)
        .first()
    )
    if not contract:
        return []

    results: List[Dict[str, str]] = []
    annexes = [a for a in contract.annexes if a.deleted_at is None]

    # ── R1 — Dates obligatoires et coherentes ──
    if not contract.start_date or not contract.end_date:
        results.append(
            {
                "rule_id": "R1",
                "level": "error",
                "message": "Dates debut/fin obligatoires non renseignees",
            }
        )
    elif contract.end_date <= contract.start_date:
        results.append(
            {
                "rule_id": "R1",
                "level": "error",
                "message": "Date fin avant ou egale a date debut",
            }
        )

    # ── R2 — Duree contractuelle raisonnable ──
    if contract.start_date and contract.end_date and contract.end_date > contract.start_date:
        months = (contract.end_date.year - contract.start_date.year) * 12 + (
            contract.end_date.month - contract.start_date.month
        )
        if months < 1:
            results.append(
                {
                    "rule_id": "R2",
                    "level": "warning",
                    "message": f"Duree < 1 mois ({months} mois) — inhabituellement court",
                }
            )
        elif months > 72:
            results.append(
                {
                    "rule_id": "R2",
                    "level": "warning",
                    "message": f"Duree > 72 mois ({months} mois) — inhabituellement long pour B2B France",
                }
            )
        # Spot long = risque volatilite
        if contract.offer_indexation and contract.offer_indexation.value == "indexe_spot" and months > 24:
            results.append(
                {
                    "rule_id": "R2",
                    "level": "warning",
                    "message": f"Contrat spot sur {months} mois — risque de volatilite eleve",
                }
            )
        # Fixe tres court
        if contract.offer_indexation and contract.offer_indexation.value == "fixe" and months < 3:
            results.append(
                {
                    "rule_id": "R2",
                    "level": "info",
                    "message": f"Contrat fixe sur {months} mois — duree inhabituellement courte",
                }
            )

    # ── R3 — Fournisseur reconnu CRE ──
    supplier = (contract.supplier_name or "").strip().lower()
    if supplier and supplier not in FOURNISSEURS_CRE:
        results.append(
            {
                "rule_id": "R3",
                "level": "info",
                "message": f"Fournisseur '{contract.supplier_name}' non reconnu dans la liste CRE — verifier orthographe",
            }
        )

    # ── R4 — Minimum 1 annexe site ──
    if not annexes:
        results.append(
            {
                "rule_id": "R4",
                "level": "warning",
                "message": "Cadre sans annexe site — au moins 1 annexe requise",
            }
        )

    # ── R5 — Coherence cadre/annexe (annexe rattachee) ──
    for a in annexes:
        if a.contrat_cadre_id and a.contrat_cadre_id != cadre_id:
            results.append(
                {
                    "rule_id": "R5",
                    "level": "error",
                    "message": f"Annexe {a.annexe_ref or a.id} rattachee au cadre {a.contrat_cadre_id}, pas {cadre_id}",
                }
            )

    # ── R6 — Chevauchement contrats sur meme PDL ──
    dp_ids = [a.delivery_point_id for a in annexes if a.delivery_point_id]
    if dp_ids and contract.start_date and contract.end_date:
        other_annexes = (
            db.query(ContractAnnexe)
            .join(EnergyContract, EnergyContract.id == ContractAnnexe.contrat_cadre_id)
            .filter(
                ContractAnnexe.delivery_point_id.in_(dp_ids),
                ContractAnnexe.contrat_cadre_id != cadre_id,
                ContractAnnexe.deleted_at.is_(None),
                EnergyContract.start_date <= contract.end_date,
                (EnergyContract.end_date.is_(None) | (EnergyContract.end_date >= contract.start_date)),
            )
            .all()
        )
        if other_annexes:
            results.append(
                {
                    "rule_id": "R6",
                    "level": "error",
                    "message": f"Chevauchement PDL avec {len(other_annexes)} autre(s) contrat(s) actif(s) sur la meme periode",
                }
            )

    # ── R7 — Prix HP > HC (standard fourniture elec) ──
    energy = contract.energy_type.value if contract.energy_type else "elec"
    if energy == "elec" and contract.pricing_lines:
        hp_lines = [p for p in contract.pricing_lines if p.period_code == "HP" and p.unit_price_eur_kwh]
        hc_lines = [p for p in contract.pricing_lines if p.period_code == "HC" and p.unit_price_eur_kwh]
        if hp_lines and hc_lines:
            hp_price = hp_lines[0].unit_price_eur_kwh
            hc_price = hc_lines[0].unit_price_eur_kwh
            if hp_price <= hc_price:
                results.append(
                    {
                        "rule_id": "R7",
                        "level": "warning",
                        "message": f"Prix HP ({hp_price:.4f}) <= HC ({hc_price:.4f}) — verifier inversion HP/HC",
                    }
                )

    # ── R8 — Poids HP + HC = 100% ──
    poids_hp = getattr(contract, "poids_hp", None)
    poids_hc = getattr(contract, "poids_hc", None)
    if poids_hp is not None and poids_hc is not None:
        total_poids = poids_hp + poids_hc
        if abs(total_poids - 100.0) > 0.5:
            results.append(
                {
                    "rule_id": "R8",
                    "level": "error",
                    "message": f"Poids HP ({poids_hp}%) + HC ({poids_hc}%) = {total_poids}% (attendu 100%)",
                }
            )

    # ── R9 — Coherence energie / PRM / PCE ──
    for a in annexes:
        prm = getattr(a, "prm", None)
        pce = getattr(a, "pce", None)
        if energy == "elec" and pce and not prm:
            results.append(
                {
                    "rule_id": "R9",
                    "level": "warning",
                    "message": f"Annexe {a.annexe_ref or a.id}: contrat elec avec PCE (gaz) sans PRM",
                }
            )
        if energy == "gaz" and prm and not pce:
            results.append(
                {
                    "rule_id": "R9",
                    "level": "warning",
                    "message": f"Annexe {a.annexe_ref or a.id}: contrat gaz avec PRM (elec) sans PCE",
                }
            )
        if not a.delivery_point_id and not prm and not pce:
            results.append(
                {
                    "rule_id": "R9",
                    "level": "warning",
                    "message": f"Annexe {a.annexe_ref or a.id} sans PDL/PRM/PCE",
                }
            )

    # ── R10 — Puissance souscrite / segment ──
    for a in annexes:
        seg = (a.segment_enedis or "").upper()
        ps = a.subscribed_power_kva
        if seg and ps:
            if seg == "C5" and ps > 36:
                results.append(
                    {
                        "rule_id": "R10",
                        "level": "error",
                        "message": f"Annexe {a.annexe_ref or a.id}: segment C5 mais PS={ps} kVA > 36 kVA (TURPE 7)",
                    }
                )
            elif seg == "C4" and (ps <= 36 or ps > 250):
                results.append(
                    {
                        "rule_id": "R10",
                        "level": "warning",
                        "message": f"Annexe {a.annexe_ref or a.id}: segment C4 mais PS={ps} kVA (attendu 37-250 kVA)",
                    }
                )
            elif seg == "C3" and (ps <= 250 or ps > 10000):
                results.append(
                    {
                        "rule_id": "R10",
                        "level": "warning",
                        "message": f"Annexe {a.annexe_ref or a.id}: segment C3 mais PS={ps} kVA (attendu 250-10000 kVA)",
                    }
                )
        # Puissance manquante si option multi-postes
        if a.tariff_option and a.tariff_option.value in ("hp_hc", "cu4", "mu4", "cu", "lu") and not ps:
            results.append(
                {
                    "rule_id": "R10",
                    "level": "warning",
                    "message": f"Puissance non renseignee pour {a.annexe_ref or a.id} (option multi-postes)",
                }
            )

    # ── R11 — Plage dates annexe dans plage cadre ──
    if contract.start_date and contract.end_date:
        for a in annexes:
            a_start = a.start_date_override
            a_end = a.end_date_override
            if a_start and a_start < contract.start_date:
                results.append(
                    {
                        "rule_id": "R11",
                        "level": "warning",
                        "message": f"Annexe {a.annexe_ref or a.id}: debut override ({a_start}) avant debut cadre ({contract.start_date})",
                    }
                )
            if a_end and a_end > contract.end_date:
                results.append(
                    {
                        "rule_id": "R11",
                        "level": "warning",
                        "message": f"Annexe {a.annexe_ref or a.id}: fin override ({a_end}) apres fin cadre ({contract.end_date})",
                    }
                )

    # ── R12 — Post-ARENH / VNU (structure 4 sous-regles) ──
    # Contexte reglementaire :
    #   - ARENH supprime au 31/12/2025 (LF 2025 art. 17)
    #   - VNU (Versement Nucleaire Universel) effectif 01/01/2026
    #     seuils 78/110 EUR/MWh, taux 50% (decrets 2025-909/910, CRE 2025-268)
    #   - Tarif unitaire VNU = 0 EUR/MWh en 2026 (revenus nucleaires ~66 < seuil bas 78)
    #   - References indexation post-ARENH valides : TRVE, EPEX_SPOT_FR, PEG_DA,
    #     PEG_M+1, TTF_DA (schemas.contract_v2_schemas.INDEXATION_REFERENCES)
    _indexation_val = (contract.offer_indexation.value if contract.offer_indexation else "") or ""
    _indexation_ref = (getattr(contract, "indexation_reference", None) or "").strip()
    _indexation_formula = (getattr(contract, "indexation_formula", None) or "").lower()
    _mentions_arenh = (
        "arenh" in _indexation_val.lower() or "arenh" in _indexation_ref.lower() or "arenh" in _indexation_formula
    )
    _is_indexed = _indexation_val in ("indexe", "indexe_trve", "indexe_peg", "indexe_spot", "spot", "hybride")
    _months = None
    if contract.start_date and contract.end_date and contract.end_date > contract.start_date:
        _months = (contract.end_date.year - contract.start_date.year) * 12 + (
            contract.end_date.month - contract.start_date.month
        )

    # R12a (ERROR) : contrat debutant apres 2025-12-31 qui mentionne encore ARENH
    if _mentions_arenh and contract.start_date and contract.start_date >= date(2026, 1, 1):
        results.append(
            {
                "rule_id": "R12",
                "level": "error",
                "message": (
                    "ARENH supprime au 31/12/2025 (LF 2025 art. 17) mais contrat debutant "
                    f"le {contract.start_date.isoformat()} y fait encore reference. "
                    "Remplacer par VNU, TRVE ou indexation EPEX/PEG explicite."
                ),
            }
        )

    # R12b (WARNING) : contrat indexe long (>24 mois) sans cap/floor/tunnel defini
    # Exposition volatilite non bornee. Clause revision = NONE ou null + pas de prix cap/floor.
    _revision = (getattr(contract, "price_revision_clause", None) or "NONE").upper()
    _has_cap = getattr(contract, "price_cap_eur_mwh", None) is not None
    _has_floor = getattr(contract, "price_floor_eur_mwh", None) is not None
    if (
        _is_indexed
        and _months is not None
        and _months > 24
        and _revision in ("NONE", "")
        and not _has_cap
        and not _has_floor
    ):
        results.append(
            {
                "rule_id": "R12",
                "level": "warning",
                "message": (
                    f"Contrat indexe ({_indexation_val}) sur {_months} mois sans cap/floor/tunnel. "
                    "Exposition volatilite non bornee post-ARENH — negocier une clause de revision."
                ),
            }
        )

    # R12c (INFO) : contrat fixe signe avant 2025-01-01 expirant en 2026-2027
    # Opportunite de renegociation avec clause post-ARENH explicite (VNU/EPEX/PEG/TRVE)
    _signature = getattr(contract, "date_signature", None)
    if (
        _indexation_val == "fixe"
        and _signature
        and _signature < date(2025, 1, 1)
        and contract.end_date
        and date(2026, 1, 1) <= contract.end_date <= date(2027, 12, 31)
    ):
        results.append(
            {
                "rule_id": "R12",
                "level": "info",
                "message": (
                    f"Contrat fixe signe le {_signature.isoformat()} expirant le "
                    f"{contract.end_date.isoformat()} — renegocier avec clause post-ARENH "
                    "explicite (VNU, EPEX_SPOT_FR, PEG_DA, TRVE)."
                ),
            }
        )

    # R12d (INFO) : contrat indexe debutant apres 2026-01-01 sans reference explicite
    # Les 5 references valides (schemas.contract_v2_schemas.INDEXATION_REFERENCES) sont
    # TRVE, EPEX_SPOT_FR, PEG_DA, PEG_M+1, TTF_DA. Si indexation_reference vide ou
    # hors liste, c'est une ambiguite contractuelle (le fournisseur peut ajuster
    # unilateralement).
    #
    # Note : R12b et R12d sont intentionnellement cumulables. Un contrat indexe
    # long + sans cap + sans reference explicite releve des DEUX risques distincts
    # (exposition volatilite ET ambiguite contractuelle) — les deux messages
    # sont complementaires, pas redondants.
    _valid_refs = {"TRVE", "EPEX_SPOT_FR", "PEG_DA", "PEG_M+1", "TTF_DA"}
    _normalized_ref = _indexation_ref.upper().replace(" ", "")
    if (
        _is_indexed
        and contract.start_date
        and contract.start_date >= date(2026, 1, 1)
        and _normalized_ref not in _valid_refs
        and not _mentions_arenh  # R12a a deja flagge le cas ARENH
    ):
        results.append(
            {
                "rule_id": "R12",
                "level": "info",
                "message": (
                    "Contrat indexe post-ARENH sans reference explicite parmi "
                    "(TRVE, EPEX_SPOT_FR, PEG_DA, PEG_M+1, TTF_DA). "
                    "Preciser l'index pour eviter une revision unilaterale."
                ),
            }
        )

    # ── R13 — Accise / tier coherent ──
    # Accise electricite depend du volume annuel (tiers)
    # < 1 GWh : taux standard, >= 1 GWh : taux reduit, >= 10 GWh : exemptions possibles
    if energy == "elec":
        for a in annexes:
            vol = a.volume_commitment.annual_kwh if (hasattr(a, "volume_commitment") and a.volume_commitment) else None
            seg = (a.segment_enedis or "").upper()
            if vol and seg:
                if vol >= 10_000_000 and seg == "C5":  # 10 GWh en C5 = tres improbable
                    results.append(
                        {
                            "rule_id": "R13",
                            "level": "warning",
                            "message": f"Annexe {a.annexe_ref or a.id}: volume {vol / 1_000_000:.1f} GWh en C5 — verifier segment/accise",
                        }
                    )

    # ── R14 — Volume engage (tolerance / penalite) ──
    for a in annexes:
        if not a.volume_commitment:
            continue
        vc = a.volume_commitment
        if (vc.penalty_eur_kwh_above or vc.penalty_eur_kwh_below) and not vc.annual_kwh:
            results.append(
                {
                    "rule_id": "R14",
                    "level": "warning",
                    "message": f"Penalite definie sans volume engage pour {a.annexe_ref or a.id}",
                }
            )
        if vc.annual_kwh and vc.annual_kwh <= 0:
            results.append(
                {
                    "rule_id": "R14",
                    "level": "error",
                    "message": f"Volume engage negatif ou nul pour {a.annexe_ref or a.id}",
                }
            )

    # ── R15 — Option tarifaire / segment compatible ──
    from schemas.contract_v2_schemas import TARIFF_OPTIONS_BY_SEGMENT

    _valid_options = {seg: {o["value"] for o in opts} for seg, opts in TARIFF_OPTIONS_BY_SEGMENT.items()}
    for a in annexes:
        seg = (a.segment_enedis or "").upper()
        opt = a.tariff_option.value if a.tariff_option else None
        if seg and opt and seg in _valid_options:
            if opt not in _valid_options[seg]:
                results.append(
                    {
                        "rule_id": "R15",
                        "level": "error",
                        "message": f"Annexe {a.annexe_ref or a.id}: option {opt.upper()} incompatible avec segment {seg}",
                    }
                )
        # Gaz + option tarifaire elec
        if energy == "gaz" and a.tariff_option and a.tariff_option.value in ("hp_hc", "cu4", "mu4", "cu", "lu"):
            results.append(
                {
                    "rule_id": "R15",
                    "level": "warning",
                    "message": f"Annexe {a.annexe_ref or a.id}: option tarifaire elec ({a.tariff_option.value}) sur contrat gaz",
                }
            )

    # ── R16 — Expiration et couverture ──
    if contract.contract_status and contract.contract_status.value == "expired":
        results.append(
            {
                "rule_id": "R16",
                "level": "warning",
                "message": "Contrat expire — verifier couverture factures et renouvellement",
            }
        )
    # Annexe override active sans grille prix
    for a in annexes:
        if a.has_price_override and not a.pricing_overrides:
            results.append(
                {
                    "rule_id": "R16",
                    "level": "error",
                    "message": f"Annexe {a.annexe_ref or a.id}: override prix active sans grille tarifaire",
                }
            )
    # Prix indexe sans source
    if contract.offer_indexation and contract.offer_indexation.value in (
        "indexe",
        "indexe_trve",
        "indexe_peg",
        "indexe_spot",
    ):
        if not contract.pricing_lines:
            results.append(
                {
                    "rule_id": "R16",
                    "level": "error",
                    "message": "Contrat indexe sans grille tarifaire de reference",
                }
            )

    # ── Prix unitaire anormal (bonus, non numerote) ──
    for p in contract.pricing_lines:
        if p.unit_price_eur_kwh:
            threshold = PRICE_THRESHOLD_ELEC if energy == "elec" else PRICE_THRESHOLD_GAZ
            if p.unit_price_eur_kwh > threshold:
                results.append(
                    {
                        "rule_id": "R7",
                        "level": "warning",
                        "message": f"Prix {p.period_code} anormalement eleve: {p.unit_price_eur_kwh:.4f} EUR/kWh (seuil {threshold})",
                    }
                )

    return results


def _as_float(v):
    """Cast Decimal (from Numeric columns) to float for API output. Passes None through."""
    return float(v) if v is not None else None


def resolve_pricing(db: Optional[Session], annexe: ContractAnnexe) -> List[Dict[str, Any]]:
    """Retourne pricing effectif avec cascade: override annexe > cadre > fallback colonnes plates.

    Chaque ligne porte 'source': 'override' | 'cadre'.
    """
    # 1. Override annexe
    if annexe.has_price_override and annexe.pricing_overrides:
        return [
            {
                "period_code": p.period_code,
                "season": p.season,
                "unit_price_eur_kwh": _as_float(p.unit_price_eur_kwh),
                "subscription_eur_month": _as_float(p.subscription_eur_month),
                "source": "override",
            }
            for p in annexe.pricing_overrides
        ]

    # 2. Heritage V2 ContratCadre (colonnes flat prix_*_eur_kwh).
    # V2 annexes reference ContratCadre via `annexe.cadre` (cadre_id FK).
    # V2 ContratCadre has no pricing_lines relationship — only flat columns.
    v2_cadre = annexe.cadre
    if v2_cadre:
        v2_lines = []
        if v2_cadre.prix_base_eur_kwh is not None:
            v2_lines.append(
                {
                    "period_code": "BASE",
                    "season": "ANNUEL",
                    "unit_price_eur_kwh": _as_float(v2_cadre.prix_base_eur_kwh),
                    "source": "cadre",
                }
            )
        if v2_cadre.prix_hp_eur_kwh is not None:
            v2_lines.append(
                {
                    "period_code": "HP",
                    "season": "ANNUEL",
                    "unit_price_eur_kwh": _as_float(v2_cadre.prix_hp_eur_kwh),
                    "source": "cadre",
                }
            )
        if v2_cadre.prix_hc_eur_kwh is not None:
            v2_lines.append(
                {
                    "period_code": "HC",
                    "season": "ANNUEL",
                    "unit_price_eur_kwh": _as_float(v2_cadre.prix_hc_eur_kwh),
                    "source": "cadre",
                }
            )
        if v2_lines:
            return v2_lines

    # 3. Legacy EnergyContract cadre (grille structuree pricing_lines)
    cadre = annexe.contrat_cadre
    if cadre and cadre.pricing_lines:
        return [
            {
                "period_code": p.period_code,
                "season": p.season,
                "unit_price_eur_kwh": _as_float(p.unit_price_eur_kwh),
                "subscription_eur_month": _as_float(p.subscription_eur_month),
                "source": "cadre",
            }
            for p in cadre.pricing_lines
        ]

    # 4. Legacy EnergyContract fallback (colonnes plates)
    if cadre:
        lines = []
        if cadre.price_base_eur_kwh:
            lines.append(
                {
                    "period_code": "BASE",
                    "season": "ANNUEL",
                    "unit_price_eur_kwh": _as_float(cadre.price_base_eur_kwh),
                    "source": "cadre",
                }
            )
        if cadre.price_hp_eur_kwh:
            lines.append(
                {
                    "period_code": "HP",
                    "season": "ANNUEL",
                    "unit_price_eur_kwh": _as_float(cadre.price_hp_eur_kwh),
                    "source": "cadre",
                }
            )
        if cadre.price_hc_eur_kwh:
            lines.append(
                {
                    "period_code": "HC",
                    "season": "ANNUEL",
                    "unit_price_eur_kwh": _as_float(cadre.price_hc_eur_kwh),
                    "source": "cadre",
                }
            )
        if cadre.fixed_fee_eur_per_month:
            lines.append(
                {
                    "period_code": "BASE",
                    "season": "ANNUEL",
                    "subscription_eur_month": _as_float(cadre.fixed_fee_eur_per_month),
                    "source": "cadre",
                }
            )
        return lines

    return []
