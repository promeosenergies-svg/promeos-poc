# PROMEOS — Sprint Énergie P3.2 · Consommation hors horaires

**Date** : 2026-05-31
**Branche** : `claude/energie-p3-2-horaires-ouverture`
**Base** : `claude/refonte-sol2` tip `971b7560` (post-P3.1)
**Cible Brique** : Énergie — Consommations → Courbe de charge (extension)

---

## 1. Besoin utilisateur

Permettre à un responsable énergie de répondre à 4 questions opérationnelles :

1. Le site consomme-t-il quand il est censé être fermé ?
2. Quels jours et quelles heures posent problème ?
3. Combien cela représente en kWh ?
4. Quelle action lancer ?

Doctrine cardinale appliquée :

- **Zéro calcul métier frontend** : ranking, classification status,
  recommandations, talon nuit — tout vient du backend.
- **Aucun horaire inventé** : si `SiteOperatingSchedule` absent →
  `schedule.source = "missing"` + empty_state explicite.
- **Aucune économie certaine** : `estimated_cost_eur = null` tant
  qu'aucun prix n'est branché (champ prêt mais doctrine respectée).
- **Timezone Europe/Paris stricte**.
- **Aucune nouvelle route / menu / rail Énergie modifié** — extension
  in-place sous `/consommations/courbe`.

---

## 2. Modèle horaires retenu

**Aucune migration SQL requise** — le modèle `SiteOperatingSchedule`
existait déjà :

| Champ                | Rôle                                                   |
|----------------------|--------------------------------------------------------|
| `open_days`          | CSV `0,1,2,3,4` (0=Lundi)                              |
| `open_time/close_time` | Plage par défaut `HH:MM`                            |
| `is_24_7`            | Force grille 00:00-23:59 sur les 7 jours              |
| `intervals_json`     | Multi-plages par jour `{"0":[{"start","end"}, …]}`    |
| `exceptions_json`    | Jours fériés / fermetures `YYYY-MM-DD`                |
| `timezone`           | IANA (Europe/Paris par défaut)                         |

5 sites HELIOS déjà seedés avec horaires :

| Site                       | Type      | Horaires                            |
|----------------------------|-----------|-------------------------------------|
| Siège HELIOS Paris         | Bureau    | Lun-Ven 08:00-19:00                 |
| Bureau Régional Lyon       | Bureau    | Lun-Ven 08:00-19:00                 |
| Entrepôt HELIOS Toulouse   | Entrepôt  | Lun-Ven 06:00-20:00                 |
| Hôtel HELIOS Nice          | Hôtel     | 24/7                                |
| École Jules Ferry Marseille | École    | Lun-Ven 07:30-18:00                 |

---

## 3. Endpoint créé

### `GET /api/energy/off-hours-analysis`

**Query params** :

| Param        | Default | Description                         |
|--------------|---------|-------------------------------------|
| `scope`      | `site`  | `site | meter`                      |
| `scope_id`   | —       | Obligatoire                         |
| `from`/`to`  | —       | ISO 8601 Europe/Paris               |
| `granularity` | `hour` | `15min | 30min | hour | day`        |
| `org_id`     | auth    | Résolu depuis JWT > X-Org-Id > param |

**Erreurs standardisées** :
`ENERGY_SCOPE_INVALID`, `ENERGY_SCOPE_ID_REQUIRED`,
`ENERGY_GRANULARITY_TOO_FINE`, `ENERGY_RANGE_INVALID`.

**Réponse** (`OffHoursAnalysisResponse`) :

- `scope` + `period`
- `schedule` (`OpeningSchedule` : source declared/default/missing + 7 jours)
- `kpis` (4) :
  - `off_hours_kwh` (Σ kwh hors plages)
  - `off_hours_share_pct` (off / total × 100)
  - `weekend_off_hours_kwh` (Σ kwh weekday ∈ (5,6))
  - `night_baseload_kw` (moyenne kw_avg sur 00h-05h)
  - `estimated_cost_eur` = `null` (doctrine pas d'économie certaine)
- `slots` (tous les créneaux hors horaires)
- `top_off_hours` (top 10 par kwh desc, status recalculé contre total)
- `recommendations` (FR métier, severity info/warning/critical, CTA)
- `warnings` + `empty_state` + `provenance` racine

**Live preview** (curl) :

```
site=1 → 27.1 % off-hours, 12 slots, 2 recommandations (critical + talon nuit)
site=3 → 16.4 % off-hours, 9 slots, 2 recommandations (warning)
site=4 (Hôtel 24/7) → 0 % off-hours, 0 slot, 1 reco info
site=999 → empty_state « Horaires d'ouverture non renseignés pour ce site. »
```

---

## 4. UI ajoutée

Deux composants `frontend/src/ui/energy/` + branchement minimal sur
`LoadCurveTab.jsx` :

### 4.1 [`OffHoursAnalysisCard.jsx`](frontend/src/ui/energy/OffHoursAnalysisCard.jsx)

- Titre canonique « Consommation hors horaires »
- Sous-titre « Comparez la consommation mesurée aux horaires déclarés du site. »
- Badge horaires : `Horaires déclarés` / `Horaires par défaut` /
  `Horaires non renseignés`
- 7 jours Lun-Dim affichés avec plages ouvertes ou « fermé »
- 4 KPI cards via `KpiCardWithProvenance`
- Liste recommandations avec icône severity + CTA (`href="/action-center-v4"`)
- Empty state inline si `payload.empty_state`

### 4.2 [`OffHoursSlotsTable.jsx`](frontend/src/ui/energy/OffHoursSlotsTable.jsx)

- Titre canonique « Top créneaux hors horaires »
- Colonnes : Jour / Heure / kWh / kW moyen / Statut / Motif / Provenance
- Statut backend coloré (sain/vigilance/critique)
- `data-status` + `data-day` exposés pour test e2e

### 4.3 Branchement `LoadCurveTab.jsx`

- Import des 2 composants + helper `getOffHoursAnalysis`
- État local isolé `offHoursPayload` + `offHoursLoading`
- Effect dédié appelant l'endpoint quand `selectedSiteId`/period/granularity
  changent (granularity day → fallback hour)
- Sections rendues sous « Profil moyen par jour » et avant le cross-link
  Centre d'action

---

## 5. Tests

### 5.1 Backend pytest (14/14 GREEN)

`backend/tests/api/test_energy_off_hours_analysis_endpoint.py` :

| Suite                              | Tests | Statut |
|------------------------------------|-------|--------|
| `TestOpeningSchedule`              | 3     | ✅      |
| `TestOffHoursDetection`            | 4     | ✅      |
| `TestKpiNightBaseload`             | 1     | ✅      |
| `TestProvenance`                   | 2     | ✅      |
| `TestBuildResponseFull`            | 4     | ✅      |
| **Total**                          | **14/14** | ✅  |

### 5.2 Vitest frontend (17/17 GREEN)

| Suite                                       | Tests | Statut |
|---------------------------------------------|-------|--------|
| `OffHoursAnalysisCard.test.jsx`             | 10    | ✅      |
| `OffHoursSlotsTable.test.jsx`               | 7     | ✅      |
| **Total**                                   | **17/17** | ✅  |

### 5.3 Source-guards Python (71/71 GREEN)

- `frontend_no_business_calc` étendu : interdit `off_hours_share = a/b*100`
  et `off_hours_kwh = reduce(...)` en frontend.
- `frontend_energy_provenance_visible` : `METIER_PROPS` enrichi
  (`payload`, `slots`).
- `frontend_energy_visual_quality` : ajout
  `test_no_english_off_hours_jargon_p3_2` (interdit « Business hours »,
  « Off hours », « Opening hours ») et
  `test_off_hours_components_render_provenance_p3_2`.
- `energy_orchestration_provenance` : ajout tests `OpeningSchedule`,
  `OffHoursSlot`, `OffHoursRecommendation`, `OffHoursAnalysisResponse`
  toutes provenance obligatoire.

### 5.4 Playwright (4/4 GREEN)

`e2e/p3_off_hours_analysis.spec.js` (config dédiée
`playwright.p3_off_hours_analysis.config.js`) — desktop 1440 :

- 01 — section `off-hours-analysis-card` visible
- 02 — microcopy FR + absence anglais + CTA Centre d'action
- 03 — rail Énergie inchangé (Consommations / Performance / Usages /
  Diagnostics, pas de nouvelle entrée)
- 04 — capture pleine page documentaire

---

## 6. Captures

[`docs/audits/p3_2_off_hours/01_off_hours_default_1440.png`](docs/audits/p3_2_off_hours/01_off_hours_default_1440.png)
[`docs/audits/p3_2_off_hours/04_off_hours_doc_1440.png`](docs/audits/p3_2_off_hours/04_off_hours_doc_1440.png)

Capture documentaire montre :
- Section « Consommation hors horaires » rendue
- Badge `Horaires déclarés` visible
- 7 jours Lun-Ven 08:00-19:00 + Sam/Dim fermés
- CTA `Créer une action d'analyse` toujours présent

---

## 7. Dettes restantes

| Dette                                                    | Sévérité | Phase de fix |
|----------------------------------------------------------|----------|--------------|
| Période FE 30d ne couvre pas le seed (avril 2026 → KPI à `—` dans capture) | Bas | Sprint données démo / actualisation seed |
| `estimated_cost_eur` non câblé (volontaire : pas d'économie certaine) | Info | P3.3 « Tarification & impact financier » |
| Pas d'override par site dans l'UI (lecture seule horaires) | Bas | Phase admin /administration |
| 236 tests vitest pré-existants fail (env infra) — non lié P3.2 | Bas | Sprint infra-test |

Aucune dette doctrinale.

---

## 8. GO / NO-GO P3.3

**GO P3.3** — base décisionnelle stable :

- Endpoint `/api/energy/off-hours-analysis` fonctionne (4 sites prouvés
  via curl live, site=1 expose 27.1 % off-hours + 12 slots + 2 recos).
- Doctrine zéro calcul FE éprouvée + source-guards 71/71.
- Microcopy FR exclusive (« Consommation hors horaires », « Horaires
  déclarés »).
- Rail Énergie strictement inchangé.

Prochain sprint **P3.3** (proposition) :

- « Tarification & impact financier » — câbler `estimated_cost_eur`
  avec contrat actif + price_canonical (assomptions explicites
  « indicatif » + provenance).
- Ou « Override horaires UI » — formulaire de saisie + audit trail
  côté administration.
