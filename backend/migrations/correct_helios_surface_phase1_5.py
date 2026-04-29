"""Migration : correction surface HELIOS Phase 1.5 (Q4 audit Vue Exécutive).

Problème : la DB locale contient des `batiments` dupliqués pour les sites
HELIOS (re-seed sans purge ou pack mixte). Total observé = 35 000 m²
au lieu de 17 500 m² spécifiés dans `packs.py:helios.sites_explicit`.

Cible canonique (cf. `services/demo_seed/packs.py` lignes 137-290) :
  Site 1 (Siège Paris)        : 3 500 m²
  Site 2 (Lyon)               : 1 200 m²
  Site 3 (Toulouse)           : 6 000 m²
  Site 4 (Nice)               : 4 000 m²
  Site 5 (Marseille)          : 2 800 m²
  TOTAL                       : 17 500 m²

Stratégie : UPDATE ciblé (pas DELETE) — on conserve le 1er batiment de
chaque site (par ordre de création) et on **redistribue** la surface
cible sur l'ensemble des batiments existants. Ainsi :
  - Pas de FK cascade à gérer (Usage/Meter restent rattachés)
  - Le SUM(surface_m2) PAR site_id devient conforme à la spec
  - Idempotent : ré-exécution = nouveau check + redistribution si dérive

Réf : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.5 (Q4).
Ref doctrine : §0.D décision A — surface utile = base KPI kWh/m²/an.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "promeos.db"

# Cible canonique HELIOS — alignée packs.py:helios.sites_explicit[*].surface_m2
HELIOS_SURFACE_TARGETS_M2 = {
    "Siège HELIOS Paris": 3500,
    "Bureau Régional Lyon": 1200,
    "Entrepôt HELIOS Toulouse": 6000,
    "Hôtel HELIOS Nice": 4000,
    "École Jules Ferry Marseille": 2800,
}


def run_migration(db_path: Path = DB_PATH) -> dict:
    """Redistribue la surface_m2 par site HELIOS pour matcher la spec canonique.

    Returns:
        dict {sites_corrected, total_before, total_after, changed}
    """
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    summary: dict = {"sites_corrected": 0, "total_before": 0, "total_after": 0, "changed": False}

    # Total avant
    cursor.execute(
        "SELECT COALESCE(SUM(b.surface_m2), 0) FROM batiments b "
        "JOIN sites s ON s.id = b.site_id "
        "WHERE s.nom IN ({})".format(",".join("?" for _ in HELIOS_SURFACE_TARGETS_M2)),
        list(HELIOS_SURFACE_TARGETS_M2.keys()),
    )
    summary["total_before"] = cursor.fetchone()[0] or 0

    # Pour chaque site HELIOS canonique, redistribuer surface uniformément
    for site_name, target_m2 in HELIOS_SURFACE_TARGETS_M2.items():
        cursor.execute("SELECT id FROM sites WHERE nom = ?", (site_name,))
        site_row = cursor.fetchone()
        if site_row is None:
            continue
        site_id = site_row[0]

        cursor.execute(
            "SELECT id FROM batiments WHERE site_id = ? ORDER BY id",
            (site_id,),
        )
        bat_ids = [r[0] for r in cursor.fetchall()]
        if not bat_ids:
            continue

        per_bat_m2 = round(target_m2 / len(bat_ids), 1)
        for bat_id in bat_ids:
            cursor.execute(
                "UPDATE batiments SET surface_m2 = ? WHERE id = ?",
                (per_bat_m2, bat_id),
            )
        summary["sites_corrected"] += 1

    conn.commit()

    # Total après
    cursor.execute(
        "SELECT COALESCE(SUM(b.surface_m2), 0) FROM batiments b "
        "JOIN sites s ON s.id = b.site_id "
        "WHERE s.nom IN ({})".format(",".join("?" for _ in HELIOS_SURFACE_TARGETS_M2)),
        list(HELIOS_SURFACE_TARGETS_M2.keys()),
    )
    summary["total_after"] = cursor.fetchone()[0] or 0
    summary["changed"] = abs(summary["total_after"] - summary["total_before"]) > 0.5

    conn.close()
    return summary


if __name__ == "__main__":
    result = run_migration()
    print(
        f"HELIOS surface migration : {result['sites_corrected']} sites corrected · "
        f"total {result['total_before']:.0f} → {result['total_after']:.0f} m²"
    )
    if abs(result["total_after"] - 17500) > 0.5:
        print(
            f"⚠️  Total {result['total_after']:.0f} m² ≠ 17 500 m² (cible) — "
            "vérifier que les 5 sites HELIOS canoniques existent en DB."
        )
    sys.exit(0)
