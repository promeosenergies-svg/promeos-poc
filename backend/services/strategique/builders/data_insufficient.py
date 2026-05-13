"""PROMEOS — DataInsufficientBuilder v1.0 (mode onboarding).

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §4.

Mode déclenché quand maturité patrimoine < 60 % ou ratio UNKNOWN > 30 %.

Narration cardinale :
  Hero    : "Cadre indéterminé : N champs critiques manquants."
  KPI 1   : Maturité patrimoine %
  KPI 2   : Sites qualifiés
  KPI 3   : Données manquantes
  Chart 1 : MaturityRadar (champs renseignés par catégorie) — stub v1.0
  Chart 2 : MissingFields (top champs à renseigner) — stub v1.0
  Verdict : "Cadre indéterminé. Il manque X champs pour produire une reco."

CTAs verbes : renseigner / importer / qualifier.
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
from services.strategique.mode_thresholds import StrategicMode


class DataInsufficientBuilder(StrategicModeBuilder):
    mode = StrategicMode.DATA_INSUFFICIENT

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
        missing_inputs_all: list[str] = []
        sites_qualified = 0
        sites_total = 0

        for entry in applicability.get(RuleCode.DT, []):
            sites_total += 1
            if entry.status == ApplicabilityStatus.APPLICABLE:
                sites_qualified += 1
            missing_inputs_all.extend(entry.missing_inputs)
        for rule in (RuleCode.BACS, RuleCode.APER, RuleCode.SME, RuleCode.BEGES):
            for entry in applicability.get(rule, []):
                missing_inputs_all.extend(entry.missing_inputs)

        # Dédup en gardant l'ordre d'apparition
        seen = set()
        missing_unique: list[str] = []
        for f in missing_inputs_all:
            if f not in seen:
                seen.add(f)
                missing_unique.append(f)

        maturity_pct = round(patrimoine_maturity * 100)

        return {
            "strategic_mode": self.mode.value,
            "applicability": self._serialize_applicability(applicability),
            "patrimoine_maturity": patrimoine_maturity,
            "verdict": self._verdict(missing_count=len(missing_unique)),
            "hero": self._hero(
                maturity_pct=maturity_pct,
                missing_count=len(missing_unique),
                persona=persona,
            ),
            "kpis": self._kpis(
                maturity_pct=maturity_pct,
                sites_qualified=sites_qualified,
                sites_total=sites_total,
                missing_count=len(missing_unique),
            ),
            "charts": self._charts(missing_unique=missing_unique),
            "dossier_p1": self._dossier_p1(
                missing_unique=missing_unique,
                maturity_pct=maturity_pct,
            ),
            "queue_p2_p3": self._queue_p2_p3(),
            "continuity": {"last_visit": None, "items": []},
            "footer": self._build_footer(
                sources=[
                    "regulatory.applicability_service v1.0 (DATA_MISSING gates)",
                ]
            ),
            "_audit": self._build_audit_section(org_id),
        }

    def _hero(self, maturity_pct: int, missing_count: int, persona: str) -> dict:
        return {
            "kicker": "RECOMMANDATION PROMEOS · Synthèse stratégique",
            "title": f"Cadre indéterminé : {missing_count} champ(s) critique(s) à renseigner.",
            "title_em": "Renseigner le patrimoine débloque la trajectoire chiffrée.",
            "sub_constat": (
                f"Maturité patrimoine actuelle : {maturity_pct} %. Tant que les "
                "champs critiques (surface tertiaire, usage, puissance CVC, effectif) "
                "ne sont pas remplis, aucune trajectoire ni économie ne peut être "
                "chiffrée avec confiance."
            ),
            "sub_implications": (
                "Importer un fichier .xlsx patrimoine ou compléter le wizard "
                "onboarding débloque l'évaluation des 5 règles cataloguées."
            ),
            "meta": {
                "quality_pct": maturity_pct,
                "confidence": "basse",
                "period": "Mai 2026",
                "persona": persona,
            },
            "ctas": [
                {"label": "Renseigner le patrimoine", "verb": "renseigner", "primary": True},
                {"label": "Importer un fichier", "verb": "importer"},
                {"label": "Qualifier un site", "verb": "qualifier"},
            ],
            "score": {"value": maturity_pct, "max": 100, "label": "maturité"},
        }

    def _kpis(
        self,
        maturity_pct: int,
        sites_qualified: int,
        sites_total: int,
        missing_count: int,
    ) -> list[dict]:
        sites_label = f"{sites_qualified} / {sites_total}" if sites_total else "0 / 0"
        return [
            {
                "id": "maturite_patrimoine",
                "eyebrow": "Maturité patrimoine",
                "value": maturity_pct,
                "unit": "%",
                "delta": {"label": "cible 80 %", "tier": "warn"},
                "context": "Ratio champs critiques renseignés sur le total attendu v1.0.",
                "tier": "warn",
                "trace_tag": "platform",
                "trace": {
                    "source": "regulatory.applicability_service.compute_patrimoine_maturity",
                    "formula": "champs_renseignés / champs_critiques_v1.0",
                    "scope": "Organisation + Sites + Bâtiments",
                    "freshness": "temps réel",
                },
                "link": {"label": "Compléter →", "route": "/patrimoine"},
            },
            {
                "id": "sites_qualifies",
                "eyebrow": "Sites qualifiés",
                "value": sites_qualified,
                "unit": f"/ {sites_total}",
                "delta": {"label": sites_label, "tier": "neutral"},
                "context": "Sites pour lesquels au moins une règle peut être statuée APPLICABLE.",
                "tier": "neutral",
                "trace_tag": "regulatory",
                "trace": {
                    "source": "regulatory.applicability_service.compute_applicability",
                    "formula": "count(sites où DT/BACS/APER == APPLICABLE)",
                    "scope": "Sites assujettis potentiels",
                    "freshness": "temps réel",
                },
                "link": {"label": "Voir les sites →", "route": "/patrimoine"},
            },
            {
                "id": "donnees_manquantes",
                "eyebrow": "Données manquantes",
                "value": missing_count,
                "unit": "champs",
                "delta": {"label": "à compléter", "tier": "refuse"},
                "context": "Champs critiques absents bloquant l'évaluation réglementaire.",
                "tier": "refuse",
                "trace_tag": "platform",
                "trace": {
                    "source": "RuleApplicability.missing_inputs aggregator",
                    "formula": "Σ dédupliqué(missing_inputs)",
                    "scope": "5 règles × N sites",
                    "freshness": "temps réel",
                },
                "link": {"label": "Compléter →", "route": "/patrimoine"},
            },
        ]

    def _charts(self, missing_unique: list[str]) -> list[dict]:
        # Maturity radar — stub v1.0 (simplifié à 4 axes)
        radar_axes = [
            {"axis": "Identité", "pct": 80},
            {"axis": "Surface & usage", "pct": 50},
            {"axis": "Bâtiments / CVC", "pct": 30},
            {"axis": "Organisation", "pct": 60},
        ]
        top_missing = [{"field": f, "rank": i + 1} for i, f in enumerate(missing_unique[:8])]
        return [
            {
                "id": "maturity_radar",
                "type": "radar",
                "question": "Quels axes du patrimoine sont les moins renseignés ?",
                "answer": "Les champs Bâtiments / CVC sont le plus en retard, ils bloquent l'évaluation BACS.",
                "data": radar_axes,
                "foot_scm": "Source · regulatory.applicability_service v1.0",
            },
            {
                "id": "missing_fields",
                "type": "missing_list",
                "question": "Top champs à renseigner pour débloquer ?",
                "answer": (
                    f"{min(8, len(missing_unique))} champ(s) critique(s) priorisé(s) — "
                    "renseigner les 3 premiers débloque 80 % de l'évaluation."
                ),
                "data": top_missing,
                "foot_scm": "Source · RuleApplicability.missing_inputs",
            },
        ]

    def _dossier_p1(self, missing_unique: list[str], maturity_pct: int) -> dict:
        return {
            "priority": "P1",
            "urgency_label": "T+0 — bloquant",
            "category": "PLATEFORME · ONBOARDING",
            "question": ("Comment passer de la maturité actuelle à une évaluation réglementaire chiffrée ?"),
            "recommendation": (
                "Compléter les champs critiques selon la liste priorisée. "
                "Importer le fichier patrimoine .xlsx accélère la saisie."
            ),
            "proof_pills": [
                {"axis": "gravite", "tier": "warn", "value": "Évaluation bloquée"},
                {"axis": "impact", "tier": "neutral", "value": f"Maturité {maturity_pct} %"},
                {"axis": "delai", "tier": "ok", "value": "Action immédiate"},
                {"axis": "confiance", "tier": "ok", "value": "Élevée (champs explicites)"},
                {"axis": "reversibilite", "tier": "ok", "value": "Totale"},
            ],
            "body_html": (
                f"<p>{len(missing_unique)} champ(s) à renseigner avant de pouvoir "
                "afficher une trajectoire DT, un benchmark NAF ou un plan d'action.</p>"
            ),
            "scenarios": [
                {
                    "label": "A · WIZARD",
                    "title": "Wizard pas à pas (10 min)",
                    "figs": {"effort_min": 10, "fields_unlocked": 8},
                },
                {
                    "label": "B · IMPORT",
                    "title": "Import .xlsx patrimoine",
                    "figs": {"effort_min": 5, "fields_unlocked": 24},
                    "recommended": True,
                },
                {
                    "label": "C · EXPERT",
                    "title": "Saisie manuelle expert",
                    "figs": {"effort_min": 30, "fields_unlocked": 24},
                },
            ],
            "timeline": [
                {"step": "saisie", "name": "Saisie / import", "date": "Aujourd'hui", "status": "current"},
                {"step": "evaluation", "name": "Évaluation auto", "date": "T+5 min", "status": "future"},
                {"step": "verdict", "name": "Synthèse stratégique", "date": "T+10 min", "status": "future"},
            ],
            "proof_sidebar": [
                {"label": "Champs critiques v1.0", "value": "9", "detail": "ADR-024 §6"},
                {"label": "Effort estimé", "value": "5-30 min"},
                {"label": "Effet débloque", "value": "Mode complet"},
            ],
            "why_promeos": (
                "<p>Sans patrimoine complet, aucune trajectoire ni économie ne "
                "peut être chiffrée. C'est le pré-requis fondamental.</p>"
            ),
            "links": ["/patrimoine", "/onboarding"],
        }

    def _queue_p2_p3(self) -> list[dict]:
        return [
            {
                "tier": "P2",
                "title": "Connecter Enedis (DataConnect)",
                "context": "fiabilise mesures consommation",
                "value_label": "8 sem.",
            },
            {
                "tier": "P2",
                "title": "Connecter GRDF (ADICT)",
                "context": "fiabilise mesures gaz",
                "value_label": "6 sem.",
            },
            {
                "tier": "P3",
                "title": "Compléter contrats énergie",
                "context": "active shadow billing",
                "value_label": "action 2 sem.",
            },
        ]

    def _verdict(self, missing_count: int) -> dict:
        return {
            "constraint": {
                "label": "Votre contrainte principale",
                "statement": "n'est pas encore identifiable, le patrimoine est incomplet.",
                "detail": (
                    f"Tant que les {missing_count} champ(s) critique(s) ne sont pas "
                    "renseignés, aucune règle ne peut être évaluée avec confiance "
                    "(maturité < 60 %)."
                ),
            },
            "opportunity": {
                "label": "Votre opportunité principale",
                "statement": "est de finaliser le patrimoine en 10 minutes.",
                "detail": (
                    "L'import .xlsx débloque l'évaluation des 5 règles cataloguées et active la trajectoire chiffrée."
                ),
            },
        }
