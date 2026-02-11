# PROMEOS - Specification Fonctionnelle V1

**Date**: 2026-02-11
**Statut**: DRAFT - a valider par les fondateurs

---

## 1. Vision Produit

PROMEOS = cockpit independant du fournisseur pour piloter un patrimoine immobilier & energetique B2B en France.

**Promesse**: onboarding ultra simple + segmentation automatique + conformite reglementaire + diagnostic consommation + intelligence factures.

**Cible V1**: syndics/copro, collectivites, bailleurs, tertiaire multi-sites, industriels legers (10-500 sites).

---

## 2. FAITS (ce qui existe aujourd'hui)

### 2.1 Backend (FastAPI + SQLAlchemy + SQLite)

| Element | Quantite | Statut |
|---------|----------|--------|
| Endpoints API | 94 | Stable |
| Modeles SQLAlchemy | 23 classes | Stable |
| Tests pytest | 363 | 363/363 green |
| DB principale | promeos.db (SQLite) | 2.0 MB demo |
| DB Knowledge Base | kb.db (SQLite FTS5) | 176 KB |

### 2.2 Briques fonctionnelles livrees

| Brique | Contenu | Endpoints |
|--------|---------|-----------|
| **Patrimoine** | Organisation > Entite juridique > Portefeuille > Site > Batiment + Compteur + Usage | CRUD sites, compteurs |
| **RegOps** | 4 moteurs de regles YAML (Decret Tertiaire, BACS, APER, CEE P6), scoring composite, cache RegAssessment, job queue async | 4 endpoints |
| **Knowledge Base** | 12 items YAML, FTS5, archetypes, regles anomalie, recommendations, lifecycle (draft/validated/deprecated) | 20 endpoints |
| **Usages & Consommations** | Import CSV/JSON, profils, anomalies, recommendations ICE-scored, analytics engine | 7 endpoints |
| **Bill Intelligence** | Parser JSON/PDF, 20 regles audit, shadow billing L1, timeline 24 mois, couverture L0-L3, export CSV/HTML | 13 endpoints |
| **Electric Monitoring** | KPIEngine (Pmax/P95/P99/profils), PowerEngine (risque 0-100), DataQualityEngine (qualite 0-100), 12 alertes Tier-1 avec lifecycle | 6 endpoints |
| **Connecteurs** | RTE eCO2mix + PVGIS (live), Enedis + Meteo (stubs) | 3 endpoints |
| **Veille reglementaire** | 3 watchers RSS (Legifrance, CRE, RTE), deduplication hash | 4 endpoints |
| **IA** | 5 agents stub (explainer, recommender, data quality, exec brief, reg change) | 5 endpoints |
| **Cockpit executif** | KPIs portefeuille, worst-sites, echeances, plan d'action | 4 endpoints |
| **Mode demo** | Seed 120 sites, activation/desactivation, templates | 4 endpoints |

### 2.3 Frontend (React 18 + Tailwind + Vite)

| Page | Route | Fonction |
|------|-------|----------|
| Dashboard | `/` | Vue portefeuille 120 sites, filtres, statuts |
| Cockpit Executif | `/cockpit` | KPIs COMEX, graphiques Recharts |
| Detail Site | `/sites/:id` | Fiche site, obligations, evidences, score |
| RegOps | `/regops/:id` | Audit reglementaire, findings, actions |
| Plan d'action | `/action-plan` | Actions priorisees cross-sites |
| Conso & Usages | `/consommations` | Profils energetiques, anomalies |
| Monitoring | `/monitoring` | KPIs electriques, alertes, jour-type |
| Connecteurs | `/connectors` | Statut connecteurs, test/sync |
| Veille Reglementaire | `/watchers` | Evenements reglementaires, revue |

---

## 3. HYPOTHESES (a valider)

| # | Hypothese | Impact si faux | Validation prevue |
|---|-----------|---------------|-------------------|
| H1 | SQLite suffit pour le pilote (<500 sites, <10 users) | Migration PostgreSQL necessaire | Pilote client |
| H2 | Les 4 reglementations couvrent 80% des cas B2B tertiaire | Ajouter d'autres regles | Interviews clients |
| H3 | Le mode stub IA est suffisant pour la demo commerciale | Activer Claude API | Demo client |
| H4 | Les archetypes KB (12 items) couvrent les principaux segments | Enrichir KB a 40+ items | Retour pilote |
| H5 | L'absence d'auth est acceptable pour le POC interne | Ajouter JWT avant pilote externe | Decision fondateurs |
| H6 | Le shadow billing L1 (recalcul prix unitaires) suffit pour convaincre | Passer au L2 (optimisation tarifaire) | Feedback commercial |

---

## 4. DECISIONS prises

| # | Decision | Raison | Alternative ecartee |
|---|----------|--------|---------------------|
| D1 | SQLite mono-fichier | Simplicite, zero config, portable | PostgreSQL (trop tot) |
| D2 | Pas d'auth dans le POC | Vitesse dev, demo interne uniquement | JWT (prevu Sprint 1 prod) |
| D3 | Regles YAML statiques (pas de DSL) | Lisibles, auditables, versionables | Moteur de regles dynamique |
| D4 | React + Tailwind (pas de design system) | Rapidite, composants autonomes | MUI, Ant Design |
| D5 | KB en SQLite FTS5 (pas Elasticsearch) | Leger, embarque, suffisant pour 100 items | Elasticsearch (overkill V1) |
| D6 | Mode stub IA (pas de vraie API) | Fonctionnel sans cle API, cout zero | Integration directe Claude |

---

## 5. Modules V1 (livres)

### M1 - Patrimoine & Organisation
- CRUD Organisation > Entite > Portefeuille > Site
- Site: surface, NAF, parking, toiture, CVC, statuts reglementaires
- Batiment: puissance CVC, surface
- Compteur: PRM/PDL, vecteur energetique, puissance souscrite

### M2 - Conformite RegOps
- 4 moteurs de regles: Decret Tertiaire, BACS, APER, CEE P6
- Scoring composite: severite x urgence x confiance x completude
- Cache RegAssessment avec invalidation par hash
- Job queue async avec cascade (compteur -> site -> entite -> org)

### M3 - Knowledge Base
- 12 items YAML: archetypes batiment, regles anomalie, recommendations
- Recherche FTS5 + application automatique
- Lifecycle: draft -> validated -> deprecated
- Citations et provenance

### M4 - Usages & Consommations
- Import CSV/JSON de donnees de comptage
- Profils de consommation, anomalies, recommendations ICE
- Analytics engine KB-driven

### M5 - Bill Intelligence
- Parser factures JSON + extraction PDF (regex)
- 20 regles d'audit (coherence, TVA, TURPE, CTA, etc.)
- Shadow billing L1 (recalcul a partir des composants)
- Timeline 24 mois, couverture L0-L3, export CSV/HTML

### M6 - Electric Monitoring
- KPIs expert: Pmax, P95, P99, Pmean, Pbase, load factor, profils jour-type
- Risque puissance: score 0-100 (P95/Psub, depassements, volatilite)
- Qualite donnees: score 0-100 (gaps, doublons, DST, negatifs, outliers)
- 12 alertes Tier-1 avec lifecycle (open/ack/resolved)

---

## 6. Modules V2 (hooks prevus, non implementes)

| Module | Description | Hook existant |
|--------|-------------|---------------|
| **Auth JWT + RBAC** | Login, roles (admin/manager/viewer), protection endpoints | Spec dans docs/security/ |
| **Multi-tenancy** | Isolation par organisation_id | Modele Organisation existe |
| **PostgreSQL** | Migration SQLite -> Postgres | SQLAlchemy ORM ready |
| **Scenarios Achat** | Simulateur achat post-ARENH (spot vs forward vs PPA) | Backlog Brique 3 |
| **Connecteur Enedis** | OAuth DataConnect, releves reels | Stub connector existe |
| **Notifications** | Email/webhook sur alertes, echeances | AlertEngine pret |
| **CI/CD** | GitHub Actions, Docker | Fichiers vides presents |
| **IA live** | Agents Claude avec vraie API key | Mode stub fonctionnel |

---

## 7. Ecran "2 minutes" (promesse fondateur)

L'ecran Dashboard + Cockpit repond aux 3 questions en <2min:

1. **Conformite?** -> Cockpit: score global, repartition conforme/a risque/non conforme, worst-sites
2. **Pertes EUR?** -> Cockpit: risque financier total (penalites estimees), Bill Intelligence: anomalies factures
3. **Action #1?** -> Plan d'action: action la plus prioritaire (ICE-scored) avec savings estimes
