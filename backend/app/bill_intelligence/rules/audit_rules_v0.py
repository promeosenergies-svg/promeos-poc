"""
PROMEOS Bill Intelligence — 20 Audit Rules V0
Regles arithmetiques + coherence + TVA + structure.
Chaque regle retourne une liste d'InvoiceAnomaly.

Principe P1 : aucune valeur chiffree sans source.
Les taux/seuils utilises ici sont des constantes legislatives universelles
(TVA 5.5%/20%, tolerance arrondi 0.01 EUR) — pas des tarifs specifiques.
"""
import uuid
from typing import List, Optional

from ..domain import (
    Invoice, InvoiceAnomaly, InvoiceComponent,
    AnomalyType, AnomalySeverity, ComponentType,
)


# ========================================
# Constantes (universelles, pas de tarif)
# ========================================
TOLERANCE_EUR = 0.02  # tolerance arrondi
TVA_REDUITE = 5.5
TVA_NORMALE = 20.0
# Composantes a TVA reduite (abonnement, CTA, TURPE gestion)
COMPONENTS_TVA_REDUITE = {
    ComponentType.ABONNEMENT,
    ComponentType.CTA,
    ComponentType.TURPE_FIXE,
    ComponentType.TERME_FIXE,
}


def _anom_id() -> str:
    return f"ANOM-{uuid.uuid4().hex[:8].upper()}"


# ========================================
# R01 — Somme composantes vs total HT
# ========================================
def rule_r01_sum_ht(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Somme des amount_ht des composantes == total_ht."""
    if invoice.total_ht is None:
        return []
    components_with_ht = [c for c in invoice.components if c.amount_ht is not None
                          and c.component_type not in (ComponentType.TVA_REDUITE, ComponentType.TVA_NORMALE)]
    if not components_with_ht:
        return []
    sum_ht = sum(c.amount_ht for c in components_with_ht)
    diff = abs(sum_ht - invoice.total_ht)
    if diff > TOLERANCE_EUR:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.ARITHMETIC_ERROR,
            severity=AnomalySeverity.ERROR,
            message=f"Somme composantes HT ({sum_ht:.2f}) != total HT facture ({invoice.total_ht:.2f}), ecart {diff:.2f} EUR",
            expected_value=invoice.total_ht,
            actual_value=sum_ht,
            difference=round(sum_ht - invoice.total_ht, 2),
            rule_card_id="RULE_R01_SUM_HT",
        )]
    return []


# ========================================
# R02 — Total TTC = Total HT + Total TVA
# ========================================
def rule_r02_ttc_check(invoice: Invoice) -> List[InvoiceAnomaly]:
    """TTC = HT + TVA."""
    if None in (invoice.total_ht, invoice.total_tva, invoice.total_ttc):
        return []
    expected_ttc = invoice.total_ht + invoice.total_tva
    diff = abs(expected_ttc - invoice.total_ttc)
    if diff > TOLERANCE_EUR:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.TOTAL_MISMATCH,
            severity=AnomalySeverity.ERROR,
            message=f"HT ({invoice.total_ht:.2f}) + TVA ({invoice.total_tva:.2f}) = {expected_ttc:.2f} != TTC ({invoice.total_ttc:.2f})",
            expected_value=expected_ttc,
            actual_value=invoice.total_ttc,
            difference=round(expected_ttc - invoice.total_ttc, 2),
            rule_card_id="RULE_R02_TTC_CHECK",
        )]
    return []


# ========================================
# R03 — TVA par composante (taux correct)
# ========================================
def rule_r03_tva_rate(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Verifie le taux TVA applicable par type de composante."""
    anomalies = []
    for comp in invoice.components:
        if comp.tva_rate is None:
            continue
        if comp.component_type in (ComponentType.TVA_REDUITE, ComponentType.TVA_NORMALE):
            continue
        expected_rate = TVA_REDUITE if comp.component_type in COMPONENTS_TVA_REDUITE else TVA_NORMALE
        if abs(comp.tva_rate - expected_rate) > 0.01:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.TVA_ERROR,
                severity=AnomalySeverity.ERROR,
                message=f"TVA {comp.label}: taux {comp.tva_rate}% applique, attendu {expected_rate}%",
                component_type=comp.component_type,
                expected_value=expected_rate,
                actual_value=comp.tva_rate,
                rule_card_id="RULE_R03_TVA_RATE",
            ))
    return anomalies


# ========================================
# R04 — TVA calcul (montant = base * taux)
# ========================================
def rule_r04_tva_amount(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Verifie montant TVA = amount_ht * tva_rate / 100."""
    anomalies = []
    for comp in invoice.components:
        if None in (comp.amount_ht, comp.tva_rate, comp.tva_amount):
            continue
        if comp.component_type in (ComponentType.TVA_REDUITE, ComponentType.TVA_NORMALE):
            continue
        expected_tva = round(comp.amount_ht * comp.tva_rate / 100, 2)
        diff = abs(expected_tva - comp.tva_amount)
        if diff > TOLERANCE_EUR:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.TVA_ERROR,
                severity=AnomalySeverity.WARNING,
                message=f"TVA {comp.label}: {comp.amount_ht:.2f} * {comp.tva_rate}% = {expected_tva:.2f}, facture {comp.tva_amount:.2f}",
                component_type=comp.component_type,
                expected_value=expected_tva,
                actual_value=comp.tva_amount,
                difference=round(expected_tva - comp.tva_amount, 2),
                rule_card_id="RULE_R04_TVA_AMOUNT",
            ))
    return anomalies


# ========================================
# R05 — Quantite * prix unitaire = montant HT
# ========================================
def rule_r05_qty_price(invoice: Invoice) -> List[InvoiceAnomaly]:
    """qty * unit_price == amount_ht."""
    anomalies = []
    for comp in invoice.components:
        if None in (comp.quantity, comp.unit_price, comp.amount_ht):
            continue
        expected = round(comp.quantity * comp.unit_price, 2)
        diff = abs(expected - comp.amount_ht)
        if diff > TOLERANCE_EUR:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.ARITHMETIC_ERROR,
                severity=AnomalySeverity.WARNING,
                message=f"{comp.label}: {comp.quantity} * {comp.unit_price} = {expected:.2f} != {comp.amount_ht:.2f}",
                component_type=comp.component_type,
                expected_value=expected,
                actual_value=comp.amount_ht,
                difference=round(expected - comp.amount_ht, 2),
                rule_card_id="RULE_R05_QTY_PRICE",
            ))
    return anomalies


# ========================================
# R06 — Dates facture coherentes
# ========================================
def rule_r06_dates(invoice: Invoice) -> List[InvoiceAnomaly]:
    """period_start < period_end, invoice_date >= period_end."""
    anomalies = []
    if invoice.period_start and invoice.period_end:
        if invoice.period_start >= invoice.period_end:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.PERIOD_OVERLAP,
                severity=AnomalySeverity.ERROR,
                message=f"Periode invalide: debut {invoice.period_start} >= fin {invoice.period_end}",
                rule_card_id="RULE_R06_DATES",
            ))
    if invoice.invoice_date and invoice.due_date:
        if invoice.due_date < invoice.invoice_date:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.PERIOD_OVERLAP,
                severity=AnomalySeverity.WARNING,
                message=f"Echeance {invoice.due_date} avant date facture {invoice.invoice_date}",
                rule_card_id="RULE_R06_DATES",
            ))
    return anomalies


# ========================================
# R07 — Composantes obligatoires presentes
# ========================================
def rule_r07_required_components(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Verifie les composantes minimales attendues."""
    anomalies = []
    types_present = {c.component_type for c in invoice.components}

    # Electricite : conso + accise + CTA minimum
    if invoice.energy_type.value == "elec":
        for required in [ComponentType.ACCISE, ComponentType.CTA]:
            if required not in types_present:
                anomalies.append(InvoiceAnomaly(
                    anomaly_id=_anom_id(),
                    anomaly_type=AnomalyType.MISSING_COMPONENT,
                    severity=AnomalySeverity.WARNING,
                    message=f"Composante manquante pour facture elec: {required.value}",
                    component_type=required,
                    rule_card_id="RULE_R07_REQUIRED",
                ))

    # Gaz : conso + accise + CTA minimum
    if invoice.energy_type.value == "gaz":
        for required in [ComponentType.ACCISE, ComponentType.CTA]:
            if required not in types_present:
                anomalies.append(InvoiceAnomaly(
                    anomaly_id=_anom_id(),
                    anomaly_type=AnomalyType.MISSING_COMPONENT,
                    severity=AnomalySeverity.WARNING,
                    message=f"Composante manquante pour facture gaz: {required.value}",
                    component_type=required,
                    rule_card_id="RULE_R07_REQUIRED",
                ))

    return anomalies


# ========================================
# R08 — Montant negatif suspect
# ========================================
def rule_r08_negative_amount(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Montant HT negatif suspect (hors remise/regularisation)."""
    anomalies = []
    for comp in invoice.components:
        if comp.amount_ht is not None and comp.amount_ht < 0:
            if comp.component_type not in (ComponentType.REMISE, ComponentType.REGULARISATION):
                anomalies.append(InvoiceAnomaly(
                    anomaly_id=_anom_id(),
                    anomaly_type=AnomalyType.QUANTITY_ANOMALY,
                    severity=AnomalySeverity.WARNING,
                    message=f"Montant negatif suspect: {comp.label} = {comp.amount_ht:.2f} EUR",
                    component_type=comp.component_type,
                    actual_value=comp.amount_ht,
                    rule_card_id="RULE_R08_NEGATIVE",
                ))
    return anomalies


# ========================================
# R09 — Composante "autre" opaque
# ========================================
def rule_r09_opaque_component(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Composante de type 'autre' sans detail."""
    anomalies = []
    for comp in invoice.components:
        if comp.component_type == ComponentType.AUTRE:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.OTHER,
                severity=AnomalySeverity.INFO,
                message=f"Composante non identifiee: '{comp.label}' ({comp.amount_ht} EUR HT)",
                component_type=ComponentType.AUTRE,
                actual_value=comp.amount_ht,
                rule_card_id="RULE_R09_OPAQUE",
            ))
    return anomalies


# ========================================
# R10 — Doublon de composante
# ========================================
def rule_r10_duplicate(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Detection de composantes en double."""
    anomalies = []
    seen = {}
    for comp in invoice.components:
        key = (comp.component_type, comp.label)
        if key in seen:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.DUPLICATE_CHARGE,
                severity=AnomalySeverity.WARNING,
                message=f"Doublon: '{comp.label}' apparait plusieurs fois",
                component_type=comp.component_type,
                rule_card_id="RULE_R10_DUPLICATE",
            ))
        seen[key] = True
    return anomalies


# ========================================
# R11 — Consommation totale coherente
# ========================================
def rule_r11_conso_coherence(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Sum conso composantes == conso_kwh globale."""
    if invoice.conso_kwh is None:
        return []
    conso_types = {
        ComponentType.CONSO_HP, ComponentType.CONSO_HC, ComponentType.CONSO_BASE,
        ComponentType.CONSO_POINTE, ComponentType.CONSO_HPH, ComponentType.CONSO_HCH,
        ComponentType.CONSO_HPE, ComponentType.CONSO_HCE,
    }
    conso_components = [c for c in invoice.components if c.component_type in conso_types and c.quantity]
    if not conso_components:
        return []
    sum_conso = sum(c.quantity for c in conso_components)
    diff = abs(sum_conso - invoice.conso_kwh)
    if diff > 1:  # tolerance 1 kWh
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.QUANTITY_ANOMALY,
            severity=AnomalySeverity.WARNING,
            message=f"Conso composantes ({sum_conso:.0f} kWh) != conso globale ({invoice.conso_kwh:.0f} kWh)",
            expected_value=invoice.conso_kwh,
            actual_value=sum_conso,
            difference=round(sum_conso - invoice.conso_kwh, 0),
            rule_card_id="RULE_R11_CONSO",
        )]
    return []


# ========================================
# R12 — Accise base coherente avec conso
# ========================================
def rule_r12_accise_base(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Accise quantity == conso_kwh."""
    if invoice.conso_kwh is None:
        return []
    accise_comps = [c for c in invoice.components if c.component_type == ComponentType.ACCISE and c.quantity]
    anomalies = []
    for acc in accise_comps:
        if abs(acc.quantity - invoice.conso_kwh) > 1:
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.TAX_BASE_ERROR,
                severity=AnomalySeverity.WARNING,
                message=f"Base accise ({acc.quantity:.0f} kWh) != conso globale ({invoice.conso_kwh:.0f} kWh)",
                component_type=ComponentType.ACCISE,
                expected_value=invoice.conso_kwh,
                actual_value=acc.quantity,
                rule_card_id="RULE_R12_ACCISE_BASE",
            ))
    return anomalies


# ========================================
# R13 — Prix unitaire dans plage credible
# ========================================
def rule_r13_unit_price_range(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Prix unitaire energie dans plage credible."""
    anomalies = []
    conso_types = {
        ComponentType.CONSO_HP, ComponentType.CONSO_HC, ComponentType.CONSO_BASE,
        ComponentType.CONSO_POINTE, ComponentType.TERME_VARIABLE,
    }
    for comp in invoice.components:
        if comp.component_type in conso_types and comp.unit_price is not None:
            # Plage credible: 0.01 - 1.00 EUR/kWh
            if comp.unit_price < 0.01 or comp.unit_price > 1.00:
                anomalies.append(InvoiceAnomaly(
                    anomaly_id=_anom_id(),
                    anomaly_type=AnomalyType.UNIT_PRICE_ANOMALY,
                    severity=AnomalySeverity.WARNING,
                    message=f"Prix unitaire suspect: {comp.label} = {comp.unit_price} EUR/kWh (plage 0.01-1.00)",
                    component_type=comp.component_type,
                    actual_value=comp.unit_price,
                    rule_card_id="RULE_R13_UNIT_PRICE",
                ))
    return anomalies


# ========================================
# R14 — Periode > 35 jours (suspect)
# ========================================
def rule_r14_period_length(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Periode de facturation > 35 jours."""
    if not (invoice.period_start and invoice.period_end):
        return []
    days = (invoice.period_end - invoice.period_start).days
    if days > 35:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.PERIOD_OVERLAP,
            severity=AnomalySeverity.INFO,
            message=f"Periode facture = {days} jours (> 35), possible regularisation ou bi-mensuel",
            actual_value=float(days),
            rule_card_id="RULE_R14_PERIOD_LENGTH",
        )]
    return []


# ========================================
# R15 — Facture sans composante
# ========================================
def rule_r15_empty_invoice(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Facture sans aucune composante."""
    if len(invoice.components) == 0:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.MISSING_COMPONENT,
            severity=AnomalySeverity.CRITICAL,
            message="Facture sans aucune composante",
            rule_card_id="RULE_R15_EMPTY",
        )]
    return []


# ========================================
# R16 — Facture zero euros
# ========================================
def rule_r16_zero_total(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Total TTC = 0."""
    if invoice.total_ttc is not None and invoice.total_ttc == 0:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.TOTAL_MISMATCH,
            severity=AnomalySeverity.INFO,
            message="Total TTC = 0 EUR (facture rectificative ou avoir ?)",
            actual_value=0.0,
            rule_card_id="RULE_R16_ZERO",
        )]
    return []


# ========================================
# R17 — PDL/PCE manquant
# ========================================
def rule_r17_pdl_missing(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Point de livraison/comptage manquant."""
    if not invoice.pdl_pce:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.OTHER,
            severity=AnomalySeverity.INFO,
            message="PDL/PCE manquant — rattachement site impossible",
            rule_card_id="RULE_R17_PDL",
        )]
    return []


# ========================================
# R18 — Somme TVA composantes vs total TVA
# ========================================
def rule_r18_sum_tva(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Somme TVA composantes == total_tva."""
    if invoice.total_tva is None:
        return []
    comps_with_tva = [c for c in invoice.components if c.tva_amount is not None
                      and c.component_type not in (ComponentType.TVA_REDUITE, ComponentType.TVA_NORMALE)]
    if not comps_with_tva:
        return []
    sum_tva = sum(c.tva_amount for c in comps_with_tva)
    diff = abs(sum_tva - invoice.total_tva)
    if diff > TOLERANCE_EUR:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.TVA_ERROR,
            severity=AnomalySeverity.ERROR,
            message=f"Somme TVA composantes ({sum_tva:.2f}) != total TVA ({invoice.total_tva:.2f})",
            expected_value=invoice.total_tva,
            actual_value=sum_tva,
            difference=round(sum_tva - invoice.total_tva, 2),
            rule_card_id="RULE_R18_SUM_TVA",
        )]
    return []


# ========================================
# R19 — Penalite/depassement sans justification
# ========================================
def rule_r19_penalty(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Penalite ou depassement detecte."""
    anomalies = []
    for comp in invoice.components:
        if comp.component_type in (ComponentType.DEPASSEMENT_PUISSANCE, ComponentType.PENALITE, ComponentType.REACTIVE):
            anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.OTHER,
                severity=AnomalySeverity.WARNING,
                message=f"Penalite/depassement detecte: '{comp.label}' = {comp.amount_ht} EUR HT",
                component_type=comp.component_type,
                actual_value=comp.amount_ht,
                rule_card_id="RULE_R19_PENALTY",
            ))
    return anomalies


# ========================================
# R20 — Montant total eleve (seuil)
# ========================================
def rule_r20_high_total(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Montant total TTC > 50 000 EUR — signalement."""
    if invoice.total_ttc and invoice.total_ttc > 50000:
        return [InvoiceAnomaly(
            anomaly_id=_anom_id(),
            anomaly_type=AnomalyType.OTHER,
            severity=AnomalySeverity.INFO,
            message=f"Montant TTC eleve: {invoice.total_ttc:.2f} EUR (> 50 000 EUR) — verification manuelle recommandee",
            actual_value=invoice.total_ttc,
            rule_card_id="RULE_R20_HIGH_TOTAL",
        )]
    return []


# ========================================
# Registre de toutes les regles
# ========================================

ALL_RULES = [
    ("R01", "Somme composantes vs total HT", rule_r01_sum_ht),
    ("R02", "TTC = HT + TVA", rule_r02_ttc_check),
    ("R03", "TVA taux correct par composante", rule_r03_tva_rate),
    ("R04", "TVA montant = base * taux", rule_r04_tva_amount),
    ("R05", "Quantite * prix unitaire = montant", rule_r05_qty_price),
    ("R06", "Dates coherentes", rule_r06_dates),
    ("R07", "Composantes obligatoires presentes", rule_r07_required_components),
    ("R08", "Montant negatif suspect", rule_r08_negative_amount),
    ("R09", "Composante opaque (type autre)", rule_r09_opaque_component),
    ("R10", "Doublon composante", rule_r10_duplicate),
    ("R11", "Conso composantes vs conso globale", rule_r11_conso_coherence),
    ("R12", "Base accise vs conso", rule_r12_accise_base),
    ("R13", "Prix unitaire dans plage credible", rule_r13_unit_price_range),
    ("R14", "Periode > 35 jours", rule_r14_period_length),
    ("R15", "Facture sans composante", rule_r15_empty_invoice),
    ("R16", "Total TTC = 0", rule_r16_zero_total),
    ("R17", "PDL/PCE manquant", rule_r17_pdl_missing),
    ("R18", "Somme TVA vs total TVA", rule_r18_sum_tva),
    ("R19", "Penalite/depassement", rule_r19_penalty),
    ("R20", "Montant total eleve", rule_r20_high_total),
]


def run_all_rules(invoice: Invoice) -> List[InvoiceAnomaly]:
    """Execute les 20 regles V0 sur une facture."""
    all_anomalies = []
    for rule_id, rule_name, rule_fn in ALL_RULES:
        try:
            anomalies = rule_fn(invoice)
            all_anomalies.extend(anomalies)
        except Exception as e:
            all_anomalies.append(InvoiceAnomaly(
                anomaly_id=_anom_id(),
                anomaly_type=AnomalyType.OTHER,
                severity=AnomalySeverity.INFO,
                message=f"Erreur execution regle {rule_id} ({rule_name}): {str(e)[:100]}",
                rule_card_id=f"RULE_{rule_id}_ERROR",
            ))
    return all_anomalies
