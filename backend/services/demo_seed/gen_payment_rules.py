"""
PROMEOS — Demo Seed: Payment Rules & Reconciliation Generator (V108)
Creates PaymentRule records (portefeuille + site level) and
ReconciliationFixLog entries for audit trail demonstration.
"""
import json
import random
from datetime import datetime, timedelta, timezone


def generate_payment_rules(db, org, sites: list, rng: random.Random) -> dict:
    """Create payment rules at portefeuille and site levels + reconciliation logs.

    Returns dict with counts.
    """
    from models.payment_rule import PaymentRule
    from models.enums import PaymentRuleLevel
    from models import EntiteJuridique, Portefeuille, EnergyContract

    rules_created = 0

    # Get entites for this org
    entites = db.query(EntiteJuridique).filter_by(
        organisation_id=org.id
    ).all()
    if not entites:
        return {"payment_rules_created": 0, "reconciliation_logs_created": 0}

    # Get portefeuilles
    ej_ids = [e.id for e in entites]
    portefeuilles = db.query(Portefeuille).filter(
        Portefeuille.entite_juridique_id.in_(ej_ids)
    ).all()

    # Cost center labels per site type
    _COST_CENTERS = {
        "bureau": "CC-ADMIN-{idx:03d}",
        "entrepot": "CC-PROD-{idx:03d}",
        "hotel": "CC-HOSP-{idx:03d}",
        "enseignement": "CC-EDUC-{idx:03d}",
    }

    # 1. Portefeuille-level rules (default payer = first entite of portefeuille)
    for pf in portefeuilles:
        # Find the entite that owns this portefeuille
        invoice_ej = db.query(EntiteJuridique).get(pf.entite_juridique_id)
        if not invoice_ej:
            continue

        existing = db.query(PaymentRule).filter_by(
            level=PaymentRuleLevel.PORTEFEUILLE,
            portefeuille_id=pf.id,
        ).first()
        if existing:
            continue

        rule = PaymentRule(
            level=PaymentRuleLevel.PORTEFEUILLE,
            portefeuille_id=pf.id,
            site_id=None,
            contract_id=None,
            invoice_entity_id=invoice_ej.id,
            payer_entity_id=None,  # same as invoice entity
            cost_center=f"CC-PF-{pf.id:03d}",
        )
        db.add(rule)
        rules_created += 1

    db.flush()

    # 2. Site-level overrides (different cost center per site)
    for idx, site in enumerate(sites):
        type_site = getattr(site, '_type_site', 'bureau')
        cc_pattern = _COST_CENTERS.get(type_site, "CC-GEN-{idx:03d}")
        cost_center = cc_pattern.format(idx=idx + 1)

        # Find the invoice entity (via portefeuille → entite_juridique)
        pf = db.query(Portefeuille).get(site.portefeuille_id)
        if not pf:
            continue
        invoice_ej_id = pf.entite_juridique_id

        # For some sites, payer is a different entity (inter-company billing)
        payer_ej_id = None
        if idx % 3 == 2 and len(entites) > 1:
            # Every 3rd site: payer is a different entity
            other_entites = [e for e in entites if e.id != invoice_ej_id]
            if other_entites:
                payer_ej_id = rng.choice(other_entites).id

        existing = db.query(PaymentRule).filter_by(
            level=PaymentRuleLevel.SITE,
            site_id=site.id,
        ).first()
        if existing:
            continue

        rule = PaymentRule(
            level=PaymentRuleLevel.SITE,
            portefeuille_id=None,
            site_id=site.id,
            contract_id=None,
            invoice_entity_id=invoice_ej_id,
            payer_entity_id=payer_ej_id,
            cost_center=cost_center,
        )
        db.add(rule)
        rules_created += 1

    db.flush()

    # 3. Reconciliation fix logs (audit trail entries)
    recon_created = _generate_reconciliation_logs(db, sites, rng)

    return {
        "payment_rules_created": rules_created,
        "reconciliation_logs_created": recon_created,
    }


def _generate_reconciliation_logs(db, sites: list, rng: random.Random) -> int:
    """Create sample ReconciliationFixLog entries showing audit trail."""
    from models.reconciliation_fix_log import ReconciliationFixLog
    from models.enums import ReconciliationStatus

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    created = 0

    _LOG_TEMPLATES = [
        {
            "check_id": "RECON_TARIF_001",
            "action": "Correction tarif HP/HC appliquee",
            "status_before": ReconciliationStatus.WARN,
            "status_after": ReconciliationStatus.OK,
            "detail": {
                "type": "tarif_correction",
                "before": {"prix_hp": 0.1950, "prix_hc": 0.1350},
                "after": {"prix_hp": 0.1841, "prix_hc": 0.1210},
                "ecart_eur": 145.20,
            },
        },
        {
            "check_id": "RECON_INDEX_002",
            "action": "Releve d'index corrigee manuellement",
            "status_before": ReconciliationStatus.FAIL,
            "status_after": ReconciliationStatus.WARN,
            "detail": {
                "type": "index_correction",
                "before": {"index_kwh": 125400},
                "after": {"index_kwh": 124850},
                "ecart_kwh": 550,
            },
        },
        {
            "check_id": "RECON_PUISSANCE_003",
            "action": "Puissance souscrite reconciliee avec contrat",
            "status_before": ReconciliationStatus.WARN,
            "status_after": ReconciliationStatus.OK,
            "detail": {
                "type": "puissance_reconciliation",
                "facture_kva": 250,
                "contrat_kva": 200,
                "note": "Facture basee sur ancienne puissance, contrat mis a jour",
            },
        },
        {
            "check_id": "RECON_PERIOD_004",
            "action": "Periode de facturation alignee",
            "status_before": ReconciliationStatus.FAIL,
            "status_after": ReconciliationStatus.OK,
            "detail": {
                "type": "period_alignment",
                "before": {"debut": "2024-11-01", "fin": "2024-12-15"},
                "after": {"debut": "2024-11-01", "fin": "2024-11-30"},
                "note": "Chevauchement de periode corrige",
            },
        },
    ]

    # Distribute logs across sites
    for i, tmpl in enumerate(_LOG_TEMPLATES):
        site = sites[i % len(sites)]
        age_days = rng.randint(5, 45)

        log = ReconciliationFixLog(
            site_id=site.id,
            check_id=tmpl["check_id"],
            action=tmpl["action"],
            status_before=tmpl["status_before"],
            status_after=tmpl["status_after"],
            detail_json=json.dumps(tmpl["detail"], ensure_ascii=False),
            applied_by="promeos@promeos.io",
            applied_at=now - timedelta(days=age_days),
        )
        db.add(log)
        created += 1

    db.flush()
    return created
