"""
PROMEOS - Routes Segmentation B2B
GET /api/segmentation/questions — liste des questions
POST /api/segmentation/answers — soumettre les reponses
GET /api/segmentation/profile — profil detecte + score
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from sqlalchemy.orm import Session

from database import get_db
from models import Organisation
from services.segmentation_service import (
    get_questions,
    get_or_create_profile,
    update_profile_with_answers,
    detect_typologie,
)

router = APIRouter(prefix="/api/segmentation", tags=["Segmentation"])


# ========================================
# Schemas
# ========================================

class AnswersRequest(BaseModel):
    answers: Dict[str, str]


# ========================================
# GET /api/segmentation/questions
# ========================================

@router.get("/questions")
def list_questions():
    """Retourne les questions du questionnaire de segmentation V1."""
    return {"questions": get_questions(), "total": len(get_questions())}


# ========================================
# POST /api/segmentation/answers
# ========================================

@router.post("/answers")
def submit_answers(req: AnswersRequest, db: Session = Depends(get_db)):
    """Soumet les reponses au questionnaire et met a jour le profil."""
    org = db.query(Organisation).first()
    if not org:
        raise HTTPException(status_code=400, detail="Aucune organisation trouvee. Creez d'abord une organisation.")

    profile = update_profile_with_answers(db, org.id, req.answers)

    return {
        "typologie": profile.typologie,
        "confidence_score": profile.confidence_score,
        "answers_count": len(json.loads(profile.answers_json)) if profile.answers_json else 0,
        "reasons": json.loads(profile.reasons_json) if profile.reasons_json else [],
    }


# ========================================
# GET /api/segmentation/profile
# ========================================

@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    """Retourne le profil de segmentation de l'organisation courante."""
    org = db.query(Organisation).first()
    if not org:
        return {
            "has_profile": False,
            "typologie": None,
            "confidence_score": 0,
            "reasons": [],
            "answers": {},
            "naf_code": None,
        }

    profile = get_or_create_profile(db, org.id)

    return {
        "has_profile": True,
        "typologie": profile.typologie,
        "confidence_score": profile.confidence_score,
        "naf_code": profile.naf_code,
        "reasons": json.loads(profile.reasons_json) if profile.reasons_json else [],
        "answers": json.loads(profile.answers_json) if profile.answers_json else {},
        "organisation": {
            "id": org.id,
            "nom": org.nom,
            "type_client": org.type_client,
        },
    }
