"""
PROMEOS — Demo Seed: Notification Events Generator (V108)
Creates 20+ realistic NotificationEvent entries spread over 60 days.
Covers BILLING, CONSUMPTION, COMPLIANCE, and ACTION_HUB sources.
"""

import json
from datetime import date, datetime, timedelta, timezone


_TEMPLATES = [
    # --- BILLING (5) ---
    {
        "source_type_key": "billing",
        "source_key": "billing:overcharge:site_0",
        "severity_key": "critical",
        "status_key": "new",
        "title": "Surfacturation détectée — facture EDF décembre",
        "message": "Anomalie de facturation : montant supérieur de 18% au tarif contractuel. Impact estimé : 1 240 €.",
        "deeplink": "/bill-intel",
        "site_idx": 0,
        "due_days": 30,
        "impact_eur": 1240.0,
        "age_days": 2,
    },
    {
        "source_type_key": "billing",
        "source_key": "billing:invoice_missing:site_1",
        "severity_key": "warn",
        "status_key": "read",
        "title": "Facture manquante — novembre Bureau Lyon",
        "message": "Aucune facture reçue pour la période de novembre. Vérifier avec TotalEnergies.",
        "deeplink": "/bill-intel",
        "site_idx": 1,
        "due_days": 15,
        "impact_eur": None,
        "age_days": 8,
    },
    {
        "source_type_key": "billing",
        "source_key": "billing:contract_expiry:site_1",
        "severity_key": "critical",
        "status_key": "new",
        "title": "Contrat élec expire dans 45 jours — Bureau Lyon",
        "message": "Le contrat TotalEnergies arrive à échéance. Négociation à engager rapidement.",
        "deeplink": "/billing/contracts",
        "site_idx": 1,
        "due_days": 45,
        "impact_eur": 5200.0,
        "age_days": 5,
    },
    {
        "source_type_key": "billing",
        "source_key": "billing:contract_expiry:site_2",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Contrat gaz expire dans 90 jours — Usine Toulouse",
        "message": "Le contrat Eni hybride arrive à échéance dans 90 jours. Comparer les offres.",
        "deeplink": "/billing/contracts",
        "site_idx": 2,
        "due_days": 90,
        "impact_eur": 3800.0,
        "age_days": 12,
    },
    {
        "source_type_key": "billing",
        "source_key": "billing:index_spike:site_3",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Hausse tarif indexé +12% — Hôtel Nice",
        "message": "Le prix spot du marché a augmenté de 12% ce mois. Impact annualisé : 2 100 EUR.",
        "deeplink": "/billing/market",
        "site_idx": 3,
        "due_days": None,
        "impact_eur": 2100.0,
        "age_days": 3,
    },
    # --- CONSUMPTION (6) ---
    {
        "source_type_key": "consumption",
        "source_key": "consumption:hors_horaires:site_0",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Consommation hors horaires élevée — Siège Paris",
        "message": "42% de la consommation en dehors des plages d'ouverture. Gisement : 8 400 kWh/an soit 1 550 EUR.",
        "deeplink": "/usages-horaires",
        "site_idx": 0,
        "due_days": None,
        "impact_eur": 1550.0,
        "age_days": 6,
    },
    {
        "source_type_key": "consumption",
        "source_key": "consumption:base_load:site_0",
        "severity_key": "info",
        "status_key": "new",
        "title": "Talon nocturne anormal — Siège Paris",
        "message": "Puissance minimale nocturne = 38% de la puissance moyenne. Équipements non éteints.",
        "deeplink": "/usages-horaires",
        "site_idx": 0,
        "due_days": None,
        "impact_eur": 680.0,
        "age_days": 15,
    },
    {
        "source_type_key": "consumption",
        "source_key": "consumption:weekend_anomaly:site_2",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Consommation weekend anormale — Usine Toulouse",
        "message": "Consommation weekend à 85% du niveau semaine. Process non programmé pour arrêt weekend ?",
        "deeplink": "/usages-horaires",
        "site_idx": 2,
        "due_days": None,
        "impact_eur": 4200.0,
        "age_days": 10,
    },
    {
        "source_type_key": "consumption",
        "source_key": "consumption:power_peak:site_3",
        "severity_key": "critical",
        "status_key": "new",
        "title": "Dépassement puissance souscrite — Hôtel Nice",
        "message": "3 dépassements de puissance souscrite détectés en 30 jours. Risque de pénalité TURPE.",
        "deeplink": "/monitoring",
        "site_idx": 3,
        "due_days": 14,
        "impact_eur": 3500.0,
        "age_days": 1,
    },
    {
        "source_type_key": "consumption",
        "source_key": "consumption:drift_cvc:site_0",
        "severity_key": "warn",
        "status_key": "read",
        "title": "Dérive CVC détectée — Siège Paris",
        "message": "Consommation CVC en hausse de 15% sur les 2 dernières semaines (janvier-février).",
        "deeplink": "/monitoring",
        "site_idx": 0,
        "due_days": None,
        "impact_eur": 1200.0,
        "age_days": 20,
    },
    {
        "source_type_key": "consumption",
        "source_key": "consumption:data_gap:site_4",
        "severity_key": "info",
        "status_key": "new",
        "title": "Trou de données — École Marseille",
        "message": "48h de données manquantes détectées (semaine 12). Vérifier la connexion du compteur.",
        "deeplink": "/monitoring",
        "site_idx": 4,
        "due_days": None,
        "impact_eur": None,
        "age_days": 25,
    },
    # --- COMPLIANCE (5) ---
    {
        "source_type_key": "compliance",
        "source_key": "compliance:bacs:deadline:site_3",
        "severity_key": "critical",
        "status_key": "new",
        "title": "Échéance BACS dans 45 jours — Hôtel Nice",
        "message": "Décret BACS : installation GTB classe A/B requise. Pénalité possible : 1 500 EUR/an.",
        "deeplink": "/conformite",
        "site_idx": 3,
        "due_days": 45,
        "impact_eur": 1500.0,
        "age_days": 7,
    },
    {
        "source_type_key": "compliance",
        "source_key": "compliance:operat:declaration:site_1",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Déclaration OPERAT incomplète — Bureau Lyon",
        "message": "Consommation de référence non renseignée. Objectif de réduction incalculable.",
        "deeplink": "/conformite/tertiaire",
        "site_idx": 1,
        "due_days": 60,
        "impact_eur": None,
        "age_days": 14,
    },
    {
        "source_type_key": "compliance",
        "source_key": "compliance:dt:trajectory:site_0",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Trajectoire -40% non atteinte — Siège Paris",
        "message": "Échéance 2030 : la trajectoire de réduction n'est pas respectée. Plan de sobriété nécessaire.",
        "deeplink": "/conformite/tertiaire",
        "site_idx": 0,
        "due_days": None,
        "impact_eur": 7500.0,
        "age_days": 30,
    },
    {
        "source_type_key": "compliance",
        "source_key": "compliance:aper:ombriere:site_2",
        "severity_key": "info",
        "status_key": "read",
        "title": "Obligation APER ombrière PV — Usine Toulouse",
        "message": "Parking > 1500 m² : obligation d'installation ombrière PV d'ici juillet 2026.",
        "deeplink": "/conformite",
        "site_idx": 2,
        "due_days": 120,
        "impact_eur": None,
        "age_days": 40,
    },
    {
        "source_type_key": "compliance",
        "source_key": "compliance:evidence:missing:site_4",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Attestation BACS manquante — École Marseille",
        "message": "L'attestation BACS n'a pas été soumise. À obtenir auprès d'un organisme agréé.",
        "deeplink": "/conformite",
        "site_idx": 4,
        "due_days": 30,
        "impact_eur": 1500.0,
        "age_days": 18,
    },
    # --- ACTION HUB (4) ---
    {
        "source_type_key": "action_hub",
        "source_key": "action:overdue:gtb:site_3",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Action en retard — Installation GTB Hôtel Nice",
        "message": "L'action 'Installer GTB classe A/B' est en retard de 12 jours. Gain non réalisé : 8 200 EUR.",
        "deeplink": "/actions",
        "site_idx": 3,
        "due_days": -12,
        "impact_eur": 8200.0,
        "age_days": 12,
    },
    {
        "source_type_key": "action_hub",
        "source_key": "action:due_soon:audit:site_2",
        "severity_key": "info",
        "status_key": "read",
        "title": "Audit énergétique à planifier — Usine Toulouse",
        "message": "L'audit énergétique réglementaire arrive à échéance. Planifier avec un prestataire agréé.",
        "deeplink": "/actions",
        "site_idx": 2,
        "due_days": 30,
        "impact_eur": None,
        "age_days": 22,
    },
    {
        "source_type_key": "action_hub",
        "source_key": "action:completed:psub:site_0",
        "severity_key": "info",
        "status_key": "dismissed",
        "title": "Action terminée — Ajustement Psub Siège Paris",
        "message": "La puissance souscrite a été ajustée de 200 à 180 kVA. Économie réalisée : 1 800 EUR/an.",
        "deeplink": "/actions",
        "site_idx": 0,
        "due_days": None,
        "impact_eur": 1800.0,
        "age_days": 45,
    },
    {
        "source_type_key": "action_hub",
        "source_key": "action:new:cvc_optim:site_4",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Nouvelle action — Optimiser horaires CVC École Marseille",
        "message": "CVC fonctionne pendant les vacances scolaires. Programmation horaire à ajuster.",
        "deeplink": "/actions",
        "site_idx": 4,
        "due_days": 60,
        "impact_eur": 2400.0,
        "age_days": 4,
    },
]

_SOURCE_TYPE_MAP = {
    "billing": "BILLING",
    "consumption": "CONSUMPTION",
    "compliance": "COMPLIANCE",
    "action_hub": "ACTION_HUB",
}
_SEVERITY_MAP = {
    "info": "INFO",
    "warn": "WARN",
    "critical": "CRITICAL",
}
_STATUS_MAP = {
    "new": "NEW",
    "read": "READ",
    "dismissed": "DISMISSED",
}


def generate_notifications(db, org, sites: list, rng=None) -> dict:
    """Create 20 demo NotificationEvent entries spread over 60 days.

    Returns dict with count created.
    """
    from models.notification import NotificationEvent, NotificationBatch, NotificationPreference
    from models.enums import (
        NotificationSeverity,
        NotificationStatus,
        NotificationSourceType,
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    created = 0

    # Cap at 10 notifications — balanced across 4 source types for realistic demo
    _by_type = {}
    for t in _TEMPLATES:
        _by_type.setdefault(t["source_type_key"], []).append(t)
    capped_templates = (
        _by_type.get("billing", [])[:3]
        + _by_type.get("consumption", [])[:3]
        + _by_type.get("compliance", [])[:2]
        + _by_type.get("action_hub", [])[:2]
    )

    for tmpl in capped_templates:
        site_idx = tmpl.get("site_idx", 0)
        site = sites[min(site_idx, len(sites) - 1)] if sites else None

        # Dedup: skip if already exists
        existing = (
            db.query(NotificationEvent)
            .filter(
                NotificationEvent.org_id == org.id,
                NotificationEvent.source_key == tmpl["source_key"],
            )
            .first()
        )
        if existing:
            continue

        due = None
        if tmpl.get("due_days") is not None:
            due = date.today() + timedelta(days=tmpl["due_days"])

        source_type = getattr(
            NotificationSourceType,
            _SOURCE_TYPE_MAP[tmpl["source_type_key"]],
        )
        severity = getattr(NotificationSeverity, _SEVERITY_MAP[tmpl["severity_key"]])
        status = getattr(NotificationStatus, _STATUS_MAP[tmpl["status_key"]])

        # Spread creation timestamps over 60 days
        age_days = tmpl.get("age_days", 0)
        created_at = now - timedelta(days=age_days)

        event = NotificationEvent(
            org_id=org.id,
            site_id=site.id if site else None,
            source_type=source_type,
            source_id=f"demo_{tmpl['source_key']}",
            source_key=tmpl["source_key"],
            severity=severity,
            title=tmpl["title"],
            message=tmpl["message"],
            due_date=due,
            estimated_impact_eur=tmpl.get("impact_eur"),
            deeplink_path=tmpl.get("deeplink"),
            status=status,
            evidence_json=json.dumps({"seed": "helios_v108"}),
            created_at=created_at,
        )
        db.add(event)
        created += 1

    # NotificationBatch record
    batch = NotificationBatch(
        org_id=org.id,
        triggered_by="demo_seed",
        created_count=created,
        updated_count=0,
        skipped_count=len(_TEMPLATES) - created,
        started_at=now,
        finished_at=now,
    )
    db.add(batch)

    # Seed notification preferences (user opts into all sources)
    _seed_preferences(db, org)

    db.flush()

    return {"notifications_created": created}


def _seed_preferences(db, org):
    """Seed NotificationPreference for the demo org."""
    from models.notification import NotificationPreference
    import json

    existing = db.query(NotificationPreference).filter_by(org_id=org.id).first()
    if existing:
        return

    pref = NotificationPreference(
        org_id=org.id,
        enable_badges=True,
        snooze_days=0,
        thresholds_json=json.dumps(
            {
                "critical_due_days": 30,
                "warn_due_days": 60,
            }
        ),
    )
    db.add(pref)
