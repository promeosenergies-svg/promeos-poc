"""
PROMEOS Routes - Connectors endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from connectors.registry import list_connectors, get_connector
from connectors.contracts import validate_mapping

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


@router.get("/validate")
def validate_connector_mapping(
    connector: str = Query(...),
    scope_type: str = Query("site"),
    scope_id: int = Query(1),
    db: Session = Depends(get_db),
):
    """Validate connector output against contract specs."""
    conn = get_connector(connector)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connector '{connector}' not found")

    # Try to get sample records
    try:
        records = conn.sync(db, scope_type, scope_id)
        # Convert datapoints to dicts if they are objects
        sample = []
        for r in records[:3]:
            if isinstance(r, dict):
                sample.append(r)
            elif hasattr(r, "__dict__"):
                sample.append({
                    "metric": getattr(r, "metric", None),
                    "value": getattr(r, "value", None),
                    "unit": getattr(r, "unit", None),
                    "ts_start": str(getattr(r, "ts_start", "")),
                })
            else:
                sample.append({"raw": str(r)})
    except Exception:
        sample = []

    report = validate_mapping(scope_type, sample, connector_name=connector)

    return {
        "connector": connector,
        "mapped_fields": report.mapped_fields,
        "missing_fields": report.missing_fields,
        "warnings": report.warnings,
        "valid": report.valid,
        "sample_count": len(sample),
    }
