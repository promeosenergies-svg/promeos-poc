"""
PROMEOS - Service d'import Sirene (stock full, delta, doublons).

Traite les fichiers CSV officiels INSEE :
  - stockUniteLegale_utf8.csv
  - stockEtablissement_utf8.csv
  - stockDoublons_utf8.csv

Usage CLI :
  python -m services.sirene_import --type full --ul path/stockUniteLegale.csv --etab path/stockEtablissement.csv
  python -m services.sirene_import --type delta --ul path/stockUniteLegale.csv --etab path/stockEtablissement.csv
  python -m services.sirene_import --type doublons --file path/stockDoublons.csv
"""

import csv
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.sirene import (
    SireneUniteLegale,
    SireneEtablissement,
    SireneDoublon,
    SireneSyncRun,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

# ======================================================================
# Mapping CSV → modele (couche explicite et testee)
# ======================================================================

# Colonnes CSV officielles → champs modele SireneUniteLegale
UL_COLUMN_MAP = {
    "siren": "siren",
    "statutDiffusionUniteLegale": "statut_diffusion",
    "dateCreationUniteLegale": "date_creation",
    "sigleUniteLegale": "sigle",
    "sexeUniteLegale": None,  # ignore (personnes physiques)
    "prenom1UniteLegale": "prenom1",
    "denominationUniteLegale": "denomination",
    "nomUniteLegale": "nom_unite_legale",
    "categorieJuridiqueUniteLegale": "categorie_juridique",
    "activitePrincipaleUniteLegale": "activite_principale",
    "nomenclatureActivitePrincipaleUniteLegale": "nomenclature_activite",
    "nicSiegeUniteLegale": "nic_siege",
    "etatAdministratifUniteLegale": "etat_administratif",
    "caractereEmployeurUniteLegale": "caractere_employeur",
    "trancheEffectifsUniteLegale": "tranche_effectifs",
    "anneeEffectifsUniteLegale": "annee_effectifs",
    "dateDernierTraitementUniteLegale": "date_dernier_traitement",
    "categorieEntreprise": "categorie_entreprise",
    "economieSocialeSolidaireUniteLegale": "economie_sociale_solidaire",
    "societeMissionUniteLegale": "societe_mission",
    "activitePrincipaleNAF25UniteLegale": "activite_principale_naf25",
}

# Colonnes CSV officielles → champs modele SireneEtablissement
ETAB_COLUMN_MAP = {
    "siren": "siren",
    "nic": "nic",
    "siret": "siret",
    "statutDiffusionEtablissement": "statut_diffusion",
    "dateCreationEtablissement": "date_creation",
    "trancheEffectifsEtablissement": "tranche_effectifs",
    "anneeEffectifsEtablissement": "annee_effectifs",
    "activitePrincipaleRegistreMetiersEtablissement": None,  # ignore
    "dateDernierTraitementEtablissement": "date_dernier_traitement",
    "etablissementSiege": "etablissement_siege",
    "nombrePeriodesEtablissement": None,  # ignore
    "complementAdresseEtablissement": "complement_adresse",
    "numeroVoieEtablissement": "numero_voie",
    "typeVoieEtablissement": "type_voie",
    "libelleVoieEtablissement": "libelle_voie",
    "codePostalEtablissement": "code_postal",
    "libelleCommuneEtablissement": "libelle_commune",
    "codeCommuneEtablissement": "code_commune",
    "etatAdministratifEtablissement": "etat_administratif",
    "enseigne1Etablissement": "enseigne",
    "denominationUsuelleEtablissement": "denomination_usuelle",
    "activitePrincipaleEtablissement": "activite_principale",
    "nomenclatureActivitePrincipaleEtablissement": "nomenclature_activite",
    "caractereEmployeurEtablissement": "caractere_employeur",
    "activitePrincipaleNAF25Etablissement": "activite_principale_naf25",
}

# Colonnes CSV doublons → champs modele
DOUBLONS_COLUMN_MAP = {
    "siren": "siren",
    "sirenDoublon": "siren_doublon",
    "dateDernierTraitementDoublon": "date_dernier_traitement",
}


def _map_row(row: dict, column_map: dict) -> dict:
    """Mappe une ligne CSV brute vers un dict de champs modele."""
    result = {}
    for csv_col, model_field in column_map.items():
        if model_field is None:
            continue
        val = row.get(csv_col, "").strip()
        if val == "":
            val = None
        # Boolean pour etablissementSiege
        if model_field == "etablissement_siege" and val is not None:
            val = val.lower() in ("true", "1", "oui")
        result[model_field] = val
    return result


# ======================================================================
# Generic upsert + CSV import (DRY)
# ======================================================================


def _upsert_batch(db: Session, model_class, key_field: str, key_column, batch: list) -> tuple:
    """Upsert generique. Retourne (inserted, updated)."""
    inserted = 0
    updated = 0
    keys = [r[key_field] for r in batch]
    existing = {getattr(obj, key_field): obj for obj in db.query(model_class).filter(key_column.in_(keys)).all()}
    for row in batch:
        key = row[key_field]
        if key in existing:
            obj = existing[key]
            if row.get("date_dernier_traitement") and (
                not obj.date_dernier_traitement or row["date_dernier_traitement"] > obj.date_dernier_traitement
            ):
                for k, v in row.items():
                    if k != "id":
                        setattr(obj, k, v)
                updated += 1
        else:
            db.add(model_class(**row))
            inserted += 1
    db.flush()
    return inserted, updated


def _import_csv(
    db: Session,
    csv_path: str,
    snapshot_date: datetime,
    column_map: dict,
    key_field: str,
    key_length: int,
    model_class,
    key_column,
    label: str,
    ddt_csv_col: Optional[str] = None,
    since: Optional[str] = None,
) -> dict:
    """Import generique CSV Sirene (full ou delta).

    Args:
        ddt_csv_col: si fourni, filtre delta par date_dernier_traitement > since.
        since: seuil delta (si None + ddt_csv_col, deduit du dernier sync_run).
    """
    # Resolve since for delta mode
    if ddt_csv_col and since is None:
        last_run = (
            db.query(SireneSyncRun)
            .filter(SireneSyncRun.sync_type.in_(["full", "delta"]), SireneSyncRun.status == "success")
            .order_by(SireneSyncRun.finished_at.desc())
            .first()
        )
        since = last_run.started_at.strftime("%Y-%m-%dT%H:%M:%S") if last_run else "1900-01-01"

    stats = {"read": 0, "inserted": 0, "updated": 0, "rejected": 0, "skipped": 0}
    batch = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["read"] += 1
            # Delta filter
            if ddt_csv_col and since:
                ddt = row.get(ddt_csv_col, "")
                if ddt and ddt <= since:
                    stats["skipped"] += 1
                    continue
            try:
                mapped = _map_row(row, column_map)
                if not mapped.get(key_field) or len(mapped[key_field]) != key_length:
                    stats["rejected"] += 1
                    continue
                mapped["snapshot_date"] = snapshot_date
                mapped["payload_brut"] = json.dumps(row, ensure_ascii=False)
                batch.append(mapped)
            except Exception as e:
                stats["rejected"] += 1
                logger.warning("%s row %d rejected: %s", label, stats["read"], e)
                continue

            if len(batch) >= BATCH_SIZE:
                ins, upd = _upsert_batch(db, model_class, key_field, key_column, batch)
                stats["inserted"] += ins
                stats["updated"] += upd
                batch = []

    if batch:
        ins, upd = _upsert_batch(db, model_class, key_field, key_column, batch)
        stats["inserted"] += ins
        stats["updated"] += upd

    db.flush()
    logger.info("%s: %s", label, stats)
    return stats


# Convenience wrappers (keep public API stable for tests)


def import_full_unites_legales(db, csv_path, snapshot_date, sync_run=None):
    return _import_csv(
        db,
        csv_path,
        snapshot_date,
        UL_COLUMN_MAP,
        "siren",
        9,
        SireneUniteLegale,
        SireneUniteLegale.siren,
        "import_full_ul",
    )


def import_full_etablissements(db, csv_path, snapshot_date, sync_run=None):
    return _import_csv(
        db,
        csv_path,
        snapshot_date,
        ETAB_COLUMN_MAP,
        "siret",
        14,
        SireneEtablissement,
        SireneEtablissement.siret,
        "import_full_etab",
    )


def import_delta_unites_legales(db, csv_path, snapshot_date, sync_run=None, since=None):
    return _import_csv(
        db,
        csv_path,
        snapshot_date,
        UL_COLUMN_MAP,
        "siren",
        9,
        SireneUniteLegale,
        SireneUniteLegale.siren,
        "import_delta_ul",
        ddt_csv_col="dateDernierTraitementUniteLegale",
        since=since,
    )


def import_delta_etablissements(db, csv_path, snapshot_date, sync_run=None, since=None):
    return _import_csv(
        db,
        csv_path,
        snapshot_date,
        ETAB_COLUMN_MAP,
        "siret",
        14,
        SireneEtablissement,
        SireneEtablissement.siret,
        "import_delta_etab",
        ddt_csv_col="dateDernierTraitementEtablissement",
        since=since,
    )


def import_doublons(
    db: Session,
    csv_path: str,
    snapshot_date: datetime,
) -> dict:
    """Import du fichier stockDoublons. Remplace entierement a chaque chargement."""
    # Purge anciens doublons
    db.query(SireneDoublon).delete()
    db.flush()

    stats = {"read": 0, "inserted": 0, "rejected": 0}
    batch = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["read"] += 1
            try:
                mapped = _map_row(row, DOUBLONS_COLUMN_MAP)
                if not mapped.get("siren") or not mapped.get("siren_doublon"):
                    stats["rejected"] += 1
                    continue
                mapped["snapshot_date"] = snapshot_date
                batch.append(mapped)
            except Exception:
                stats["rejected"] += 1
                continue

            if len(batch) >= BATCH_SIZE:
                for item in batch:
                    db.add(SireneDoublon(**item))
                stats["inserted"] += len(batch)
                batch = []
                db.flush()

    if batch:
        for item in batch:
            db.add(SireneDoublon(**item))
        stats["inserted"] += len(batch)
        db.flush()

    db.flush()
    logger.info("import_doublons: %s", stats)
    return stats


# ======================================================================
# Orchestrateur
# ======================================================================


def run_sirene_import(
    db: Session,
    sync_type: str,
    ul_path: Optional[str] = None,
    etab_path: Optional[str] = None,
    doublons_path: Optional[str] = None,
    snapshot_date: Optional[datetime] = None,
) -> SireneSyncRun:
    """Lance un import Sirene complet (full ou delta ou doublons).

    Retourne le SireneSyncRun avec les stats.
    """
    now = datetime.now(timezone.utc)
    snapshot = snapshot_date or now
    correlation_id = uuid.uuid4().hex[:12]

    source_files = [p for p in [ul_path, etab_path, doublons_path] if p]
    run = SireneSyncRun(
        sync_type=sync_type,
        source_file="; ".join(source_files) if source_files else None,
        started_at=now,
        status="running",
        correlation_id=correlation_id,
    )
    db.add(run)
    db.flush()

    def _merge(total, s):
        for k in total:
            total[k] += s.get(k, 0)

    try:
        total_stats = {"read": 0, "inserted": 0, "updated": 0, "rejected": 0, "skipped": 0}

        if sync_type == "doublons" and doublons_path:
            _merge(total_stats, import_doublons(db, doublons_path, snapshot))

        elif sync_type == "full":
            if ul_path:
                _merge(total_stats, import_full_unites_legales(db, ul_path, snapshot))
            if etab_path:
                _merge(total_stats, import_full_etablissements(db, etab_path, snapshot))

        elif sync_type == "delta":
            if ul_path:
                _merge(total_stats, import_delta_unites_legales(db, ul_path, snapshot))
            if etab_path:
                _merge(total_stats, import_delta_etablissements(db, etab_path, snapshot))
        else:
            raise ValueError(f"sync_type invalide: {sync_type}")

        run.finished_at = datetime.now(timezone.utc)
        run.lines_read = total_stats["read"]
        run.lines_inserted = total_stats["inserted"]
        run.lines_updated = total_stats["updated"]
        run.lines_rejected = total_stats["rejected"]
        run.status = "success"

    except Exception as e:
        db.rollback()
        # Re-create run record after rollback (previous was lost)
        failed_run = SireneSyncRun(
            sync_type=sync_type,
            source_file="; ".join(source_files) if source_files else None,
            started_at=now,
            finished_at=datetime.now(timezone.utc),
            status="failed",
            error_message=str(e)[:2000],
            correlation_id=correlation_id,
        )
        db.add(failed_run)
        db.commit()
        logger.error("sirene_import failed [%s]: %s", correlation_id, e)
        return failed_run

    db.commit()
    return run


# ======================================================================
# CLI entry point
# ======================================================================

if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(description="Import Sirene INSEE")
    parser.add_argument("--type", choices=["full", "delta", "doublons"], required=True)
    parser.add_argument("--ul", help="Chemin stockUniteLegale CSV")
    parser.add_argument("--etab", help="Chemin stockEtablissement CSV")
    parser.add_argument("--file", help="Chemin fichier doublons CSV")
    parser.add_argument("--snapshot-date", help="Date snapshot YYYY-MM-DD", default=None)
    args = parser.parse_args()

    from database.connection import SessionLocal

    snapshot = (
        datetime.strptime(args.snapshot_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.snapshot_date
        else datetime.now(timezone.utc)
    )

    db = SessionLocal()
    try:
        run = run_sirene_import(
            db=db,
            sync_type=args.type,
            ul_path=args.ul,
            etab_path=args.etab,
            doublons_path=args.file,
            snapshot_date=snapshot,
        )
        print(f"Import termine: {run.status}")
        print(
            f"  Lu: {run.lines_read}, Inseres: {run.lines_inserted}, "
            f"Mis a jour: {run.lines_updated}, Rejetes: {run.lines_rejected}"
        )
        if run.error_message:
            print(f"  Erreur: {run.error_message}")
    finally:
        db.close()
