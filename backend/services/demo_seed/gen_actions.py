"""
PROMEOS - Demo Seed: Action Items Generator
Creates unified actions from compliance findings and consumption insights.
"""

import random
from datetime import date, timedelta

from models import ActionItem, ActionSourceType, ActionStatus


_ACTION_TEMPLATES = {
    "compliance": [
        {
            "title": "Installer un système GTB classe A/B",
            "rationale": "Le site est assujetti au décret BACS et ne dispose pas d'un système de GTB conforme.",
            "priority": 1,
            "severity": "critical",
            "source_key": "bacs:gtb_install",
            "gain": (5000, 25000),
        },
        {
            "title": "Obtenir attestation BACS auprès d'un organisme agréé",
            "rationale": "Attestation de conformité requise pour le décret BACS.",
            "priority": 2,
            "severity": "high",
            "source_key": "bacs:attestation",
            "gain": (500, 5000),
        },
        {
            "title": "Compléter la déclaration OPERAT",
            "rationale": "Données de consommation partielles. Déclaration incomplète risquant une sanction.",
            "priority": 2,
            "severity": "medium",
            "source_key": "dt:operat_complete",
            "gain": (1000, 10000),
        },
        {
            "title": "Réaliser un audit énergétique réglementaire",
            "rationale": "Audit requis pour identifier les gisements d'économie d'énergie.",
            "priority": 3,
            "severity": "medium",
            "source_key": "dt:audit",
            "gain": (3000, 15000),
        },
        {
            "title": "Évaluer l'installation d'une ombrière PV parking",
            "rationale": "Parking > 1500 m², obligation APER d'installation ENR.",
            "priority": 3,
            "severity": "high",
            "source_key": "aper:ombriere",
            "gain": (2000, 20000),
        },
    ],
    "consumption": [
        {
            "title": "Réduire la consommation nocturne",
            "rationale": "Talon de puissance nocturne anormalement élevé détecté par le monitoring.",
            "priority": 2,
            "severity": "high",
            "source_key": "conso:night_base",
            "gain": (2000, 15000),
        },
        {
            "title": "Optimiser les horaires d'ouverture CVC",
            "rationale": "Consommation hors horaires d'ouverture significative.",
            "priority": 2,
            "severity": "medium",
            "source_key": "conso:off_hours",
            "gain": (1000, 8000),
        },
        {
            "title": "Ajuster la puissance souscrite",
            "rationale": "Risque de dépassement de puissance souscrite détecté.",
            "priority": 1,
            "severity": "high",
            "source_key": "conso:psub_adjust",
            "gain": (500, 5000),
        },
        {
            "title": "Programmer l'arrêt CVC le week-end",
            "rationale": "Consommation week-end à 85% du niveau semaine. Arrêt programmable.",
            "priority": 2,
            "severity": "medium",
            "source_key": "conso:weekend_stop",
            "gain": (1500, 6000),
        },
        {
            "title": "Installer des détecteurs de présence éclairage",
            "rationale": "Éclairage permanent détecté hors occupation. Détecteurs recommandés.",
            "priority": 3,
            "severity": "low",
            "source_key": "conso:presence_detect",
            "gain": (800, 4000),
        },
    ],
    "billing": [
        {
            "title": "Contester la surfacturation détectée",
            "rationale": "Écart significatif entre le montant facturé et le shadow billing.",
            "priority": 1,
            "severity": "critical",
            "source_key": "billing:overcharge",
            "gain": (500, 10000),
        },
        {
            "title": "Négocier le renouvellement du contrat",
            "rationale": "Le contrat arrive à échéance, les conditions de marché sont favorables.",
            "priority": 3,
            "severity": "medium",
            "source_key": "billing:renewal",
            "gain": (2000, 30000),
        },
        {
            "title": "Vérifier l'option tarifaire TURPE",
            "rationale": "L'option tarifaire actuelle ne correspond pas au profil de consommation du site.",
            "priority": 2,
            "severity": "medium",
            "source_key": "billing:tarif_option",
            "gain": (1000, 8000),
        },
    ],
}


def generate_actions(db, org, sites: list, actions_count: int, rng: random.Random, **kwargs) -> dict:
    """Generate action items from various sources.

    If compliance_findings is passed (list of ComplianceFinding), compliance
    actions are linked to real finding IDs for demo traceability.
    """
    created = 0
    source_types = list(_ACTION_TEMPLATES.keys())
    compliance_findings = kwargs.get("compliance_findings", [])
    # Index NOK/UNKNOWN findings by source_key prefix for linking
    _nok_findings = [f for f in compliance_findings if f.status in ("NOK", "UNKNOWN")]

    # Track used (template, site) pairs to avoid duplicates
    used_pairs = set()

    for i in range(actions_count):
        source_type_str = source_types[i % len(source_types)]
        templates = _ACTION_TEMPLATES[source_type_str]
        tpl = templates[i % len(templates)]
        site = sites[i % len(sites)]

        # Skip if this exact template+site combo was already created
        pair_key = (tpl["source_key"], site.id)
        if pair_key in used_pairs:
            continue
        used_pairs.add(pair_key)

        source_type_map = {
            "compliance": ActionSourceType.COMPLIANCE,
            "consumption": ActionSourceType.CONSUMPTION,
            "billing": ActionSourceType.BILLING,
        }

        # Due date: 30 to 180 days from now
        due = date.today() + timedelta(days=rng.randint(30, 180))

        # Status: mix of open, in_progress, done
        status_choices = [ActionStatus.OPEN] * 5 + [ActionStatus.IN_PROGRESS] * 3 + [ActionStatus.DONE] * 2
        status = rng.choice(status_choices)

        # Link compliance actions to real finding IDs when available
        source_id = f"demo_{i}"
        if source_type_str == "compliance" and _nok_findings:
            prefix = tpl["source_key"].split(":")[0]  # "bacs", "dt", "aper"
            reg_map = {"bacs": "bacs", "dt": "decret_tertiaire_operat", "aper": "aper"}
            reg = reg_map.get(prefix)
            matching = [f for f in _nok_findings if f.regulation == reg and f.site_id == site.id]
            if not matching:
                matching = [f for f in _nok_findings if f.regulation == reg]
            if matching:
                source_id = str(matching[0].id)

        # Ensure gain is never 0
        gain_min, gain_max = tpl["gain"]
        estimated_gain = max(100, rng.randint(gain_min, gain_max))

        # Include site name in title to differentiate across sites
        site_short = site.nom.split()[0] if site.nom else f"Site{site.id}"
        title_with_site = f"{tpl['title']} — {site_short}"

        # For completed actions, set a realized gain (70–100% of estimate)
        realized_gain = None
        realized_at = None
        if status == ActionStatus.DONE:
            realized_gain = rng.randint(int(0.70 * estimated_gain), estimated_gain)
            realized_at = date.today() - timedelta(days=rng.randint(5, 60))

        action = ActionItem(
            org_id=org.id,
            site_id=site.id,
            source_type=source_type_map[source_type_str],
            source_id=source_id,
            source_key=f"{tpl['source_key']}:{site.id}",
            title=title_with_site,
            rationale=tpl["rationale"],
            priority=tpl["priority"],
            severity=tpl["severity"],
            estimated_gain_eur=estimated_gain,
            realized_gain_eur=realized_gain,
            realized_at=realized_at,
            due_date=due,
            status=status,
        )
        db.add(action)
        created += 1

    db.flush()
    return {"actions_count": created}
