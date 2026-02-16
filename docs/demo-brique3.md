# PROMEOS — Demo Script Brique 3 "Leader du Marche" (8 minutes)

## Prerequis

```bash
# Terminal 1 — Backend
cd backend
py -3.14 -m uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Ouvrir http://localhost:5173 → Naviguer vers **Achats energie**

---

## Scene 1 : Energy Gate — ELEC Only (1 min)

**Message cle** : _"Post-ARENH, nous nous concentrons exclusivement sur l'electricite."_

1. Ouvrir l'onglet **Simulation**
2. Montrer le selecteur d'energie : **verrouille sur "Electricite"** avec icone cadenas
3. Noter le texte : _"Post-ARENH — elec uniquement"_
4. **Point technique** : le backend rejette toute tentative de GAZ (HTTP 422)

> **Talking point** : "La plateforme enforce automatiquement la contrainte post-ARENH. Impossible de creer des hypotheses GAZ par erreur."

---

## Scene 2 : Simulation Mono-Site (2 min)

**Message cle** : _"3 strategies comparees en un clic."_

1. Selectionner un site dans le dropdown
2. Observer les **cartes d'estimation** :
   - Volume estime (kWh/an)
   - Profil de charge (facteur)
3. Ajuster les **preferences** :
   - Tolerance au risque : **Moyen**
   - Priorite budget : **60%**
   - Cocher **Offre verte**
4. Cliquer **"Calculer les scenarios"**
5. Presenter les **3 cartes scenario** :
   - **Prix Fixe** : prix garanti, risque 15/100
   - **Indexe** : suit le marche, risque 45/100
   - **Spot** : temps reel, risque 75/100
6. Montrer :
   - Badge **"Recommande"** sur la meilleure strategie
   - Barre de risque coloree
   - Fourchette P10/P90
   - Analyse textuelle en bas
7. Cliquer **"Exporter Note de Decision (A4)"**
8. Montrer l'apercu A4 → cliquer **"Imprimer / PDF"**

> **Talking point** : "En un clic, le decision-maker a une note de decision imprimable avec comparaison des 3 strategies."

---

## Scene 3 : Portfolio Multi-Sites (2.5 min)

**Message cle** : _"Vision portefeuille : 15 sites analyses simultanement."_

1. Aller sur l'onglet **Portefeuille**
2. Cliquer le bouton demo **"15 sites (happy)"** (bandeau vert)
3. Observer la confirmation : _"Dataset happy charge : 15 sites, 45 scenarios, 15 contrats"_
4. Cliquer **"Calculer le portefeuille"**
5. Presenter les **KPIs agreges** :
   - **Sites analyses** : 15
   - **Cout annuel total** : X EUR
   - **Risque moyen pondere** : X/100
   - **Economies potentielles** : -X%
6. Faire defiler le **tableau par site** :
   - Chaque site avec sa strategie recommandee
   - Couts, risques, economies individualises
7. Cliquer **"Exporter Pack RFP (A4)"**
8. Montrer l'apercu multi-page :
   - Page 1 : synthese executif
   - Page 2 : detail par site
9. **"Imprimer / PDF"**

> **Talking point** : "Pour un appel d'offre, le Pack RFP est genere automatiquement avec tous les sites et scenarios detailles."

---

## Scene 4 : Donnees Degradees (1 min)

**Message cle** : _"La plateforme gere les cas limites sans planter."_

1. Cliquer le bouton demo **"15 sites (dirty)"** (bandeau orange)
2. Observer les warnings dans le resultat
3. Cliquer **"Calculer le portefeuille"** sur le dataset dirty
4. Montrer que le calcul aboutit malgre :
   - Sites a volume 0
   - Sites avec profiles extremes
   - Sites sans contrats
5. _(dev only)_ Cliquer l'icone **Bug** en bas a droite → Debug Drawer
6. Montrer les assumptions, scenarios, portfolio data

> **Talking point** : "Meme avec des donnees degradees, la plateforme ne plante pas et produit des resultats exploitables."

---

## Scene 5 : Echeances & Historique (1 min)

**Message cle** : _"Suivi des renouvellements et historique complet."_

1. Onglet **Echeances** :
   - Badges d'urgence (rouge/orange/jaune/gris)
   - Deadline de preavis calculee automatiquement
   - Flag auto-renew
2. Onglet **Historique** :
   - Montrer 2+ runs de calcul
   - Cliquer sur un run pour detailler
   - Run ID + hash des entrees

> **Talking point** : "Chaque calcul est trace et reproductible. Les echeances de renouvellement sont suivies automatiquement."

---

## Scene 6 : Recapitulatif (30s)

**Points cles a resumer** :

| Fonctionnalite | Status |
|---|---|
| Energy Gate ELEC-only | Enforce (backend + frontend) |
| Simulation 3 strategies | Fixe / Indexe / Spot |
| Portfolio 15+ sites | Agregation ponderee |
| Note de Decision A4 | 1 page, imprimable |
| Pack RFP A4 | 2-3 pages, multi-site |
| Donnees degradees | Resilient, debug drawer |
| Echeances contrats | Urgence + preavis |
| Historique des runs | Tracabilite complete |

> **Closing** : "Brique 3 transforme le module Achat en outil de decision pour les investisseurs et les directions achats, avec des exports professionnels et une gestion multi-site robuste."

---

## Presets & Tooling

### Reset rapide (entre demos)

```bash
# Supprimer la DB et relancer
rm backend/data/promeos.db
cd backend && py -3.14 -m uvicorn main:app --reload
# La DB se recree automatiquement via Base.metadata.create_all()
```

### Charger les datasets via API

```bash
# Happy dataset
curl -X POST http://localhost:8000/api/purchase/seed-wow-happy

# Dirty dataset
curl -X POST http://localhost:8000/api/purchase/seed-wow-dirty

# Classic demo (2 sites)
curl -X POST http://localhost:8000/api/purchase/seed-demo
```

### Verification rapide

```bash
# Backend tests (all purchase + adapter)
cd backend && py -3.14 -m pytest tests/test_purchase.py tests/test_data_adapter_b1_b2.py -v

# Frontend build
cd frontend && npm run build
```
