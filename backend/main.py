"""
PROMEOS - Point d'entrée principal de l'API
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from middleware.request_context import RequestContextMiddleware
from services.json_logger import setup_logging

# Structured JSON logging
setup_logging()

# Import des routes
from routes import (
    sites_router, compteurs_router, consommations_router, alertes_router,
    cockpit_router, compliance_router, demo_router, guidance_router,
    regops_router, connectors_router, watchers_router, ai_router,
    kb_usages_router, energy_router, monitoring_router, onboarding_router,
    import_router, dashboard_2min_router, segmentation_router,
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
)

# Import KB router
from app.kb.router import router as kb_router

# Import Bill Intelligence router
from app.bill_intelligence.router import router as bill_router

# Créer l'application FastAPI
app = FastAPI(
    title="PROMEOS API",
    description="API de gestion énergétique multi-sites - 120 sites",
    version="1.0.0"
)

# Request context middleware (request_id + timing) — must be added before CORS
app.add_middleware(RequestContextMiddleware)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
app.include_router(dev_tools_router)  # Dev Tools (reset_db)
app.include_router(tertiaire_router)  # Tertiaire / OPERAT V39 (EFA, controls, precheck, export)

# Run safe schema migrations (idempotent, no drop)
from database import engine as _engine, run_migrations as _run_migrations
_run_migrations(_engine)


@app.on_event("startup")
async def restore_or_seed_helios():
    """
    Au démarrage : si DEMO_MODE=true, restaurer DemoState depuis la DB
    (org is_demo=True existante) ou seeder HELIOS fresh si aucune org demo.
    Idempotent — ne re-seed pas si une org demo existe déjà en DB.
    """
    if os.environ.get("PROMEOS_DEMO_MODE", "false").lower() != "true":
        return
    # Never run during pytest — test fixtures manage their own DB isolation
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return

    from database import SessionLocal
    from services.demo_state import DemoState

    if DemoState.get_demo_org_id():
        return  # DemoState déjà rempli (ex: test ou rechargement uvicorn)

    db = SessionLocal()
    try:
        from models import Organisation, Site, Portefeuille, EntiteJuridique
        demo_org = (db.query(Organisation)
            .filter(Organisation.actif == True, Organisation.is_demo == True)
            .order_by(Organisation.id.desc())
            .first())

        if demo_org:
            # Re-register après restart — pas de re-seed
            pf_ids = [row.id for row in (
                db.query(Portefeuille.id)
                .join(EntiteJuridique,
                      Portefeuille.entite_juridique_id == EntiteJuridique.id)
                .filter(EntiteJuridique.organisation_id == demo_org.id)
                .all()
            )]
            sites_q = db.query(Site).filter(
                Site.portefeuille_id.in_(pf_ids), Site.actif == True
            )
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
        else:
            # Fresh seed — premier démarrage, DB vide
            from services.demo_seed import SeedOrchestrator
            import logging
            logging.getLogger("promeos.startup").info(
                "[startup] Seeding HELIOS demo data..."
            )
            orch = SeedOrchestrator(db)
            orch.seed(pack="helios", size="S", rng_seed=42)
    except Exception as exc:
        import logging
        logging.getLogger("promeos.startup").warning(
            f"[startup] HELIOS init failed (non-bloquant): {exc}"
        )
    finally:
        db.close()


# Route racine
@app.get("/")
def root():
    return {
        "message": "Bienvenue sur l'API PROMEOS 🔥",
        "version": "1.0.0",
        "sites": 120,
        "docs": "/docs",
        "health": "/health"
    }

# Health check
@app.get("/api/health")
def api_health():
    import subprocess, datetime
    git_sha = "unknown"
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        pass
    return {
        "ok": True,
        "version": "1.0.0",
        "git_sha": git_sha,
        "time": datetime.datetime.now(datetime.UTC).isoformat(),
        "engine_versions": {
            "compliance": "1.0",
            "bacs": "bacs_v2.0",
        },
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Backend PROMEOS opérationnel",
        "version": "1.0.0"
    }

# Lancement du serveur
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
