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


# ─── R21 CTA mauvais calcul (Phase H Jean-Marc CFO) ────────────────────────


def detect_r21_cta_mismatch(invoice: EnergyInvoice, db: Session) -> Optional[BillAnomaly]:
    """R21 — CTA calculée incorrectement vs taux réglementaire (CRE 2026-14).

    Persona Jean-Marc CFO : ROI 3-5 k€/an, formule complexe (15 % distribution
    élec depuis 02/2026 + 5 % transport ≥50 kV) avec ~30 % d'erreurs constatées.

    Heuristique :
    - Identifier les lignes TURPE NETWORK (assiette CTA distribution) → Σ TURPE
    - Identifier la ligne CTA TAX (label LIKE %CTA%) → CTA facturée
    - CTA attendue = Σ TURPE × 0.15 (post 2026-02-01) ou × 0.2193 (pré 2026-02-01)
    - Si écart > 10 % de l'attendu (et > 5 €) → R21 anomalie

    Returns:
        BillAnomaly ou None
    """
    from datetime import date as _date

    from models.enums import InvoiceLineType

    lines = invoice.lines or []
    network_lines = [
        line for line in lines if line.line_type == InvoiceLineType.NETWORK and line.amount_eur is not None
    ]
    cta_lines = [
        line for line in lines if line.line_type == InvoiceLineType.TAX and line.label and "CTA" in line.label.upper()
    ]
    if not network_lines or not cta_lines:
        return None

    turpe_total = sum(float(line.amount_eur or 0) for line in network_lines)
    cta_facturee = sum(float(line.amount_eur or 0) for line in cta_lines)
    if turpe_total <= 0:
        return None

    # Date de référence : period_start ou issue_date
    ref_date = invoice.period_start or invoice.issue_date or _date.today()
    cutover = _date(2026, 2, 1)
    cta_rate = 0.15 if ref_date >= cutover else 0.2193  # distribution élec
    cta_attendue = turpe_total * cta_rate
    if cta_attendue <= 0:
        return None

    ecart_eur = cta_facturee - cta_attendue
    ecart_pct = abs(ecart_eur) / cta_attendue * 100

    # Seuils : > 10 % d'écart ET > 5 € absolu (anti-bruit arrondis)
    if ecart_pct < 10 or abs(ecart_eur) < 5:
        return None

    severity = "critical" if abs(ecart_eur) > 100 else "warning"
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R21",
        severity=severity,
        threshold_value=Decimal("10.0"),  # %
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

    # Récupère Σ MeterReading.value_kwh sur fenêtre période invoice
    from sqlalchemy import func

    sum_readings = (
        db.query(func.sum(MeterReading.value_kwh))
        .join(Meter, Meter.id == MeterReading.meter_id)
        .filter(
            Meter.site_id == invoice.site_id,
            MeterReading.timestamp >= invoice.period_start,
            MeterReading.timestamp <= invoice.period_end,
        )
        .scalar()
    )
    count_readings = (
        db.query(func.count(MeterReading.id))
        .join(Meter, Meter.id == MeterReading.meter_id)
        .filter(
            Meter.site_id == invoice.site_id,
            MeterReading.timestamp >= invoice.period_start,
            MeterReading.timestamp <= invoice.period_end,
        )
        .scalar()
        or 0
    )

    if sum_readings is None or sum_readings <= 0:
        return None
    if count_readings < 7:  # Couverture insuffisante (cas import partiel)
        return None

    conso_facturee = float(invoice.energy_kwh)
    conso_mesuree = float(sum_readings)
    ecart_kwh = conso_facturee - conso_mesuree
    ecart_pct = abs(ecart_kwh) / conso_mesuree * 100 if conso_mesuree > 0 else 0

    # Seuils anti-bruit : > 10 % ET > 100 kWh
    if ecart_pct < 10 or abs(ecart_kwh) < 100:
        return None

    severity = "critical" if abs(ecart_kwh) > 1000 else "warning"
    # Estimation impact € via prix marginal CRE T4 2025 ETI tertiaire (130 €/MWh)
    from doctrine.constants import PRICE_ELEC_ETI_2026_EUR_PER_MWH

    montant_impact_eur = round(abs(ecart_kwh) / 1000 * PRICE_ELEC_ETI_2026_EUR_PER_MWH, 2)

    return BillAnomaly(
        invoice_id=invoice.id,
        code="R27",
        severity=severity,
        threshold_value=Decimal("10.0"),
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

    total_facture = float(invoice.total_eur)
    # 2 hypothèses : lignes en TTC (=total_eur) ou en HT (×1.20 ≈ total_eur)
    ecart_ttc = total_lignes_ht - total_facture
    ecart_ht_x_tva = (total_lignes_ht * 1.20) - total_facture

    # Le scénario qui colle le mieux gagne
    ecart_eur = min((ecart_ttc, ecart_ht_x_tva), key=abs)
    pct_base = total_facture
    ecart_pct = abs(ecart_eur) / pct_base * 100 if pct_base > 0 else 0

    if ecart_pct < 5 or abs(ecart_eur) < 5:
        return None

    severity = "critical" if abs(ecart_eur) > 50 else "warning"
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R26",
        severity=severity,
        threshold_value=Decimal("5.0"),
        actual_value=Decimal(str(round(ecart_pct, 2))),
        details_json={
            "total_eur_facture": round(total_facture, 2),
            "total_lignes_ht": round(total_lignes_ht, 2),
            "total_lignes_x_tva20": round(total_lignes_ht * 1.20, 2),
            "ecart_eur": round(ecart_eur, 2),
            "ecart_pct": round(ecart_pct, 2),
            "lines_count": len(lines),
            "regulatory_ref": "Cohérence comptable interne (sanity check)",
            "montant_anomalie_eur": round(abs(ecart_eur), 2),
        },
    )


# ─── R25 Abonnement divergent contrat (Phase L Jean-Marc CFO ROI 1-3 k€/an) ─


def detect_r25_subscription_mismatch(invoice: EnergyInvoice, db: Session) -> Optional[BillAnomaly]:
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

    if not invoice.contract_id:
        return None

    contract = invoice.contract  # SQLAlchemy back_populates relation
    if contract is None or contract.fixed_fee_eur_per_month is None:
        return None
    fixed_fee_attendu = float(contract.fixed_fee_eur_per_month)
    if fixed_fee_attendu <= 0:
        return None

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
    # Calcul mensuel : si invoice couvre N mois, on prorate
    if invoice.period_start and invoice.period_end:
        days = (invoice.period_end - invoice.period_start).days + 1
        months_covered = max(1.0, days / 30.4375)  # Avg jours/mois
        abo_mensuel_facture = abo_facture / months_covered
    else:
        abo_mensuel_facture = abo_facture  # Hypothèse 1 mois si période inconnue

    ecart_eur = abo_mensuel_facture - fixed_fee_attendu
    ecart_pct = abs(ecart_eur) / fixed_fee_attendu * 100

    # Seuils anti-bruit : > 5 % d'écart ET > 2 € absolu
    if ecart_pct < 5 or abs(ecart_eur) < 2:
        return None

    severity = "critical" if abs(ecart_eur) > 20 else "warning"
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R25",
        severity=severity,
        threshold_value=Decimal("5.0"),
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
    invoice: EnergyInvoice, db: Session, *, dp_category_cache: Optional[dict] = None
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
    from models.enums import InvoiceLineType

    if not invoice.energy_kwh or invoice.energy_kwh <= 0:
        return None

    accise_lines = [
        line
        for line in (invoice.lines or [])
        if line.line_type == InvoiceLineType.TAX
        and line.label
        and re.search(r"\b(accise|ticfe|cspe|contrib.*service.*public)", line.label, re.IGNORECASE)
    ]
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

    # Seuils selon source catégorie :
    # - DP_CATEGORY (catégorie connue) : 10 % d'écart suffit (haute confiance)
    # - FALLBACK T1 : 35 % d'écart (couvre marge T2/HP légitime)
    threshold_pct = 10.0 if category_source == "DP_CATEGORY" else 35.0
    if ecart_pct < threshold_pct or abs(ecart_eur) < 5:
        return None

    severity = "critical" if abs(ecart_eur) > 50 else "warning"
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


def detect_r24_tva_rate_mismatch(invoice: EnergyInvoice, db: Session) -> Optional[BillAnomaly]:
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
    from models.enums import InvoiceLineType

    lines = invoice.lines or []
    tva_lines = [
        line
        for line in lines
        if line.line_type == InvoiceLineType.TAX
        and line.label
        and re.search(r"\bTVA\b|\bVAT\b", line.label, re.IGNORECASE)
    ]
    if not tva_lines:
        return None

    # Total HT = somme de toutes les lignes non-TVA
    ht_total = sum(
        float(line.amount_eur or 0)
        for line in lines
        if not (
            line.line_type == InvoiceLineType.TAX
            and line.label
            and re.search(r"\bTVA\b|\bVAT\b", line.label, re.IGNORECASE)
        )
    )
    tva_facturee = sum(float(line.amount_eur or 0) for line in tva_lines)
    if ht_total <= 0:
        return None

    taux_effectif_pct = (tva_facturee / ht_total) * 100
    # Taux attendu B2B tertiaire : 20 % (exception 5,5 % CTA + accise = composite)
    # MVP : on flag écart > 0,5 pt vs 20 % (couvre erreur 19,6/19,3/etc.)
    taux_attendu_pct = 20.0
    ecart_pct_abs = abs(taux_effectif_pct - taux_attendu_pct)

    if ecart_pct_abs < 0.5 or tva_facturee < 10:
        return None

    severity = "critical" if ecart_pct_abs > 5.0 else "warning"
    return BillAnomaly(
        invoice_id=invoice.id,
        code="R24",
        severity=severity,
        threshold_value=Decimal("0.5"),  # pt %
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


def detect_r23_turpe_double(invoice: EnergyInvoice, db: Session) -> list[BillAnomaly]:
    """R23 — TURPE doublé : 2+ lignes TURPE pour même période sur invoice unique.

    Persona Jean-Marc CFO cardinal Phase H : impact ROI 6-15 k€/an récupérables
    sur portefeuille tertiaire IDF (5 % des factures observées en doublon
    bascule HTA/BT ou changement fournisseur).

    Heuristique :
    - Regrouper EnergyInvoiceLine `line_type=NETWORK` par période détectée
      (HPH / HCH / HPB / HCB / P / HP / HC / BASE)
    - Si ≥ 2 lignes pour même période sur même invoice → R23 anomalie
    - Sévérité `critical` si total doublé > 100 € ; `warning` sinon

    Returns:
        list[BillAnomaly] : 0..N anomalies (1 par groupe période doublé)
    """
    from collections import defaultdict

    from models.enums import InvoiceLineType

    network_lines = [
        line
        for line in (invoice.lines or [])
        if line.line_type == InvoiceLineType.NETWORK and line.amount_eur is not None
    ]
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

    anomalies: list[BillAnomaly] = []
    for period, lines in by_period.items():
        if len(lines) < 2:
            continue
        # Doublon détecté : même période sur 2+ lignes NETWORK
        total_doublon_eur = sum(float(line.amount_eur or 0) for line in lines[1:])
        # On considère que la 1ère ligne est légitime, les suivantes sont doublons
        severity = "critical" if total_doublon_eur > 100 else "warning"
        anomalies.append(
            BillAnomaly(
                invoice_id=invoice.id,
                code="R23",
                severity=severity,
                threshold_value=Decimal("100.0"),
                actual_value=Decimal(str(round(total_doublon_eur, 2))),
                details_json={
                    "period_code": period,
                    "duplicate_count": len(lines),
                    "duplicate_lines_ids": [line.id for line in lines],
                    "montant_anomalie_eur": round(total_doublon_eur, 2),
                    "regulatory_ref": "CRE Délib. 2025-78 art. 8 — TURPE 7 facturation unique période",
                },
            )
        )
    return anomalies


# ─── Pipeline ───────────────────────────────────────────────────────────────


def detect_anomalies_for_invoice(
    invoice: EnergyInvoice,
    db: Session,
    *,
    dp_category_cache: Optional[dict] = None,
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

    # R23 : 0..N anomalies (1 par période doublée) — Phase H cardinal CFO
    try:
        r23_list = detect_r23_turpe_double(invoice, db)
        for r23 in r23_list:
            db.add(r23)
            anomalies.append(r23)
    except Exception as e:
        _logger.error(f"R23 detector failed for invoice {invoice.id}: {e}")

    # R21 : 0 ou 1 — Phase H CFO CTA mauvais calcul
    try:
        r21 = detect_r21_cta_mismatch(invoice, db)
        if r21:
            db.add(r21)
            anomalies.append(r21)
    except Exception as e:
        _logger.error(f"R21 detector failed for invoice {invoice.id}: {e}")

    # R22 : 0 ou 1 — Phase I CFO accise erronée (cache K2 propagé Phase K audit fix)
    try:
        r22 = detect_r22_accise_mismatch(invoice, db, dp_category_cache=dp_category_cache)
        if r22:
            db.add(r22)
            anomalies.append(r22)
    except Exception as e:
        _logger.error(f"R22 detector failed for invoice {invoice.id}: {e}")

    # R24 : 0 ou 1 — Phase I CFO TVA mauvais taux
    try:
        r24 = detect_r24_tva_rate_mismatch(invoice, db)
        if r24:
            db.add(r24)
            anomalies.append(r24)
    except Exception as e:
        _logger.error(f"R24 detector failed for invoice {invoice.id}: {e}")

    # R25 : 0 ou 1 — Phase L CFO abonnement divergent contrat
    try:
        r25 = detect_r25_subscription_mismatch(invoice, db)
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

    return anomalies
