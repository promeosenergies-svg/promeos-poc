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
            "title": "Installer un systeme GTB classe A/B",
            "rationale": "Le site est assujetti au decret BACS et ne dispose pas d'un systeme de GTB conforme.",
            "priority": 1,
            "severity": "critical",
            "source_key": "bacs:gtb_install",
            "gain": (5000, 25000),
        },
        {
            "title": "Obtenir attestation BACS aupres d'un organisme agree",
            "rationale": "Attestation de conformite requise pour le decret BACS.",
            "priority": 2,
            "severity": "high",
            "source_key": "bacs:attestation",
            "gain": (0, 5000),
        },
        {
            "title": "Completer la declaration OPERAT",
            "rationale": "Donnees de consommation partielles. Declaration incomplete risquant une sanction.",
            "priority": 2,
            "severity": "medium",
            "source_key": "dt:operat_complete",
            "gain": (1000, 10000),
        },
        {
            "title": "Realiser un audit energetique reglementaire",
            "rationale": "Audit requis pour identifier les gisements d'economie d'energie.",
            "priority": 3,
            "severity": "medium",
            "source_key": "dt:audit",
            "gain": (3000, 15000),
        },
        {
            "title": "Evaluer l'installation d'une ombriere PV parking",
            "rationale": "Parking > 1500 m2, obligation APER d'installation ENR.",
            "priority": 3,
            "severity": "high",
            "source_key": "aper:ombriere",
            "gain": (2000, 20000),
        },
    ],
    "consumption": [
        {
            "title": "Reduire la consommation nocturne",
            "rationale": "Talon de puissance nocturne anormalement eleve detecte par le monitoring.",
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
            "rationale": "Risque de depassement de puissance souscrite detecte.",
            "priority": 1,
            "severity": "high",
            "source_key": "conso:psub_adjust",
            "gain": (500, 5000),
        },
    ],
    "billing": [
        {
            "title": "Contester la surfacturation detectee",
            "rationale": "Ecart significatif entre le montant facture et le shadow billing.",
            "priority": 1,
            "severity": "critical",
            "source_key": "billing:overcharge",
            "gain": (500, 10000),
        },
        {
            "title": "Negocier le renouvellement du contrat",
            "rationale": "Le contrat arrive a echeance, les conditions de marche sont favorables.",
            "priority": 3,
            "severity": "medium",
            "source_key": "billing:renewal",
            "gain": (2000, 30000),
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

    for i in range(actions_count):
        source_type_str = source_types[i % len(source_types)]
        templates = _ACTION_TEMPLATES[source_type_str]
        tpl = templates[i % len(templates)]
        site = sites[i % len(sites)]

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

        action = ActionItem(
            org_id=org.id,
            site_id=site.id,
            source_type=source_type_map[source_type_str],
            source_id=source_id,
            source_key=f"{tpl['source_key']}:{site.id}",
            title=tpl["title"],
            rationale=tpl["rationale"],
            priority=tpl["priority"],
            severity=tpl["severity"],
            estimated_gain_eur=rng.randint(*tpl["gain"]),
            due_date=due,
            status=status,
        )
        db.add(action)
        created += 1

    db.flush()
    return {"actions_count": created}
