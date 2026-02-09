"""
PROMEOS - Demo Mode API Routes
POST /api/demo/enable, POST /api/demo/disable, GET /api/demo/status
GET /api/demo/templates, GET /api/demo/templates/{template_id}
"""
from fastapi import APIRouter, HTTPException
from services.demo_state import DemoState

router = APIRouter(prefix="/api/demo", tags=["Demo Mode"])


@router.post("/enable")
def enable_demo():
    DemoState.enable()
    return DemoState.status()


@router.post("/disable")
def disable_demo():
    DemoState.disable()
    return DemoState.status()


@router.get("/status")
def get_demo_status():
    return DemoState.status()


@router.get("/templates")
def get_templates():
    """Liste des profils demo disponibles."""
    from services.demo_templates import get_all_templates
    return {"templates": get_all_templates()}


@router.get("/templates/{template_id}")
def get_template_detail(template_id: str):
    """Detail d'un profil demo."""
    from services.demo_templates import get_template
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template non trouve")
    return tpl
