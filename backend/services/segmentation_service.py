"""
PROMEOS - Service de segmentation B2B
Detection automatique de la typologie client + questionnaire d'affinage.
V100: portfolio_id, derived_from, segment_label, missing_questions, recommendations.
"""
import json
from typing import Optional, List

from sqlalchemy.orm import Session

from models import (
    Organisation, Site, Compteur, SegmentationProfile, SegmentationAnswer,
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
# Label humain des typologies
# ========================================

TYPO_LABELS = {
    Typologie.TERTIAIRE_PRIVE: "Tertiaire Prive",
    Typologie.TERTIAIRE_PUBLIC: "Tertiaire Public",
    Typologie.INDUSTRIE: "Industrie",
    Typologie.COMMERCE_RETAIL: "Commerce / Retail",
    Typologie.COPROPRIETE_SYNDIC: "Copropriete / Syndic",
    Typologie.BAILLEUR_SOCIAL: "Bailleur Social",
    Typologie.COLLECTIVITE: "Collectivite",
    Typologie.HOTELLERIE_RESTAURATION: "Hotellerie / Restauration",
    Typologie.SANTE_MEDICO_SOCIAL: "Sante / Medico-social",
    Typologie.ENSEIGNEMENT: "Enseignement",
    Typologie.MIXTE: "Mixte (multi-activites)",
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
# Recommendations par typologie
# ========================================

_RECOMMENDATIONS = {
    Typologie.TERTIAIRE_PRIVE: [
        {"key": "operat", "label": "Declarer sur OPERAT", "description": "Le decret tertiaire impose une declaration annuelle sur la plateforme OPERAT.", "priority": "high"},
        {"key": "bacs", "label": "Verifier conformite BACS", "description": "Vos batiments > 290 kW doivent disposer d'un systeme d'automatisation.", "priority": "high"},
        {"key": "cee", "label": "Valoriser les CEE", "description": "Identifiez les travaux eligibles aux Certificats d'Economie d'Energie.", "priority": "medium"},
    ],
    Typologie.INDUSTRIE: [
        {"key": "iso50001", "label": "Audit energetique / ISO 50001", "description": "Obligation d'audit tous les 4 ans pour les grandes entreprises.", "priority": "high"},
        {"key": "cee", "label": "Valoriser les CEE industriels", "description": "Fiches CEE specifiques industrie (variateurs, recuperation chaleur).", "priority": "high"},
        {"key": "flex", "label": "Evaluer la flexibilite", "description": "Monetisez votre capacite d'effacement via les mecanismes de marche.", "priority": "medium"},
    ],
    Typologie.COPROPRIETE_SYNDIC: [
        {"key": "dpe_collectif", "label": "DPE collectif", "description": "Obligatoire pour les coproprietes > 50 lots (depuis 2024).", "priority": "high"},
        {"key": "ptz_copro", "label": "Eco-PTZ copropriete", "description": "Financement a taux zero pour travaux de renovation energetique.", "priority": "medium"},
        {"key": "maprimereno", "label": "MaPrimeRenov Copropriete", "description": "Aide collective pour la renovation globale.", "priority": "medium"},
    ],
    Typologie.COLLECTIVITE: [
        {"key": "operat", "label": "Declarer sur OPERAT", "description": "Batiments publics > 1000 m2 soumis au decret tertiaire.", "priority": "high"},
        {"key": "schema_directeur", "label": "Schema directeur energie", "description": "Planifier la transition energetique du patrimoine public.", "priority": "high"},
        {"key": "intracting", "label": "Intracting energetique", "description": "Reinvestir les economies d'energie dans de nouveaux travaux.", "priority": "medium"},
    ],
    Typologie.SANTE_MEDICO_SOCIAL: [
        {"key": "operat", "label": "Declarer sur OPERAT", "description": "Etablissements de sante soumis au decret tertiaire.", "priority": "high"},
        {"key": "bacs", "label": "BACS et GTB", "description": "Automatisation critique pour le confort et les economies.", "priority": "high"},
        {"key": "continu", "label": "Optimiser le 24h/24", "description": "Pilotage specifique pour les batiments a occupation continue.", "priority": "medium"},
    ],
}

# Default recommendations for typologies without specific ones
_DEFAULT_RECOMMENDATIONS = [
    {"key": "audit", "label": "Realiser un audit energetique", "description": "Identifiez les principaux postes de consommation et les gisements d'economies.", "priority": "high"},
    {"key": "suivi", "label": "Mettre en place un suivi mensuel", "description": "Suivez vos consommations pour detecter les derives.", "priority": "medium"},
    {"key": "contrats", "label": "Optimiser vos contrats", "description": "Verifiez la coherence de vos puissances souscrites et tarifs.", "priority": "medium"},
]


def get_recommendations(typologie_str: str) -> list:
    """Return recommendations for a given typologie key."""
    if not typologie_str:
        return _DEFAULT_RECOMMENDATIONS
    try:
        typo = Typologie(typologie_str)
    except (ValueError, KeyError):
        return _DEFAULT_RECOMMENDATIONS
    return _RECOMMENDATIONS.get(typo, _DEFAULT_RECOMMENDATIONS)


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
            "derived_from": str,  # V100
        }
    """
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        return {
            "typologie": Typologie.TERTIAIRE_PRIVE,
            "confidence_score": 0.0,
            "reasons": ["Organisation introuvable"],
            "naf_code": None,
            "derived_from": "mix",
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
            "derived_from": "mix",
        }

    # Score de confiance
    typologies = [c[1] for c in candidates]
    sources = [c[0] for c in candidates]
    unique = set(typologies)

    if len(unique) == 1:
        # Tous les signaux convergent
        score = min(30 + len(candidates) * 25, 80)
        final = typologies[0]
    else:
        # Divergence → priorite: heuristic > naf > sites
        final = typologies[0]
        score = 30 + (len(candidates) - len(unique)) * 10

    # V100: derived_from — dominant source
    if len(sources) == 1:
        derived = {"heuristic": "patrimoine", "naf": "naf", "sites": "patrimoine"}.get(sources[0], "mix")
    elif "naf" in sources and "sites" not in sources:
        derived = "naf"
    elif "sites" in sources and "naf" not in sources:
        derived = "patrimoine"
    else:
        derived = "mix"

    return {
        "typologie": final,
        "confidence_score": round(score, 1),
        "reasons": reasons,
        "naf_code": naf_code,
        "derived_from": derived,
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
# Missing questions helper
# ========================================

def get_missing_questions(profile: SegmentationProfile) -> list:
    """Return list of question IDs not yet answered."""
    existing = json.loads(profile.answers_json) if profile.answers_json else {}
    all_ids = [q["id"] for q in QUESTIONS_V1]
    return [qid for qid in all_ids if qid not in existing or not existing[qid]]


# ========================================
# CRUD operations
# ========================================

def get_or_create_profile(db: Session, org_id: int) -> SegmentationProfile:
    """Recupere ou cree le profil de segmentation pour une org."""
    profile = db.query(SegmentationProfile).filter(
        SegmentationProfile.organisation_id == org_id,
        SegmentationProfile.portfolio_id.is_(None),
    ).first()

    if profile:
        return profile

    # Detection auto
    detection = detect_typologie(db, org_id)
    typo = detection["typologie"]

    profile = SegmentationProfile(
        organisation_id=org_id,
        typologie=typo.value,
        segment_label=TYPO_LABELS.get(typo, typo.value),
        naf_code=detection["naf_code"],
        confidence_score=detection["confidence_score"],
        derived_from=detection["derived_from"],
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

    # V100: Sync SegmentationAnswer rows
    for qid, val in answers.items():
        if not val:
            continue
        sa = db.query(SegmentationAnswer).filter(
            SegmentationAnswer.profile_id == profile.id,
            SegmentationAnswer.question_id == qid,
        ).first()
        if sa:
            sa.answer_value = val
        else:
            db.add(SegmentationAnswer(
                profile_id=profile.id,
                organisation_id=org_id,
                portfolio_id=profile.portfolio_id,
                question_id=qid,
                answer_value=val,
            ))

    # Recalculate confidence with boost
    detection = detect_typologie(db, org_id)
    boost = _score_boost_from_answers(existing)
    profile.confidence_score = min(detection["confidence_score"] + boost, 100.0)

    # Update derived_from when questionnaire answers exist
    nb_answers = sum(1 for v in existing.values() if v and v != "ne_sait_pas")
    if nb_answers > 0:
        if detection["derived_from"] == "questionnaire":
            profile.derived_from = "questionnaire"
        else:
            profile.derived_from = "mix"

    # Update segment_label
    try:
        typo = Typologie(profile.typologie)
        profile.segment_label = TYPO_LABELS.get(typo, profile.typologie)
    except (ValueError, KeyError):
        pass

    # Update reasons
    reasons = detection["reasons"]
    reasons.append(f"Questionnaire: {len(existing)} reponses (+{boost}pts)")
    profile.reasons_json = json.dumps(reasons, ensure_ascii=False)

    db.commit()
    db.refresh(profile)
    return profile


def recompute_profile(db: Session, org_id: int) -> SegmentationProfile:
    """V100: Force re-detection from patrimoine data (post-import)."""
    profile = get_or_create_profile(db, org_id)

    detection = detect_typologie(db, org_id)
    typo = detection["typologie"]

    # Preserve existing answers boost
    existing = json.loads(profile.answers_json) if profile.answers_json else {}
    boost = _score_boost_from_answers(existing)

    profile.typologie = typo.value
    profile.segment_label = TYPO_LABELS.get(typo, typo.value)
    profile.naf_code = detection["naf_code"]
    profile.confidence_score = min(detection["confidence_score"] + boost, 100.0)
    profile.derived_from = detection["derived_from"]

    reasons = detection["reasons"]
    if boost > 0:
        reasons.append(f"Questionnaire: {len(existing)} reponses (+{boost}pts)")
    profile.reasons_json = json.dumps(reasons, ensure_ascii=False)

    db.commit()
    db.refresh(profile)
    return profile


def get_questions(org_id: int = None) -> list:
    """Retourne la liste des questions V1."""
    return QUESTIONS_V1


# ========================================
# V101: Next Best Step
# ========================================

def compute_next_best_step(db: Session, org_id: int, portfolio_id: Optional[int] = None) -> dict:
    """
    V101: 1 prochaine action recommandee, deterministe.
    Cascade de priorite:
      1. confidence < 50 → "Repondez a quelques questions pour affiner votre profil"
      2. contrats expirants (90j) → "Preparer le renouvellement"
      3. reconciliation fail → "Debloquer vos donnees"
      4. defaut → top recommendation
    """
    profile = get_or_create_profile(db, org_id)
    missing = get_missing_questions(profile)

    # 1. Confidence < 50 and questions remaining → answer questions
    if profile.confidence_score < 50 and len(missing) > 0:
        return {
            "key": "answer_questions",
            "title": f"{min(len(missing), 3)} questions pour affiner votre profil",
            "why": f"Votre profil est a {int(profile.confidence_score)}% de confiance. Repondre ameliore vos recommandations.",
            "impact_label": "Profil",
            "score_gain_hint": "+10 pts confiance",
            "cta": {
                "type": "modal",
                "label": "Repondre maintenant",
                "route": None,
                "payload": {"questions_remaining": len(missing)},
            },
        }

    # 2. Expiring contracts → renouvellement
    try:
        from services.contract_radar_service import compute_contract_radar
        radar = compute_contract_radar(db, org_id, portfolio_id, horizon_days=90)
        expiring = radar.get("stats", {}).get("expiring", 0)
        expired = radar.get("stats", {}).get("expired", 0)
        if expiring > 0 or expired > 0:
            total = expiring + expired
            return {
                "key": "contract_renewal",
                "title": f"Preparer le renouvellement de {total} contrat{'s' if total > 1 else ''}",
                "why": f"{expired} expire{'s' if expired > 1 else ''}, {expiring} a echeance sous 90 jours.",
                "impact_label": "Finance",
                "score_gain_hint": "Eviter les reconductions tacites",
                "cta": {
                    "type": "route",
                    "label": "Voir les contrats",
                    "route": "/renouvellements",
                    "payload": None,
                },
            }
    except Exception:
        pass

    # 3. Reconciliation failures → patrimoine
    try:
        from services.reconciliation_service import reconcile_portfolio
        recon = reconcile_portfolio(db, org_id, portfolio_id)
        fail_count = recon.get("stats", {}).get("fail", 0)
        if fail_count > 0:
            return {
                "key": "fix_reconciliation",
                "title": f"Debloquer {fail_count} site{'s' if fail_count > 1 else ''} en erreur",
                "why": "Des sites ont des donnees manquantes ou incoherentes.",
                "impact_label": "Donnees",
                "score_gain_hint": f"+{fail_count * 5} pts reconciliation",
                "cta": {
                    "type": "route",
                    "label": "Voir le patrimoine",
                    "route": "/patrimoine",
                    "payload": None,
                },
            }
    except Exception:
        pass

    # 4. Default → top recommendation
    recs = get_recommendations(profile.typologie)
    if recs:
        top = recs[0]
        return {
            "key": top["key"],
            "title": top["label"],
            "why": top.get("description", "Action recommandee pour votre profil."),
            "impact_label": "Energie",
            "score_gain_hint": "Optimisation",
            "cta": {
                "type": "route",
                "label": "En savoir plus",
                "route": "/segmentation",
                "payload": None,
            },
        }

    return {
        "key": "explore",
        "title": "Explorer vos donnees",
        "why": "Consultez votre patrimoine pour identifier des opportunites.",
        "impact_label": "General",
        "score_gain_hint": None,
        "cta": {
            "type": "route",
            "label": "Voir le patrimoine",
            "route": "/patrimoine",
            "payload": None,
        },
    }
