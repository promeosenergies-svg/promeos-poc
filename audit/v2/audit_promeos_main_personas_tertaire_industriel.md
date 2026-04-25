# Audit PROMEOS — Branche MAIN
**Date** : 2026-04-24
**Commit testé** : `43ab8f21` (branche `claude/agents-sdk-catalogue`, fonctionnellement équivalent à `origin/main` : 4 fichiers nav cleanup uniquement, aucun impact user-facing)
**Caveat** : services lancés depuis le repo principal après un redémarrage forcé (le BE tournait depuis 4h59 du matin et était figé en LISTEN sans répondre). Git SHA `43ab8f21` confirmé via `/api/health`.
**Environnement** : BE FastAPI :8001 / FE Vite :5173 / DB SQLite HELIOS restaurée (5 sites, DemoState OK)
**Auditeur** : Claude Code — 2 personas (responsable énergie multisite tertiaire + directeur énergie industrie agroalimentaire)

---

## 1. Executive Summary

### Verdict démo readiness

**Score global : 5.5/10 — BLOQUÉ EN L'ÉTAT, débloquable en 15 minutes.**

**Bloqueur unique P0 qui masque tout le reste** : une modale onboarding *"Navigation par module"* s'affiche en overlay plein écran sur **toutes** les pages dès la connexion. Elle empêche toute interaction (27/27 pages Playwright OK mais 8/8 interactions automatiques timeouts car la modale bloque les clics). Si un prospect arrive sur la démo, il doit cliquer 4 fois "Suivant" avant de voir quoi que ce soit. Aucune indication visuelle que c'est un tutoriel qu'on peut passer (le lien "Passer le tour" est discret en bas-gauche).

### Top 10 problèmes (priorité décroissante)

| # | Sévérité | Module | Problème | Impact |
|---|---------|--------|----------|--------|
| 1 | **P0** | Global | Modale *Navigation par module* en overlay sur toutes les pages, bloque clics | Zéro interaction possible en démo. Dossier démo cassé à l'accueil |
| 2 | **P0** | Cockpit | `GET /api/pilotage/nebco-simulation/retail-001` → 404 | Widget NEBCO muet dans la Vue exécutive |
| 3 | **P0** | KB | `GET /api/kb/search` → 500 Internal Server Error | Recherche Mémobox cassée côté serveur |
| 4 | **P0** | Dates billing | Factures datées `2028-09`, `2028-10`, `2028-11` flaggées "Périodes manquantes" | Données aberrantes (futur 2 ans) — perte de crédibilité KPI facturation |
| 5 | **P0** | Energy copilot | `/energy-copilot` → "Page introuvable" mais breadcrumb reste affiché comme si la route existait | Lien fantôme dans nav/commande |
| 6 | **P1** | Conformité | Warning React "Each child in a list should have a unique key prop" dans `KBObligationsSection` | Rendu React instable, bug futur probable |
| 7 | **P1** | Usages & Horaires | KPI "0%" / "0%" / "2226.72 kW" / "100" sans définition, warning React `HeatmapGrid2` | Valeurs génériques sans sens pour utilisateur |
| 8 | **P1** | Diagnostic conso | Tableau rempli de "N/A / 0 kWh / chargement" pour les 5 sites | L'écran n'apporte aucune valeur |
| 9 | **P1** | Cockpit | 67 requêtes réseau au chargement (vs 49-52 pour autres pages) | Risque dégradation perçue, N+1 probable |
| 10 | **P1** | Facturation | Section "Constat dernière facture" : "-1.7%" sans définition de ce que c'est, pas de currency unit claire | KPI illisible sans glossaire |

### Top 10 quick wins (à impact fort, effort < 1j)

1. **Désactiver la modale onboarding par défaut** ou la conditionner à un flag `seenOnboardingTour` en localStorage — 30 min
2. **Fix 404 `/api/pilotage/nebco-simulation/retail-001`** : soit endpoint absent (re-introduire), soit ID hardcodé à corriger — 1h
3. **Fix 500 `/api/kb/search`** : regarder les logs backend, typiquement manque un handler d'empty query ou type mismatch — 1h
4. **Réindexer les factures démo à des dates < aujourd'hui** : corriger `gen_billing.py` pour ne pas écrire du `2028-XX` — 2h
5. **Ajouter Empty State explicite sur `/diagnostic-conso`** plutôt que N/A partout — 1h
6. **Fixer les warnings React `key`** dans KBObligationsSection + HeatmapGrid2 — 30 min
7. **Dépublier la route `/energy-copilot`** (supprimer lazy import + redirect vers `/cockpit`) — 15 min
8. **Ajouter un badge visuel "DEMO MODE"** fixe dans le header — 20 min
9. **Ajouter tooltips `<Explain>` sur les KPIs Performance Électrique** (aimant / 70% solaire / 41 tCO₂) — 1h
10. **Préciser unités `€` vs `k€`** sur bill-intel et retirer les KPI "0 €" génériques — 30 min

### Risque principal pour la démo

**Un prospect arrive sur `/cockpit`, voit la modale, ferme, puis voit des données qu'il ne comprend pas parce que les unités/formules ne sont pas explicitées (KPI orphelins).** Il clique sur `/diagnostic-conso` et trouve un écran vide. Il clique sur `/usages-horaires` et voit "0%" partout. Il clique sur Mémobox et la recherche est cassée. **5 frictions dans les 2 premières minutes.**

---

## 2. Méthodologie

### Commandes lancées
```bash
# V2.1 — Reset BE
kill 7280                                           # BE zombie
cd backend && ./venv/bin/python main.py            # restart → gitsha 43ab8f21 OK

# V2.2 — Captures Playwright 27 routes + 8 interactions
node tools/playwright/audit-agent.mjs --interactions --out audit/v2/captures-main
# → 28 screenshots PNG (1920x1080 fullPage), 8 interactions timeout 30s chacune

# V2.3 — Console + network errors 36 routes
node tools/playwright/audit-console-network.mjs --out audit/v2/console-network-main
# → console-network-report.json (5 console errors, 2 API fails, 0 crashes, 0 404 détectés formellement)

# API sondage persona
curl /api/patrimoine/sites           # 5 sites HELIOS détaillés
curl /api/compliance/summary         # 48.4 score global
curl /api/purchase/scenarios?site_id=3  # OK scénarios
curl /api/cockpit/executive          # 404 (endpoint absent)
curl /api/cockpit/2min               # 404
curl /api/flex/score                 # 404
curl /api/billing/anomalies          # 404
curl /openapi.json                   # 649 endpoints réels
```

### Personas utilisés
- **A — Responsable énergie multisite tertiaire** (profil V1 executive summary)
- **B — Directeur énergie industrie agroalimentaire**

### Limites de l'audit
1. **Tests fonctionnels automatisés non joués** (`pytest`, `vitest`) — hors scope de cette vague, utilisateur n'a pas demandé
2. **Seed HELIOS est 100% tertiaire** (bureau, bureau, entrepôt, hôtel, école) — **aucun site industriel agroalimentaire dans la démo**. Le persona B sera évalué sur sa capacité à "se projeter" dans HELIOS (entrepôt Toulouse est le plus proche d'un contexte industriel)
3. **Interactions Playwright toutes failed** à cause du bloqueur P0 modale — captures d'états intermédiaires manquantes (drawers, dropdowns ouverts, filtres appliqués)
4. **Audit responsive non fait** (uniquement viewport 1920×1080 pour audit-agent, 1440×900 pour console-network). Mobile/tablette à faire en V2 bis si nécessaire
5. **Pas de test vocal / accessibilité WCAG** automatisé en dehors des warnings React

---

## 3. Cartographie des routes testées (36 routes)

| Route | Status HTTP | Console errs | API fails | Load ms | Requests | Verdict |
|-------|------------|-------------|-----------|---------|----------|---------|
| `/` (Command Center) | OK | 0 | 0 | 1746 | 39 | **OK** (contenu riche mais modale bloquante) |
| `/cockpit` | OK | **1** | **1** (404 NEBCO) | 2001 | 67 | **P0** 404 NEBCO + 67 requêtes |
| `/actions` | OK | 0 | 0 | 1720 | 41 | OK |
| `/notifications` | OK | 0 | 0 | 1606 | 48 | OK |
| `/patrimoine` | OK | 0 | 0 | 1766 | 43 | OK |
| `/conformite` | OK | **1** (React key) | 0 | 1793 | 52 | **P1** warning React |
| `/contrats` | OK | 0 | 0 | 1615 | 29 | OK |
| `/conformite/tertiaire` | OK | 0 | 0 | 1659 | 38 | OK |
| `/conformite/aper` | OK | 0 | 0 | 1611 | 28 | OK |
| `/consommations` | OK | 0 | 0 | 1715 | 41 | OK |
| `/consommations/explorer` | OK | 0 | 0 | 1701 | 45 | OK |
| `/consommations/portfolio` | OK | 0 | 0 | 1665 | 42 | OK (KPIs riches) |
| `/consommations/import` | OK | 0 | 0 | 1605 | 23 | OK (wizard 7 steps) |
| `/diagnostic-conso` | OK | 0 | 0 | 1614 | 35 | **P1** tableau vide N/A |
| `/monitoring` | OK | 0 | 0 | 1656 | 48 | OK (KPIs Performance Électrique) |
| `/usages-horaires` | OK | **1** (React key) | 0 | 1625 | 44 | **P1** KPI 0% génériques + warning |
| `/usages` | OK | 0 | 0 | 2064 | 49 | OK |
| `/bill-intel` | OK | 0 | 0 | 1643 | 39 | OK mais dates 2028 suspectes |
| `/billing` | OK | 0 | 0 | 1657 | 37 | OK mais mêmes dates futures |
| `/achat-energie` | OK | 0 | 0 | 1630 | 42 | OK (wizard simulation) |
| `/achat-assistant` | OK | 0 | 0 | 1684 | 40 | OK |
| `/renouvellements` | OK | 0 | 0 | 1613 | 31 | OK (2 contrats, J-88) |
| `/admin/users` | OK | 0 | 0 | 1607 | 27 | OK (4 users) |
| `/onboarding` | OK | 0 | 0 | 1663 | 25 | OK |
| `/onboarding/sirene` | OK | 0 | 0 | 1613 | 22 | OK |
| `/connectors` | OK | 0 | 0 | 1610 | 28 | OK (6 connecteurs) |
| `/activation` | OK | 0 | 0 | 1613 | 26 | OK (5/5 briques) |
| `/status` | OK | 0 | 0 | 1780 | 51 | OK (649 endpoints, 6/6 checks) |
| `/kb` (Mémobox) | OK | **1** (500 search) | **1** (500 KB search) | 1885 | 42 | **P0** API KB cassée |
| `/segmentation` | OK | 0 | 0 | 1609 | 18 | OK (HIDDEN, accessible direct) |
| `/anomalies` | OK | 0 | 0 | 1649 | 36 | OK (HIDDEN) |
| `/compliance/pipeline` | OK | 0 | 0 | 1621 | 29 | OK (HIDDEN, orpheline V1) |
| `/watchers` | OK | 0 | 0 | 1610 | 24 | OK |
| `/energy-copilot` | OK selon audit | 0 | 0 | 1597 | 18 | **P0** visuellement "Page introuvable" |
| `/energy-copilot-legacy` | OK | 0 | 0 | 1601 | 18 | idem |

**Bilan** : 36 routes visitées, 5 avec erreurs console, 2 API 4xx/5xx, 0 crash. Latence moyenne 1.7s (acceptable mais `/cockpit` lent à 2s + 67 requests suggère optimisation possible).

---

## 4. Audit Persona A — Responsable énergie multisite tertiaire

**Contexte joué** : responsable énergie d'un groupe de 80-300 sites tertiaires (bureaux, commerces, établissements recevant du public). HELIOS est cohérent avec ce profil (Siège Paris, Bureau Lyon, Entrepôt Toulouse, Hôtel Nice, École Marseille).

### Parcours joué

| # | Étape | Route | Résultat | Friction |
|---|-------|-------|----------|----------|
| 1 | J'arrive sur la démo | `/cockpit` | **Modale "Navigation par module" plein écran** | **P0** — doit cliquer "Suivant" 4× ou trouver "Passer le tour" en bas-gauche |
| 2 | Je veux comprendre mon patrimoine | `/patrimoine` | Tableau 5 sites avec KPIs (2 684€, 2.9 GWh, -47%, conformité 100%) + colonnes (CONFO, SCORE, RISQUE €, CONSO, ANOMALIES, ALERTES) | **Bon** — tableau riche. KPIs header sans définition |
| 3 | Je veux identifier mes 5 sites les plus critiques | `/patrimoine` trié | Siège Paris non_conforme score 20 ; Bureau Lyon a_risque score 48.7 ; 3 autres "a_risque" ou "conforme" | **Bon** — ranking clair, couleurs (rouge/ambre/vert) |
| 4 | Je veux savoir pourquoi ils sont critiques | clic site | Impossible (modale ou drawer indisponible via Playwright) | **Inconnu** — au moins la page Site360 existe (testée à V1 en statique) |
| 5 | Je veux vérifier ma conformité DT / BACS | `/conformite` | Score 48, Conformité majeure (46/52), Plan d'Action, warning "OPERAT 2031 en retard depuis 01/10/2025", bloc Audit Énergétique | **Bon** — écran dense mais lisible. Warning **OPERAT "en retard depuis 01/10/2025"** = vendeur de valeur |
| 6 | Je veux ouvrir un site | `/sites/1` (Siège Paris) | Non testé fonctionnellement (blocage modale) — V1 confirmait l'existence de `Site360.jsx` | **Inconnu** |
| 7 | Je veux voir s'il y a une anomalie de facture | `/bill-intel` | KPI "64 k€ factures 2026", "19 anomalies", -1.7% vs attendu. Tableau anomalies avec périodes 2025/TURPE. **Mais dates 2028-09/10/11 dans Périodes manquantes** | **P0** — données futures 2028 = perte crédibilité immédiate |
| 8 | Je veux voir les actions recommandées | `/actions` | Plan d'actions : 17 en cours, 7 urgentes, 2 en retard. Tableau 10 actions (Conformité/Facture/Contrat), IMPACT, ÉCHÉANCE, RESPONSABLE | **Bon** — très complet. Colonnes IMPACT et CA (€) vides sur certains items |
| 9 | Je veux savoir quoi faire cette semaine | `/cockpit` Top 3 | "Installer un système GTB classe A/B — Siège" / "Ajuster la puissance souscrite — Entrepôt" / "Renouveler contrat Paris — échéance 3 mois" | **Excellent** — Top 3 narratif actionnable |

### Score CX persona A

| Axe | Note /10 | Commentaire |
|-----|---------|-------------|
| Compréhension immédiate de la valeur | 4 | La modale cache la valeur pendant 30 secondes |
| Navigation | 7 | 5 modules (Accueil / Conformité / Énergie / Patrimoine / Achat) — clairs, bien conçus |
| KPIs et unités | 5 | Mix d'unités bonnes (k€, MWh, %) et KPIs orphelins sans définition (Performance Électrique "aimant" / "70% solaire") |
| Conformité | 7 | Score DT 48 + OPERAT 2031 + BACS + Audit = couverture complète. Le warning "en retard" est un excellent accroche |
| Actions | 8 | Plan d'actions riche, Top 3 priorités cockpit = l'un des meilleurs écrans |
| Crédibilité données | 4 | Factures datées 2028 = signal rouge. "0 kWh / N/A" dans diagnostic = signal rouge |
| Rapport qualité/prix ressenti | 5 | Outil riche mais 3 frictions en 2 minutes pourrissent l'impression |

**Verdict persona A** : une fois la modale passée et 2-3 bugs corrigés (factures 2028, /cockpit NEBCO 404, diagnostic vide), **l'écran Patrimoine + Conformité + Actions fait le job** pour un responsable énergie tertiaire. Crédibilité 7.5/10 post-fixes, 4.5/10 en l'état.

---

## 5. Audit Persona B — Directeur énergie industrie agroalimentaire

**Contexte joué** : directeur énergie/maintenance d'un site ou groupe agroalimentaire (froid industriel, process thermique, air comprimé, HVAC, 24/7). **Écart crédibilité immédiat** : HELIOS n'a aucun site agroalimentaire, le plus proche est **Entrepôt HELIOS Toulouse** (NAF 5210B — entreposage, 6000m², 720 MWh/an). Je documente ce que l'outil pourrait offrir pour un vrai agroalimentaire.

### Parcours joué (sur Entrepôt Toulouse)

| # | Étape | Route | Résultat | Friction |
|---|-------|-------|----------|----------|
| 1 | Je suis directeur énergie d'une usine agroalim | `/cockpit` | Modale onboarding + vue exécutive générique | Rien ne parle "industrie" |
| 2 | Je cherche pics puissance et talon nuit | `/monitoring` Performance Électrique | KPIs "À relever" / "Non détecté" / "OK" / "41 tCO₂/an" / "70% solaire" — aucune heatmap visible (cachée par modale) | **P1** KPIs non industriels, pas de kW max / baseload visible |
| 3 | Je veux voir froid/process/air comprimé | `/usages` | Répartition par usage (UsagesDashboard) — non inspecté visuellement mais **V1 confirme** la disaggregation existe (CVC, éclairage, process) | Présent mais générique tertiaire, pas d'usages spécifiques industrie |
| 4 | Je veux détecter une dérive | `/diagnostic-conso` | Tableau "N/A chargement 0kWh" pour tous les sites → rien à voir | **P1** écran inutilisable en l'état |
| 5 | Je veux voir impact en € | `/patrimoine` colonne Risque | Entrepôt Toulouse = 3 750€ risque (vs 7 500€ Siège Paris, 4 500€ autres) | **Bon** — ratio cohérent, visible |
| 6 | Je veux vérifier mes factures | `/bill-intel` | Toulouse 1 anomalie facture (absent dans tableau mais listé ailleurs) | Bon mais dates 2028 |
| 7 | Je veux identifier une opportunité flex | `/usages-horaires` ou un `/flex` | **Aucune route `/flex` exposée**. `/usages-horaires` = KPI "0%" génériques. `/api/flex/score` → 404 | **P0** module flex absent côté front (V1 carto dit route cachée, mais 0 entry) |
| 8 | Je veux un plan d'action industriel | `/actions` | "Installer GTB Siège Paris", "Mise à jour APEX Toulouse", "Maintenance BACS", "Anomalie weekend Marseille chauffage" | Actions globalement tertiaire — 1 seule évoque Toulouse |
| 9 | Je veux un achat industriel (grande volumétrie HP/HC/Pointe) | `/achat-energie` site=Entrepôt Toulouse | Scénarios fixe/indexé OK, Volume 686.9 MWh/an, tolérance risque Moyen, Priorité budget 50% — **Très bien** | **Bon** — le wizard achat est le meilleur écran pour un industriel |

### Score CX persona B

| Axe | Note /10 | Commentaire |
|-----|---------|-------------|
| Crédibilité industrie | 3 | HELIOS = 100% tertiaire. Pas de site agroalim, pas d'usages froid/process/air comprimé |
| Pics / talon nuit | 3 | Monitoring n'affiche pas clairement P max, P moy, facteur charge. Heatmap horaire cachée |
| Flex / DR | 1 | Module absent de la nav principale. `/usages-horaires` KPI 0% |
| Factures HP/HC/Pointe | 4 | TURPE 7 mentionné dans alertes mais pas de vue HP/HC dédiée évidente depuis le cockpit |
| Achat grande volumétrie | 8 | Wizard simulation + scénarios = meilleur écran persona B |
| Vocabulaire | 4 | "GTB" / "BACS" / "OPERAT" — vocabulaire tertiaire, pas de "COP", "EER", "SWEP", "NEBCO" en surface |
| Actionnabilité pour exploitation 24/7 | 5 | Plan d'action lisible mais pas d'alertes temps réel / signal EcoWatt visible |

**Verdict persona B** : **l'outil n'est pas crédible pour un vrai agroalim en l'état**, même si les briques existent (V1 confirme flex_score, usage_service ventilation, pilotage_nebco côté backend). **Le gap est côté UX/navigation** : aucune entrée principale "Flexibilité" ou "Industrie". Les KPIs sont trop tertiaires. Pour un vrai pilote industriel il faudrait :
- Un archétype agroalim dans le seed (avec usage froid, process thermique)
- Une vue "Pilotage énergie 24/7" (P max, talon nuit, facteur charge)
- Un module "Flexibilité / NEBCO / EcoWatt" accessible depuis la nav
- Du vocabulaire adapté (COP, EER, baseload)

---

## 6. Audit UX/UI transverse

### Navigation
- **Structure 5 modules + Administration** (cohérente avec NavRegistry V1) — clair
- Rail gauche icônes + Panel contextuel = pattern classique correct
- Breadcrumb fonctionnel : `PROMEOS > Module > Page`
- Scope switcher en haut : "Groupe HELIOS > Siège HELIOS Paris" — OK pour monosite/portefeuille
- Badge notifications rouge (9+ / 4) sur icônes Conformité et Énergie — visible
- Expert toggle présent en header — OK

### Layout
- Header slim ~60px avec search palette (⌘K) + notifications + Expert + user menu — pro
- Content area bien structurée
- **Modale onboarding = overlay bloquant** — P0 critique

### Responsive
- Non testé (viewport 1920×1080 + 1440×900 uniquement)
- Architecture Rail+Panel fait penser que <1024px risque de poser problème

### Graphes (Recharts)
- Courbes CDC dans `/consommations/explorer` lisibles
- Barres chronologie facture dans `/billing` OK
- Aucun graphe avec tooltip explicatif visible sur les captures

### Tables
- Patrimoine : 12 colonnes — dense mais lisible
- Actions : 10 actions avec colonne STATUT, SITE, IMPACT — bon
- Admin users : 4 users, colonnes claires

### Copy
- **Français correct** en général
- Micro-typo dans Connectors : "Production photovoltaïque" vs "photovoltaïque" OK
- "CORMITÉ" visible dans une colonne Activation (page 22) → **typo probable**
- Labels techniques non traduits : "BACS", "OPERAT", "APEX", "NEBCO", "TURPE" — OK dans contexte B2B

### États vides / erreur / loading
- **Loading** : Skeletons vus (animate-pulse). Audit script les attend (waitForFunction)
- **Empty** : `/diagnostic-conso` remplit le tableau de N/A au lieu d'un EmptyState propre → **P1**
- **Error** : `/energy-copilot` affiche "Page introuvable" → correct mais la route ne devrait pas être atteignable
- **KB search 500** : aucun message utilisateur visible — erreur silencieuse

### Accessibilité
- 3 warnings React `key prop missing` → **P1 a11y/stabilité**
- Contraste rayons bleus actifs OK
- Pas d'audit WCAG AA automatisé fait

---

## 7. Audit métier énergie

### Unités vérifiées

| KPI | Unité affichée | Correct ? |
|-----|---------------|----------|
| Consommation | MWh (ex: 758,4 MWh, 2 653 MWh) | ✓ |
| Coût | k€ (ex: 90 k€, 64 k€) + € pur (ex: 8 k€ dernière visite) | ⚠ Mix k€/€ selon écran |
| Risque € | € pur (ex: 7 500€, 3 750€) | ⚠ À passer en k€ pour cohérence |
| CO₂ | tCO₂e/an (ex: 41 tCO₂e/an) | ✓ |
| Puissance | kW (2226.72 kW sur Usages horaires) | ✓ mais précision excessive (2 décimales) |
| Score | 0-100 | ✓ |

**Écart principal** : mix k€/€ selon l'écran — à standardiser en **k€ partout**.

### KPIs et définition
- **Aucun KPI n'a de tooltip visible** (le composant `<Explain>` existe mais n'est pas systématique)
- **Performance Électrique** `/monitoring` : KPIs opaques ("aimant" / "Non détecté" / "70% solaire") → **P1**
- Score conformité 48.4 % avec breakdown (DT/BACS/APER) : **source affichée "RegAssessment"** ✓ — bon
- Score global /100 vs /52 (46/52 obligations) : **dénominateurs différents** sur la même page → à harmoniser

### Cohérence transverse

| Même donnée | Cockpit | Portfolio Conso | Patrimoine | Note |
|-------------|---------|-----------------|------------|------|
| Total sites | "Groupe HELIOS" | 5/5 sites | 5 sites | ✓ cohérent |
| Total MWh an | 2 653 MWh (affiché Tableau bord) | 758.4 MWh (Portefeuille Consommation) | 2 905 GWh (header Patrimoine) | **❌ 3 valeurs différentes pour ce qui semble la même mesure** |
| Total coût € | 8 k€ (header) / 10 000€ risque | 90 k€ (Consommation) | 2 684€ / 8 456€ | **❌ incohérence — probablement périodes ou périmètres différents mais non explicité** |
| Score conformité | 48 (conformité.page) / 100% (patrimoine.page) | — | 100% (patrimoine header) | **❌ 48 vs 100% sans contexte** |

**Verdict métier** : **incohérences majeures** entre écrans sur les chiffres totaux de consommation, coût et score conformité. Sans source+période+périmètre affichés, impossible de dire si c'est un bug ou juste des unités différentes. **P0 crédibilité**.

### Billing / shadow billing
- `/bill-intel` : 19 anomalies détectées, coût facturé 104k€ vs attendu 105k€ → -1.7% ✓ cohérent avec shadow billing
- `/billing` : timeline mensuelle sur années visibles (2024-2028) → **dates 2028 suspectes**

### Achat post-ARENH
- `/achat-energie` : scénarios fixe/indexé/spot visibles, prix spot 62 EUR/MWh (cohérent marché 2026 actuel)
- Budget badge "Budget élevé" en rouge = pédagogique
- Mentions NEBCO/flex absentes des scénarios — gap

### Actions
- Plan d'actions cohérent avec triggers conformité (BACS, TURPE, APER)
- Liens site ↔ action visibles dans colonne SITE
- Responsables affichés — bon

---

## 8. Audit technique

### Front
- React 18 + Vite, lazy-loaded, 51 routes
- Skeletons + Empty/Error states : présents mais inégaux (Admin, Diagnostic partiels)
- **3 warnings React `key prop`** dans KBObligationsSection + HeatmapGrid2 → ombrelle P1

### API
- **649 endpoints exposés** via OpenAPI (cartographie V1 disait 607 — écart lié au comptage)
- 2 fails identifiés en navigation :
  - `404 /api/pilotage/nebco-simulation/retail-001?period_days=30` (cockpit)
  - `500 /api/kb/search` (Mémobox)
- `/api/health` répond ✓, `/api/demo/status` ✓, `/api/patrimoine/sites` ✓, `/api/purchase/scenarios` ✓
- `/api/flex/score?site_id=3` → **404** (endpoint absent côté prod)
- `/api/billing/anomalies?site_id=1` → **404** (path différent probablement `/api/bill/...`)
- `/api/cockpit/executive` → **404**, `/api/cockpit/2min` → **404** (cartographie V1 datée)

### Console
- 5 erreurs console sur 36 routes (14%) — **correct mais à 0 c'est mieux**
- Dominantes : React key props + 2 API fails

### Network
- Moyenne 36 requêtes par page (cockpit = 67, /usages = 49)
- Tous les temps < 2.1s → **OK**
- `/cockpit` 67 requêtes suggère un pattern N+1 ou appels en série (à auditer)

### Performance ressentie
- Backend warmup 12s au démarrage (DemoState restore)
- Skeletons durent ~1-2s par page

### Tests existants (cf V1)
- 330 fichiers tests pytest + vitest
- **Non rejoués dans cette vague**

### Dette technique visible
- 3 warnings React `key prop` — dette facile à résorber
- Routes legacy `/energy-copilot`, `/conformite/sites`, `/compliance/pipeline` encore actives
- Mix k€/€ non standardisé
- Dates factures 2028 : **bug seed** `gen_billing.py`

---

## 9. Backlog priorisé (18 issues)

| ID | Sévérité | Module | Problème | Impact | Reproduction | Correction recommandée | Effort | Risque régression |
|----|---------|--------|---------|--------|--------------|-----------------------|--------|-------------------|
| M-01 | P0 | Global | Modale onboarding bloquante overlay toutes pages | Démo inutilisable | Connexion → tout écran → modale plein | Flag `localStorage.seenNavTour` + bouton "skip" visible en haut | 30min | Faible |
| M-02 | P0 | Cockpit | `404 /api/pilotage/nebco-simulation/retail-001` | Widget NEBCO muet | F12 > Network sur /cockpit | Corriger ID retail-001 ou exposer endpoint absent | 1h | Faible |
| M-03 | P0 | KB | `500 /api/kb/search` | Mémobox inutilisable | F12 > Network sur /kb | Tail logs BE + try/catch empty query | 1h | Moyen |
| M-04 | P0 | Seed | Factures dates 2028-09/10/11 | Crédibilité pourrie | /billing > Périodes manquantes | Fix `gen_billing.py` — clamp max date à today | 2h | Moyen |
| M-05 | P0 | Routing | `/energy-copilot` → "Page introuvable" mais breadcrumb affiche | Lien fantôme | Nav vers /energy-copilot | Supprimer lazy import + redirect /cockpit | 15min | Faible |
| M-06 | P0 | Cohérence | 3 valeurs différentes pour "total MWh an" (2 653 / 758 / 2 905 GWh) | Crédibilité | Compare Cockpit vs Portfolio Conso vs Patrimoine | Source unique `consumption_unified_service` + afficher période/périmètre | 1j | Élevé |
| M-07 | P0 | Cohérence | 2 valeurs score conformité (48 vs 100%) | Confusion | /conformite vs /patrimoine header | Clarifier "Score global /100" vs "% sites conformes" | 2h | Moyen |
| M-08 | P1 | Diagnostic | Tableau 5 sites "N/A 0 kWh chargement" | Écran inutile | /diagnostic-conso | EmptyState + CTA "Lancer diagnostic" | 1h | Faible |
| M-09 | P1 | Usages horaires | KPI "0% / 0% / 2226.72 kW / 100" génériques | Incompréhensible | /usages-horaires | Remplir KPI avec vraies métriques (talon nuit, pic jour) | 3h | Moyen |
| M-10 | P1 | Monitoring | Performance Électrique KPIs sans définition | Incompréhensible | /monitoring | Ajouter `<Explain>` tooltip sur chaque KPI | 2h | Faible |
| M-11 | P1 | Billing | -1.7% sans currency unit / définition | KPI illisible | /bill-intel | Tooltip "écart shadow vs facturé %" | 30min | Faible |
| M-12 | P1 | React | 3 warnings `key prop` (KBObligationsSection, HeatmapGrid2) | Stabilité rendu | Console /conformite et /usages-horaires | Ajouter `key={item.id}` | 30min | Faible |
| M-13 | P1 | Unités | Mix k€ / € sur écrans | Cohérence | Cockpit / Patrimoine / Bill | Standardiser k€ partout (fonction `fmtMoney`) | 2h | Moyen |
| M-14 | P1 | Activation | Typo "CORMITÉ" colonne | Crédibilité | /activation tableau | Fix colonne → "CONFORMITÉ" | 5min | Faible |
| M-15 | P1 | Nav persona B | Aucune entrée "Flexibilité" / industrie | Crédibilité persona B | Nav menu | Ajouter module ou section Flex dans Énergie | 1j | Moyen |
| M-16 | P2 | Seed | Aucun site agroalimentaire/industriel vrai | Crédibilité persona B | /patrimoine | Créer pack HELIOS-INDUSTRIE (3 sites) | 2j | Faible |
| M-17 | P2 | A11y | WCAG AA non audité | Risque compliance | Pages clés | Audit axe-core systématique | 1j | Faible |
| M-18 | P2 | Badge | Pas de badge "DEMO MODE" visible | Confusion réel vs démo | Header | Badge ambré fixed top | 20min | Faible |

---

## 10. Plan de correction

### P0 — à corriger avant toute démo (< 1 jour cumulé)
1. **M-01 Modale onboarding** — 30 min
2. **M-05 /energy-copilot** — 15 min
3. **M-02 NEBCO 404** — 1h
4. **M-03 KB search 500** — 1h
5. **M-14 Typo CORMITÉ** — 5 min (bonus a11y)

### P0 data cohérence (< 2 jours)
6. **M-04 Factures 2028** — 2h (seed)
7. **M-06 3 valeurs MWh différentes** — 1j (architecture)
8. **M-07 Score 48 vs 100%** — 2h

### P1 — crédibilité B2B (< 2 jours)
9. M-08 Diagnostic Empty State — 1h
10. M-09 Usages horaires KPIs — 3h
11. M-10 Tooltips Performance — 2h
12. M-11 Tooltip -1.7% — 30min
13. M-12 React key warnings — 30min
14. M-13 k€ standardisation — 2h

### P2 — best-in-world (effort variable)
15. M-15 Module Flex visible — 1j
16. M-16 Seed industriel — 2j
17. M-17 Audit WCAG AA — 1j
18. M-18 Badge DEMO — 20min

**Estimation cumulée P0 + P1** : **~4-5 jours/homme**. Démo robuste possible après 1j (P0 bloquants seuls).

---

## 11. Definition of Done recommandée avant démo cliente

- [ ] **M-01** fait + test visuel cockpit/patrimoine/conformite sans modale bloquante
- [ ] **M-02, M-03, M-05** fait + `console` clean sur `/cockpit`, `/kb`, `/energy-copilot`
- [ ] **M-04** fait + seed HELIOS S reset + vérif toutes dates factures < today
- [ ] **M-06, M-07** fait + même chiffre sur 3 écrans différents pour la même mesure
- [ ] Test utilisateur non-technique joue le parcours persona A en 5 min sans help
- [ ] 0 erreur console critique sur les 10 routes les plus visibles
- [ ] Screenshot de chaque route archive dans `audit/v2/captures-main-v2/`
