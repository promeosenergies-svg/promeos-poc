"""
PROMEOS - Import de sites via CSV
POST /api/import/sites  - Import massif (standalone, fonctionne si org existe)
GET  /api/import/template - Retourne la structure CSV attendue
"""

import io
import csv
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Organisation, Portefeuille, EntiteJuridique
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.onboarding_service import create_site_from_data, provision_site

router = APIRouter(prefix="/api/import", tags=["Import"])

_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
}

_CSV_COLUMNS = ["nom", "adresse", "code_postal", "ville", "surface_m2", "type", "naf_code"]


def _parse_surface(raw: str) -> float | None:
    """Parse surface_m2 supportant formats FR: '1 234,5' / '1234.5' / '1 234'."""
    if not raw or not raw.strip():
        return None
    s = raw.strip().replace("\u00a0", "").replace(" ", "")
    s = s.replace(",", ".")
    try:
        val = float(s)
        return val if val > 0 else None
    except ValueError:
        return None


@router.get("/template")
def get_csv_template():
    """Retourne la structure CSV attendue + un exemple."""
    return {
        "columns": _CSV_COLUMNS,
        "delimiter": ",",
        "encoding": "utf-8",
        "example_rows": [
            {
                "nom": "Bureau Paris",
                "adresse": "10 rue de la Paix",
                "code_postal": "75002",
                "ville": "Paris",
                "surface_m2": "1200",
                "type": "bureau",
                "naf_code": "",
            },
            {
                "nom": "Hotel Nice",
                "adresse": "Promenade des Anglais",
                "code_postal": "06000",
                "ville": "Nice",
                "surface_m2": "800",
                "type": "",
                "naf_code": "55.10Z",
            },
        ],
        "notes": [
            "Separateur: , ou ; (auto-detecte)",
            "Encodage: UTF-8 (avec ou sans BOM Excel)",
            "Si 'type' est vide, le code NAF est utilise pour classifier automatiquement",
            "surface_m2 optionnel (defaut: 1000 m2)",
        ],
    }


@router.post("/sites")
async def import_sites_csv(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Import massif de sites via CSV.
    Necessite une organisation existante.
    Les sites sont crees dans le premier portefeuille de l'organisation resolue.
    """
    org_id = resolve_org_id(request, auth, db)

    portefeuille = (
        db.query(Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .first()
    )
    if not portefeuille:
        raise HTTPException(status_code=400, detail="Aucun portefeuille pour cette organisation.")

    # MIME / extension validation
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Type de fichier invalide — CSV attendu")
    fname = (file.filename or "").lower()
    if fname and not fname.endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Extension invalide — .csv ou .txt attendu")

    # File size limit (50 MB)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50 Mo)")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")

    try:
        text = content.decode("utf-8-sig")
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Encodage invalide — le fichier doit être en UTF-8")

    first_line = text.split("\n")[0]
    delimiter = ";" if ";" in first_line else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows_list = list(reader)

    row_warning = None
    if len(rows_list) > 10000:
        row_warning = f"Fichier volumineux : {len(rows_list)} lignes. L'import peut prendre du temps."

    imported = []
    errors = []

    for row_num, row in enumerate(rows_list, start=2):
        try:
            nom = (row.get("nom") or "").strip()
            if not nom:
                errors.append({"row": row_num, "error": "Champ 'nom' manquant ou vide"})
                continue

            surface_raw = (row.get("surface_m2") or "").strip()
            surface = _parse_surface(surface_raw)

            site = create_site_from_data(
                db=db,
                portefeuille_id=portefeuille.id,
                nom=nom,
                type_site=(row.get("type") or "").strip() or None,
                naf_code=(row.get("naf_code") or "").strip() or None,
                adresse=(row.get("adresse") or "").strip() or None,
                code_postal=(row.get("code_postal") or "").strip() or None,
                ville=(row.get("ville") or "").strip() or None,
                surface_m2=surface,
            )
            prov = provision_site(db, site)
            imported.append(
                {
                    "id": site.id,
                    "nom": site.nom,
                    "type": site.type.value,
                    **prov,
                }
            )

        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})

    db.commit()

    return {
        "status": "ok",
        "imported": len(imported),
        "errors": len(errors),
        "sites": imported,
        "error_details": errors,
        "warning": row_warning,
    }
