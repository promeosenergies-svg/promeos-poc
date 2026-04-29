"""
PROMEOS — Lever Engine service (migration JS → Python).

Phase 1.4.c du sprint refonte cockpit dual sol2 (29/04/2026). Migration
de `frontend/src/models/leverEngineModel.js` (291 lignes, V1+V35+V36+V37+V39+V42+V43+V44)
vers backend Python pour respecter la règle d'or CLAUDE.md #1 :
zero business logic in frontend.

Logique :
    Agrège les leviers activables à partir des KPIs et signals :
    - Conformité (nonConformes, aRisque, tertiaire, EFA)
    - Facturation (anomalies, surcoût)
    - Optimisation (1% du facturé)
    - Achat d'énergie (renouvellement, contrats manquants)
    - Data activation (briques manquantes)

Types de leviers : 'conformite' | 'facturation' | 'optimisation' | 'achat' | 'data_activation'

Exports :
    Lever                       — dataclass d'un levier
    LeverResult                 — dataclass du résultat agrégé
    compute_actionable_levers() — fonction principale
    is_compliance_available()   — helper signals conformité
    is_billing_insights_available() — helper insights facturation
    is_purchase_available()     — helper signaux achat

Compatibilité : accepte les clés camelCase legacy (nonConformes, aRisque,
risqueTotal) en plus des clés snake_case.
"""

from dataclasses import dataclass, field
from typing import Optional

from doctrine.constants import COCKPIT_ACTIVATION_THRESHOLD, COCKPIT_OPTIM_RATE_V1

# ── Constantes canoniques ────────────────────────────────────────────────────
# Single SoT : doctrine/constants.py (cf /simplify audit P0 — dedup avec
# data_activation_service.py qui importe les mêmes constantes).

ACTIVATION_THRESHOLD = COCKPIT_ACTIVATION_THRESHOLD

# Nombre total de dimensions d'activation (transposé depuis ACTIVATION_DIMENSIONS.length = 5)
TOTAL_ACTIVATION_DIMENSIONS = 5

OPTIM_RATE_V1 = COCKPIT_OPTIM_RATE_V1


# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class Lever:
    """
    Représentation d'un levier actionnable.

    Attributes:
        lever_type: 'conformite' | 'facturation' | 'optimisation' | 'achat' | 'data_activation'
        action_key: clé unique pour idempotency et deep-link (ex: 'lev-conf-nc')
        label: description FR du levier
        impact_eur: impact estimé en euros (None si inconnu)
        cta_path: route cible
        proof_hint: description de la preuve attendue (optionnel)
        proof_links: liens vers preuves disponibles (optionnel)
        reasons_fr: lignes de justification FR (optionnel, V43+)
    """

    lever_type: str
    action_key: str
    label: str
    impact_eur: Optional[float]
    cta_path: str
    proof_hint: Optional[str] = None
    proof_links: Optional[list] = None
    reasons_fr: Optional[list] = None

    def to_dict(self) -> dict:
        d = {
            "type": self.lever_type,
            "actionKey": self.action_key,
            "label": self.label,
            "impactEur": self.impact_eur,
            "ctaPath": self.cta_path,
        }
        if self.proof_hint is not None:
            d["proofHint"] = self.proof_hint
        if self.proof_links is not None:
            d["proofLinks"] = self.proof_links
        if self.reasons_fr is not None:
            d["reasons_fr"] = self.reasons_fr
        return d


@dataclass
class LeverResult:
    """
    Résultat agrégé du moteur de leviers.

    Attributes:
        total_levers: nombre total de leviers
        levers_by_type: répartition par type
        estimated_impact_eur: somme risque + surcoût (si disponibles)
        top_levers: leviers triés par impact_eur desc (None en dernier)
    """

    total_levers: int
    levers_by_type: dict
    estimated_impact_eur: float
    top_levers: list

    def to_dict(self) -> dict:
        return {
            "totalLevers": self.total_levers,
            "leversByType": self.levers_by_type,
            "estimatedImpactEur": self.estimated_impact_eur,
            "topLevers": [lv.to_dict() for lv in self.top_levers],
        }


# ── Helpers signals contracts ────────────────────────────────────────────────


def is_compliance_available(compliance_signals: Optional[dict]) -> bool:
    """Vérifie si des signaux conformité sont disponibles et non vides."""
    if not compliance_signals or not isinstance(compliance_signals, dict):
        return False
    signals = compliance_signals.get("signals", [])
    return isinstance(signals, list) and len(signals) > 0


def is_billing_insights_available(billing_insights: Optional[dict]) -> bool:
    """Vérifie si des insights facturation sont disponibles et non vides."""
    if not billing_insights or not isinstance(billing_insights, dict):
        return False
    count = billing_insights.get("anomalies_count", 0) or 0
    loss = billing_insights.get("total_loss_eur", 0) or 0
    return count > 0 or loss > 0


def is_purchase_available(purchase_signals: Optional[dict]) -> bool:
    """Vérifie si des signaux achat d'énergie sont disponibles et non vides.

    Sémantique stricte : au moins un contrat existant (totalContracts > 0).
    `totalSites > 0` seul ne suffit pas — un site sans contrat ne fournit
    pas de signal d'achat exploitable. Tolère snake_case `total_contracts`.

    Aligné /simplify audit P0 (29/04/2026) : SoT unique pour les 2 services
    cockpit (lever_engine + data_activation).
    """
    if not purchase_signals or not isinstance(purchase_signals, dict):
        return False
    total_contracts = purchase_signals.get("totalContracts", purchase_signals.get("total_contracts", 0)) or 0
    return total_contracts > 0


def _compute_activated_count(kpis: dict, billing_summary: dict, purchase_signals: Optional[dict]) -> int:
    """
    Compte rapide des briques d'activation actives (0-5).
    Transposé depuis dataActivationModel.js::computeActivatedCount().
    """
    total = kpis.get("total", 0) or 0
    conformes = (
        (kpis.get("conformes", 0) or 0)
        + (kpis.get("nonConformes", kpis.get("non_conformes", 0)) or 0)
        + (kpis.get("aRisque", kpis.get("a_risque", 0)) or 0)
    )
    couverture_donnees = kpis.get("couvertureDonnees", kpis.get("couverture_donnees", 0)) or 0
    has_billing = (billing_summary.get("total_invoices", 0) or billing_summary.get("total_eur", 0) or 0) > 0
    has_purchase = is_purchase_available(purchase_signals)

    booleans = [
        total > 0,
        conformes > 0,
        couverture_donnees > 0,
        has_billing,
        has_purchase,
    ]
    return sum(1 for b in booleans if b)


# ── Fonction principale ──────────────────────────────────────────────────────


def compute_actionable_levers(
    kpis: Optional[dict] = None,
    billing_summary: Optional[dict] = None,
    compliance_signals: Optional[dict] = None,
    billing_insights: Optional[dict] = None,
    purchase_signals: Optional[dict] = None,
) -> LeverResult:
    """
    Calcule les leviers activables à partir des données scope.

    Transposé fidèlement depuis leverEngineModel.js (V1+V35+V36+V37+V39+V42+V43+V44).
    Accepte les clés camelCase legacy (nonConformes, aRisque, risqueTotal) pour
    compatibilité avec les dicts KPI existants.

    Args:
        kpis: dict KPI Cockpit (total, nonConformes/non_conformes, aRisque/a_risque,
              risqueTotal/risque_total_eur, couvertureDonnees, _tertiaireIssues,
              _tertiaireSiteSignals, etc.)
        billing_summary: résumé billing (total_eur, total_loss_eur,
                         invoices_with_anomalies, total_invoices)
        compliance_signals: dict normalisé ComplianceSignals (optionnel, V35)
        billing_insights: dict BillingInsights (optionnel, V35)
        purchase_signals: dict PurchaseSignals (optionnel, V36)

    Returns:
        LeverResult avec total_levers, levers_by_type, estimated_impact_eur, top_levers.
    """
    k = kpis or {}
    bs = billing_summary or {}
    levers: list[Lever] = []

    has_compliance = is_compliance_available(compliance_signals)
    has_billing_insights = is_billing_insights_available(billing_insights)
    has_purchase = is_purchase_available(purchase_signals)

    # ── Conformité ────────────────────────────────────────────────────────────
    # Tolérance camelCase legacy (nonConformes, aRisque, risqueTotal)
    non_conformes = k.get("nonConformes", k.get("non_conformes", 0)) or 0
    a_risque = k.get("aRisque", k.get("a_risque", 0)) or 0
    risque_total = k.get("risqueTotal", k.get("risque_total_eur", 0)) or 0
    total_risque_sites = non_conformes + a_risque

    # V35 : enrichissement conformité via compliance_signals
    comp_signals_list = compliance_signals.get("signals", []) if has_compliance else []
    comp_high_count = sum(1 for s in comp_signals_list if s.get("severity") in ("critical", "high"))
    comp_proof_hint = None
    if comp_signals_list and comp_signals_list[0].get("proof_expected"):
        comp_proof_hint = comp_signals_list[0]["proof_expected"]

    if non_conformes > 0:
        nc_s = "s" if non_conformes > 1 else ""
        if has_compliance and comp_high_count > 0:
            cs = "s" if comp_high_count > 1 else ""
            label = (
                f"Régulariser {non_conformes} site{nc_s} non conforme{nc_s} ({comp_high_count} signal{cs} critique{cs})"
            )
        else:
            label = f"Régulariser {non_conformes} site{nc_s} non conforme{nc_s}"

        impact = round(risque_total * (non_conformes / (total_risque_sites or 1))) if risque_total > 0 else None
        levers.append(
            Lever(
                lever_type="conformite",
                action_key="lev-conf-nc",
                label=label,
                impact_eur=impact,
                cta_path="/conformite",
                proof_hint=comp_proof_hint,
            )
        )

    if a_risque > 0:
        ar_s = "s" if a_risque > 1 else ""
        impact = round(risque_total * (a_risque / (total_risque_sites or 1))) if risque_total > 0 else None
        levers.append(
            Lever(
                lever_type="conformite",
                action_key="lev-conf-ar",
                label=f"Prévenir {a_risque} site{ar_s} à risque",
                impact_eur=impact,
                cta_path="/conformite",
                proof_hint=comp_proof_hint,
            )
        )

    # ── Facturation ───────────────────────────────────────────────────────────
    anomalies = bs.get("invoices_with_anomalies", bs.get("total_insights", 0)) or 0
    total_loss = max(0, bs.get("total_loss_eur", 0) or 0)

    # V35 : enrichissement facturation via billing_insights
    bi_anom = billing_insights.get("anomalies_count", 0) if has_billing_insights else 0
    bi_loss = billing_insights.get("total_loss_eur", 0) if has_billing_insights else 0
    bi_conf = billing_insights.get("confidence", None) if has_billing_insights else None
    bi_proofs = (
        billing_insights.get("proof_links") if has_billing_insights and billing_insights.get("proof_links") else None
    )

    effective_anomalies = bi_anom if has_billing_insights else anomalies
    effective_loss = max(bi_loss, total_loss) if has_billing_insights else total_loss

    if bi_conf == "high":
        conf_label = " (confiance haute)"
    elif bi_conf == "medium":
        conf_label = " (confiance moyenne)"
    else:
        conf_label = ""

    if effective_anomalies > 0:
        ea_s = "s" if effective_anomalies > 1 else ""
        levers.append(
            Lever(
                lever_type="facturation",
                action_key="lev-fact-anom",
                label=f"Corriger {effective_anomalies} anomalie{ea_s} facture{conf_label}",
                impact_eur=effective_loss if effective_loss > 0 else None,
                cta_path="/bill-intel",
                proof_links=bi_proofs,
            )
        )
    elif effective_loss > 0:
        levers.append(
            Lever(
                lever_type="facturation",
                action_key="lev-fact-loss",
                label="Récupérer le surcoût facture détecté",
                impact_eur=effective_loss,
                cta_path="/bill-intel",
                proof_links=bi_proofs,
            )
        )

    # ── Optimisation ──────────────────────────────────────────────────────────
    total_eur = bs.get("total_eur", 0) or 0
    if total_eur > 0:
        levers.append(
            Lever(
                lever_type="optimisation",
                action_key="lev-optim-ener",
                label="Lancer l'optimisation énergétique",
                impact_eur=round(total_eur * OPTIM_RATE_V1),
                cta_path="/diagnostic-conso",
            )
        )

    # ── Achat d'énergie V36 ───────────────────────────────────────────────────
    if has_purchase:
        exp_count = purchase_signals.get("expiringSoonCount", 0) or 0
        missing_count = purchase_signals.get("missingContractsCount", 0) or 0
        exp_sites = purchase_signals.get("expiringSoonSites", []) or []
        estimated_exposure = purchase_signals.get("estimatedExposureEur", None)

        if exp_count > 0:
            ec_s = "s" if exp_count > 1 else ""
            es_s = "s" if len(exp_sites) > 1 else ""
            levers.append(
                Lever(
                    lever_type="achat",
                    action_key="lev-achat-renew",
                    label=(f"Renouveler {exp_count} contrat{ec_s} d'énergie ({len(exp_sites)} site{es_s})"),
                    impact_eur=estimated_exposure,
                    cta_path="/achat-energie?filter=renewal",
                    proof_hint="Contrat de fourniture / avenants / échéancier",
                )
            )

        if missing_count > 0:
            mc_s = "s" if missing_count > 1 else ""
            levers.append(
                Lever(
                    lever_type="achat",
                    action_key="lev-achat-data",
                    label=f"Completer {missing_count} site{mc_s} sans contrat energie",
                    impact_eur=None,
                    cta_path="/achat-energie?filter=missing",
                )
            )

    # ── Tertiaire / OPERAT V39 ────────────────────────────────────────────────
    tertiaire_issues = k.get("_tertiaireIssues", 0) or 0
    tertiaire_critical = k.get("_tertiaireCritical", 0) or 0
    if tertiaire_issues > 0:
        ti_s = "s" if tertiaire_issues > 1 else ""
        severity_label = ""
        if tertiaire_critical > 0:
            tc_s = "s" if tertiaire_critical > 1 else ""
            severity_label = f" ({tertiaire_critical} critique{tc_s})"
        impact = None
        if risque_total > 0 and total_risque_sites > 0:
            impact = round(risque_total * (tertiaire_issues / (total_risque_sites + tertiaire_issues)))
        levers.append(
            Lever(
                lever_type="conformite",
                action_key="lev-tertiaire-efa",
                label=f"Corriger {tertiaire_issues} anomalie{ti_s} Décret tertiaire{severity_label}",
                impact_eur=impact,
                cta_path="/conformite/tertiaire/anomalies",
                proof_hint="Attestation OPERAT ou dossier de modulation — Estimation V1",
            )
        )

    # ── Tertiaire / Site signals V42 + V43 explainability ─────────────────────
    tertiaire_site_signals = k.get("_tertiaireSiteSignals", {}) or {}
    uncovered_probable = tertiaire_site_signals.get("uncovered_probable", 0) or 0
    incomplete_data = tertiaire_site_signals.get("incomplete_data", 0) or 0
    signal_sites = tertiaire_site_signals.get("sites", []) or []
    top_missing_fields = tertiaire_site_signals.get("top_missing_fields", {}) or {}

    if uncovered_probable > 0:
        sample_site = next(
            (s for s in signal_sites if s.get("signal") == "assujetti_probable" and not s.get("is_covered")),
            None,
        )
        reasons = sample_site.get("reasons_fr", []) if sample_site else []
        rationale_lines = list(reasons[:2]) + ["Aucune EFA créée — action recommandée"]
        cta_site_id = sample_site.get("site_id") if sample_site else None
        cta_path = f"/conformite/tertiaire/wizard?site_id={cta_site_id}" if cta_site_id else "/conformite/tertiaire"
        up_s = "s" if uncovered_probable > 1 else ""
        levers.append(
            Lever(
                lever_type="conformite",
                action_key="lev-tertiaire-create-efa",
                label=(f"Créer une EFA pour {uncovered_probable} site{up_s} assujetti{up_s} probable{up_s}"),
                impact_eur=None,
                cta_path=cta_path,
                proof_hint="Attestation OPERAT ou justificatif de surface",
                reasons_fr=rationale_lines,
            )
        )

    if incomplete_data > 0:
        missing_labels = []
        for field_key, fr_label in [
            ("surface", "surface"),
            ("batiments", "bâtiments"),
            ("usage_site", "usage"),
            ("surface_batiment", "surfaces bâtiment"),
        ]:
            cnt = top_missing_fields.get(field_key, 0) or 0
            if cnt > 0:
                s = "s" if cnt > 1 else ""
                missing_labels.append(f"{fr_label} ({cnt} site{s})")
        id_s = "s" if incomplete_data > 1 else ""
        rationale_lines = [
            f"{incomplete_data} site{id_s} avec données incomplètes",
            (
                f"Données manquantes : {', '.join(missing_labels)}"
                if missing_labels
                else "Qualification impossible sans données complètes"
            ),
            "Heuristique V1 — à confirmer par analyse réglementaire",
        ]
        levers.append(
            Lever(
                lever_type="data_activation",
                action_key="lev-tertiaire-complete-patrimoine",
                label=(f"Compléter les données de {incomplete_data} site{id_s} pour qualifier l'assujettissement"),
                impact_eur=None,
                cta_path="/patrimoine",
                reasons_fr=rationale_lines,
            )
        )

    # ── Activation données V37 ────────────────────────────────────────────────
    activated_count = _compute_activated_count(k, bs, purchase_signals)
    total_kpis = k.get("total", 0) or 0
    if total_kpis > 0 and activated_count < ACTIVATION_THRESHOLD:
        missing = TOTAL_ACTIVATION_DIMENSIONS - activated_count
        ms = "s" if missing > 1 else ""
        me = "s" if missing > 1 else ""
        levers.append(
            Lever(
                lever_type="data_activation",
                action_key="lev-data-cover",
                label=f"Compléter {missing} brique{ms} de données manquante{me}",
                impact_eur=None,
                cta_path="/activation",
            )
        )

    # ── Agrégation ────────────────────────────────────────────────────────────
    top_levers = sorted(levers, key=lambda lv: (lv.impact_eur is None, -(lv.impact_eur or 0)))

    levers_by_type = {
        "conformite": sum(1 for lv in levers if lv.lever_type == "conformite"),
        "facturation": sum(1 for lv in levers if lv.lever_type == "facturation"),
        "optimisation": sum(1 for lv in levers if lv.lever_type == "optimisation"),
        "achat": sum(1 for lv in levers if lv.lever_type == "achat"),
        "data_activation": sum(1 for lv in levers if lv.lever_type == "data_activation"),
    }

    estimated_impact_eur = (risque_total if risque_total > 0 else 0) + (total_loss if total_loss > 0 else 0)

    return LeverResult(
        total_levers=len(levers),
        levers_by_type=levers_by_type,
        estimated_impact_eur=estimated_impact_eur,
        top_levers=top_levers,
    )
