"""
PROMEOS Connectors — Enedis Open Data (ODS v2.1)

Datasets supportés :
- conso-sup36-region : agrégats >36 kVA par NAF × puissance × profil × région
- conso-inf36-region : agrégats ≤36 kVA par profil × puissance × région

API : https://opendata.enedis.fr/api/explore/v2.1/catalog/datasets/{id}/records
"""

import logging
import time
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session

from .base import Connector

logger = logging.getLogger(__name__)

ODS_BASE = "https://opendata.enedis.fr/api/explore/v2.1/catalog/datasets"
ODS_PAGE_SIZE = 100
ODS_TIMEOUT = 30
ODS_MIN_INTERVAL = 0.5  # 500ms entre requêtes


from utils.parsing import parse_iso_datetime as _parse_dt, safe_float as _safe_float, safe_int as _safe_int


class EnedisOpenDataConnector(Connector):
    name = "enedis_opendata"
    description = "Enedis Open Data — agrégats consommation, profils réglementaires"
    requires_auth = False
    env_vars = []

    def __init__(self):
        self._last_call = 0.0

    def test_connection(self) -> dict:
        """Vérifie l'accès à l'API ODS Enedis."""
        try:
            with httpx.Client(timeout=ODS_TIMEOUT) as client:
                resp = client.get(
                    f"{ODS_BASE}/conso-sup36-region/records",
                    params={"limit": 1},
                )
                if resp.status_code == 200:
                    return {"status": "ok", "message": "API Enedis Open Data accessible"}
                return {"status": "error", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def sync(self, db: Session, object_type: str = "benchmark", object_id: int = 0, date_from=None, date_to=None):
        """Synchronise les agrégats Enedis Open Data.

        object_type: "sup36" | "inf36" | "all" (défaut: import les deux)
        """
        results = []
        if object_type in ("sup36", "all", "benchmark"):
            n = self._sync_conso_sup36(db, date_from, date_to)
            results.append({"dataset": "conso-sup36-region", "rows_imported": n})
        if object_type in ("inf36", "all"):
            n = self._sync_conso_inf36(db, date_from, date_to)
            results.append({"dataset": "conso-inf36-region", "rows_imported": n})
        return results

    # Mapping ODS field → model attribute (shared between sup36 and inf36)
    _COMMON_FIELDS = {
        "horodate": ("horodate", _parse_dt),
        "region": ("region", None),
        "code_region": ("code_region", None),
        "profil": ("profil", None),
        "plage_de_puissance_souscrite": ("plage_puissance", None),
        "nb_points_soutirage": ("nb_points_soutirage", _safe_int),
        "total_energie_soutiree_wh": ("total_energie_wh", _safe_float),
        "courbe_moyenne_ndeg1_ndeg2_wh": ("courbe_moyenne_wh", _safe_float),
        "indice_representativite_courbe_ndeg1_ndeg2": ("indice_representativite", _safe_float),
    }

    def _sync_dataset(
        self, db: Session, dataset_id: str, model_cls, extra_fields: dict, date_from=None, date_to=None
    ) -> int:
        """Import générique d'un dataset ODS avec pagination."""
        batch_id = f"{dataset_id.split('-')[1]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        where = self._build_date_filter(date_from, date_to)

        total = 0
        offset = 0
        all_fields = {**self._COMMON_FIELDS, **extra_fields}

        while True:
            records = self._fetch_records(dataset_id, where, offset)
            if not records:
                break

            rows = []
            for rec in records:
                kwargs = {"import_batch": batch_id}
                for ods_key, (attr, converter) in all_fields.items():
                    val = rec.get(ods_key)
                    if val is None and attr == "profil":
                        val = ""  # profil NOT NULL — coalesce None et missing-key
                    kwargs[attr] = converter(val) if converter else val
                rows.append(model_cls(**kwargs))

            db.bulk_save_objects(rows)
            db.commit()
            total += len(rows)
            offset += ODS_PAGE_SIZE

            if len(records) < ODS_PAGE_SIZE:
                break

        logger.info("enedis_opendata: imported %d rows %s (batch %s)", total, dataset_id, batch_id)
        return total

    def _sync_conso_sup36(self, db: Session, date_from=None, date_to=None) -> int:
        from models.enedis_opendata import EnedisConsoSup36

        return self._sync_dataset(
            db,
            "conso-sup36-region",
            EnedisConsoSup36,
            extra_fields={"secteur_activite": ("secteur_activite", None)},
            date_from=date_from,
            date_to=date_to,
        )

    def _sync_conso_inf36(self, db: Session, date_from=None, date_to=None) -> int:
        from models.enedis_opendata import EnedisConsoInf36

        return self._sync_dataset(
            db,
            "conso-inf36-region",
            EnedisConsoInf36,
            extra_fields={},
            date_from=date_from,
            date_to=date_to,
        )

    def _fetch_records(self, dataset_id: str, where: str, offset: int, _retries: int = 0) -> list[dict]:
        """Fetch une page de records depuis l'API ODS v2.1."""
        self._rate_limit()

        params = {
            "limit": ODS_PAGE_SIZE,
            "offset": offset,
            "order_by": "horodate ASC",
        }
        if where:
            params["where"] = where

        try:
            with httpx.Client(timeout=ODS_TIMEOUT) as client:
                resp = client.get(f"{ODS_BASE}/{dataset_id}/records", params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                return results
        except httpx.HTTPStatusError as e:
            logger.warning("ODS API error %s for %s offset=%d: %s", e.response.status_code, dataset_id, offset, e)
            if e.response.status_code == 429 and _retries < 3:
                wait = 5 * (2**_retries)  # backoff exponentiel : 5, 10, 20s
                logger.info("Rate limited, retrying in %ds (attempt %d/3)", wait, _retries + 1)
                time.sleep(wait)
                return self._fetch_records(dataset_id, where, offset, _retries + 1)
            return []
        except Exception as e:
            logger.error("ODS API fetch failed for %s: %s", dataset_id, e)
            return []

    def _rate_limit(self):
        """Respecte l'intervalle minimum entre appels."""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < ODS_MIN_INTERVAL:
            time.sleep(ODS_MIN_INTERVAL - elapsed)
        self._last_call = time.monotonic()

    @staticmethod
    def _build_date_filter(date_from=None, date_to=None) -> str:
        """Construit le filtre where ODS pour les dates."""
        parts = []
        if date_from:
            d = date_from if isinstance(date_from, str) else date_from.isoformat()
            parts.append(f"horodate >= '{d}'")
        if date_to:
            d = date_to if isinstance(date_to, str) else date_to.isoformat()
            parts.append(f"horodate <= '{d}'")
        return " AND ".join(parts)
