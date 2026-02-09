"""
PROMEOS Routes - Connectors endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from connectors.registry import list_connectors, get_connector

router = APIRouter(prefix="/api/connectors", tags=["Connectors"])


@router.get("/list")
def connectors_list():
    """Liste tous les connecteurs disponibles."""
    return {"connectors": list_connectors()}


@router.post("/{name}/test")
def test_connector(name: str):
    """Teste la connexion d'un connecteur."""
    connector = get_connector(name)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector.test_connection()


@router.post("/{name}/sync")
def sync_connector(
    name: str,
    object_type: str,
    object_id: int,
    db: Session = Depends(get_db)
):
    """Declenche la synchro d'un connecteur."""
    connector = get_connector(name)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    try:
        datapoints = connector.sync(db, object_type, object_id)
        return {
            "connector": name,
            "object_type": object_type,
            "object_id": object_id,
            "datapoints_created": len(datapoints)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
