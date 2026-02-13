"""
PROMEOS - EMS Consumption Explorer Routes
Timeseries, weather, energy signature, saved views.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/ems", tags=["EMS Explorer"])


@router.get("/health")
def ems_health():
    return {"status": "ok", "module": "ems_explorer"}
