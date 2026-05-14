# PROMEOS V4 · Brief Pair Reviewer Externe

> Version : v1.0 · 2026-05-14
> Document : Brief pour pair reviewer externe (dev senior · architecte · CTO advisory)
> Durée review estimée : 1-2h pour aperçu · 1 journée pour audit complet
> Confidentialité : interne PROMEOS · ne pas distribuer hors-cadre

---

## 0. Pourquoi cette review

Mois 1 du projet PROMEOS V4 vient de se terminer en mode **docs only** (aucune ligne de code modifiée pendant 4 semaines). Ce parti pris doctrinal a produit 20 commits / ~22 000 lignes de documentation structurée avant tout sprint backend.

**L'objectif de ta review** : vérifier que cette doctrine résistera à  6 mois de développement réel, et identifier d'éventuelles failles avant que les sprints backend démarrent.

C'est un investissement de 1-2h de ton temps qui peut éviter 2-4 semaines de refactor cardinal Mois 3-6.

---

## 1. Contexte projet (compacté)

**PROMEOS** est un SaaS B2B de management énergétique pour les ETI tertiaires français (cible : 10-500 sites multi-sites). Le pitch produit est "Fournisseur 4.0 sans la fourniture" — neutralité structurelle vs les fournisseurs traditionnels post-ARENH 2026.

**Le Centre d'Action V4** (objet de Mois 1) est la **brique cardinale du produit** : un cockpit unifié qui consolide alertes, anomalies, recommandations, preuves de conformité, et permet à  l'utilisateur (typiquement Responsable Énergie ETI) de piloter sa stratégie en 30 secondes (briefing du jour) ou 3 minutes (synthèse stratégique).

**État avant Mois 1** :

- Backend FastAPI + SQLAlchemy + SQLite (PostgreSQL-ready)
- Frontend React 18 + Vite + Tailwind v4
- Données démo : 5 sites HELIOS + 3 sites MERIDIAN
- 18 tables legacy dont 15 vides (Sprint 13 dette pure)
- ~173 rows data réelle dans 3 tables (action_items + bill_anomaly + anomaly KB)
- ~1 667 LoC frontend mortes
- 51 endpoints legacy hétérogènes
- 6 vocabulaires de statuts incompatibles
- 7 IDOR fixes historiques (signal de fragilité sécurité)

**Décision Q6-A acté en doctrine** : Mois 1 = docs only. Aucun code écrit. Tous les arbitrages tranchés en amont, par sessions Claude.ai dédiées, avant tout sprint backend.

---

## 2. Les 10 livrables Mois 1 (à reviewer)

| # | Livrable | Volume | Auto-éval | Statut |
|---|---|---|---|---|
| 1 | Doctrine v0.2 → v0.3 (+ avenant versionné) | ~6 800 lignes | N/A | Accepted |
| 2 | L1 Décisionnel (86 verdicts garde/migre/supprime/remplace/régénère) | ~1 460 lignes | N/A | Validé |
| 3 | ADR-025 Architecture V4 (8 tables · 20 indexes · 100 tests planifiés) | ~1 290 lignes | 32/32 | Accepted |
| 4 | ADR-026 Migration legacy → V4 (cutover Mois 4 · STOP GATE J+14) | ~1 119 lignes | 36/36 | Accepted |
| 5 | ADR-027 Sécurité org-scoping (IDOR matrix 288 · 50 source-guards · 4 outils CI) | ~1 354 lignes | 50/50 | Accepted |
| 6 | ADR-028 Lifecycle states (5 états · 10 transitions strictes · 6 closure_reasons) | ~1 173 lignes | 53/53 | Accepted |
| 7 | ADR-029 Evidence + audit trail (RGPD 16 events × 3 catégories · magic bytes MIME) | ~1 696 lignes | 48/48 | Accepted |
| 8 | L7 Data Dictionary V4 (manuel référence consolidé · 70 termes glossaire) | ~1 086 lignes | 40/30 | Accepted |
| 9 | L8 Plan suppression legacy Mois 5 J+14 (procédure opérationnelle) | ~600 lignes | 27/18 | Accepted |
| 10 | L9 Mois 2 backend pilot manual (8 sprints planifiés · 20 critères DoD) | ~635 lignes | 22/20 | Accepted |

**Cumul** :
- 49 invariants doctrinaux (9 Q + 9 I + 11 IS + 11 IL + 9 IE)
- 46 arbitrages cardinaux tranchés (Q1-Q46)
- 11 décisions cardinales Amine non-débattables
- 1 avenant doctrinal versionné (premier du projet)
- 0 fichier code modifié · 0 table DB modifiée · 0 script créé

---

## 3. Les 11 décisions cardinales Amine non-débattables

Ces décisions ne sont **pas négociables sans avenant doctrinal versionné**. Si tu identifies un risque sur l'une d'elles, c'est précieux.

| # | Décision | Référence | Justification |
|---|---|---|---|
| 1 | **Q2-α** table rase legacy + triple backup obligatoire (binaire + SQL + JSON + SHA256) | Doctrine v0.3 + ADR-026 | Sortie propre de 18 tables legacy hétérogènes |
| 2 | **Q6-A** Mois 1 docs only (TERMINÉ) | Doctrine v0.3 §0 | Investissement amont · zéro arbitrage à chaud Mois 2-6 |
| 3 | **Q9-B** `recurrence_groups` ≠ `duplicate_groups` (tables séparées) | Doctrine v0.3 §6.3 | Récurrence (cause-racine) ≠ Doublon (signature stricte) |
| 4 | **IL3** Réouverture admin + fresh token (<5min) + justification non vide obligatoire | ADR-028 §6.2 | Réversibilité encadrée vs sauvage |
| 5 | **IL4** `expired` interdit P0/P1 conformité/facturation (escalade à la place) | ADR-028 §4.2 | Pas de risque conformité enterré silencieusement |
| 6 | **IL5** `merged_duplicate` interdit si `recurrence_group` sans `duplicate_group` | ADR-028 §4.2 | Cohérence Q9-B au niveau closure |
| 7 | **IL7** Auto-close récurrence P0/P1 exige preuve OU justification | ADR-028 §4.3 | Pas de clôture cascade silencieuse sur priorités critiques |
| 8 | **IS11** Pas d'accès DB direct dans routes · pattern repository obligatoire | ADR-027 §6 | Défense en profondeur contre 7 IDOR historiques |
| 9 | **IE9** Validation MIME par magic bytes (anti-spoofing) · pas par header client | ADR-029 §6 | Anti-upload malware déguisé en PDF |
| 10 | **I9** Backup hors Git · receipt sanitizé in Git | ADR-026 §3 | Protection commit accidentel data clients |
| 11 | **Doctrine v0.3** = source de vérité unique (1er avenant versionné · pattern d'évolution) | Doctrine v0.3 §11 | Pas de modification doctrinale silencieuse possible |

---

## 4. Points d'attention pour la review (priorisés)

### 4.1 Architecture (ADR-025)

- **Single-table inheritance Q10-A** pour `ActionCenterItem` polymorphique (3 kinds : anomaly · decision · action) avec 7 tables filles dédiées
- **Pattern repository org-scopé IS11** : signature obligatoire `organisation_id` dans toutes les méthodes
- **20 indexes** documentés (performance budgets §9 ADR-025 critiques)
- **Discriminated union TypeScript Q14-A** pour cohérence FE typing

**Question pour toi** : la combinaison single-table inheritance + 7 tables filles est-elle scalable au-delà de ~100k items par org ? Avons-nous anticipé les requêtes de cardinalité élevée ?

### 4.2 Sécurité (ADR-027)

- **4 lignes de défense empilées** : middleware OrgScopingMiddleware + décorateur `@org_scoped` + pattern repository + 50 source-guards CI
- **IDOR matrix 288 cellules** (12 routes à 3 rôles à 2 orgs à 4 cas) tous auto-générés via pytest parametrize
- **Cross-org returns 404** (anti-énumération) plutôt que 403
- **Admin endpoints** exigent `role=admin` ET token <5min
- **CI bloquante** : Bandit + Semgrep + gitleaks + pip-audit + 50 source-guards

**Question pour toi** : les 4 lignes de défense suffisent-elles pour un audit type ANSSI/CNIL externe ? Manque-t-il un threat-model formel type STRIDE ?

### 4.3 Lifecycle (ADR-028)

- **5 états** : new → triaged → planned → in_progress → closed
- **10 transitions strictes** (no-ops `closed → closed` exclus)
- **6 closure_reasons révisés** : `resolved` · `dismissed` · `not_applicable` · `merged_duplicate` · `resolved_via_recurrence` · `expired`
- **HTTP 409 Conflict** sur toutes transitions interdites (avec payload `{code, message, hint}`)
- **Auto-close cascade récurrence** : si `recurrence_group.status = resolved`, fermeture cascade avec `resolved_via_recurrence` (jamais `merged_duplicate`)

**Question pour toi** : 10 transitions sont-elles trop rigides ? Manque-t-il un état intermédiaire (ex: `awaiting_evidence`) ? Les hooks pré/post couvrent-ils les cas réels métier ?

### 4.4 Evidence + audit trail RGPD (ADR-029)

- **Storage abstrait** `EvidenceStorageBackend` (filesystem Mois 2 · S3 V4.1+)
- **Validation MIME par magic bytes** (python-magic) avec double-check manuel
- **Validation manuelle obligatoire** + métadonnées extraites + flag confiance (Q41-D)
- **`expires_at = verified_at + 90 jours`** strict (IE6)
- **Rétention RGPD 3 catégories** : compliance 5 ans · business 3 ans · system 1 an
- **16 schemas Pydantic v1** avec `schema_version` (future-proof V4.1)
- **Purge mensuelle triple garde-fou** : feature flag + dry-run + trace `security_audit_log`
- **8 articles CNIL** référencés (5(1)(b), 5(1)(e), 5(2), 6, 15, 17, 30, 32)

**Question pour toi** : la matrice rétention 3 catégories est-elle défendable devant la CNIL ? Manque-t-il des éléments RGPD comme `consent_given_at`, `purpose_limitation_proof` ?

### 4.5 Méthodologie

- **Phase 0 audit cohérence** avant Phase 1 production (32-39 vérifications par ADR)
- **STOP GATE** systématique avant action destructive
- **Auto-évaluations chiffrées** binaires (32/32, 50/50, etc.)
- **Avenant doctrinal versionné** vs modification silencieuse
- **MCPs obligatoires** chaque session Claude Code : Context7 + code-review + simplify

**Question pour toi** : la méthodologie est-elle reproductible par une équipe sans accès à Claude ? Que se passe-t-il si Amine s'absente 2 semaines pendant Mois 2 ?

---

## 5. Questions cardinales à creuser (suggestions)

Si tu as 1 heure max, focalise sur **3 sujets** :

1. **Performance** : les 20 indexes ADR-025 §3 sont-ils suffisants pour les requêtes cardinales (pilotage, IDOR matrix, audit trail) ? Lire ADR-025 §9 budgets perf et challenger.

2. **Sécurité** : la défense en profondeur IS1-IS11 a-t-elle des angles morts ? Notamment : token refresh, CSRF cross-site, JWT replay. Lire ADR-027 §10 modèle de menace M1-M8.

3. **RGPD** : la matrice rétention 16 events × 3 catégories est-elle défendable ? Les endpoints art. 15 (export) et art. 17 (anonymisation) sont-ils suffisants ? Lire ADR-029 §10 + §7.

Si tu as 1 journée complète, ajoute :

4. **Doctrine + lifecycle** : les 11 invariants IL1-IL11 couvrent-ils tous les cas métier ? Notamment auto-close récurrence et expired. Lire ADR-028 §4 + §12.

5. **Migration legacy** : la procédure cutover Mois 4 (ADR-026 §5) + suppression Mois 5 (L8) sont-elles assez prudentes ? Manque-t-il une étape ?

6. **Sprint plan** : les 8 sprints Mois 2 (L9 §2) sont-ils réalistes en 4 semaines ? Le séquencement strict (M2-1 → M2-8) crée-t-il des goulots ?

---

## 6. Comment lire les livrables (ordre suggéré)

**Pour 1h max** :
1. Doctrine v0.3 §0 TL;DR + §7 (5-10 min)
2. L9 §0-2 Synthèse + sprint plan (15 min)
3. ADR-027 §0 TL;DR + §10 modèle de menace (15 min)
4. ADR-029 §0 TL;DR + §7 rétention RGPD (10 min)
5. M1-RISKS-CONSOLIDATED.md (10 min)

**Pour 1 journée** :
1. Tout ci-dessus (1h)
2. Lecture intégrale des 5 ADR (4h)
3. Lecture L1 décisionnel + L7 Data Dictionary (1h)
4. Lecture L8 procédure suppression (30 min)
5. Préparation feedback (1h30)

---

## 7. Output attendu de ta review

### Format suggéré

```markdown
# Review PROMEOS V4 Mois 1 · <Ton nom> · <Date>

## Verdict global
[Acceptable · Acceptable avec réserves · Refonte cardinale nécessaire]

## Points forts identifiés
1. ...
2. ...

## Risques identifiés (par criticité)
### P0 (bloquants)
- [Risque] · [Section/ADR] · [Suggestion fix]

### P1 (crédibilité menacée)
- ...

### P2 (optimisation)
- ...

## Questions ouvertes
1. ...

## Suggestions doctrine v0.4 (si pertinentes)
- ...

## Recommandation pour Sprint M2-1
[Démarrer · Démarrer avec ajustements · Reporter de N semaines]
```

### Canaux

- Email à `<adresse Amine>` avec ce template rempli
- Ou PR sur le repo dans `docs/dev/REVIEWS/M1-REVIEW-<ton-nom>.md`
- Ou discussion 1h en visio si tu préfères

---

## 8. Confidentialité

Ce document contient :

- ✅ Architecture et méthodologie : OK à discuter
- ✅ Tableaux d'invariants : OK
- ⚠️ Noms d'entités HELIOS / MERIDIAN : pseudonymes (pas de PII réelle)
- ❌ Pas d'informations clients réelles
- ❌ Pas de secrets / credentials / URLs production

Tu peux partager ce document avec un pair externe de confiance (CTO advisory, architecte senior, security expert) sans risque de fuite client.

---

## 9. Remerciements

Si tu acceptes cette review, **merci** — c'est un investissement bénévole précieux dont l'impact se mesurera sur 6 mois.

Ta réponse, même un simple "OK, peu de risques détectés", est utile pour Amine. Et si tu identifies UN seul risque P0 que nous avons manqué, ça vaut largement l'heure de lecture.

**Bonne review.**

---

## Annexes pratiques

### A. Liste des fichiers à lire

```
docs/doctrine/doctrine_v4_classement_priorisation.md          (v0.3 · ~6 800L)
docs/dev/L1_audit_centre_action_v4_decisional.md              (~1 460L)
docs/dev/L2_ADR-025_architecture_v4.md                         (~1 290L)
docs/dev/L3_ADR-026_migration_data.md                          (~1 119L)
docs/dev/L4_ADR-027_securite_org_scoping.md                    (~1 354L)
docs/dev/L5_ADR-028_lifecycle_states.md                        (~1 173L)
docs/dev/L6_ADR-029_evidence_audit_trail.md                    (~1 696L)
docs/dev/L7_data_dictionary_v4.md                              (~1 086L)
docs/dev/L8_plan_suppression_legacy.md                         (~600L)
docs/dev/L9_mois2_backend_pilotage.md                          (~635L)
docs/dev/M1-RISKS-CONSOLIDATED.md                              (annexe risques)
```

### B. Commands utiles pour explorer le repo

```bash
# Lister tous les ADR Accepted
ls docs/dev/L*_ADR-*.md

# Voir l'historique commits Mois 1
git log --oneline mois1-docs-only-complete

# Compter les invariants
grep -c "^### I[SLE][0-9]" docs/dev/L7_data_dictionary_v4.md

# Compter les mentions doctrine v0.3
grep -c "v0.3" docs/dev/L*.md

# Voir le sprint plan
sed -n '/## 2. Sprint plan/,/## 3/p' docs/dev/L9_mois2_backend_pilotage.md
```

### C. Contact

- **Auteur projet** : Amine · founder PROMEOS
- **Branche review** : `claude/refonte-sol2` (ou `main` si mergée)
- **Tag fin Mois 1** : `mois1-docs-only-complete`

---

**Fin du brief.** ~3 pages de lecture · 1-2h de review · output attendu : template §7.
