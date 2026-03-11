# PLAN D'EXÉCUTION PROMEOS — 90 JOURS

> **Date** : 11 mars 2026
> **Rôle** : Chief of Staff Produit + Principal PM + Program Manager
> **Version** : 2.0 — Plan opérable
> **Horizon** : 12 semaines (11 mars → 3 juin 2026)

---

## 1. SYNTHÈSE EXÉCUTIVE

### La roadmap actuelle en 10 lignes

PROMEOS a un wedge solide : conformité énergétique multi-sites exécutable et opposable. Le POC couvre 3 cadres (DT + BACS + APER), moteur YAML explicable, score unifié, shadow billing, 5586 tests green. La séquence stratégique est bonne : crédibilité → opposabilité → automatisation → plateforme. **Mais** la roadmap H1 mélange 4 initiatives de natures différentes (coffre + PDF + notifications + APER enrichi), sans gates de passage, avec 7 KPIs dilués. APER enrichi n'a aucune dépendance sur le coffre et dilue le focus. Le benchmark sectoriel est positionné trop tard alors qu'il est le seul argument qui convainc un DG. La roadmap est stratégiquement juste mais opérationnellement molle — pas de semaine, pas de livrable précis, pas de critère de passage.

### Message central

> **En 90 jours, PROMEOS doit passer de "POC qui montre" à "plateforme qui prouve".**
> Cela se traduit par 4 paris et seulement 4 :
> **Coffre de preuves** (le verrou) → **Dossier PDF** (le livrable) → **Notifications** (la rétention) → **Benchmark V0** (la crédibilité).
> Tout le reste attend. APER enrichi passe en quick win opportuniste.
> On mesure 3 choses : preuves déposées, PDF générés, actions tracées.

---

## 2. DÉCISIONS

### FAITS

**Ce que la roadmap actuelle fait bien :**
- Thèse de domination claire : chaîne Patrimoine → Obligation → Risque → Action → Preuve → Impact
- Séquence stratégique cohérente : crédibilité → opposabilité → automatisation → plateforme
- Identification correcte du coffre de preuves comme moat #1
- Positionnement anti-cabinet, anti-GTB, anti-dashboard juste
- Base technique solide (5586 tests, seed démo crédible, architecture propre)

**Ce qui est trop large :**
- H1 contient 4 initiatives dont une (APER enrichi) sans lien avec les 3 autres
- 7 KPIs → impossible de focaliser une petite équipe
- Pas de granularité semaine — "0-30 jours" n'est pas un plan
- Benchmark positionné en H2 alors que c'est l'argument DG #1 en démo
- Pas de gate de passage → risque de dériver indéfiniment

### HYPOTHÈSES

**Ce qui peut être déplacé sans risque :**
- APER enrichi → quick win opportuniste (2j max) ou H2. Impact moat = faible. Aucun prospect ne choisit PROMEOS pour le calcul kWc APER.
- Workflow multi-acteurs → H3 minimum. Aucun client n'a encore 2 rôles actifs.
- Simulation "si j'agis" → H3. Nécessite benchmark + projection, trop tôt.
- Lien conformité→facture → H2. Shadow billing existe, le lien visible peut attendre.

**Ce qui doit rester non négociable :**
- Coffre de preuves persisté → c'est le verrou d'adoption ET le moat. Sans ça, PROMEOS = dashboard de plus.
- Dossier PDF exportable → c'est le livrable qui justifie l'abonnement. Sans ça, pas de monétisation.
- Notifications échéances → c'est la rétention. Sans ça, l'utilisateur oublie PROMEOS entre 2 comités.
- Benchmark V0 → c'est la crédibilité DG. "Score 46/100" ne veut rien dire sans référentiel.

### DÉCISIONS

**4 paris retenus pour les 90 jours :**

| # | Pari | Sert | Semaines |
|---|------|------|----------|
| 1 | **Coffre de preuves persisté** | Moat + adoption + démo | S1–S4 |
| 2 | **Dossier PDF comité** | Monétisation + démo | S3–S6 |
| 3 | **Notifications échéances intelligentes** | Rétention + valeur perçue | S5–S8 |
| 4 | **Benchmark sectoriel V0** | Crédibilité DG + démo | S7–S10 |

**APER** : repositionné en quick win opportuniste (voir Partie 2).

**KPIs retenus** : preuves déposées, PDF générés, actions créées depuis conformité.

---

## 3. LES 4 PARIS — DÉTAIL

### PARI 1 — Coffre de preuves persisté

**Pourquoi maintenant** : Aujourd'hui les preuves sont un `useState({})` — elles disparaissent au refresh. C'est le gap le plus critique entre "démo qui impressionne" et "outil utilisable". Aucun prospect ne déploie un outil où les preuves s'évaporent.

**Ce que cela débloque** :
- L'utilisateur dépose une preuve, fait F5, la retrouve → confiance
- Le dossier PDF peut inclure les preuves jointes → opposabilité
- Le taux de preuves par obligation devient mesurable → KPI
- Lock-in : une fois les preuves dedans, le client ne migre plus

**Ce que cela reporte** : Rien. C'est le prérequis de tout le reste.

**Impact attendu** : 100% des obligations conformes ont au moins 1 preuve jointe en démo. Upload + retrieval + inclusion PDF fonctionnels.

**Livrables** :
- Backend : modèle `ProofFile` (id, obligation_id, site_id, filename, content_type, size_bytes, hash_sha256, uploaded_by, uploaded_at, storage_path)
- Backend : API REST `POST/GET/DELETE /api/compliance/obligations/{id}/proofs`
- Backend : stockage fichier local (filesystem) avec migration S3 prévue
- Frontend : remplacement `proofFiles` state → appels API
- Frontend : composant `ProofUpload` (drag & drop, progress, types acceptés)
- Contraintes : max 10 Mo, types PDF/JPG/PNG, hash de vérification

### PARI 2 — Dossier PDF comité

**Pourquoi maintenant** : Le DossierPrintView existe mais c'est un print CSS. Un vrai PDF généré côté serveur est le livrable qui justifie l'abonnement. C'est ce que le DG montre en comité. Sans PDF, PROMEOS = outil technique. Avec PDF, PROMEOS = outil de gouvernance.

**Ce que cela débloque** :
- Le DG a un livrable tangible → justification abonnement
- Le PDF inclut les preuves du coffre → boucle complète
- Le PDF est horodaté et signé → opposabilité
- Les rapports périodiques (H3) réutilisent le même engine

**Ce que cela reporte** : La projection 2030 dans le PDF (ajoutée quand benchmark sera prêt).

**Impact attendu** : PDF téléchargeable en 1 clic, contenant score + obligations + findings + preuves jointes + top urgences + date de génération.

**Livrables** :
- Backend : service `pdf_generator.py` (WeasyPrint ou Playwright PDF)
- Backend : endpoint `GET /api/compliance/dossier/{org_id}/pdf`
- Backend : template HTML/CSS optimisé impression (logo, en-tête, pagination)
- Frontend : bouton "Télécharger le dossier PDF" dans ConformitePage
- Contenu : page de garde, score synthèse, tableau obligations, findings critiques, preuves jointes (miniatures), plan d'actions top 5, date + signature

### PARI 3 — Notifications échéances intelligentes

**Pourquoi maintenant** : Aujourd'hui PROMEOS est passif — l'utilisateur doit penser à revenir. Les notifications transforment PROMEOS en vigie réglementaire. C'est le mécanisme de rétention #1 : "PROMEOS m'a alerté, je n'aurais pas su sans."

**Ce que cela débloque** :
- Rétention hebdomadaire → l'utilisateur revient
- Perception de valeur proactive → "PROMEOS travaille pour moi"
- Email digest → touche les non-utilisateurs quotidiens
- Prépare les alertes réglementaires intelligentes (H3)

**Ce que cela reporte** : La veille réglementaire (changements de textes). On se concentre sur les échéances connues.

**Impact attendu** : Notifications J-90 / J-30 / J-7 / J-0 / J+30 pour chaque obligation non conforme. Email digest hebdomadaire optionnel.

**Livrables** :
- Backend : service `notification_engine.py` (calcul échéances, déclenchement)
- Backend : modèle `Notification` (id, org_id, user_id, type, title, body, read, created_at)
- Backend : API `GET /api/notifications` + `PATCH /api/notifications/{id}/read`
- Backend : cron hebdomadaire (ou endpoint trigger)
- Frontend : icône cloche dans AppShell avec badge compteur
- Frontend : panneau notifications (liste, mark as read, lien vers obligation)
- Templates : "Échéance BACS dans 30 jours — 3 sites concernés", "Échéance OPERAT dépassée depuis 14 mois"

### PARI 4 — Benchmark sectoriel V0

**Pourquoi maintenant** : "Score 46/100" ne parle pas à un DG. "Votre bureau est au P75 des bureaux IDF" parle immédiatement. Le benchmark est l'argument de crédibilité #1 en démo. Il contextualise chaque obligation et justifie chaque action.

**Ce que cela débloque** :
- Crédibilité DG → le score a un référentiel
- Widget "vs médiane" dans ObligationsTab DT → impact visuel fort
- Prépare la projection 2030 (H2) qui s'appuie sur le benchmark
- Argument commercial : "Vous êtes 40% au-dessus de la médiane"

**Ce que cela reporte** : La projection 2030 complète (courbe trajectoire) → début H2.

**Impact attendu** : Widget "Votre site vs médiane secteur" visible dans chaque obligation DT en démo.

**Livrables** :
- Backend : modèle `BenchmarkRef` (usage, zone_climat, surface_tranche, conso_kwh_m2_median, p25, p75, source, year)
- Backend : seed données ADEME/CEREN (10 usages × 3 zones climat × 3 tranches surface)
- Backend : endpoint `GET /api/compliance/benchmark?usage=bureau&zone=H1&surface=2500`
- Frontend : widget "vs médiane" dans ObligationsTab (barre horizontale : P25 | médiane | P75 | votre site)
- Frontend : intégration dans le score header ("Score 46/100 — P65 du secteur Bureaux IDF")

---

## 4. DÉCISION APER ENRICHI

### Verdict : Quick win opportuniste — hors chemin critique

| Critère | Évaluation |
|---------|------------|
| **Impact perçu** | Faible. Aucun prospect n'a demandé le calcul kWc APER. L'obligation APER est déjà affichée (assujettissement OK/UNKNOWN). |
| **Impact moat** | Nul. Le calcul kWc/m² est une formule triviale que tout concurrent peut reproduire en 2h. Aucun lock-in. |
| **Effort** | 2j back + 1j front = 3j. Faible mais pas nul. 3j c'est la moitié d'un sprint. |
| **Dépendances** | Aucune. Ni le coffre, ni le PDF, ni le benchmark n'en ont besoin. Et APER enrichi n'a besoin d'aucun d'eux. |
| **Urgence marché** | Faible. L'échéance APER est juillet 2026. Les parkings > 1500m² concernent peu de prospects early. |

### Décision

**APER enrichi passe en quick win opportuniste** :
- Si un développeur a une demi-journée libre entre deux sprints → il peut l'implémenter
- Il ne bloque aucun autre pari
- Il ne figure pas dans le plan 12 semaines
- Il peut être ajouté à n'importe quel moment sans perturber la séquence
- Cible réaliste : S11-S12 si le plan est en avance, sinon début H2

**Ce qu'on garde en H1** : L'affichage APER existant (assujettissement, statut, échéance) est suffisant pour la démo.

---

## 5. GATES DE PASSAGE

### Gate G1 : H1 → H2 (fin S6, ~22 avril)
> **Question clé** : "Les preuves sont-elles persistées et le dossier est-il exportable ?"

| # | Critère | Seuil | Pourquoi il compte |
|---|---------|-------|-------------------|
| 1 | Upload preuve → F5 → preuve toujours là | 100% fiable | Si ça casse, tout le moat s'effondre |
| 2 | PDF dossier téléchargeable avec preuves incluses | Fonctionnel en démo | C'est le livrable qui justifie l'abonnement |
| 3 | % obligations démo avec au moins 1 preuve | ≥ 60% | Prouve que le coffre est utilisable et le seed crédible |
| 4 | Temps upload → affichage dans obligation | < 3 secondes | UX minimum pour adoption |
| 5 | Zéro régression tests (frontend + backend) | 100% green | Non négociable |

**Si G1 n'est pas atteint** : on ne commence PAS le benchmark. On reste sur coffre + PDF jusqu'à ce que ce soit solide.

---

### Gate G2 : H2 → H3 (fin S10, ~20 mai)
> **Question clé** : "PROMEOS notifie-t-il et contextualise-t-il le score ?"

| # | Critère | Seuil | Pourquoi il compte |
|---|---------|-------|-------------------|
| 1 | Notifications échéances générées pour toutes les obligations non conformes | 100% couverture | La vigie doit être exhaustive |
| 2 | Email digest fonctionnel (même si pas encore envoyé en prod) | Testable en démo | Prouve la rétention proactive |
| 3 | Widget "vs médiane secteur" visible sur obligations DT | Fonctionnel en démo | Crédibilité DG |
| 4 | Nb de PDF générés en tests/démo | ≥ 5 distincts | Prouve que le PDF est utilisable, pas un one-shot |
| 5 | Parcours démo 15 min fluide (coffre + PDF + notif + benchmark) | Déroulé sans accroc | La démo est la preuve ultime |

**Si G2 n'est pas atteint** : on ne lance PAS la projection 2030. On stabilise notifications + benchmark.

---

### Gate G3 : H3 → H4 (fin S12+, ~3 juin → mois 4-6)
> **Question clé** : "Peut-on montrer PROMEOS à 5 prospects et obtenir un feedback structuré ?"

| # | Critère | Seuil | Pourquoi il compte |
|---|---------|-------|-------------------|
| 1 | 3 démos réalisées avec prospects réels | 3 démos min | Validation marché, pas seulement technique |
| 2 | Feedback structuré collecté (grille 10 critères) | 3 feedbacks | Base de décision pour H4 |
| 3 | Projection trajectoire 2030 visible dans obligation DT | Fonctionnel | Narratif long terme = rétention prospect |
| 4 | Lien conformité → consommation visible en UI | Widget conso dans obligation | Différenciation cockpit |
| 5 | Temps onboarding démo (seed → 1er dossier PDF) | < 10 minutes | Prouve la fluidité du parcours |

---

## 6. PLAN D'EXÉCUTION 12 SEMAINES

> **Équipe hypothèse** : 1 lead dev fullstack + 1 contributeur partiel (0.5 ETP)
> **Cadence** : sprint hebdomadaire, review vendredi
> **Convention** : chaque semaine produit un livrable démontrable

---

### SPRINT 1 — Semaine 1 (11-14 mars)
**PARI 1 : Coffre de preuves — Fondations backend**

| | |
|---|---|
| **Objectif** | Modèle ProofFile + API REST + stockage fichier |
| **Livrables** | `models/proof_file.py` (modèle SQLAlchemy), migration Alembic, `routes/proofs.py` (POST upload multipart, GET list, GET download, DELETE), stockage filesystem `data/proofs/{org_id}/{obligation_id}/`, validation type/taille |
| **Owner** | Lead dev (backend) |
| **Dépendances** | Modèle Obligation existant (OK) |
| **Risque** | Upload multipart avec FastAPI + SQLite → tester avec fichiers 10 Mo |
| **Preuve vendredi** | `curl POST` un PDF → `curl GET` le retrouve → `curl DELETE` le supprime. Tests pytest green. |

---

### SPRINT 2 — Semaine 2 (17-21 mars)
**PARI 1 : Coffre de preuves — Frontend upload**

| | |
|---|---|
| **Objectif** | Composant ProofUpload + remplacement useState → API |
| **Livrables** | `components/ProofUpload.jsx` (drag & drop, progress bar, types acceptés badge, suppression), `services/proofService.js` (uploadProof, getProofs, deleteProof), remplacement `proofFiles` state dans ConformitePage par appels API, PreuvesTab connecté à l'API |
| **Owner** | Lead dev (frontend) |
| **Dépendances** | API Sprint 1 (backend doit tourner) |
| **Risque** | UX drag & drop sur tous navigateurs → fallback input file |
| **Preuve vendredi** | Upload un PDF dans obligation BACS → F5 → le fichier est toujours là. Vitest green. |

---

### SPRINT 3 — Semaine 3 (24-28 mars)
**PARI 1 : Coffre — Polish + hash + seed démo / PARI 2 : PDF — Exploration**

| | |
|---|---|
| **Objectif** | Coffre production-ready + spike PDF |
| **Livrables** | Hash SHA-256 sur chaque upload (intégrité vérifiable), seed démo enrichi (gen_compliance seed des ProofFile réalistes : attestation BACS, déclaration OPERAT, rapport audit), compteurs preuves dans ObligationsTab ("2/3 preuves jointes"), **spike** : test WeasyPrint vs Playwright PDF vs html-pdf, choix technique documenté |
| **Owner** | Lead dev (fullstack) |
| **Dépendances** | Sprint 2 complet |
| **Risque** | WeasyPrint difficile sur Windows → Playwright `page.pdf()` en fallback |
| **Preuve vendredi** | `--reset` seed → preuves visibles dans PreuvesTab. Spike PDF : 1 page PDF générée avec score. |

---

### SPRINT 4 — Semaine 4 (31 mars - 4 avril)
**PARI 2 : Dossier PDF — Template + engine backend**

| | |
|---|---|
| **Objectif** | Service PDF complet côté backend |
| **Livrables** | `services/pdf_generator.py` (template HTML/CSS, rendu PDF), template : page de garde (logo PROMEOS, org, date), score synthèse (score/100 + breakdown DT/BACS/APER), tableau obligations (statut, échéance, avancement), findings critiques (top 5), section preuves (liste avec dates upload), endpoint `GET /api/compliance/dossier/{org_id}/pdf` |
| **Owner** | Lead dev (backend) |
| **Dépendances** | Coffre preuves (Sprint 1-3) pour inclure les fichiers |
| **Risque** | Mise en page CSS complexe → garder simple, itérer |
| **Preuve vendredi** | `curl GET .../pdf` → PDF lisible avec score + obligations + preuves listées |

---

### SPRINT 5 — Semaine 5 (7-11 avril)
**PARI 2 : PDF frontend + PARI 3 : Notifications — Fondations**

| | |
|---|---|
| **Objectif** | Bouton PDF dans l'app + modèle notifications |
| **Livrables** | **PDF** : bouton "Télécharger le dossier PDF" dans ConformitePage (remplace ou complète le DossierPrintView), feedback loading/success. **Notifications** : modèle `Notification` (id, org_id, user_id, type, severity, title, body, link, read, created_at), migration, `routes/notifications.py` (GET list, PATCH read, PATCH read-all) |
| **Owner** | Lead dev (fullstack) |
| **Dépendances** | PDF backend Sprint 4 |
| **Risque** | Téléchargement PDF gros (si preuves incluses en images) → limiter à listing |
| **Preuve vendredi** | Clic "Télécharger PDF" → PDF se télécharge. API notifications retourne []. |

---

### SPRINT 6 — Semaine 6 (14-18 avril)
**PARI 3 : Notifications — Engine + Frontend**

| | |
|---|---|
| **Objectif** | Moteur de calcul échéances + UI cloche |
| **Livrables** | `services/notification_engine.py` : scan obligations, génère notifications J-90/J-30/J-7/J-0/J+30 (échéance dépassée), déduplique (pas de doublon si déjà notifié), endpoint `POST /api/notifications/trigger` (déclenche le scan). Frontend : icône cloche dans AppShell avec badge rouge (nb non lues), panneau dropdown (liste notifications, clic → navigation vers obligation), mark as read |
| **Owner** | Lead dev (fullstack) |
| **Dépendances** | Modèle Notification Sprint 5 |
| **Risque** | Trop de notifications → regrouper par régulation ("3 obligations BACS arrivent à échéance") |
| **Preuve vendredi** | Trigger → 5+ notifications générées. Cloche avec badge. Clic → obligation. |

**>>> GATE G1 — Vérification fin S6 <<<**

---

### SPRINT 7 — Semaine 7 (21-25 avril)
**PARI 3 : Notifications — Email digest + PARI 4 : Benchmark — Données**

| | |
|---|---|
| **Objectif** | Email digest template + table benchmark |
| **Livrables** | **Notifications** : template email digest HTML (résumé hebdo : nb urgences, échéances proches, actions ouvertes), service `email_digest.py` (génère le HTML, prêt pour envoi SMTP/SendGrid — sans envoi réel en POC, juste endpoint preview). **Benchmark** : modèle `BenchmarkRef` (usage, zone_climat, surface_tranche, conso_kwh_m2_median, p25, p75, source, year), migration, seed données ADEME/CEREN (bureaux, enseignement, commerces × H1/H2/H3 × petit/moyen/grand) |
| **Owner** | Lead dev (backend) |
| **Dépendances** | Données ADEME publiques (disponibles) |
| **Risque** | Données ADEME pas toujours granulaires → utiliser les agrégats disponibles, documenter les hypothèses |
| **Preuve vendredi** | Preview email digest HTML lisible. Table benchmark_refs avec 30+ entrées seedées. |

---

### SPRINT 8 — Semaine 8 (28 avril - 2 mai)
**PARI 4 : Benchmark — API + Widget frontend**

| | |
|---|---|
| **Objectif** | Widget "vs médiane secteur" fonctionnel |
| **Livrables** | Backend : endpoint `GET /api/compliance/benchmark` (params : usage, zone, surface → retourne median, p25, p75), matching automatique site → benchmark (via usage + zone_climat + surface). Frontend : widget barre horizontale dans ObligationsTab (P25 | médiane | P75 | "Votre site" avec marqueur), couleur contextuelle (vert si < médiane, orange si médiane-P75, rouge si > P75), intégration dans score header ("Score 46/100 — positionnement P65") |
| **Owner** | Lead dev (fullstack) |
| **Dépendances** | Seed benchmark Sprint 7 |
| **Risque** | Matching site → usage pas toujours évident → utiliser le champ `usage` du site ou fallback "bureau" |
| **Preuve vendredi** | Widget "vs médiane" visible dans obligation DT en démo. Barre avec P25/médiane/P75/site. |

---

### SPRINT 9 — Semaine 9 (5-9 mai)
**Intégration complète + benchmark dans PDF**

| | |
|---|---|
| **Objectif** | Tout fonctionne ensemble, benchmark dans le PDF |
| **Livrables** | Benchmark intégré dans le PDF dossier (section "Positionnement sectoriel"), notifications intégrées dans la démo seed (trigger auto au seed), parcours démo 15 min validé de bout en bout (cockpit → conformité → obligation expandée → preuves → PDF → notifications → benchmark), correction de tous les bugs d'intégration |
| **Owner** | Lead dev (fullstack) |
| **Dépendances** | Sprints 1-8 tous livrés |
| **Risque** | Intégration cross-features → prévoir 1j de bug fixing |
| **Preuve vendredi** | Parcours démo complet sans accroc, filmé en screencast. |

---

### SPRINT 10 — Semaine 10 (12-16 mai)
**Stabilisation + tests + polish démo**

| | |
|---|---|
| **Objectif** | Production-ready, zéro bug démo |
| **Livrables** | Tests backend complets : test_proofs.py, test_pdf_generator.py, test_notifications.py, test_benchmark.py. Tests frontend : source guards pour chaque nouveau composant. Polish UX : loading states, error handling, empty states cohérents. Seed démo optimal : preuves réalistes, notifications pré-générées, benchmark visible immédiatement |
| **Owner** | Lead dev (fullstack) |
| **Dépendances** | Sprint 9 complet |
| **Risque** | Tests révèlent des edge cases → buffer S11 |
| **Preuve vendredi** | CI 100% green (backend + frontend). Aucun crash en parcours démo. |

**>>> GATE G2 — Vérification fin S10 <<<**

---

### SPRINT 11 — Semaine 11 (19-23 mai)
**Projection 2030 V0 + Lien conformité→conso**

| | |
|---|---|
| **Objectif** | Début H3 — narratif long terme + différenciation cockpit |
| **Livrables** | **Projection** : service `projection_trajectory.py` (conso actuelle, objectif -40% 2030 / -60% 2050, courbe linéaire), endpoint GET, sparkline chart dans obligation DT. **Lien conso** : dans chaque obligation DT, lien "Voir la consommation" → /consommations?site=X, widget résumé kWh/m²/an dans la carte obligation |
| **Owner** | Lead dev (fullstack) |
| **Dépendances** | Benchmark (Sprint 7-8) pour la référence |
| **Risque** | Projection linéaire trop simpliste → documenter hypothèses, suffisant pour V0 |
| **Preuve vendredi** | Sparkline trajectoire 2030 visible. Lien conso fonctionnel. |

---

### SPRINT 12 — Semaine 12 (26-30 mai)
**Préparation démos prospects + APER quick win + rétrospective**

| | |
|---|---|
| **Objectif** | Prêt pour les premières démos prospects réelles |
| **Livrables** | Script démo affiné (parcours 15 min avec coffre + PDF + notif + benchmark + projection + lien conso), APER enrichi quick win (calcul kWc estimé, coût, ROI — si temps disponible), guide de démo interne (points clés par écran, objections anticipées, kill shots), rétrospective 90 jours : ce qui a marché, ce qui a coincé, décisions pour H4 |
| **Owner** | Lead dev + Product |
| **Dépendances** | Tous sprints précédents |
| **Risque** | Retard accumulé → APER et guide de démo sont optionnels |
| **Preuve vendredi** | 1 démo interne filmée. Grille de feedback prospect prête. |

**>>> GATE G3 — Vérification fin S12+ (démos réelles à suivre) <<<**

---

## 7. TABLEAU RÉCAPITULATIF 12 SEMAINES

| Sem. | Dates | Pari | Objectif | Livrable clé | Preuve |
|------|-------|------|----------|-------------|--------|
| S1 | 11-14 mars | Coffre | Backend API proofs | POST/GET/DELETE proofs | curl upload+retrieve |
| S2 | 17-21 mars | Coffre | Frontend upload | ProofUpload + API integration | Upload → F5 → toujours là |
| S3 | 24-28 mars | Coffre+PDF | Polish coffre + spike PDF | Hash SHA-256, seed preuves, choix tech PDF | Seed preuves visibles |
| S4 | 31 mars-4 avr | PDF | Template + engine backend | pdf_generator.py + endpoint | PDF téléchargeable |
| S5 | 7-11 avril | PDF+Notif | Bouton PDF + modèle notif | Download PDF + modèle Notification | Clic → PDF |
| S6 | 14-18 avril | Notif | Engine + UI cloche | notification_engine + cloche AppShell | **GATE G1** |
| S7 | 21-25 avril | Notif+Bench | Email digest + données bench | email_digest + seed BenchmarkRef | Preview email + 30 entrées |
| S8 | 28 avr-2 mai | Bench | API + widget frontend | Widget "vs médiane" | Barre benchmark visible |
| S9 | 5-9 mai | Intégration | Tout ensemble | Parcours démo complet | Screencast démo |
| S10 | 12-16 mai | Stabilisation | Tests + polish | CI 100% green | **GATE G2** |
| S11 | 19-23 mai | Projection | Trajectoire 2030 + lien conso | Sparkline + widget conso | Projection visible |
| S12 | 26-30 mai | Démo ready | Script démo + APER QW + rétro | Guide démo + rétrospective | **GATE G3 prep** |

---

## 8. 3 KPIs OBSESSIONNELS

### KPI 1 — Preuves déposées par obligation

| | |
|---|---|
| **Définition** | Nombre de fichiers preuves persistés (ProofFile) rapporté au nombre total d'obligations actives |
| **Formule** | `COUNT(proof_files WHERE deleted_at IS NULL) / COUNT(obligations WHERE statut != 'hors_perimetre')` |
| **Pourquoi critique** | C'est le signal #1 que le coffre a de la valeur. Si personne ne dépose, le moat n'existe pas. Chaque preuve déposée = 1 raison de ne pas quitter PROMEOS. |
| **Cible 30 jours** | ≥ 0.5 (au moins 1 preuve pour 2 obligations) — mesuré sur le seed démo |
| **Cible 90 jours** | ≥ 1.0 (au moins 1 preuve par obligation active) — mesuré sur démo + premiers prospects |
| **Risque mauvaise lecture** | Compter les preuves seed comme des "vraies" preuves. Ne mesurer que les preuves uploadées manuellement chez les prospects réels. Le seed sert à la démo, pas au KPI. |

### KPI 2 — Dossiers PDF générés

| | |
|---|---|
| **Définition** | Nombre de PDF dossier comité générés (endpoint appelé avec succès) |
| **Formule** | `COUNT(pdf_generation_logs WHERE status = 'success')` |
| **Pourquoi critique** | Le PDF est le livrable monétisable. Si personne ne génère de PDF, c'est que le contenu ne convainc pas ou que le bouton n'est pas trouvé. Chaque PDF généré = 1 preuve que PROMEOS a de la valeur pour un comité. |
| **Cible 30 jours** | ≥ 3 (tests internes + démo) |
| **Cible 90 jours** | ≥ 10 (démos prospects + usage interne) |
| **Risque mauvaise lecture** | Compter les PDF générés par les développeurs en test. Distinguer "PDF généré en démo" vs "PDF généré par un utilisateur réel". Tracker le user_id. |

### KPI 3 — Actions créées depuis conformité

| | |
|---|---|
| **Définition** | Nombre d'ActionItems dont la source est une obligation ou un finding de conformité |
| **Formule** | `COUNT(action_items WHERE source_type = 'COMPLIANCE' AND created_at > date_debut)` |
| **Pourquoi critique** | C'est le signal que la boucle fonctionne : diagnostic → action. Si les findings ne génèrent pas d'actions, PROMEOS montre des problèmes mais ne fait pas agir. La chaîne Finding → Action → Preuve est le coeur du wedge. |
| **Cible 30 jours** | ≥ 5 (seed démo enrichi) |
| **Cible 90 jours** | ≥ 20 (seed + actions créées manuellement en démo) |
| **Risque mauvaise lecture** | Compter les actions seed comme des "vraies" actions. Ne compter en KPI réel que les actions créées par un utilisateur humain (pas le seed). Le seed sert à démontrer le flux. |

---

## 9. TOP 5 ACTIONS — CETTE SEMAINE

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| 1 | **Créer le modèle ProofFile + migration** : SQLAlchemy model, relation Obligation, migration Alembic/auto | 1j | Lead dev | Mercredi 12 mars |
| 2 | **Implémenter API REST proofs** : POST multipart upload, GET list par obligation, GET download fichier, DELETE avec soft-delete | 1.5j | Lead dev | Jeudi 13 mars |
| 3 | **Écrire les tests backend proofs** : test upload, test retrieve, test delete, test hash, test taille max, test type invalide | 0.5j | Lead dev | Vendredi 14 mars |
| 4 | **Préparer le spike PDF** : tester WeasyPrint install, tester Playwright page.pdf(), documenter le choix dans ADR | 0.5j | Lead dev | Vendredi 14 mars |
| 5 | **Mettre à jour le seed démo** : gen_compliance doit créer des ProofFile réalistes pour la démo (au lieu du useState seed actuel) | 0.5j | Lead dev | Vendredi 14 mars si temps, sinon S2 |

---

## 10. CE QU'ON NE FAIT PAS (EXPLICITEMENT)

| Initiative | Quand | Pourquoi pas maintenant |
|-----------|-------|------------------------|
| APER enrichi (calcul kWc) | Quick win S12 ou H2 | Pas de lien avec coffre/PDF/notif, pas de demande prospect |
| Projection 2030 complète | S11 (début) | Nécessite benchmark d'abord |
| Simulation "si j'agis" | H3 (mois 4-5) | Nécessite benchmark + projection + shadow billing intégré |
| Workflow multi-acteurs | H3-H4 | Aucun client n'a 2 rôles actifs |
| Connecteur OPERAT auto | H3 | API OPERAT pas encore dispo, CSV suffisant |
| Multi-tenant SaaS | H4 (mois 6+) | Pas avant 5 prospects qualifiés |
| API publique | H4 | Pas avant 1 intégrateur identifié |
| Veille réglementaire | H3 | Les échéances connues suffisent pour 90 jours |

---

## 11. SIGNAUX D'ALERTE

| Signal | Action immédiate |
|--------|-----------------|
| Sprint en retard de > 2 jours | Couper le scope du sprint, reporter le nice-to-have |
| Gate G1 non atteinte fin S6 | STOP — ne pas commencer benchmark. Stabiliser coffre + PDF. |
| 0 preuve déposée après S4 | Revoir l'UX upload — le composant n'est pas trouvable ou pas intuitif |
| PDF jamais téléchargé en démo | Revoir le contenu — le PDF ne convainc pas le DG |
| Notifications ignorées (0 clic) | Revoir le contenu/fréquence — trop de bruit ou pas assez de valeur |
| Benchmark pas crédible en démo | Documenter les sources ADEME + ajouter disclaimer "données publiques" |

---

> **Ce plan n'est pas une roadmap.**
> **C'est un plan de bataille.**
> **4 paris. 12 semaines. 3 KPIs. Pas de bruit.**
>
> *La seule question chaque vendredi : "Est-ce que la preuve de fin de semaine est livrée ?"*
