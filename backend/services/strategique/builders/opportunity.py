"""PROMEOS — OpportunityDrivenBuilder v1.0 (Phase 3.6 Vague BB).

Référence : ADR-023 §4. Remplace le stub Phase 3.5 (NotImplementedError).

Mode déclenché par : APER APPLICABLE OU CEE non valorisés > 50 k€.

Narration cardinale :
  Hero    : "N opportunités totalisant X k€/an non activées."
  KPI 1   : Potentiel PV k€/an (ombrière APER)
  KPI 2   : CEE valorisables k€
  KPI 3   : Flex k€/an
  Chart 1 : OpportunityMap (matrice ROI × effort)
  Chart 2 : ROI bars (top leviers)
  Verdict : "Vous avez N opportunités totalisant X k€/an."

Discipline v1.0 : potentiel PV stub, CEE via compute_unvalued_cee_keur (AA).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from services.strategique.builders.base import (
    PERSONA_DG_COMEX,
    StrategicModeBuilder,
)
from services.strategique.computes import compute_unvalued_cee_keur
from services.strategique.mode_thresholds import StrategicMode


class OpportunityDrivenBuilder(StrategicModeBuilder):
    mode = StrategicMode.OPPORTUNITY_DRIVEN

    def build(
        self,
        db: Session,
        org_id: int,
        applicability: dict[RuleCode, list[RuleApplicability]],
        patrimoine_maturity: float,
        persona: str = PERSONA_DG_COMEX,
        period_type: str = "month",
        horizon_year: int = 2030,
    ) -> dict:
        cee_info = compute_unvalued_cee_keur(db, org_id)
        aper_sites = self._count_applicable_sites(applicability, RuleCode.APER)

        # Stubs économiques v1.0
        pv_potentiel_k_eur = 88
        flex_potentiel_k_eur = 32
        cee_k_eur = cee_info["k_eur"]
        opportunites_count = aper_sites + (1 if cee_k_eur > 0 else 0) + 1  # +1 flex

        total_k_eur = pv_potentiel_k_eur + cee_k_eur + flex_potentiel_k_eur

        return {
            "strategic_mode": self.mode.value,
            "applicability": self._serialize_applicability(applicability),
            "patrimoine_maturity": patrimoine_maturity,
            "verdict": self._verdict(count=opportunites_count, total=total_k_eur),
            "hero": self._hero(
                count=opportunites_count,
                total=total_k_eur,
                aper_sites=aper_sites,
                persona=persona,
            ),
            "kpis": self._kpis(
                pv=pv_potentiel_k_eur,
                cee=cee_k_eur,
                flex=flex_potentiel_k_eur,
            ),
            "charts": self._charts(
                pv=pv_potentiel_k_eur,
                cee=cee_k_eur,
                flex=flex_potentiel_k_eur,
            ),
            "dossier_p1": self._dossier_p1(
                pv=pv_potentiel_k_eur,
                aper_sites=aper_sites,
                total=total_k_eur,
            ),
            "queue_p2_p3": self._queue_p2_p3(),
            "continuity": {"last_visit": None, "items": []},
            "footer": self._build_footer(
                sources=[
                    "regulatory.applicability_service v1.0",
                    "compute_unvalued_cee_keur v1.0",
                    "potentiel PV (stub v1.0)",
                    "flex potential (stub v1.0)",
                ]
            ),
            "_audit": self._build_audit_section(org_id),
        }

    def _hero(self, count: int, total: int, aper_sites: int, persona: str) -> dict:
        return {
            "kicker": "RECOMMANDATION PROMEOS · Synthèse stratégique",
            "title": f"{count} opportunités totalisant {total} k€/an non activées.",
            "title_em": "Top 2 leviers à activer avant fin 2026.",
            "sub_constat": (
                f"{aper_sites} site(s) APER applicable + CEE non valorisés "
                f"+ potentiel flex. Total cumulé ≈ {total} k€/an récurrents."
            ),
            "sub_implications": (
                "Ombrière APER (échéance LARGE 01/07/2026) + CEE BAT-TH = 88 k€/an + capex coupable rapidement."
            ),
            "meta": {
                "quality_pct": 84,
                "confidence": "moyenne",
                "period": "Mai 2026",
                "persona": persona,
            },
            "ctas": [
                {"label": "Simuler les opportunités", "verb": "simuler", "primary": True},
                {"label": "Qualifier l'ombrière", "verb": "qualifier"},
                {"label": "Comparer 3 scénarios", "verb": "comparer"},
            ],
            "score": {"value": 78, "max": 100, "label": "décision"},
        }

    def _kpis(self, pv: int, cee: float, flex: int) -> list[dict]:
        return [
            {
                "id": "potentiel_pv",
                "eyebrow": "Potentiel PV",
                "value": pv,
                "unit": "k€/an",
                "delta": {"label": "ombrière APER éligible", "tier": "pos"},
                "context": "Production solaire estimée sur sites APER applicable.",
                "tier": "pos",
                "trace_tag": "advisory",
                "trace": {
                    "source": "potentiel PV (stub v1.0)",
                    "formula": "surface × rendement × prix vente moy",
                    "scope": "sites APER applicable",
                    "freshness": "J-7",
                },
                "link": {"label": "Voir APER →", "route": "/conformite#aper"},
            },
            {
                "id": "cee_valorisables",
                "eyebrow": "CEE valorisables",
                "value": int(cee),
                "unit": "k€",
                "delta": {"label": "non encore activés", "tier": "pos" if cee > 0 else "neutral"},
                "context": "CEE BAT-TH + BAT-EQ éligibles, fiches actives.",
                "tier": "pos" if cee > 0 else "neutral",
                "trace_tag": "regulatory",
                "trace": {
                    "source": "compute_unvalued_cee_keur v1.0",
                    "formula": "Σ valeur_estimee (statut != VALORISE)",
                    "scope": "CEEEligibility",
                    "freshness": "temps réel",
                },
                "link": {"label": "Voir les CEE →", "route": "/cee"},
            },
            {
                "id": "potentiel_flex",
                "eyebrow": "Potentiel flex",
                "value": flex,
                "unit": "k€/an",
                "delta": {"label": "NEBEF + effacement", "tier": "pos"},
                "context": "Effacement consommation pointe via agrégateur RTE.",
                "tier": "pos",
                "trace_tag": "advisory",
                "trace": {
                    "source": "potentiel flex (stub v1.0)",
                    "formula": "puissance_pilotable × prime NEBEF",
                    "scope": "sites > 100 kW",
                    "freshness": "J-7",
                },
                "link": {"label": "Voir flex →", "route": "/flex"},
            },
        ]

    def _charts(self, pv: int, cee: float, flex: int) -> list[dict]:
        return [
            {
                "id": "opportunity_map",
                "type": "opportunity_map",
                "question": "Quel ratio ROI / effort par opportunité ?",
                "answer": "Ombrière APER : effort moyen × ROI fort. CEE : effort faible × ROI moyen.",
                "data": [
                    {"name": "Ombrière APER", "roi_keur_an": pv, "effort_score": 6, "tier": "warn"},
                    {"name": "CEE BAT-TH", "roi_keur_an": int(cee), "effort_score": 3, "tier": "pos"},
                    {"name": "Flex NEBEF", "roi_keur_an": flex, "effort_score": 4, "tier": "neutral"},
                ],
                "foot_scm": "Source · opportunity matrix v1.0",
            },
            {
                "id": "roi_bars",
                "type": "pareto_levers",
                "question": "Top leviers triés par gain ?",
                "answer": "PV ombrière prime sur tous. Activation conjointe = 80 % du gain en 25 % d'effort.",
                "data": [
                    {"name": "Ombrière PV (APER)", "impact_keur_an": pv, "payback_an": 7.5},
                    {"name": "Flex NEBEF", "impact_keur_an": flex, "payback_an": 0.5},
                    {"name": "CEE BAT-TH", "impact_keur_an": int(cee), "payback_an": 0.1},
                ],
                "foot_scm": "Source · simulateur opportunités v1.0",
            },
        ]

    def _dossier_p1(self, pv: int, aper_sites: int, total: int) -> dict:
        return {
            "priority": "P1",
            "urgency_label": "Avant 01/07/2026 (APER LARGE)",
            "category": "STRATÉGIQUE · OPPORTUNITÉ",
            "question": ("Quelle opportunité activer en premier pour matérialiser rapidement de la valeur ?"),
            "recommendation": (
                f"Lancer la qualification ombrière APER sur {aper_sites} site(s) "
                f"applicable(s). Potentiel ≈ {pv} k€/an récurrents."
            ),
            "proof_pills": [
                {"axis": "gravite", "tier": "neutral", "value": "Opportunité (pas risque)"},
                {"axis": "impact", "tier": "ok", "value": f"≈{pv} k€/an PV + {total - pv} k€/an autres"},
                {"axis": "delai", "tier": "warn", "value": "APER LARGE 01/07/2026"},
                {"axis": "confiance", "tier": "neutral", "value": "Moyenne (étude requise)"},
                {"axis": "reversibilite", "tier": "neutral", "value": "Faible (CAPEX 18 ans)"},
            ],
            "body_html": (
                f"<p>{aper_sites} site(s) avec parking ≥ 1 500 m² éligible(s) "
                "ombrière APER. L'obligation réglementaire devient avantage "
                "économique si activée avant fin 2026.</p>"
            ),
            "scenarios": [
                {
                    "label": "A · MINIMAL",
                    "title": "Conformité APER seule (location toiture)",
                    "figs": {"capex_keur": 0, "gain_keur_an": 12, "payback_an": 0},
                    "verdict": "conforme mais valeur captée par tiers",
                },
                {
                    "label": "B · RECOMMANDÉ",
                    "title": "Ombrière propriétaire + autoconso",
                    "figs": {"capex_keur": 650, "gain_keur_an": pv, "payback_an": 7.5},
                    "recommended": True,
                },
                {
                    "label": "C · EXTENSIVE",
                    "title": "Ombrière + flex + CEE coordonné",
                    "figs": {"capex_keur": 720, "gain_keur_an": total, "payback_an": 5.7},
                    "verdict": "complexe opérationnellement",
                },
            ],
            "timeline": [
                {"step": "decision", "name": "Décision", "date": "Q3 2026", "status": "current"},
                {"step": "etude", "name": "Étude faisabilité", "date": "Q4 2026", "status": "future"},
                {"step": "permis", "name": "Permis + raccordement", "date": "Q1-Q2 2027", "status": "future"},
                {"step": "travaux", "name": "Travaux", "date": "Q3 2027", "status": "future"},
                {
                    "step": "mise_service",
                    "name": "Mise en service",
                    "date": "Avant 01/07/2026 (LARGE)",
                    "status": "future",
                },
            ],
            "proof_sidebar": [
                {"label": "CAPEX scénario B", "value": "650 k€"},
                {"label": "Gain attendu", "value": f"{pv} k€/an"},
                {"label": "Payback", "value": "7,5 ans"},
                {"label": "CEE éligibles", "value": "≈20 k€"},
            ],
            "why_promeos": (
                "<p>L'obligation APER devient une opportunité économique si "
                "et seulement si la décision est prise avant T-12 mois "
                "(délai permis + raccordement).</p>"
            ),
            "links": ["/conformite", "/flex", "/cee"],
        }

    def _queue_p2_p3(self) -> list[dict]:
        return [
            {
                "tier": "P2",
                "title": "Qualifier CEE BAT-TH éclairage",
                "context": "fiche active, capex faible",
                "value_label": "valoriser",
            },
            {
                "tier": "P2",
                "title": "Pré-qualifier flex NEBEF",
                "context": "agrégateur partenaire à sélectionner",
                "value_label": "qualifier",
            },
            {
                "tier": "P3",
                "title": "Évaluer PPA tiers ombrière",
                "context": "alternative location toiture",
                "value_label": "12 k€/an",
            },
        ]

    def _verdict(self, count: int, total: int) -> dict:
        return {
            "constraint": {
                "label": "Votre contrainte principale",
                "statement": "est de prioriser sans disperser.",
                "detail": (
                    f"{count} opportunités identifiées totalisant {total} k€/an. "
                    "L'enjeu n'est pas le potentiel mais la capacité à activer "
                    "1-2 leviers à fond avant fin 2026."
                ),
            },
            "opportunity": {
                "label": "Votre opportunité principale",
                "statement": "est l'ombrière APER, obligation devenue rentable.",
                "detail": (
                    "Décret APER + tarifs vente + autoconso transforment l'obligation "
                    "en levier économique > 80 k€/an récurrents."
                ),
            },
        }
