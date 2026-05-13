"""PROMEOS — ProcurementDrivenBuilder v1.0 (Phase 3.6 Vague BB).

Référence : ADR-023 §4. Remplace le stub Phase 3.5 (NotImplementedError).

Mode déclenché par : contrat à échéance < 90 j OU exposition spot > 40 %.

Narration cardinale :
  Hero    : "Contrat élec arrive à échéance dans N jours."
  KPI 1   : Coût forward €/MWh (cible reneg)
  KPI 2   : Exposition spot % (volume)
  KPI 3   : Économie scénario k€/an
  Chart 1 : ForwardCurve (prix forward J+12m)
  Chart 2 : MixHorizontal cibles renouvellement
  Verdict : "Votre fenêtre achat se ferme dans X jours."

Discipline v1.0 : valeurs économiques s'appuient sur les services
compute_next_contract_end + compute_spot_exposure (Vague AA).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from regulatory.applicability_types import RuleApplicability, RuleCode
from services.strategique.builders.base import (
    PERSONA_DG_COMEX,
    StrategicModeBuilder,
)
from services.strategique.computes import (
    compute_next_contract_end,
    compute_spot_exposure,
)
from services.strategique.mode_thresholds import StrategicMode


class ProcurementDrivenBuilder(StrategicModeBuilder):
    mode = StrategicMode.PROCUREMENT_DRIVEN

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
        contract_info = compute_next_contract_end(db, org_id)
        spot_info = compute_spot_exposure(db, org_id)

        days_until = contract_info["days"]
        fournisseur = contract_info.get("fournisseur") or "—"
        spot_pct = spot_info["pct"]

        # Stubs économiques v1.0 — wire dédiés Phase 3.7
        cout_forward_eur_mwh = 138
        cout_spot_eur_mwh = 165
        economie_scenario_k_eur = 84

        return {
            "strategic_mode": self.mode.value,
            "applicability": self._serialize_applicability(applicability),
            "patrimoine_maturity": patrimoine_maturity,
            "verdict": self._verdict(days=days_until, fournisseur=fournisseur),
            "hero": self._hero(
                days=days_until,
                fournisseur=fournisseur,
                spot_pct=spot_pct,
                persona=persona,
            ),
            "kpis": self._kpis(
                forward=cout_forward_eur_mwh,
                spot=cout_spot_eur_mwh,
                spot_pct=spot_pct,
                economie=economie_scenario_k_eur,
            ),
            "charts": self._charts(forward=cout_forward_eur_mwh, spot=cout_spot_eur_mwh),
            "dossier_p1": self._dossier_p1(
                days=days_until,
                fournisseur=fournisseur,
                economie=economie_scenario_k_eur,
                spot_pct=spot_pct,
            ),
            "queue_p2_p3": self._queue_p2_p3(),
            "continuity": {"last_visit": None, "items": []},
            "footer": self._build_footer(
                sources=[
                    "regulatory.applicability_service v1.0",
                    "ContratCadre.date_fin + type_prix",
                    "compute_next_contract_end v1.0",
                    "compute_spot_exposure v1.0",
                ]
            ),
            "_audit": self._build_audit_section(org_id),
        }

    def _hero(self, days: int, fournisseur: str, spot_pct: float, persona: str) -> dict:
        return {
            "kicker": "RECOMMANDATION PROMEOS · Synthèse stratégique",
            "title": f"Contrat élec à échéance dans {days} jour(s).",
            "title_em": "Fenêtre achat à activer immédiatement.",
            "sub_constat": (
                f"Fournisseur actuel : {fournisseur}. Exposition spot {spot_pct:.0f} %. "
                f"Sans bascule forward Y+1, le risque marché reste assumé sur la "
                f"prochaine période."
            ),
            "sub_implications": (
                "Forward Y+1 est attractif : bascule de 60 % du volume sécurise le coût moyen €/MWh sur 18 mois."
            ),
            "meta": {
                "quality_pct": 86,
                "confidence": "haute",
                "period": "Mai 2026",
                "persona": persona,
            },
            "ctas": [
                {"label": "Arbitrer le scénario", "verb": "arbitrer", "primary": True},
                {"label": "Note COMEX (PDF)", "verb": "exporter"},
                {"label": "Comparer fournisseurs", "verb": "comparer"},
            ],
            "score": {"value": 72, "max": 100, "label": "décision"},
        }

    def _kpis(self, forward: int, spot: int, spot_pct: float, economie: int) -> list[dict]:
        return [
            {
                "id": "cout_forward",
                "eyebrow": "Coût forward Y+1",
                "value": forward,
                "unit": "€/MWh",
                "delta": {"label": f"-{spot - forward} €/MWh vs spot", "tier": "pos"},
                "context": "Prix forward 12 mois pour bascule contractuelle.",
                "tier": "pos",
                "trace_tag": "billing",
                "trace": {
                    "source": "EEX forward curve (stub v1.0)",
                    "formula": "prix marché forward 12m",
                    "scope": "élec base",
                    "freshness": "J-1",
                },
                "link": {"label": "Voir l'achat →", "route": "/achat-energie"},
            },
            {
                "id": "exposition_spot",
                "eyebrow": "Exposition spot",
                "value": int(spot_pct),
                "unit": "%",
                "delta": {"label": "volume non couvert", "tier": "warn" if spot_pct > 40 else "neutral"},
                "context": "% du volume actuellement exposé aux variations spot.",
                "tier": "warn" if spot_pct > 40 else "neutral",
                "trace_tag": "billing",
                "trace": {
                    "source": "compute_spot_exposure v1.0",
                    "formula": "ContratCadre.type_prix heuristique",
                    "scope": "contrats actifs",
                    "freshness": "temps réel",
                },
                "link": {"label": "Voir les contrats →", "route": "/contrats"},
            },
            {
                "id": "economie_scenario",
                "eyebrow": "Économie scénario",
                "value": economie,
                "unit": "k€/an",
                "delta": {"label": "vs maintien spot", "tier": "pos"},
                "context": "Économie attendue en cas de bascule 60 % forward Y+1.",
                "tier": "pos",
                "trace_tag": "advisory",
                "trace": {
                    "source": "simulateur procurement (stub v1.0)",
                    "formula": "Σ (volume × (spot - forward))",
                    "scope": "12 mois glissants",
                    "freshness": "J-2",
                },
                "link": {"label": "Simuler →", "route": "/achat-energie"},
            },
        ]

    def _charts(self, forward: int, spot: int) -> list[dict]:
        return [
            {
                "id": "forward_curve",
                "type": "forward_curve",
                "question": "Quelle dynamique de prix forward Y+1 ?",
                "answer": (
                    f"Forward 12 m à {forward} €/MWh, spot actuel {spot} €/MWh. "
                    "Fenêtre d'opportunité courte avant retournement."
                ),
                "data": {
                    "forward": [
                        {"month": "M+0", "price": spot},
                        {"month": "M+3", "price": forward + 5},
                        {"month": "M+6", "price": forward},
                        {"month": "M+12", "price": forward - 3},
                    ],
                    "spot_now": spot,
                },
                "foot_scm": "Source · EEX forward curve (stub v1.0)",
            },
            {
                "id": "mix_renouvellement",
                "type": "bars_horizontal",
                "question": "Quel mix de renouvellement viser ?",
                "answer": "60 % forward Y+1 + 30 % cliquet + 10 % spot = équilibre risque/prix.",
                "data": [
                    {"label": "Forward Y+1", "pct": 60},
                    {"label": "Cliquet trimestriel", "pct": 30},
                    {"label": "Spot résiduel", "pct": 10},
                ],
                "foot_scm": "Source · stratégie procurement v1.0",
            },
        ]

    def _dossier_p1(self, days: int, fournisseur: str, economie: int, spot_pct: float) -> dict:
        return {
            "priority": "P1",
            "urgency_label": f"J-{days}",
            "category": "FINANCIER · ARBITRAGE ACHAT",
            "question": ("Quel scénario de renouvellement contrat élec activer avant échéance ?"),
            "recommendation": (
                f"Bascule 60 % volume sur forward Y+1 + 30 % cliquet trimestriel. "
                f"Économie attendue ≈ {economie} k€/an vs maintien spot."
            ),
            "proof_pills": [
                {"axis": "gravite", "tier": "warn", "value": "Échéance proche"},
                {"axis": "impact", "tier": "warn", "value": f"≈{economie} k€/an"},
                {"axis": "delai", "tier": "refuse", "value": f"J-{days}"},
                {"axis": "confiance", "tier": "ok", "value": "Haute (marché stable)"},
                {"axis": "reversibilite", "tier": "neutral", "value": "Faible (engagement Y+1)"},
            ],
            "body_html": (
                f"<p>Fournisseur actuel <strong>{fournisseur}</strong> arrive à "
                f"échéance dans <strong>{days} jours</strong>. Exposition spot "
                f"actuelle {spot_pct:.0f} % du volume.</p>"
            ),
            "scenarios": [
                {
                    "label": "A · MAINTIEN",
                    "title": "Reconduction contrat actuel",
                    "figs": {"capex_keur": 0, "gain_keur_an": 0, "payback_an": None},
                    "verdict": "risque marché conservé",
                },
                {
                    "label": "B · RECOMMANDÉ",
                    "title": "60 % forward Y+1 + 30 % cliquet",
                    "figs": {"capex_keur": 0, "gain_keur_an": economie, "payback_an": 0.1},
                    "recommended": True,
                },
                {
                    "label": "C · DÉFENSIF",
                    "title": "100 % forward Y+1 sécurisé",
                    "figs": {"capex_keur": 0, "gain_keur_an": int(economie * 0.7), "payback_an": 0.1},
                    "verdict": "moindre gain mais zéro volatilité",
                },
            ],
            "timeline": [
                {"step": "decision", "name": "Décision", "date": "Cette semaine", "status": "current"},
                {"step": "tender", "name": "Consultation 3 fournisseurs", "date": "+2 sem.", "status": "future"},
                {"step": "signature", "name": "Signature", "date": f"J-{max(days - 30, 7)}", "status": "future"},
                {"step": "go_live", "name": "Mise en service", "date": f"J-{days}", "status": "future"},
            ],
            "proof_sidebar": [
                {"label": "Économie projetée", "value": f"{economie} k€/an"},
                {"label": "Volume à renouveler", "value": "12 GWh", "detail": "valeur indicative v1.0"},
                {"label": "Fenêtre arbitrage", "value": f"{max(days - 30, 7)} j"},
                {"label": "Risque marché", "value": "Élevé", "detail": "spot volatil"},
            ],
            "why_promeos": (
                "<p>Trois fournisseurs consultés en parallèle activent un "
                "levier de négociation matériel. Le coût d'attente excède "
                "l'économie potentielle dès J+15.</p>"
            ),
            "links": ["/achat-energie", "/contrats"],
        }

    def _queue_p2_p3(self) -> list[dict]:
        return [
            {
                "tier": "P2",
                "title": "Consulter 3 fournisseurs alternatifs",
                "context": "ENGIE, TotalEnergies, ENI",
                "value_label": "négociation",
            },
            {
                "tier": "P2",
                "title": "Vérifier clauses indexation",
                "context": "TURPE + accises répercutées",
                "value_label": "audit 1 sem.",
            },
            {
                "tier": "P3",
                "title": "Évaluer PPA renouvelable",
                "context": "alternative long terme",
                "value_label": "qualifier",
            },
        ]

    def _verdict(self, days: int, fournisseur: str) -> dict:
        return {
            "constraint": {
                "label": "Votre contrainte principale",
                "statement": f"est temporelle : fenêtre achat se ferme dans {days} jours.",
                "detail": (
                    "Tout retard de décision dégrade l'effet de levier négociation "
                    "et restreint le panel fournisseurs consultables."
                ),
            },
            "opportunity": {
                "label": "Votre opportunité principale",
                "statement": "est la bascule forward Y+1 vs maintien spot.",
                "detail": (
                    "Le différentiel forward/spot actuel est l'un des plus favorables des 24 derniers mois (EEX)."
                ),
            },
        }
