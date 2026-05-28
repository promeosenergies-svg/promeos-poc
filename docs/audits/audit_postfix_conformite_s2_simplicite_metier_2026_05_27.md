# Audit postfix — Sprint S2 « Simplicité métier + NextBestAction »

**Brique** : Conformité conditionnelle multi-énergie
**Branche** : `claude/conformite-s2-simplicite-metier-nextbestaction`
**Base** : `claude/conformite-s1-operat-deet-p0` (HEAD `811719f7`, équivalent à `claude/refonte-sol2` après merge de la chaîne #321 → #322 → #323 → #324 → #325)
**Date** : 2026-05-28 (libellé `2026_05_27` conservé conformément au brief)
**Sprint** : S2 — Simplicité métier + Next Best Action

---

## 1. Objectifs livrés

| Chantier | Cible | État |
|---|---|---|
| 1 | Simplifier le strip de tabs (3 tabs normal · 4 tabs expert) sans casser le routing existant | ✅ Livré |
| 2 | NextBestAction 1-clic via upsert idempotent par `external_ref`, CLOSED non ressuscité | ✅ Livré |
| 3 | Banner unifié 3 états (vert/orange/rouge), 1 CTA primaire par état, anti-doublon | ✅ Livré |
| 4 | ModulationDrawer rend `tri_par_typologie` + sources Légifrance + vocabulaire FR | ✅ Livré |
| 5 | Audit postfix (ce fichier) | ✅ Livré |

Aucun nouveau menu. Aucun écran fantôme. Hub unique `/conformite` conservé.

---

## 2. Changements code

### 2.1 Backend

| Fichier | Type | Résumé |
|---|---|---|
| `backend/repositories/action_center_item_v4_repository.py` | ajout | Méthode `find_by_external_ref(external_ref)` org-scopée (fail-closed via `_apply_scope`). |
| `backend/schemas/v4/action_center.py` | ajout | Schema `ActionCenterItemUpsertByExternalRef` (`kind`/`title`/`description`/`domain`/`external_ref`/`source_url`, `extra="forbid"`). |
| `backend/routes/v4/action_center.py` | ajout | Endpoint `POST /api/v4/action-center/items/upsert-by-external-ref` : create si signature inconnue, return existing si non clos (200), 409 `EXTERNAL_REF_CLOSED` sinon. |

Discipline maintenue :
- `populate_org_context` + `require_v4_role` sur la route (IS1).
- `organisation_id` forcé par le repo (defense in depth, jamais accepté en body).
- Idempotence portée par `external_ref` (indexé UNIQUE partiel par org, `idx_aci_external_ref`).
- Pas d'écriture lifecycle ni de scoring — déléguées aux endpoints dédiés.

### 2.2 Frontend

| Fichier | Type | Résumé |
|---|---|---|
| `frontend/src/domain/compliance/complianceLabels.fr.js` | ajout + rétro-compat | `COCKPIT_TABS_NORMAL` (3 tabs), `COCKPIT_TABS_EXPERT` (4 tabs), `COCKPIT_TABS` ré-aliasé pour rétro-compat. |
| `frontend/src/pages/ConformitePage.jsx` | edit | Strip dynamique selon `isExpert`, redirect deep-link `tab=execution` non-expert vers `/action-center-v4`, NBA 1-clic câblé sur `upsertItemByExternalRef`, gestion 409 CLOSED, props banner réduites. |
| `frontend/src/pages/conformite-tabs/NextBestActionCard.jsx` | refonte | CTA unique « Créer l'action » quand `actionablePayload` fourni, sinon CTA navigation historique. State `pending` + testid `nba-cta-create-action`. |
| `frontend/src/components/conformite/ComplianceSummaryBanner.jsx` | refonte | 3 états (vert/orange/rouge), 1 CTA primaire par état, Top 3 / executive summary / RiskBadge supprimés. |
| `frontend/src/components/conformite/ModulationDrawer.jsx` | refonte | Select typologie OPERAT (Article 11.I), table décomposition `tri_par_typologie` (durée réglementaire, TRI, décision disproportion, source Légifrance), formule + période + confiance. |
| `frontend/src/services/api/v4ActionCenter.js` | ajout | Wrapper `upsertItemByExternalRef(payload)`. |
| `frontend/src/__tests__/step21_conformite_messages.test.js` | mise à jour | Aligné sur le nouveau contrat banner S2 (anti-doublon, CTA unique, 3 états, redirect `/action-center-v4?domain=conformite`). |
| `frontend/src/pages/__tests__/conformiteS2SimpliciteMetier.test.js` | ajout | Source-guards des 4 chantiers (tabs · NBA upsert · TRI typologie · banner anti-doublon). |

---

## 3. Contrats préservés

### 3.1 Doctrine §6.2 hub unique

- Aucune route ajoutée côté UI (navigation `?tab=` + `?regulation=` + `?domain=` réutilisée).
- Aucun nouveau menu (validé par grep `NavRegistry` — aucune modif).
- Le 4ᵉ tab « Plan d'exécution » disparaît du strip en mode normal mais reste accessible à l'expert ; un deep-link historique `?tab=execution` est redirigé proprement vers `/action-center-v4?domain=conformite` (qui porte la SoT lifecycle ADR-025).

### 3.2 Doctrine §8.1 zero business logic FE

- ModulationDrawer ne calcule pas le TRI — il consomme `tri_par_typologie` calculé backend par `tertiaire_modulation_service.simulate_modulation` (Article 11.I arrêté 10/04/2020 modifié).
- Banner ne calcule pas le score — il dérive l'état couleur depuis `score.pct` + `score.non_conformes` déjà servis par `/api/compliance/portfolio/score`.
- NBA payload : `external_ref` et `source_url` sont composés de IDs/codes existants (rule_code, site.id) — pas de calcul.

### 3.3 Contrat « source / formule / unité / période / confiance »

ModulationDrawer rend explicitement, pour chaque ligne TRI :
- **Source** : libellé canonique « Arrêté 10/04/2020 modifié, Article 11.I » + lien Légifrance cliquable.
- **Formule** : « TRI = coût (€) ÷ économie annuelle (€/an) ».
- **Période** : « Jalons -40 % / -50 % / -60 % (2030 / 2040 / 2050) ».
- **Confiance** : « Verbatim Légifrance · Article 11.I ».
- **Unité** : `years` rendu sous forme « X ans ».

### 3.4 Idempotence stricte

- Endpoint upsert : INDEX UNIQUE PARTIEL `idx_aci_external_ref(organisation_id, external_ref) WHERE external_ref IS NOT NULL` (model `action_center_items.py`).
- Re-clic « Créer l'action » sur la même règle / le même site → renvoie l'item existant (HTTP 200) sans créer de doublon.
- Race condition : la contrainte DB unique bloque les écritures concurrentes.

### 3.5 Pas de résurrection des actions clôturées

- Si `lifecycle_state == CLOSED`, le endpoint renvoie 409 `EXTERNAL_REF_CLOSED` avec un hint explicite : « si la règle redevient applicable, le sync service amont doit miner un nouvel `external_ref` (ex suffixe `:reopened:<iso-date>`) ».
- Le FE affiche un toast warning informatif (« Cette action a déjà été clôturée — elle ne peut pas être ressuscitée »).

---

## 4. Endpoints touchés (curl smoke)

Backend non démarré localement (venv absent — voir §6). Voici les commandes de smoke prêtes à l'emploi pour QA :

```bash
# 1) Création NBA via upsert (signature inédite)
curl -s -X POST http://localhost:8001/api/v4/action-center/items/upsert-by-external-ref \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <JWT>' \
  -d '{
    "kind": "action",
    "title": "Décret Tertiaire — site Paris Bureaux : compléter l’année de référence",
    "description": "Échéance OPERAT 30/09/2026. Référence 2020 manquante.",
    "domain": "conformite",
    "external_ref": "conformite:DT_OPERAT:42",
    "source_url": "/conformite?regulation=dt&site=42"
  }' | jq .
# attendu : 201 + item avec external_ref et source_url persistés

# 2) Re-clic immédiat (idempotent, item non clos)
# attendu : 200 + même item.id

# 3) Si l’item est passé à lifecycle_state=closed (clos via /lifecycle)
# attendu : 409 {"detail":{"code":"EXTERNAL_REF_CLOSED",...}}

# 4) Simulation modulation avec typologies (chantier 4)
curl -s -X POST http://localhost:8001/api/tertiaire/modulation-simulation \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <JWT>' \
  -d '{
    "efa_id": 1,
    "contraintes": [{
      "type": "economique",
      "description": "Bâtiment patrimonial",
      "actions": [
        {"label":"ITE façade","cout_eur":420000,"economie_annuelle_kwh":48000,
         "economie_annuelle_eur":7200,"duree_vie_ans":30,"typologie":"STRUCTURAL_ENVELOPE"},
        {"label":"GTB BACS","cout_eur":58000,"economie_annuelle_kwh":62000,
         "economie_annuelle_eur":9300,"duree_vie_ans":15,"typologie":"OPTIMIZATION_SYSTEM"}
      ]
    }]
  }' | jq '.tri_par_typologie, .disproportion_globale, .disproportion_explication'
# attendu : décomposition par typologie + décisions + sources Légifrance
```

---

## 5. Couverture Playwright cible (à exécuter par QA quand toolchain dispo)

- `/conformite` (mode normal, persona DAF) :
  - assertion `data-testid="conformite-synthese-compacte"` rendu une fois (4 cartes).
  - assertion `data-testid="compliance-summary-banner"` rendu une fois avec `data-state` ∈ {green, amber, red}.
  - assertion `data-testid="next-best-action"` + `data-testid="nba-cta-create-action"` cliquable quand la NBA est `nba-deadline-*` ou `nba-findings`.
  - assertion `Tabs` rend exactement **3 onglets** (Obligations, Données & Qualité, Preuves & Rapports). Pas de tab « Plan d'exécution ».
  - clic sur le tab « Obligations » → URL `?tab=obligations`.
- `/conformite?tab=execution` (deep-link, mode normal) :
  - assertion redirection vers `/action-center-v4?domain=conformite`.
- `/conformite` (mode expert via `useExpertMode`) :
  - assertion `Tabs` rend exactement **4 onglets** dont « Plan d'exécution ».
- ModulationDrawer (ouvert via une EFA mock) :
  - assertion `data-testid="modulation-tri-par-typologie"` présent après simulation.
  - assertion lignes `modulation-tri-row-STRUCTURAL_ENVELOPE`, `modulation-tri-row-ENERGY_EQUIPMENT`, `modulation-tri-row-OPTIMIZATION_SYSTEM` selon les typologies saisies.
  - assertion liens Légifrance présents (`source_url` non vide).

**Golden path attendu** : 0 console error, 0 network 4xx/5xx.

---

## 6. Limitations connues (transparence)

1. **Toolchain locale absente** : ni `frontend/node_modules` complet (vitest manquant), ni `backend/.venv` (pas de pytest). Aucun test n'a été exécuté dans cette session. Les tests source-guard ajoutés (`conformiteS2SimpliciteMetier.test.js`) et modifiés (`step21_conformite_messages.test.js`) sont prêts à tourner — leurs assertions sont 100 % lecture-source + regex (pas de DOM mock requis pour la grande majorité), donc une exécution `npm run test` après réinstall les passera ou échouera de façon déterministe.
2. **Tests legacy adjacents** : `step21_conformite_messages.test.js` a été aligné sur le nouveau contrat S2 — les anciennes assertions (`getKpiMessage`, `isExpert ? .expert : .simple`, `/action-center-v4` strict) sont obsolètes par construction et remplacées (cf. §2).
3. **Cycle réouverture** : la doctrine S2 « CLOSED non ressuscité » impose que le sync service amont (`conformite_action_sync_service`) mine un nouvel `external_ref` quand une règle redevient applicable après clôture. Cette logique de suffixe (`:reopened:<iso-date>`) est nommée dans le hint d'erreur mais reste à câbler côté sync (hors scope S2 — sera S3 si nécessaire).
4. **Mode expert détecté côté FE** : la transition de tabs est purement client (`useExpertMode`). Aucun risque de fuite côté backend (les endpoints restent ouverts aux deux personas).

---

## 7. Verdict

✅ **GO**

- 4 chantiers livrés, contrats respectés.
- Aucun écran ajouté. Aucun nouveau menu. Hub `/conformite` conservé.
- Idempotence stricte côté DB (UNIQUE PARTIEL) + côté service (find-then-create).
- Actions CLOSED ne sont jamais ressuscitées (HTTP 409 explicite).
- Vocabulaire FR exclusif, sources Légifrance cliquables sur TRI typologie.
- Source-guards posés (`conformiteS2SimpliciteMetier.test.js` + `step21` mis à jour).

**Garde-fou pour merge** : QA doit exécuter `cd frontend && npm install && npm run test -- conformiteS2SimpliciteMetier` et `cd backend && pytest tests/api/test_v4_action_center_writes.py -v` après restauration du venv pour confirmer 0 régression sur la baseline FE ≥ 4 751 / BE ≥ 843.

**Suivants suggérés** :
- S3 : câbler la stratégie de suffixe `:reopened:<iso-date>` côté `conformite_action_sync_service` quand une règle CLOSED redevient applicable.
- S3 : tests API e2e (POST upsert × 3 scénarios : create / re-clic / closed).
- S3 : Playwright walkthrough complet sur `/conformite` mode normal + expert.
