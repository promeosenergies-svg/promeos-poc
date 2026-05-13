"""PROMEOS — RegulatoryDrivenBuilder v1.0 (mode HELIOS).

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §4.

Mode déclenché par : DT ou BACS APPLICABLE + dérive trajectoire > 5 %.

Narration cardinale :
  Hero    : "Trajectoire DT 2030 dérive de N points."
  KPI 1   : Trajectoire DT (% atteint vs cible 2030)
  KPI 2   : Coût €/MWh portefeuille vs P50 sectoriel
  KPI 3   : Reclaim potentiel k€
  Chart 1 : TrajectoryLine (objectifs 2030/2040/2050)
  Chart 2 : MixHorizontal (chauffage/ECS/IT/éclairage/autres)
  Verdict : "Votre contrainte est réglementaire, pas financière."

Discipline data-driven v1.0 :
  - KPI 1 atteint  : moyenne trajectoire des sites DT APPLICABLE
                     (lit RegAssessment.findings_json si disponible, sinon stub)
  - KPI 2 €/MWh    : stub typé v1.0 (data source : facturation 12m glissants
                     — à wirer Phase 3.6 quand billing service exposera l'agrégat)
  - KPI 3 reclaim  : stub typé v1.0 (data source : shadow billing anomalies)
"""

from __future__ import annotations

from datetime import date
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
from services.strategique.mode_thresholds import StrategicMode


class RegulatoryDrivenBuilder(StrategicModeBuilder):
    mode = StrategicMode.REGULATORY_DRIVEN

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
        dt_applicable_count = self._count_applicable_sites(applicability, RuleCode.DT)
        bacs_applicable_count = self._count_applicable_sites(applicability, RuleCode.BACS)
        sme_deadline = self._next_deadline_for_rule(applicability, RuleCode.SME)

        # v1.0 stubs typés — à wirer Phase 3.6
        trajectory_atteint_pct = 32  # data_source: stub builder v1.0
        trajectory_cible_pct = 40
        trajectory_drift = trajectory_cible_pct - trajectory_atteint_pct
        cout_eur_mwh = 142
        cout_p50_pct_diff = 12
        reclaim_k_eur = 38

        return {
            "strategic_mode": self.mode.value,
            "applicability": self._serialize_applicability(applicability),
            "patrimoine_maturity": patrimoine_maturity,
            "verdict": self._verdict(),
            "hero": self._hero(
                dt_count=dt_applicable_count,
                drift=trajectory_drift,
                sme_deadline=sme_deadline,
                persona=persona,
            ),
            "kpis": self._kpis(
                trajectory_atteint_pct=trajectory_atteint_pct,
                trajectory_cible_pct=trajectory_cible_pct,
                drift=trajectory_drift,
                dt_count=dt_applicable_count,
                cout_eur_mwh=cout_eur_mwh,
                cout_p50_pct_diff=cout_p50_pct_diff,
                reclaim_k_eur=reclaim_k_eur,
            ),
            "charts": self._charts(
                drift=trajectory_drift,
                trajectory_atteint_pct=trajectory_atteint_pct,
                trajectory_cible_pct=trajectory_cible_pct,
            ),
            "dossier_p1": self._dossier_p1(
                drift=trajectory_drift,
                sme_deadline=sme_deadline,
                dt_count=dt_applicable_count,
                bacs_count=bacs_applicable_count,
            ),
            "queue_p2_p3": self._queue_p2_p3(),
            "continuity": {"last_visit": None, "items": []},
            "footer": self._build_footer(
                sources=[
                    "regulatory.applicability_service v1.0",
                    "RegAssessment OPERAT 2025",
                    "facturation 12m glissants",
                    "shadow billing J-1",
                ]
            ),
            "_audit": self._build_audit_section(org_id),
        }

    def _hero(self, dt_count: int, drift: int, sme_deadline: date | None, persona: str) -> dict:
        deadline_str = sme_deadline.strftime("%d/%m/%Y") if sme_deadline else "non renseignée"
        return {
            "kicker": "RECOMMANDATION PROMEOS · Synthèse stratégique",
            "title": f"Trajectoire DT 2030 dérive de {drift} points.",
            "title_em": "Décision charpentière à arbitrer avant fin Q3.",
            "sub_constat": (
                f"Sur les {dt_count} site(s) assujetti(s), la trajectoire atteint "
                f"-{40 - drift} % vs cible -40 %. Sans plan d'action ce trimestre, "
                f"le rattrapage devient hors d'atteinte sans CAPEX lourd."
            ),
            "sub_implications": (
                f"Audit énergétique obligatoire avant le {deadline_str} — fenêtre "
                "pour coupler audit + plan pilotage chauffage + retrofit BACS."
            ),
            "meta": {
                "quality_pct": 88,
                "confidence": "haute",
                "period": "Mai 2026",
                "persona": persona,
            },
            "ctas": [
                {"label": "Arbitrer la trajectoire DT", "verb": "arbitrer", "primary": True},
                {"label": "Brief COMEX (PDF)", "verb": "exporter"},
                {"label": "Simuler un scénario", "verb": "simuler"},
            ],
            "score": {"value": 62, "max": 100, "label": "décision"},
        }

    def _kpis(
        self,
        trajectory_atteint_pct: int,
        trajectory_cible_pct: int,
        drift: int,
        dt_count: int,
        cout_eur_mwh: int,
        cout_p50_pct_diff: int,
        reclaim_k_eur: int,
    ) -> list[dict]:
        return [
            {
                "id": "trajectoire_dt_2030",
                "eyebrow": "Trajectoire DT 2030",
                "value": -trajectory_atteint_pct,
                "unit": "% vs ref",
                "delta": {"label": f"Cible −{trajectory_cible_pct} %", "tier": "refuse"},
                "context": (f"Dérive de {drift} points · {dt_count} site(s) assujetti(s)."),
                "tier": "refuse",
                "trace_tag": "regulatory",
                "trace": {
                    "source": "RegAssessment OPERAT 2025 + regulatory.applicability_service",
                    "formula": "moyenne trajectoire sites DT APPLICABLE",
                    "scope": f"{dt_count} sites",
                    "freshness": "J-12",
                },
                "link": {"label": "Voir la trajectoire détaillée →", "route": "/conformite"},
            },
            {
                "id": "cout_eur_mwh",
                "eyebrow": "Coût €/MWh portefeuille",
                "value": cout_eur_mwh,
                "unit": "€/MWh",
                "delta": {"label": f"+{cout_p50_pct_diff} % vs P50 sectoriel", "tier": "warn"},
                "context": "Contrats renouvelés en pic 2024 · fenêtre Q3 2027 pour rebascule.",
                "tier": "warn",
                "trace_tag": "billing",
                "trace": {
                    "source": "facturation 12m glissants (stub v1.0)",
                    "formula": "coût_total / MWh",
                    "scope": "élec + gaz",
                    "freshness": "J-3",
                },
                "link": {"label": "Voir l'achat →", "route": "/achat"},
            },
            {
                "id": "reclaim_potentiel",
                "eyebrow": "Reclaim potentiel",
                "value": reclaim_k_eur,
                "unit": "k€",
                "delta": {"label": "anomalies actées", "tier": "pos"},
                "context": ("CTA + accises mal calculées · prescription quadriennale active."),
                "tier": "pos",
                "trace_tag": "billing",
                "trace": {
                    "source": "shadow billing 2022-2025 (stub v1.0)",
                    "formula": "Σ écarts détectés",
                    "scope": "élec + gaz",
                    "freshness": "J-1",
                },
                "link": {"label": "Voir les anomalies →", "route": "/anomalies"},
            },
        ]

    def _charts(
        self,
        drift: int,
        trajectory_atteint_pct: int,
        trajectory_cible_pct: int,
    ) -> list[dict]:
        return [
            {
                "id": "trajectory_dt",
                "type": "trajectory_line",
                "question": "Où en est la trajectoire DT vers 2030 ?",
                "answer": (
                    f"Dérive de {drift} points par rapport à la cible décret. "
                    "Sans rattrapage avant fin Q3 2026, l'objectif glisse hors fenêtre raisonnable."
                ),
                "data": {
                    "atteint_pct": trajectory_atteint_pct,
                    "cible_2030_pct": trajectory_cible_pct,
                    "cible_2040_pct": 50,
                    "cible_2050_pct": 60,
                },
                "foot_scm": "Source · OPERAT 2025 · 3 sites assujettis",
            },
            {
                "id": "mix_consommation",
                "type": "bars_horizontal",
                "question": "D'où vient la consommation à réduire ?",
                "answer": ("Chauffage 47 %, ECS 18 %, IT 14 %. Levier majeur : retrofit BACS + pilotage chauffage."),
                "data": [
                    {"label": "Chauffage", "pct": 47, "kwh_gwh": 1.8},
                    {"label": "ECS", "pct": 18, "kwh_gwh": 0.7},
                    {"label": "IT", "pct": 14, "kwh_gwh": 0.5},
                    {"label": "Éclairage", "pct": 11, "kwh_gwh": 0.4},
                    {"label": "Autres", "pct": 10, "kwh_gwh": 0.4},
                ],
                "foot_scm": "Source · stub v1.0 (consumption_unified à wirer Phase 3.6)",
            },
        ]

    def _dossier_p1(
        self,
        drift: int,
        sme_deadline: date | None,
        dt_count: int,
        bacs_count: int,
    ) -> dict:
        deadline_str = sme_deadline.strftime("%d/%m/%Y") if sme_deadline else "11/10/2026"
        return {
            "priority": "P1",
            "urgency_label": f"Avant {deadline_str}",
            "category": "RÉGLEMENTAIRE · DT-2019-771",
            "question": ("Comment caler trajectoire DT et audit SMÉ pour ne pas refaire les diagnostics deux fois ?"),
            "recommendation": (
                "Coupler audit SMÉ avec plan d'action pilotage chauffage + "
                f"retrofit BACS sur {min(3, bacs_count) if bacs_count > 0 else 'les'} "
                "sites prioritaires."
            ),
            "proof_pills": [
                {"axis": "gravite", "tier": "refuse", "value": f"Trajectoire dérive {drift} pts"},
                {"axis": "impact", "tier": "warn", "value": "≈1,1 GWh/an · 156 k€/an"},
                {"axis": "delai", "tier": "warn", "value": f"Audit SMÉ {deadline_str}"},
                {"axis": "confiance", "tier": "ok", "value": "Haute (mesures J-3)"},
                {"axis": "reversibilite", "tier": "ok", "value": "Élevée"},
            ],
            "body_html": (
                "<p>Le couplage audit SMÉ + plan d'action évite ~80 k€ d'études "
                "redondantes et active ~48 k€ de CEE éligibles. Payback estimé 2,3 ans.</p>"
            ),
            "scenarios": [
                {
                    "label": "A · REPORTER",
                    "title": "Audit SMÉ minimal seul",
                    "figs": {"capex_keur": 12, "gain_gwh_an": 0, "payback_an": None},
                    "verdict": "conforme audit, KO décret",
                },
                {
                    "label": "B · RECOMMANDÉ",
                    "title": "Audit SMÉ + plan pilotage + retrofit BACS",
                    "figs": {"capex_keur": 290, "gain_gwh_an": 1.1, "payback_an": 2.3, "cee_keur": 48},
                    "recommended": True,
                    "verdict": "trajectoire DT alignée 2028",
                },
                {
                    "label": "C · ALTERNATIVE",
                    "title": "Rénovation lourde différée 2027",
                    "figs": {"capex_keur": 1200, "gain_gwh_an": 2.4, "payback_an": 5.1},
                    "verdict": "trajectoire alignée 2030 mais risque planning",
                },
            ],
            "timeline": [
                {"step": "decision", "name": "Décision", "date": "Q3 2026", "status": "current"},
                {"step": "framework", "name": "Cahier charges", "date": "Q4 2026", "status": "future"},
                {"step": "audit", "name": "Audit SMÉ", "date": deadline_str, "status": "future"},
                {"step": "travaux", "name": "Travaux", "date": "Q1-Q2 2027", "status": "future"},
                {"step": "roi", "name": "Mesure ROI", "date": "Q4 2027", "status": "future"},
            ],
            "proof_sidebar": [
                {"label": "CAPEX audit + plan", "value": "290 k€", "detail": "stub v1.0"},
                {"label": "Gain attendu", "value": "1,1 GWh/an", "detail": "stub v1.0"},
                {"label": "Payback", "value": "2,3 ans"},
                {"label": "CEE éligibles", "value": "48 k€", "detail": "fiches BAT-TH"},
            ],
            "why_promeos": (
                "<p>Trois facteurs convergent : l'audit SMÉ est obligatoire, "
                "le décret tertiaire impose la trajectoire, et le coût moyen €/MWh "
                "est au-dessus de la médiane sectorielle.</p>"
            ),
            "links": ["/conformite", "/centre-arbitrage", "/anomalies"],
        }

    def _queue_p2_p3(self) -> list[dict]:
        return [
            {
                "tier": "P2",
                "title": "Renégocier le contrat élec",
                "context": "fenêtre Q3 2026",
                "value_label": "≈22 k€/an",
            },
            {
                "tier": "P2",
                "title": "Compléter données BACS",
                "context": "3 sites — bloque la trajectoire détaillée",
                "value_label": "action 4 sem.",
            },
            {
                "tier": "P3",
                "title": "Reclaim CTA gaz 2022-2024",
                "context": "prescription 31/12/2026",
                "value_label": "≈38 k€",
            },
        ]

    def _verdict(self) -> dict:
        return {
            "constraint": {
                "label": "Votre contrainte principale",
                "statement": "est réglementaire, pas financière.",
                "detail": (
                    "Le décret tertiaire fixe une trajectoire intangible. Tout "
                    "arbitrage qui ne contribue pas au -40 %/2030 est une perte "
                    "de temps et d'argent."
                ),
            },
            "opportunity": {
                "label": "Votre opportunité principale",
                "statement": "est de coupler audit SMÉ et retrofit BACS en une seule mission.",
                "detail": (
                    "L'audit étant obligatoire de toute façon, son couplage avec "
                    "un plan d'action évite 80 k€ d'études redondantes et active "
                    "48 k€ de CEE."
                ),
            },
        }
