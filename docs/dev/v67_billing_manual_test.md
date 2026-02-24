# V67 — Checklist QA Manuelle (10 min)

> Prérequis : backend + frontend démarrés, seed billing demo exécuté (`POST /api/billing/seed-demo`)

---

## Étape 1 — Page Timeline (2 min)

1. Aller sur `http://localhost:5173/billing`
2. ✅ KPIs affichés : mois couverts / partiels / manquants
3. ✅ CoverageBar visible avec proportion couleurs (vert/orange/rouge)
4. ✅ Range affiché (ex: "Jan 2024 → Fév 2025")
5. ✅ Liste timeline : au moins 1 mois visible avec statut

## Étape 2 — Filtrage par site (1 min)

1. Sélectionner un site dans le filtre
2. ✅ URL se met à jour : `/billing?site_id=X`
3. ✅ KPIs et timeline rechargent pour ce site
4. ✅ Réinitialiser le filtre → données globales rechargent

## Étape 3 — Périodes manquantes (2 min)

1. Vérifier la section "Périodes manquantes"
2. ✅ Si trous présents : liste avec site, mois, raison
3. ✅ Bouton "Importer" visible sur chaque ligne manquante
4. Cliquer "Importer" pour le premier trou
5. ✅ Redirige vers `/bill-intel?site_id=X&month=YYYY-MM`

## Étape 4 — CTA Créer action (1 min)

1. Sur une ligne manquante, cliquer "Créer action"
2. ✅ Bouton passe à l'état "créé" (idempotent)
3. Aller dans le Plan d'action → ✅ action visible avec source BILLING

## Étape 5 — Pagination (1 min)

1. Si plus de 24 mois : bouton "Charger plus" visible
2. ✅ Cliquer → 24 mois supplémentaires chargés
3. ✅ Pas de doublon dans la liste

## Étape 6 — Lien depuis Site360 (1 min)

1. Aller sur `/patrimoine` → ouvrir un site
2. Cliquer onglet "Factures"
3. ✅ `SiteBillingMini` affiché avec KPIs
4. ✅ Bouton "Voir timeline complète" visible
5. Cliquer → ✅ Redirige vers `/billing?site_id=X`

## Étape 7 — Navigation (30s)

1. ✅ "Timeline facturation" apparaît dans la nav section "Marché & Factures"
2. ✅ `/facturation` redirige vers `/billing`

## Étape 8 — Multi-org isolation (1 min)

1. Se connecter avec `sophie@atlas.demo` (org Atlas)
2. ✅ Données billing visibles
3. (Si 2e org disponible) Se connecter avec autre org → ✅ aucune donnée Atlas visible

## Étape 9 — Couverture partielle (30s)

1. Importer une facture qui couvre 15/31 jours d'un mois
2. ✅ Ce mois apparaît comme "partial" (orange) dans la timeline
3. ✅ Raison affichée : "Couverture X% (Y/Z jours)"

## Étape 10 — API Swagger (30s)

1. Ouvrir `http://localhost:8000/docs`
2. ✅ `GET /billing/periods` visible avec schéma response
3. ✅ `GET /billing/coverage-summary` visible
4. ✅ `GET /billing/missing-periods` visible
5. Tester `/billing/coverage-summary` → ✅ JSON correct

---

## Checklist finale avant merge

- [ ] `pytest tests/ -x -q` → 0 failed
- [ ] `vitest run` → 0 failed
- [ ] `grep -c "resolve_org_id" routes/billing.py` → ≥ 16
- [ ] `grep "Organisation.first()" routes/billing.py` → 0
- [ ] Page `/billing` accessible sans erreur console
- [ ] `/billing?site_id=1` filtre correctement
- [ ] CoverageBar proportionnelle (vert + orange + rouge = 100%)
- [ ] Boutons "Importer" pointent vers `/bill-intel` avec site_id
