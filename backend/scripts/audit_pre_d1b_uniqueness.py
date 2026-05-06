"""Sprint D1-B Pre-migration uniqueness audit (cardinal anti-corruption).

À exécuter AVANT la migration Alembic 15e (`483f25dd86d3`) pour vérifier
qu'aucun doublon existant ne ferait échouer l'ajout des contraintes UNIQUE :

- delivery_points.code unique global (C60+C85)
- batiments (site_id, nom) unique (C50)
- contract_pricing dates incohérentes (C108)

Usage :
    cd backend && python -m scripts.audit_pre_d1b_uniqueness

Sortie :
    - 0 doublon → migration safe (exit 0)
    - 1+ doublons → exit 1 + listing des conflits à résoudre manuellement
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def audit() -> int:
    """Returns 0 if migration safe, 1 if duplicates detected."""
    db_path = Path(__file__).resolve().parent.parent / "data" / "promeos.db"
    if not db_path.exists():
        print(f"[SKIP] Pas de DB locale ({db_path}) — audit ignoré (CI/dev test sans seed).")
        return 0

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    issues: list[str] = []

    # C60+C85 — DP code doublons
    cur.execute("SELECT code, COUNT(*) FROM delivery_points WHERE deleted_at IS NULL GROUP BY code HAVING COUNT(*) > 1")
    dp_dups = cur.fetchall()
    if dp_dups:
        issues.append(f"C60/C85 — {len(dp_dups)} doublon(s) DP code : {dp_dups[:5]}")

    # C50 — Batiment (site_id, nom) doublons
    cur.execute(
        "SELECT site_id, nom, COUNT(*) FROM batiments "
        "WHERE deleted_at IS NULL GROUP BY site_id, nom HAVING COUNT(*) > 1"
    )
    b_dups = cur.fetchall()
    if b_dups:
        issues.append(f"C50 — {len(b_dups)} doublon(s) batiment (site_id, nom) : {b_dups[:5]}")

    # C108 — ContractPricing dates inversées
    cur.execute(
        "SELECT id, period_code, effective_from, effective_to FROM contract_pricing "
        "WHERE effective_from IS NOT NULL AND effective_to IS NOT NULL "
        "AND effective_to <= effective_from"
    )
    cp_invalid = cur.fetchall()
    if cp_invalid:
        issues.append(f"C108 — {len(cp_invalid)} ContractPricing dates inversées : {cp_invalid[:5]}")

    conn.close()

    if issues:
        print("[FAIL] Pre-migration audit Sprint D1-B :")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRésoudre les conflits manuellement AVANT `alembic upgrade head`.")
        return 1

    print("[OK] Pre-migration audit Sprint D1-B : 0 doublon — migration safe.")
    return 0


if __name__ == "__main__":
    sys.exit(audit())
