"""
PROMEOS — Bill Intelligence anomaly_detector (Sprint C-5 Phase 5.1, ADR-013).

Différenciateur produit cardinal Phase C : détection rules-based pure d'anomalies de
facturation énergie (CFO scrute factures, vs Deepki/Spacewell généralistes).

Détecteurs cardinaux MVP :
- R19 : VNU dormant facturé (Σ amount_eur sur EnergyInvoiceLine TAX label LIKE '%VNU%' > 0
        sur invoice sans usage attendu — heuristique consumption < 100 kWh)
- R20 : Capacité variance > 5% (NETWORK kVA facturé vs PowerContract.ps_par_poste_kva[code])

Adaptations Phase 5.1.0 (post-diagnostic mini-audit) :
- FK invoice_id → energy_invoices.id (modèle EnergyInvoice, pas Facture)
- R19 scan EnergyInvoiceLine line_type=TAX + label LIKE '%VNU%' (vs invoice.vnu_montant inexistant)
- R20 scan EnergyInvoiceLine line_type=NETWORK + unit LIKE '%kVA%' + JSON dict navigation
       ps_par_poste_kva[period_code]
- JOIN chain : EnergyInvoice → Site → Meter → PowerContract (pas DeliveryPoint direct)

Seuils YAML SoT (sources_reglementaires.yaml domain bill_intelligence) :
- BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR : 0.01 EUR
- BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT : 5.0 %

Pipeline résilience par-action : try/except chaque détecteur — anomalies indépendantes
ne se cassent pas mutuellement.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from config.regulatory_sources_loader import get_term_value
from models import (
    BillAnomaly,
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    Meter,
    PowerContract,
)
from models.enums import BillAnomalySeverity, InvoiceLineType

_logger = logging.getLogger(__name__)

# Phase L8.2 — alias pour éviter répétition `BillAnomalySeverity.X.value`
_SEV_CRITICAL = BillAnomalySeverity.CRITICAL.value
_SEV_WARNING = BillAnomalySeverity.WARNING.value

# Phase L11.1 — type alias pour pré-partition invoice.lines
LinesByType = dict[InvoiceLineType, list[EnergyInvoiceLine]]


def _partition_invoice_lines(invoice: EnergyInvoice) -> LinesByType:
    """Phase L11.1 — Pré-partition unique invoice.lines par line_type (audit P1 cumul L8+L9+L10).

    Avant L11 : 6 détecteurs (R21+R22+R23+R24+R28+R31) itéraient invoice.lines
    indépendamment avec un filter `line.line_type == X` Python-side. Sur 30 lignes
    × 6 détecteurs × 1000 factures batch = 180 000 itérations Python.

    Après L11 : 1 traversal unique au pipeline + 6 lookups O(1) sur dict =
    30 000 itérations + 6 dict accesses.

    Returns:
        dict {InvoiceLineType.X: [lines]} initialisé pour 4 line_types canoniques
        (ENERGY/NETWORK/TAX/OTHER) — toujours initialisé avec listes vides
        pour éviter KeyError sur lookup détecteur.
    """
    partitioned: LinesByType = {
        InvoiceLineType.ENERGY: [],
        InvoiceLineType.NETWORK: [],
        InvoiceLineType.TAX: [],
        InvoiceLineType.OTHER: [],
    }
    for line in invoice.lines or []:
        if line.line_type in partitioned:
            partitioned[line.line_type].append(line)
    return partitioned


def _resolve_lines(invoice: EnergyInvoice, lines_by_type: Optional[LinesByType]) -> LinesByType:
    """Phase L11.6 audit fix F2 — Helper DRY pour pattern fallback partition.

    Avant L11.6 : ternaire `lines_by_type if lines_by_type is not None else
    _partition_invoice_lines(invoice)` répété verbatim 6× (R21/R22/R23/R24/R28/R31).
    Audit code-reviewer P1 reuse : 1 modification = 6 callsites cohérents.

    Args:
        invoice : EnergyInvoice cible (utilisé en mode unitaire)
        lines_by_type : pré-partition pipeline ou None

    Returns:
        LinesByType (dict 4 line_types canoniques)
    """
    return lines_by_type if lines_by_type is not None else _partition_invoice_lines(invoice)


def _resolve_contract(
    invoice: EnergyInvoice,
    *,
    contract_cache: Optional[dict[int, EnergyContract]] = None,
) -> Optional[EnergyContract]:
    """Phase L8.2 + L12.1 — Helper guard partagé R25/R28/R30.

    Phase L8.2 : centralise check `contract_id` + accès `invoice.contract`.
    Phase L12.1 : kwarg `contract_cache` optionnel pour mode batch (P1 efficiency
    cumul L8+L9+L10+L11). Pré-rempli par caller via `build_contract_cache()`
    qui charge en 1 SELECT IN tous les contrats du batch (vs N lazy-loads séparés).

    Args:
        invoice : EnergyInvoice cible
        contract_cache : dict {contract_id: EnergyContract} optionnel (mode batch)

    Returns:
        EnergyContract si invoice.contract_id non null, sinon None.
        Mode cached : lookup O(1) sur dict.
        Mode unitaire : invoice.contract (lazy-load 1er accès, identity map ensuite).
    """
    if invoice.contract_id is None:
        return None
    if contract_cache is not None:
        # Phase L12.5 audit fix F1 — cache miss warning explicite (avant : None
        # silencieux → faux négatifs R25/R28/R30 non observables si caller a
        # oublié contract_id du cache).
        result = contract_cache.get(invoice.contract_id)
        if result is None:
            _logger.warning(
                "contract_cache miss invoice_id=%s contract_id=%s — fallback skip",
                invoice.id,
                invoice.contract_id,
            )
        return result
    return invoice.contract  # fallback lazy-load mode unitaire


_AnomalyCode = Literal["R19", "R20", "R21", "R22", "R23", "R24", "R25", "R26", "R27", "R28", "R29", "R30", "R31"]


def _build_doublon_anomaly(
    *,
    invoice: EnergyInvoice,
    code: _AnomalyCode,
    candidate_lines: list[EnergyInvoiceLine],
    critical_eur: float,
    regulatory_ref: str,
    extra_details: Optional[dict] = None,
) -> Optional[BillAnomaly]:
    """Phase L10.1 + L10.3 — Helper anti-doublon partagé R23 + R31.

    Pattern cardinal cumulé L9.5 + L10.1 + L10.3 :
    - len(candidate_lines) < 2 → None (pas de doublon possible)
    - total_doublon = sum_total - max() (robuste ordre arbitraire — L9.5 sum-max)
    - PII sanitization systématique duplicate_labels (CWE-532/359)
    - Cap _DOUBLON_DETAIL_CAP_LINES (constante L10.3 — anti-magic number)
    - severity bascule sur critical_eur (YAML SoT)
    - L10.3 audit fix F4 : extra_details mergé EN PREMIER (clés helper canoniques
      écrasent toujours, anti-collision silencieuse sur "duplicate_count" etc.)
    - L10.3 audit fix F1+F3 : code Literal + candidate_lines typed
    - L10.3 audit fix F7 : pré-pass unique sur candidate_lines (4 passes → 1)

    Args:
        invoice : EnergyInvoice cible
        code : Literal R19→R31 (anti-typo)
        candidate_lines : lignes pré-filtrées (TAX accise, NETWORK même période…)
        critical_eur : seuil bascule warning→critical (YAML SoT)
        regulatory_ref : citation source juridique cardinale
        extra_details : dict optionnel mergé EN PREMIER (clés helper prévalent)

    Returns:
        BillAnomaly ou None si pas de doublon
    """
    if len(candidate_lines) < 2:
        return None

    # Phase L10.3 F7 — pré-pass unique : extraction simultanée amounts + ids + labels
    amounts: list[float] = []
    capped_ids: list[int] = []
    capped_labels: list[str] = []
    for idx, line in enumerate(candidate_lines):
        amounts.append(float(line.amount_eur or 0))
        if idx < _DOUBLON_DETAIL_CAP_LINES:
            capped_ids.append(line.id)
            capped_labels.append(_sanitize_pii_label(line.label or ""))

    total_doublon_eur = sum(amounts) - max(amounts)
    severity = _SEV_CRITICAL if total_doublon_eur > critical_eur else _SEV_WARNING

    # Phase L10.3 F4 — extra_details mergé EN PREMIER : clés helper canoniques
    # écrasent toujours (anti-collision silencieuse).
    details: dict = dict(extra_details) if extra_details else {}
    details.update(
        {
            "duplicate_count": len(candidate_lines),
            "duplicate_lines_ids": capped_ids,
            "duplicate_labels": capped_labels,
            "montant_anomalie_eur": round(total_doublon_eur, 2),
            "regulatory_ref": regulatory_ref,
        }
    )

    return BillAnomaly(
        invoice_id=invoice.id,
        code=code,
        severity=severity,
        threshold_value=Decimal(str(critical_eur)),
        actual_value=Decimal(str(round(total_doublon_eur, 2))),
        details_json=details,
    )


# ─── Helpers ────────────────────────────────────────────────────────────────

# Sprint C-7 Phase 7.8 — D-Audit-Phase7-TURPE-7-Codes-Obsolete-006 (fix audit deep) :
# Codes TURPE 7 OFFICIEL (CRE délibération 2025-78 du 13/03/2025, JO 14/05/2025) :
#   - "P" (Pointe), "HPH" (Heures Pleines Hautes), "HCH" (Heures Creuses Hautes),
#     "HPB" (Heures Pleines Basses), "HCB" (Heures Creuses Basses)
#   - "HP", "HC" : tarification standard BT (TURPE 7 BT≤36 kVA)
#   - "BASE" : tarif unique BT
#
# Codes LEGACY TURPE 6 (obsolètes 1/08/2025) conservés pour rétro-compat parsing
# factures historiques pré-TURPE 7 (data fixtures HELIOS/MERIDIAN + clients ayant
# encore des factures 2024-2025 à analyser) :
#   - "HPE" (Heures Pleines Été), "HCE" (Heures Creuses Été)
#   - "PM" (Pointe Mobile, TURPE 5/6 obsolète)
#   - "POINTE" (terme générique pré-TURPE 7)
#
# Ordre cardinal : codes longs d'abord (anti-overlap label parsing word-boundary).
_PERIOD_CODES_KNOWN_TURPE_7 = ["HPH", "HCH", "HPB", "HCB", "P", "HP", "HC", "BASE"]
_PERIOD_CODES_LEGACY_TURPE_6 = ["HPE", "HCE", "PM", "POINTE"]
_PERIOD_CODES_KNOWN = [
    *_PERIOD_CODES_KNOWN_TURPE_7,
    *_PERIOD_CODES_LEGACY_TURPE_6,
]

# Phase L9.5 — regex accise/CSPE/TICFE/contrib service public partagée R22 + R31.
# Audit code-reviewer Phase L9 P1 finding 2 : avant L9.5 dupliquée verbatim
# entre détecteurs → risque divergence si R22 patché et R31 oublié (ou vice-versa).
_ACCISE_PATTERN = re.compile(r"\b(accise|ticfe|cspe|contrib.*service.*public)", re.IGNORECASE)

# Phase L11.6 audit fix F1 — regex TVA module-level (avant : recompilée à chaque
# appel de detect_r24_tva_rate_mismatch ; pattern cohérent _ACCISE_PATTERN).
_TVA_PATTERN = re.compile(r"\bTVA\b|\bVAT\b", re.IGNORECASE)

# Phase L10.3 audit fix F5 — cap labels/ids dans details_json (mémoire + PII).
# Cohérent R19 vnu_labels (Sprint C-7 Phase 7.7), R23 + R31 doublons (helper L10.1).
_DOUBLON_DETAIL_CAP_LINES = 5

# Sprint C-7 Phase 7.7 Lot A — D-Sprint-C7-BillAnomaly-PII-Vnu-Labels-Sanitization-001 :
# regex sanitization SIREN (9 chiffres) / SIRET (14 chiffres) / PRM/PCE (14 chiffres) /
# PDL (14 chiffres). Évite leak PII dans details_json.vnu_labels (security-auditor SEC-002).
#
# Sprint C-8 Phase 8.2 — D-Audit-Phase7-PII-Sanitization-Extended-001 P1 SEC :
# extension cumulée patterns email/téléphone FR/IBAN FR/RIB pour couverture cross-fournisseur
# (EDF/Engie/TotalEnergies labels VNU peuvent contenir email contact, IBAN domiciliation, etc.).
# Anti-CWE-532 (Insertion of Sensitive Information into Log File) + CWE-359 (Privacy).
# Phase D-1 hotfix — D-Audit-C8-PII-Patterns-Order-006 P1 SEC :
# Phase D-3 Tier 2 SEC-2 fix P1-AUDIT-D-014 : SoT centralisé `services/security/pii_sanitizer.py`.
# Les patterns/helpers ci-dessous sont des aliases rétro-compatibles vers le SoT unique.
from services.security.pii_sanitizer import (
    PII_VALUE_PATTERNS as _PII_PATTERNS,
)
from services.security.pii_sanitizer import (
    sanitize_pii_value as _sanitize_pii_label,
)


def _resolve_period_code(line: EnergyInvoiceLine) -> Optional[str]:
    """Helper cardinal Phase 5.1.0 : extraire period_code depuis EnergyInvoiceLine.

    Matching `ps_par_poste_kva[period_code]` dépend de cette extraction.

    Priorité 1 : champ direct `line.period_code` si présent + non vide
    Priorité 2 : `line.meta_json["period_code"]` si dict JSON
    Priorité 3 : extraction depuis `line.label` (recherche tokens HPH/HCH/HPB/HCB/POINTE/BASE/HP/HC)
    """
    # Priorité 1
    if hasattr(line, "period_code") and line.period_code:
        return line.period_code

    # Priorité 2
    meta = getattr(line, "meta_json", None)
    if meta:
        if isinstance(meta, dict):
            code = meta.get("period_code")
            if code:
                return code
        elif isinstance(meta, str):
            # meta_json stocké en TEXT JSON — best-effort parse
            try:
                import json

                parsed = json.loads(meta)
                if isinstance(parsed, dict) and parsed.get("period_code"):
                    return parsed["period_code"]
            except (ValueError, TypeError):
                pass

    # Priorité 3 : label parsing
    # Sprint C-7 Phase 7.7 Lot A — D-Sprint-C7-BillAnomaly-Word-Boundary-Regex-001 :
    # word-boundary `\b<code>\b` (vs substring) anti-faux-positifs (ex : "CHC" ne match plus "HC").
    if line.label:
        label_upper = line.label.upper()
        for code in _PERIOD_CODES_KNOWN:
            if re.search(rf"\b{re.escape(code)}\b", label_upper):
                return code

    return None


# ─── R19 : VNU dormant ──────────────────────────────────────────────────────


def detect_r19_vnu_dormant(invoice: EnergyInvoice, db: Session) -> Optional[BillAnomaly]:
    """R19 : détecte VNU > seuil sur invoice sans usage attendu.

    Adaptation Phase 5.1.0 : scan EnergyInvoiceLine line_type=TAX + label LIKE '%VNU%'
    (vs invoice.vnu_montant direct inexistant sur modèle EnergyInvoice).

    Seuil : YAML BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR (default 0.01 EUR).

    Retour : 0 ou 1 BillAnomaly (NON ajoutée à la session — caller responsable).
    """
    from models.enums import InvoiceLineType

    threshold = Decimal(str(get_term_value("BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR")))

    vnu_lines = (
        db.query(EnergyInvoiceLine)
        .filter(
            EnergyInvoiceLine.invoice_id == invoice.id,
            EnergyInvoiceLine.line_type == InvoiceLineType.TAX.value,
            or_(
                EnergyInvoiceLine.label.ilike("%VNU%"),
                EnergyInvoiceLine.label.ilike("%VERSEMENT NUCLEAIRE%"),
                EnergyInvoiceLine.label.ilike("%VERSEMENT NUCLÉAIRE%"),
            ),
        )
        .all()
    )

    vnu_total = sum((Decimal(str(line.amount_eur or 0)) for line in vnu_lines), Decimal("0"))
    if vnu_total <= threshold:
        return None

    # Sprint C-5 Phase 5.6 F2 fix : energy_kwh IS NULL = facture acompte sans relève
    # (cas légitime EDF/Engie B2B). Distinguer NULL de 0 (consommation inconnue ≠ 0)
    # évite faux positif systématique sur factures acompte avec VNU.
    if invoice.energy_kwh is None:
        return None

    # Phase L14.2 — seuil YAML SoT (no fake code) : avant L14.2 hardcoded 100
    consumption_threshold_kwh = float(get_term_value("BILL_ANOMALY_VNU_DORMANT_CONSUMPTION_KWH"))
    consumption = float(invoice.energy_kwh)
    if consumption > consumption_threshold_kwh:
        return None

    return BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity=_SEV_WARNING,
        threshold_value=float(threshold),
        actual_value=float(vnu_total),
        details_json={
            "vnu_total_eur": float(vnu_total),
            "vnu_lines_count": len(vnu_lines),
            "consumption_kwh": consumption,
            "vnu_labels": [_sanitize_pii_label(line.label or "") for line in vnu_lines[:5]],
            "explanation": "VNU facturé > seuil sans usage attendu détecté (consumption < 100 kWh).",
        },
    )


# ─── R20 : Capacité variance ────────────────────────────────────────────────


def detect_r20_capacity_variance(invoice: EnergyInvoice, db: Session) -> list[BillAnomaly]:
    """R20 : détecte écart capacité facturée vs souscription contractuelle > 5%.

    Adaptation Phase 5.1.0 :
    - Scan EnergyInvoiceLine line_type=NETWORK + unit LIKE '%kVA%'
    - JOIN chain : EnergyInvoice → Site → Meter → PowerContract
    - Navigation JSON dict : ps_par_poste_kva[period_code] avec matching cardinal

    Seuil : YAML BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT (default 5.0).

    Retour : LISTE de BillAnomaly (1 par poste tarifaire avec variance > seuil).
    """
    threshold_pct = float(get_term_value("BILL_ANOMALY_CAPACITY_VARIANCE_THRESHOLD_PCT"))

    if not invoice.site_id:
        return []

    # Sprint C-5 Phase 5.5 fix B2 (audit bill-intelligence) : filtrer ELECTRICITY +
    # tri par puissance souscrite descendante pour cibler le meter principal
    # (PMA HTA 500 kVA prioritaire vs sous-compteur BT 36 kVA). Sans ce filtre,
    # `.first()` retournait potentiellement le sous-compteur sans PowerContract,
    # produisant un `[]` silencieux sur sites multi-meter (faux négatifs R20).
    from models import EnergyVector
    from models.enums import InvoiceLineType

    meter = (
        db.query(Meter)
        .filter(
            Meter.site_id == invoice.site_id,
            Meter.energy_vector == EnergyVector.ELECTRICITY,
            Meter.is_active.is_(True),
        )
        .order_by(Meter.subscribed_power_kva.desc().nullslast())
        .first()
    )
    if not meter:
        return []

    # PowerContract actif sur la période facturée (chevauchement)
    period_start = invoice.period_start
    period_end = invoice.period_end
    if not period_start or not period_end:
        return []

    contract = (
        db.query(PowerContract)
        .filter(
            PowerContract.meter_id == meter.id,
            PowerContract.date_debut <= period_end,
            or_(
                PowerContract.date_fin >= period_start,
                PowerContract.date_fin.is_(None),
            ),
        )
        .first()
    )
    if not contract or not contract.ps_par_poste_kva:
        return []

    # Lignes NETWORK kVA
    network_lines = (
        db.query(EnergyInvoiceLine)
        .filter(
            EnergyInvoiceLine.invoice_id == invoice.id,
            EnergyInvoiceLine.line_type == InvoiceLineType.NETWORK.value,
            EnergyInvoiceLine.unit.ilike("%kVA%"),
        )
        .all()
    )

    anomalies: list[BillAnomaly] = []
    ps_dict = contract.ps_par_poste_kva  # JSON dict {HPH: 36, HCH: 36, ...}

    for line in network_lines:
        period_code = _resolve_period_code(line)
        if not period_code:
            continue

        capacite_souscrite = ps_dict.get(period_code)
        if not capacite_souscrite or capacite_souscrite <= 0:
            continue

        # Sprint C-5 Phase 5.8 fix G2 (audit transversal AXE 3 P0-1) : line.qty IS NULL
        # = donnée manquante (estimation acompte sans relève kVA), pas d'anomalie inférable.
        # Réplique pattern F2 R19 Phase 5.6 sur ligne capacité.
        if line.qty is None:
            continue
        capacite_facturee = float(line.qty)
        if capacite_facturee == 0:
            continue

        variance_pct = abs(capacite_facturee - capacite_souscrite) / capacite_souscrite * 100
        if variance_pct <= threshold_pct:
            continue

        # Phase L8.1 — seuil critical YAML SoT (avant : threshold_pct × 2 implicite)
        critical_pct = float(get_term_value("BILL_ANOMALY_CAPACITY_VARIANCE_CRITICAL_PCT"))
        severity = _SEV_CRITICAL if variance_pct > critical_pct else _SEV_WARNING

        anomalies.append(
            BillAnomaly(
                invoice_id=invoice.id,
                code="R20",
                severity=severity,
                threshold_value=threshold_pct,
                actual_value=variance_pct,
                details_json={
                    "period_code": period_code,
                    "capacite_facturee_kva": capacite_facturee,
                    "capacite_souscrite_kva": capacite_souscrite,
                    "variance_pct": round(variance_pct, 2),
                    "contract_id": contract.id,
                    "line_id": line.id,
                },
            )
        )

    return anomalies


# ─── R21 CTA mauvais calcul (Phase H Jean-Marc CFO) ────────────────────────


def detect_r21_cta_mismatch(
    invoice: EnergyInvoice,
    db: Session,
    *,
    lines_by_type: Optional[LinesByType] = None,
) -> Optional[BillAnomaly]:
    """R21 — CTA calculée incorrectement vs taux réglementaire (CRE 2026-14).

    Persona Jean-Marc CFO : ROI 3-5 k€/an, formule complexe (15 % distribution
    élec depuis 02/2026 + 5 % transport ≥50 kV) avec ~30 % d'erreurs constatées.

    Phase L11.2 — `lines_by_type` kwarg optionnel pour mode batch (pré-partition
    unique au pipeline). Fallback à `invoice.lines or []` si non fourni
    (mode unitaire ad-hoc).

    Returns:
        BillAnomaly ou None
    """
    from datetime import date as _date

    parts = _resolve_lines(invoice, lines_by_type)
    network_lines = [line for line in parts[InvoiceLineType.NETWORK] if line.amount_eur is not None]
    cta_lines = [line for line in parts[InvoiceLineType.TAX] if line.label and "CTA" in line.label.upper()]
    if not network_lines or not cta_lines:
        return None

    turpe_total = sum(float(line.amount_eur or 0) for line in network_lines)
    cta_facturee = sum(float(line.amount_eur or 0) for line in cta_lines)
    if turpe_total <= 0:
        return None

    # Phase L8.1 — seuils YAML SoT (no fake code)
    cta_rate_post_2026 = float(get_term_value("CTA_ELEC_DISTRIBUTION_PCT")) / 100  # SoT 15%
    # Phase L14.2 — taux historique YAML SoT (avant : hardcoded 0.2193)
    cta_rate_pre_2026 = float(get_term_value("CTA_ELEC_DISTRIBUTION_PRE_2026_PCT")) / 100  # SoT 21.93%
    threshold_pct = float(get_term_value("BILL_ANOMALY_CTA_THRESHOLD_PCT"))
    threshold_min_eur = float(get_term_value("BILL_ANOMALY_CTA_MIN_EUR"))
    critical_eur = float(get_term_value("BILL_ANOMALY_CTA_CRITICAL_EUR"))

    # Date de référence : period_start ou issue_date
    ref_date = invoice.period_start or invoice.issue_date or _date.today()
    cutover = _date(2026, 2, 1)
    cta_rate = cta_rate_post_2026 if ref_date >= cutover else cta_rate_pre_2026
    cta_attendue = turpe_total * cta_rate
    if cta_attendue <= 0:
        return None

    ecart_eur = cta_facturee - cta_attendue
    ecart_pct = abs(ecart_eur) / cta_attendue * 100

    if ecart_pct < threshold_pct or abs(ecart_eur) < threshold_min_eur:
        return None

    severity = _SEV_CRITICAL if abs(ecart_eur) > critical_eur else _SEV_WARNING
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R21",
        severity=severity,
        threshold_value=Decimal(str(threshold_pct)),
        actual_value=Decimal(str(round(ecart_pct, 2))),
        details_json={
            "turpe_total_eur": round(turpe_total, 2),
            "cta_facturee_eur": round(cta_facturee, 2),
            "cta_attendue_eur": round(cta_attendue, 2),
            "ecart_eur": round(ecart_eur, 2),
            "ecart_pct": round(ecart_pct, 2),
            "cta_rate_applied": cta_rate,
            "regulatory_ref": "Arrêté CTA 27/01/2026 (CRE 2026-14, JORF) — 15 % distribution élec",
            "montant_anomalie_eur": round(abs(ecart_eur), 2),
        },
    )


# ─── R28 Prix unitaire énergie ligne vs contrat (Phase L4 CFO ROI 3-8 k€/an) ──


def detect_r28_energy_unit_price_drift(
    invoice: EnergyInvoice,
    db: Session,
    *,
    lines_by_type: Optional[LinesByType] = None,
    contract_cache: Optional[dict[int, EnergyContract]] = None,
) -> Optional[BillAnomaly]:
    """R28 — Prix unitaire énergie facturé divergent vs `EnergyContract.price_ref_eur_per_kwh`.

    Persona Jean-Marc CFO : ROI 3-8 k€/an. Complément à R25 (abonnement) — vérifie
    cette fois le prix au kWh sur les lignes énergie. Cas typique : fournisseur
    applique le tarif "ouvert" au lieu du tarif contrat négocié, ou applique le
    nouveau tarif post-renouvellement plus tôt que l'échéance.

    Heuristique cardinale :
    - Identifier lignes ENERGY (line_type=ENERGY) avec `unit_price` non null
    - Récupérer prix contrat : `EnergyContract.price_ref_eur_per_kwh` (ou prix HP/HC si tariff_option défini)
    - Comparer chaque ligne unit_price vs prix contrat attendu
    - Écart > 5 % ET > 0,005 €/kWh absolu → R28 anomalie

    Sévérité : `critical` si écart > 0,02 €/kWh ; `warning` sinon

    Garde-fous (anti-faux positifs) :
    - Skip si invoice.contract_id manquant (pas de référence)
    - Skip si contract.price_ref_eur_per_kwh non défini
    - Skip si aucune ligne ENERGY avec unit_price (ex: facture forfaitaire)

    Returns:
        BillAnomaly ou None
    """
    contract = _resolve_contract(invoice, contract_cache=contract_cache)
    if contract is None or contract.price_ref_eur_per_kwh is None:
        return None
    prix_attendu_eur_kwh = float(contract.price_ref_eur_per_kwh)
    if prix_attendu_eur_kwh <= 0:
        return None

    # Phase L7.2 — seuils YAML SoT (no fake code)
    threshold_pct = float(get_term_value("BILL_ANOMALY_UNIT_PRICE_DRIFT_THRESHOLD_PCT"))
    threshold_abs = float(get_term_value("BILL_ANOMALY_UNIT_PRICE_DRIFT_ABSOLUTE_EUR_KWH"))
    critical_abs = float(get_term_value("BILL_ANOMALY_UNIT_PRICE_CRITICAL_EUR_KWH"))

    # Phase L11.2 — pré-partition `lines_by_type` (fallback si mode unitaire)
    parts = _resolve_lines(invoice, lines_by_type)
    energy_lines = [
        line for line in parts[InvoiceLineType.ENERGY] if line.unit_price is not None and line.unit_price > 0
    ]
    if not energy_lines:
        return None

    # Détection : la ligne avec le plus gros écart (worst case)
    worst_drift = None
    for line in energy_lines:
        unit_price = float(line.unit_price)
        ecart = unit_price - prix_attendu_eur_kwh
        ecart_pct = abs(ecart) / prix_attendu_eur_kwh * 100
        if ecart_pct < threshold_pct or abs(ecart) < threshold_abs:
            continue
        if worst_drift is None or abs(ecart) > abs(worst_drift["ecart_eur_kwh"]):
            worst_drift = {
                "line_id": line.id,
                "line_label": line.label,
                "qty_kwh": float(line.qty or 0),
                "unit_price_facture_eur_kwh": unit_price,
                "ecart_eur_kwh": ecart,
                "ecart_pct": ecart_pct,
            }

    if worst_drift is None:
        return None

    # Estimation impact € : delta unit_price × qty (kWh) sur la ligne
    montant_impact = round(abs(worst_drift["ecart_eur_kwh"]) * worst_drift["qty_kwh"], 2)
    severity = _SEV_CRITICAL if abs(worst_drift["ecart_eur_kwh"]) > critical_abs else _SEV_WARNING

    return BillAnomaly(
        invoice_id=invoice.id,
        code="R28",
        severity=severity,
        threshold_value=Decimal(str(threshold_pct)),
        actual_value=Decimal(str(round(worst_drift["ecart_pct"], 2))),
        details_json={
            "prix_attendu_eur_kwh": round(prix_attendu_eur_kwh, 4),
            "prix_facture_eur_kwh": round(worst_drift["unit_price_facture_eur_kwh"], 4),
            "ecart_eur_kwh": round(worst_drift["ecart_eur_kwh"], 4),
            "ecart_pct": round(worst_drift["ecart_pct"], 2),
            "qty_kwh": round(worst_drift["qty_kwh"], 1),
            "line_id": worst_drift["line_id"],
            "line_label": worst_drift["line_label"],
            "contract_id": contract.id,
            "regulatory_ref": "EnergyContract.price_ref_eur_per_kwh (clause contractuelle)",
            "montant_anomalie_eur": montant_impact,
        },
    )


# ─── R27 Cross-validation conso facturée vs MeterReading (Phase L3 CFO ROI 5-10 k€) ──


def detect_r27_consumption_meter_drift(invoice: EnergyInvoice, db: Session) -> Optional[BillAnomaly]:
    """R27 — Cross-validation `invoice.energy_kwh` vs `Σ MeterReading.value_kwh` période.

    Persona Jean-Marc CFO : ROI 5-10 k€/an cardinal. Cas typique : fournisseur
    facture une conso "estimée" significativement supérieure à la conso réelle
    mesurée par compteur (PRM/PCE) — détection anti-fraude majeure.

    Heuristique cardinale :
    - JOIN Site → Meter (energy_vector compatible)
    - Σ MeterReading.value_kwh sur période [period_start, period_end]
    - Compare avec invoice.energy_kwh (TTC)
    - Écart > 10 % ET > 100 kWh absolu → R27 anomalie
    - Sévérité : `critical` si écart > 1000 kWh ; `warning` sinon

    Garde-fous (anti-faux positifs) :
    - Skip si invoice.period_start/period_end manquants (pas de fenêtre temporelle)
    - Skip si pas de Meter sur le site (cas legacy sans télérelevé)
    - Skip si Σ readings = 0 (compteur silencieux : autre anomalie hors scope R27)
    - Skip si moins de 7 readings sur la période (couverture insuffisante)

    Returns:
        BillAnomaly ou None
    """
    from models.energy_models import Meter, MeterReading

    if not invoice.energy_kwh or invoice.energy_kwh <= 0:
        return None
    if not invoice.period_start or not invoice.period_end:
        return None

    # Phase L13 + L13.4 — 1 seul SELECT agrégé (sum + count) sur partition
    # (meter_id, timestamp). Évite double scan MeterReading vs avant L13.
    from datetime import datetime, time

    from sqlalchemy import func

    # Phase L13.4 audit fix F1 (P1 CRITIQUE correctness pré-existant depuis L3) —
    # invoice.period_start et period_end sont Date, MeterReading.timestamp est
    # DateTime. SQLAlchemy coerce implicitement Date → 00:00:00 → si l'on filtre
    # `timestamp <= period_end` (Date), on exclut TOUTES les lectures du dernier
    # jour après 00:00:00 (soit ~23h sur 24 d'une CDC horaire). Faux positif R27
    # systématique sur tout site avec télémesure active.
    period_start_dt = datetime.combine(invoice.period_start, time.min)  # 00:00:00
    period_end_dt = datetime.combine(invoice.period_end, time(23, 59, 59))

    # Phase L13.4 audit fix F2 — .one_or_none() défensif (vs .one() qui lève
    # NoResultFound si JOIN strict + table vide). func.sum + func.count
    # retourne toujours 1 row agrégée en SQL standard, mais defense-in-depth.
    # Phase L13.4 audit fix F3 — count() sans argument plus efficace que
    # count(id) (NULL check redondant sur PK NOT NULL).
    agg_row = (
        db.query(func.sum(MeterReading.value_kwh), func.count())
        .join(Meter, Meter.id == MeterReading.meter_id)
        .filter(
            Meter.site_id == invoice.site_id,
            MeterReading.timestamp >= period_start_dt,
            MeterReading.timestamp <= period_end_dt,
        )
        .one_or_none()
    )
    if agg_row is None:
        return None
    sum_readings, count_readings = agg_row[0], agg_row[1] or 0

    if sum_readings is None or sum_readings <= 0:
        return None

    # Phase L8.1 — seuils YAML SoT (no fake code)
    min_readings = int(get_term_value("BILL_ANOMALY_METER_DRIFT_MIN_READINGS"))
    threshold_pct = float(get_term_value("BILL_ANOMALY_METER_DRIFT_THRESHOLD_PCT"))
    threshold_min_kwh = float(get_term_value("BILL_ANOMALY_METER_DRIFT_MIN_KWH"))
    critical_kwh = float(get_term_value("BILL_ANOMALY_METER_DRIFT_CRITICAL_KWH"))

    if count_readings < min_readings:
        return None

    conso_facturee = float(invoice.energy_kwh)
    conso_mesuree = float(sum_readings)
    ecart_kwh = conso_facturee - conso_mesuree
    ecart_pct = abs(ecart_kwh) / conso_mesuree * 100 if conso_mesuree > 0 else 0

    if ecart_pct < threshold_pct or abs(ecart_kwh) < threshold_min_kwh:
        return None

    severity = _SEV_CRITICAL if abs(ecart_kwh) > critical_kwh else _SEV_WARNING
    # Estimation impact € via prix marginal CRE T4 2025 ETI tertiaire (130 €/MWh)
    from doctrine.constants import PRICE_ELEC_ETI_2026_EUR_PER_MWH

    montant_impact_eur = round(abs(ecart_kwh) / 1000 * PRICE_ELEC_ETI_2026_EUR_PER_MWH, 2)

    return BillAnomaly(
        invoice_id=invoice.id,
        code="R27",
        severity=severity,
        threshold_value=Decimal(str(threshold_pct)),
        actual_value=Decimal(str(round(ecart_pct, 2))),
        details_json={
            "conso_facturee_kwh": round(conso_facturee, 1),
            "conso_mesuree_kwh": round(conso_mesuree, 1),
            "ecart_kwh": round(ecart_kwh, 1),
            "ecart_pct": round(ecart_pct, 2),
            "readings_count": count_readings,
            "period_start": invoice.period_start.isoformat(),
            "period_end": invoice.period_end.isoformat(),
            "regulatory_ref": "Cross-validation MeterReading vs invoice (Bill Intelligence cardinal)",
            "montant_anomalie_eur": montant_impact_eur,
        },
    )


# ─── R26 Sanity check total_eur vs Σ lignes (Phase L2 Jean-Marc CFO) ───────


def detect_r26_total_vs_lines_inconsistency(invoice: EnergyInvoice, db: Session) -> Optional[BillAnomaly]:
    """R26 — Cohérence totale facture : `EnergyInvoice.total_eur` vs Σ amount_eur lignes.

    Persona Jean-Marc CFO : ROI 0,5-2 k€/an. Cas typique : facture papier mal
    imprimée OU saisie/import partiel — total ≠ somme des lignes détaillées.
    Sanity check cardinal qui complète les autres règles (anti-bruit aval).

    Heuristique :
    - Calculer `total_lignes = Σ amount_eur` sur toutes lignes invoice
    - Comparer avec `invoice.total_eur` (TTC)
    - Si écart > 5 % ET > 5 € absolu → R26 anomalie
    - Tolère TVA implicite : si `total_lignes ~ total_eur / 1.20`, considère OK

    Returns:
        BillAnomaly ou None
    """
    if not invoice.total_eur or invoice.total_eur <= 0:
        return None

    lines = invoice.lines or []
    if len(lines) < 2:  # Sanity check pas pertinent sur facture quasi-vide
        return None

    total_lignes_ht = sum(float(line.amount_eur or 0) for line in lines)
    if total_lignes_ht <= 0:
        return None

    # Phase L8.1 — seuils YAML SoT (no fake code) ; tva_normale_pct depuis SoT existant
    threshold_pct = float(get_term_value("BILL_ANOMALY_TOTAL_LINES_THRESHOLD_PCT"))
    threshold_min_eur = float(get_term_value("BILL_ANOMALY_TOTAL_LINES_MIN_EUR"))
    critical_eur = float(get_term_value("BILL_ANOMALY_TOTAL_LINES_CRITICAL_EUR"))
    tva_multiplier = 1 + float(get_term_value("TVA_NORMALE_PCT")) / 100  # SoT existant 20%

    total_facture = float(invoice.total_eur)
    # 2 hypothèses : lignes en TTC (=total_eur) ou en HT (×1.20 ≈ total_eur)
    ecart_ttc = total_lignes_ht - total_facture
    ecart_ht_x_tva = (total_lignes_ht * tva_multiplier) - total_facture

    # Le scénario qui colle le mieux gagne
    ecart_eur = min((ecart_ttc, ecart_ht_x_tva), key=abs)
    pct_base = total_facture
    ecart_pct = abs(ecart_eur) / pct_base * 100 if pct_base > 0 else 0

    if ecart_pct < threshold_pct or abs(ecart_eur) < threshold_min_eur:
        return None

    severity = _SEV_CRITICAL if abs(ecart_eur) > critical_eur else _SEV_WARNING
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R26",
        severity=severity,
        threshold_value=Decimal(str(threshold_pct)),
        actual_value=Decimal(str(round(ecart_pct, 2))),
        details_json={
            "total_eur_facture": round(total_facture, 2),
            "total_lignes_ht": round(total_lignes_ht, 2),
            "total_lignes_x_tva20": round(total_lignes_ht * tva_multiplier, 2),
            "ecart_eur": round(ecart_eur, 2),
            "ecart_pct": round(ecart_pct, 2),
            "lines_count": len(lines),
            "regulatory_ref": "Cohérence comptable interne (sanity check)",
            "montant_anomalie_eur": round(abs(ecart_eur), 2),
        },
    )


# ─── R25 Abonnement divergent contrat (Phase L Jean-Marc CFO ROI 1-3 k€/an) ─


def detect_r25_subscription_mismatch(
    invoice: EnergyInvoice,
    db: Session,
    *,
    contract_cache: Optional[dict[int, EnergyContract]] = None,
) -> Optional[BillAnomaly]:
    """R25 — Abonnement (fixed fee) facturé divergent vs `EnergyContract.fixed_fee_eur_per_month`.

    Persona Jean-Marc CFO : ROI 1-3 k€/an. Cas typique : le fournisseur ne met
    pas à jour la facturation après changement de contrat (renouvellement,
    avenant tarifaire) → abonnement reste à l'ancien prix pendant des mois.

    Heuristique cardinale Phase L :
    - Identifier ligne SUBSCRIPTION (line_type=ABONNEMENT) sur l'invoice
    - Comparer total mensuel facturé vs `contract.fixed_fee_eur_per_month`
    - Si écart > 5 % ET > 2 € absolu → R25 anomalie

    Ne fire que si :
    - Invoice.contract_id rattaché (sinon impossible de comparer)
    - Contrat a `fixed_fee_eur_per_month` défini
    - Invoice a au moins 1 ligne ABONNEMENT

    Returns:
        BillAnomaly ou None
    """
    from models.enums import InvoiceLineType

    contract = _resolve_contract(invoice, contract_cache=contract_cache)
    if contract is None or contract.fixed_fee_eur_per_month is None:
        return None
    fixed_fee_attendu = float(contract.fixed_fee_eur_per_month)
    if fixed_fee_attendu <= 0:
        return None

    # Phase L8.1 — seuils YAML SoT (no fake code)
    threshold_pct = float(get_term_value("BILL_ANOMALY_SUBSCRIPTION_THRESHOLD_PCT"))
    threshold_min_eur = float(get_term_value("BILL_ANOMALY_SUBSCRIPTION_MIN_EUR"))
    critical_eur = float(get_term_value("BILL_ANOMALY_SUBSCRIPTION_CRITICAL_EUR"))

    # Détection par label : InvoiceLineType n'a pas ABONNEMENT — on identifie via
    # label `abonnement|redevance.*fixe|fee.*month`. Phase M : enum dédié envisageable.
    abo_lines = [
        line
        for line in (invoice.lines or [])
        if line.amount_eur is not None
        and line.label
        and re.search(r"\b(abonnement|redevance\s+fixe)\b", line.label, re.IGNORECASE)
    ]
    if not abo_lines:
        return None

    abo_facture = sum(float(line.amount_eur or 0) for line in abo_lines)
    if invoice.period_start and invoice.period_end:
        days = (invoice.period_end - invoice.period_start).days + 1
        months_covered = max(1.0, days / 30.4375)  # Avg jours/mois Grégorien
        abo_mensuel_facture = abo_facture / months_covered
    else:
        abo_mensuel_facture = abo_facture  # Hypothèse 1 mois si période inconnue

    ecart_eur = abo_mensuel_facture - fixed_fee_attendu
    ecart_pct = abs(ecart_eur) / fixed_fee_attendu * 100

    if ecart_pct < threshold_pct or abs(ecart_eur) < threshold_min_eur:
        return None

    severity = _SEV_CRITICAL if abs(ecart_eur) > critical_eur else _SEV_WARNING
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R25",
        severity=severity,
        threshold_value=Decimal(str(threshold_pct)),
        actual_value=Decimal(str(round(ecart_pct, 2))),
        details_json={
            "abonnement_attendu_eur_par_mois": round(fixed_fee_attendu, 2),
            "abonnement_facture_eur_par_mois": round(abo_mensuel_facture, 2),
            "abonnement_total_facture_eur": round(abo_facture, 2),
            "ecart_eur": round(ecart_eur, 2),
            "ecart_pct": round(ecart_pct, 2),
            "contract_id": contract.id,
            "regulatory_ref": "EnergyContract.fixed_fee_eur_per_month (clause contractuelle)",
            "montant_anomalie_eur": round(abs(ecart_eur), 2),
        },
    )


# ─── R22 Accise erronée (Phase I Jean-Marc CFO ROI 2-4 k€/an) ──────────────


# Phase L2.1 (P1 /simplify reporté) : helper extrait vers `utils/enum_normalize.py`
# (Pilier 13 ADR-016 SoT cross-services). Alias rétro-compat conservé.
from utils.enum_normalize import normalize_enum_value as _normalize_enum_value  # noqa: E402


def _resolve_accise_rate_from_dp(
    invoice: EnergyInvoice,
    db: Session,
    *,
    cache: Optional[dict] = None,
) -> tuple[float, str, str]:
    """Phase J — Résout le taux accise applicable selon `AcciseCategorieElec` du DP.

    Pattern Pilier 13 ADR-016 (SoT cardinal) : utilise les catégories CIBS
    déclarées sur les DeliveryPoints liés à l'invoice via Site → Meter → DP.
    Fallback T1 (MENAGES_ASSIMILES) si catégorie indéterminée.

    Phase K cardinal cache : `cache` dict optionnel `{site_id: result}` pour batch
    ingestion N invoices/site (évite N queries DP redondantes). P2 audit reporté
    Phase K (perf hot-path).

    Phase K perf : query `with_entities(...).distinct()` sur colonne scalaire
    (vs charger tous DP objects).

    Returns:
        tuple (rate_eur_per_mwh, category_value, source_label)
    """
    from doctrine.constants import (
        ACCISE_ELEC_HP_EUR_PER_MWH,
        ACCISE_ELEC_T1_EUR_PER_MWH,
        ACCISE_ELEC_T2_EUR_PER_MWH,
    )
    from models import DeliveryPoint
    from models.enums import AcciseCategorieElec

    site_id = getattr(invoice, "site_id", None)

    # Cache hit batch ingestion (Phase K perf)
    if cache is not None and site_id is not None and site_id in cache:
        return cache[site_id]

    result: tuple[float, str, str] = (ACCISE_ELEC_T1_EUR_PER_MWH, "T1_FALLBACK", "FALLBACK")
    if site_id:
        # Phase K perf : DISTINCT scalaire (vs charger objets DP complets)
        categories = {
            _normalize_enum_value(row[0])
            for row in db.query(DeliveryPoint.accise_categorie_elec)
            .filter(DeliveryPoint.site_id == site_id)
            .distinct()
            .all()
        }
        categories.discard(None)
        if len(categories) == 1:
            cat_value = categories.pop()
            if cat_value == AcciseCategorieElec.HAUTE_PUISSANCE.value:
                result = (ACCISE_ELEC_HP_EUR_PER_MWH, cat_value, "DP_CATEGORY")
            elif cat_value == AcciseCategorieElec.PME.value:
                result = (ACCISE_ELEC_T2_EUR_PER_MWH, cat_value, "DP_CATEGORY")
            else:
                result = (ACCISE_ELEC_T1_EUR_PER_MWH, cat_value, "DP_CATEGORY")

    if cache is not None and site_id is not None:
        cache[site_id] = result
    return result


def detect_r22_accise_mismatch(
    invoice: EnergyInvoice,
    db: Session,
    *,
    dp_category_cache: Optional[dict] = None,
    lines_by_type: Optional[LinesByType] = None,
) -> Optional[BillAnomaly]:
    """R22 — Accise élec (TICFE/CSPE) divergence taux réglementaire.

    Persona Jean-Marc CFO : ROI 2-4 k€/an, transitions tarifaires accise 2024→2025
    et 2025→2026 régulièrement ratées par fournisseurs.

    Phase J raffinement : route via `AcciseCategorieElec` depuis DP du site
    (T1 MENAGES_ASSIMILES / T2 PME / HP HAUTE_PUISSANCE) au lieu de T1 fixe.
    Réduit faux positifs pour PME et industriels haute puissance.

    Heuristique cardinale :
    - Trouver ligne TAX `accise|ticfe|cspe|contrib.*service.*public`
    - Résoudre catégorie via DP.accise_categorie_elec → taux réglementaire
    - Calculer accise attendue = energy_mwh × tarif_categorie
    - Si écart > 10 % ET > 5 € → R22 anomalie (seuil resserré vs T1 fallback 35 %)

    Returns:
        BillAnomaly ou None
    """
    if not invoice.energy_kwh or invoice.energy_kwh <= 0:
        return None

    # Phase L11.2 — pré-partition `lines_by_type` (fallback si mode unitaire)
    parts = _resolve_lines(invoice, lines_by_type)
    accise_lines = [line for line in parts[InvoiceLineType.TAX] if line.label and _ACCISE_PATTERN.search(line.label)]
    if not accise_lines:
        return None

    accise_facturee = sum(float(line.amount_eur or 0) for line in accise_lines)
    energy_mwh = float(invoice.energy_kwh) / 1000

    # Phase J : résoudre catégorie depuis DP (T1/T2/HP) au lieu de T1 fixe
    rate_eur_per_mwh, category_value, category_source = _resolve_accise_rate_from_dp(
        invoice, db, cache=dp_category_cache
    )
    accise_attendue = energy_mwh * rate_eur_per_mwh

    if accise_attendue <= 0:
        return None

    ecart_eur = accise_facturee - accise_attendue
    ecart_pct = abs(ecart_eur) / accise_attendue * 100

    # Phase L8.1 — seuils YAML SoT (no fake code)
    threshold_dp = float(get_term_value("BILL_ANOMALY_ACCISE_THRESHOLD_DP_PCT"))
    threshold_fallback = float(get_term_value("BILL_ANOMALY_ACCISE_THRESHOLD_FALLBACK_PCT"))
    threshold_min_eur = float(get_term_value("BILL_ANOMALY_ACCISE_MIN_EUR"))
    # Critical seuil R22 partagé avec R26 (cohérence audit CFO > 50 €)
    critical_eur = float(get_term_value("BILL_ANOMALY_TOTAL_LINES_CRITICAL_EUR"))

    # Seuils selon source catégorie :
    # - DP_CATEGORY (catégorie connue) : haute confiance → seuil strict
    # - FALLBACK T1 : couvre marge T2/HP légitime → seuil lâche
    threshold_pct = threshold_dp if category_source == "DP_CATEGORY" else threshold_fallback
    if ecart_pct < threshold_pct or abs(ecart_eur) < threshold_min_eur:
        return None

    severity = _SEV_CRITICAL if abs(ecart_eur) > critical_eur else _SEV_WARNING
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R22",
        severity=severity,
        threshold_value=Decimal(str(threshold_pct)),
        actual_value=Decimal(str(round(ecart_pct, 2))),
        details_json={
            "energy_kwh": float(invoice.energy_kwh),
            "energy_mwh": round(energy_mwh, 3),
            "accise_facturee_eur": round(accise_facturee, 2),
            "accise_attendue_eur": round(accise_attendue, 2),
            "tarif_eur_per_mwh": rate_eur_per_mwh,
            "category_value": category_value,
            "category_source": category_source,  # DP_CATEGORY ou FALLBACK
            "ecart_eur": round(ecart_eur, 2),
            "ecart_pct": round(ecart_pct, 2),
            "regulatory_ref": "JORFTEXT000053407616 — Accise élec fév 2026+ (T1=30,85 / T2=26,58 / HP=5,71 €/MWh)",
            "montant_anomalie_eur": round(abs(ecart_eur), 2),
        },
    )


# ─── R24 TVA mauvais taux (Phase I Jean-Marc CFO ROI 1-2 k€/an) ────────────


def detect_r24_tva_rate_mismatch(
    invoice: EnergyInvoice,
    db: Session,
    *,
    lines_by_type: Optional[LinesByType] = None,
) -> Optional[BillAnomaly]:
    """R24 — TVA appliquée à mauvais taux vs total HT.

    Persona Jean-Marc CFO : ROI 1-2 k€/an, erreurs CTA (5,5% vs 20%) et
    accise (5,5% vs 20%) sur transitions TVA 2024-2025.

    Heuristique cardinale :
    - Calculer total HT = Σ(amount_eur sur lignes non-TVA)
    - Détecter ligne TVA (label LIKE %TVA% ou %VAT%)
    - Calculer taux effectif = TVA / HT
    - Comparer avec taux attendu (20 % par défaut tertiaire B2B)
    - Si écart > 0,5 pt absolu (ex: 19,3 % vs 20 %) ET montant > 10 € → R24

    Returns:
        BillAnomaly ou None
    """
    # Phase L11.2 — pré-partition `lines_by_type` (fallback si mode unitaire)
    parts = _resolve_lines(invoice, lines_by_type)

    # Phase L11.6 audit fix F1 — _TVA_PATTERN module-level (avant : compilée par appel)
    tax_lines = parts[InvoiceLineType.TAX]
    tva_lines = [line for line in tax_lines if line.label and _TVA_PATTERN.search(line.label)]
    if not tva_lines:
        return None

    # Phase L11.6 audit fix F3 — total HT = Σ amount_eur sur lignes non-TVA via
    # `id()` Python builtin (object identity), pas line.id DB.
    # Avant L11.6 : `{line.id for ...}` collisionnait en session non-flushée
    # (line.id=None × N → set {None} → exclusion silencieusement incorrecte).
    # Après : `id(line)` toujours unique par instance Python (immune au DB state).
    tva_obj_ids = {id(line) for line in tva_lines}
    ht_total = sum(
        float(line.amount_eur or 0)
        for ltype in (
            InvoiceLineType.ENERGY,
            InvoiceLineType.NETWORK,
            InvoiceLineType.TAX,
            InvoiceLineType.OTHER,
        )
        for line in parts[ltype]
        if id(line) not in tva_obj_ids
    )
    tva_facturee = sum(float(line.amount_eur or 0) for line in tva_lines)
    if ht_total <= 0:
        return None

    taux_effectif_pct = (tva_facturee / ht_total) * 100
    # Phase L8.1 — seuils YAML SoT (no fake code) ; taux_attendu = TVA_NORMALE_PCT SoT existant
    taux_attendu_pct = float(get_term_value("TVA_NORMALE_PCT"))
    tolerance_pt = float(get_term_value("BILL_ANOMALY_TVA_TOLERANCE_PT"))
    min_eur = float(get_term_value("BILL_ANOMALY_TVA_MIN_EUR"))
    critical_pt = float(get_term_value("BILL_ANOMALY_TVA_CRITICAL_PT"))

    ecart_pct_abs = abs(taux_effectif_pct - taux_attendu_pct)

    if ecart_pct_abs < tolerance_pt or tva_facturee < min_eur:
        return None

    severity = _SEV_CRITICAL if ecart_pct_abs > critical_pt else _SEV_WARNING
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R24",
        severity=severity,
        threshold_value=Decimal(str(tolerance_pt)),
        actual_value=Decimal(str(round(ecart_pct_abs, 2))),
        details_json={
            "ht_total_eur": round(ht_total, 2),
            "tva_facturee_eur": round(tva_facturee, 2),
            "taux_effectif_pct": round(taux_effectif_pct, 2),
            "taux_attendu_pct": taux_attendu_pct,
            "ecart_pct": round(ecart_pct_abs, 2),
            "regulatory_ref": "CGI art. 278 — TVA 20 % énergie B2B tertiaire",
            "montant_anomalie_eur": round(abs(tva_facturee - (ht_total * taux_attendu_pct / 100)), 2),
        },
    )


# ─── R23 TURPE doublé (Phase H Jean-Marc CFO cardinal) ─────────────────────


def detect_r23_turpe_double(
    invoice: EnergyInvoice,
    db: Session,
    *,
    lines_by_type: Optional[LinesByType] = None,
) -> list[BillAnomaly]:
    """R23 — TURPE doublé : 2+ lignes TURPE pour même période sur invoice unique.

    Persona Jean-Marc CFO cardinal Phase H : impact ROI 6-15 k€/an récupérables
    sur portefeuille tertiaire IDF (5 % des factures observées en doublon
    bascule HTA/BT ou changement fournisseur).

    Heuristique :
    - Regrouper EnergyInvoiceLine `line_type=NETWORK` par période détectée
      (HPH / HCH / HPB / HCB / P / HP / HC / BASE)
    - Si ≥ 2 lignes pour même période sur même invoice → R23 anomalie
    - Sévérité `critical` si total doublé > seuil YAML SoT ; `warning` sinon

    Implémentation : délègue à `_build_doublon_anomaly()` (Phase L10.1) qui
    consolide le pattern doublon avec R31 (sum-max robustness + PII sanitize +
    cap module-level).

    Returns:
        list[BillAnomaly] : 0..N anomalies (1 par groupe période doublé)
    """
    from collections import defaultdict

    # Phase L11.2 — pré-partition `lines_by_type` (fallback si mode unitaire)
    parts = _resolve_lines(invoice, lines_by_type)
    network_lines = [line for line in parts[InvoiceLineType.NETWORK] if line.amount_eur is not None]
    if len(network_lines) < 2:
        return []

    # Regroupement par période détectée dans label
    by_period: dict[str, list] = defaultdict(list)
    for line in network_lines:
        label = (line.label or "").upper()
        period = None
        for code in _PERIOD_CODES_KNOWN:
            if re.search(rf"\b{code}\b", label):
                period = code
                break
        if period:
            by_period[period].append(line)

    # Phase L8.1 — seuil YAML SoT (no fake code)
    critical_eur = float(get_term_value("BILL_ANOMALY_TURPE_DOUBLE_CRITICAL_EUR"))

    # Phase L10.1 — _build_doublon_anomaly() helper (audit P1 reuse #4 + hérite
    # automatiquement du fix L9.5 sum-max + PII sanitize sur duplicate_labels).
    anomalies: list[BillAnomaly] = []
    for period, lines in by_period.items():
        anomaly = _build_doublon_anomaly(
            invoice=invoice,
            code="R23",
            candidate_lines=lines,
            critical_eur=critical_eur,
            regulatory_ref="CRE Délib. 2025-78 art. 8 — TURPE 7 facturation unique période",
            extra_details={"period_code": period},
        )
        if anomaly is not None:
            anomalies.append(anomaly)
    return anomalies


# ─── R31 Doublons accise/CSPE/TICFE (Phase L9 CFO post-renommage 2022) ────


def detect_r31_accise_double(
    invoice: EnergyInvoice,
    db: Session,
    *,
    lines_by_type: Optional[LinesByType] = None,
) -> Optional[BillAnomaly]:
    """R31 — Multi-lignes accise sur même facture (doublons post-renommage CSPE→TICFE→Accise).

    Persona Jean-Marc CFO : ROI 0,5-3 k€/an. Cas typique post-décret 2022-130
    (renommage CSPE→TICFE→Accise) : certains fournisseurs persistent à facturer
    simultanément sous 2 ou 3 noms (ex: ligne "CSPE" + ligne "Accise sur
    l'électricité" sur la même facture). C'est un doublon historique systémique
    sur ~5-10 % du parc fournisseur historique.

    Différencié de R22 (mauvais taux accise) : R22 vérifie le tarif appliqué,
    R31 vérifie la duplication de lignes (multi-comptage). Détecté indépendamment
    de la catégorie DP (T1/T2/HP).

    Implémentation : délègue à `_build_doublon_anomaly()` (Phase L10.1) qui
    consolide le pattern doublon avec R23 (sum-max robustness + PII sanitize +
    cap module-level + extra_details merge ordre prudent).

    Returns:
        BillAnomaly ou None
    """
    # Phase L11.2 — pré-partition `lines_by_type` (fallback si mode unitaire)
    parts = _resolve_lines(invoice, lines_by_type)
    # Phase L9.5 — filtre amount_eur > 0 (exclut avoirs/régularisations négatives)
    accise_lines = [
        line
        for line in parts[InvoiceLineType.TAX]
        if line.amount_eur is not None and line.amount_eur > 0 and line.label and _ACCISE_PATTERN.search(line.label)
    ]
    critical_eur = float(get_term_value("BILL_ANOMALY_ACCISE_DOUBLE_CRITICAL_EUR"))

    # Phase L10.1 — _build_doublon_anomaly() helper (audit P1 reuse #4) consolide
    # le pattern doublon avec R23. Hérite : sum-max robustness + PII sanitize + cap[:5].
    return _build_doublon_anomaly(
        invoice=invoice,
        code="R31",
        candidate_lines=accise_lines,
        critical_eur=critical_eur,
        # CIBS art. L.312-1 (taxe élec post-2022) + LFR 2021 art. 54
        # (renommage CSPE/TICFE→Accise effective 01/01/2022).
        regulatory_ref="CIBS art. L.312-1 + LFR 2021 art. 54 — renommage CSPE/TICFE→Accise élec (01/01/2022, anti-doublon historique)",
    )


# ─── R29 Période chevauchement / trou facturation (Phase L5 CFO anti-double-billing) ──


def detect_r29_period_overlap_or_gap(
    invoice: EnergyInvoice,
    db: Session,
    *,
    prev_invoice_cache: Optional[dict[int, list[EnergyInvoice]]] = None,
) -> Optional[BillAnomaly]:
    """R29 — Période facturée chevauche ou crée un trou avec facture précédente même site.

    Persona Jean-Marc CFO : ROI 2-5 k€/an. Anti-fraude double-billing (chevauchement)
    + détection rupture suivi conso (trou).

    Phase L7.3 P0 efficiency : `prev_invoice_cache` optionnel pour mode batch.
    Pré-rempli par caller avec `build_prev_invoice_cache(db, site_ids)` qui charge
    en 1 SELECT toutes les factures triées par period_end DESC pour les sites cibles.
    Fallback DB query si cache None (mode unitaire).

    Args:
        invoice: facture à analyser
        db: session SQLAlchemy
        prev_invoice_cache: dict {site_id: [EnergyInvoice ordonnées period_end DESC]}
                           si fourni, lookup O(n) sur liste triée (vs SELECT par invoice)

    Returns:
        BillAnomaly ou None
    """
    if invoice.site_id is None or invoice.period_start is None or invoice.period_end is None:
        return None

    # Phase L7.3 P0 — cache lookup O(n) sur liste pré-triée période_end DESC
    if prev_invoice_cache is not None:
        candidates = prev_invoice_cache.get(invoice.site_id, [])
        prev = next(
            (
                inv
                for inv in candidates
                if inv.id != invoice.id
                and inv.period_start is not None
                and inv.period_end is not None
                and inv.period_start < invoice.period_start
            ),
            None,
        )
    else:
        # Mode unitaire : fallback SELECT (ex: pipeline ad-hoc 1 facture)
        prev = (
            db.query(EnergyInvoice)
            .filter(
                EnergyInvoice.site_id == invoice.site_id,
                EnergyInvoice.id != invoice.id,
                EnergyInvoice.period_end.isnot(None),
                EnergyInvoice.period_start.isnot(None),
                EnergyInvoice.period_start < invoice.period_start,
            )
            .order_by(EnergyInvoice.period_end.desc())
            .first()
        )
    if prev is None:
        return None  # 1ʳᵉ facture du site, pas de référence

    # Phase L7.2 — seuils YAML SoT (no fake code)
    gap_tolerance = int(get_term_value("BILL_ANOMALY_PERIOD_GAP_TOLERANCE_DAYS"))
    gap_critical = int(get_term_value("BILL_ANOMALY_PERIOD_GAP_CRITICAL_DAYS"))
    overlap_critical = int(get_term_value("BILL_ANOMALY_PERIOD_OVERLAP_CRITICAL_DAYS"))

    # gap_days : jours pleins entre prev.period_end et invoice.period_start
    # Convention : si prev.period_end=30/04 et invoice.period_start=01/05 → gap=0 (continu)
    gap_days = (invoice.period_start - prev.period_end).days - 1

    if 0 <= gap_days <= gap_tolerance:
        return None  # Continuité acceptable

    if gap_days < 0:
        # Chevauchement
        overlap_days = -gap_days
        severity = _SEV_CRITICAL if overlap_days > overlap_critical else _SEV_WARNING
        details = {
            "kind": "chevauchement",
            "overlap_days": overlap_days,
            "gap_days": gap_days,
            "prev_invoice_id": prev.id,
            "prev_invoice_number": prev.invoice_number,
            "prev_period_end": prev.period_end.isoformat(),
            "invoice_period_start": invoice.period_start.isoformat(),
            "regulatory_ref": "CRE TURPE 7 art. 8 — facturation unique par période",
            "montant_anomalie_eur": round(
                float(invoice.total_eur or 0)
                * overlap_days
                / max((invoice.period_end - invoice.period_start).days + 1, 1),
                2,
            ),
        }
    else:
        # Trou (gap_days > gap_tolerance)
        severity = _SEV_CRITICAL if gap_days > gap_critical else _SEV_WARNING
        details = {
            "kind": "trou",
            "gap_days": gap_days,
            "prev_invoice_id": prev.id,
            "prev_invoice_number": prev.invoice_number,
            "prev_period_end": prev.period_end.isoformat(),
            "invoice_period_start": invoice.period_start.isoformat(),
            "regulatory_ref": "Suivi conso continu — gap suspect ingestion",
            "montant_anomalie_eur": 0.0,
        }

    return BillAnomaly(
        invoice_id=invoice.id,
        code="R29",
        severity=severity,
        threshold_value=Decimal(str(gap_tolerance)),
        actual_value=Decimal(str(gap_days)),
        details_json=details,
    )


# ─── R30 Période facturée hors fenêtre contractuelle (Phase L6 CFO date prise d'effet) ──


def detect_r30_invoice_period_outside_contract_window(
    invoice: EnergyInvoice,
    db: Session,
    *,
    contract_cache: Optional[dict[int, EnergyContract]] = None,
) -> Optional[BillAnomaly]:
    """R30 — Période facture hors fenêtre [`contract.start_date`, `contract.end_date`].

    Persona Jean-Marc CFO : ROI 1-4 k€/an. Détecte mauvais binding facture↔contrat
    OU tarif appliqué hors période contractuelle (anti-fraude prise d'effet).

    Cas typiques :
    - Fournisseur applique tarif négocié AVANT prise d'effet contractuelle
      (ex: contract.start_date=01/05 mais facture Mars-Avril utilise déjà le tarif)
    - Fournisseur prolonge tarif APRÈS fin contractuelle alors qu'un nouveau contrat
      ou tarif "ouvert" devrait s'appliquer (ex: contract.end_date=30/09 mais facture
      Octobre-Novembre encore liée au contrat expiré)
    - Erreur de mapping invoice.contract_id (lien vers mauvais contrat)

    Heuristique cardinale :
    - invoice.period_end < contract.start_date → période entièrement avant début contrat
    - invoice.period_start > contract.end_date → période entièrement après fin contrat
    - Chevauchement partiel (period_start < contract.start_date <= period_end OU
      period_start <= contract.end_date < period_end) → flag warning si ≥ 7j hors fenêtre

    Sévérité :
    - critical : période entièrement hors fenêtre (0 % couverture contractuelle)
    - warning : chevauchement partiel ≥ 7 jours hors fenêtre

    Garde-fous (anti-faux-positifs) :
    - Skip si invoice.contract_id manquant (pas de référence)
    - Skip si invoice.period_start / period_end manquants
    - Skip si contract.start_date ET contract.end_date tous deux NULL
    - Tolère start_date OR end_date NULL (contrat ouvert d'un côté)

    Returns:
        BillAnomaly ou None
    """
    if invoice.period_start is None or invoice.period_end is None:
        return None
    contract = _resolve_contract(invoice, contract_cache=contract_cache)
    if contract is None:
        return None
    if contract.start_date is None and contract.end_date is None:
        return None  # Contrat ouvert sans fenêtre — pas de référence

    # Phase L7.2 — seuil YAML SoT (no fake code)
    partial_warn_days = int(get_term_value("BILL_ANOMALY_PERIOD_OUTSIDE_CONTRACT_WARN_DAYS"))

    period_start = invoice.period_start
    period_end = invoice.period_end
    cs = contract.start_date  # peut être None
    ce = contract.end_date  # peut être None

    # Cas 1 : période entièrement avant start_date
    if cs is not None and period_end < cs:
        days_before = (cs - period_end).days
        return BillAnomaly(
            invoice_id=invoice.id,
            code="R30",
            severity=_SEV_CRITICAL,
            threshold_value=Decimal("0"),  # 0 j tolérance entièrement hors fenêtre
            actual_value=Decimal(str(days_before)),
            details_json={
                "kind": "avant_debut_contrat",
                "days_outside": days_before,
                "contract_id": contract.id,
                "contract_start_date": cs.isoformat(),
                "contract_end_date": ce.isoformat() if ce else None,
                "invoice_period_start": period_start.isoformat(),
                "invoice_period_end": period_end.isoformat(),
                "regulatory_ref": "Code civil art. 1103 — effet contractuel à compter date prise d'effet",
                "montant_anomalie_eur": float(invoice.total_eur or 0),
            },
        )

    # Cas 2 : période entièrement après end_date
    if ce is not None and period_start > ce:
        days_after = (period_start - ce).days
        return BillAnomaly(
            invoice_id=invoice.id,
            code="R30",
            severity=_SEV_CRITICAL,
            threshold_value=Decimal("0"),
            actual_value=Decimal(str(days_after)),
            details_json={
                "kind": "apres_fin_contrat",
                "days_outside": days_after,
                "contract_id": contract.id,
                "contract_start_date": cs.isoformat() if cs else None,
                "contract_end_date": ce.isoformat(),
                "invoice_period_start": period_start.isoformat(),
                "invoice_period_end": period_end.isoformat(),
                "regulatory_ref": "Code civil art. 1103 — fin contractuelle = fin effet tarif",
                "montant_anomalie_eur": float(invoice.total_eur or 0),
            },
        )

    # Cas 3 : chevauchement partiel — calcule jours hors fenêtre
    days_outside = 0
    overlap_kind = None
    if cs is not None and period_start < cs:
        days_outside += (cs - period_start).days
        overlap_kind = "partiel_avant_debut"
    if ce is not None and period_end > ce:
        days_outside += (period_end - ce).days
        overlap_kind = "partiel_apres_fin" if overlap_kind is None else "partiel_double"

    if days_outside >= partial_warn_days:
        period_days = max((period_end - period_start).days + 1, 1)
        return BillAnomaly(
            invoice_id=invoice.id,
            code="R30",
            severity=_SEV_WARNING,
            threshold_value=Decimal(str(partial_warn_days)),
            actual_value=Decimal(str(days_outside)),
            details_json={
                "kind": overlap_kind,
                "days_outside": days_outside,
                "period_days": period_days,
                "contract_id": contract.id,
                "contract_start_date": cs.isoformat() if cs else None,
                "contract_end_date": ce.isoformat() if ce else None,
                "invoice_period_start": period_start.isoformat(),
                "invoice_period_end": period_end.isoformat(),
                "regulatory_ref": "Code civil art. 1103 — fenêtre contractuelle stricte",
                "montant_anomalie_eur": round(float(invoice.total_eur or 0) * days_outside / period_days, 2),
            },
        )

    return None


# ─── Pipeline ───────────────────────────────────────────────────────────────


def build_prev_invoice_cache(db: Session, site_ids: list[int]) -> dict[int, list[EnergyInvoice]]:
    """Phase L7.3 P0 — Préchargement batch des EnergyInvoice par site, triés period_end DESC.

    Permet au pipeline R29 batch (1000 invoices) de remplacer 1000 SELECT
    individuels par 1 unique SELECT WHERE site_id IN (...). Caller responsable
    de fournir la liste de site_ids pertinents (typiquement les sites des
    invoices à analyser dans le batch).

    Args:
        db: session SQLAlchemy
        site_ids: liste IDs sites à pré-charger (cardinal du batch)

    Returns:
        dict {site_id: [EnergyInvoice triées period_end DESC]}
    """
    if not site_ids:
        return {}
    rows = (
        db.query(EnergyInvoice)
        .filter(
            EnergyInvoice.site_id.in_(site_ids),
            EnergyInvoice.period_end.isnot(None),
            EnergyInvoice.period_start.isnot(None),
        )
        .order_by(EnergyInvoice.site_id, EnergyInvoice.period_end.desc())
        .all()
    )
    cache: dict[int, list[EnergyInvoice]] = {}
    for inv in rows:
        cache.setdefault(inv.site_id, []).append(inv)
    return cache


def build_contract_cache(db: Session, contract_ids: list[int]) -> dict[int, EnergyContract]:
    """Phase L12.1 P1 — Préchargement batch EnergyContract pour R25/R28/R30.

    Pattern aligné `build_prev_invoice_cache` (Phase L7.3) + `dp_category_cache`
    (Phase K2). Audit P1 efficiency cumul L8+L9+L10+L11 : avant L12, R25/R28/R30
    accédaient `invoice.contract` (lazy-load) → 3 SQL/invoice × 1000 invoices
    batch = 3000 SELECT séparés.

    Après L12 : 1 SELECT IN sur tous les contract_ids distincts du batch =
    3 SQL × 1000 → 1 SQL total (gain × 3000).

    Args:
        db: session SQLAlchemy
        contract_ids: liste contract_id distincts à pré-charger

    Returns:
        dict {contract_id: EnergyContract}. Contracts inactifs/inexistants
        absents du dict (R25/R28/R30 traitent comme None via .get()).
    """
    if not contract_ids:
        return {}
    # Phase L12.5 audit fix F2 — filter None (cas caller buggy avec contract_id NULL
    # dans la liste) ; sans guard, IN(NULL) silencieusement ignoré par SQL → résultat
    # cohérent mais bug upstream non détecté.
    contract_ids = [cid for cid in contract_ids if cid is not None]
    if not contract_ids:
        return {}
    rows = db.query(EnergyContract).filter(EnergyContract.id.in_(contract_ids)).all()
    return {c.id: c for c in rows}


def detect_anomalies_for_invoice(
    invoice: EnergyInvoice,
    db: Session,
    *,
    dp_category_cache: Optional[dict] = None,
    prev_invoice_cache: Optional[dict[int, list[EnergyInvoice]]] = None,
    contract_cache: Optional[dict[int, EnergyContract]] = None,
) -> list[BillAnomaly]:
    """Pipeline détection complète sur 1 invoice.

    Trigger : cascade ingestion facture (Sprint C-5 Phase 5.1) ou batch nightly fallback.
    Résilience par-action : try/except chaque détecteur — un échec n'interrompt pas les autres.

    Sprint C-7 Phase 7.7 Lot A — D-Sprint-C7-BillAnomaly-Decoupling-Commit-001 :
    db.commit() retiré (couplage caller). Pattern aligné `log_consent_change` Phase 7.4 :
    le caller décide quand commit (transactional batch / unit-of-work). Anomalies sont
    flushées via `db.add()` mais persistées par caller.

    Phase K audit P1 fix : `dp_category_cache` propagé à R22 — caller peut
    instancier dict {} pour batch ingestion (évite N queries DP redondantes).

    Phase L11 — `_partition_invoice_lines()` exécuté UNE seule fois en tête
    de pipeline ; le dict `lines_by_type` est propagé en kwarg aux 6 détecteurs
    qui filtrent par `line_type` (R21+R22+R23+R24+R28+R31). Réduit 6 traversals
    Python-side O(N) à 1 traversal + 6 dict lookups O(1).

    Retour : liste anomalies ajoutées à la session (caller responsable du commit).
    """
    anomalies: list[BillAnomaly] = []

    # Phase L11.3 — pré-partition unique propagée à 6 détecteurs (audit P1
    # cumul L8/L9/L10 finding 8 efficiency).
    lines_by_type = _partition_invoice_lines(invoice)

    # R19 : 0 ou 1 anomaly
    try:
        r19 = detect_r19_vnu_dormant(invoice, db)
        if r19:
            db.add(r19)
            anomalies.append(r19)
    except Exception as e:
        _logger.error(f"R19 detector failed for invoice {invoice.id}: {e}")

    # R20 : 0..N anomalies (1 par poste tarifaire)
    try:
        r20_list = detect_r20_capacity_variance(invoice, db)
        for r20 in r20_list:
            db.add(r20)
            anomalies.append(r20)
    except Exception as e:
        _logger.error(f"R20 detector failed for invoice {invoice.id}: {e}")

    # R23 : 0..N anomalies (1 par période doublée) — Phase H cardinal CFO
    try:
        r23_list = detect_r23_turpe_double(invoice, db, lines_by_type=lines_by_type)
        for r23 in r23_list:
            db.add(r23)
            anomalies.append(r23)
    except Exception as e:
        _logger.error(f"R23 detector failed for invoice {invoice.id}: {e}")

    # R21 : 0 ou 1 — Phase H CFO CTA mauvais calcul
    try:
        r21 = detect_r21_cta_mismatch(invoice, db, lines_by_type=lines_by_type)
        if r21:
            db.add(r21)
            anomalies.append(r21)
    except Exception as e:
        _logger.error(f"R21 detector failed for invoice {invoice.id}: {e}")

    # R22 : 0 ou 1 — Phase I CFO accise erronée (cache K2 propagé Phase K audit fix)
    try:
        r22 = detect_r22_accise_mismatch(invoice, db, dp_category_cache=dp_category_cache, lines_by_type=lines_by_type)
        if r22:
            db.add(r22)
            anomalies.append(r22)
    except Exception as e:
        _logger.error(f"R22 detector failed for invoice {invoice.id}: {e}")

    # R24 : 0 ou 1 — Phase I CFO TVA mauvais taux
    try:
        r24 = detect_r24_tva_rate_mismatch(invoice, db, lines_by_type=lines_by_type)
        if r24:
            db.add(r24)
            anomalies.append(r24)
    except Exception as e:
        _logger.error(f"R24 detector failed for invoice {invoice.id}: {e}")

    # R25 : 0 ou 1 — Phase L CFO abonnement divergent contrat
    try:
        r25 = detect_r25_subscription_mismatch(invoice, db, contract_cache=contract_cache)
        if r25:
            db.add(r25)
            anomalies.append(r25)
    except Exception as e:
        _logger.error(f"R25 detector failed for invoice {invoice.id}: {e}")

    # R26 : 0 ou 1 — Phase L2 CFO sanity check total vs lignes
    try:
        r26 = detect_r26_total_vs_lines_inconsistency(invoice, db)
        if r26:
            db.add(r26)
            anomalies.append(r26)
    except Exception as e:
        _logger.error(f"R26 detector failed for invoice {invoice.id}: {e}")

    # R27 : 0 ou 1 — Phase L3 CFO cross-validation conso facturée vs compteur (anti-fraude)
    try:
        r27 = detect_r27_consumption_meter_drift(invoice, db)
        if r27:
            db.add(r27)
            anomalies.append(r27)
    except Exception as e:
        _logger.error(f"R27 detector failed for invoice {invoice.id}: {e}")

    # R28 : 0 ou 1 — Phase L4 CFO prix unitaire énergie facturé divergent contrat
    try:
        r28 = detect_r28_energy_unit_price_drift(
            invoice, db, lines_by_type=lines_by_type, contract_cache=contract_cache
        )
        if r28:
            db.add(r28)
            anomalies.append(r28)
    except Exception as e:
        _logger.error(f"R28 detector failed for invoice {invoice.id}: {e}")

    # R29 : 0 ou 1 — Phase L5 CFO chevauchement/trou période facturation (anti-double-billing)
    # Phase L7.3 P0 — propage prev_invoice_cache pour éviter SELECT par-invoice en mode batch
    try:
        r29 = detect_r29_period_overlap_or_gap(invoice, db, prev_invoice_cache=prev_invoice_cache)
        if r29:
            db.add(r29)
            anomalies.append(r29)
    except Exception as e:
        _logger.error(f"R29 detector failed for invoice {invoice.id}: {e}")

    # R30 : 0 ou 1 — Phase L6 CFO période facturée hors fenêtre contractuelle
    try:
        r30 = detect_r30_invoice_period_outside_contract_window(invoice, db, contract_cache=contract_cache)
        if r30:
            db.add(r30)
            anomalies.append(r30)
    except Exception as e:
        _logger.error(f"R30 detector failed for invoice {invoice.id}: {e}")

    # R31 : 0 ou 1 — Phase L9 CFO doublons accise/CSPE/TICFE post-renommage 2022
    try:
        r31 = detect_r31_accise_double(invoice, db, lines_by_type=lines_by_type)
        if r31:
            db.add(r31)
            anomalies.append(r31)
    except Exception as e:
        _logger.error(f"R31 detector failed for invoice {invoice.id}: {e}")

    return anomalies
