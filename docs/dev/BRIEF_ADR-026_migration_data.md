# BRIEF ADR-026 · Migration data legacy → V4

> **Statut** : `Proposed` → à acter par Amine avant production L3
> **Version** : v0.1
> **Date** : 2026-05-14
> **Branche cible** : `claude/refonte-sol2`
> **Doctrine source** : `docs/doctrine/doctrine_v4_classement_priorisation.md` v0.2
> **ADR amont** : `docs/dev/L2_ADR-025_architecture_v4.md` (commit `712da32a`)
> **Auteurs** : Amine + Claude (cadrage session 2026-05-14)

---

## 0. TL;DR exécutif

**ADR-026 = manuel de bascule sécurisé**, pas une simple note de migration.

Procédure opératoire complète pour basculer du **modèle legacy** (18 tables, ~9 modèles, 1 667 LoC frontend mortes) vers le **modèle V4** (8 tables, ActionCenterItem polymorphique, 6 tables filles dédiées) **sans perte d'historique POC** et **avec rollback garanti**.

**9 invariants doctrinaux non négociables** :

| # | Invariant |
|---|---|
| I1 | Zéro double-write — jamais d'écriture cross-modèle legacy + V4 |
| I2 | Backup = preuve exportée de l'ancien monde (Q2-α non négociable) |
| I3 | Alembic = schéma uniquement · seeds V4 = script Python dédié idempotent |
| I4 | Rollback = restore backup binaire + reseed · pas de replay event log |
| I5 | Backup triple artefact : `.backup` + `.sql` + JSON + checksum SHA256 |
| I6 | Suppression legacy 1 667 LoC après **STOP GATE manuel J+14** |
| I7 | Backup Q2-α mentionné ≥6× dans ce document |
| I8 | Observation J+14 minimum avant DROP tables legacy |
| **I9** | **Backup hors Git · receipt sanitizé in Git** (garde-fou sécurité) |

**7 arbitrages techniques Q19-Q25 actés** :

| Q | Décision finale |
|---|---|
| Q19-C | Triple artefact backup : binaire `.backup` + dump SQL texte + export JSON |
| Q20-A | Script Python idempotent `regen_seeds_v4.py` hors Alembic |
| Q21-A | Dossier daté self-contained + manifest + checksums SHA256 |
| Q22-A | Rollback complet seulement (pas de granulaire, pas de replay) |
| Q23-A | Script bash manuel + checklist J-1 (pas de cron silencieux) |
| Q24-A | STOP GATE J+14 obligatoire avant suppression Mois 5 |
| Q25-A | Dry-run staging J-7 obligatoire avec rapport diff |

**Plan opérationnel** :

```
Mois 2-3 : Coexistence (V4 tables existent vides, legacy continue à servir le FE)
Mois 4 J-7   : Dry-run staging complet (rapport diff exhaustif)
Mois 4 J-3   : Communication interne, fenêtre maintenance annoncée
Mois 4 J-1   : BACKUP TRIPLE ARTEFACT (sortie : dossier daté + receipt sanitizé)
Mois 4 J0    : Cutover (régen seeds V4 + feature flag ON + smoke tests J+0)
Mois 4 J+1 à J+13 : Observation (KPI suivis, aucun rollback déclenché)
Mois 5 J+14  : STOP GATE manuel binaire (8 critères tous cochés)
Mois 5 J+14+ : DROP tables legacy + DELETE 1 667 LoC FE + suppression services
Mois 6       : Stabilisation · backup conservé 12 mois (RGPD)
```

---

## 1. Périmètre et hors-scope

### 1.1 Périmètre ADR-026

L'ADR couvre :

- Procédure de backup triple artefact pré-cutover (binaire + SQL + JSON + checksum)
- Receipt sanitizé in Git (preuve d'exécution)
- Script de régénération seeds V4 idempotent (Python, hors Alembic)
- Plan détaillé cutover Mois 4 (J-7 dry-run → J+14 STOP GATE)
- Procédure de rollback complet en cas d'échec
- Checklist STOP GATE J+14 binaire avant suppression
- Procédure de suppression définitive Mois 5 (tables + LoC mortes + services)
- Rétention RGPD 12 mois post-suppression
- Critères de cohérence avec ADR-025 (architecture cible)
- Tests dry-run staging exhaustifs

### 1.2 Hors-scope ADR-026

- **ADR-025** : architecture V4 cible (schéma DB, services, API) — déjà acté
- **ADR-027 Sécurité org-scoping** : payload JWT, IDOR matrix, audit pen-test
- **ADR-028 Lifecycle states** : state machine, transitions, hooks
- **ADR-029 Evidence + audit trail** : politique rétention RGPD par event_type, formats acceptés

ADR-026 **référence** ces ADR mais ne les remplace pas.

---

## 2. Procédure de backup triple artefact (I5)

### 2.1 Les 3 artefacts obligatoires

```
/backups/promeos_pre_v4_YYYYMMDD_HHMMSS/
├── promeos.db.backup              ← Artefact 1 : binaire SQLite restorable
├── promeos.sql                     ← Artefact 2 : SQL texte (.dump), human-readable, PG-compatible
├── legacy_json/                    ← Artefact 3 : JSON par table, lisible & métier
│   ├── action.json
│   ├── anomaly.json
│   ├── anomaly_event.json
│   ├── action_plan.json
│   ├── action_plan_item.json
│   ├── ... (18 tables legacy au total)
│   └── _empty_tables.json          (les 10 tables vides Sprint 13)
├── MANIFEST.json                   ← Métadonnées : timestamp, tables, counts, schema version
├── CHECKSUMS.sha256                ← Hash SHA256 de chaque artefact
└── README.md                        ← Procédure restore (procédure dans le dossier)
```

### 2.2 Script `backup_pre_v4.sh` complet

```bash
#!/usr/bin/env bash
# scripts/migration/backup_pre_v4.sh
# Triple artefact backup pré-cutover V4
# Invariants : I5 (triple artefact) + I7 (≥6 mentions Q2-α) + I9 (hors Git)

set -euo pipefail

TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/promeos_pre_v4_${TS}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "BACKUP PRÉ-V4 — Cutover Mois 4 PROMEOS"
echo "Q2-α non négociable · I5 triple artefact"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}/legacy_json"

# ─── Artefact 1 : binaire SQLite restorable ───
echo "▶ Artefact 1/3 : binaire SQLite..."
sqlite3 promeos.db ".backup ${BACKUP_DIR}/promeos.db.backup"

# ─── Artefact 2 : SQL texte dump ───
echo "▶ Artefact 2/3 : SQL texte..."
sqlite3 promeos.db ".dump" > "${BACKUP_DIR}/promeos.sql"

# ─── Artefact 3 : JSON par table ───
echo "▶ Artefact 3/3 : JSON par table..."
python scripts/migration/export_legacy_to_json.py \
    --db promeos.db \
    --output "${BACKUP_DIR}/legacy_json/"

# ─── Manifest ───
echo "▶ Génération MANIFEST.json..."
python scripts/migration/generate_manifest.py "${BACKUP_DIR}"

# ─── Checksums ───
echo "▶ Génération CHECKSUMS.sha256..."
cd "${BACKUP_DIR}"
find . -type f -name "*.backup" -o -name "*.sql" -o -name "*.json" \
    | sort \
    | xargs -I{} sha256sum {} > CHECKSUMS.sha256

# ─── README restore ───
cp /repo/scripts/migration/templates/RESTORE_README.md "${BACKUP_DIR}/README.md"

# ─── Verification ───
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Backup terminé : ${BACKUP_DIR}"
echo "▶ Vérification :"
ls -la "${BACKUP_DIR}"
echo
echo "▶ MANIFEST :"
cat "${BACKUP_DIR}/MANIFEST.json"
echo
echo "▶ Checksums :"
cat "${BACKUP_DIR}/CHECKSUMS.sha256"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

### 2.3 Script Python `export_legacy_to_json.py`

```python
# scripts/migration/export_legacy_to_json.py
"""
Export legacy tables to JSON for auditability and reseed.
Invariant I5 : artefact JSON par table.
"""
import argparse, json, sqlite3
from pathlib import Path
from datetime import datetime

LEGACY_TABLES = [
    "action", "anomaly", "anomaly_event", "anomaly_detector",
    "action_plan", "action_plan_item",
    # ... 18 tables au total
]

def export_table(conn, table_name: str, output_dir: Path):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    output_file = output_dir / f"{table_name}.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump({
            "table": table_name,
            "row_count": len(data),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "schema_version": "legacy_pre_v4",
            "rows": data
        }, f, indent=2, default=str, ensure_ascii=False)

    return len(data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    empty_tables = []
    conn = sqlite3.connect(args.db)
    for table in LEGACY_TABLES:
        count = export_table(conn, table, output_dir)
        if count == 0:
            empty_tables.append(table)
        print(f"  ✓ {table} : {count} rows")

    # Marquer les tables vides
    with (output_dir / "_empty_tables.json").open("w") as f:
        json.dump({"empty_tables": empty_tables, "count": len(empty_tables)}, f, indent=2)

    conn.close()
    print(f"\n✓ Export terminé : {len(LEGACY_TABLES)} tables · {len(empty_tables)} vides")

if __name__ == "__main__":
    main()
```

### 2.4 Script Python `generate_manifest.py`

```python
# scripts/migration/generate_manifest.py
"""
Génère MANIFEST.json sanitizé pour Q2-α + I9 (receipt in Git).
"""
import sys, json, sqlite3, hashlib
from pathlib import Path
from datetime import datetime

def main():
    backup_dir = Path(sys.argv[1])

    # Compter rows par table depuis legacy_json/
    table_counts = {}
    legacy_json_dir = backup_dir / "legacy_json"
    for json_file in legacy_json_dir.glob("*.json"):
        if json_file.name.startswith("_"): continue
        with json_file.open() as f:
            data = json.load(f)
            table_counts[data["table"]] = data["row_count"]

    # Schema version legacy
    binary_file = backup_dir / "promeos.db.backup"
    binary_size = binary_file.stat().st_size

    manifest = {
        "backup_timestamp": datetime.utcnow().isoformat() + "Z",
        "schema_version_legacy": "v3.x_pre_v4",
        "schema_version_v4_target": "v4.0.0",
        "tables_exported": len(table_counts),
        "tables_with_data": sum(1 for c in table_counts.values() if c > 0),
        "tables_empty": sum(1 for c in table_counts.values() if c == 0),
        "total_rows": sum(table_counts.values()),
        "table_counts": table_counts,
        "binary_backup_size_bytes": binary_size,
        "artefacts": {
            "binary": "promeos.db.backup",
            "sql_dump": "promeos.sql",
            "json_dir": "legacy_json/",
            "checksums": "CHECKSUMS.sha256"
        },
        "operator": "TBD_fill_at_cutover",   # Sera rempli au moment du cutover
        "cutover_phase": "pre_cutover_backup"
    }

    with (backup_dir / "MANIFEST.json").open("w") as f:
        json.dump(manifest, f, indent=2)

    print("✓ MANIFEST.json généré")

if __name__ == "__main__":
    main()
```

---

## 3. Receipt sanitizé in Git (I9 cardinal)

### 3.1 Gitignore obligatoire

```gitignore
# ─── ADR-026 : backups hors Git (I9) ───
/backups/
*.backup
*.sql
promeos.db
**/legacy_json/

# Receipts sanitizés autorisés dans docs/migrations/
!docs/migrations/L3_cutover_receipts/RECEIPT_*.md
```

### 3.2 Format `RECEIPT_<TIMESTAMP>.md` sanitizé

```markdown
# CUTOVER RECEIPT · YYYYMMDD_HHMMSS

> **Statut** : Pre-cutover backup completed
> **Operator** : (à remplir au moment du cutover)
> **Date cutover prévue** : YYYY-MM-DD

## Backup metadata

- **Timestamp** : 2026-MM-DDTHH:MM:SSZ
- **Schema version legacy** : v3.x_pre_v4
- **Schema version V4 cible** : v4.0.0
- **Tables exportées** : 18 (8 actives + 10 vides Sprint 13)

## Counts par table (sanitizés)

| Table | Row count | Status |
|---|---|---|
| action | 142 | ACTIVE |
| anomaly | 387 | ACTIVE |
| anomaly_event | 1247 | ACTIVE |
| ... | ... | ... |
| action_plan | 0 | EMPTY (Sprint 13 dette) |
| ... | ... | ... |

## Checksums SHA256

| Artefact | SHA256 |
|---|---|
| promeos.db.backup | a3f7c9e2... (full hash) |
| promeos.sql | b2e8d4f1... |
| legacy_json/action.json | c5a1b9e3... |
| legacy_json/anomaly.json | d8f2a4c7... |
| ... | ... |

## Vérifications

- [ ] Restore test sur staging effectué (date : YYYY-MM-DD)
- [ ] Vérification cardinalité post-restore : OK
- [ ] Checksums vérifiés post-écriture : OK
- [ ] Dossier accessible et lisible : OK

## Notes operator

(Notes opérationnelles libres, sans PII)

---

**Backup conservé** : `/backups/promeos_pre_v4_YYYYMMDD_HHMMSS/` (hors Git, I9)
**Rétention** : 12 mois (RGPD CNIL)
**Procédure restore** : voir `README.md` dans le dossier de backup
```

### 3.3 Garde-fou anti-PII

Le script `generate_manifest.py` **ne contient aucune donnée utilisateur** :

- Pas de noms (`actor_name` exclu du manifest)
- Pas d'emails
- Pas de titres d'items
- Pas de descriptions
- Pas de payload JSONB

**Uniquement** : counts numériques, schema versions, timestamps, checksums, noms de tables.

**Test source-guard** à ajouter Mois 2 :

```python
def test_receipt_has_no_pii():
    """Vérifie que RECEIPT_*.md ne contient ni email, ni nom, ni payload."""
    receipts = Path("docs/migrations/L3_cutover_receipts").glob("RECEIPT_*.md")
    for receipt in receipts:
        content = receipt.read_text()
        # Patterns email
        assert not re.search(r'[\w.-]+@[\w.-]+', content), f"Email leak in {receipt}"
        # Patterns noms (à raffiner par règles métier)
        assert "actor_name" not in content
        assert "payload" not in content
        # Patterns données legacy
        assert "INSERT INTO" not in content
```

---

## 4. Régénération seeds V4 — script Python idempotent (Q20-A · I3)

### 4.1 Architecture

```
scripts/seeds_v4/
├── regen_seeds_v4.py                  ← Script principal
├── canonical/
│   ├── helios_canonical.yaml          ← Données canoniques HELIOS (5 sites)
│   ├── meridian_canonical.yaml        ← Données canoniques MERIDIAN (3 sites)
│   └── shared_canonical.yaml          ← Données partagées (enums, refs)
├── builders/
│   ├── action_center_items_builder.py
│   ├── event_log_builder.py
│   ├── evidence_builder.py
│   └── ...
└── tests/
    ├── test_idempotence.py            ← Run ×3 → same state
    ├── test_canonical_yaml.py         ← Validation YAML
    └── test_counts.py                 ← Counts attendus par scenario
```

### 4.2 Script `regen_seeds_v4.py`

```python
# scripts/seeds_v4/regen_seeds_v4.py
"""
Régénère intégralement les seeds V4 depuis canonicals YAML.
Idempotent : run ×N → même état final.

Invariants :
- I3 : Alembic = schéma · seeds = ici uniquement
- I4 : Reseed = part of rollback procedure
"""
import argparse, yaml
from pathlib import Path
from sqlalchemy.orm import Session

from backend.models import ActionCenterItem, ActionEventLog, Evidence
from backend.db import get_session

SCENARIOS = ["helios", "meridian"]
CANONICAL_DIR = Path(__file__).parent / "canonical"

def clear_scenario(db: Session, scenario: str):
    """Supprime tous les items d'un scenario (idempotence cardinale)."""
    org_id = get_org_id_for_scenario(scenario)
    db.query(ActionEventLog).filter(ActionEventLog.organisation_id == org_id).delete()
    db.query(Evidence).filter(Evidence.organisation_id == org_id).delete()
    db.query(ActionCenterItem).filter(ActionCenterItem.organisation_id == org_id).delete()
    db.commit()
    print(f"  ✓ Cleared scenario {scenario}")

def load_canonical(scenario: str) -> dict:
    yaml_file = CANONICAL_DIR / f"{scenario}_canonical.yaml"
    with yaml_file.open() as f:
        return yaml.safe_load(f)

def insert_scenario(db: Session, scenario: str, canonical: dict):
    """Insère items + events + evidences depuis YAML canonical."""
    for item_data in canonical["items"]:
        item = ActionCenterItem(**item_data)
        db.add(item)
    for event_data in canonical["events"]:
        event = ActionEventLog(**event_data)
        db.add(event)
    # ... evidences, scenarios, blockers, links, etc.
    db.commit()
    print(f"  ✓ Inserted scenario {scenario} : {len(canonical['items'])} items")

def regen_seeds_v4(scenarios: list[str], dry_run: bool = False):
    db = get_session()
    for scenario in scenarios:
        canonical = load_canonical(scenario)
        if not dry_run:
            clear_scenario(db, scenario)
            insert_scenario(db, scenario, canonical)
        else:
            print(f"  [DRY-RUN] Would clear and insert {scenario}")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="helios,meridian")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    scenarios = args.scenario.split(",")
    print(f"▶ Regen seeds V4 : {scenarios}")
    regen_seeds_v4(scenarios, dry_run=args.dry_run)
    print("✓ Seeds V4 régénérés")
```

### 4.3 Test d'idempotence

```python
# scripts/seeds_v4/tests/test_idempotence.py

def test_run_3_times_same_state():
    """
    Cardinal : le script doit produire le MÊME état après 3 runs successifs.
    """
    db = get_test_session()

    # Run 1
    regen_seeds_v4(["helios"])
    state_after_run_1 = capture_state(db, scenario="helios")

    # Run 2
    regen_seeds_v4(["helios"])
    state_after_run_2 = capture_state(db, scenario="helios")

    # Run 3
    regen_seeds_v4(["helios"])
    state_after_run_3 = capture_state(db, scenario="helios")

    assert state_after_run_1 == state_after_run_2 == state_after_run_3
```

---

## 5. Plan détaillé cutover Mois 4

### 5.1 J-7 — Dry-run staging (Q25-A obligatoire)

```bash
# Sur copie DB staging
./scripts/migration/dry_run_staging.sh

# Étapes du dry-run :
# 1. Backup triple artefact sur staging
# 2. Régénération seeds V4 sur staging
# 3. Smoke tests sur staging
# 4. Rapport diff : avant/après seeds V4
# 5. Performance benchmark : queries cardinales < budgets §9 ADR-025
```

**Output dry-run** : `docs/migrations/L3_cutover_receipts/DRY_RUN_<TS>.md` avec rapport diff exhaustif (tables avant/après, perfs, smoke tests OK/FAIL).

**Critères go/no-go J-7** :

- [ ] Dry-run terminé sans erreur
- [ ] Performance benchmark : 100% des queries < budgets ADR-025 §9
- [ ] Smoke tests : 100% green
- [ ] Rapport diff cohérent avec attendus

Si **un seul critère ❌** → reporter le cutover, investiguer, refaire dry-run.

### 5.2 J-3 — Communication interne

- Annoncer fenêtre maintenance (J0 09:00-11:00 UTC par exemple)
- Préparer canaux communication (Slack, mail)
- Confirmer disponibilité opérateur + backup operator

### 5.3 J-1 — BACKUP TRIPLE ARTEFACT (Invariant I5)

```bash
# Sur prod
./scripts/migration/backup_pre_v4.sh

# Vérification cardinaux :
# 1. Vérifier MANIFEST.json (counts cohérents)
# 2. Vérifier CHECKSUMS.sha256 (3 artefacts hash OK)
# 3. Tester restore sur staging avec ce backup
# 4. Commit RECEIPT sanitizé dans docs/migrations/L3_cutover_receipts/
```

**Garde-fou opérateur** : la **checklist J-1** est cochée manuellement avant J0 :

```markdown
## Checklist J-1 (validation manuelle)

- [ ] Script backup exécuté sans erreur
- [ ] Dossier backup créé hors Git (/backups/promeos_pre_v4_TS/)
- [ ] 3 artefacts présents (binaire + SQL + JSON)
- [ ] MANIFEST.json contient counts cohérents
- [ ] CHECKSUMS.sha256 calculés
- [ ] README.md restore présent dans le dossier
- [ ] Restore test sur staging : OK (cardinalité matchent)
- [ ] RECEIPT sanitizé commité dans docs/migrations/L3_cutover_receipts/
- [ ] Backup accessible depuis serveur backup (read-only)
- [ ] Communication interne envoyée

❌ Un seul ❌ → cutover REPORTÉ, investigation déclenchée.
```

### 5.4 J0 — CUTOVER (heure H)

```bash
# Phase 1 : Activate feature flag (peut être instantané)
./scripts/migration/activate_v4_feature_flag.sh

# Phase 2 : Régénération seeds V4 (atomique)
./scripts/seeds_v4/regen_seeds_v4.py --scenario helios,meridian

# Phase 3 : Smoke tests J+0 immédiat
./scripts/migration/smoke_tests_post_cutover.sh
```

**Smoke tests J+0 obligatoires** :

```python
# scripts/migration/smoke_tests_post_cutover.py

def test_pilotage_loads():
    """GET /api/action-center/pilotage retourne 200 + summary cohérent."""
    response = client.get("/api/action-center/pilotage")
    assert response.status_code == 200
    assert "summary" in response.json()
    assert response.json()["summary"]["active_items_count"] > 0

def test_detail_drawer_opens():
    """GET /api/action-center/items/<id> retourne 200 + sections doctrine."""
    # ...

def test_impact_drawer_loads():
    """GET /api/action-center/impact retourne 200 + 6 dimensions."""
    # ...

def test_org_scoping_active():
    """Cross-org access → 404."""
    # ...

def test_audit_event_log_writes():
    """Mutation → entry dans action_event_log."""
    # ...
```

### 5.5 J+1 à J+13 — Observation

**KPI à suivre** :

- Nombre de requêtes 5xx par jour (cible : 0)
- Performance budgets respectés (cible : < budgets ADR-025 §9)
- Tickets utilisateurs internes (cible : 0 bloquant)
- Logs erreurs FastAPI (cible : pas de stack trace inédit)

**Si bug détecté** : décision binaire :

- **Bug mineur** → fix-forward (PR rapide)
- **Bug bloquant** → **ROLLBACK** déclenché (§6)

### 5.6 J+14 — STOP GATE manuel (Q24-A)

**Avant DROP tables legacy, checklist binaire 8 critères TOUS cochés** :

```markdown
## STOP GATE J+14 — Avant suppression legacy Mois 5

- [ ] Cutover Mois 4 effectué J0 sans rollback déclenché
- [ ] Smoke tests J+0 : 100% OK
- [ ] Observation J+1 à J+13 : aucun bug bloquant remonté
- [ ] Tests pyramide 50/30/15/5 : 100% green sur main
- [ ] Backup pré-cutover vérifié et accessible
- [ ] Restore test sur staging avec backup : OK
- [ ] Performance budgets respectés en prod-like : OK
- [ ] Validation utilisateur explicite : OUI

❌ Si UN seul ❌ → suppression REPORTÉE, investigation déclenchée.
```

---

## 6. Procédure rollback complet (Q22-A · I4)

### 6.1 Critères d'activation

Rollback déclenché si **un seul** des critères suivants est atteint :

- Bug bloquant P0 sécu (org-scoping leak, IDOR)
- Performance dégradée > 2× budgets ADR-025 §9 persistant > 24h
- Bug bloquant fonctionnel (impossible d'utiliser le Centre d'action)
- Décision opérateur (cas explicite, traçable)

### 6.2 Procédure rollback

```bash
# 1. Désactivation feature flag (frontend repasse sur API legacy)
./scripts/migration/deactivate_v4_feature_flag.sh

# 2. Vidage tables V4 (préparation reseed propre)
./scripts/migration/truncate_v4_tables.sh

# 3. Restore backup binaire (Invariant I4 : pas de replay event log)
./scripts/migration/restore_backup.sh /backups/promeos_pre_v4_<TS>/

# 4. Smoke tests legacy
./scripts/migration/smoke_tests_legacy.sh

# 5. Communication interne (rollback déclenché, V4 reportée)
```

### 6.3 Fenêtre rollback

- **Mois 4 J0 à Mois 5 J+14** : rollback possible
- **Mois 6+** : fix-forward seulement (suppression tables legacy actée)

### 6.4 Post-rollback

- Investigation root cause obligatoire
- Refonte plan cutover Mois 5+ après correctifs
- Backup conservé encore 12 mois

---

## 7. Suppression legacy Mois 5 (I6)

### 7.1 Trigger STOP GATE J+14

Si **8/8 critères STOP GATE** cochés manuellement → procéder à la suppression.

### 7.2 Procédure suppression

```bash
# 1. Backup additionnel pré-suppression (paranoïa cardinale)
./scripts/migration/backup_pre_v4.sh
# Génère un 2e backup, juste avant DROP

# 2. Migration Alembic destructive (DROP tables legacy)
alembic upgrade head
# Migration : drop_legacy_tables_post_v4.py
# DROP TABLE action;
# DROP TABLE anomaly;
# DROP TABLE anomaly_event;
# DROP TABLE action_plan;
# DROP TABLE action_plan_item;
# ... (18 tables au total)

# 3. Suppression code legacy
git rm backend/models/action.py backend/models/anomaly.py ...
git rm -r backend/services/anomaly_detection/
git rm -r backend/services/action_plan/
git rm frontend/src/components/legacy/AnomalyPage.tsx ...
# Total : 1 667 LoC FE mortes + 20 services Action/Anomaly

# 4. Suppression endpoints legacy
git rm backend/api/anomalies.py backend/api/action_plans.py ...
# Total : 51 endpoints legacy supprimés

# 5. Commit atomique
git commit -m "chore(action-center-v4): remove legacy code after STOP GATE J+14

After M4 cutover stability confirmed (J+14 observation OK), remove:
- 18 legacy tables (DROP via Alembic migration)
- 1 667 LoC dead frontend code
- 20 Action/Anomaly services
- 51 legacy endpoints

Backup conserved 12 months in /backups/promeos_pre_v4_<TS>/ (offline)
Receipt: docs/migrations/L3_cutover_receipts/RECEIPT_<TS>.md

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 7.3 Verification post-suppression

```bash
# Vérifier que rien de legacy ne subsiste
grep -r "from backend.models.action import" backend/  # Doit être vide
grep -r "AnomalyEvent" backend/                        # Doit être vide
grep -r "action_plan_item" backend/                    # Doit être vide

# Lancer toute la pyramide tests
pytest tests/ -v
pnpm test
```

---

## 8. Rétention RGPD (I7 + I8)

- **Backups physiques** : conservés 12 mois (recommandation CNIL pour preuves)
- **Receipts sanitizés in Git** : conservés indéfiniment (historique projet)
- **Logs cutover** : archivés 12 mois avec backup
- **Action event log V4** : politique rétention détaillée dans ADR-029

---

## 9. Tests dry-run staging (Q25-A)

### 9.1 Script `dry_run_staging.sh`

```bash
#!/usr/bin/env bash
# scripts/migration/dry_run_staging.sh

set -euo pipefail

STAGING_DB=${STAGING_DB:-promeos_staging.db}

echo "▶ Dry-run staging démarré"

# 1. Copy DB prod → staging
cp promeos.db ${STAGING_DB}

# 2. Backup triple sur staging
./scripts/migration/backup_pre_v4.sh

# 3. Régen seeds V4 sur staging
./scripts/seeds_v4/regen_seeds_v4.py --scenario helios,meridian

# 4. Smoke tests sur staging
./scripts/migration/smoke_tests_post_cutover.sh

# 5. Benchmark perfs
./scripts/migration/benchmark_v4_queries.sh

# 6. Rapport diff
./scripts/migration/generate_diff_report.sh > DRY_RUN_REPORT.md

echo "✓ Dry-run terminé"
echo "▶ Rapport : DRY_RUN_REPORT.md"
```

### 9.2 Critères rapport dry-run

- ✓ Backup triple artefact produit sans erreur
- ✓ Régen seeds V4 idempotent (test ×3)
- ✓ Smoke tests : 100% green
- ✓ Performance budgets : 100% respectés
- ✓ Pas de régression performance vs legacy

---

## 10. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Backup corrompu / non restorable | Faible | Très élevé | Triple artefact (I5) + checksums + restore test J-1 |
| Bug post-cutover bloquant | Moyen | Élevé | Rollback procédure §6 + fenêtre J0-J+14 |
| Suppression Mois 5 prématurée | Faible | Élevé | STOP GATE J+14 manuel binaire (I6) |
| Re-seed non idempotent | Faible | Moyen | Tests idempotence ×3 (§4.3) |
| PII fuite dans receipt Git | Faible | Élevé (RGPD) | I9 + source-guard test anti-PII (§3.3) |
| Dry-run J-7 ratée | Moyen | Élevé | Report cutover obligatoire, re-dry-run |
| Operator absent J0 | Faible | Élevé | Backup operator identifié J-3 |
| Connexion perdue mid-cutover | Faible | Élevé | Procédure atomique, étapes documentées, restart safe |

---

## 11. Renvois ADR amont/aval

- **ADR-022 (priorisation héritée)** : composantes du score préservées
- **ADR-025 (architecture V4)** : tables cibles + indexes
- **ADR-027 (sécurité org-scoping)** : preuves d'absence d'IDOR post-V4
- **ADR-029 (evidence + audit trail)** : politique rétention par event_type

---

## 12. Critères de validation finale ADR-026

### 12.1 Les 9 invariants vérifiés

- [ ] **I1** Zéro double-write — §2/§4/§7 confirment zéro écriture cross-modèle
- [ ] **I2** Backup = preuve exportée — §2.1 triple artefact + I9 receipt in Git
- [ ] **I3** Alembic = schéma · seeds Python — §4.1 architecture seeds_v4/ hors Alembic
- [ ] **I4** Rollback = restore + reseed — §6.2 procédure sans replay event log
- [ ] **I5** Triple artefact + checksum — §2.1 dossier daté + CHECKSUMS.sha256
- [ ] **I6** Suppression après STOP GATE manuel — §5.6 + §7.1 8 critères binaires
- [ ] **I7** Backup Q2-α mentionné ≥6× — TL;DR + §1 + §2 + §5 + §6 + §7 (objectif ≥6 mentions)
- [ ] **I8** Observation J+14 minimum — §5.5 + §5.6 + §7.1
- [ ] **I9** Backup hors Git · receipt sanitizé — §3 .gitignore + structure RECEIPT

### 12.2 Cohérence cross-documents

- [ ] Cohérence avec ADR-025 (architecture cible) — schéma V4 référencé
- [ ] Cohérence avec L1 (28 SUPPRIME confirmé Mois 5)
- [ ] Cohérence avec doctrine v0.2 (table rase Q2-α)
- [ ] Cohérence avec maquettes M1-M5 (rien à perdre côté UX)

### 12.3 Conformité Q6-A

- [ ] Aucun code Python/TypeScript modifié dans le commit
- [ ] Aucune table DB modifiée
- [ ] Seuls scripts shell et docs ajoutés

---

## 13. Métadonnées ADR

```yaml
adr_number: 026
title: Migration data legacy → V4 — manuel de bascule sécurisé
version: v0.1
status: Proposed
date: 2026-05-14
authors:
  - Amine (PROMEOS founder)
  - Claude (architecture co-pilot)
arbitrages_q19_q25:
  Q19: C   # triple artefact backup
  Q20: A   # seeds Python idempotent
  Q21: A   # dossier daté self-contained
  Q22: A   # rollback complet only
  Q23: A   # backup manuel + checklist
  Q24: A   # STOP GATE J+14 obligatoire
  Q25: A   # dry-run staging J-7
invariants_doctrinaux:
  I1: "Zéro double-write"
  I2: "Backup = preuve exportée Q2-α"
  I3: "Alembic schéma · seeds Python"
  I4: "Rollback = restore + reseed, pas replay"
  I5: "Triple artefact + checksum"
  I6: "Suppression STOP GATE J+14 manuel"
  I7: "Backup Q2-α mentionné ≥6×"
  I8: "Observation J+14 minimum"
  I9: "Backup hors Git · receipt sanitizé"
backup_q2_alpha_mentions: 6  # cible
total_scripts_documented: 6  # backup, export, manifest, regen_seeds, dry_run, restore
total_invariants: 9
next_adr: ADR-027 Sécurité org-scoping
```

---

**Statut** : `Proposed`. À acter par Amine avant L3 production.

Une fois acté, ADR-026 devient **le manuel de bascule** pour Mois 4 cutover. Aucune modification après acceptance sauf avenant versionné.
