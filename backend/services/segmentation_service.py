"""
PROMEOS - Service de segmentation B2B
Detection automatique de la typologie client + questionnaire d'affinage.
"""
import json
from typing import Optional, List

from sqlalchemy.orm import Session

from models import (
    Organisation, Site, Compteur, SegmentationProfile,
    TypeSite,
)
from models.enums import Typologie
from services.naf_classifier import classify_naf


# ========================================
# Mapping TypeSite → Typologie
# ========================================

_TYPSITE_TO_TYPO = {
    TypeSite.BUREAU: Typologie.TERTIAIRE_PRIVE,
    TypeSite.MAGASIN: Typologie.COMMERCE_RETAIL,
    TypeSite.COMMERCE: Typologie.COMMERCE_RETAIL,
    TypeSite.USINE: Typologie.INDUSTRIE,
    TypeSite.ENTREPOT: Typologie.INDUSTRIE,
    TypeSite.COPROPRIETE: Typologie.COPROPRIETE_SYNDIC,
    TypeSite.LOGEMENT_SOCIAL: Typologie.BAILLEUR_SOCIAL,
    TypeSite.COLLECTIVITE: Typologie.COLLECTIVITE,
    TypeSite.HOTEL: Typologie.HOTELLERIE_RESTAURATION,
    TypeSite.SANTE: Typologie.SANTE_MEDICO_SOCIAL,
    TypeSite.ENSEIGNEMENT: Typologie.ENSEIGNEMENT,
}


# ========================================
# Questionnaire V1 (8 questions max)
# ========================================

QUESTIONS_V1 = [
    {
        "id": "q_travaux",
        "text": "Avez-vous realise des travaux d'efficacite energetique ces 3 dernieres annees ?",
        "type": "single",
        "options": [
            {"value": "oui", "label": "Oui"},
            {"value": "non", "label": "Non"},
            {"value": "ne_sait_pas", "label": "Je ne sais pas"},
        ],
    },
    {
        "id": "q_gtb",
        "text": "Disposez-vous d'une GTB (Gestion Technique du Batiment) ?",
        "type": "single",
        "options": [
            {"value": "oui_centralisee", "label": "Oui, centralisee"},
            {"value": "oui_partielle", "label": "Oui, sur certains sites"},
            {"value": "non", "label": "Non"},
            {"value": "ne_sait_pas", "label": "Je ne sais pas"},
        ],
    },
    {
        "id": "q_bacs",
        "text": "Connaissez-vous vos obligations BACS (Building Automation & Control Systems) ?",
        "type": "single",
        "options": [
            {"value": "oui_conforme", "label": "Oui, nous sommes conformes"},
            {"value": "oui_en_cours", "label": "Oui, mise en conformite en cours"},
            {"value": "non", "label": "Non, pas au courant"},
        ],
    },
    {
        "id": "q_operat",
        "text": "Avez-vous declare vos consommations sur OPERAT ?",
        "type": "single",
        "options": [
            {"value": "oui_a_jour", "label": "Oui, a jour"},
            {"value": "oui_retard", "label": "Oui, mais en retard"},
            {"value": "non", "label": "Non"},
            {"value": "non_concerne", "label": "Non concerne"},
        ],
    },
    {
        "id": "q_cee",
        "text": "Avez-vous deja beneficie de CEE (Certificats d'Economie d'Energie) ?",
        "type": "single",
        "options": [
            {"value": "oui", "label": "Oui"},
            {"value": "non", "label": "Non"},
            {"value": "ne_sait_pas", "label": "Je ne sais pas"},
        ],
    },
    {
        "id": "q_horaires",
        "text": "Quels sont les horaires d'occupation principaux de vos batiments ?",
        "type": "single",
        "options": [
            {"value": "bureau_standard", "label": "Bureau standard (8h-19h, L-V)"},
            {"value": "etendu", "label": "Etendu (6h-22h)"},
            {"value": "continu_24h", "label": "24h/24 (hopital, usine, hotel)"},
            {"value": "variable", "label": "Variable selon les sites"},
        ],
    },
    {
        "id": "q_chauffage",
        "text": "Quel est le mode de chauffage principal ?",
        "type": "single",
        "options": [
            {"value": "gaz", "label": "Gaz naturel"},
            {"value": "electrique", "label": "Electrique (PAC, convecteurs)"},
            {"value": "reseau_chaleur", "label": "Reseau de chaleur urbain"},
            {"value": "mixte", "label": "Mixte / autre"},
        ],
    },
    {
        "id": "q_irve",
        "text": "Disposez-vous de bornes de recharge pour vehicules electriques (IRVE) ?",
        "type": "single",
        "options": [
            {"value": "oui", "label": "Oui"},
            {"value": "projet", "label": "En projet"},
            {"value": "non", "label": "Non"},
        ],
    },
]


# ========================================
# Detection automatique de la typologie
# ========================================

def _detect_from_naf(naf_code: Optional[str]) -> Optional[Typologie]:
    """Detecte la typologie a partir du code NAF."""
    if not naf_code:
        return None
    type_site = classify_naf(naf_code)
    return _TYPSITE_TO_TYPO.get(type_site)


def _detect_from_sites(db: Session, org_id: int) -> Optional[Typologie]:
    """Detecte la typologie a partir des types de sites du patrimoine."""
    sites = db.query(Site).join(
        Site.portefeuille
    ).filter(
        Site.portefeuille.has(
            entite_juridique=db.query(Organisation).get(org_id).entites_juridiques[0] if db.query(Organisation).get(org_id) else None
        )
    ).all() if False else []  # Simplified: query sites via org

    # Simplified approach: get all sites for the org
    from models import Portefeuille, EntiteJuridique
    sites = (
        db.query(Site)
        .join(Site.portefeuille)
        .join(Portefeuille.entite_juridique)
        .join(EntiteJuridique.organisation)
        .filter(Organisation.id == org_id)
        .all()
    )

    if not sites:
        return None

    # Count types
    type_counts = {}
    for s in sites:
        ts = s.type
        typo = _TYPSITE_TO_TYPO.get(ts, Typologie.TERTIAIRE_PRIVE)
        type_counts[typo] = type_counts.get(typo, 0) + 1

    # If > 2 typologies differentes → MIXTE
    if len(type_counts) > 2:
        return Typologie.MIXTE

    # Sinon: la plus frequente
    return max(type_counts, key=type_counts.get)


def _detect_from_heuristics(
    db: Session, org_id: int, type_client: Optional[str] = None
) -> Optional[Typologie]:
    """Heuristiques supplementaires basees sur type_client de l'org."""
    if not type_client:
        return None

    _CLIENT_MAP = {
        "copropriete": Typologie.COPROPRIETE_SYNDIC,
        "syndic": Typologie.COPROPRIETE_SYNDIC,
        "bailleur": Typologie.BAILLEUR_SOCIAL,
        "logement_social": Typologie.BAILLEUR_SOCIAL,
        "collectivite": Typologie.COLLECTIVITE,
        "mairie": Typologie.COLLECTIVITE,
        "commune": Typologie.COLLECTIVITE,
        "hopital": Typologie.SANTE_MEDICO_SOCIAL,
        "ehpad": Typologie.SANTE_MEDICO_SOCIAL,
        "clinique": Typologie.SANTE_MEDICO_SOCIAL,
        "hotel": Typologie.HOTELLERIE_RESTAURATION,
        "restaurant": Typologie.HOTELLERIE_RESTAURATION,
        "ecole": Typologie.ENSEIGNEMENT,
        "universite": Typologie.ENSEIGNEMENT,
        "lycee": Typologie.ENSEIGNEMENT,
        "industrie": Typologie.INDUSTRIE,
        "usine": Typologie.INDUSTRIE,
        "commerce": Typologie.COMMERCE_RETAIL,
        "magasin": Typologie.COMMERCE_RETAIL,
        "retail": Typologie.COMMERCE_RETAIL,
        "bureau": Typologie.TERTIAIRE_PRIVE,
        "tertiaire": Typologie.TERTIAIRE_PRIVE,
    }
    key = type_client.lower().strip()
    return _CLIENT_MAP.get(key)


def detect_typologie(
    db: Session, org_id: int
) -> dict:
    """Detecte la typologie d'une organisation.

    Strategie en cascade:
    1. Heuristique type_client
    2. Code NAF (entite juridique)
    3. Analyse des sites existants
    4. Defaut: TERTIAIRE_PRIVE

    Returns:
        {
            "typologie": Typologie,
            "confidence_score": float (0-100),
            "reasons": [str, ...],
            "naf_code": str | None,
        }
    """
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        return {
            "typologie": Typologie.TERTIAIRE_PRIVE,
            "confidence_score": 0.0,
            "reasons": ["Organisation introuvable"],
            "naf_code": None,
        }

    reasons = []
    candidates = []

    # 1. Heuristique type_client
    typo_heur = _detect_from_heuristics(db, org_id, org.type_client)
    if typo_heur:
        candidates.append(("heuristic", typo_heur))
        reasons.append(f"Type client '{org.type_client}' → {typo_heur.value}")

    # 2. Code NAF
    from models import EntiteJuridique
    entite = db.query(EntiteJuridique).filter(
        EntiteJuridique.organisation_id == org_id
    ).first()
    naf_code = entite.naf_code if entite and entite.naf_code else None

    if naf_code:
        typo_naf = _detect_from_naf(naf_code)
        if typo_naf:
            candidates.append(("naf", typo_naf))
            reasons.append(f"Code NAF '{naf_code}' → {typo_naf.value}")

    # 3. Analyse des sites
    typo_sites = _detect_from_sites(db, org_id)
    if typo_sites:
        candidates.append(("sites", typo_sites))
        reasons.append(f"Analyse patrimoine → {typo_sites.value}")

    # Resolution
    if not candidates:
        return {
            "typologie": Typologie.TERTIAIRE_PRIVE,
            "confidence_score": 20.0,
            "reasons": ["Aucune donnee — defaut tertiaire prive"],
            "naf_code": naf_code,
        }

    # Score de confiance
    typologies = [c[1] for c in candidates]
    unique = set(typologies)

    if len(unique) == 1:
        # Tous les signaux convergent
        score = min(30 + len(candidates) * 25, 80)
        final = typologies[0]
    else:
        # Divergence → priorite: heuristic > naf > sites
        final = typologies[0]
        score = 30 + (len(candidates) - len(unique)) * 10

    return {
        "typologie": final,
        "confidence_score": round(score, 1),
        "reasons": reasons,
        "naf_code": naf_code,
    }


# ========================================
# Score boost from answers
# ========================================

def _score_boost_from_answers(answers: dict) -> float:
    """Calcule le boost de confiance apporte par les reponses au questionnaire."""
    boost = 0.0
    nb_answered = sum(1 for v in answers.values() if v and v != "ne_sait_pas")
    # +2.5 par reponse non-vide (max 8 * 2.5 = 20)
    boost = nb_answered * 2.5
    return min(boost, 20.0)


# ========================================
# CRUD operations
# ========================================

def get_or_create_profile(db: Session, org_id: int) -> SegmentationProfile:
    """Recupere ou cree le profil de segmentation pour une org."""
    profile = db.query(SegmentationProfile).filter(
        SegmentationProfile.organisation_id == org_id
    ).first()

    if profile:
        return profile

    # Detection auto
    detection = detect_typologie(db, org_id)

    profile = SegmentationProfile(
        organisation_id=org_id,
        typologie=detection["typologie"].value,
        naf_code=detection["naf_code"],
        confidence_score=detection["confidence_score"],
        reasons_json=json.dumps(detection["reasons"], ensure_ascii=False),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile_with_answers(
    db: Session, org_id: int, answers: dict
) -> SegmentationProfile:
    """Met a jour le profil avec les reponses au questionnaire."""
    profile = get_or_create_profile(db, org_id)

    # Merge with existing answers
    existing = json.loads(profile.answers_json) if profile.answers_json else {}
    existing.update(answers)
    profile.answers_json = json.dumps(existing, ensure_ascii=False)

    # Recalculate confidence with boost
    detection = detect_typologie(db, org_id)
    boost = _score_boost_from_answers(existing)
    profile.confidence_score = min(detection["confidence_score"] + boost, 100.0)

    # Update reasons
    reasons = detection["reasons"]
    reasons.append(f"Questionnaire: {len(existing)} reponses (+{boost}pts)")
    profile.reasons_json = json.dumps(reasons, ensure_ascii=False)

    db.commit()
    db.refresh(profile)
    return profile


def get_questions(org_id: int = None) -> list:
    """Retourne la liste des questions V1."""
    return QUESTIONS_V1
