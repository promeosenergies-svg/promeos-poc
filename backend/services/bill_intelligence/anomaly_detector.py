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
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from config.regulatory_sources_loader import get_term_value
from models import (
    BillAnomaly,
    EnergyInvoice,
    EnergyInvoiceLine,
    Meter,
    PowerContract,
)

_logger = logging.getLogger(__name__)


# ─── Helpers ────────────────────────────────────────────────────────────────

# Sprint C-7 Phase 7.7 Lot A — D-Sprint-C7-BillAnomaly-Multi-Postes-HTA-001 :
# HPE/HCE/PM ajoutés pour TURPE 7 HTA (Heures de Pointe d'Eté/Hiver, Heures Creuses d'Eté,
# Pointe Mobile). Ordre cardinal : codes longs d'abord (anti-overlap label parsing).
_PERIOD_CODES_KNOWN = [
    "HPH",
    "HCH",
    "HPB",
    "HCB",
    "HPE",
    "HCE",
    "POINTE",
    "BASE",
    "PM",
    "HP",
    "HC",
]

# Sprint C-7 Phase 7.7 Lot A — D-Sprint-C7-BillAnomaly-PII-Vnu-Labels-Sanitization-001 :
# regex sanitization SIREN (9 chiffres) / SIRET (14 chiffres) / PRM/PCE (14 chiffres) /
# PDL (14 chiffres). Évite leak PII dans details_json.vnu_labels (security-auditor SEC-002).
_PII_PATTERNS = (
    re.compile(r"\b\d{14}\b"),  # SIRET / PRM / PCE / PDL
    re.compile(r"\b\d{9}\b"),  # SIREN
)


def _sanitize_pii_label(label: str) -> str:
    """Masque les identifiants PII (SIREN/SIRET/PRM/PCE) dans un label.

    Retourne label avec chaque match remplacé par `<PII_REDACTED>`.
    """
    if not label:
        return label
    sanitized = label
    for pattern in _PII_PATTERNS:
        sanitized = pattern.sub("<PII_REDACTED>", sanitized)
    return sanitized


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
    threshold = Decimal(str(get_term_value("BILL_ANOMALY_VNU_DORMANT_THRESHOLD_EUR")))

    vnu_lines = (
        db.query(EnergyInvoiceLine)
        .filter(
            EnergyInvoiceLine.invoice_id == invoice.id,
            EnergyInvoiceLine.line_type == "tax",
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

    # Heuristique MVP : usage attendu si conso > 100 kWh — pas d'anomalie si conso normale
    consumption = float(invoice.energy_kwh)
    if consumption > 100:
        return None

    return BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
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
            EnergyInvoiceLine.line_type == "network",
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

        severity = "critical" if variance_pct > threshold_pct * 2 else "warning"

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


# ─── Pipeline ───────────────────────────────────────────────────────────────


def detect_anomalies_for_invoice(invoice: EnergyInvoice, db: Session) -> list[BillAnomaly]:
    """Pipeline détection complète sur 1 invoice.

    Trigger : cascade ingestion facture (Sprint C-5 Phase 5.1) ou batch nightly fallback.
    Résilience par-action : try/except chaque détecteur — un échec n'interrompt pas les autres.

    Sprint C-7 Phase 7.7 Lot A — D-Sprint-C7-BillAnomaly-Decoupling-Commit-001 :
    db.commit() retiré (couplage caller). Pattern aligné `log_consent_change` Phase 7.4 :
    le caller décide quand commit (transactional batch / unit-of-work). Anomalies sont
    flushées via `db.add()` mais persistées par caller.

    Retour : liste anomalies ajoutées à la session (caller responsable du commit).
    """
    anomalies: list[BillAnomaly] = []

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

    return anomalies
