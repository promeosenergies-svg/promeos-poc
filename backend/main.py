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
    kb_usages_router, energy_router
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
