# ADR-F-01 — Fournisseur entité normalisée (élimination chaîne libre `supplier_name`)

**Statut** : 🟢 ACCEPTED — Phase F1 cardinal post-Phase E (commit `ccd0c4e5` sur `claude/refonte-sol2`)
**Date** : 2026-05-08
**Sprint** : Phase F1 Tier 1 (P0 Vision Consolidée v1.3, 10.5 h granulaires)
**Décideurs** : architect-helios + bill-intelligence + regulatory-expert + security-auditor (post-design read-only)
**Supersede** : N/A (création initiale)
**Lié** : ADR-F-02 (à venir, parser PDF facture) · ADR-D-04 (validators EJ) · ADR-D-05 (Enum strict pattern)

## Contexte

Vision PROMEOS Consolidée v1.3 (08/05/2026) liste **3 P0 repo** pour passer le livré 48 % → 78 % :

1. **Fournisseur entité** (cet ADR) — 4-8 j/h
2. Parser PDF facture — séparé (ADR-F-02 à venir)
3. Parser contrat — séparé (ADR-F-03 à venir)

État actuel cardinal : `backend/models/billing_models.py:61` stocke le fournisseur en chaîne libre :

```python
supplier_name = Column(String(200), nullable=False)
```

Conséquences mesurables :
- **Aucune mutualisation cross-sites** — 8 PDLs seedés Phase V113 → 8 entrées textuelles potentiellement divergentes (`"EDF"` / `"E.D.F."` / `"EDF Entreprises"`)
- **Pas de SIREN/TVA intra/contact stable** — bloque réconciliation parser PDF facture (P0-Vision-2) et bridge eIDAS (Universign/Yousign Advanced 3-5 k€/an Compliance+ v1.3)
- **Pas de catalogue partagé** — chaque org doit ressaisir EDF/Engie/TotalEnergies
- **Pas de scoring fournisseur cross-portefeuille** — bloque Marketplace P2 (couche 4 doctrine)
- **Pas de FK cohérente** — empêche `bill-intelligence` de tracer alertes hausse tarifaire par fournisseur

Pattern Phase D-4 EJ (18 épisodes anti-DROP) impose migration **idempotente non-destructive** + validators stricts.

## Sources & alignement doctrine

- Vision Consolidée v1.3 §"3 fixes P0 repo (4-8 j/h pour 48 %→78 % livré)"
- CLAUDE.md règle 1 (zero business logic FE) + règle 2 (org-scoping `resolve_org_id`)
- ADR-D-04 pattern validators stricts (SIREN 9 digits + TVA `FR\d{11}` + email RFC5322)
- ADR-D-05 pattern Enum strict canonique (Pilier 9)
- `backend/utils/naf_resolver.py:resolve_naf_code()` SoT NAF (CLAUDE.md règle 7)
- Pattern Phase E IDOR cardinal (commit `55a72b72`)
- Hiérarchie cardinale : Org → EJ → Portefeuille → Site → Bâtiment → Compteur → DeliveryPoint → **Fournisseur** transversal

## Options considérées

### Option A — Catalogue global lecture seule (Promeos master)

Table `suppliers` sans `organisation_id`, seed initial 10-15 fournisseurs FR. Org peut référencer mais pas créer.

- ✅ Mutualisation maximale, données canoniques uniques
- ✅ Cohérence parser PDF facture (clé SIREN unique nationale)
- ❌ Bloque fournisseurs régionaux/coopératives non-seedés (Enercoop régional, ELD locales)
- ❌ Aucune autonomie tenant — friction onboarding
- ❌ Anti-doctrine multi-tenant (Phase E IDOR pattern récent)

### Option B — Multi-tenant strict (`organisation_id` FK NOT NULL)

Chaque org possède son catalogue privé. Pas de partage.

- ✅ Org-scoping cardinal (CLAUDE.md règle 2)
- ✅ Pattern Phase E IDOR strict
- ❌ Duplication massive — 100 orgs × EDF = 100 lignes
- ❌ Bloque Marketplace P2 (scoring fournisseur cross-portefeuille impossible)
- ❌ Backfill impossible sans inférence org_id par contract.site_id → org

### Option C — Hybride catalogue partagé + override tenant ⭐

Table `fournisseurs` avec `organisation_id` **nullable** :
- `organisation_id IS NULL` → fournisseur **canonique global** (Promeos master, lecture seule pour tenants)
- `organisation_id NOT NULL` → fournisseur **privé** d'une org (ex: ELD régionale, négociation custom)

Résolution runtime : `get_fournisseurs_for_org(org_id)` UNION (canoniques + privés org).

- ✅ Mutualisation maximale (10-15 majeurs canoniques)
- ✅ Autonomie tenant (créer fournisseur privé)
- ✅ Org-scoping respecté (privés strictement scopés)
- ✅ Marketplace P2 compatible (scoring sur canoniques)
- ✅ Bridge parser PDF facture par SIREN (clé déterministe)
- ⚠️ Complexité légère : 1 contrainte unique composite

## Décision

**Option C — Hybride catalogue partagé + override tenant.**

Justification :
1. Aligné Vision v1.3 (Marketplace P2 + bridge eIDAS)
2. Respecte CLAUDE.md règle 2 (org-scoping) sans pénaliser mutualisation
3. Pattern Phase E IDOR maintenu sur fournisseurs privés
4. Backfill simple : 8 PDLs seedés → matching textuel 10-15 canoniques

### Décisions granulaires

| ID | Décision | Choix retenu |
|---|---|---|
| **D1** | Multi-tenant ou catalogue global ? | **Hybride** (`organisation_id` nullable, NULL = canonique Promeos) |
| **D2** | Migration `supplier_name` String → FK | **Miroir transitoire** : conserver `supplier_name` String + ajouter `fournisseur_id` FK nullable. Hard-cut Phase F2 ADR séparé après backfill validé |
| **D3** | Validators stricts | **Cohérent ADR-D-04 EJ** : SIREN 9 chiffres (`^\d{9}$`), TVA FR (`^FR\d{11}$`), email via EMAIL_RFC5322_PATTERN named export, NAF via `resolve_naf_code()` |
| **D4** | Catalogue seed initial | **10 fournisseurs FR majeurs** (cf. §Seed canonique) |

## Modèle Fournisseur (cardinal)

```python
# backend/models/fournisseur.py (nouveau)
class Fournisseur(Base, TimestampMixin):
    __tablename__ = "fournisseurs"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(
        Integer, ForeignKey("organisations.id"),
        nullable=True, index=True,
        comment="NULL = catalogue canonique Promeos (lecture seule tenants). NOT NULL = privé org."
    )
    # Identité
    nom = Column(String(200), nullable=False, comment="Raison sociale")
    siren = Column(String(9), nullable=True, index=True, comment="SIREN 9 chiffres")
    tva_intra = Column(String(13), nullable=True, comment="FR + 11 chiffres")
    naf_code = Column(String(5), nullable=True, comment="Via resolve_naf_code()")

    # Type fourniture (Enum strict pattern ADR-D-05)
    type_fourniture = Column(
        Enum(TypeFournitureEnum),  # ELEC / GAZ / MULTI
        nullable=False,
    )

    # Contact + Web
    contact_email = Column(String(320), nullable=True, comment="RFC5322")
    contact_telephone = Column(String(30), nullable=True)
    site_web = Column(String(500), nullable=True)
    cgv_url = Column(String(500), nullable=True, comment="URL conditions générales")

    # Lifecycle
    actif = Column(Boolean, nullable=False, default=True, index=True)

    # Bridge eIDAS (Compliance+ v1.3)
    signataire_nom = Column(String(200), nullable=True)
    signataire_email = Column(String(320), nullable=True, comment="Bridge Universign/Yousync")

    __table_args__ = (
        UniqueConstraint("siren", "organisation_id", name="uq_fournisseur_siren_org"),
        Index("ix_fournisseur_org_actif", "organisation_id", "actif"),
    )

class TypeFournitureEnum(str, enum.Enum):
    ELEC = "ELEC"
    GAZ = "GAZ"
    MULTI = "MULTI"
```

## Migration EnergyContract (idempotente non-destructive)

**Phase F1 — Miroir transitoire** (D2 retenu) :

```python
# Alembic migration add_fournisseurs_table_and_fk.py
def upgrade():
    # 1. Créer table fournisseurs (idempotent)
    op.create_table("fournisseurs", ...)

    # 2. Ajouter FK nullable sur energy_contracts (NON-DESTRUCTIF)
    op.add_column("energy_contracts",
        sa.Column("fournisseur_id", sa.Integer, sa.ForeignKey("fournisseurs.id"), nullable=True, index=True)
    )
    # supplier_name reste pour Phase F1 (miroir transitoire)
```

**Phase F2 — Hard-cut** (sprint suivant, après backfill validé + tests verts) :
- ADR-F-04 séparé : DROP `supplier_name` après vérification 100 % FK peuplées

## Backfill (idempotent)

```python
# backend/scripts/backfill_fournisseur_id.py
SUPPLIER_NAME_TO_CANONICAL = {
    "EDF": "EDF",
    "E.D.F.": "EDF",
    "EDF Entreprises": "EDF",
    "Engie": "ENGIE",
    "ENGIE": "ENGIE",
    "TotalEnergies": "TOTALENERGIES",
    # ...
}

def backfill():
    for contract in session.query(EnergyContract).filter(EnergyContract.fournisseur_id.is_(None)):
        canonical_key = SUPPLIER_NAME_TO_CANONICAL.get(contract.supplier_name.strip())
        if canonical_key:
            f = session.query(Fournisseur).filter_by(
                nom=canonical_key, organisation_id=None
            ).first()
            if f:
                contract.fournisseur_id = f.id
    session.commit()
```

Idempotence garantie par filtre `fournisseur_id IS NULL`.

## Seed canonique (D4)

10 fournisseurs FR cardinaux (`backend/services/demo_seed/fournisseurs_canoniques.py`) :

| Nom | SIREN | Type | Note |
|---|---|---|---|
| EDF | 552081317 | MULTI | Historique élec |
| ENGIE | 542107651 | MULTI | Historique gaz + élec |
| TOTALENERGIES | 542051180 | MULTI | |
| EKWATEUR | 814488395 | ELEC | Vert |
| ALPIQ | 484549526 | ELEC | |
| ENERCOOP | 484223094 | ELEC | Coop vert |
| PLUM_ENERGIE | 813292475 | ELEC | |
| MINT_ENERGIE | 821530771 | MULTI | |
| OHM_ENERGIE | 851251411 | ELEC | |
| GAZ_DE_BORDEAUX | 552108220 | GAZ | ELD |

SIREN à vérifier `regulatory-expert` Phase F1.5.

## Conséquences

**Positives** :
- Réconciliation parser PDF facture par SIREN déterministe (P0 Vision v1.3 ADR-F-02)
- Bridge eIDAS Compliance+ (signataire_email)
- Marketplace P2 scoring fournisseur cross-portefeuille déblocable
- Mutualisation 10 canoniques évite duplication par tenant
- Pattern multi-tenant respecté (Phase E IDOR)

**Négatives** :
- 1 sprint miroir transitoire (`supplier_name` + `fournisseur_id` cohabitent) — discipline tests
- 1 contrainte unique composite (`siren`, `organisation_id`)

## Tiers d'implémentation (10.5 h granulaire)

1. **F1.1** — `models/fournisseur.py` + Enum (1 h)
2. **F1.2** — Migration Alembic `add_fournisseurs_table` idempotent (1 h)
3. **F1.3** — Migration Alembic `add_fournisseur_id_to_energy_contracts` FK nullable (0.5 h)
4. **F1.4** — Validators @validates strict cohérent ADR-D-04 (1 h)
5. **F1.5** — Seed canonique 10 fournisseurs FR (`demo_seed/fournisseurs_canoniques.py`) (1.5 h)
6. **F1.6** — Service `fournisseur_service.get_for_org(org_id)` UNION canoniques + privés (1 h)
7. **F1.7** — Script backfill idempotent (`scripts/backfill_fournisseur_id.py`) (1 h)
8. **F1.8** — 15 tests cardinaux (cf. §Tests) (2 h)
9. **F1.9** — Audit 3 passes pré-commit per `feedback_audit_3x_before_commit.md` (0.5 h)
10. **F1.10** — Endpoint `GET /api/fournisseurs` org-scopé via `resolve_org_id` (1 h)

**Total : 10.5 h ≈ 1.5 j/h** (dans la fourchette Vision v1.3 4-8 j/h).

## Tests cardinaux (15)

| ID | Description | Type |
|---|---|---|
| T-FOUR-01 | Création Fournisseur canonique (org_id=NULL) | unit |
| T-FOUR-02 | Création Fournisseur privé org (org_id=42) | unit |
| T-FOUR-03 | Validator SIREN 8 chiffres → ValueError | unit |
| T-FOUR-04 | Validator TVA `FRXX` → ValueError | unit |
| T-FOUR-05 | Validator email malformé → ValueError | unit |
| T-FOUR-06 | UniqueConstraint SIREN canonique → IntegrityError sur duplicate | unit |
| T-FOUR-07 | UniqueConstraint SIREN privé même org → IntegrityError | unit |
| T-FOUR-08 | SIREN identique cross-org privé → autorisé | unit |
| T-FOUR-09 | **IDOR** : org A ne voit pas fournisseurs privés org B (canoniques OK) | sec |
| T-FOUR-10 | Backfill idempotent : 2× exécution = même résultat | integ |
| T-FOUR-11 | Backfill : `supplier_name="EDF"` + `="E.D.F."` → même `fournisseur_id` | integ |
| T-FOUR-12 | Endpoint `GET /api/fournisseurs` retourne canoniques + privés org | api |
| T-FOUR-13 | Endpoint refuse mutation fournisseur canonique par tenant | sec |
| T-FOUR-14 | Source-guard : aucun nouvel `EnergyContract` créé sans `fournisseur_id` post-F2 | guard |
| T-FOUR-15 | Migration Alembic : up + down idempotents | migration |

Cible : **15 tests verts** + 0 régression baseline.

## Risques & mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| Backfill loupe variantes orthographiques (`"E D F"`, `"edf"`) | contrats orphelins | Mapping insensible casse + trim + log warnings |
| Org crée fournisseur privé avec SIREN canonique existant | doublon métier | Validator runtime : si SIREN match canonique → erreur 409 + suggestion |
| Migration `supplier_name` Phase F2 perd données | rollback impossible | Sauvegarde DB + ADR-F-04 dédié + tests T-FOUR-14 source-guard |
| ELD régionale absente seed | onboarding manuel | UI "Créer fournisseur privé" Phase F1.10 |

## Liens

- Vision Consolidée v1.3 : `memory/project_promeos_vision_consolidee_v1_3_2026_05_08.md` §"3 fixes P0 repo"
- ADR-D-04 (validators EJ pattern)
- ADR-D-05 (Enum strict canonique pattern)
- `backend/models/billing_models.py:61` (état actuel)
- `backend/utils/naf_resolver.py:resolve_naf_code()` (SoT NAF)
- Pattern Phase E IDOR commit `55a72b72`
- Pattern audit 3 passes `memory/feedback_audit_3x_before_commit.md`
