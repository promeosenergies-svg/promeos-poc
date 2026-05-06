# ADR-007 — Modèle RGPD consentement DataConnect + GRDF (cascade Org/DP)

**Statut** : Draft (validation Sprint C-4 amont)
**Date** : 2026-05-04
**Sprint** : C-4 amont (Phase 0)
**Personnes impliquées** : Amine (founder), Claude architect-helios + regulatory-expert + security-auditor
**Tracking dette** : `D-Sprint-C3-7d-ADR-RGPD-Consent-Detail-001` + `D-Sprint-C3-Org-Consentement-Modele-001` + `D-Sprint-C3-Cascade-Consentement-Activation-001`

---

## Contexte

Sprint C-3 Phase 3.7 audit pré-build a découvert que les champs ciblés par la dette `D-Phase6-Cascade-Org-Consentements-001` n'existent pas dans le modèle ORM :

- `Organisation.consentement_dataconnect_global` — absent
- `Organisation.consentement_grdf_global` — absent
- `DeliveryPoint.consentement_dataconnect_local` — absent
- `DeliveryPoint.consentement_grdf_local` — absent

Diagnostic Phase 0 Sprint C-4 confirme : seul `connector_token.py` expose `consent_expiry` + `consent_status` (PRM-spécifique DataConnect, pas Org/DP-level).

→ Décision pragmatique Phase 3.7 : **NE PAS livrer cascade fantôme**, scinder en 2 dettes successeurs (Modèle + Activation). Cet ADR figure le design AVANT implémentation Sprint C-4.

### Doctrine RGPD applicable

- **CNIL délibération 2024-XXX** : consentement explicite + traçabilité (qui/quand/version CGU/IP) obligatoire pour collecte tiers (Enedis DataConnect, GRDF ADICT)
- **RGPD art. 7** : preuve du consentement + droit de retrait à tout moment
- **CGU PROMEOS v1** : niveau d'agrégation = organisation OU PRM individuel (cf. `connector_token.consent_expiry` PRM-level existant)
- **Court-circuit ELD locales** (différenciateur Sprint C-3) : consentement GRDF national ≠ consentement ELD locale (Régaz / GreenAlp / R-GDS / etc. ont leur propre process)

---

## Décision

### Schéma cible Organisation (4 colonnes)

```python
class Organisation(Base):
    # ... champs existants ...

    # RGPD DataConnect (Enedis) — global org-level
    consentement_dataconnect_global = Column(Boolean, default=False, nullable=False)
    consentement_dataconnect_global_at = Column(DateTime(timezone=True), nullable=True)
    consentement_dataconnect_global_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    consentement_dataconnect_global_cgu_version = Column(String(20), nullable=True)

    # RGPD GRDF ADICT — global org-level (court-circuit ELD locales)
    consentement_grdf_global = Column(Boolean, default=False, nullable=False)
    consentement_grdf_global_at = Column(DateTime(timezone=True), nullable=True)
    consentement_grdf_global_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    consentement_grdf_global_cgu_version = Column(String(20), nullable=True)
```

### Schéma cible DeliveryPoint (4 colonnes)

```python
class DeliveryPoint(Base):
    # ... champs existants ...

    # RGPD DataConnect — local PRM-level (override org global)
    consentement_dataconnect_local = Column(Boolean, default=False, nullable=False)
    consentement_dataconnect_local_at = Column(DateTime(timezone=True), nullable=True)

    # RGPD GRDF — local PCE-level (uniquement si grd_code=GRDF, court-circuit ELD)
    consentement_grdf_local = Column(Boolean, default=False, nullable=False)
    consentement_grdf_local_at = Column(DateTime(timezone=True), nullable=True)
```

### Cascade activation (Phase 4.5 Sprint C-4)

| Trigger | Cible cascade | Condition |
|---|---|---|
| `Organisation.consentement_dataconnect_global = true` | Tous DPs élec de l'org → `consentement_dataconnect_local = true` | Si `local = false` (ne pas écraser opt-out individuel) |
| `Organisation.consentement_grdf_global = true` | DPs gaz `grd_code = "GRDF"` UNIQUEMENT → `consentement_grdf_local = true` | **Court-circuit ELD locales** (différenciateur RGPD Sprint C-3 P3.6) |
| `Organisation.consentement_*_global = false` (retrait) | Tous DPs concernés → `consentement_*_local = false` + log retrait | Audit trail obligatoire CNIL |

### Audit trail — niveau de détail

`AuditLog` (étendu Sprint C-2 P1.2 +6 cols) couvre déjà `correlation_id`, `org_id`, `user_id`, `field_modified`, `old_value`, `new_value`, `user_agent`. **Pas de nouvelle table dédiée**.

Nouvelles règles d'écriture pour les changements consentement :
1. `event_type = "RGPD_CONSENT_CHANGE"` (constante ajoutée enum)
2. `field_modified` = nom complet du champ booléen (ex : `Organisation.consentement_grdf_global`)
3. `old_value` / `new_value` = `"true"` / `"false"` (string)
4. `metadata` JSON optionnel = `{"cgu_version": "v1.2", "user_agent": "...", "ip_hash": "sha256:..."}` (IP hashée RGPD-safe)

→ Granularité : **1 entrée AuditLog par changement de champ booléen** (4 entrées max si user accepte tout en une action UI).

### Ce qui est explicitement HORS scope

- ❌ Table dédiée `consent_history` (overkill, AuditLog suffit)
- ❌ Versioning CGU complet (tracé via `cgu_version` string field)
- ❌ Stockage IP brute (hashée seulement, RGPD-safe)
- ❌ Notification email automatique sur retrait (Sprint C-5 polish)
- ❌ UI gestion consentement granulaire par PRM (Sprint C-5)

---

## Conséquences

### Positives

- **Différenciateur RGPD-compliant** confirmé : court-circuit ELD locales testable + traçable
- **Audit trail naturel** via `AuditLog` étendu (pas de nouvelle table)
- **Override local** possible (PRM individuel peut opt-out malgré global org)
- **Migration Alembic propre** : 4+4=8 cols ajoutées nullable (sauf 2 booléens NOT NULL default false)
- **Cascade testable** : 3 patterns explicites (activation org → propagation conditionnelle, retrait org → propagation totale + log)

### Négatives / Compromis

- 8 colonnes ajoutées au total (Org +4 + DP +4) → migration mineure mais signifiante
- **Cohérence org/local** = responsabilité applicative (pas de contrainte SQL `local <= global`) → tests cardinaux obligatoires
- IP hash via SHA-256 = pas réversible (audit trail forensique limité — accepté RGPD)
- Pas de purge automatique des `AuditLog RGPD_CONSENT_CHANGE` (rétention CNIL = 3 ans recommandé, à programmer Sprint C-7)

### Migration Alembic

```python
# alembic/versions/XXXX_rgpd_consentement_org_dp.py
def upgrade():
    op.add_column("organisations", sa.Column("consentement_dataconnect_global", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("organisations", sa.Column("consentement_dataconnect_global_at", sa.DateTime(timezone=True), nullable=True))
    # ... 8 columns total ...
    op.add_column("delivery_points", sa.Column("consentement_dataconnect_local", sa.Boolean(), nullable=False, server_default="false"))
    # ... 4 columns DP ...
```

Pattern réflexe Phase C : cleanup manuel des `op.drop_table()` Enedis legacy fantômes (cf. discipline anti-DROP, 6e épisode tenu).

### Source-guards à ajouter Sprint C-4

- `test_rgpd_consent_org_dp_no_direct_writes_source_guards.py` — interdit `Organisation.consentement_* =` direct hors `services/rgpd_consent_service.py`
- `test_rgpd_consent_audit_log_required_source_guards.py` — toute écriture consentement déclenche AuditLog `RGPD_CONSENT_CHANGE`

### Tests anti-régression Sprint C-4 P4.5

- 3 tests cascade activation (org → DP, court-circuit ELD GRDF, retrait org)
- 1 test override local (DP opt-out individuel malgré global)
- 1 test AuditLog RGPD_CONSENT_CHANGE généré
- 1 test idempotence (re-set même valeur ≠ nouveau log)

---

## Alternatives considérées

| Option | Pourquoi rejetée |
|---|---|
| **Table dédiée `consent_history`** | AuditLog étendu Sprint C-2 P1.2 suffit. Évite duplication infrastructure. |
| **Champ JSON `consentements`** sur Organisation | Pas de contraintes type, pas d'index, queries SQL pénibles. |
| **Stocker IP brute** | Violation RGPD art. 5 (minimisation). Hash SHA-256 suffisant pour audit. |
| **Notification email retrait automatique** | Scope Sprint C-5 polish UX. Hors scope ADR archi MVP. |
| **Sync auto avec connector_token.consent_expiry** | Complexité élevée vs valeur faible (connector_token = état runtime, Org/DP = consentement contractuel — sémantiques distinctes). |

---

## Statut & validation

- **Draft** : 2026-05-04 (Sprint C-4 amont)
- **Validation requise** : architect-helios + regulatory-expert (RGPD/CNIL) + security-auditor (PII/audit trail)
- **Implémentation** : Sprint C-4 Phase 4.5 (cascade) après migration modèle Phase 4.4
- **Extension audit trail** : Sprint C-5 Phase 5.3 (consentement_*_by + cgu_version)

Closes (post-implémentation) : `D-Sprint-C3-7d-ADR-RGPD-Consent-Detail-001` + `D-Sprint-C3-Org-Consentement-Modele-001` + `D-Sprint-C3-Cascade-Consentement-Activation-001` + `D-Phase4-4-ADR-007-Consent-By-CGU-Version-001` (Phase 5.3).

---

## Implémentation Phase 5.3 actée (Sprint C-5, 2026-05-06)

ADR-007 ext (`consentement_*_by` + `cgu_version`) implémenté en **migration Alembic 9e propre** (`b86d01f19001`). Cumul Phase C : 9 migrations propres / 0 destructive.

### Audit trail RGPD complet livré

**Org +4 cols** : `consentement_{dataconnect|grdf}_{by|cgu_version}`
**DP +4 cols** : `consentement_{dataconnect|grdf}_local_{by|cgu_version}`

**FK `users.id` ondelete=SET NULL** cardinal — suppression user (RGPD droit oubli art. 17 RGPD) préserve l'historique de consentement (la trace persiste, la référence personnelle disparaît). Les 4 contraintes FK nommées :

- `fk_organisations_consent_dataconnect_by_users`
- `fk_organisations_consent_grdf_by_users`
- `fk_delivery_points_consent_dataconnect_local_by_users`
- `fk_delivery_points_consent_grdf_local_by_users`

### Helper enrichi `get_effective_consent_with_audit`

Signature stable : `(dp, type_: ConsentType) -> dict`

Retour dict 5 clés cardinales (contrat sérialisation API stable) :

- `active` : bool | None
- `by_user_id` : int | None
- `cgu_version` : str | None
- `at` : datetime | None
- `scope` : `"local"` | `"global"` | `"none"`

Hiérarchie ADR-007 préservée : DP._local prioritaire si non-null, sinon Org._global, sinon `scope="none"`. Lecture seule (Option B archi-helios Phase 4.5 maintenue).

### Cas d'usage cardinaux

- **Audit RGPD officiel CNIL** ("prouver que tel utilisateur a accepté tel jour la version X")
- **Cockpit RGPD UI Sprint C-5+** — affichage trace complète par PRM/PCE
- **Export RGPD droit d'accès personnel** (article 15 RGPD) — sérialisation API directement consommable

### Tests + source-guards

- `tests/test_org_dp_consentement_by_cgu_version.py` — 13 tests verts (CRUD Org/DP + ondelete SET NULL × 2 + helper 3 scopes + sérialisation contrat)
- `tests/source_guards/test_consent_audit_trail_structure_source_guards.py` — 4 SG verts (Org 4 cols + DP 4 cols + ondelete=SET NULL × 4 + helper signature stable)

### Cohérence doctrine "preuve d'origine + valeur"

Un consentement est désormais **traçable jusqu'au dernier détail** : qui (FK users.id), quand (DateTime tz=True existant Phase 4.4), sur quelle CGU (String 20), pour quel scope (local override vs global Org).

### Champs reportés Sprint C-7+ (non bloquants)

- `consentement_*_ip_hash` (String SHA-256) — IP hashée RGPD-safe pour audit forensique. Optionnel, à activer si CNIL/audit le requiert pré-pilote.
