# AUDIT PROMEOS — ÉTAPE 1 : FIL CONDUCTEUR

> **Date** : 2026-03-23
> **Baseline** : `docs/audits/AUDIT_PROMEOS_ETAPE_00_CADRAGE_2026-03-23.md` (note 7.0/10)
> **Méthode** : Trace code-path exhaustive (3 agents parallèles), vérification fichier/ligne
> **Statut** : AUDIT UNIQUEMENT — aucune modification du repo

---

## 1. Résumé exécutif

Le fil conducteur `patrimoine → données → KPI → conformité → facture → achat → actions` est **partiellement câblé**. Sur 6 maillons de la chaîne, 2 sont solides, 2 sont partiels, et 2 sont cassés.

**Découverte critique** : `dt_trajectory_service.py:181` définit `update_site_avancement()` qui calcule dynamiquement `Site.avancement_decret_pct` depuis la trajectoire OPERAT réelle. Cette fonction n'a **AUCUN appelant** dans tout le repo. Le chaînon manquant est identifié, localisé, et réparable en une ligne.

**Verdict fil conducteur** : Un utilisateur qui déroule la chaîne complète en démo percevra un produit **intégré à 65%**. Les 35% manquants sont des ruptures silencieuses — le produit ne plante pas, mais les données ne circulent pas.

| Maillon | Statut | Note |
| --- | --- | --- |
| A. Patrimoine → Données | **IMPLÉMENTÉ** | 9/10 |
| B. Données → KPI | **PARTIEL** | 6/10 — avancement DT = champ plat, pas trajectoire dynamique |
| C. KPI → Conformité | **IMPLÉMENTÉ** | 8/10 — même source (compliance_score_service), cohérent |
| D. Conformité → Facture | **CASSÉ** | 2/10 — aucun lien code, aucun lien UI |
| E. Facture → Achat | **PARTIEL** | 6/10 — volume kWh réel, mais price_factor fixe |
| F. Achat → Actions | **PARTIEL** | 5/10 — actions calculées mais éphémères sans sync |

---

## 2. Cartographie réelle du fil conducteur

```text
                    CHAÎNE RÉELLE TRACÉE
                    =====================

[PATRIMOINE]──auto──→[OBLIGATIONS]──auto──→[COMPLIANCE ENGINE]──auto──→[KPI SERVICE]
     │                     │                       │                        │
     │ QuickCreateSite     │ provision_site()       │ recompute_site_full() │ get_summary()
     │ POST /api/sites/    │ onboarding_service     │ compliance_coord.     │ GET /api/cockpit
     │ quick-create        │ :203-217               │ :22-78                │
     │                     │                        │                       │
     │                     ▼                        ▼                       ▼
     │              [SITE SNAPSHOTS]          [RegAssessment]         [COCKPIT UI]
     │              .avancement_decret_pct    .score                  Cockpit.jsx
     │              .risque_financier_euro    .findings               :124-173
     │              .statut_bacs                                           │
     │                     │                                               │
     │                     ╳ RUPTURE ──── dt_trajectory_service.py         │
     │                     │              update_site_avancement()          │
     │                     │              EXISTE MAIS 0 APPELANT           │
     │                     │                                               │
     │                     ▼                                               │
     │              [CONFORMITE UI]                                        │
     │              ConformitePage.jsx                                      │
     │              :116-159                                               │
     │                     │                                               │
     │                     ╳ RUPTURE ──── AUCUN LIEN ──────────────────────│
     │                     │              billing ↔ conformite              │
     │                     ▼                                               │
     │              [BILL INTEL UI]    ◄──── "Contrôler facture" ◄── [ACHAT UI]
     │              BillIntelPage.jsx         PurchasePage.jsx:1254
     │              :530 "CTA achat" ────────► PurchasePage.jsx
     │                     │
     │                     ▼
     │              [PURCHASE ENGINE]
     │              purchase_scenarios_service.py:160
     │              estimate_eur = price_ref × FACTOR × annual_kwh
     │              annual_kwh ◄── EnergyInvoice (RÉEL)
     │              FACTOR = 1.05/0.95/0.88 (FIXE)
     │                     │
     │                     ▼
     │              [PURCHASE ACTIONS ENGINE]
     │              purchase_actions_engine.py:30-206
     │              5 types actions (renewal, strategy, reco)
     │              ──── ÉPHÉMÈRES ────
     │                     │
     │                     ▼ (seulement si sync_actions() appelé)
     │              [ACTION HUB]
     │              action_hub_service.py:258-402
     │              sync_actions() → persiste ActionItem
     │              source_type = PURCHASE
```

---

## 3. Liens réellement fonctionnels

### A. Patrimoine → Données — IMPLÉMENTÉ (9/10)

La création d'un site déclenche automatiquement toute la chaîne de provisionnement.

| Étape | Auto ? | Fichier:ligne | Preuve |
| --- | --- | --- | --- |
| Utilisateur crée un site | Manuel | `QuickCreateSite.jsx:67-103` → `POST /api/sites/quick-create` | |
| Bâtiment auto-créé avec CVC estimé | **OUI** | `onboarding_service.py:208` → `create_batiment_for_site()` | CVC estimé par ratio W/m² selon type (bureau 40-70, hôtel 60-100) |
| Obligations DT/BACS auto-créées | **OUI** | `onboarding_service.py:209` → `create_obligations_for_site()` | DT si tertiaire_area >= 1000m², BACS si CVC > 70kW |
| DeliveryPoints auto-liés | **OUI** | `onboarding_service.py:210` → `ensure_delivery_points_for_site()` | |
| Compliance recomputed | **OUI** | `onboarding_service.py:211` → `recompute_site(db, site.id)` | Appelle `compliance_coordinator.recompute_site_full()` |
| Score A.2 écrit sur Site | **OUI** | `compliance_coordinator.py:60-68` → `sync_site_unified_score()` | `Site.compliance_score_composite` mis à jour |
| Risque financier écrit sur Site | **OUI** | `compliance_engine.py:214-216` → `7500 * non_conforme + 3750 * a_risque` | `Site.risque_financier_euro` mis à jour |

**Verdict** : IMPLÉMENTÉ — La chaîne patrimoine→données est la plus solide du produit. Tout est automatique dès la création du site.

### C. KPI → Conformité — IMPLÉMENTÉ (8/10)

Le cockpit et la page conformité lisent la **même source de vérité**.

| Vue | Endpoint | Source backend | Cohérence |
| --- | --- | --- | --- |
| Cockpit score conformité | `GET /api/compliance/portfolio/score` | `compliance_score_service.compute_portfolio_compliance()` | ✅ |
| ConformitePage score | `GET /api/compliance/portfolio/score` (même) | `compliance_score_service.compute_portfolio_compliance()` | ✅ |
| Cockpit risque financier | `GET /api/cockpit` | `kpi_service.get_financial_risk_eur()` → `SUM(Site.risque_financier_euro)` | ✅ |
| ConformitePage risque | `compliance/bundle` | `score.total_impact_eur` | ✅ |
| Cockpit trend 6 mois | `GET /api/compliance/score-trend` | `ComplianceScoreHistory` | ✅ |

**Verdict** : IMPLÉMENTÉ — Les deux vues sont cohérentes, même source.

---

## 4. Liens partiels

### B. Données → KPI — PARTIEL (6/10)

Le KPI `avancement_decret_pct` affiché au cockpit est **déconnecté de la trajectoire OPERAT réelle**.

**Preuve formelle de la rupture :**

| Composant | Ce qu'il fait | Fichier:ligne |
| --- | --- | --- |
| `dt_trajectory_service.compute_site_trajectory()` | Calcule `reduction_pct = (1 - conso_actuelle / conso_ref) * 100` puis `avancement_2030 = reduction_pct / 40 * 100` depuis données mesurées | `dt_trajectory_service.py:46-178` |
| `dt_trajectory_service.update_site_avancement()` | Persiste `Site.avancement_decret_pct = result.avancement_2030` | `dt_trajectory_service.py:181-195` |
| **RUPTURE** : `update_site_avancement()` n'est appelé **NULLE PART** | Grep sur tout le backend = 0 appelant hors sa propre définition | Vérifié par grep `update_site_avancement` |
| `compliance_engine.recompute_site()` | Écrit `Site.avancement_decret_pct = average_avancement(obligations)` = **moyenne des `Obligation.avancement_pct`** (valeurs manuelles/seed) | `compliance_engine.py:211` |
| `kpi_service.get_avancement_decret_pct()` | Lit `AVG(Site.avancement_decret_pct)` | `kpi_service.py:218` |
| Cockpit | Affiche la valeur | `Cockpit.jsx` via `GET /api/cockpit` |

**Conséquence** : Le KPI "avancement Décret Tertiaire" affiché au cockpit est une **moyenne de valeurs manuelles** (`Obligation.avancement_pct`), pas le calcul dynamique `(conso_ref - conso_actuelle) / conso_ref`. La fonction qui ferait le lien existe (`update_site_avancement`) mais n'est jamais appelée.

**Tag** : À RISQUE CRÉDIBILITÉ — Un expert OPERAT détecterait que l'avancement ne bouge pas quand les consommations changent.

### E. Facture → Achat — PARTIEL (6/10)

Les scénarios achat consomment des **données facture réelles** (volume kWh), mais le calcul de prix est un **multiplicateur fixe**.

| Donnée | Source réelle ? | Fichier:ligne | Verdict |
| --- | --- | --- | --- |
| Volume annuel kWh | **OUI** | `purchase_service.py:74-96` → `SUM(EnergyInvoice.energy_kwh)` 12 mois | IMPLÉMENTÉ |
| Profil HP/HC | **NON** | Non utilisé dans les scénarios | NON TROUVÉ |
| Saisonnalité | **NON** | Somme annuelle plate, pas de décomposition mensuelle | NON TROUVÉ |
| Prix de référence | **OUI** (du contrat) | `purchase_scenarios_service.py:138` → `ct.price_ref_eur_per_kwh` | IMPLÉMENTÉ |
| Calcul coût scénario | **FACTEUR FIXE** | `purchase_scenarios_service.py:160` → `price_ref * price_factor * annual_kwh` | PLACEHOLDER |
| price_factor | **HARDCODÉ** | Fixe: 1.05, Indexé: 0.95, Spot: 0.88 | PLACEHOLDER |

**Conséquence** : L'écart entre scénarios est TOUJOURS identique (fixe = +5%, indexé = -5%, spot = -12% vs. prix actuel). Un DAF rigoureux détectera cette constance suspecte.

**Tag** : À RISQUE CRÉDIBILITÉ

### F. Achat → Actions — PARTIEL (5/10)

Les actions d'achat sont **calculées** mais **éphémères** par défaut.

| Étape | Implémenté ? | Fichier:ligne | Détail |
| --- | --- | --- | --- |
| Calcul actions achat | **OUI** | `purchase_actions_engine.py:30-206` | 5 types : renewal_urgent/soon/plan, strategy_switch, accept_reco |
| Persistance automatique | **NON** | Actions en mémoire seulement | Retournées par `GET /api/purchase/actions` mais pas en DB |
| Persistance via sync | **OUI** (manuel) | `action_hub_service.py:302-307` → `build_actions_from_purchase()` | Sync via `POST /api/actions/sync` |
| Traçabilité source | **OUI** | `action_item.py:34-42` → `source_type=PURCHASE` | Dedup par `(org_id, PURCHASE, source_id, source_key)` |
| Filtrage UI | **OUI** | `ActionsPage.jsx:561` → `?source=purchase` | Filtre par type source |
| Cap par org | **OUI** | `action_hub_service.py:284` → max 6 purchase actions/sync | |

**Conséquence** : En démo, si personne ne déclenche `sync_actions()`, les recommandations achat n'apparaissent jamais dans le centre d'actions. L'utilisateur voit des scénarios mais aucune action tracée.

**Tag** : IMPLICITE MAIS NON FIABILISÉ

---

## 5. Ruptures de logique

### RUPTURE D1 : Conformité → Facture — CASSÉ (2/10)

**Constat** : Il n'existe **AUCUN lien** entre les briques conformité et facturation.

| Recherche | Résultat | Preuve |
| --- | --- | --- |
| Grep "billing\|facture\|invoice" dans `ConformitePage.jsx` | **0 résultat** | Aucune mention de facturation dans la page conformité |
| Grep "compliance\|conformite\|obligation\|risque" dans `BillIntelPage.jsx` | **0 résultat** | Aucune mention de conformité dans la page facturation |
| Grep "compliance" dans `billing_service.py` | **0 résultat** | Le service billing ne connaît pas la conformité |
| Grep "billing" dans `compliance_engine.py` | Uniquement `BillingInsight` importé pour un comptage | Import utilitaire, pas un lien fonctionnel |

**Impacts concrets** :
- Un site NON_CONFORME avec 7 500 EUR de risque financier → la vue facture ne montre rien
- Un utilisateur sur BillIntelPage ne voit pas que son site a un risque réglementaire
- Le lien "conformité = argent" est affiché au cockpit (risque_financier_euro) mais **invisible dans les vues détail facture**
- Site360 montre les deux en tabs séparés (Factures et Conformité) mais **sans cross-référence entre les deux tabs**

**Tag** : CASSÉ — Rupture totale, pas même un lien de navigation

### RUPTURE D2 : KPI avancement DT déconnecté de la trajectoire réelle

Détaillé en section 4.B ci-dessus. Le code de liaison existe (`update_site_avancement`) mais n'est jamais appelé.

**Tag** : À RISQUE CRÉDIBILITÉ — Le chaînon manquant est une seule ligne d'appel dans `compliance_coordinator.py`

---

## 6. KPI ou vues trompeuses

### KPI-1 : avancement_decret_pct = valeur manuelle, pas trajectoire dynamique

| Aspect | Réalité | Fichier:ligne |
| --- | --- | --- |
| **Ce que l'utilisateur croit** | "Mon avancement vers -40% est calculé depuis mes consommations réelles" | Cockpit affiche le % |
| **Ce qui se passe réellement** | `AVG(Obligation.avancement_pct)` — valeurs manuelles ou seedées, jamais recalculées depuis les conso | `compliance_engine.py:211`, `kpi_service.py:218` |
| **Ce qui existe mais n'est pas câblé** | `dt_trajectory_service.compute_site_trajectory()` calcule `(1 - conso_actuelle/conso_ref) * 100` | `dt_trajectory_service.py:162` |
| **Fonction de liaison** | `update_site_avancement()` persiste le résultat sur Site | `dt_trajectory_service.py:181-195` |
| **Nombre d'appelants** | **0** | Grep confirmé |

**Tag** : À RISQUE CRÉDIBILITÉ

### KPI-2 : risque_financier_euro = 7500 EUR flat par obligation

| Aspect | Réalité | Fichier:ligne |
| --- | --- | --- |
| **Ce que l'utilisateur croit** | "Mon risque financier reflète ma situation réelle" | Cockpit et ConformitePage |
| **Ce qui se passe** | `7500 * non_conforme + 3750 * a_risque`, sans modulation surface/type | `compliance_engine.py:57,214-216` |
| **Problème** | 50 sites × 1 obligation NON_CONFORME chacun = 375 000 EUR — pas modulé | Chiffre théorique maximum, pas risque probable |

**Tag** : IMPLICITE MAIS NON FIABILISÉ — Le label "risque" ne précise pas "théorique maximum"

### KPI-3 : Scénarios achat = écarts constants

| Aspect | Réalité | Fichier:ligne |
| --- | --- | --- |
| **Ce que l'utilisateur croit** | "Les scénarios reflètent les conditions marché actuelles" | PurchasePage affiche 3 scénarios |
| **Ce qui se passe** | `price_factor` fixe : Fixe=+5%, Indexé=-5%, Spot=-12% vs. prix contrat | `purchase_scenarios_service.py:40,69,100` |
| **Problème** | Tous les sites, toutes les périodes, même écart | Un DAF compare et voit la constance |

**Tag** : À RISQUE CRÉDIBILITÉ

---

## 7. Risques crédibilité marché

### RC-1 : En démo, le fil conducteur se casse après la conformité

Un démonstrateur qui suit le parcours naturel :
1. Crée un site ✅ (patrimoine → obligations auto)
2. Voit le cockpit avec score conformité ✅ (cohérent)
3. Navigue vers ConformitePage ✅ (même source)
4. Cherche le lien vers la facture ❌ (aucun lien)
5. Va sur BillIntel par le menu ❌ (aucune mention conformité)
6. Revient sur achat ✅ (lien "Contrôler facture" existe depuis PurchasePage)
7. Compare les scénarios ❌ (écarts toujours identiques)
8. Cherche les actions générées ❌ (rien sans sync manuel)

**Impact** : Un prospect ou investisseur qui suit ce parcours verra un produit qui "se juxtapose" au lieu de "s'intégrer" à partir de l'étape 4.

### RC-2 : L'avancement DT ne bouge jamais

Si un utilisateur importe 12 mois de consommation réelle, l'avancement DT au cockpit **ne change pas** (car c'est un champ plat). Le produit semble statique là où il devrait être le plus dynamique.

### RC-3 : Le centre d'actions semble vide en usage normal

Les actions des 4 sources (compliance, billing, conso, purchase) ne sont persistées qu'après `POST /api/actions/sync`. Sans cet appel (qui n'est pas déclenché automatiquement par l'UI lors de la navigation standard), le centre d'actions reste vide.

---

## 8. Top P0 / P1 / P2

### P0 — Bloquant crédibilité démo

| # | Problème | Fichier:ligne | Impact | Correctif |
| --- | --- | --- | --- | --- |
| P0-1 | `update_site_avancement()` jamais appelé — KPI DT = champ plat | `dt_trajectory_service.py:181` (0 appelant), `compliance_coordinator.py` (ne l'appelle pas) | Avancement DT statique, ne reflète pas les conso réelles | Ajouter `update_site_avancement(db, site_id)` dans `compliance_coordinator.recompute_site_full()` après l'étape 3 |
| P0-2 | Conformité ↔ Facture = aucun lien | `ConformitePage.jsx` (0 ref billing), `BillIntelPage.jsx` (0 ref compliance) | Rupture totale entre les 2 briques les plus stratégiques | Ajouter bandeau risque financier dans BillIntelPage + CTA "Voir conformité" |

### P1 — Crédibilité marché

| # | Problème | Fichier:ligne | Impact | Correctif |
| --- | --- | --- | --- | --- |
| P1-1 | Actions achat éphémères — rien dans le centre d'actions sans sync | `purchase_actions_engine.py` (calcul) vs `action_hub_service.py:302` (sync manuelle) | Centre d'actions vide en usage normal | Auto-déclencher sync_actions() en fin de calcul scénario OU lors navigation vers ActionsPage |
| P1-2 | price_factor hardcodé (1.05/0.95/0.88) | `purchase_scenarios_service.py:40,69,100` | Écarts constants, détectables | Même simplifiés : intégrer prix moyen marché EPEX 12 mois + spread historique fixe/indexé |
| P1-3 | Pas de lien BillIntel → Conformité | `BillIntelPage.jsx` (0 ref) | Utilisateur ne comprend pas le lien argent ↔ conformité | Ajouter encart "Risque réglementaire" si site non-conforme |

### P2 — Premium

| # | Problème | Impact | Correctif |
| --- | --- | --- | --- |
| P2-1 | risque_financier_euro sans label "théorique maximum" | Chiffre anxiogène ou décrédibilisant | Ajouter tooltip/Explain "Risque maximum théorique selon Décret Tertiaire art. L174-1" |
| P2-2 | Site360 tabs Factures et Conformité non cross-référencés | Informations côte à côte mais isolées | Ajouter mini-KPI conformité dans tab Factures et vice-versa |
| P2-3 | Import conso ne trigger pas recalcul KPI | KPI cockpit stale après import | Appeler `recompute_site_full()` après import consommation réussi |

---

## 9. Plan de correction priorisé

### Immédiat (1-2 jours)

| # | Action | Fichier à modifier | Effort |
| --- | --- | --- | --- |
| 1 | Ajouter `update_site_avancement(db, site_id)` dans `recompute_site_full()` | `backend/services/compliance_coordinator.py:76` (avant return) | **1 ligne** |
| 2 | Bandeau risque financier dans BillIntelPage si site non-conforme | `frontend/src/pages/BillIntelPage.jsx` | S |
| 3 | CTA "Voir conformité" dans BillIntelPage | `frontend/src/pages/BillIntelPage.jsx` | XS |
| 4 | CTA "Voir factures" dans ConformitePage | `frontend/src/pages/ConformitePage.jsx` | XS |

### Court terme (1 semaine)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 5 | Auto-sync actions à l'ouverture d'ActionsPage | `frontend/src/pages/ActionsPage.jsx` (appel API sync au mount) | S |
| 6 | Ajouter mini-KPI conformité dans tab Factures de Site360 | `frontend/src/pages/Site360.jsx` | S |
| 7 | Label "risque théorique maximum" sur risque_financier_euro | `frontend` (tous les affichages de risque) | S |
| 8 | Appeler `recompute_site_full()` après import consommation | `backend/routes/` (endpoint import conso) | S |

### Moyen terme (2-4 semaines)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 9 | Remplacer price_factor fixe par calcul dynamique simplifié | `backend/services/purchase_scenarios_service.py` | L |
| 10 | Intégrer profil HP/HC dans les scénarios achat | `backend/services/purchase_scenarios_service.py`, `purchase_service.py` | L |

---

## 10. Definition of Done

L'étape 1 est terminée quand :

| Critère | Statut |
| --- | --- |
| Chaîne patrimoine→données tracée avec auto-provision | FAIT — 7 étapes documentées |
| Chaîne données→KPI tracée avec identification du champ plat | FAIT — `update_site_avancement` identifié (0 appelant) |
| Chaîne KPI→conformité vérifiée cohérente | FAIT — même source `compliance_score_service` |
| Rupture conformité↔facture prouvée | FAIT — 0 référence croisée (grep bilatéral) |
| Chaîne facture→achat tracée (volume réel, prix fixe) | FAIT — `EnergyInvoice.energy_kwh` + `price_factor` hardcodé |
| Chaîne achat→actions tracée (éphémère vs. persisté) | FAIT — `sync_actions()` requis |
| 3 KPI trompeurs identifiés avec preuve | FAIT — avancement DT, risque financier, écarts achat |
| Cross-navigation inter-modules cartographiée | FAIT — liens existants et manquants listés |
| P0/P1/P2 priorisés avec fichiers et effort | FAIT — 2 P0, 3 P1, 3 P2 |
| Plan de correction avec fichiers précis | FAIT — 10 actions, effort XS à L |

---

## Annexe : Navigation inter-modules existante

| Depuis | Vers | Lien | Fichier:ligne |
| --- | --- | --- | --- |
| Cockpit | Actions | "Voir plan d'action" | `Cockpit.jsx:353,511,540,916` |
| Cockpit | Site détail | Clic sur site dans TopSites | `Cockpit.jsx:777` |
| Patrimoine | Site détail | Clic sur ligne site | `Patrimoine.jsx:1074,1110,1172` |
| PurchasePage | BillIntel | "Contrôler facture" | `PurchasePage.jsx:1254-1260` |
| BillIntelPage | Purchase | "CTA vers achat énergie" | `BillIntelPage.jsx:530` |
| ConformitePage | BillIntel | **AUCUN** | — |
| BillIntelPage | Conformité | **AUCUN** | — |
| ConformitePage | Purchase | **AUCUN** | — |
| ActionsPage | Source (purchase/compliance) | Filtre par `?source=purchase` | `ActionsPage.jsx:561` |
| Site360 | Modules | Tabs internes (Resume/Conso/Factures/Conformité/Actions) | `Site360.jsx:90-97` |

**Lacunes navigation** :
- ConformitePage est **isolée** — pas de lien vers facture ni achat
- BillIntelPage ne renvoie pas vers conformité
- Le "triangle stratégique" conformité ↔ facture ↔ achat n'a qu'un seul côté câblé (facture ↔ achat)

---

*Audit étape 1 réalisé le 2026-03-23. Prêt pour l'étape 2 : audit des règles métier et conformité.*
