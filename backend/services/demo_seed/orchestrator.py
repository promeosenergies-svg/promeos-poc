"""
PROMEOS - Demo Seed Orchestrator
Coordinates all generators in the correct order.
"""

import random
import time
from datetime import datetime, timezone
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

    def seed(self, pack: str = "casino", size: str = "S", rng_seed: Optional[int] = None, days: int = 90) -> dict:
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
            return {
                "error": f"Size '{size}' not available for pack '{pack}'",
                "available": list(pack_def["sizes"].keys()),
            }

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
        result["default_site_name"] = master["sites"][0].nom if master["sites"] else None

        # Auto-create DeliveryPoints for meters that have PRM/PCE but no DP
        from services.onboarding_service import ensure_delivery_points_for_site

        dp_total = 0
        for s in master["sites"]:
            dp_total += ensure_delivery_points_for_site(self.db, s.id)
        self.db.flush()
        result["delivery_points_created"] = dp_total

        # V107: build site_meta for surface-normalized consumption
        site_meta = {}
        for s in master["sites"]:
            site_meta[s.id] = {
                "surface_m2": getattr(s, "_surface_m2", s.surface_m2 or 0),
                "type_site": getattr(s, "_type_site", "bureau"),
                "city": getattr(s, "_city", s.ville or ""),
            }

        # 2-3. Weather + Readings
        readings_freq = pack_def.get("readings_frequency", "hourly")
        # V85: pack can specify extended hourly window (helios → 730 days = 2 years)
        hourly_days = pack_def.get("hourly_days", days)
        temp_lookup = {}

        if readings_freq == "monthly":
            # ── Issue #115: Frequency-coherent reading generation ────────────
            # Guarantee: SUM(fine) == coarse for any overlapping time period.
            #
            # Time windows (helios: hourly_days=730, min15_days=365, months=60):
            #   Days 1-365:   MIN_15 → derived HOURLY/DAILY/MONTHLY (fully coherent)
            #   Days 366-730: independent HOURLY → derived DAILY/MONTHLY
            #   Months 25-60: independent MONTHLY (no finer data exists)

            from .gen_weather import generate_weather

            temp_lookup = generate_weather(self.db, master["sites"], hourly_days, rng)
            result["weather_days"] = hourly_days

            # Step 1: Coherent 15min → derived hourly + daily for recent period
            from .gen_readings import generate_coherent_readings

            min15_days = pack_def.get("min15_days", 365)
            min15_count, hourly_derived, daily_derived = generate_coherent_readings(
                self.db, master["meters"], master["site_profiles"], temp_lookup, min15_days, rng, site_meta=site_meta
            )
            result["min15_readings_count"] = min15_count

            # Step 2: Extended hourly for full range (INSERT OR IGNORE skips
            # the recent period where derived hourly already exists)
            from .gen_readings import generate_readings

            hourly_total = generate_readings(
                self.db, master["meters"], master["site_profiles"], temp_lookup, hourly_days, rng, site_meta=site_meta
            )
            result["hourly_readings_count"] = hourly_total

            # Step 3: Derive daily for the extended period (older hourly)
            from .gen_readings import _derive_daily_from_hourly, _derive_monthly_from_daily, _bulk_insert_ignore
            from datetime import timedelta as _td
            from models import MeterReading, FrequencyType

            now_ts = datetime.now().replace(microsecond=0)
            ext_start = now_ts - _td(days=hourly_days)
            ext_end = now_ts - _td(days=min15_days)
            extended_hourly = (
                self.db.query(MeterReading)
                .filter(
                    MeterReading.frequency == FrequencyType.HOURLY,
                    MeterReading.timestamp >= ext_start,
                    MeterReading.timestamp < ext_end,
                )
                .all()
            )
            ext_daily = _derive_daily_from_hourly(extended_hourly)
            _bulk_insert_ignore(self.db, ext_daily)
            self.db.flush()

            # Step 4: Derive monthly from ALL electricity daily (both periods)
            from models.energy_models import EnergyVector as _EV

            elec_meter_ids = [
                m.id
                for m in master["meters"]
                if m.parent_meter_id is None
                and not (
                    getattr(m, "energy_vector", None)
                    and (m.energy_vector == _EV.GAS or str(m.energy_vector).lower() == "gas")
                )
            ]
            if elec_meter_ids:
                all_elec_daily = (
                    self.db.query(MeterReading)
                    .filter(
                        MeterReading.frequency == FrequencyType.DAILY,
                        MeterReading.meter_id.in_(elec_meter_ids),
                    )
                    .all()
                )
                derived_monthly = _derive_monthly_from_daily(all_elec_daily)
                # Exclude current (partial) month to keep count deterministic
                current_month_start = now_ts.replace(day=1, hour=0, minute=0, second=0)
                derived_monthly = [r for r in derived_monthly if r.timestamp < current_month_start]
                _bulk_insert_ignore(self.db, derived_monthly)
                self.db.flush()

            # Step 5: Independent monthly (fills months beyond hourly coverage;
            # INSERT OR IGNORE skips months already covered by derived monthly)
            from .gen_readings import generate_monthly_readings

            readings_months = pack_def.get("readings_months", 36)
            readings_count = generate_monthly_readings(
                self.db, master["meters"], master["site_profiles"], readings_months, rng, site_meta=site_meta
            )
            result["readings_count"] = readings_count
            result["readings_frequency"] = "monthly"

            # Step 6: Gas daily readings (unchanged — gas has no hourly)
            from .gen_readings import generate_gas_readings

            gas_count = generate_gas_readings(
                self.db, master["meters"], master["site_profiles"], temp_lookup, hourly_days, rng, site_meta=site_meta
            )
            result["gas_readings_count"] = gas_count
        else:
            # Hourly readings (tertiaire) — with weather
            from .gen_weather import generate_weather

            temp_lookup = generate_weather(self.db, master["sites"], days, rng)
            result["weather_days"] = days

            from .gen_readings import generate_readings

            readings_count = generate_readings(
                self.db, master["meters"], master["site_profiles"], temp_lookup, days, rng, site_meta=site_meta
            )
            result["readings_count"] = readings_count
            result["readings_frequency"] = "hourly"

        # 3b. Sub-meter readings (Step 26) — proportional to parent
        from .gen_readings import generate_sub_meter_readings

        sub_days = hourly_days if readings_freq == "monthly" else days
        sub_count = generate_sub_meter_readings(self.db, master["meters"], sub_days, rng)
        if sub_count:
            result["sub_meter_readings_count"] = sub_count

        # 3c. Power Intelligence (CDC, contrats PS, plages HC)
        from .gen_power import seed_power

        power_stats = seed_power(self.db, days=days)
        result["power"] = power_stats

        # 4. Compliance
        from .gen_compliance import generate_compliance

        compliance = generate_compliance(self.db, master["org"], master["sites"], rng)
        result["compliance"] = compliance

        # 4b. Sync site compliance statuses from obligations
        self._sync_site_compliance_statuses(master["sites"])

        # 4c. BACS assets (V87: BacsAsset / BacsCvcSystem / BacsAssessment / BacsInspection)
        from .gen_bacs import generate_bacs

        bacs = generate_bacs(self.db, master["sites"], rng)
        result["bacs"] = bacs

        # 4d. Consumption targets (V87: yearly + monthly 2024-2026)
        from .gen_targets import generate_targets

        targets = generate_targets(self.db, master["sites"], rng, site_meta=site_meta)
        result["targets"] = targets

        # 4d-bis. DT baseline 2020-2023 (Decret Tertiaire reference period)
        from .gen_dt_baseline import generate_dt_baseline

        dt_baseline = generate_dt_baseline(self.db, master["sites"], rng, site_meta=site_meta)
        result["dt_baseline"] = dt_baseline

        # 4d-ter. Audit Energetique / SME (Loi 2025-391)
        from .gen_audit_sme import seed_audit_sme

        # Estimation conso totale org = somme conso sites
        total_conso_kwh = sum(getattr(s, "conso_kwh_an", 0) or 0 for s in master["sites"])
        if total_conso_kwh > 0:
            audit_sme = seed_audit_sme(self.db, master["org"].id, master["org"].nom, total_conso_kwh)
            result["audit_sme_obligation"] = audit_sme.obligation if audit_sme else None

        # 4e. EMS Explorer pre-built views + collections (V87)
        from .gen_ems_views import generate_ems_views

        ems_views = generate_ems_views(self.db, master["sites"])
        result["ems_views"] = ems_views

        # 5. Monitoring (hourly data now available for all packs)
        from .gen_monitoring import generate_monitoring

        monitoring = generate_monitoring(self.db, master["sites"], master["meters"], master["site_profiles"], rng)
        result["monitoring"] = monitoring

        # 6. Billing
        from .gen_billing import generate_billing

        billing = generate_billing(
            self.db,
            master["org"],
            master["sites"],
            pack_def.get("invoices_count", 10),
            rng,
            pack_def=pack_def,
        )
        result["billing"] = billing

        # 6a. V2 Cadre+Annexe contracts
        from .gen_billing import generate_cadre_contracts

        cadre_result = generate_cadre_contracts(
            self.db,
            master["org"],
            master["sites"],
            rng,
        )
        result["cadre_contracts"] = cadre_result

        # 6b. Billing audit-all → génère insights/anomalies post-seed
        from services.billing_service import audit_invoice_full
        from models import EnergyInvoice

        org_invoices = (
            self.db.query(EnergyInvoice).filter(EnergyInvoice.site_id.in_([s.id for s in master["sites"]])).all()
        )
        audit_count = 0
        for inv in org_invoices:
            try:
                audit_invoice_full(self.db, inv.id)
                audit_count += 1
            except Exception:
                pass  # non-blocking — seed continues even if one audit fails
        self.db.flush()
        result["billing_audit"] = {"audited": audit_count}

        # 6c. Vary insight statuses for demo realism (60% open, 15% ack, 15% resolved, 10% false_positive)
        from models.billing_models import BillingInsight
        from models.enums import InsightStatus

        all_insights = (
            self.db.query(BillingInsight).filter(BillingInsight.site_id.in_([s.id for s in master["sites"]])).all()
        )
        for bi in all_insights:
            roll = rng.random()
            if roll < 0.60:
                bi.insight_status = InsightStatus.OPEN
            elif roll < 0.75:
                bi.insight_status = InsightStatus.ACK
                bi.owner = rng.choice(["claire@atlas.demo", "lucas@atlas.demo"])
            elif roll < 0.90:
                bi.insight_status = InsightStatus.RESOLVED
                bi.owner = rng.choice(["claire@atlas.demo", "lucas@atlas.demo"])
                bi.notes = rng.choice(
                    [
                        "Verifie - facture correcte apres rapprochement compteur",
                        "Ecart justifie par changement tarifaire",
                        "Regularisation obtenue du fournisseur",
                    ]
                )
            else:
                bi.insight_status = InsightStatus.FALSE_POSITIVE
                bi.owner = "lucas@atlas.demo"
                bi.notes = "Faux positif - estimation fournisseur"
        self.db.flush()

        # 7. Actions (pass compliance findings for linking)
        from .gen_actions import generate_actions
        from models import ComplianceFinding

        site_ids = [s.id for s in master["sites"]]
        cf_list = self.db.query(ComplianceFinding).filter(ComplianceFinding.site_id.in_(site_ids)).all()
        actions = generate_actions(
            self.db,
            master["org"],
            master["sites"],
            pack_def.get("actions_count", 10),
            rng,
            compliance_findings=cf_list,
        )
        result["actions"] = actions

        # 8. Purchase scenarios
        from .gen_purchase import generate_purchase

        purchase = generate_purchase(self.db, master["sites"], rng)
        result["purchase"] = purchase

        # 9. Tertiaire / OPERAT (EFA, buildings, responsibilities, issues)
        from .gen_tertiaire import generate_tertiaire

        tertiaire = generate_tertiaire(
            self.db,
            master["org"],
            master["sites"],
            rng,
            buildings_map=master.get("buildings_map"),
        )
        result["tertiaire"] = tertiaire

        # 9b. Tertiaire EFA scenarios (3 named EFA for HELIOS demo)
        from .gen_tertiaire_efa import seed_tertiaire_efa

        helios_sites = {}
        for s in master["sites"]:
            name_lower = s.nom.lower()
            if "paris" in name_lower:
                helios_sites["paris"] = s
            elif "nice" in name_lower:
                helios_sites["nice"] = s
            elif "lyon" in name_lower:
                helios_sites["lyon"] = s
            elif "marseille" in name_lower:
                helios_sites["marseille"] = s
            elif "toulouse" in name_lower:
                helios_sites["toulouse"] = s
        efa_list = seed_tertiaire_efa(self.db, helios_sites)
        result["tertiaire_efa"] = {"efas_created": len(efa_list)}

        # 9b-bis. Run quality controls on seeded EFAs to populate issues
        try:
            from services.tertiaire_service import run_controls as run_tertiaire_controls

            issues_total = 0
            for efa in efa_list:
                issues = run_tertiaire_controls(self.db, efa.id, year=2024)
                issues_total += len(issues) if issues else 0
            result["tertiaire_efa"]["quality_issues"] = issues_total
        except Exception as exc:
            import logging

            logging.getLogger("demo_seed").warning("run_tertiaire_controls failed: %s", exc)
            result["tertiaire_efa"]["quality_issues_error"] = str(exc)

        # 9c. Compliance score history (6 months sparkline)
        from .gen_score_history import seed_score_history

        score_hist = seed_score_history(self.db, master["org"].id, master["sites"])
        result["score_history"] = score_hist

        # 10. TOU Schedules (HP/HC tariff windows per site)
        from .gen_tou import generate_tou

        tou = generate_tou(self.db, master["sites"], rng)
        result["tou"] = tou

        # 11. Notifications (20+ events spread over 60 days)
        from .gen_notifications import generate_notifications

        notifications = generate_notifications(self.db, master["org"], master["sites"], rng)
        result["notifications"] = notifications

        # 12. Payment rules & reconciliation audit trail
        from .gen_payment_rules import generate_payment_rules

        payment = generate_payment_rules(self.db, master["org"], master["sites"], rng)
        result["payment_rules"] = payment

        # 13. Market prices (EPEX Spot FR 24 mois)
        from .gen_market_prices import generate_market_prices

        market = generate_market_prices(self.db)
        result["market_prices"] = market

        # 13b. Tarifs réglementaires (TURPE 7, CSPE, CEE, CTA, TVA, Capacité, VNU)
        from services.market_tariff_loader import load_tariffs_from_yaml

        tariff_result = load_tariffs_from_yaml(self.db)
        result["market_tariffs"] = tariff_result

        # 14b. Geocode all sites via BAN
        from services.geocoding_service import geocode_org_sites

        try:
            geo_results = geocode_org_sites(self.db, master["org"].id, force=False)
            result["geocoding"] = {"geocoded": len(geo_results)}
        except Exception:
            result["geocoding"] = {"geocoded": 0, "error": "skipped"}

        # 14. Superuser
        self._create_superuser(master["org"])

        # 15. Onboarding auto-detect — mark completed steps from seeded data
        try:
            from models.onboarding_progress import OnboardingProgress
            from models import Organisation, EntiteJuridique, Portefeuille, Site, Compteur, ActionItem
            from models.user import UserOrgRole
            from models.billing import EnergyInvoice

            org_id = master["org"].id
            progress = self.db.query(OnboardingProgress).filter_by(org_id=org_id).first()
            if not progress:
                progress = OnboardingProgress(org_id=org_id)
                self.db.add(progress)
                self.db.flush()
            progress.step_org_created = True
            progress.step_sites_added = len(master["sites"]) > 0
            progress.step_meters_connected = True  # seed creates meters
            progress.step_invoices_imported = True  # seed creates invoices
            progress.step_users_invited = True  # superuser just created
            progress.step_first_action = True  # actions seeded above
            from datetime import datetime as dt, timezone

            progress.completed_at = dt.now(timezone.utc)
            self.db.flush()
            result["onboarding"] = {"completed": True}
        except Exception as e:
            result["onboarding"] = {"completed": False, "error": str(e)}

        # 15b. KB / Mémobox seed (archetypes, rules, recommendations)
        try:
            from routes.kb_usages import seed_demo_kb

            seed_demo_kb(self.db)
            self.db.flush()
            result["kb"] = {"seeded": True}
        except Exception as e:
            result["kb"] = {"seeded": False, "error": str(e)}

        # 15c. KB knowledge items seed (Mémobox content visible in frontend)
        try:
            self._seed_kb_items()
            result["kb_items"] = {"seeded": True}
        except Exception as e:
            result["kb_items"] = {"seeded": False, "error": str(e)}

        # 15d. Run analytics engine on all meters (KB-driven: archetype, anomalies, recommendations)
        try:
            from services.analytics_engine import AnalyticsEngine
            from models import Meter

            engine = AnalyticsEngine(self.db)
            meters = self.db.query(Meter).filter(Meter.site_id.in_([s.id for s in master["sites"]])).all()
            analyzed = 0
            for m in meters:
                try:
                    engine.analyze(m.id)
                    analyzed += 1
                except Exception:
                    pass  # Non-bloquant par meter
            self.db.flush()
            result["analytics"] = {"meters_analyzed": analyzed, "total": len(meters)}
        except Exception as e:
            result["analytics"] = {"error": str(e)}

        # 15e. Create ActionItems from top KB recommendations
        try:
            from models.energy_models import Recommendation as RecoModel
            from models import ActionItem, Site as SiteModel
            from models.enums import ActionSourceType, ActionStatus
            from datetime import date, timedelta
            from config.emission_factors import get_emission_factor

            top_recos = self.db.query(RecoModel).order_by(RecoModel.ice_score.desc().nullslast()).limit(10).all()
            kb_actions_created = 0
            seen_keys = set()
            for reco in top_recos:
                meter_obj = self.db.query(Meter).filter(Meter.id == reco.meter_id).first()
                if not meter_obj:
                    continue
                site_obj = self.db.query(SiteModel).filter(SiteModel.id == meter_obj.site_id).first()
                if not site_obj:
                    continue
                key = f"kb-reco:{site_obj.id}:{reco.recommendation_code}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                self.db.add(
                    ActionItem(
                        org_id=master["org"].id,
                        site_id=site_obj.id,
                        source_type=ActionSourceType.INSIGHT,
                        source_id=f"kb-reco:{reco.id}",
                        source_key=f"{site_obj.id}:{reco.recommendation_code}",
                        idempotency_key=key,
                        title=f"{reco.title} \u2014 {site_obj.nom}",
                        rationale=reco.title,
                        priority=3,
                        severity="medium",
                        estimated_gain_eur=reco.estimated_savings_eur_year,
                        co2e_savings_est_kg=round(reco.estimated_savings_kwh_year * get_emission_factor("ELEC"))
                        if reco.estimated_savings_kwh_year
                        else None,
                        due_date=date.today() + timedelta(days=60),
                        category="energie",
                        status=ActionStatus.OPEN,
                    )
                )
                kb_actions_created += 1
            self.db.flush()
            result["kb_actions"] = {"created": kb_actions_created}
        except Exception as e:
            result["kb_actions"] = {"error": str(e)}

        # 11. Segmentation profile (V101: seeded for demo coherence)
        self._seed_segmentation(master["org"])

        # Phase 1 completion: fill remaining gaps (APER, DataPoints, RegEvents, Purchase, Actions, Notifs, Evidence)
        from .gen_seed_completion import seed_completion

        completion = seed_completion(self.db, master["org"], master["sites"], rng)
        result["seed_completion"] = completion

        # Enable demo mode and register current org in DemoState (single source of truth)
        from services.demo_state import DemoState

        DemoState.enable()
        DemoState.set_demo_org(
            org_id=master["org"].id,
            org_nom=master["org"].nom,
            pack=pack,
            size=size,
            sites_count=len(master["sites"]),
            default_site_id=result.get("default_site_id"),
            default_site_name=result.get("default_site_name"),
        )

        # Recompute compliance scores for all sites (sync DT + BACS + unified score)
        try:
            from services.compliance_coordinator import recompute_site_full

            for s in master["sites"]:
                recompute_site_full(self.db, s.id)
            self.db.flush()
        except Exception as exc:
            import logging

            logging.getLogger("demo_seed").warning("Compliance recompute failed (non-bloquant): %s", exc)

        self.db.commit()

        result["elapsed_s"] = round(time.time() - t0, 2)
        result["status"] = "ok"
        return result

    def status(self, org_id: int = None) -> dict:
        """Get current demo data status (counts per table).

        Args:
            org_id: if provided, filter site/meter/reading counts to that org only.
                    Falls back to DemoState.get_demo_org_id() if None.
        """
        from models import (
            Organisation,
            Site,
            Portefeuille,
            EntiteJuridique,
            Meter,
            MeterReading,
            MonitoringSnapshot,
            MonitoringAlert,
            EnergyInvoice,
            ActionItem,
            ComplianceFinding,
            ConsumptionInsight,
            PurchaseScenarioResult,
            EmsWeatherCache,
        )
        from services.demo_state import DemoState

        effective_org_id = org_id or DemoState.get_demo_org_id()

        counts = {}

        # Organisation count (global — may be more than one if reseeded)
        try:
            counts["organisations"] = self.db.query(Organisation).count()
        except Exception:
            counts["organisations"] = 0

        # Site count — scoped to org when possible
        try:
            if effective_org_id is not None:
                counts["sites"] = (
                    self.db.query(Site)
                    .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
                    .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
                    .filter(EntiteJuridique.organisation_id == effective_org_id)
                    .count()
                )
            else:
                counts["sites"] = self.db.query(Site).count()
        except Exception:
            counts["sites"] = 0

        # Other counts (global for status panel — not critical for scope correctness)
        for label, model in [
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
            Organisation,
            EntiteJuridique,
            Portefeuille,
            Site,
            Batiment,
            Compteur,
            Meter,
            MeterReading,
            MonitoringSnapshot,
            MonitoringAlert,
            UsageProfile,
            Anomaly as AnomalyModel,
            Recommendation as RecommendationModel,
            EnergyContract,
            EnergyInvoice,
            EnergyInvoiceLine,
            BillingInsight,
            ActionItem,
            ActionSyncBatch,
            ComplianceFinding,
            ComplianceRunBatch,
            ConsumptionInsight,
            Obligation,
            Evidence,
            PurchaseAssumptionSet,
            PurchaseScenarioResult,
            EmsWeatherCache,
            SiteOperatingSchedule,
            Alerte,
        )
        from models.patrimoine import DeliveryPoint, ContractDeliveryPoint
        from models.usage import Usage
        from models.bacs_models import BacsInspection, BacsAssessment, BacsCvcSystem, BacsAsset
        from models.consumption_target import ConsumptionTarget
        from models.ems_models import EmsSavedView, EmsCollection
        from models.segmentation import SegmentationProfile, SegmentationAnswer
        from models.notification import NotificationEvent, NotificationBatch, NotificationPreference
        from models.tou_schedule import TOUSchedule
        from models.payment_rule import PaymentRule
        from models.reconciliation_fix_log import ReconciliationFixLog
        from models.compliance_score_history import ComplianceScoreHistory
        from models.iam import User, UserOrgRole, UserScope
        from models.tertiaire import (
            TertiaireDataQualityIssue,
            TertiaireProofArtifact,
            TertiaireDeclaration,
            TertiairePerimeterEvent,
            TertiaireResponsibility,
            TertiaireEfaBuilding,
            TertiaireEfaLink,
            TertiaireEfa,
            CsrdAssujettissementSite,
        )
        from models.audit_sme import AuditEnergetique
        from models.copilot_models import CopilotAction
        from models.intake import IntakeSession
        from models.onboarding_progress import OnboardingProgress
        from models.patrimoine import OrgEntiteLink, StagingBatch
        from models.market_models import PriceDecomposition, PriceSignal
        from models.notification import DigestPreference, WebhookSubscription

        deleted = {}

        # FK-safe deletion order (leaves first, roots last)
        delete_order = [
            # V87: BACS asset tree (inspections/assessments/systems before assets)
            ("bacs_inspections", BacsInspection),
            ("bacs_assessments", BacsAssessment),
            ("bacs_cvc_systems", BacsCvcSystem),
            ("bacs_assets", BacsAsset),
            # V87: consumption targets + EMS views (standalone, no site cascade)
            ("consumption_targets", ConsumptionTarget),
            ("ems_saved_views", EmsSavedView),
            ("ems_collections", EmsCollection),
            # Tertiaire V39 (leaves of tertiaire_efa)
            ("tertiaire_quality_issues", TertiaireDataQualityIssue),
            ("tertiaire_proofs", TertiaireProofArtifact),
            ("tertiaire_declarations", TertiaireDeclaration),
            ("tertiaire_events", TertiairePerimeterEvent),
            ("tertiaire_responsibilities", TertiaireResponsibility),
            ("tertiaire_buildings", TertiaireEfaBuilding),
            ("tertiaire_links", TertiaireEfaLink),
            ("tertiaire_efas", TertiaireEfa),
            # Payment & Reconciliation (V108)
            ("reconciliation_fix_logs", ReconciliationFixLog),
            ("payment_rules", PaymentRule),
            ("tou_schedules", TOUSchedule),
            # Purchase
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
            # Analytics engine results (FK to meter, kb_archetype, kb_anomaly_rule, kb_recommendation)
            ("usage_profiles", UsageProfile),
            ("anomalies", AnomalyModel),
            ("recommendations", RecommendationModel),
            ("weather_cache", EmsWeatherCache),
            ("compliance_score_history", ComplianceScoreHistory),
            ("compliance_findings", ComplianceFinding),
            ("compliance_batches", ComplianceRunBatch),
            ("evidences", Evidence),
            ("obligations", Obligation),
            ("operating_schedules", SiteOperatingSchedule),
            ("segmentation_answers", SegmentationAnswer),
            ("segmentation_profiles", SegmentationProfile),
            # Notifications (org_id FK)
            ("notification_events", NotificationEvent),
            ("notification_batches", NotificationBatch),
            ("notification_preferences", NotificationPreference),
            # IAM (user_scope → user_org_role → users)
            ("user_scopes", UserScope),
            ("user_org_roles", UserOrgRole),
            ("users", User),
            ("alertes", Alerte),
            ("usages", Usage),  # V107: FK to batiments, must delete before
            # DeliveryPoints (FK to sites, referenced by contract_delivery_points)
            ("contract_delivery_points", ContractDeliveryPoint),
            ("delivery_points", DeliveryPoint),
            ("meters", Meter),
            ("compteurs", Compteur),
            ("batiments", Batiment),
            ("sites", Site),
            ("portefeuilles", Portefeuille),
            # Tables avec FK org_id manquantes — doivent précéder organisations
            ("audit_energetique", AuditEnergetique),
            ("copilot_actions", CopilotAction),
            ("csrd_site_reporting", CsrdAssujettissementSite),
            ("digest_preferences", DigestPreference),
            ("intake_sessions", IntakeSession),
            ("onboarding_progress", OnboardingProgress),
            ("org_entite_links", OrgEntiteLink),
            ("price_decompositions", PriceDecomposition),
            ("price_signals", PriceSignal),
            ("staging_batches", StagingBatch),
            ("webhook_subscriptions", WebhookSubscription),
            ("entites_juridiques", EntiteJuridique),
            ("organisations", Organisation),
        ]

        if mode == "hard":
            # Hard: purge ALL tables via metadata (FK-safe reverse order)
            # Chaque table dans sa propre transaction pour éviter qu'un rollback
            # annule les suppressions précédentes (ex: tables enedis absentes).
            from sqlalchemy import text
            from models.base import Base as _Base

            self.db.execute(text("PRAGMA foreign_keys = OFF"))
            self.db.commit()
            for table in reversed(_Base.metadata.sorted_tables):
                try:
                    count = self.db.execute(table.delete()).rowcount
                    self.db.commit()
                    if count:
                        deleted[table.name] = count
                except Exception:
                    self.db.rollback()
            self.db.execute(text("PRAGMA foreign_keys = ON"))
            self.db.commit()
        else:
            # Soft: only delete data linked to is_demo=True orgs/sites
            demo_org_ids = [r[0] for r in self.db.query(Organisation.id).filter_by(is_demo=True).all()]
            demo_site_ids = [r[0] for r in self.db.query(Site.id).filter_by(is_demo=True).all()]

            if not demo_org_ids and not demo_site_ids:
                return {"status": "ok", "mode": mode, "deleted": {}, "message": "no_demo_data"}

            # Collect intermediate IDs for nested FK chains
            demo_meter_ids = (
                [r[0] for r in self.db.query(Meter.id).filter(Meter.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids
                else []
            )
            demo_snapshot_ids = (
                [
                    r[0]
                    for r in self.db.query(MonitoringSnapshot.id)
                    .filter(MonitoringSnapshot.site_id.in_(demo_site_ids))
                    .all()
                ]
                if demo_site_ids
                else []
            )
            demo_invoice_ids = (
                [r[0] for r in self.db.query(EnergyInvoice.id).filter(EnergyInvoice.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids
                else []
            )
            demo_assumption_ids = (
                [
                    r[0]
                    for r in self.db.query(PurchaseAssumptionSet.id)
                    .filter(PurchaseAssumptionSet.site_id.in_(demo_site_ids))
                    .all()
                ]
                if demo_site_ids
                else []
            )
            demo_ej_ids = (
                [
                    r[0]
                    for r in self.db.query(EntiteJuridique.id)
                    .filter(EntiteJuridique.organisation_id.in_(demo_org_ids))
                    .all()
                ]
                if demo_org_ids
                else []
            )
            demo_pf_ids = (
                [
                    r[0]
                    for r in self.db.query(Portefeuille.id)
                    .filter(Portefeuille.entite_juridique_id.in_(demo_ej_ids))
                    .all()
                ]
                if demo_ej_ids
                else []
            )

            def _del(label, model, fk_col, id_list):
                """Delete rows where fk_col IN id_list."""
                if not id_list:
                    deleted[label] = 0
                    return
                try:
                    count = self.db.query(model).filter(fk_col.in_(id_list)).delete(synchronize_session=False)
                    deleted[label] = count
                except Exception:
                    deleted[label] = 0

            # V87: collect bacs_asset IDs for FK-safe deletion
            demo_bacs_asset_ids = (
                [r[0] for r in self.db.query(BacsAsset.id).filter(BacsAsset.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids
                else []
            )

            # Delete in FK-safe order using the appropriate FK for each table
            _del("bacs_inspections", BacsInspection, BacsInspection.asset_id, demo_bacs_asset_ids)
            _del("bacs_assessments", BacsAssessment, BacsAssessment.asset_id, demo_bacs_asset_ids)
            _del("bacs_cvc_systems", BacsCvcSystem, BacsCvcSystem.asset_id, demo_bacs_asset_ids)
            _del("bacs_assets", BacsAsset, BacsAsset.site_id, demo_site_ids)
            _del("consumption_targets", ConsumptionTarget, ConsumptionTarget.site_id, demo_site_ids)
            # EMS views/collections are always demo-only — delete all
            try:
                deleted["ems_saved_views"] = self.db.query(EmsSavedView).delete(synchronize_session=False)
                deleted["ems_collections"] = self.db.query(EmsCollection).delete(synchronize_session=False)
            except Exception:
                pass

            # V108: Payment & Reconciliation
            _del("reconciliation_fix_logs", ReconciliationFixLog, ReconciliationFixLog.site_id, demo_site_ids)
            # PaymentRule: site-level + portefeuille-level
            _del("payment_rules_site", PaymentRule, PaymentRule.site_id, demo_site_ids)
            _del("payment_rules_pf", PaymentRule, PaymentRule.portefeuille_id, demo_pf_ids)
            _del("tou_schedules", TOUSchedule, TOUSchedule.site_id, demo_site_ids)
            _del(
                "purchase_scenarios",
                PurchaseScenarioResult,
                PurchaseScenarioResult.assumption_set_id,
                demo_assumption_ids,
            )
            _del("purchase_assumptions", PurchaseAssumptionSet, PurchaseAssumptionSet.site_id, demo_site_ids)
            _del("action_items", ActionItem, ActionItem.org_id, demo_org_ids)
            _del("action_sync_batches", ActionSyncBatch, ActionSyncBatch.org_id, demo_org_ids)
            _del("billing_insights", BillingInsight, BillingInsight.invoice_id, demo_invoice_ids)
            _del("invoice_lines", EnergyInvoiceLine, EnergyInvoiceLine.invoice_id, demo_invoice_ids)
            _del("invoices", EnergyInvoice, EnergyInvoice.site_id, demo_site_ids)
            _del("contracts", EnergyContract, EnergyContract.site_id, demo_site_ids)
            _del("consumption_insights", ConsumptionInsight, ConsumptionInsight.site_id, demo_site_ids)
            _del("monitoring_alerts", MonitoringAlert, MonitoringAlert.snapshot_id, demo_snapshot_ids)
            _del("monitoring_snapshots", MonitoringSnapshot, MonitoringSnapshot.site_id, demo_site_ids)
            _del("meter_readings", MeterReading, MeterReading.meter_id, demo_meter_ids)
            _del("weather_cache", EmsWeatherCache, EmsWeatherCache.site_id, demo_site_ids)
            _del("compliance_score_history", ComplianceScoreHistory, ComplianceScoreHistory.site_id, demo_site_ids)
            _del("compliance_findings", ComplianceFinding, ComplianceFinding.site_id, demo_site_ids)
            _del("compliance_batches", ComplianceRunBatch, ComplianceRunBatch.org_id, demo_org_ids)
            _del("evidences", Evidence, Evidence.site_id, demo_site_ids)
            _del("obligations", Obligation, Obligation.site_id, demo_site_ids)
            _del("operating_schedules", SiteOperatingSchedule, SiteOperatingSchedule.site_id, demo_site_ids)
            # V100: Segmentation (answers → profiles, both keyed by org_id)
            _del("segmentation_answers", SegmentationAnswer, SegmentationAnswer.organisation_id, demo_org_ids)
            _del("segmentation_profiles", SegmentationProfile, SegmentationProfile.organisation_id, demo_org_ids)
            # Notifications (org_id FK)
            _del("notification_events", NotificationEvent, NotificationEvent.org_id, demo_org_ids)
            _del("notification_batches", NotificationBatch, NotificationBatch.org_id, demo_org_ids)
            _del("notification_preferences", NotificationPreference, NotificationPreference.org_id, demo_org_ids)
            # IAM: collect user_org_role IDs for FK-safe deletion
            demo_uor_ids = (
                [r[0] for r in self.db.query(UserOrgRole.id).filter(UserOrgRole.org_id.in_(demo_org_ids)).all()]
                if demo_org_ids
                else []
            )
            _del("user_scopes", UserScope, UserScope.user_org_role_id, demo_uor_ids)
            _del("user_org_roles", UserOrgRole, UserOrgRole.org_id, demo_org_ids)
            _del("alertes", Alerte, Alerte.site_id, demo_site_ids)
            # V107: Usage records (FK to batiment)
            demo_bat_ids = (
                [r[0] for r in self.db.query(Batiment.id).filter(Batiment.site_id.in_(demo_site_ids)).all()]
                if demo_site_ids
                else []
            )
            _del("usages", Usage, Usage.batiment_id, demo_bat_ids)
            _del("meters", Meter, Meter.site_id, demo_site_ids)
            _del("compteurs", Compteur, Compteur.site_id, demo_site_ids)
            _del("batiments", Batiment, Batiment.site_id, demo_site_ids)

            # Sites, portefeuilles, entites, orgs
            _del("sites", Site, Site.id, demo_site_ids)
            _del("portefeuilles", Portefeuille, Portefeuille.entite_juridique_id, demo_ej_ids)
            _del("entites_juridiques", EntiteJuridique, EntiteJuridique.organisation_id, demo_org_ids)
            _del("organisations", Organisation, Organisation.id, demo_org_ids)

        self.db.commit()

        # Only disable demo mode if no demo orgs remain
        remaining = self.db.query(Organisation).filter_by(is_demo=True).count()
        if remaining == 0:
            from services.demo_state import DemoState

            DemoState.disable()
            DemoState.clear_demo_org()

        return {"status": "ok", "mode": mode, "deleted": deleted}

    def _sync_site_compliance_statuses(self, sites):
        """Update Site.statut_decret_tertiaire/bacs + risque_financier_euro + avancement from Obligation records."""
        from models import Obligation, TypeObligation, StatutConformite
        from config.emission_factors import BASE_PENALTY_EURO, A_RISQUE_PENALTY_EURO

        for site in sites:
            for type_obl, attr in [
                (TypeObligation.DECRET_TERTIAIRE, "statut_decret_tertiaire"),
                (TypeObligation.BACS, "statut_bacs"),
            ]:
                obl = self.db.query(Obligation).filter_by(site_id=site.id, type=type_obl).first()
                if obl:
                    setattr(site, attr, obl.statut)
                else:
                    setattr(site, attr, None)

            # Sync avancement_decret_pct from DT obligation
            dt_obl = self.db.query(Obligation).filter_by(site_id=site.id, type=TypeObligation.DECRET_TERTIAIRE).first()
            if dt_obl and dt_obl.avancement_pct is not None:
                site.avancement_decret_pct = dt_obl.avancement_pct

            # Compute risque_financier_euro from all obligations
            obls = self.db.query(Obligation).filter_by(site_id=site.id).all()
            risque = 0.0
            for o in obls:
                if o.statut == StatutConformite.NON_CONFORME:
                    risque += BASE_PENALTY_EURO  # confirmed penalty
                elif o.statut == StatutConformite.A_RISQUE:
                    risque += A_RISQUE_PENALTY_EURO  # estimated potential risk
            site.risque_financier_euro = round(risque, 2)
        self.db.flush()

    def _seed_segmentation(self, org):
        """Seed a coherent segmentation profile for the demo org."""
        try:
            from models.segmentation import SegmentationProfile
            from services.segmentation_service import detect_typologie, TYPO_LABELS
            import json

            # Delete any stale profile
            self.db.query(SegmentationProfile).filter(SegmentationProfile.organisation_id == org.id).delete(
                synchronize_session=False
            )

            detection = detect_typologie(self.db, org.id)
            typo = detection["typologie"]

            profile = SegmentationProfile(
                organisation_id=org.id,
                typologie=typo.value,
                segment_label=TYPO_LABELS.get(typo, typo.value),
                naf_code=detection.get("naf_code"),
                confidence_score=detection["confidence_score"],
                derived_from=detection.get("derived_from", "mix"),
                reasons_json=json.dumps(detection["reasons"], ensure_ascii=False),
            )
            self.db.add(profile)
            self.db.flush()
        except Exception:
            pass

    def _create_superuser(self, org):
        """Create demo admin user + 3 team members for realistic user list."""
        try:
            from models.iam import User, UserOrgRole, UserScope
            from models.enums import UserRole, ScopeLevel
            from services.iam_service import hash_password

            demo_users = [
                {"email": "promeos@promeos.io", "nom": "Admin", "prenom": "Promeos", "role": UserRole.DG_OWNER},
                {
                    "email": "m.leclerc@helios-energie.fr",
                    "nom": "Leclerc",
                    "prenom": "Marie",
                    "role": UserRole.ENERGY_MANAGER,
                },
                {"email": "j.dupont@helios-energie.fr", "nom": "Dupont", "prenom": "Jean", "role": UserRole.AUDITEUR},
                {
                    "email": "s.moreau@helios-energie.fr",
                    "nom": "Moreau",
                    "prenom": "Sophie",
                    "role": UserRole.RESP_SITE,
                },
            ]

            for u in demo_users:
                existing = self.db.query(User).filter_by(email=u["email"]).first()
                if existing:
                    continue

                user = User(
                    email=u["email"],
                    hashed_password=hash_password("promeos2024"),
                    nom=u["nom"],
                    prenom=u["prenom"],
                    actif=True,
                )
                self.db.add(user)
                self.db.flush()

                uor = UserOrgRole(user_id=user.id, org_id=org.id, role=u["role"])
                self.db.add(uor)
                self.db.flush()

                scope = UserScope(user_org_role_id=uor.id, scope_level=ScopeLevel.ORG, scope_id=org.id)
                self.db.add(scope)
                self.db.flush()
        except Exception:
            pass

    def _seed_kb_items(self):
        """Seed 15 Mémobox knowledge items for a credible demo."""
        from app.kb.store import KBStore

        store = KBStore()
        now = datetime.now(timezone.utc).isoformat()

        ITEMS = [
            {
                "id": "rule-bacs-290kw",
                "type": "rule",
                "domain": "reglementaire",
                "title": "BACS — Obligation GTB pour bâtiments > 290 kW",
                "summary": "Le décret BACS impose l'installation d'un système de GTB de classe A ou B pour tout bâtiment tertiaire dont la puissance CVC dépasse 290 kW, avant le 1er janvier 2025.",
                "content_md": "## Décret BACS (Building Automation & Control Systems)\n\n**Seuil** : 290 kW de puissance nominale CVC.\n\n**Obligation** : installer un système GTB de classe A ou B (norme EN 15232).\n\n**Échéance** : 1er janvier 2025 (bâtiments existants > 290 kW).\n\n**Sanctions** : Pas de sanction directe mais non-éligibilité aux aides CEE et risque de non-conformité OPERAT.",
                "tags": {"regulation": "bacs", "seuil": "290kW", "energie": "tous"},
                "confidence": "high",
                "priority": 1,
            },
            {
                "id": "rule-decret-tertiaire",
                "type": "rule",
                "domain": "reglementaire",
                "title": "Décret Tertiaire — Objectifs de réduction -40% à 2030",
                "summary": "Le décret tertiaire (éco-énergie tertiaire) impose une réduction des consommations énergétiques de -40% en 2030, -50% en 2040 et -60% en 2050 par rapport à une année de référence.",
                "content_md": "## Décret Tertiaire (DEET)\n\n**Périmètre** : Bâtiments tertiaires > 1000 m².\n\n**Objectifs** :\n- 2030 : -40% vs année de référence\n- 2040 : -50%\n- 2050 : -60%\n\n**Alternative** : Atteindre un seuil absolu en kWh/m²/an (valeurs CVC).\n\n**Déclaration** : Annuelle sur la plateforme OPERAT (ADEME).\n\n**Sanctions** : Amende administrative, name & shame.",
                "tags": {"regulation": "tertiaire", "operat": True, "seuil": "1000m2"},
                "confidence": "high",
                "priority": 1,
            },
            {
                "id": "rule-operat-declaration",
                "type": "knowledge",
                "domain": "reglementaire",
                "title": "OPERAT — Guide de déclaration annuelle",
                "summary": "La plateforme OPERAT de l'ADEME permet de déclarer les consommations énergétiques des bâtiments tertiaires. Chaque EFA (Entité Fonctionnelle Assujettie) doit être déclarée individuellement.",
                "content_md": "## Plateforme OPERAT\n\n**Accès** : operat.ademe.fr\n\n**Données requises** :\n- Surface utile par EFA\n- Consommations annuelles (tous vecteurs)\n- Année de référence\n- Activité exercée (catégorie OPERAT)\n\n**Délai** : Déclaration avant le 30 septembre de chaque année.\n\n**Astuce PROMEOS** : Utilisez l'export automatique depuis le module Patrimoine.",
                "tags": {"regulation": "operat", "ademe": True},
                "confidence": "high",
                "priority": 2,
            },
            {
                "id": "rule-aper-solaire",
                "type": "rule",
                "domain": "reglementaire",
                "title": "Loi APER — Obligation solaire sur parkings > 1 500 m²",
                "summary": "La loi APER impose l'installation de panneaux photovoltaïques ou de dispositifs d'ombrage sur les parkings extérieurs de plus de 1 500 m², avec un calendrier progressif.",
                "content_md": "## Loi APER (Accélération de la Production d'Énergies Renouvelables)\n\n**Seuil** :\n- Parkings > 1 500 m² : échéance 1er juillet 2026\n- Parkings > 10 000 m² : échéance 1er juillet 2025\n\n**Taux de couverture** : 50% minimum de la surface.\n\n**Alternatives** : Ombrières solaires, procédés de production d'EnR.\n\n**Exemptions** : Contraintes techniques, architecturales, patrimoniales.",
                "tags": {"regulation": "aper", "solaire": True, "parking": True},
                "confidence": "high",
                "priority": 2,
            },
            {
                "id": "kb-cee-valorisation",
                "type": "knowledge",
                "domain": "acc",
                "title": "CEE — Valorisation des certificats d'économie d'énergie",
                "summary": "Les CEE permettent de financer jusqu'à 25-40% des travaux d'efficacité énergétique. Les fiches standardisées BAT (bâtiment tertiaire) couvrent l'isolation, la GTB, l'éclairage LED et le CVC.",
                "content_md": "## Certificats d'Économie d'Énergie (CEE)\n\n**Principe** : Les obligés (fournisseurs d'énergie) financent des actions d'économie via des primes.\n\n**Fiches courantes** :\n- BAT-TH-116 : GTB/BACS\n- BAT-TH-104 : Robinets thermostatiques\n- BAT-EQ-133 : Éclairage LED\n- BAT-EN-101 : Isolation combles\n\n**Valorisation** : 4 à 8 €/MWhc selon le cours.\n\n**Astuce** : Cumulable avec MaPrimeRénov' Copropriété.",
                "tags": {"cee": True, "financement": True},
                "confidence": "high",
                "priority": 2,
            },
            {
                "id": "kb-autoconsommation",
                "type": "knowledge",
                "domain": "usages",
                "title": "Autoconsommation solaire — Dimensionnement et rentabilité",
                "summary": "L'autoconsommation photovoltaïque en tertiaire permet un TRI de 7-10 ans selon l'ensoleillement et le profil de charge. Le taux d'autoconsommation optimal vise 70-85%.",
                "content_md": "## Autoconsommation PV en tertiaire\n\n**Règle de dimensionnement** : Viser un taux d'autoconsommation de 70-85% pour maximiser la rentabilité.\n\n**Indicateurs clés** :\n- Productible : 900-1400 kWh/kWc/an selon la zone\n- LCOE : 60-90 €/MWh\n- TRI : 7-10 ans (sans stockage)\n\n**Bonnes pratiques** :\n- Aligner la puissance crête sur le talon de consommation\n- Privilégier les toitures orientées Sud ±30°\n- Coupler avec un contrat d'obligation d'achat pour le surplus",
                "tags": {"solaire": True, "autoconsommation": True, "pv": True},
                "confidence": "medium",
                "priority": 3,
            },
            {
                "id": "kb-flexibilite-effacement",
                "type": "knowledge",
                "domain": "flex",
                "title": "Flexibilité — Mécanismes d'effacement et valorisation",
                "summary": "L'effacement de consommation permet de valoriser la flexibilité des bâtiments tertiaires sur les marchés de capacité et d'ajustement, avec des revenus de 5-15 k€/MW/an.",
                "content_md": "## Effacement et flexibilité\n\n**Mécanismes** :\n- Mécanisme de capacité : Obligation annuelle, certifiée par RTE\n- Appel d'offres effacement : NEBCO (valorisation sur le marché spot)\n- Réserves rapides : aFRR / mFRR via agrégateur\n\n**Potentiel tertiaire** :\n- CVC : 20-40% de la puissance pendant 2-4h\n- Éclairage : 10-15% en heures creuses\n- Process léger : variable\n\n**Revenus** : 5 000 à 15 000 €/MW/an selon le mécanisme.",
                "tags": {"flexibilite": True, "effacement": True, "rte": True},
                "confidence": "medium",
                "priority": 3,
            },
            {
                "id": "kb-arenh-fin",
                "type": "knowledge",
                "domain": "acc",
                "title": "Post-ARENH / VNU — Nouveau cadre de marché depuis 2026",
                "summary": "L'ARENH (42 €/MWh) a pris fin le 31/12/2025. Remplacé par le VNU (Versement Nucléaire Universel) au 01/01/2026. EDF vend 100% du nucléaire au marché. Le VNU est une taxe redistributive activée uniquement si prix > 78 €/MWh (seuil 1) ou > 110 €/MWh (seuil 2). Prix marché actuel ~60 €/MWh → VNU dormant.",
                "content_md": "## Post-ARENH / VNU — Cadre 2026+\n\n**Contexte** : L'ARENH (42 €/MWh, 100 TWh/an) a pris fin le 31/12/2025.\n\n**VNU (depuis 01/01/2026)** :\n- EDF vend 100% du nucléaire au prix de marché\n- VNU = taxe sur EDF redistribuée universellement si prix > seuils\n- Seuil 1 : 78 €/MWh — Seuil 2 : ~110 €/MWh\n- Prix marché actuel ~60 €/MWh → VNU dormant (au moins jusqu'en 2028)\n- Révision triennale des seuils par la CRE\n\n**Impact entreprises** :\n- Exposition directe au marché (fin du prix garanti 42 €/MWh)\n- Couverture à long terme recommandée (PPA, contrats forward)\n- VNU protège uniquement en cas de flambée > 78 €/MWh\n\n**Recommandation PROMEOS** : Diversifier les stratégies d'achat (PPA, autoconsommation, flexibilité).",
                "tags": {"arenh": True, "vnu": True, "prix": True, "marche": True},
                "confidence": "medium",
                "priority": 2,
            },
            {
                "id": "kb-facture-turpe",
                "type": "knowledge",
                "domain": "facturation",
                "title": "TURPE 6 — Comprendre les composantes du tarif réseau",
                "summary": "Le TURPE (Tarif d'Utilisation des Réseaux Publics d'Électricité) représente 25-35% d'une facture d'électricité tertiaire. Le TURPE 6 HTA est en vigueur depuis août 2023.",
                "content_md": "## TURPE 6 — Tarif réseau\n\n**Composantes** :\n- CG : Composante de gestion (fixe, ~10 €/mois)\n- CC : Composante de comptage (fixe)\n- CS : Composante de soutirage (variable, €/kWh par poste horosaisonnier)\n- CMDPS : Composante de dépassement de puissance souscrite\n\n**Segments tarifaires** :\n- C5 : ≤ 36 kVA (petits sites)\n- C4 : > 36 kVA en BT (bureaux, commerces)\n- C3 : HTA courte utilisation\n- C2 : HTA longue utilisation\n\n**Astuce** : Optimiser la puissance souscrite évite les CMDPS (pénalité x2).",
                "tags": {"turpe": True, "facturation": True, "reseau": True},
                "confidence": "high",
                "priority": 2,
            },
            {
                "id": "kb-shadow-billing",
                "type": "checklist",
                "domain": "facturation",
                "title": "Facturation théorique — Checklist de vérification",
                "summary": "La facturation théorique (shadow billing) reconstruit le montant attendu de chaque facture à partir des index de consommation et des grilles tarifaires. Checklist des points de contrôle.",
                "content_md": "## Checklist facturation théorique\n\n- [ ] Vérifier la cohérence index compteur vs relevé fournisseur\n- [ ] Contrôler le segment tarifaire (C2/C3/C4/C5)\n- [ ] Valider la puissance souscrite vs puissance atteinte\n- [ ] Recalculer le TURPE poste par poste (HPH, HCH, HPE, HCE, P)\n- [ ] Vérifier le taux CTA (27,04% de la part fixe TURPE HTA)\n- [ ] Vérifier le taux d'accise (ex-CSPE + TICFE) : 21 €/MWh\n- [ ] Contrôler la TVA : 5,5% sur abonnement, 20% sur consommation\n- [ ] Comparer total théorique vs total facturé (seuil alerte : ±5%)",
                "tags": {"facturation": True, "shadow_billing": True, "checklist": True},
                "confidence": "high",
                "priority": 1,
            },
            {
                "id": "kb-gtb-roi",
                "type": "knowledge",
                "domain": "usages",
                "title": "GTB — ROI et bonnes pratiques d'installation",
                "summary": "Une GTB de classe A permet 20-30% d'économies sur le CVC. Le ROI est de 3-5 ans pour un investissement de 15-40 €/m² selon la complexité du bâtiment.",
                "content_md": "## GTB (Gestion Technique du Bâtiment)\n\n**Classes EN 15232** :\n- Classe D : Pas d'automatisation\n- Classe C : Automatisation standard\n- Classe B : Automatisation avancée (BACS)\n- Classe A : Haute performance énergétique\n\n**Économies attendues** :\n- Classe C → B : 10-15% sur le CVC\n- Classe C → A : 20-30% sur le CVC\n\n**Investissement** : 15-40 €/m² (équipements + intégration)\n\n**ROI** : 3-5 ans (hors CEE)\n\n**Prérequis** : Comptage par zone, capteurs T°/HR, actionneurs CVC.",
                "tags": {"gtb": True, "bacs": True, "cvc": True},
                "confidence": "high",
                "priority": 2,
            },
            {
                "id": "kb-qualite-donnees",
                "type": "checklist",
                "domain": "usages",
                "title": "Qualité des données — Checklist de diagnostic",
                "summary": "Une base de données énergétiques fiable est le prérequis de toute analyse. Checklist des contrôles qualité à effectuer avant toute exploitation.",
                "content_md": "## Checklist qualité des données\n\n- [ ] Couverture temporelle : au moins 12 mois glissants par site\n- [ ] Granularité : courbe de charge 10 min ou horaire\n- [ ] Complétude : < 5% de trous (données manquantes)\n- [ ] Cohérence : pas de valeurs négatives ou > 3× la médiane\n- [ ] Concordance : index compteur vs données télérelevées\n- [ ] Météo : données DJU disponibles pour la normalisation\n- [ ] Surface : surface utile renseignée (pas surface SHON)\n- [ ] Activité : horaires d'occupation documentés",
                "tags": {"qualite": True, "donnees": True, "diagnostic": True},
                "confidence": "high",
                "priority": 1,
            },
            {
                "id": "kb-contrat-couverture",
                "type": "knowledge",
                "domain": "acc",
                "title": "Stratégies de couverture — Prix fixe vs indexé",
                "summary": "Le choix entre contrat à prix fixe et contrat indexé dépend de l'appétence au risque et de l'horizon. Un mix 60% fixe / 40% indexé offre un bon compromis risque-rendement.",
                "content_md": "## Stratégies de couverture\n\n**Prix fixe** :\n- Avantage : Budget prévisible, protection contre la hausse\n- Inconvénient : Prime de risque intégrée (+5-15%)\n- Idéal pour : Profils risque-averse, budgets publics\n\n**Indexé marché** :\n- Avantage : Bénéficie des baisses, prix moyen plus bas\n- Inconvénient : Volatilité, budget imprévisible\n- Idéal pour : Profils flexibles, trésorerie confortable\n\n**Mix recommandé** : 60% fixe + 40% indexé sur 24-36 mois.\n\n**PPA** : Contrat long terme (10-20 ans) à prix garanti avec producteur EnR.",
                "tags": {"contrat": True, "couverture": True, "achat": True},
                "confidence": "medium",
                "priority": 3,
            },
            {
                "id": "kb-iso50001",
                "type": "knowledge",
                "domain": "usages",
                "title": "ISO 50001 — Système de management de l'énergie",
                "summary": "La norme ISO 50001 structure la démarche d'amélioration continue de la performance énergétique. Elle exempte du dispositif d'audit énergétique obligatoire pour les grandes entreprises.",
                "content_md": "## ISO 50001\n\n**Principe** : Cycle PDCA (Plan-Do-Check-Act) appliqué à l'énergie.\n\n**Bénéfices** :\n- Exemption d'audit énergétique obligatoire (art. L233-1 Code énergie)\n- Réduction de 10-20% des consommations en 3 ans\n- Éligibilité bonifiée aux CEE\n- Image RSE\n\n**Prérequis** :\n- Revue énergétique initiale\n- Indicateurs de performance (IPÉ/EnPI)\n- Objectifs et cibles quantifiés\n- Plan de mesurage\n\n**Coût certification** : 5-15 k€/an (audit externe).",
                "tags": {"iso50001": True, "management": True, "certification": True},
                "confidence": "high",
                "priority": 3,
            },
            {
                "id": "kb-pointe-puissance",
                "type": "rule",
                "domain": "facturation",
                "title": "Optimisation puissance souscrite — Règle des 5%",
                "summary": "La puissance souscrite doit être dimensionnée au plus juste : un dépassement ponctuel coûte 2× le tarif normal (CMDPS), mais un surdimensionnement gaspille l'abonnement fixe.",
                "content_md": "## Optimisation de la puissance souscrite\n\n**Règle PROMEOS** : La puissance souscrite optimale = P90 de la courbe de charge + 5% de marge.\n\n**Risques** :\n- Sous-dimensionnement : CMDPS à 2× le tarif → surcoût immédiat\n- Surdimensionnement : Abonnement fixe trop élevé → 500-2000 €/an gaspillés\n\n**Calcul** :\n1. Extraire la courbe de charge 10 min sur 12 mois\n2. Calculer le percentile 90 (P90)\n3. Ajouter 5% de marge de sécurité\n4. Arrondir au palier supérieur du TURPE\n\n**Fréquence de révision** : Annuelle ou après tout changement d'équipement.",
                "tags": {"puissance": True, "turpe": True, "optimisation": True},
                "confidence": "high",
                "priority": 1,
            },
            # ── Phase 5 : Items KB réglementaires DT enrichis ──────────────
            {
                "id": "reg-sanctions-cch-l174",
                "type": "rule",
                "domain": "reglementaire",
                "title": "Sanctions DT — Code de la construction Art. L174-1",
                "summary": "Pénalités administratives pour non-conformité au Décret Tertiaire : 7 500 EUR pour non-déclaration OPERAT, 1 500 EUR pour non-affichage de l'attestation. Publication name & shame sur le site ADEME.",
                "content_md": "## Sanctions Décret Tertiaire\n\n**Art. L174-1 Code de la construction** :\n- Non-déclaration OPERAT : **7 500 EUR** d'amende administrative\n- Non-affichage attestation : **1 500 EUR**\n- Name & shame : Publication sur le site de l'ADEME\n\n**Procédure** :\n1. Mise en demeure par le préfet (délai 3 mois)\n2. Amende administrative si non-régularisation\n3. Publication du nom de l'assujetti défaillant\n\n**Calcul PROMEOS** : Risque = 7 500 × nb(NON_CONFORME) + 3 750 × nb(A_RISQUE)",
                "tags": {"regulation": "tertiaire", "sanctions": True, "penalites": True},
                "confidence": "high",
                "priority": 1,
            },
            {
                "id": "reg-arrete-2020-04-10",
                "type": "rule",
                "domain": "reglementaire",
                "title": "Arrêté du 10 avril 2020 — Modalités DT",
                "summary": "Définit les catégories d'activité OPERAT, les valeurs absolues (Cabs), les modalités de déclaration, les cas de modulation et l'ajustement climatique DJU.",
                "content_md": "## Arrêté du 10 avril 2020\n\n**Contenu clé** :\n- Art. 2 : Définition de l'EFA (Entité Fonctionnelle Assujettie)\n- Art. 3 : Année de référence (2010-2020), déclaration annuelle sur OPERAT\n- Art. 4 : Rénovation majeure → nouvelle année de référence possible\n- Art. 5 : Affichage public de l'attestation (depuis 01/07/2026)\n- Art. 6-2 : Dossier de modulation (dépôt avant 30/09/2026)\n- Annexe I : Nomenclature catégories d'activité OPERAT\n- Annexe II : Indicateur d'Intensité d'Usage (IIU)\n- Annexe VI : Valeurs absolues Cabs par catégorie + zone climatique\n\n**URL** : legifrance.gouv.fr/jorf/id/JORFTEXT000041842389",
                "tags": {"regulation": "tertiaire", "arrete": True, "modulation": True, "cabs": True},
                "confidence": "high",
                "priority": 1,
            },
            {
                "id": "kb-dt-modulation",
                "type": "knowledge",
                "domain": "reglementaire",
                "title": "Modulation DT — Préparer son dossier avant le 30/09/2026",
                "summary": "Un assujetti peut demander un ajustement de son objectif DT s'il justifie de contraintes techniques, architecturales ou de disproportion économique. Le dossier doit être déposé sur OPERAT.",
                "content_md": "## Dossier de modulation — Décret Tertiaire\n\n**Base légale** : Arrêté du 10 avril 2020, Art. 6-2\n\n**Cas de modulation** :\n- Contrainte technique : impossibilité d'isoler (bâtiment classé, etc.)\n- Contrainte architecturale : patrimoine historique\n- Disproportion économique : TRI > seuil raisonnable\n\n**Pièces du dossier** :\n1. Périmètre précis (EFA + surface)\n2. Données de consommation fiables (couverture > 80%)\n3. Actions déjà engagées avec justificatifs\n4. Justification technique par contrainte\n5. Calcul TRI par action envisagée\n6. Cohérence avec la stratégie patrimoniale\n\n**Deadline** : 30 septembre 2026\n\n**Astuce PROMEOS** : Utilisez le simulateur de modulation pour évaluer votre score de readiness.",
                "tags": {"regulation": "tertiaire", "modulation": True, "deadline": True},
                "confidence": "high",
                "priority": 1,
            },
            {
                "id": "kb-dt-mutualisation",
                "type": "knowledge",
                "domain": "reglementaire",
                "title": "Mutualisation DT — Compenser entre sites du même portefeuille",
                "summary": "La mutualisation permet d'évaluer la conformité au niveau du portefeuille plutôt que site par site. Un site performant compense un site en retard. Fonctionnalité prévue dans OPERAT.",
                "content_md": "## Mutualisation — Décret Tertiaire\n\n**Base légale** : Décret n°2019-771, Art. 3\n\n**Principe** :\n- Un propriétaire avec N sites peut compenser les sites en déficit avec les sites en surplus\n- L'objectif est évalué au niveau portefeuille (somme des écarts)\n- Si le portefeuille est conforme en mutualisé, aucune pénalité\n\n**Calcul** :\n- Par site : écart = conso_actuelle - objectif_kwh\n- Portefeuille : écart_total = Σ(écart par site)\n- Conforme si écart_total ≤ 0\n\n**Économie** :\n- Sans mutualisation : 7 500 € × nb sites en déficit\n- Avec mutualisation : 7 500 € si déficit résiduel, sinon 0 €\n\n**Statut OPERAT** : Fonctionnalité non encore disponible — PROMEOS permet de l'anticiper.\n\n**Astuce** : Le simulateur PROMEOS calcule l'économie potentielle en 1 clic.",
                "tags": {"regulation": "tertiaire", "mutualisation": True, "portefeuille": True},
                "confidence": "high",
                "priority": 1,
            },
        ]

        seeded = 0
        for item in ITEMS:
            item["updated_at"] = now
            item["status"] = "validated"
            if store.upsert_item(item):
                seeded += 1

        # Also index items for FTS5 search
        try:
            from app.kb.indexer import KBIndexer

            indexer = KBIndexer()
            indexer.rebuild_index()
        except Exception:
            pass  # indexer may not be available
