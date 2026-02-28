"""
PROMEOS — Demo Seed: Notification Events Generator (V83)
Creates realistic demo NotificationEvent entries spread across 4 source types.
"""
import json
from datetime import date, datetime, timedelta


_TEMPLATES = [
    # --- BILLING anomalies (2) ---
    {
        "source_type_key": "billing",
        "source_key": "billing:overcharge:site_0",
        "severity_key": "critical",
        "status_key": "new",
        "title": "Surfacturation détectée — facture EDF décembre",
        "message": (
            "Une anomalie de facturation a été détectée sur la facture de décembre. "
            "Le montant facturé est supérieur de 18 % au tarif contractuel. "
            "Impact estimé : 1 240 €."
        ),
        "deeplink": "/bill-intel",
        "site_idx": 0,
        "due_days": 30,
        "impact_eur": 1240.0,
    },
    {
        "source_type_key": "billing",
        "source_key": "billing:invoice_missing:site_1",
        "severity_key": "warn",
        "status_key": "read",
        "title": "Facture manquante — novembre site Paris-La-Défense",
        "message": (
            "Aucune facture reçue pour la période de novembre sur ce site. "
            "Vérifier avec le fournisseur Engie."
        ),
        "deeplink": "/bill-intel",
        "site_idx": 1,
        "due_days": 15,
        "impact_eur": None,
    },
    # --- CONSUMPTION monitoring (2) ---
    {
        "source_type_key": "consumption",
        "source_key": "consumption:hors_horaires:site_2",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Consommation hors horaires élevée — Site 3",
        "message": (
            "42 % de la consommation a lieu en dehors des plages d'ouverture déclarées. "
            "Gisement d'économie estimé : 8 400 kWh/an soit 1 550 €."
        ),
        "deeplink": "/usages-horaires",
        "site_idx": 2,
        "due_days": None,
        "impact_eur": 1550.0,
    },
    {
        "source_type_key": "consumption",
        "source_key": "consumption:base_load:site_0",
        "severity_key": "info",
        "status_key": "new",
        "title": "Talon de consommation nuit anormal — Site 1",
        "message": (
            "La puissance minimale nocturne (talon) représente 38 % de la puissance moyenne. "
            "Des équipements restent allumés hors production."
        ),
        "deeplink": "/usages-horaires",
        "site_idx": 0,
        "due_days": None,
        "impact_eur": 680.0,
    },
    # --- COMPLIANCE deadlines (2) ---
    {
        "source_type_key": "compliance",
        "source_key": "compliance:bacs:deadline:site_3",
        "severity_key": "critical",
        "status_key": "new",
        "title": "Échéance BACS dans 45 jours — Site 4",
        "message": (
            "Le décret BACS impose l'installation d'un système GTB classe A ou B. "
            "L'échéance réglementaire approche. Pénalité possible : 1 500 €/an."
        ),
        "deeplink": "/conformite",
        "site_idx": 3,
        "due_days": 45,
        "impact_eur": 1500.0,
    },
    {
        "source_type_key": "compliance",
        "source_key": "compliance:operat:declaration:site_1",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Déclaration OPERAT incomplète",
        "message": (
            "La consommation de référence n'est pas renseignée dans OPERAT. "
            "Sans cette donnée, l'objectif de réduction ne peut pas être calculé."
        ),
        "deeplink": "/conformite/tertiaire",
        "site_idx": 1,
        "due_days": 60,
        "impact_eur": None,
    },
    # --- ACTION HUB (2) ---
    {
        "source_type_key": "action_hub",
        "source_key": "action:overdue:gtb:site_4",
        "severity_key": "warn",
        "status_key": "new",
        "title": "Action en retard — Installation GTB Site 5",
        "message": (
            "L'action 'Installer un système GTB classe A/B' est en retard de 12 jours. "
            "Gain potentiel non réalisé : 8 200 €."
        ),
        "deeplink": "/actions",
        "site_idx": 4,
        "due_days": -12,  # overdue
        "impact_eur": 8200.0,
    },
    {
        "source_type_key": "action_hub",
        "source_key": "action:due_soon:audit:site_2",
        "severity_key": "info",
        "status_key": "read",
        "title": "Audit énergétique à planifier d'ici 30 jours",
        "message": (
            "L'action 'Réaliser un audit énergétique réglementaire' arrive à échéance. "
            "Planifier avec le prestataire agréé."
        ),
        "deeplink": "/actions",
        "site_idx": 2,
        "due_days": 30,
        "impact_eur": None,
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
    """Create 8 demo NotificationEvent entries for the org.

    Returns dict with count created.
    """
    from models.notification import NotificationEvent, NotificationBatch
    from models.enums import (
        NotificationSeverity, NotificationStatus, NotificationSourceType,
    )

    now = datetime.utcnow()
    created = 0

    for tmpl in _TEMPLATES:
        site_idx = tmpl.get("site_idx", 0)
        site = sites[min(site_idx, len(sites) - 1)] if sites else None

        # Dedup: skip if already exists
        existing = db.query(NotificationEvent).filter(
            NotificationEvent.org_id == org.id,
            NotificationEvent.source_key == tmpl["source_key"],
        ).first()
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
            evidence_json=json.dumps({"seed": "helios_v83"}),
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
    db.flush()

    return {"notifications_created": created}
