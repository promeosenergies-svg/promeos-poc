"""
PROMEOS — Impact & Décision service (migration JS → Python).

Phase 1.4.b du sprint refonte cockpit dual sol2 (29/04/2026). Migration
de `frontend/src/models/impactDecisionModel.js` (131 lignes) vers backend
Python pour respecter la règle d'or CLAUDE.md #1 : zero business logic
in frontend.

Le composant React `ImpactDecisionPanel` qui consommait ce modèle a été
décommissionné en Phase 0.3 (commit 59e27705). Le service Python expose
les 2 fonctions historiques pour les consommateurs ultérieurs (page
/cockpit/strategique Phase 2-3) via endpoint `/api/cockpit/impact_decision`.

Exports :
    compute_impact_kpis(kpis, billing_summary) → ImpactKpis
        Calcule les 3 KPIs Impact & Décision :
        - risque_conformite_eur : risque financier conformité (depuis kpis)
        - surcout_facture_eur : surcoût détecté billing (clamp >= 0)
        - opportunite_optim_eur : opportunité optimisation (1% facturé V1)

    compute_recommendation(impact, kpis) → Recommendation
        Détermine la recommandation prioritaire (rule-based V1) :
        max(risque, surcoût, opportunité) → thème de la reco.
        Si tout à 0 → recommandation "compléter les données".

Compatibilité : contrat de retour identique au modèle JS V30 pour
tolérance migration. La signature accepte des dicts neutres pour
compatibilité avec les KpiService + BillingService existants.
"""

from dataclasses import dataclass
from typing import Optional


# Heuristique V1 : opportunité optimisation = 1 % du montant facturé total.
# À remplacer Phase 2 par calcul rigoureux (CEE BAT-TH-* + référentiels).
OPTIM_RATE_V1 = 0.01


@dataclass(frozen=True)
class ImpactKpis:
    """3 KPIs Impact & Décision avec drapeaux de disponibilité."""

    risque_conformite_eur: float
    surcout_facture_eur: float
    opportunite_optim_eur: float
    risque_available: bool
    surcout_available: bool
    optim_available: bool

    def to_dict(self) -> dict:
        return {
            "risque_conformite_eur": self.risque_conformite_eur,
            "surcout_facture_eur": self.surcout_facture_eur,
            "opportunite_optim_eur": self.opportunite_optim_eur,
            "risque_available": self.risque_available,
            "surcout_available": self.surcout_available,
            "optim_available": self.optim_available,
        }


@dataclass(frozen=True)
class Recommendation:
    """Recommandation prioritaire avec CTA et bullets."""

    key: str  # 'no_data' | 'conformite' | 'facture' | 'optimisation'
    titre: str
    bullets: list[str]
    cta: str
    cta_path: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "titre": self.titre,
            "bullets": self.bullets,
            "cta": self.cta,
            "cta_path": self.cta_path,
        }


def _fmt_eur_explicit(value: float) -> str:
    """Format euro lisible avec fallback "non estimé" pour 0."""
    if not value:
        return "non estimé"
    return f"{round(value):,} €".replace(",", " ")


def compute_impact_kpis(kpis: Optional[dict] = None, billing_summary: Optional[dict] = None) -> ImpactKpis:
    """
    Calcule les 3 KPIs Impact & Décision déterministes.

    Args:
        kpis: dict KPI Cockpit avec clés {risque_total_eur, total, non_conformes, a_risque}
        billing_summary: résultat de get_billing_summary() ou {}

    Returns:
        ImpactKpis avec 3 valeurs + 3 drapeaux available.

    Notes:
        - risque_conformite vient directement du scope (kpis.risque_total_eur)
        - surcout_facture clampé >= 0 (anti-valeur négative)
        - opportunite_optim = 1% du facturé (heuristique V1, à remplacer Phase 2)
    """
    k = kpis or {}
    bs = billing_summary or {}

    # 1. Risque conformité — directement depuis le scope
    risque = float(k.get("risque_total_eur", k.get("risqueTotal", 0)) or 0)
    risque_available = (k.get("total", 0) or 0) > 0

    # 2. Surcoût facture — delta pertes billing (clamp >= 0)
    total_loss = float(bs.get("total_loss_eur", 0) or 0)
    surcout = max(0.0, total_loss)
    surcout_available = total_loss > 0 or (bs.get("total_invoices", 0) or 0) > 0

    # 3. Opportunité optimisation — 1% du facturé (heuristique V1)
    total_eur = float(bs.get("total_eur", 0) or 0)
    opportunite = round(total_eur * OPTIM_RATE_V1)
    optim_available = total_eur > 0

    return ImpactKpis(
        risque_conformite_eur=risque,
        surcout_facture_eur=surcout,
        opportunite_optim_eur=opportunite,
        risque_available=risque_available,
        surcout_available=surcout_available,
        optim_available=optim_available,
    )


def compute_recommendation(impact: Optional[ImpactKpis | dict] = None, kpis: Optional[dict] = None) -> Recommendation:
    """
    Détermine la recommandation prioritaire (rule-based V1).

    Règle:
        max(risque_conformite, surcout_facture, opportunite_optim) → thème.
        Si tout à 0 → recommandation par défaut "compléter les données".

    Args:
        impact: résultat de compute_impact_kpis() (ou dict équivalent)
        kpis: dict KPIs Cockpit avec {non_conformes, a_risque}

    Returns:
        Recommendation avec key/titre/bullets/cta/cta_path.
    """
    if isinstance(impact, ImpactKpis):
        i = impact.to_dict()
    else:
        i = impact or {}
    k = kpis or {}

    risque = float(i.get("risque_conformite_eur", 0) or 0)
    surcout = float(i.get("surcout_facture_eur", 0) or 0)
    opportunite = float(i.get("opportunite_optim_eur", 0) or 0)

    non_conformes = int(k.get("non_conformes", k.get("nonConformes", 0)) or 0)
    a_risque = int(k.get("a_risque", k.get("aRisque", 0)) or 0)

    max_val = max(risque, surcout, opportunite)

    # Cas tout à zéro — données manquantes
    if max_val == 0:
        return Recommendation(
            key="no_data",
            titre="Compléter les données pour activer les recommandations",
            bullets=[
                "Aucune donnée de risque, facture ou consommation détectée",
                "Importez votre patrimoine et vos factures",
                "Les recommandations apparaîtront automatiquement",
            ],
            cta="Importer le patrimoine",
            cta_path="/patrimoine",
        )

    # Risque conformité prioritaire
    if risque >= surcout and risque >= opportunite:
        sites_count = non_conformes + a_risque
        plural_s = "s" if sites_count > 1 else ""
        return Recommendation(
            key="conformite",
            titre="Priorité : réduire le risque conformité",
            bullets=[
                f"{sites_count} site{plural_s} non conforme{plural_s} ou à risque",
                f"Risque financier estimé : {_fmt_eur_explicit(risque)}",
                "Échéance Décret Tertiaire — actions correctives recommandées",
            ],
            cta="Voir les sites à risque",
            cta_path="/conformite",
        )

    # Surcoût facture prioritaire
    if surcout >= opportunite:
        return Recommendation(
            key="facture",
            titre="Priorité : corriger les anomalies facture",
            bullets=[
                f"Surcoût détecté : {_fmt_eur_explicit(surcout)}",
                "Anomalies identifiées par le moteur de facturation théorique",
                "Vérifiez les écarts prix, volumes et doublons",
            ],
            cta="Voir les anomalies",
            cta_path="/bill-intel",
        )

    # Opportunité optimisation prioritaire
    return Recommendation(
        key="optimisation",
        titre="Priorité : lancer l'optimisation énergétique",
        bullets=[
            f"Économie potentielle estimée : {_fmt_eur_explicit(opportunite)}",
            "Basé sur 1 % du montant facturé total (heuristique V1)",
            "Identifiez les sites énergivores et les surconsommations",
        ],
        cta="Voir le diagnostic conso",
        cta_path="/diagnostic-conso",
    )
