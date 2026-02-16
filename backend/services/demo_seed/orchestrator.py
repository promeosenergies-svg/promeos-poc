"""
PROMEOS - Demo Seed Orchestrator
Coordinates all generators in the correct order.
"""
import random
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .packs import get_pack, list_packs


class SeedOrchestrator:
    """
    Orchestrate demo data seeding.

    Usage:
        orch = SeedOrchestrator(db)
        result = orch.seed(pack="casino", size="S")
    """

    def __init__(self, db: Session):
        self.db = db

    def seed(self, pack: str = "casino", size: str = "S",
             rng_seed: Optional[int] = None, days: int = 90) -> dict:
        """
        Seed demo data for a given pack and size.

        Args:
            pack: pack name ("casino", "tertiaire")
            size: "S" or "M"
            rng_seed: optional seed for deterministic generation
            days: readings lookback period

        Returns:
            dict with counts and timing
        """
        pack_def = get_pack(pack)
        if not pack_def:
            return {"error": f"Pack '{pack}' not found", "available": [p["key"] for p in list_packs()]}

        if size not in pack_def["sizes"]:
            return {"error": f"Size '{size}' not available for pack '{pack}'",
                    "available": list(pack_def["sizes"].keys())}

        rng = random.Random(rng_seed or 42)
        t0 = time.time()
        result = {"pack": pack, "size": size, "rng_seed": rng_seed or 42}

        # 1. Master data (org, sites, meters)
        from .gen_master import generate_master
        master = generate_master(self.db, pack_def, size, rng)
        result["org_id"] = master["org"].id
        result["org_nom"] = master["org"].nom
        result["sites_count"] = len(master["sites"])
        result["meters_count"] = len(master["meters"])
        result["default_site_id"] = master["sites"][0].id if master["sites"] else None

        # 2. Weather
        from .gen_weather import generate_weather
        temp_lookup = generate_weather(self.db, master["sites"], days, rng)
        result["weather_days"] = days

        # 3. Meter readings (depends on weather for correlation)
        from .gen_readings import generate_readings
        readings_count = generate_readings(
            self.db, master["meters"], master["site_profiles"],
            temp_lookup, days, rng
        )
        result["readings_count"] = readings_count

        # 4. Compliance
        from .gen_compliance import generate_compliance
        compliance = generate_compliance(self.db, master["org"], master["sites"], rng)
        result["compliance"] = compliance

        # 5. Monitoring (uses real engines on generated readings)
        from .gen_monitoring import generate_monitoring
        monitoring = generate_monitoring(
            self.db, master["sites"], master["meters"],
            master["site_profiles"], rng
        )
        result["monitoring"] = monitoring

        # 6. Billing
        from .gen_billing import generate_billing
        billing = generate_billing(
            self.db, master["org"], master["sites"],
            pack_def.get("invoices_count", 10), rng
        )
        result["billing"] = billing

        # 7. Actions
        from .gen_actions import generate_actions
        actions = generate_actions(
            self.db, master["org"], master["sites"],
            pack_def.get("actions_count", 10), rng
        )
        result["actions"] = actions

        # 8. Purchase scenarios
        from .gen_purchase import generate_purchase
        purchase = generate_purchase(self.db, master["sites"], rng)
        result["purchase"] = purchase

        # 9. Superuser
        self._create_superuser(master["org"])

        # Enable demo mode
        from services.demo_state import DemoState
        DemoState.enable()

        self.db.commit()

        result["elapsed_s"] = round(time.time() - t0, 2)
        result["status"] = "ok"
        return result

    def status(self) -> dict:
        """Get current demo data status (counts per table)."""
        from models import (
            Organisation, Site, Meter, MeterReading, MonitoringSnapshot,
            MonitoringAlert, EnergyInvoice, ActionItem, ComplianceFinding,
            ConsumptionInsight, PurchaseScenarioResult, EmsWeatherCache,
        )

        counts = {}
        for label, model in [
            ("organisations", Organisation),
            ("sites", Site),
            ("meters", Meter),
            ("readings", MeterReading),
            ("weather_days", EmsWeatherCache),
            ("snapshots", MonitoringSnapshot),
            ("alerts", MonitoringAlert),
            ("invoices", EnergyInvoice),
            ("actions", ActionItem),
            ("compliance_findings", ComplianceFinding),
            ("insights", ConsumptionInsight),
            ("purchase_scenarios", PurchaseScenarioResult),
        ]:
            try:
                counts[label] = self.db.query(model).count()
            except Exception:
                counts[label] = 0

        return counts

    def reset(self, mode: str = "soft") -> dict:
        """
        Reset demo data.

        Args:
            mode: "soft" (delete only is_demo=True data) or "hard" (purge all)

        Returns:
            dict with deleted counts
        """
        from sqlalchemy import or_
        from models import (
            Organisation, EntiteJuridique, Portefeuille, Site, Batiment,
            Compteur, Meter, MeterReading, MonitoringSnapshot, MonitoringAlert,
            EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight,
            ActionItem, ActionSyncBatch, ComplianceFinding, ComplianceRunBatch,
            ConsumptionInsight, Obligation, Evidence,
            PurchaseAssumptionSet, PurchaseScenarioResult,
            EmsWeatherCache, SiteOperatingSchedule,
        )

        deleted = {}

        # FK-safe deletion order (leaves first, roots last)
        delete_order = [
            ("purchase_scenarios", PurchaseScenarioResult),
            ("purchase_assumptions", PurchaseAssumptionSet),
            ("action_items", ActionItem),
            ("action_sync_batches", ActionSyncBatch),
            ("billing_insights", BillingInsight),
            ("invoice_lines", EnergyInvoiceLine),
            ("invoices", EnergyInvoice),
            ("contracts", EnergyContract),
            ("consumption_insights", ConsumptionInsight),
            ("monitoring_alerts", MonitoringAlert),
            ("monitoring_snapshots", MonitoringSnapshot),
            ("meter_readings", MeterReading),
            ("weather_cache", EmsWeatherCache),
            ("compliance_findings", ComplianceFinding),
            ("compliance_batches", ComplianceRunBatch),
            ("evidences", Evidence),
            ("obligations", Obligation),
            ("operating_schedules", SiteOperatingSchedule),
            ("meters", Meter),
            ("compteurs", Compteur),
            ("batiments", Batiment),
            ("sites", Site),
            ("portefeuilles", Portefeuille),
            ("entites_juridiques", EntiteJuridique),
            ("organisations", Organisation),
        ]

        if mode == "hard":
            # Hard: purge ALL rows
            for label, model in delete_order:
                try:
                    count = self.db.query(model).delete(synchronize_session=False)
                    deleted[label] = count
                except Exception:
                    deleted[label] = 0
        else:
            # Soft: only delete data linked to is_demo=True orgs/sites
            demo_org_ids = [r[0] for r in
                           self.db.query(Organisation.id).filter_by(is_demo=True).all()]
            demo_site_ids = [r[0] for r in
                            self.db.query(Site.id).filter_by(is_demo=True).all()]

            if not demo_org_ids and not demo_site_ids:
                return {"status": "ok", "mode": mode, "deleted": {},
                        "message": "no_demo_data"}

            # Collect intermediate IDs for nested FK chains
            demo_meter_ids = (
                [r[0] for r in self.db.query(Meter.id).filter(
                    Meter.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids else []
            )
            demo_snapshot_ids = (
                [r[0] for r in self.db.query(MonitoringSnapshot.id).filter(
                    MonitoringSnapshot.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids else []
            )
            demo_invoice_ids = (
                [r[0] for r in self.db.query(EnergyInvoice.id).filter(
                    EnergyInvoice.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids else []
            )
            demo_assumption_ids = (
                [r[0] for r in self.db.query(PurchaseAssumptionSet.id).filter(
                    PurchaseAssumptionSet.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids else []
            )
            demo_ej_ids = (
                [r[0] for r in self.db.query(EntiteJuridique.id).filter(
                    EntiteJuridique.organisation_id.in_(demo_org_ids)).all()]
                if demo_org_ids else []
            )

            def _del(label, model, fk_col, id_list):
                """Delete rows where fk_col IN id_list."""
                if not id_list:
                    deleted[label] = 0
                    return
                try:
                    count = self.db.query(model).filter(
                        fk_col.in_(id_list)
                    ).delete(synchronize_session=False)
                    deleted[label] = count
                except Exception:
                    deleted[label] = 0

            # Delete in FK-safe order using the appropriate FK for each table
            _del("purchase_scenarios", PurchaseScenarioResult,
                 PurchaseScenarioResult.assumption_set_id, demo_assumption_ids)
            _del("purchase_assumptions", PurchaseAssumptionSet,
                 PurchaseAssumptionSet.site_id, demo_site_ids)
            _del("action_items", ActionItem, ActionItem.org_id, demo_org_ids)
            _del("action_sync_batches", ActionSyncBatch,
                 ActionSyncBatch.org_id, demo_org_ids)
            _del("billing_insights", BillingInsight,
                 BillingInsight.invoice_id, demo_invoice_ids)
            _del("invoice_lines", EnergyInvoiceLine,
                 EnergyInvoiceLine.invoice_id, demo_invoice_ids)
            _del("invoices", EnergyInvoice,
                 EnergyInvoice.site_id, demo_site_ids)
            _del("contracts", EnergyContract,
                 EnergyContract.site_id, demo_site_ids)
            _del("consumption_insights", ConsumptionInsight,
                 ConsumptionInsight.site_id, demo_site_ids)
            _del("monitoring_alerts", MonitoringAlert,
                 MonitoringAlert.snapshot_id, demo_snapshot_ids)
            _del("monitoring_snapshots", MonitoringSnapshot,
                 MonitoringSnapshot.site_id, demo_site_ids)
            _del("meter_readings", MeterReading,
                 MeterReading.meter_id, demo_meter_ids)
            _del("weather_cache", EmsWeatherCache,
                 EmsWeatherCache.site_id, demo_site_ids)
            _del("compliance_findings", ComplianceFinding,
                 ComplianceFinding.site_id, demo_site_ids)
            _del("compliance_batches", ComplianceRunBatch,
                 ComplianceRunBatch.org_id, demo_org_ids)
            _del("evidences", Evidence, Evidence.site_id, demo_site_ids)
            _del("obligations", Obligation, Obligation.site_id, demo_site_ids)
            _del("operating_schedules", SiteOperatingSchedule,
                 SiteOperatingSchedule.site_id, demo_site_ids)
            _del("meters", Meter, Meter.site_id, demo_site_ids)
            _del("compteurs", Compteur, Compteur.site_id, demo_site_ids)
            _del("batiments", Batiment, Batiment.site_id, demo_site_ids)

            # Sites, portefeuilles, entites, orgs
            _del("sites", Site, Site.id, demo_site_ids)
            _del("portefeuilles", Portefeuille,
                 Portefeuille.entite_juridique_id, demo_ej_ids)
            _del("entites_juridiques", EntiteJuridique,
                 EntiteJuridique.organisation_id, demo_org_ids)
            _del("organisations", Organisation,
                 Organisation.id, demo_org_ids)

        self.db.commit()

        # Only disable demo mode if no demo orgs remain
        remaining = self.db.query(Organisation).filter_by(is_demo=True).count()
        if remaining == 0:
            from services.demo_state import DemoState
            DemoState.disable()

        return {"status": "ok", "mode": mode, "deleted": deleted}

    def _create_superuser(self, org):
        """Create demo admin user."""
        try:
            from models.iam import User, UserOrgRole, UserScope
            from models.enums import UserRole, ScopeLevel
            from services.iam_service import hash_password

            existing = self.db.query(User).filter_by(email="promeos@promeos.io").first()
            if existing:
                return

            user = User(
                email="promeos@promeos.io",
                hashed_password=hash_password("promeos2024"),
                nom="Admin", prenom="Promeos", actif=True,
            )
            self.db.add(user)
            self.db.flush()

            uor = UserOrgRole(user_id=user.id, org_id=org.id, role=UserRole.DG_OWNER)
            self.db.add(uor)
            self.db.flush()

            scope = UserScope(user_org_role_id=uor.id, scope_level=ScopeLevel.ORG, scope_id=org.id)
            self.db.add(scope)
            self.db.flush()
        except Exception:
            pass
