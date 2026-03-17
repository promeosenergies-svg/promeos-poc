# KPI Formels PROMEOS — Documentation de référence

**Version :** 1.0
**Date :** 2026-03-17
**Statut :** Documenté depuis le code source

---

## 1. Score de conformité composite (compliance_score_composite)

| Champ | Valeur |
|-------|--------|
| **Nom** | Score de conformité réglementaire |
| **Modèle** | `Site.compliance_score_composite` |
| **Unité** | 0–100 (sans unité) |
| **Période** | Instantané, recalculé à chaque évaluation |
| **Périmètre** | Par site |
| **Source** | `services/compliance_score_service.py:143–265` |

**Formule :**
```
raw_score = (score_DT × 0.45 + score_BACS × 0.30 + score_APER × 0.25) / poids_applicable
critical_penalty = MIN(20, nb_findings_critiques × 5)
final_score = CLAMP(0, 100, raw_score − critical_penalty)
```

**Score par framework :**
1. `RegAssessment.compliance_score` si disponible
2. Sinon : `(ok_count + unknown × 0.5) / total × 100 − overdue_penalty`
3. Sinon : statut snapshot (CONFORME=100, A_RISQUE=50, NON_CONFORME=0)

**Grades :** A ≥ 85 | B ≥ 70 | C ≥ 50 | D ≥ 30 | F < 30

**Confiance :**
- `high` = 3/3 frameworks évalués
- `medium` = 2/3
- `low` = 0–1

---

## 2. Risque financier estimé (risque_financier_euro)

| Champ | Valeur |
|-------|--------|
| **Nom** | Risque financier estimé |
| **Modèle** | `Site.risque_financier_euro` |
| **Unité** | EUR (€) |
| **Période** | Instantané |
| **Périmètre** | Par site, agrégé par SUM au niveau org |
| **Source** | `services/compliance_engine.py:93–97` |

**Formule :**
```
BASE_PENALTY = 7 500 €
risque = BASE_PENALTY × nb(NON_CONFORME) + BASE_PENALTY × 0.5 × nb(A_RISQUE)
```

**Important :** Ce montant est une estimation indicative. Il ne constitue pas un calcul de pénalité réglementaire officielle.

---

## 3. Score de complétude site

| Champ | Valeur |
|-------|--------|
| **Nom** | Score de complétude patrimoniale |
| **Endpoint** | `GET /api/patrimoine/sites/{id}/completeness` |
| **Unité** | 0–100 (%) |
| **Période** | Instantané |
| **Périmètre** | Par site |
| **Source** | `routes/patrimoine/_helpers.py:357–400` |

**Formule :**
```
8 checks binaires :
  adresse        = site.adresse ET site.ville
  surface        = site.surface_m2 > 0
  type_site      = site.type non vide
  entite_juridique = site.portefeuille_id non nul
  delivery_point = COUNT(DeliveryPoint WHERE site_id) > 0
  contrat_actif  = COUNT(EnergyContract actif) > 0
  coordonnees    = site.latitude ET site.longitude
  siret          = site.siret non vide

score = ROUND(filled / 8 × 100)
```

**Niveaux :** complet ≥ 80 | partiel ≥ 50 | critique < 50

---

## 4. KPI Patrimoine (endpoint patrimoine_kpis)

| Champ | Valeur |
|-------|--------|
| **Endpoint** | `GET /api/patrimoine/kpis` |
| **Source** | `routes/patrimoine/sites.py:95–213` |

**KPI retournés :**

| KPI | Formule |
|-----|---------|
| total | COUNT(sites) scoped org |
| conformes | COUNT(sites WHERE statut_DT = CONFORME) |
| aRisque | COUNT(sites WHERE statut_DT = A_RISQUE) |
| nonConformes | COUNT(sites WHERE statut_DT = NON_CONFORME) |
| totalRisque | SUM(site.risque_financier_euro) |
| totalSurface | SUM(site.surface_m2) |
| nb_contrats_actifs | COUNT(contracts WHERE end_date ≥ today OR end_date IS NULL) |
| nb_contrats_expiring_90j | COUNT(contracts WHERE end_date BETWEEN today AND today+90) |
| completude_moyenne_pct | AVG(completeness scores) |

---

## 5. Cockpit — Vue exécutive

| Champ | Valeur |
|-------|--------|
| **Endpoint** | `GET /api/cockpit` |
| **Source** | `routes/cockpit.py:41–142` |

| KPI | Formule |
|-----|---------|
| total_sites | COUNT(Site) scoped org, non supprimés |
| sites_actifs | = total_sites (même requête) |
| compliance_score | compute_portfolio_compliance() = moyenne pondérée surface |
| risque_financier_euro | SUM(Site.risque_financier_euro) scoped org |

---

## 6. Statut BACS

| Champ | Valeur |
|-------|--------|
| **Source** | `services/compliance_engine.py:123–157` |

**Logique de détermination :**
```
SI evidence DEROGATION_BACS valide → DEROGATION
SI evidence ATTESTATION_BACS valide → CONFORME
SI échéance dépassée (today > echeance) → NON_CONFORME
SINON → A_RISQUE
```

**Score numérique BACS** (dans le composite) : même logique que les autres frameworks.

---

## 7. Limites connues

| Limite | Impact |
|--------|--------|
| Pénalité forfaitaire 7 500 € | Ne reflète pas les pénalités réelles par obligation |
| Score APER souvent "non applicable" | Le poids 25% se redistribue sur DT+BACS |
| Normalisation climatique absente du score | Le score ne corrige pas les biais météo |
| sites_actifs = total_sites | Pas de distinction "actifs avec données" vs "déclarés" |
| Complétude = 8 checks fixes | Pas de pondération par criticité métier |
