"""
PROMEOS — Action Templates routes (Chantier 4)
GET  /api/action-templates         — list all templates
POST /api/action-templates/seed    — seed 20 default templates
GET  /api/action-templates/{code}  — single template detail
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.action_template import ActionTemplate

router = APIRouter(prefix="/api/action-templates", tags=["action-templates"])

# ── 20 action templates MVP ──────────────────────────────────────────────────
DEFAULT_TEMPLATES = [
    # Energie
    {
        "code": "TPL_ECLAIRAGE_LED",
        "title": "Remplacement eclairage LED",
        "description": "Remplacer les tubes fluorescents par des LED T5/T8. ROI typique 2-3 ans.",
        "category": "energie",
        "priority": 2,
        "estimated_gain_kwh": 15000,
        "estimated_gain_eur": 2700,
        "complexity": "simple",
        "typical_duration_days": 30,
        "tags": "eclairage,led,renovation",
        "typical_gain_pct": 12.0,
        "typical_cost_range": "3000-8000 EUR",
        "confidence_level": "high",
        "regulatory_link": "https://www.ecologie.gouv.fr/politiques-publiques/decret-tertiaire",
    },
    {
        "code": "TPL_VEILLE_EQUIPEMENTS",
        "title": "Coupure veille equipements",
        "description": "Installer des prises programmables ou coupe-veille pour les equipements bureautiques.",
        "category": "energie",
        "priority": 3,
        "estimated_gain_kwh": 5000,
        "estimated_gain_eur": 900,
        "complexity": "simple",
        "typical_duration_days": 14,
        "tags": "veille,bureautique",
        "typical_gain_pct": 3.5,
        "typical_cost_range": "200-500 EUR",
        "confidence_level": "high",
    },
    {
        "code": "TPL_REGLAGE_CVC",
        "title": "Optimisation reglage CVC",
        "description": "Ajuster les consignes de temperature (19C hiver, 26C ete) et les plages horaires de fonctionnement.",
        "category": "energie",
        "priority": 2,
        "estimated_gain_kwh": 20000,
        "estimated_gain_eur": 3600,
        "complexity": "medium",
        "typical_duration_days": 7,
        "tags": "cvc,chauffage,climatisation",
        "typical_gain_pct": 15.0,
        "typical_cost_range": "0-500 EUR",
        "confidence_level": "high",
    },
    {
        "code": "TPL_ISOLATION_COMBLES",
        "title": "Isolation des combles",
        "description": "Isoler les combles perdus (laine de verre/roche 300mm). Eligible CEE.",
        "category": "energie",
        "priority": 2,
        "estimated_gain_kwh": 30000,
        "estimated_gain_eur": 5400,
        "complexity": "complex",
        "typical_duration_days": 60,
        "tags": "isolation,combles,cee",
        "typical_gain_pct": 20.0,
        "typical_cost_range": "15000-40000 EUR",
        "confidence_level": "medium",
        "regulatory_link": "https://www.ecologie.gouv.fr/politiques-publiques/certificats-economies-denergie",
    },
    {
        "code": "TPL_VARIATEURS_VITESSE",
        "title": "Variateurs de vitesse moteurs",
        "description": "Installer des variateurs de frequence sur les moteurs CVC (pompes, ventilateurs).",
        "category": "energie",
        "priority": 2,
        "estimated_gain_kwh": 25000,
        "estimated_gain_eur": 4500,
        "complexity": "medium",
        "typical_duration_days": 45,
        "tags": "moteurs,variateur,cvc",
        "typical_gain_pct": 18.0,
        "typical_cost_range": "5000-15000 EUR",
        "confidence_level": "medium",
    },
    # Talon / Base load
    {
        "code": "TPL_EXTINCTION_NUIT",
        "title": "Programmation extinction nuit",
        "description": "Programmer l'arret des equipements non essentiels entre 20h et 6h.",
        "category": "talon",
        "priority": 2,
        "estimated_gain_kwh": 10000,
        "estimated_gain_eur": 1800,
        "complexity": "simple",
        "typical_duration_days": 7,
        "tags": "talon,nuit,programmation",
    },
    {
        "code": "TPL_DETECTION_PRESENCE",
        "title": "Detecteurs de presence",
        "description": "Installer des detecteurs de presence dans les zones de passage (couloirs, sanitaires).",
        "category": "talon",
        "priority": 3,
        "estimated_gain_kwh": 8000,
        "estimated_gain_eur": 1440,
        "complexity": "simple",
        "typical_duration_days": 21,
        "tags": "eclairage,detecteur,presence",
    },
    {
        "code": "TPL_COUPURE_WEEKEND",
        "title": "Arret CVC week-end",
        "description": "Programmer l'arret du chauffage/clim pendant les week-ends et jours feries.",
        "category": "talon",
        "priority": 2,
        "estimated_gain_kwh": 12000,
        "estimated_gain_eur": 2160,
        "complexity": "simple",
        "typical_duration_days": 3,
        "tags": "cvc,weekend,programmation",
    },
    # Conformite
    {
        "code": "TPL_AUDIT_ENERGETIQUE",
        "title": "Audit energetique reglementaire",
        "description": "Realiser l'audit energetique obligatoire (>250 salaries ou CA>50M EUR).",
        "category": "conformite",
        "priority": 1,
        "estimated_gain_eur": 0,
        "complexity": "complex",
        "typical_duration_days": 90,
        "tags": "audit,reglementaire,obligatoire",
    },
    {
        "code": "TPL_DECRET_TERTIAIRE",
        "title": "Plan d'actions Decret tertiaire",
        "description": "Elaborer le plan d'actions pour atteindre les objectifs -40% a 2030.",
        "category": "conformite",
        "priority": 1,
        "estimated_gain_eur": 0,
        "complexity": "complex",
        "typical_duration_days": 60,
        "tags": "decret,tertiaire,operat",
    },
    {
        "code": "TPL_BACS_INSTALL",
        "title": "Installation GTB/GTC (BACS)",
        "description": "Installer un système BACS conforme au décret n°2020-887.",
        "category": "conformite",
        "priority": 1,
        "estimated_gain_kwh": 40000,
        "estimated_gain_eur": 7200,
        "complexity": "complex",
        "typical_duration_days": 180,
        "tags": "bacs,gtb,gtc,reglementaire",
    },
    {
        "code": "TPL_DPE_MISE_A_JOUR",
        "title": "Mise a jour DPE",
        "description": "Mettre a jour le Diagnostic de Performance Energetique du batiment.",
        "category": "conformite",
        "priority": 3,
        "estimated_gain_eur": 0,
        "complexity": "simple",
        "typical_duration_days": 30,
        "tags": "dpe,diagnostic",
    },
    # Donnees
    {
        "code": "TPL_IMPORT_FACTURES",
        "title": "Import factures fournisseur",
        "description": "Importer l'historique des factures d'electricite et de gaz (24 mois).",
        "category": "donnees",
        "priority": 2,
        "estimated_gain_eur": 0,
        "complexity": "simple",
        "typical_duration_days": 7,
        "tags": "factures,import,donnees",
    },
    {
        "code": "TPL_RACCORDEMENT_COMPTEUR",
        "title": "Raccordement compteur communicant",
        "description": "Activer la telereleve Linky/Gazpar pour disposer de donnees horaires.",
        "category": "donnees",
        "priority": 2,
        "estimated_gain_eur": 0,
        "complexity": "simple",
        "typical_duration_days": 14,
        "tags": "compteur,linky,telereleve",
    },
    {
        "code": "TPL_SOUS_COMPTAGE",
        "title": "Installation sous-comptage",
        "description": "Installer des sous-compteurs par usage (CVC, eclairage, process) pour le suivi detaille.",
        "category": "donnees",
        "priority": 3,
        "estimated_gain_kwh": 0,
        "estimated_gain_eur": 0,
        "complexity": "medium",
        "typical_duration_days": 45,
        "tags": "sous-comptage,monitoring",
    },
    # Usage
    {
        "code": "TPL_SENSIBILISATION",
        "title": "Campagne sensibilisation occupants",
        "description": "Former et sensibiliser les occupants aux eco-gestes (affichage, ateliers).",
        "category": "usage",
        "priority": 3,
        "estimated_gain_kwh": 5000,
        "estimated_gain_eur": 900,
        "complexity": "simple",
        "typical_duration_days": 30,
        "tags": "sensibilisation,eco-gestes",
    },
    {
        "code": "TPL_SUIVI_HEBDO",
        "title": "Revue hebdomadaire energie",
        "description": "Mettre en place une revue hebdomadaire des consommations avec l'equipe maintenance.",
        "category": "usage",
        "priority": 3,
        "estimated_gain_kwh": 3000,
        "estimated_gain_eur": 540,
        "complexity": "simple",
        "typical_duration_days": 7,
        "tags": "suivi,management",
    },
    # Achat
    {
        "code": "TPL_RENEGOCIATION_CONTRAT",
        "title": "Renegociation contrat fourniture",
        "description": "Lancer un appel d'offres ou renegocier le contrat d'electricite/gaz.",
        "category": "achat",
        "priority": 2,
        "estimated_gain_eur": 5000,
        "complexity": "medium",
        "typical_duration_days": 60,
        "tags": "contrat,achat,negociation",
    },
    {
        "code": "TPL_OPTIMISATION_PUISSANCE",
        "title": "Optimisation puissance souscrite",
        "description": "Ajuster la puissance souscrite au profil reel de consommation (eviter penalites depassement).",
        "category": "achat",
        "priority": 3,
        "estimated_gain_eur": 2000,
        "complexity": "simple",
        "typical_duration_days": 14,
        "tags": "puissance,souscrite,turpe",
    },
    {
        "code": "TPL_AUTOCONSOMMATION",
        "title": "Etude autoconsommation solaire",
        "description": "Etudier la faisabilite d'une installation photovoltaique en autoconsommation.",
        "category": "achat",
        "priority": 3,
        "estimated_gain_kwh": 50000,
        "estimated_gain_eur": 9000,
        "complexity": "complex",
        "typical_duration_days": 120,
        "tags": "solaire,photovoltaique,autoconsommation",
    },
]


@router.get("")
def list_templates(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all active action templates."""
    query = db.query(ActionTemplate).filter(ActionTemplate.is_active == True)
    if category:
        query = query.filter(ActionTemplate.category == category)
    templates = query.order_by(ActionTemplate.category, ActionTemplate.priority).all()
    return {
        "templates": [
            {
                "id": t.id,
                "code": t.code,
                "title": t.title,
                "description": t.description,
                "category": t.category,
                "priority": t.priority,
                "estimated_gain_eur": t.estimated_gain_eur,
                "estimated_gain_kwh": t.estimated_gain_kwh,
                "complexity": t.complexity,
                "typical_duration_days": t.typical_duration_days,
                "tags": t.tags,
                "typical_gain_pct": t.typical_gain_pct,
                "typical_cost_range": t.typical_cost_range,
                "confidence_level": t.confidence_level,
                "regulatory_link": t.regulatory_link,
            }
            for t in templates
        ],
        "total": len(templates),
    }


@router.get("/{code}")
def get_template(code: str, db: Session = Depends(get_db)):
    """Get a single template by code."""
    t = db.query(ActionTemplate).filter(ActionTemplate.code == code).first()
    if not t:
        raise HTTPException(404, f"Template {code} not found")
    return {
        "id": t.id,
        "code": t.code,
        "title": t.title,
        "description": t.description,
        "category": t.category,
        "priority": t.priority,
        "estimated_gain_eur": t.estimated_gain_eur,
        "estimated_gain_kwh": t.estimated_gain_kwh,
        "complexity": t.complexity,
        "typical_duration_days": t.typical_duration_days,
        "tags": t.tags,
        "typical_gain_pct": t.typical_gain_pct,
        "typical_cost_range": t.typical_cost_range,
        "confidence_level": t.confidence_level,
        "regulatory_link": t.regulatory_link,
    }


@router.post("/seed")
def seed_templates(db: Session = Depends(get_db)):
    """Seed default templates (idempotent)."""
    created = 0
    skipped = 0
    for tpl in DEFAULT_TEMPLATES:
        existing = db.query(ActionTemplate).filter(ActionTemplate.code == tpl["code"]).first()
        if existing:
            skipped += 1
            continue
        t = ActionTemplate(**tpl, is_active=True)
        db.add(t)
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped, "total_templates": len(DEFAULT_TEMPLATES)}
