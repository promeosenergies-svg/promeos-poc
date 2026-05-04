# ADR-008 — Cohabitation `/api/energy/intensity` vs `/api/portfolio/intensity`

**Statut** : Draft (validation Sprint C-4 amont)
**Date** : 2026-05-04
**Sprint** : C-4 amont (Phase 0)
**Personnes impliquées** : Amine (founder), Claude architect-helios + ems-expert
**Tracking dette** : `D-Sprint-C3-7d-ADR-Intensity-OPERAT-Naming-001`

---

## Contexte

Sprint C-3 Phase 3.4 a livré `GET /api/portfolio/intensity` (clôture dette `D-Phase4-3-Portfolio-Intensity-Backend-001`). L'audit security-auditor Phase 3.7d a relevé qu'un endpoint similaire pré-existait : `GET /api/energy/intensity`. Audit Phase 0 Sprint C-4 confirme :

| Endpoint | Source | Sémantique | Cas d'usage cardinal |
|---|---|---|---|
| `GET /api/energy/intensity` | `routes/energy.py:703` | `Meter readings` (timeseries réel mesuré) — `services/energy_intensity_service.py` | Cockpit/RegOps précision réelle (intensité kWh_m2_final + kWh_m2_primary par vecteur, ratio EP) |
| `GET /api/portfolio/intensity` | `routes/portfolio_intensity.py:33` | `Site.annual_kwh_total` snapshot patrimoine — `services/portfolio_intensity_service.py` | Patrimoine.jsx KpiStripItem global rapide (Σ kWh / Σ m² doctrine ratio des SOMMES) |

**Risque sans ADR** : divergence formule + quel endpoint est canonical pour quel KPI ? Anti-pattern doctrine §6.4 "1 SoT par concept réglementaire" potentiel.

### Différentiel cardinal

| Aspect | `/api/energy/intensity` | `/api/portfolio/intensity` |
|---|---|---|
| **Source data** | Meter readings timeseries (Enedis R6X + GRDF R171) | `Site.annual_kwh_total` snapshot (champ persisté) |
| **Granularité** | site OU portfolio (paramètre exclusif) | portfolio org-scopé (avec filtre `portefeuille_id` optionnel) |
| **Formule portfolio** | Moyenne pondérée par surface (legacy ems-expert) | **Σ(kWh) / Σ(m²) ratio des SOMMES** (doctrine PROMEOS Sprint C-3 P3.4) |
| **Précision** | Réel mesuré (haute fidélité) | Snapshot patrimoine (rafraîchissement périodique) |
| **Coût compute** | Élevé (aggregation timeseries N points) | Faible (1 query Site.annual_kwh_total) |
| **Couverture** | Limitée aux sites avec Meter readings | Tous sites avec `annual_kwh_total` saisi |
| **Détail réponse** | `kWh_m2_final + kWh_m2_primary + ratio EP par vecteur + coverage` | `intensity_kwh_m2_total + intensity_kwh_m2_tertiaire + sites_count + sum_*` |

---

## Décision

### Principe cardinal : 2 endpoints distincts à pérenniser

**Pas de fusion.** Les 2 endpoints servent des cas d'usage **sémantiquement différents** :
- `/api/energy/intensity` = **précision réelle mesurée** (Cockpit/RegOps audit conformité OPERAT/DT)
- `/api/portfolio/intensity` = **agrégat patrimoine rapide** (Patrimoine.jsx KpiStripItem global, dashboard top-level)

Cohérent avec la doctrine PROMEOS "1 SoT par concept" : ce sont 2 concepts distincts, pas une duplication.

### Règles de routage applicatives

| Cas d'usage UI | Endpoint canonique | Justification |
|---|---|---|
| Cockpit KPI conformité OPERAT (Cabs target) | `/api/energy/intensity?site_id=X` | Précision Meter readings requise pour audit conformité |
| RegOps obligation DT (intensité réelle vs Cabs) | `/api/energy/intensity?site_id=X` | Idem |
| Patrimoine.jsx KpiStripItem global "Conso kWh/m² moy." | `/api/portfolio/intensity` | Snapshot patrimoine rapide, ratio SOMMES doctrine |
| Patrimoine.jsx ligne par site | `Site.intensity_kwh_m2_total` (cascade Site C-2 P4.2 — pas d'endpoint) | Pré-calculé persisté |
| Cockpit Decision dashboard (top-level KPI) | `/api/portfolio/intensity` | Snapshot rapide, pas besoin précision timeseries |
| EMS signature énergétique | `/api/energy/intensity` (timeseries) | Précision mesure obligatoire |

### Naming convention figée

- `kwh_m2_total` (snapshot patrimoine) ≠ `kWh_m2_final` (réel mesuré, énergie finale par vecteur)
- `kwh_m2_tertiaire` (snapshot, dénominateur `tertiaire_area_m2`) ≠ pas d'équivalent côté `/api/energy/intensity` (pas de notion tertiaire dans le service legacy)

→ Naming distinct **VOLONTAIRE** pour signaler la sémantique différente côté FE/API consumers.

### Anti-cycle préservé

- `/api/energy/intensity` ne lit JAMAIS `Site.annual_kwh_total` (sinon cycle avec cascade C-2 P4.2)
- `/api/portfolio/intensity` ne lit JAMAIS Meter readings (sinon performance dégradée + cycle inverse)

→ Source-guard à ajouter Sprint C-4 P4.5 : `test_intensity_endpoints_no_cross_dependency_source_guards.py`

### Documentation exigée Sprint C-4 P4.5

Header docstring obligatoire sur chaque endpoint avec :
1. **Source data** (Meter readings vs Site.annual_kwh_total)
2. **Cas d'usage canonique** (référence ce ADR-008)
3. **Pas de cohabitation** : pourquoi pas l'autre endpoint
4. **Cohérence** : cite ADR-008

---

## Conséquences

### Positives

- **Pas de breaking change** sur les 2 endpoints existants
- **Cohérence doctrinale** : 2 concepts distincts → 2 endpoints distincts (pas duplication)
- **Performance préservée** : portfolio rapide (1 query), energy précis (timeseries optimisé)
- **Documentation explicite** sur quel endpoint utiliser quand
- **Source-guard anti-cycle** ajouté Sprint C-4 (cardinal contre dérive future)

### Négatives / Compromis

- **Coût cognitif** : devs FE doivent connaître les 2 endpoints + leurs cas d'usage
  - Mitigation : header docstring + ADR-008 référencé partout + doc API publique (Swagger)
- **Risque divergence formule** dans le futur si ems-expert refacto `energy_intensity_service` sans coordination
  - Mitigation : source-guard test_intensity_*_doctrine_source_guards.py + ADR-008 cité dans CHANGELOG énergie

### Source-guards Sprint C-4

- `test_intensity_endpoints_no_cross_dependency_source_guards.py` (anti-cycle)
- `test_portfolio_intensity_ratio_des_sommes_source_guards.py` (doctrine Σ/Σ Phase 3.4 préservée)
- Mention ADR-008 obligatoire dans docstring de tout nouveau service `intensity_*`

### Tests anti-régression Sprint C-4

- 1 test cohérence entre les 2 endpoints sur dataset HELIOS demo (différentiel attendu documenté)
- 1 test perf bulk `/api/portfolio/intensity` 50/200/500 sites (< 500ms / 2s / 5s targets)
- 1 test `/api/energy/intensity` site_id_with_no_meter → fallback gracieux

---

## Alternatives considérées

| Option | Pourquoi rejetée |
|---|---|
| **Fusionner les 2 endpoints** sous `/api/intensity?source=meter|snapshot` | Casse contrat existant + complexifie le routing applicatif. Sémantiques différentes méritent endpoints différents. |
| **Déprécier `/api/energy/intensity`** au profit de portfolio_intensity | Casse Cockpit + RegOps qui ont besoin précision Meter readings. Intensité réelle ≠ snapshot. |
| **Déprécier `/api/portfolio/intensity`** au profit de energy_intensity | Casse Patrimoine.jsx KpiStripItem global + perf dashboard top-level. |
| **Aliaser** les 2 endpoints (`/api/portfolio/intensity` → `/api/energy/intensity?portfolio_id`) | Simplification apparente mais formule différente (ratio des sommes vs moyenne pondérée) → divergence métier. |
| **Naming unifié** `kwh_m2_total` partout | Perd la signalisation sémantique (snapshot vs réel, total vs final EF par vecteur). |

---

## Statut & validation

- **Draft** : 2026-05-04 (Sprint C-4 amont)
- **Validation requise** : architect-helios + ems-expert (energy_intensity_service legacy)
- **Implémentation Sprint C-4 P4.5** :
  - Documentation docstrings + Swagger
  - Source-guards anti-cycle
  - Tests cohérence + perf bulk

Closes (post-implémentation) : `D-Sprint-C3-7d-ADR-Intensity-OPERAT-Naming-001`.
