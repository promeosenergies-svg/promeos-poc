"""
PROMEOS - Demo Seed: Billing Generator
Creates contracts, invoices, invoice lines, and billing insights.
"""

import json
import random
from datetime import date, datetime, timedelta

from models import (
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    BillingInsight,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
    InsightStatus,
    ContractIndexation,
    TariffOptionEnum,
    DeliveryPoint,
    DeliveryPointEnergyType,
    ContractDeliveryPoint,
    not_deleted,
)
from services.billing_engine.seasonal_resolver import compute_seasonal_ratios


_SUPPLIERS = ["EDF", "Engie", "TotalEnergies", "Eni", "Vattenfall"]


def generate_billing(db, org, sites: list, invoices_count: int, rng: random.Random, pack_def: dict = None) -> dict:
    """Generate contracts + invoices + lines + insights."""
    contracts_created = 0
    invoices_created = 0
    lines_created = 0
    insights_created = 0

    _ENERGY_TYPE_MAP = {"elec": BillingEnergyType.ELEC, "gaz": BillingEnergyType.GAZ}

    contract_map = {}  # site_id → list[contract] (all contracts per site, for invoices)

    if pack_def and "contracts_spec" in pack_def:
        # ── Explicit contracts (helios) ──────────────────────────────
        _DYNAMIC_ENDS = {
            "EXPIRING_SOON": 60,
            "EXPIRING_30": 30,
            "EXPIRING_90": 90,
            "EXPIRING_180": 180,
        }
        _INDEXATION_MAP = {
            "fixe": ContractIndexation.FIXE,
            "indexe": ContractIndexation.INDEXE,
            "spot": ContractIndexation.SPOT,
            "hybride": ContractIndexation.HYBRIDE,
        }
        for c_spec in pack_def["contracts_spec"]:
            site = sites[c_spec["site_idx"]]
            end_str = c_spec["end"]
            if end_str in _DYNAMIC_ENDS:
                end_date_val = date.today() + timedelta(days=_DYNAMIC_ENDS[end_str])
            else:
                end_date_val = date.fromisoformat(end_str)

            strategy = c_spec.get("strategy", "fixe")
            # V-registre: reference fournisseur + date de signature
            _REF_PREFIXES = {"EDF": "EDF", "Engie": "ENG", "TotalEnergies": "TE", "Eni": "ENI", "Vattenfall": "VAT"}
            ref_prefix = _REF_PREFIXES.get(c_spec["supplier"], "CTR")
            ref_fournisseur = f"{ref_prefix}-{date.fromisoformat(c_spec['start']).year}-{c_spec['site_idx']:03d}{c_spec['type'][0].upper()}"
            sig_date = date.fromisoformat(c_spec["start"]) - timedelta(days=rng.randint(15, 60))

            # V2 Engine: tariff option mapping
            _TARIFF_OPT_MAP = {
                "base": TariffOptionEnum.BASE,
                "hp_hc": TariffOptionEnum.HP_HC,
                "cu": TariffOptionEnum.CU,
                "mu": TariffOptionEnum.MU,
                "lu": TariffOptionEnum.LU,
            }

            contract = EnergyContract(
                site_id=site.id,
                energy_type=_ENERGY_TYPE_MAP.get(c_spec["type"], BillingEnergyType.ELEC),
                supplier_name=c_spec["supplier"],
                start_date=date.fromisoformat(c_spec["start"]),
                end_date=end_date_val,
                price_ref_eur_per_kwh=c_spec["price"],
                fixed_fee_eur_per_month=c_spec.get("fee", 50),
                notice_period_days=90,
                auto_renew=c_spec.get("auto_renew", False),
                offer_indexation=_INDEXATION_MAP.get(strategy),
                metadata_json=json.dumps({"strategy": strategy}),
                # V-registre: champs registre patrimonial & contractuel
                reference_fournisseur=ref_fournisseur,
                date_signature=sig_date,
                conditions_particulieres=c_spec.get("conditions"),
                # V2 Engine: puissance, option tarifaire, prix par periode
                subscribed_power_kva=c_spec.get("subscribed_power_kva"),
                tariff_option=_TARIFF_OPT_MAP.get(c_spec.get("tariff_option", "")),
                price_hpe_eur_kwh=c_spec.get("price_hpe_eur_kwh"),
                price_hce_eur_kwh=c_spec.get("price_hce_eur_kwh"),
                price_hp_eur_kwh=c_spec.get("price_hp_eur_kwh"),
                price_hc_eur_kwh=c_spec.get("price_hc_eur_kwh"),
                price_base_eur_kwh=c_spec.get("price_base_eur_kwh"),
            )
            db.add(contract)
            db.flush()

            # V-registre: rattacher les delivery points du site pour cette energie
            _DP_ENERGY_MAP = {"elec": DeliveryPointEnergyType.ELEC, "gaz": DeliveryPointEnergyType.GAZ}
            dp_energy = _DP_ENERGY_MAP.get(c_spec["type"])
            site_dps = (
                db.query(DeliveryPoint)
                .filter(
                    DeliveryPoint.site_id == site.id,
                    not_deleted(DeliveryPoint),
                )
                .all()
            )
            # Filtre par type energie si possible, sinon rattache tous les DP
            matching_dps = [dp for dp in site_dps if dp.energy_type == dp_energy] if dp_energy else site_dps
            if not matching_dps:
                matching_dps = site_dps  # fallback: rattache tout
            for dp in matching_dps:
                existing = (
                    db.query(ContractDeliveryPoint).filter_by(contract_id=contract.id, delivery_point_id=dp.id).first()
                )
                if not existing:
                    db.add(ContractDeliveryPoint(contract_id=contract.id, delivery_point_id=dp.id))

            # Store all contracts per site for invoice generation (ELEC + GAZ)
            contract_map.setdefault(site.id, []).append(contract)
            contracts_created += 1
    else:
        # ── Randomized contracts (tertiaire) ────────────────
        for site in sites:
            supplier = _SUPPLIERS[rng.randint(0, len(_SUPPLIERS) - 1)]
            price = round(rng.uniform(0.10, 0.25), 4)
            contract = EnergyContract(
                site_id=site.id,
                energy_type=BillingEnergyType.ELEC,
                supplier_name=supplier,
                start_date=date(2024, 1, 1),
                end_date=date(2026, 12, 31),
                price_ref_eur_per_kwh=price,
                fixed_fee_eur_per_month=round(rng.uniform(20, 200), 2),
                notice_period_days=90,
                auto_renew=rng.choice([True, False]),
            )
            db.add(contract)
            db.flush()
            contract_map.setdefault(site.id, []).append(contract)
            contracts_created += 1

    # Generate invoices — spread across sites and ALL their contracts (ELEC + GAZ)
    # Build flat list of (site, contract) pairs
    site_contract_pairs = []
    for site in sites:
        for ct in contract_map.get(site.id, []):
            site_contract_pairs.append((site, ct))
    if not site_contract_pairs:
        site_contract_pairs = [(s, None) for s in sites]

    for inv_idx in range(invoices_count):
        site, contract = site_contract_pairs[inv_idx % len(site_contract_pairs)]
        if not contract:
            continue

        # Period: rolling monthly invoices anchored to current date
        month_offset = inv_idx % 12
        today = date.today()
        # Go back month_offset months from current month
        target_month = today.month - month_offset
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        period_start = date(target_year, target_month, 1)
        if period_start.month == 12:
            period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

        supplier_prefix = (contract.supplier_name or "GEN")[:3].upper()
        inv_number = f"{supplier_prefix}-{site.id:04d}-{period_start.strftime('%Y%m')}"

        # Skip if invoice already exists (avoid IntegrityError on re-seed)
        existing = (
            db.query(EnergyInvoice)
            .filter_by(site_id=site.id, invoice_number=inv_number, period_start=period_start, period_end=period_end)
            .first()
        )
        if existing:
            continue

        # Realistic energy — aligned with shadow billing rates to avoid false anomalies
        is_gaz = contract.energy_type == BillingEnergyType.GAZ if contract.energy_type else False
        annual = site.annual_kwh_total or 500000
        # GAZ: lower volume (~30-40% of ELEC for tertiaire)
        annual_for_vector = annual * 0.35 if is_gaz else annual
        monthly_kwh = round(annual_for_vector / 12 * rng.uniform(0.8, 1.2), 0)
        price = contract.price_ref_eur_per_kwh or (0.08 if is_gaz else 0.15)
        energy_eur = round(monthly_kwh * price, 2)
        # Rates differ by energy vector
        if is_gaz:
            network_rate = 0.032  # ATRD/ATRT gaz
            tax_rate = 0.016  # TICGN
        else:
            network_rate = 0.0453  # TURPE C5 BT
            tax_rate = 0.0225  # Accise ELEC (TIEE)
        # Add small variance ±8% to look realistic without triggering 20% shadow_gap
        network_eur = round(monthly_kwh * network_rate * rng.uniform(0.92, 1.08), 2)
        tax_eur = round(monthly_kwh * tax_rate * rng.uniform(0.92, 1.08), 2)
        abo_eur = contract.fixed_fee_eur_per_month or 0
        # TTC = HT components + TVA (20% on energy/network/taxes, 5.5% on abonnement)
        ht = energy_eur + network_eur + tax_eur + abo_eur
        tva = round((energy_eur + network_eur + tax_eur) * 0.20 + abo_eur * 0.055, 2)
        total = round(ht + tva, 2)

        # Anomaly: 1 in 5 invoices — varied types
        # Anomalies modify specific line components, then recompute total with TVA
        is_anomaly = inv_idx % 5 == 3
        anomaly_type = None
        if is_anomaly:
            anomaly_type = rng.choice(["overcharge", "network_drift", "tax_mismatch"])
            if anomaly_type == "overcharge":
                energy_eur = round(energy_eur * rng.uniform(1.25, 1.45), 2)
            elif anomaly_type == "network_drift":
                network_eur = round(network_eur * rng.uniform(1.35, 1.65), 2)
            elif anomaly_type == "tax_mismatch":
                tax_eur = round(tax_eur * rng.uniform(1.30, 1.55), 2)
            # Recompute total with TVA so lines always sum to total
            ht = energy_eur + network_eur + tax_eur + abo_eur
            tva = round((energy_eur + network_eur + tax_eur) * 0.20 + abo_eur * 0.055, 2)
            total = round(ht + tva, 2)

        invoice = EnergyInvoice(
            site_id=site.id,
            contract_id=contract.id,
            invoice_number=inv_number,
            period_start=period_start,
            period_end=period_end,
            issue_date=period_end + timedelta(days=rng.randint(5, 20)),
            total_eur=total,
            energy_kwh=monthly_kwh,
            status=BillingInvoiceStatus.ANOMALY if is_anomaly else BillingInvoiceStatus.VALIDATED,
            source="demo_seed",
        )
        db.add(invoice)
        db.flush()
        invoices_created += 1

        # Invoice lines (including TVA so sum(lines) == total_eur)
        tva_line = round(total - (energy_eur + network_eur + tax_eur + abo_eur), 2)

        # V110: ventilation saisonnière pour les contrats 4 plages (CU/MU/LU)
        _4P_OPTIONS = {TariffOptionEnum.CU, TariffOptionEnum.MU, TariffOptionEnum.LU}
        is_4p = contract.tariff_option in _4P_OPTIONS if contract.tariff_option else False

        if is_4p:
            # Ventiler l'énergie par plage horosaisonnière via calendrier TURPE
            ratios = compute_seasonal_ratios(period_start, period_end, is_seasonal=True)
            for period_code, ratio in ratios.items():
                period_kwh = round(monthly_kwh * ratio, 1)
                period_price = price  # même prix unitaire pour la démo
                period_amount = round(energy_eur * ratio, 2)
                db.add(
                    EnergyInvoiceLine(
                        invoice_id=invoice.id,
                        line_type=InvoiceLineType.ENERGY,
                        label=f"Fourniture {period_code}",
                        amount_eur=period_amount,
                        qty=period_kwh,
                        unit="kWh",
                        unit_price=period_price,
                        period_code=period_code,
                        line_category=f"supply_{period_code.lower()}",
                    )
                )
                lines_created += 1
        else:
            db.add(
                EnergyInvoiceLine(
                    invoice_id=invoice.id,
                    line_type=InvoiceLineType.ENERGY,
                    label="Fourniture gaz naturel" if is_gaz else "Fourniture electricite",
                    amount_eur=energy_eur,
                    qty=monthly_kwh,
                    unit="kWh",
                    unit_price=price,
                )
            )
            lines_created += 1

        for lt, label, amount in [
            (InvoiceLineType.NETWORK, "Acheminement (ATRD)" if is_gaz else "Acheminement (TURPE)", network_eur),
            (InvoiceLineType.TAX, "TICGN" if is_gaz else "Taxes et contributions", tax_eur),
            (InvoiceLineType.OTHER, "Abonnement mensuel", contract.fixed_fee_eur_per_month or 0),
            (InvoiceLineType.OTHER, "TVA", tva_line),
        ]:
            db.add(
                EnergyInvoiceLine(
                    invoice_id=invoice.id,
                    line_type=lt,
                    label=label,
                    amount_eur=amount,
                    qty=monthly_kwh if lt == InvoiceLineType.NETWORK else None,
                    unit="kWh" if lt == InvoiceLineType.NETWORK else None,
                    unit_price=None,
                )
            )
            lines_created += 1

        # Billing insight for anomalous invoices — varied messages
        if is_anomaly and anomaly_type:
            _ANOMALY_TEMPLATES = {
                "overcharge": {
                    "type": "overcharge",
                    "severity": "high",
                    "msg": f"Surfacturation détectée sur {invoice.invoice_number}: montant TTC supérieur de "
                    f"{rng.randint(15, 35)}% au prix contractuel.",
                },
                "volume_spike": {
                    "type": "volume_spike",
                    "severity": "medium",
                    "msg": f"Pic de consommation anormal sur {invoice.invoice_number}: volume facturé "
                    f"{monthly_kwh:.0f} kWh vs moyenne attendue {annual / 12:.0f} kWh (+{rng.randint(20, 45)}%).",
                },
                "network_drift": {
                    "type": "network_drift",
                    "severity": "medium",
                    "msg": f"Dérive réseau (TURPE) sur {invoice.invoice_number}: coût acheminement "
                    f"{network_eur:.0f} EUR, soit +{rng.randint(30, 55)}% vs référence tarifaire.",
                },
                "tax_mismatch": {
                    "type": "tax_mismatch",
                    "severity": "low",
                    "msg": f"Écart taxes sur {invoice.invoice_number}: montant taxes {tax_eur:.0f} EUR "
                    f"ne correspond pas au taux applicable ({rng.choice(['accise', 'CTA', 'TVA'])} incorrect).",
                },
            }
            tpl = _ANOMALY_TEMPLATES[anomaly_type]
            # P1.3: Statuts variés — 60% OPEN, 15% ACK, 15% RESOLVED, 10% FALSE_POSITIVE
            _status_roll = rng.random()
            if _status_roll < 0.60:
                _insight_status = InsightStatus.OPEN
                _owner, _notes = None, None
            elif _status_roll < 0.75:
                _insight_status = InsightStatus.ACK
                _owner = rng.choice(["claire@atlas.demo", "lucas@atlas.demo"])
                _notes = None
            elif _status_roll < 0.90:
                _insight_status = InsightStatus.RESOLVED
                _owner = rng.choice(["claire@atlas.demo", "lucas@atlas.demo"])
                _notes = rng.choice(
                    [
                        "Verifie — facture correcte apres rapprochement compteur",
                        "Ecart justifie par changement tarifaire",
                        "Regularisation obtenue du fournisseur",
                    ]
                )
            else:
                _insight_status = InsightStatus.FALSE_POSITIVE
                _owner = "lucas@atlas.demo"
                _notes = "Faux positif — ecart lie a une estimation fournisseur"
            db.add(
                BillingInsight(
                    site_id=site.id,
                    invoice_id=invoice.id,
                    type=tpl["type"],
                    severity=tpl["severity"],
                    message=tpl["msg"],
                    estimated_loss_eur=round(total * rng.uniform(0.05, 0.20), 2),
                    insight_status=_insight_status,
                    owner=_owner,
                    notes=_notes,
                )
            )
            insights_created += 1

    db.flush()

    return {
        "contracts_count": contracts_created,
        "invoices_count": invoices_created,
        "lines_count": lines_created,
        "insights_count": insights_created,
    }


# ──────────────────────────────────────────────────────────────
# V2 Cadre + Annexes seed
# ──────────────────────────────────────────────────────────────


def generate_cadre_contracts(db, org, sites: list, rng=None) -> dict:
    """Generate V2 cadre contracts with annexes, pricing, volumes, events.
    Additive — does not break existing seed."""
    from models.contract_v2_models import ContractAnnexe, ContractPricing, VolumeCommitment, ContractEvent
    from models import EntiteJuridique, ContractStatus

    if len(sites) < 3:
        return {"cadres": 0, "annexes": 0}

    # Find EJ for org
    ej = db.query(EntiteJuridique).filter(EntiteJuridique.organisation_id == org.id).first()
    ej_id = ej.id if ej else None

    cadres_created = 0
    annexes_created = 0

    # ── Cadre 1: EDF Elec multi-site (3 annexes) ──
    cadre1 = EnergyContract(
        site_id=sites[0].id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF Entreprises",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 6, 15),
        reference_fournisseur="CADRE-2024-001",
        auto_renew=False,
        notice_period_days=90,
        offer_indexation=ContractIndexation.FIXE,
        contract_status=ContractStatus.EXPIRING,
        is_cadre=True,
        contract_type="CADRE",
        entite_juridique_id=ej_id,
        notice_period_months=3,
        is_green=False,
        segment_enedis="C4",
        annual_consumption_kwh=2_100_000.0,
        indexation_formula="TRVE-5%",
        indexation_reference="TRVE",
        indexation_spread_eur_mwh=-5.0,
        price_revision_clause="ANNUAL_REVIEW",
        notes="Contrat cadre EDF 3 sites — demo HELIOS",
    )
    db.add(cadre1)
    db.flush()
    cadres_created += 1

    # Pricing cadre EDF: horosaisonnier
    for pc, season, price in [
        ("HP", "HIVER", 0.1680),
        ("HC", "HIVER", 0.1220),
        ("HP", "ETE", 0.1425),
        ("HC", "ETE", 0.0985),
    ]:
        db.add(
            ContractPricing(
                contract_id=cadre1.id,
                period_code=pc,
                season=season,
                unit_price_eur_kwh=price,
            )
        )
    db.add(
        ContractPricing(
            contract_id=cadre1.id,
            period_code="BASE",
            season="ANNUEL",
            subscription_eur_month=145.80,
        )
    )

    # Annexe 1: Paris (herite)
    a1 = ContractAnnexe(
        contrat_cadre_id=cadre1.id,
        site_id=sites[0].id,
        annexe_ref="ANX-Paris-001",
        tariff_option=TariffOptionEnum.LU,
        subscribed_power_kva=108,
        segment_enedis="C4",
        has_price_override=False,
        status=ContractStatus.ACTIVE,
    )
    db.add(a1)
    db.flush()
    db.add(
        VolumeCommitment(
            annexe_id=a1.id,
            annual_kwh=850000,
            tolerance_pct_up=10,
            tolerance_pct_down=10,
            penalty_eur_kwh_above=0.015,
            penalty_eur_kwh_below=0.010,
        )
    )
    annexes_created += 1

    # Annexe 2: Lyon (override prix fixe 138)
    a2 = ContractAnnexe(
        contrat_cadre_id=cadre1.id,
        site_id=sites[1].id,
        annexe_ref="ANX-Lyon-002",
        tariff_option=TariffOptionEnum.MU4,
        subscribed_power_kva=60,
        segment_enedis="C4",
        has_price_override=True,
        override_pricing_model="FIXE",
        end_date_override=date(2026, 6, 28),
        status=ContractStatus.EXPIRING,
    )
    db.add(a2)
    db.flush()
    db.add(
        ContractPricing(
            annexe_id=a2.id,
            period_code="BASE",
            season="ANNUEL",
            unit_price_eur_kwh=0.138,
        )
    )
    db.add(
        VolumeCommitment(
            annexe_id=a2.id,
            annual_kwh=420000,
            tolerance_pct_up=10,
            tolerance_pct_down=10,
        )
    )
    annexes_created += 1

    # Annexe 3: Toulouse (herite)
    a3 = ContractAnnexe(
        contrat_cadre_id=cadre1.id,
        site_id=sites[2].id if len(sites) > 2 else sites[0].id,
        annexe_ref="ANX-Toulouse-003",
        tariff_option=TariffOptionEnum.CU4,
        subscribed_power_kva=72,
        segment_enedis="C4",
        has_price_override=False,
        status=ContractStatus.ACTIVE,
    )
    db.add(a3)
    db.flush()
    db.add(
        VolumeCommitment(
            annexe_id=a3.id,
            annual_kwh=380000,
            tolerance_pct_up=10,
            tolerance_pct_down=10,
        )
    )
    annexes_created += 1

    # Events cadre 1
    db.add(
        ContractEvent(
            contract_id=cadre1.id,
            event_type="CREATION",
            event_date=date(2024, 1, 1),
            description="Signature cadre 3 sites",
        )
    )
    db.add(
        ContractEvent(
            contract_id=cadre1.id,
            event_type="AVENANT",
            event_date=date(2024, 6, 15),
            description="Ajout Toulouse + PS Paris 96→108 kVA",
        )
    )

    # ── Cadre 2: ENGIE Gaz mono-site ──
    if len(sites) > 3:
        cadre2 = EnergyContract(
            site_id=sites[3].id,
            energy_type=BillingEnergyType.GAZ,
            supplier_name="ENGIE Pro",
            start_date=date(2025, 9, 1),
            end_date=date(2027, 12, 31),
            reference_fournisseur="GP-2025-114",
            auto_renew=True,
            notice_period_days=90,
            offer_indexation=ContractIndexation.INDEXE,
            contract_status=ContractStatus.ACTIVE,
            is_cadre=True,
            contract_type="UNIQUE",
            entite_juridique_id=ej_id,
            notice_period_months=3,
            annual_consumption_kwh=320_000.0,
            indexation_formula="PEG_DA+3",
            indexation_reference="PEG_DA",
            indexation_spread_eur_mwh=3.0,
            price_revision_clause="ANNUAL_REVIEW",
        )
        db.add(cadre2)
        db.flush()
        cadres_created += 1

        db.add(
            ContractPricing(
                contract_id=cadre2.id,
                period_code="BASE",
                season="ANNUEL",
                unit_price_eur_kwh=0.0528,
            )
        )
        a4 = ContractAnnexe(
            contrat_cadre_id=cadre2.id,
            site_id=sites[3].id,
            annexe_ref="ANX-Marseille-001",
            subscribed_power_kva=45,
            segment_enedis=None,
            has_price_override=False,
            status=ContractStatus.ACTIVE,
        )
        db.add(a4)
        db.flush()
        db.add(
            VolumeCommitment(
                annexe_id=a4.id,
                annual_kwh=320000,
            )
        )
        annexes_created += 1

        db.add(
            ContractEvent(
                contract_id=cadre2.id,
                event_type="CREATION",
                event_date=date(2025, 9, 1),
                description="Signature ENGIE gaz Marseille",
            )
        )

    # ── Cadre 3: TotalEnergies Elec mono-site ──
    if len(sites) > 4:
        cadre3 = EnergyContract(
            site_id=sites[4].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="TotalEnergies",
            start_date=date(2025, 1, 1),
            end_date=date(2027, 9, 30),
            reference_fournisseur="TE-B2B-2025-087",
            auto_renew=False,
            notice_period_days=90,
            # D.2: pricing SPOT + TUNNEL (cap+floor) pour Nice
            offer_indexation=ContractIndexation.SPOT,
            price_granularity="horaire",
            contract_status=ContractStatus.ACTIVE,
            is_cadre=True,
            contract_type="UNIQUE",
            entite_juridique_id=ej_id,
            notice_period_months=3,
            segment_enedis="C3",
            annual_consumption_kwh=720_000.0,
            # Clause TUNNEL : cap + floor
            price_revision_clause="TUNNEL",
            price_cap_eur_mwh=180.0,
            price_floor_eur_mwh=80.0,
            indexation_reference="EPEX_SPOT_FR",
            indexation_spread_eur_mwh=5.0,
            indexation_formula="SPOT+5",
        )
        db.add(cadre3)
        db.flush()
        cadres_created += 1

        for pc, season, price in [
            ("HP", "HIVER", 0.1780),
            ("HC", "HIVER", 0.1340),
            ("HP", "ETE", 0.1520),
            ("HC", "ETE", 0.1080),
        ]:
            db.add(
                ContractPricing(
                    contract_id=cadre3.id,
                    period_code=pc,
                    season=season,
                    unit_price_eur_kwh=price,
                )
            )
        a5 = ContractAnnexe(
            contrat_cadre_id=cadre3.id,
            site_id=sites[4].id,
            annexe_ref="ANX-Nice-001",
            tariff_option=TariffOptionEnum.HP_HC,
            subscribed_power_kva=120,
            segment_enedis="C4",
            has_price_override=False,
            status=ContractStatus.ACTIVE,
        )
        db.add(a5)
        db.flush()
        db.add(
            VolumeCommitment(
                annexe_id=a5.id,
                annual_kwh=720000,
            )
        )
        annexes_created += 1

        db.add(
            ContractEvent(
                contract_id=cadre3.id,
                event_type="CREATION",
                event_date=date(2025, 1, 1),
                description="Signature TotalEnergies Nice",
            )
        )

    # ── Cadre 4: ENGIE Gaz expire ──
    cadre4 = EnergyContract(
        site_id=sites[0].id,
        energy_type=BillingEnergyType.GAZ,
        supplier_name="ENGIE Pro",
        start_date=date(2023, 1, 1),
        end_date=date(2025, 12, 31),
        reference_fournisseur="GP-2023-089",
        auto_renew=False,
        notice_period_days=90,
        offer_indexation=ContractIndexation.FIXE,
        contract_status=ContractStatus.EXPIRED,
        is_cadre=True,
        contract_type="UNIQUE",
        entite_juridique_id=ej_id,
        notice_period_months=3,
        annual_consumption_kwh=150_000.0,
        indexation_formula="FIXE",
        price_revision_clause="NONE",
    )
    db.add(cadre4)
    db.flush()
    cadres_created += 1

    db.add(
        ContractPricing(
            contract_id=cadre4.id,
            period_code="BASE",
            season="ANNUEL",
            unit_price_eur_kwh=0.0486,
        )
    )
    a6 = ContractAnnexe(
        contrat_cadre_id=cadre4.id,
        site_id=sites[0].id,
        annexe_ref="ANX-Paris-Gaz-001",
        has_price_override=False,
        status=ContractStatus.EXPIRED,
    )
    db.add(a6)
    db.flush()
    db.add(
        VolumeCommitment(
            annexe_id=a6.id,
            annual_kwh=150000,
        )
    )
    annexes_created += 1

    db.add(
        ContractEvent(
            contract_id=cadre4.id,
            event_type="CREATION",
            event_date=date(2023, 1, 1),
            description="Signature ENGIE gaz Paris",
        )
    )

    db.flush()

    return {"cadres": cadres_created, "annexes": annexes_created}
