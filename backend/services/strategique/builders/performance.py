"""PROMEOS — PerformanceDrivenBuilder v1.0 (mode MERIDIAN).

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §4.

Mode déclenché par défaut quand DT/BACS non applicables et intensité
> médiane NAF + 10 %.

Narration cardinale :
  Hero    : "Performance énergétique sous la médiane sectorielle."
  KPI 1   : Intensité kWh/m²
  KPI 2   : Coût €/MWh
  KPI 3   : Économies activables k€
  Chart 1 : BenchSites (intensité vs médiane NAF)
  Chart 2 : Pareto leviers (gain k€/an triés)
  Verdict : "Votre contrainte n'est pas réglementaire, elle est économique."

Discipline v1.0 :
  - Économies activables : stub typé v1.0 (data source : simulateur leviers
    à wirer Phase 3.6)
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from regulatory.applicability_types import RuleApplicability, RuleCode
from services.strategique.builders.base import (
    PERSONA_DG_COMEX,
    StrategicModeBuilder,
)
from services.strategique.computes import compute_bench_sites
from services.strategique.mode_thresholds import StrategicMode


class PerformanceDrivenBuilder(StrategicModeBuilder):
    mode = StrategicMode.PERFORMANCE_DRIVEN

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
        sme_deadline = self._next_deadline_for_rule(applicability, RuleCode.SME)

        # Phase 3.7 JJ : compute_bench_sites réel remplace les noms génériques
        # (Site phare/médian/meilleur élève) — fix violation AP-stratX7
        # signalée par architect-helios Phase 3.5.
        bench_rows = compute_bench_sites(db, org_id, top_n=3)
        if bench_rows:
            intensite_kwh_m2 = int(bench_rows[0]["value"])
            intensite_mediane_naf = int(bench_rows[0]["ref"])
        else:
            # Fallback v1.0 si aucun site exploitable
            intensite_kwh_m2 = 198
            intensite_mediane_naf = 162
        intensite_diff_pct = round((intensite_kwh_m2 - intensite_mediane_naf) / intensite_mediane_naf * 100)

        # Stubs économiques v1.0 — wire dédiés Phase 3.8
        cout_eur_mwh = 156
        cout_p50_diff_pct = 18
        economies_k_eur = 128

        return {
            "strategic_mode": self.mode.value,
            "applicability": self._serialize_applicability(applicability),
            "patrimoine_maturity": patrimoine_maturity,
            "verdict": self._verdict(),
            "hero": self._hero(
                intensite=intensite_kwh_m2,
                diff_pct=intensite_diff_pct,
                sme_deadline=sme_deadline,
                persona=persona,
            ),
            "kpis": self._kpis(
                intensite=intensite_kwh_m2,
                mediane=intensite_mediane_naf,
                diff_pct=intensite_diff_pct,
                cout=cout_eur_mwh,
                cout_p50_diff=cout_p50_diff_pct,
                economies=economies_k_eur,
            ),
            "charts": self._charts(
                intensite=intensite_kwh_m2,
                mediane=intensite_mediane_naf,
                bench_rows=bench_rows,
            ),
            "dossier_p1": self._dossier_p1(
                intensite=intensite_kwh_m2,
                diff_pct=intensite_diff_pct,
                sme_deadline=sme_deadline,
            ),
            "queue_p2_p3": self._queue_p2_p3(),
            "continuity": {"last_visit": None, "items": []},
            "footer": self._build_footer(
                sources=[
                    "regulatory.applicability_service v1.0",
                    "CDC Enedis J-1 (stub v1.0)",
                    "INSEE NAF benchmark (stub v1.0)",
                    "simulateur leviers (stub v1.0)",
                ]
            ),
            "_audit": self._build_audit_section(org_id),
        }

    def _hero(self, intensite: int, diff_pct: int, sme_deadline: date | None, persona: str) -> dict:
        deadline_str = sme_deadline.strftime("%d/%m/%Y") if sme_deadline else "11/10/2026"
        return {
            "kicker": "RECOMMANDATION PROMEOS · Synthèse stratégique",
            "title": "Performance énergétique sous la médiane sectorielle.",
            "title_em": "3 leviers d'économie à activer cette année.",
            "sub_constat": (
                f"Intensité {intensite} kWh/m² · {diff_pct} % au-dessus du benchmark "
                "NAF. Perte annualisée estimée 49 k€."
            ),
            "sub_implications": (
                f"Audit SMÉ obligatoire {deadline_str} — convertir cette obligation en plan d'action chiffré."
            ),
            "meta": {
                "quality_pct": 88,
                "confidence": "haute",
                "period": "Mai 2026",
                "persona": persona,
            },
            "ctas": [
                {"label": "Arbitrer les leviers", "verb": "arbitrer", "primary": True},
                {"label": "Note COMEX (PDF)", "verb": "exporter"},
                {"label": "Comparer 3 scénarios", "verb": "comparer"},
            ],
            "score": {"value": 76, "max": 100, "label": "décision"},
        }

    def _kpis(
        self,
        intensite: int,
        mediane: int,
        diff_pct: int,
        cout: int,
        cout_p50_diff: int,
        economies: int,
    ) -> list[dict]:
        return [
            {
                "id": "intensite_kwh_m2",
                "eyebrow": "Intensité énergétique",
                "value": intensite,
                "unit": "kWh_EF/m²",
                "delta": {"label": f"+{diff_pct} % vs médiane NAF", "tier": "warn"},
                "context": "Site phare tire l'intensité groupe à la hausse.",
                "tier": "warn",
                "trace_tag": "measure",
                "trace": {
                    "source": "CDC 30 min Enedis (stub v1.0)",
                    "formula": "MWh / SDP_m²",
                    "scope": "sites assujettis OPERAT",
                    "freshness": "J-1",
                },
                "link": {"label": "Voir la conso →", "route": "/consommations"},
            },
            {
                "id": "cout_eur_mwh",
                "eyebrow": "Coût élec",
                "value": cout,
                "unit": "€/MWh",
                "delta": {"label": f"+{cout_p50_diff} % vs P50 secteur", "tier": "warn"},
                "context": "Contrat fixe 2024-2027 conclu en pic · fenêtre arbitrage Q3 2026.",
                "tier": "warn",
                "trace_tag": "billing",
                "trace": {
                    "source": "facturation 12m glissants (stub v1.0)",
                    "formula": "coût_total / MWh",
                    "scope": "élec",
                    "freshness": "J-3",
                },
                "link": {"label": "Voir l'achat →", "route": "/achat-energie"},
            },
            {
                "id": "economies_activables",
                "eyebrow": "Économies activables",
                "value": economies,
                "unit": "k€/an",
                "delta": {"label": "3 leviers chiffrés", "tier": "pos"},
                "context": "Audit + pilotage + renégociation = payback moyen 1,7 an.",
                "tier": "pos",
                "trace_tag": "advisory",
                "trace": {
                    "source": "simulateur leviers (stub v1.0)",
                    "formula": "Σ ROI scénarios",
                    "scope": "sites assujettis",
                    "freshness": "J-2",
                },
                "link": {"label": "Voir les leviers →", "route": "/anomalies"},
            },
        ]

    def _charts(self, intensite: int, mediane: int, bench_rows: list[dict] | None = None) -> list[dict]:
        # Phase 3.7 JJ : bench_rows réel via compute_bench_sites (worst+median+best
        # avec vrais noms de sites). Fallback labels génériques si aucun site
        # exploitable (test source-guard G3 reste vert pour ce cas dégradé).
        if bench_rows:
            chart_data = [
                {
                    "site": row["site"],
                    "value": row["value"],
                    "ref": row["ref"],
                    "delta_pct": row["delta_pct"],
                    "tier": row["tier"],
                }
                for row in bench_rows
            ]
            answer_text = (
                f"{bench_rows[0]['site']} +{bench_rows[0]['delta_pct']} % au-dessus médiane · "
                f"{bench_rows[-1]['site']} {bench_rows[-1]['delta_pct']:+} % meilleur élève."
            )
            foot_scm = "Source · compute_bench_sites v1.0 (intensity_kwh_m2_tertiaire SoT)"
        else:
            chart_data = [
                {"site": "Site phare", "value": intensite, "ref": mediane, "delta_pct": 22, "tier": "warn"},
                {"site": "Site médian", "value": 168, "ref": mediane, "delta_pct": 4, "tier": "neutral"},
                {"site": "Site meilleur élève", "value": 133, "ref": mediane, "delta_pct": -18, "tier": "pos"},
            ]
            answer_text = "Aucune donnée bench disponible — labels génériques (compléter patrimoine)."
            foot_scm = "Source · fallback labels v1.0 (aucun site avec intensity)"
        return [
            {
                "id": "bench_sites_intensity",
                "type": "bench_sites",
                "question": "Quels sites tirent la performance vers le bas ?",
                "answer": answer_text,
                "data": chart_data,
                "foot_scm": foot_scm,
            },
            {
                "id": "pareto_leviers",
                "type": "pareto_levers",
                "question": "Quels leviers offrent le meilleur ROI ?",
                "answer": ("Pilotage CTA + renégociation = 80 % du gain potentiel pour 25 % du CAPEX."),
                "data": [
                    {"name": "Pilotage CTA Toulouse", "impact_keur_an": 52, "payback_an": 1.2},
                    {"name": "Renégociation contrat élec", "impact_keur_an": 42, "payback_an": 0.3},
                    {"name": "Audit SMÉ (obligatoire)", "impact_keur_an": 22, "payback_an": 1.1},
                    {"name": "LED + détection", "impact_keur_an": 12, "payback_an": 2.4},
                ],
                "foot_scm": "Source · simulateur leviers (stub v1.0)",
            },
        ]

    def _dossier_p1(self, intensite: int, diff_pct: int, sme_deadline: date | None) -> dict:
        deadline_str = sme_deadline.strftime("%d/%m/%Y") if sme_deadline else "11/10/2026"
        return {
            "priority": "P1",
            "urgency_label": "T+1 trimestre",
            "category": "FINANCIER · ARBITRAGE PERFORMANCE",
            "question": "Comment ramener le site phare au niveau du meilleur élève ?",
            "recommendation": (
                "Lancer un audit SMÉ sur le site phare + plan de pilotage CTA, "
                "finançable sur 12 mois. Économie attendue ≈ 49 k€/an, payback 1,4 an."
            ),
            "proof_pills": [
                {"axis": "gravite", "tier": "warn", "value": "Perte récurrente"},
                {"axis": "impact", "tier": "warn", "value": "320 MWh/an · 49 k€/an"},
                {"axis": "delai", "tier": "warn", "value": f"Audit SMÉ {deadline_str}"},
                {"axis": "confiance", "tier": "ok", "value": "Haute"},
                {"axis": "reversibilite", "tier": "ok", "value": "Élevée"},
            ],
            "body_html": (
                f"<p>Le site phare consomme {intensite} kWh/m² · +{diff_pct} % au-dessus "
                "de la médiane NAF. L'écart est financier (≈49 k€/an récurrents), "
                "non réglementaire.</p>"
            ),
            "scenarios": [
                {
                    "label": "A · REPORTER",
                    "title": "Audit SMÉ minimal seul",
                    "figs": {"capex_keur": 12, "gain_keur_an": 22, "payback_an": 0.6},
                },
                {
                    "label": "B · RECOMMANDÉ",
                    "title": "Audit SMÉ + plan pilotage CTA",
                    "figs": {"capex_keur": 68, "gain_keur_an": 49, "payback_an": 1.4, "cee_keur": 18},
                    "recommended": True,
                },
                {
                    "label": "C · ALTERNATIVE",
                    "title": "Rénovation lourde différée",
                    "figs": {"capex_keur": 480, "gain_keur_an": 78, "payback_an": 6.2},
                },
            ],
            "timeline": [
                {"step": "decision", "name": "Décision", "date": "Q3 2026", "status": "current"},
                {"step": "audit", "name": "Audit SMÉ", "date": deadline_str, "status": "future"},
                {"step": "pilotage", "name": "Plan pilotage", "date": "Q4 2026", "status": "future"},
                {"step": "roi", "name": "Mesure ROI", "date": "Q2 2027", "status": "future"},
            ],
            "proof_sidebar": [
                {"label": "CAPEX scénario B", "value": "68 k€", "detail": "valeur indicative v1.0"},
                {"label": "Gain attendu", "value": "49 k€/an", "detail": "valeur indicative v1.0"},
                {"label": "Payback", "value": "1,4 an"},
                {"label": "CEE éligibles", "value": "18 k€"},
            ],
            "why_promeos": (
                "<p>L'audit SMÉ étant déjà obligatoire, son couplage avec "
                "un plan d'action sécurise 49 k€/an et active 18 k€ de CEE.</p>"
            ),
            "links": ["/consommations", "/achat-energie", "/anomalies"],
        }

    def _queue_p2_p3(self) -> list[dict]:
        return [
            {
                "tier": "P2",
                "title": "Renégociation contrat élec",
                "context": "fenêtre Q3 2026",
                "value_label": "≈42 k€/an",
            },
            {
                "tier": "P2",
                "title": "Compléter données APER",
                "context": "1 site — bloque l'évaluation EnR",
                "value_label": "action 2 sem.",
            },
            {
                "tier": "P3",
                "title": "LED + détection 3 sites",
                "context": "candidats CEE BAT-EQ",
                "value_label": "≈12 k€/an",
            },
        ]

    def _verdict(self) -> dict:
        return {
            "constraint": {
                "label": "Votre contrainte principale",
                "statement": "n'est pas réglementaire, elle est économique.",
                "detail": (
                    "Aucune trajectoire DT ni BACS à tenir. Le levier majeur est "
                    "l'écart de performance vs benchmark NAF, soit ≈49 k€/an récurrents."
                ),
            },
            "opportunity": {
                "label": "Votre opportunité principale",
                "statement": "est l'audit SMÉ couplé au pilotage, payback 1,4 an.",
                "detail": (
                    "L'audit étant déjà obligatoire, son couplage avec un plan "
                    "d'action sécurise 49 k€/an et active 18 k€ de CEE."
                ),
            },
        }
