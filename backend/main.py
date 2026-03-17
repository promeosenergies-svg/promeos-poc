"""
PROMEOS - Point d'entrée principal de l'API
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from middleware.request_context import RequestContextMiddleware
from services.json_logger import setup_logging

# Structured JSON logging
setup_logging()

# Import des routes
from routes import (
    sites_router,
    compteurs_router,
    consommations_router,
    alertes_router,
    cockpit_router,
    compliance_router,
    demo_router,
    guidance_router,
    regops_router,
    connectors_router,
    watchers_router,
    ai_router,
    kb_usages_router,
    energy_router,
    monitoring_router,
    onboarding_router,
    import_router,
    dashboard_2min_router,
    segmentation_router,
    consumption_diag_router,
    site_config_router,
    billing_router,
    purchase_router,
    actions_router,
    reports_router,
    notifications_router,
    auth_router,
    admin_users_router,
    patrimoine_router,
    intake_router,
    bacs_router,
    ems_router,
    dev_tools_router,
    flex_router,
    tertiaire_router,
    portfolio_router,
    consumption_context_router,
    contracts_radar_router,
    data_quality_router,
    operat_router,
    copilot_router,
    action_templates_router,
    onboarding_stepper_router,
    consumption_unified_router,
    market_router,
    referentiel_router,
    patrimoine_crud_router,
    aper_router,
    geocoding_router,
    usages_router,
)

# Import KB router
from app.kb.router import router as kb_router

# Import Bill Intelligence router
from app.bill_intelligence.router import router as bill_router

# Créer l'application FastAPI (lifespan assigned after startup funcs are defined)
app = FastAPI(
    title="PROMEOS API",
    description="API de gestion énergétique multi-sites - 120 sites",
    version="1.0.0",
)

# Request context middleware (request_id + timing) — must be added before CORS
app.add_middleware(RequestContextMiddleware)

# Configuration CORS — restrict origins in production, wildcard in demo mode
_DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() in ("true", "1", "yes")
if _DEMO_MODE:
    _CORS_ORIGINS = ["*"]
else:
    _CORS_ORIGINS = os.environ.get(
        "PROMEOS_CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
    ).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=not _DEMO_MODE,  # credentials not supported with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Response-Time"],
)

# Enregistrer les routes
app.include_router(sites_router)
app.include_router(compteurs_router)
app.include_router(consommations_router)
app.include_router(alertes_router)
app.include_router(cockpit_router)
app.include_router(compliance_router)
app.include_router(demo_router)
app.include_router(guidance_router)
app.include_router(regops_router)
app.include_router(connectors_router)
app.include_router(watchers_router)
app.include_router(ai_router)
app.include_router(kb_router)  # Knowledge Base (generic)
app.include_router(kb_usages_router)  # KB Usages (archetypes, rules, recommendations)
app.include_router(energy_router)  # Energy (import, analysis)
app.include_router(bill_router)  # Bill Intelligence (audit, shadow billing)
app.include_router(monitoring_router)  # Electric Monitoring (KPIs, alerts, risk)
app.include_router(onboarding_router)  # Onboarding B2B (org, sites, CSV import)
app.include_router(import_router)  # Import CSV standalone
app.include_router(dashboard_2min_router)  # Dashboard 2 minutes
app.include_router(segmentation_router)  # Segmentation B2B (profil, questionnaire)
app.include_router(consumption_diag_router)  # Diagnostic consommation V1
app.include_router(site_config_router)  # Site config (schedule, tariff)
app.include_router(billing_router)  # Bill Intelligence V2 (CSV import, shadow billing, anomaly engine)
app.include_router(purchase_router)  # Achat Energie V1 (scenarios fixe/indexe/spot)
app.include_router(actions_router)  # Action Hub V1 (unified actions from all briques)
app.include_router(reports_router)  # Reports (audit PDF, audit JSON)
app.include_router(notifications_router)  # Notifications & Alert Center V1
app.include_router(auth_router)  # IAM Auth (login, me, refresh, logout, password, switch-org)
app.include_router(admin_users_router)  # IAM Admin (CRUD users, roles, scopes)
app.include_router(patrimoine_router)  # Patrimoine DIAMANT (staging, quality gate, activation)
app.include_router(intake_router)  # Smart Intake DIAMANT (questions, answers, before/after)
app.include_router(bacs_router)  # BACS Expert (Decret n°2020-887)
app.include_router(ems_router)  # EMS Consumption Explorer
app.include_router(flex_router)  # Flex Mini V0 (demand-side flexibility)
if os.environ.get("PROMEOS_ENV") != "production":
    app.include_router(dev_tools_router)  # Dev Tools (reset_db)
app.include_router(tertiaire_router)  # Tertiaire / OPERAT V39 (EFA, controls, precheck, export)
app.include_router(portfolio_router)  # Portfolio Consumption (multi-site B2B view)
app.include_router(consumption_context_router)  # Consumption Context V0 (usages & horaires)
app.include_router(contracts_radar_router)  # V99 Contract Renewal Radar + Purchase Scenarios
app.include_router(data_quality_router)  # V113 Data Quality Dashboard
app.include_router(operat_router)  # V113 OPERAT CSV Export
app.include_router(copilot_router)  # V113 Energy Copilot
app.include_router(action_templates_router)  # V113 Action Templates
app.include_router(onboarding_stepper_router)  # V113 Onboarding Stepper
app.include_router(consumption_unified_router)  # A.1 Unified Consumption (metered/billed/reconciled)
app.include_router(market_router)  # M.1 Market Prices (EPEX Spot FR)
app.include_router(referentiel_router)  # M.2 Référentiel Tarifs (TURPE/taxes YAML)
app.include_router(patrimoine_crud_router)  # O.3 CRUD Organisation/Entité/Portefeuille/Site
app.include_router(geocoding_router)  # Géocodage BAN (sites → lat/lng)
app.include_router(aper_router)  # Step 29 APER Solarisation (parkings & toitures)
app.include_router(usages_router)  # V1.1 Usage (readiness, metering plan, UES, cost breakdown)

# Run safe schema migrations (idempotent, no drop)
from database import engine as _engine, run_migrations as _run_migrations

_run_migrations(_engine)

# Startup route validation: verify critical V67 billing routes are registered
_REQUIRED_BILLING_PATHS = ["/api/billing/periods", "/api/billing/coverage-summary", "/api/billing/missing-periods"]
_registered = {r.path for r in app.routes}
_missing = [p for p in _REQUIRED_BILLING_PATHS if p not in _registered]
if _missing:
    import logging

    logging.getLogger("promeos").error(
        f"[STARTUP] CRITICAL: billing routes missing from app: {_missing}. Restart uvicorn."
    )
else:
    import logging

    logging.getLogger("promeos").info(f"[STARTUP] Billing V67 routes OK ({len(_REQUIRED_BILLING_PATHS)} verified)")


async def _startup_restore_or_seed_helios():
    """Restore DemoState or seed HELIOS if DEMO_MODE=true.

    Uses run_in_executor to avoid blocking the async event loop
    and sets a SQLite busy_timeout to prevent deadlocks with uvicorn reloader.
    """
    if os.environ.get("PROMEOS_DEMO_MODE", "false").lower() != "true":
        return
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if os.environ.get("SKIP_STARTUP_SEED"):
        return

    import asyncio

    await asyncio.get_event_loop().run_in_executor(None, _sync_restore_or_seed_helios)


def _sync_restore_or_seed_helios():
    """Synchronous helper — restores DemoState from existing DB.

    The actual seed must be done via CLI: python -m services.demo_seed --pack helios --size S --reset
    This function only reads the DB to restore in-memory DemoState after server restart.
    This avoids SQLite deadlocks with uvicorn --reload (reloader + worker both run lifespan).
    """
    from database import SessionLocal
    from services.demo_state import DemoState
    import logging

    logger = logging.getLogger("promeos.startup")

    if DemoState.get_demo_org_id():
        return

    db = SessionLocal()
    try:
        # Set SQLite busy timeout to avoid contention with reloader process
        from sqlalchemy import text

        db.execute(text("PRAGMA busy_timeout = 5000"))

        from models import Organisation, Site, Portefeuille, EntiteJuridique

        demo_org = (
            db.query(Organisation)
            .filter(Organisation.actif == True, Organisation.is_demo == True)
            .order_by(Organisation.id.desc())
            .first()
        )

        if demo_org:
            pf_ids = [
                row.id
                for row in (
                    db.query(Portefeuille.id)
                    .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
                    .filter(EntiteJuridique.organisation_id == demo_org.id)
                    .all()
                )
            ]
            sites_q = db.query(Site).filter(Site.portefeuille_id.in_(pf_ids), Site.actif == True)
            sites_count = sites_q.count()
            first_site = sites_q.first()
            DemoState.set_demo_org(
                org_id=demo_org.id,
                org_nom=demo_org.nom,
                pack="helios",
                size="S",
                sites_count=sites_count,
                default_site_id=first_site.id if first_site else None,
                default_site_name=first_site.nom if first_site else None,
            )
            logger.info(f"[startup] DemoState restored: {demo_org.nom} ({sites_count} sites)")
        else:
            logger.warning(
                "[startup] No demo org found. Run: python -m services.demo_seed --pack helios --size S --reset"
            )
    except Exception as exc:
        logger.warning(f"[startup] HELIOS restore failed (non-bloquant): {exc}")
    finally:
        db.close()


async def _startup_seed_hourly_if_missing():
    """Auto-seed hourly data if only monthly exists (for diagnostics)."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return

    from database import SessionLocal
    from sqlalchemy import text
    import logging

    db = SessionLocal()
    try:
        hourly_count = db.execute(text("SELECT COUNT(*) FROM meter_reading WHERE frequency = 'HOURLY'")).scalar()
        if hourly_count and hourly_count > 0:
            return

        from models import Site

        sites = db.query(Site).filter(Site.actif == True).limit(5).all()
        if not sites:
            return

        from services.consumption_diagnostic import generate_demo_consumption

        seeded = 0
        for site in sites:
            try:
                result = generate_demo_consumption(db, site.id, days=90)
                if result and not result.get("error"):
                    seeded += 1
            except Exception as exc:
                logging.getLogger("promeos.startup").debug(f"[startup] Site {site.id} seed failed: {exc}")

        if seeded > 0:
            logging.getLogger("promeos.startup").info(
                f"[startup] Auto-seeded hourly consumption for {seeded} sites (90 days each)"
            )
    except Exception as exc:
        logging.getLogger("promeos.startup").warning(f"[startup] Hourly seed failed (non-bloquant): {exc}")
    finally:
        db.close()


# Lifespan context manager (replaces deprecated @app.on_event("startup"))
@asynccontextmanager
async def _lifespan(app):
    await _startup_restore_or_seed_helios()
    await _startup_seed_hourly_if_missing()
    yield


app.router.lifespan_context = _lifespan


# Route racine
@app.get("/")
def root():
    return {
        "message": "Bienvenue sur l'API PROMEOS 🔥",
        "version": "1.0.0",
        "sites": 120,
        "docs": "/docs",
        "health": "/health",
    }


# Health check
@app.get("/api/health")
def api_health():
    import logging, subprocess, datetime
    from sqlalchemy import text
    from database import SessionLocal

    _logger = logging.getLogger("promeos.health")

    git_sha = "unknown"
    try:
        git_sha = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(__file__),
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        _logger.debug("Could not resolve git SHA", exc_info=True)

    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception:
        _logger.error("Health check DB connectivity failed", exc_info=True)

    return {
        "ok": db_ok,
        "version": "1.0.0",
        "git_sha": git_sha,
        "db": "ok" if db_ok else "error",
        "time": datetime.datetime.now(datetime.UTC).isoformat(),
        "engine_versions": {
            "compliance": "1.0",
            "bacs": "bacs_v2.0",
        },
    }


@app.get("/api/meta/version")
def api_meta_version():
    """V69: Git sha + branch — visible en mode Expert."""
    import subprocess, datetime

    git_sha, branch = "unknown", "unknown"
    try:
        git_sha = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(__file__),
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=os.path.dirname(__file__),
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        pass
    return {
        "sha": git_sha,
        "branch": branch,
        "build_time": datetime.datetime.now(datetime.UTC).isoformat(),
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Backend PROMEOS opérationnel", "version": "1.0.0"}


# Lancement du serveur
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=int(os.environ.get("PORT", 8001)), reload=True, log_level="info")
