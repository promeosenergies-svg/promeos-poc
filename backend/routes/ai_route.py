"""
PROMEOS Routes - AI agents endpoints
"""

from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from ai_layer.registry import run_agent
from middleware.auth import get_optional_auth, AuthContext
from models import AiInsight, Annotation
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/ai", tags=["AI Agents"])


@router.get("/site/{site_id}/explain")
def explain_site(site_id: int, db: Session = Depends(get_db)):
    """Agent explainer: brief du site."""
    try:
        insight = run_agent("regops_explainer", db, site_id=site_id)
        import json

        content = json.loads(insight.content_json)
        return {
            "site_id": site_id,
            "brief": content.get("brief"),
            "sources_used": content.get("sources_used"),
            "needs_human_review": content.get("needs_human_review"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/site/{site_id}/recommend")
def recommend_actions(site_id: int, db: Session = Depends(get_db)):
    """Agent recommender: suggestions IA."""
    try:
        insight = run_agent("regops_recommender", db, site_id=site_id)
        import json

        content = json.loads(insight.content_json)
        return {"site_id": site_id, "suggestions": content.get("suggestions"), "is_ai_suggestion": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/site/{site_id}/data-quality")
def check_data_quality(site_id: int, db: Session = Depends(get_db)):
    """Agent data quality."""
    try:
        insight = run_agent("data_quality_agent", db, site_id=site_id)
        import json

        return {"analysis": json.loads(insight.content_json)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/org/brief")
def exec_brief(org_id: int = 1, db: Session = Depends(get_db)):
    """Agent exec brief."""
    try:
        insight = run_agent("exec_brief_agent", db, org_id=org_id)
        import json

        return {"brief": json.loads(insight.content_json)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
def list_insights(object_type: str = None, object_id: int = None, limit: int = 20, db: Session = Depends(get_db)):
    """Liste des insights IA."""
    query = db.query(AiInsight)
    if object_type:
        query = query.filter(AiInsight.object_type == object_type)
    if object_id:
        query = query.filter(AiInsight.object_id == object_id)

    insights = query.order_by(AiInsight.created_at.desc()).limit(limit).all()

    return {
        "insights": [
            {
                "id": i.id,
                "object_type": i.object_type,
                "object_id": i.object_id,
                "insight_type": str(i.insight_type).split(".")[-1],
                "created_at": i.created_at.isoformat(),
            }
            for i in insights
        ]
    }


# ── Phase 3.2 — PATCH resolve insight ─────────────────────────


class AiInsightResolution(str, Enum):
    VALIDATED = "validated"
    DISMISSED = "dismissed"
    CORRECTED = "corrected"


class ResolveInsightBody(BaseModel):
    resolution: AiInsightResolution
    correction_note: Optional[str] = None


@router.patch("/insights/{insight_id}")
def resolve_ai_insight(
    insight_id: int,
    body: ResolveInsightBody,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Ferme la boucle needs_human_review.
    Cree une Annotation pour alimenter le profil annotateur.
    """
    insight = db.query(AiInsight).filter(AiInsight.id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight non trouve")

    import json

    content = json.loads(insight.content_json) if insight.content_json else {}

    # Resolve org_id from auth or fallback
    from fastapi import Request

    org_id = 1  # fallback demo
    if auth and hasattr(auth, "org_id"):
        org_id = auth.org_id

    # Determine annotation label
    label_map = {
        AiInsightResolution.VALIDATED: "validated",
        AiInsightResolution.DISMISSED: "false_positive",
        AiInsightResolution.CORRECTED: "corrected",
    }

    annotator_id = f"user:{auth.user_id}" if auth and hasattr(auth, "user_id") else "anonymous"

    annotation = Annotation(
        object_type="ai_insight",
        object_id=insight_id,
        label=label_map[body.resolution],
        confidence=0.85,
        correction=body.correction_note,
        annotator_type="user",
        annotator_id=annotator_id,
        org_id=org_id,
        kb_item_id=content.get("kb_item_id"),
    )
    db.add(annotation)
    db.commit()

    return {
        "status": "resolved",
        "resolution": body.resolution.value,
        "annotation_id": annotation.id,
    }
