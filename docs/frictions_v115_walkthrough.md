# V115 Sirene — Walkthrough E2E réel (2026-04-12)

**Contexte** : audit stratégique post-merge pour valider le claim "SIREN → premier insight en 3 min".

**Méthode** : walkthrough de bout en bout avec un vrai SIREN (CARREFOUR HYPERMARCHES, SIREN `451321335`) sans aucun seed/mock. Mesure de chaque étape.

## Résultats mesurés

| Étape | Durée | Statut |
|-------|-------|--------|
| Hydratation API gouv (bridge créé pour ce walkthrough) | 1311 ms | ✅ |
| `POST /api/onboarding/from-sirene` | 158 ms | ✅ |
| Funnel wiring `OnboardingProgress` | inline | ✅ `step_org_created` + `step_sites_added` = True |
| **TTFV (Time To First Value)** | **~1.5 s** | ✅ **Excellent** |
| **TTFI (Time To First Insight)** | **∞** | ❌ **Bloqué** |

## Frictions réelles identifiées

### Friction #1 — Hydratation per-SIREN manquante (bloquant P0)

**Symptôme** : le module V115 importe via CSV 2.6 GB mais n'a aucun moyen de charger un SIREN unique. Impossible de faire une démo, un pilote, ou un onboarding client sans avoir importé le stock complet au préalable.

**Fix de ce walkthrough** : création de `backend/services/sirene_hydrate.py` qui wrap l'API gouv et insère un SIREN + ses établissements dans les tables locales. **Doit être intégré au flow onboarding** pour que la démo fonctionne sans l'import CSV complet.

**Action V116** : exposer un endpoint `POST /api/reference/sirene/hydrate/{siren}` admin + appel auto depuis la page de recherche si SIREN absent.

### Friction #2 — API gouv limite drastiquement les établissements (bloquant P0)

**Symptôme** : Carrefour Hypermarches est un groupe avec ~200+ magasins en France. L'API `recherche-entreprises.api.gouv.fr` en mode `q=siren` ne retourne **que le siège** (1 établissement dans `matching_etablissements`).

**Impact stratégique** : le flow multi-site est **silencieusement cassé** pour les grands groupes. L'utilisateur croit créer son patrimoine complet mais obtient 1 site.

**Fix V116** :
- Utiliser le paramètre `limite_matching_etablissements=100` (max API)
- Paginer sur `matching_etablissements` si besoin
- Mieux : passer à l'API-Entreprise (service payant DINUM) qui expose tous les établissements

### Friction #3 — Site créé sans surface_m2 → compliance muette (bloquant P0)

**Symptôme** :
```
Site #1 surface : None
Site #1 compliance_score : None
Site #1 risque_financier_euro : 0.0
```

Sirene ne contient **pas** la surface. Les 3 briques compliance de PROMEOS (Décret Tertiaire, BACS, APER) ont besoin de surface + type CVC. Sans input, aucun score.

**Impact stratégique** : le NextStepsHub envoie vers `/conformite` mais **il n'y a rien**. La promesse "scoring instantané DT/BACS/APER" est **un mensonge marketing** tant que l'utilisateur n'a pas saisi manuellement la surface.

**Fix V116** (2 options non exclusives) :
- **A (rapide)** : après création Sirene, rediriger vers un micro-stepper "Indiquez la surface de chacun de vos sites (1 min)" qui déclenche `_recompute_site()` à chaque input
- **B (scalable)** : intégration cadastre via API [Cadastre étalab](https://apicarto.ign.fr) qui retourne la surface au sol depuis l'adresse (gratuite, 1 call/site)

### Friction #4 — Aucune donnée énergie → aucun insight (attendu mais non communiqué)

**Symptôme** : après onboarding, le site a 0 compteur, 0 facture, 0 consommation. Donc :
- Billing : vide
- Anomalies : vide
- Shadow billing : vide
- Archétype flex : non calculable

**Impact stratégique** : TTFI = infini tant que l'utilisateur n'a pas connecté Enedis ou uploadé une facture. Le claim "3 min to first insight" nécessite que la chaîne soit pré-câblée.

**Fix V116** :
- Auto-déclencher la promesse d'impact **avant** la création. Ex : "Votre patrimoine aura un coût d'inaction estimé à X k€/an (basé NAF + surface cadastre)". Même sans données réelles, donner un ordre de grandeur calibré par archétype.
- Proposer un connecteur Enedis en 1 clic après Sirene, avec fallback vers l'upload facture PDF.

## Ce qui marche parfaitement (à préserver V116)

- ✅ Funnel wiring automatique `OnboardingProgress` (step_org_created + step_sites_added)
- ✅ Règle absolue "Sirene ne crée jamais bâtiment/compteur/obligation" respectée (0/0/0)
- ✅ NAF détecté et mappé (`47.11F` → `TypeSite.COMMERCE`)
- ✅ Catégorie entreprise INSEE (`GE`) disponible pour lead scoring
- ✅ TTFV < 2s end-to-end
- ✅ 0 exception, 0 warning, 0 effet de bord sur le patrimoine existant

## Verdict stratégique

Le **wedge Sirene est architecturalement correct** mais **3 frictions P0 empêchent** le claim marketing de tenir :

1. Pas d'hydratation per-SIREN (démo impossible)
2. API gouv limite les établissements (multi-site cassé)
3. Pas de surface → pas de compliance (insight bloqué)

**Roadmap V116 priorisée** :
- **P0.1** : endpoint `/hydrate/{siren}` + câblage auto dans `/search`
- **P0.2** : `limite_matching_etablissements=100` + pagination
- **P0.3** : post-création → micro-stepper surface OU intégration cadastre
- **P0.4** : lead score service (Option B du plan stratégique) = monétisation immédiate

Le walkthrough a validé la **fondation** V115 et révélé **3 frictions mesurables** (vs hypothèses). V116 doit attaquer ces 3 frictions avant tout nouveau module.
