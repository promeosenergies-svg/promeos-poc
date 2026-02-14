"""
PROMEOS - Point d'entrée principal de l'API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Run safe schema migrations (idempotent, no drop)
from database import engine as _engine, run_migrations as _run_migrations
_run_migrations(_engine)

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
