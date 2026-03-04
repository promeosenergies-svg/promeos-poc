"""
PROMEOS Routes - AI agents endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from ai_layer.registry import run_agent
from models import AiInsight

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
