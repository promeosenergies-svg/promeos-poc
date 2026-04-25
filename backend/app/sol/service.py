"""
PROMEOS Sol — ProposalService.

Compose un plan d'action prescriptif (3 actions chiffrées max) à partir des
sources métiers déjà disponibles :
  - ActionPlanItem (issues actionnables avec estimated_impact_eur déjà calculé)
  - Site (statut conformité, risque financier)
  - KpiService (agrégats canoniques pour validation cohérence)

ZÉRO calcul métier inventé ici : on lit ce que les moteurs amont ont produit
(action_plan_engine, compliance_engine, kpi_service) et on l'organise pour
la consommation par le SolHero front.
"""

from __future__ import annotations
from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.action_plan_item import ActionPlanItem
from models.site import Site, StatutConformite
from models.organisation import Organisation
from models.entite_juridique import EntiteJuridique
from models.portefeuille import Portefeuille

from .schemas import (
    ConfidenceT,
    DelayT,
    ImpactKindT,
    PeerComparison,
    SeverityT,
    SolAction,
    SolProposal,
    SourceModuleT,
)


# Benchmark tarifs pairs B2B 2026 par archétype NAF (€/kWh moyen TTC C4/C5).
# Source : OID/CEREN agrégats publics + observatoire CRE.
PEER_AVG_PRICE_EUR_KWH = {
    'bureau': 0.168,
    'bureaux': 0.168,
    'tertiaire': 0.168,
    'commerce': 0.182,
    'retail': 0.182,
    'hotel': 0.176,
    'restaurant': 0.195,
    'ecole': 0.156,
    'scolaire': 0.156,
    'sante': 0.172,
    'industrie': 0.142,
    'industrial': 0.142,
    'logistique': 0.158,
    'entrepot': 0.158,
}
PEER_AVG_PRICE_DEFAULT = 0.175

ARCHETYPE_LABELS = {
    'bureau': 'Bureau tertiaire',
    'bureaux': 'Bureau tertiaire',
    'tertiaire': 'Tertiaire général',
    'commerce': 'Commerce',
    'retail': 'Retail/Commerce',
    'hotel': 'Hôtellerie',
    'restaurant': 'Restauration',
    'ecole': 'Établissement scolaire',
    'scolaire': 'Établissement scolaire',
    'sante': 'Santé',
    'industrie': 'Industrie',
    'industrial': 'Industrie',
    'logistique': 'Logistique',
    'entrepot': 'Entrepôt logistique',
}


# ────────────────────────────────────────────────────────────────────────────
# Mappings priorités → schéma Sol

_PRIORITY_TO_SEVERITY: dict[str, SeverityT] = {
    "critical": "critical",
    "high": "high",
    "medium": "warn",
    "low": "info",
}

_DOMAIN_TO_SOURCE_MODULE: dict[str, SourceModuleT] = {
    "compliance": "conformite",
    "conformite": "conformite",
    "billing": "billing",
    "facturation": "billing",
    "purchase": "achat-energie",
    "achat": "achat-energie",
    "patrimoine": "patrimoine",
    "flex": "flex",
    "actions": "actions",
}

_DOMAIN_TO_PATH: dict[str, str] = {
    "compliance": "/conformite",
    "conformite": "/conformite",
    "billing": "/bill-intel",
    "facturation": "/bill-intel",
    "purchase": "/achat-energie",
    "achat": "/achat-energie",
    "patrimoine": "/patrimoine",
    "flex": "/pilotage",
    "actions": "/actions",
}

_DOMAIN_TO_IMPACT_KIND: dict[str, ImpactKindT] = {
    "compliance": "compliance_unlock",
    "conformite": "compliance_unlock",
    "billing": "saving",
    "facturation": "saving",
    "purchase": "gain",
    "achat": "gain",
    "patrimoine": "saving",
    "flex": "gain",
    "actions": "saving",
}

_SEVERITY_TO_DELAY: dict[SeverityT, DelayT] = {
    "critical": "aujourd'hui",
    "high": "cette semaine",
    "warn": "ce mois",
    "info": "ce trimestre",
}

_SEVERITY_RANK: dict[SeverityT, int] = {
    "critical": 0,
    "high": 1,
    "warn": 2,
    "info": 3,
}


# ────────────────────────────────────────────────────────────────────────────
# Service


class ProposalService:
    """Compose un SolProposal pour un scope donné (org_id, optional site_ids)."""

    MAX_ACTIONS = 3

    def __init__(self, db: Session):
        self.db = db

    # ── public API ────────────────────────────────────────────────────────

    def build_proposal(
        self,
        org_id: int,
        site_ids: Optional[Iterable[int]] = None,
    ) -> SolProposal:
        """Compose la proposition agentique pour le scope donné.

        Stratégie :
            1. Charger l'organisation pour le scope_label
            2. Récupérer les sites scopés (org_id + filter optionnel site_ids)
            3. Charger les ActionPlanItem ouverts sur ces sites
            4. Trier sévérité × impact descendant, garder TOP 3
            5. Mapper en SolAction avec chiffrage existant
            6. Composer headline + sources distinctes
        """

        org = self.db.query(Organisation).filter(Organisation.id == org_id).first()
        org_name = org.nom if org else None

        # Hiérarchie PROMEOS : Site -> Portefeuille -> EntiteJuridique -> Organisation
        site_query = (
            self.db.query(Site)
            .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(
                EntiteJuridique.organisation_id == org_id,
                Site.deleted_at.is_(None),
            )
        )
        if site_ids:
            site_ids_list = list(site_ids)
            if site_ids_list:
                site_query = site_query.filter(Site.id.in_(site_ids_list))
        sites = site_query.all()
        scoped_site_ids = [s.id for s in sites]

        scope_label = self._build_scope_label(org_name, len(sites), site_ids)

        actions = self._build_action_list(scoped_site_ids, sites)

        total_impact = sum(a.impact_eur_per_year for a in actions)
        sources = sorted({a.source_module for a in actions})
        headline_severity = (
            actions[0].severity if actions else "info"
        )
        headline = self._build_headline(actions, total_impact, len(sites))

        return SolProposal(
            generated_at=datetime.utcnow(),
            org_id=org_id,
            org_name=org_name,
            scope_label=scope_label,
            headline=headline,
            headline_severity=headline_severity,
            actions=actions,
            total_impact_eur_per_year=total_impact,
            sources=list(sources),
        )

    # ── internal ──────────────────────────────────────────────────────────

    def _build_action_list(
        self, scoped_site_ids: List[int], sites: List[Site]
    ) -> List[SolAction]:
        """Top 3 actions issues d'ActionPlanItem + fallback conformité sites."""

        actions: List[SolAction] = []

        # Étape 1 : ActionPlanItem ouverts sur le scope
        if scoped_site_ids:
            api_items = (
                self.db.query(ActionPlanItem)
                .filter(
                    ActionPlanItem.site_id.in_(scoped_site_ids),
                    ActionPlanItem.status.in_(["open", "in_progress"]),
                )
                .all()
            )
            actions.extend(self._map_action_items(api_items))

        # Étape 2 : Fallback / complément depuis Site.statut_decret_tertiaire
        # (utile pour démo sans ActionPlanItem persistés)
        if len(actions) < self.MAX_ACTIONS:
            actions.extend(self._build_compliance_fallback_actions(sites, exclude=actions))

        # Étape 3 : Billing anomalies (cumul estimated_loss_eur sur insights ouverts)
        if len(actions) < self.MAX_ACTIONS and scoped_site_ids:
            billing_action = self._build_billing_fallback_action(scoped_site_ids)
            if billing_action:
                actions.append(billing_action)

        # Étape 4 : Top recommendation (KB rules / IAR / shadow billing) — gain pur
        if len(actions) < self.MAX_ACTIONS and scoped_site_ids:
            reco_action = self._build_recommendation_fallback_action(scoped_site_ids)
            if reco_action:
                actions.append(reco_action)

        # Tri + cap
        actions.sort(
            key=lambda a: (_SEVERITY_RANK.get(a.severity, 9), -a.impact_eur_per_year)
        )
        return actions[: self.MAX_ACTIONS]

    def _map_action_items(self, items: List[ActionPlanItem]) -> List[SolAction]:
        out: List[SolAction] = []
        for it in items:
            severity = _PRIORITY_TO_SEVERITY.get(it.priority or "medium", "warn")
            domain_key = (it.domain or "").lower()
            source_module = _DOMAIN_TO_SOURCE_MODULE.get(domain_key, "actions")
            path = _DOMAIN_TO_PATH.get(domain_key, "/actions")
            impact_kind = _DOMAIN_TO_IMPACT_KIND.get(domain_key, "saving")
            impact_eur = int(round(it.estimated_impact_eur or 0))
            confidence: ConfidenceT = "high" if it.estimated_impact_eur else "medium"
            out.append(
                SolAction(
                    id=f"api-{it.id}",
                    title=(it.recommended_action or it.issue_label or "Action")[:80],
                    description=it.issue_label or "Action prioritaire",
                    severity=severity,
                    impact_eur_per_year=impact_eur,
                    impact_kind=impact_kind,
                    roi_months=None,
                    delay=_SEVERITY_TO_DELAY[severity],
                    source_module=source_module,
                    action_path=path,
                    confidence=confidence,
                )
            )
        return out

    def _build_compliance_fallback_actions(
        self, sites: List[Site], exclude: List[SolAction]
    ) -> List[SolAction]:
        """Construit des actions depuis Site.statut_decret_tertiaire si pas d'API items."""

        excluded_ids = {a.id for a in exclude}
        out: List[SolAction] = []

        non_conformes = [
            s for s in sites if s.statut_decret_tertiaire == StatutConformite.NON_CONFORME
        ]
        a_risque = [
            s for s in sites if s.statut_decret_tertiaire == StatutConformite.A_RISQUE
        ]

        if non_conformes:
            risque = sum(int(s.risque_financier_euro or 0) for s in non_conformes)
            n = len(non_conformes)
            site_id = "fallback-non-conformes"
            if site_id not in excluded_ids:
                out.append(
                    SolAction(
                        id=site_id,
                        title=f"Mettre en conformité {n} site{'s' if n > 1 else ''} Décret tertiaire",
                        description=(
                            f"{n} site{'s' if n > 1 else ''} non conforme{'s' if n > 1 else ''} sur le périmètre. "
                            f"Risque financier cumulé estimé à {risque:,} € si non régularisé.".replace(",", " ")
                        ),
                        severity="critical",
                        impact_eur_per_year=risque,
                        impact_kind="risk_avoided",
                        roi_months=None,
                        delay="aujourd'hui",
                        source_module="conformite",
                        action_path="/conformite",
                        confidence="high",
                    )
                )

        if a_risque:
            risque = sum(int(s.risque_financier_euro or 0) for s in a_risque)
            n = len(a_risque)
            site_id = "fallback-a-risque"
            if site_id not in excluded_ids:
                out.append(
                    SolAction(
                        id=site_id,
                        title=f"Sécuriser {n} site{'s' if n > 1 else ''} à risque DT",
                        description=(
                            f"{n} site{'s' if n > 1 else ''} à risque sur la trajectoire 2030. "
                            f"Plan d'action recommandé sous 3 mois pour éviter la bascule en non-conforme."
                        ),
                        severity="high",
                        impact_eur_per_year=risque,
                        impact_kind="risk_avoided",
                        roi_months=None,
                        delay="cette semaine",
                        source_module="conformite",
                        action_path="/conformite",
                        confidence="medium",
                    )
                )

        return out

    def _build_billing_fallback_action(
        self, scoped_site_ids: List[int]
    ) -> Optional[SolAction]:
        """Construit une action billing depuis billing_insights ouverts."""

        if not scoped_site_ids:
            return None
        site_ids_str = ",".join(str(i) for i in scoped_site_ids)
        # Somme défensive — insights ouverts (status NEW/OPEN/PENDING) sur scope
        row = self.db.execute(
            text(
                f"""
                SELECT COUNT(*) AS n,
                       COALESCE(SUM(estimated_loss_eur), 0) AS total_loss
                FROM billing_insights
                WHERE site_id IN ({site_ids_str})
                  AND insight_status IN ('new', 'pending', 'open', 'NEW', 'OPEN', 'PENDING')
                """
            )
        ).fetchone()
        if not row or not row.n or row.total_loss <= 0:
            return None
        n = int(row.n)
        loss = int(round(row.total_loss))
        return SolAction(
            id="fallback-billing-anomalies",
            title=f"Lever {n} anomalie{'s' if n > 1 else ''} facture détectée{'s' if n > 1 else ''}",
            description=(
                f"Le moteur shadow billing a détecté {n} anomalie{'s' if n > 1 else ''} "
                f"sur vos factures fournisseur. Réclamation potentielle : {loss:,} €.".replace(",", " ")
            ),
            severity="high" if loss > 10000 else "warn",
            impact_eur_per_year=loss,
            impact_kind="saving",
            roi_months=1,
            delay="cette semaine",
            source_module="billing",
            action_path="/bill-intel",
            confidence="high",
        )

    def _build_recommendation_fallback_action(
        self, scoped_site_ids: List[int]
    ) -> Optional[SolAction]:
        """Construit une action depuis la top recommendation par impact_score.

        Si estimated_savings_eur_year est NULL (cas seed démo HELIOS), on
        valorise estimated_savings_kwh_year au prix par défaut élec B2B
        (DEFAULT_PRICE_ELEC_EUR_KWH du config).
        """

        if not scoped_site_ids:
            return None
        try:
            from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH

            default_price = float(DEFAULT_PRICE_ELEC_EUR_KWH)
        except Exception:
            default_price = 0.18  # Prix B2B élec moyen 2026 (fallback ultime)

        site_ids_str = ",".join(str(i) for i in scoped_site_ids)
        row = self.db.execute(
            text(
                f"""
                SELECT r.id, r.title, r.description,
                       r.estimated_savings_eur_year,
                       r.estimated_savings_kwh_year,
                       r.impact_score, r.confidence_score
                FROM recommendation r
                JOIN meter m ON m.id = r.meter_id
                WHERE m.site_id IN ({site_ids_str})
                  AND (
                      r.estimated_savings_eur_year > 0
                      OR r.estimated_savings_kwh_year > 0
                  )
                ORDER BY COALESCE(r.estimated_savings_eur_year, r.estimated_savings_kwh_year * {default_price}) DESC
                LIMIT 1
                """
            )
        ).fetchone()
        if not row:
            return None
        gain_eur = (
            row.estimated_savings_eur_year
            if row.estimated_savings_eur_year and row.estimated_savings_eur_year > 0
            else (row.estimated_savings_kwh_year or 0) * default_price
        )
        gain = int(round(gain_eur))
        if gain <= 0:
            return None
        confidence: ConfidenceT = "high" if (row.confidence_score or 0) >= 7 else "medium"
        return SolAction(
            id=f"fallback-reco-{row.id}",
            title=(row.title or "Optimisation énergétique")[:80],
            description=(
                (row.description or row.title or "Recommandation prioritaire identifiée par Sol")
                + f" — gain estimé {gain:,} €/an.".replace(",", " ")
            ),
            severity="warn",
            impact_eur_per_year=gain,
            impact_kind="gain",
            roi_months=12,
            delay="ce mois",
            source_module="actions",
            action_path="/actions",
            confidence=confidence,
        )

    @staticmethod
    def _build_headline(
        actions: List[SolAction], total_impact: int, sites_count: int
    ) -> str:
        if not actions:
            return f"Patrimoine sous contrôle — Sol surveille en continu vos {sites_count} sites."

        n = len(actions)
        if total_impact > 0:
            return (
                f"Sol propose {n} action{'s' if n > 1 else ''} pour récupérer "
                f"{total_impact:,} € sur 12 mois.".replace(",", " ")
            )
        # Pas de chiffrage disponible — focus sur sévérité
        top = actions[0]
        return f"Sol propose {n} action{'s' if n > 1 else ''} prioritaire{'s' if n > 1 else ''} : {top.title.lower()}"

    # ── PeerComparison ────────────────────────────────────────────────────

    def build_peer_comparison(
        self,
        org_id: int,
        site_ids: Optional[Iterable[int]] = None,
    ) -> PeerComparison:
        """Compose une comparaison tarif moyen org vs pairs sectoriels.

        Méthode :
            1. Récupère sites scope + archétype dominant (par usage_type)
            2. Calcule prix moyen €/kWh = SUM(billing_total_eur) / SUM(billing_total_kwh)
            3. Compare au benchmark pair de l'archétype
            4. Génère une phrase d'interprétation actionnable
        """

        # Sites scopés (même chaîne que build_proposal)
        site_query = (
            self.db.query(Site)
            .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(
                EntiteJuridique.organisation_id == org_id,
                Site.deleted_at.is_(None),
            )
        )
        if site_ids:
            site_ids_list = list(site_ids)
            if site_ids_list:
                site_query = site_query.filter(Site.id.in_(site_ids_list))
        sites = site_query.all()

        # Archétype dominant (mode des usage_type des sites)
        usage_counts: dict[str, int] = {}
        for s in sites:
            ut = (getattr(s, 'usage_type', None) or '').lower().strip()
            if ut:
                usage_counts[ut] = usage_counts.get(ut, 0) + 1
        archetype = (
            max(usage_counts, key=usage_counts.get) if usage_counts else 'tertiaire'
        )
        archetype_label = ARCHETYPE_LABELS.get(archetype, 'Tertiaire général')
        peer_avg = PEER_AVG_PRICE_EUR_KWH.get(archetype, PEER_AVG_PRICE_DEFAULT)

        # Tarif moyen org via billing_summary agrégé
        # SUM(total_eur) / SUM(total_kwh) sur energy_invoices scope
        scoped_site_ids = [s.id for s in sites]
        my_avg_price: Optional[float] = None
        annual_overpayment: Optional[int] = None
        spread_pct: Optional[float] = None
        annual_kwh = 0

        if scoped_site_ids:
            site_ids_str = ','.join(str(i) for i in scoped_site_ids)
            row = self.db.execute(
                text(
                    f"""
                    SELECT
                        COALESCE(SUM(total_eur), 0) AS total_eur,
                        COALESCE(SUM(total_kwh), 0) AS total_kwh
                    FROM energy_invoices
                    WHERE site_id IN ({site_ids_str})
                      AND total_kwh > 0
                    """
                )
            ).fetchone()
            if row and row.total_kwh > 0:
                my_avg_price = row.total_eur / row.total_kwh
                annual_kwh = row.total_kwh
                spread_pct = ((my_avg_price - peer_avg) / peer_avg) * 100
                if spread_pct > 0:
                    annual_overpayment = int(round((my_avg_price - peer_avg) * row.total_kwh))

        # Phrase d'interprétation
        if my_avg_price is None:
            interpretation = (
                f"Pas assez de factures pour comparer — connectez vos factures "
                f"pour évaluer votre position vs pairs {archetype_label}."
            )
        elif spread_pct is None or abs(spread_pct) < 2:
            interpretation = (
                f"Vous payez {my_avg_price:.3f} €/kWh, dans la moyenne des pairs "
                f"{archetype_label} ({peer_avg:.3f} €/kWh) — contrat correctement calibré."
            )
        elif spread_pct > 0:
            interpretation = (
                f"Vous payez {my_avg_price:.3f} €/kWh contre {peer_avg:.3f} €/kWh "
                f"chez vos pairs {archetype_label} — surpaiement de "
                f"{spread_pct:.1f}% (≈ {annual_overpayment:,} €/an).".replace(',', ' ')
            )
        else:
            interpretation = (
                f"Vous payez {my_avg_price:.3f} €/kWh, "
                f"{abs(spread_pct):.1f}% MOINS que les pairs {archetype_label} "
                f"({peer_avg:.3f} €/kWh) — contrat performant."
            )

        confidence: ConfidenceT = (
            "high" if annual_kwh > 100000 else "medium" if annual_kwh > 10000 else "low"
        )

        return PeerComparison(
            org_id=org_id,
            archetype=archetype,
            archetype_label=archetype_label,
            my_avg_kwh_price_eur=my_avg_price,
            peer_avg_kwh_price_eur=peer_avg,
            spread_pct=spread_pct,
            annual_overpayment_eur=annual_overpayment,
            sites_count_in_scope=len(sites),
            confidence=confidence,
            peer_source="OID/CEREN benchmarks B2B 2026 + Observatoire CRE T4 2025",
            interpretation=interpretation,
        )

    @staticmethod
    def _build_scope_label(
        org_name: Optional[str], sites_count: int, site_ids: Optional[Iterable[int]]
    ) -> str:
        if site_ids and len(list(site_ids)) == 1:
            return f"site sélectionné"
        if org_name:
            return f"{org_name} — {sites_count} site{'s' if sites_count > 1 else ''}"
        return "votre patrimoine"
