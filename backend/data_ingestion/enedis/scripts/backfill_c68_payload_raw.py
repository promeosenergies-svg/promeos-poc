"""Backfill C68 derived columns from stored payload_raw.

This script reparses the raw per-PRM payload archived in enedis_flux_itc_c68
and updates only derived/queryable columns. It does not reload Enedis files and
does not mutate payload_raw.

Usage:
    cd promeos-poc
    PYTHONPATH=backend python -m data_ingestion.enedis.scripts.backfill_c68_payload_raw
    PYTHONPATH=backend python -m data_ingestion.enedis.scripts.backfill_c68_payload_raw --dry-run
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Allow direct execution from arbitrary working directories.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from database import FluxDataSessionLocal  # noqa: E402
from data_ingestion.enedis.models import EnedisFluxItcC68  # noqa: E402
from data_ingestion.enedis.parsers.c68 import C68ParseError, ParsedC68Row, parse_c68_payload  # noqa: E402


DERIVED_COLUMNS = (
    "contractual_situation_count",
    "date_debut_situation_contractuelle",
    "segment",
    "etat_contractuel",
    "formule_tarifaire_acheminement",
    "code_tarif_acheminement",
    "siret",
    "siren",
    "domaine_tension",
    "tension_livraison",
    "type_comptage",
    "mode_releve",
    "media_comptage",
    "periodicite_releve",
    "puissance_souscrite_valeur",
    "puissance_souscrite_unite",
    "puissance_limite_soutirage_valeur",
    "puissance_limite_soutirage_unite",
    "puissance_raccordement_soutirage_valeur",
    "puissance_raccordement_soutirage_unite",
    "puissance_raccordement_injection_valeur",
    "puissance_raccordement_injection_unite",
    "type_injection",
    "borne_fixe",
    "refus_pose_linky",
    "date_refus_pose_linky",
)


def _csv_payload_from_raw(raw_obj: dict[str, Any]) -> bytes:
    buffer = io.StringIO()
    fieldnames = list(raw_obj.keys())
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerow(raw_obj)
    return buffer.getvalue().encode("utf-8")


def _derive_row(row: EnedisFluxItcC68) -> ParsedC68Row:
    raw_obj = json.loads(row.payload_raw)
    if not isinstance(raw_obj, dict):
        raise C68ParseError("payload_raw must decode to an object")

    source_format = row.source_format.upper()
    if source_format == "JSON":
        payload_bytes = json.dumps([raw_obj], ensure_ascii=False).encode("utf-8")
    elif source_format == "CSV":
        payload_bytes = _csv_payload_from_raw(raw_obj)
    else:
        raise C68ParseError(f"unsupported source_format {row.source_format!r}")

    parsed = parse_c68_payload(payload_bytes, source_format, row.payload_member_name)
    if len(parsed.rows) != 1:
        raise C68ParseError(f"expected one parsed row from payload_raw, got {len(parsed.rows)}")
    return parsed.rows[0]


def _non_null_counts(rows: list[EnedisFluxItcC68]) -> dict[str, int]:
    return {column: sum(1 for row in rows if getattr(row, column) is not None) for column in DERIVED_COLUMNS}


def backfill_c68_payload_raw(*, dry_run: bool = False) -> dict[str, Any]:
    session = FluxDataSessionLocal()
    try:
        rows = (
            session.query(EnedisFluxItcC68)
            .filter(EnedisFluxItcC68.source_format.in_(("JSON", "CSV")))
            .order_by(EnedisFluxItcC68.id)
            .all()
        )
        before = _non_null_counts(rows)
        updated = 0
        failed: list[dict[str, str]] = []

        for db_row in rows:
            try:
                parsed_row = _derive_row(db_row)
            except (C68ParseError, json.JSONDecodeError, TypeError, ValueError) as exc:
                failed.append({"id": str(db_row.id), "error": str(exc)})
                continue

            changed = False
            for column in DERIVED_COLUMNS:
                value = getattr(parsed_row, column)
                if getattr(db_row, column) != value:
                    setattr(db_row, column, value)
                    changed = True
            if changed:
                updated += 1

        after = _non_null_counts(rows)
        if dry_run:
            session.rollback()
        else:
            session.commit()

        return {
            "dry_run": dry_run,
            "rows_seen": len(rows),
            "rows_updated": updated,
            "rows_failed": len(failed),
            "failed": failed[:20],
            "before": before,
            "after": after,
        }
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill C68 derived columns from payload_raw")
    parser.add_argument("--dry-run", action="store_true", help="Compute updates and roll them back")
    args = parser.parse_args()

    result = backfill_c68_payload_raw(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result["rows_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
