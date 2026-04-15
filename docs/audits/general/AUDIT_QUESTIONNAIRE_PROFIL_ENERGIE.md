# AUDIT + REFONTE — Questionnaire "Affinez votre profil énergie"

**Date** : 2026-03-14
**Auteur** : CPO / Energy Lead PROMEOS
**Statut** : Audit + Proposition V1.3

---

## 1. RÉSUMÉ EXÉCUTIF

Le questionnaire actuel existe, fonctionne, mais **ne sert quasiment à rien**. Les réponses sont stockées en base mais n'impactent ni le moteur usages, ni la conformité, ni l'achat, ni les recommandations de manière visible. C'est un formulaire déclaratif sans conséquence produit. En l'état, il risque de décevoir l'utilisateur ("j'ai répondu, et alors ?"). La V1.3 doit transformer ce questionnaire en **levier de personnalisation réel** : chaque réponse doit déclencher un effet visible (activation de module, ajustement de benchmark, priorisation de recommandation, filtrage de réglementation applicable).

---

## 2. FAITS

- Le questionnaire est défini dans `backend/services/segmentation_service.py` (7 questions)
- Le composant frontend est `SegmentationQuestionnaireModal.jsx` — affiche max 4 questions
- Les questions prioritaires filtrées sont : `q_operat`, `q_bacs`, `q_horaires`
- Les réponses sont stockées dans `SegmentationAnswer` (modèle SQLAlchemy)
- La page `SegmentationPage.jsx` affiche le profil résultant
- Les recommandations sont **uniquement par typologie** (tertiaire privé, industrie, etc.) — PAS par réponse individuelle
- **Aucun module ne lit les réponses** pour adapter son comportement (usages, conformité, achat)
- Les questions affichées en modal ne sont que 4 sur 7 (rotation par questions non répondues)
- L'API backend retourne les 7 questions ; le frontend en montre 4

---

## 3. HYPOTHÈSES

- Le questionnaire a été conçu comme un "nice-to-have" de segmentation commerciale, pas comme un levier produit
- L'intention était probablement d'adapter les recommandations par segment, mais le lien n'est que typologie → recommandation, pas réponse → action
- L'utilisateur ne voit pas l'effet de ses réponses → frustration ou abandon
- Les questions Q3 (chauffage) et Q4 (IRVE) sont utiles mais déconnectées des briques

---

## 4. DÉCISIONS

### Ce qui est bon
- UX du modal : simple, claire, skippable, format bouton-pill
- Questions pertinentes métier (GTB, BACS, OPERAT, CEE, chauffage, IRVE, horaires)
- Backend solide (questions + réponses + profil + confiance)
- Priorité sur q_operat, q_bacs, q_horaires = correct pour le tertiaire

### Ce qui est faible — UX
1. **Pas de feedback immédiat** — après validation, rien ne change visiblement
2. **"Affinez votre profil énergie"** — titre vague, ne dit pas pourquoi c'est utile
3. **Sous-titre "Répondez pour améliorer la précision"** — trop générique
4. **Pas de barre de progression** — déjà partiellement résolu (X/4 réponses)
5. **"Plus tard"** — ok, mais pas de relance programmée

### Ce qui est faible — Logique métier
1. **Réponses stockées mais pas exploitées** — zéro impact visible
2. **q_operat** (OPERAT) est demandé à tous — mais seuls les bâtiments tertiaire > 1000 m² sont concernés
3. **q_bacs** — pertinent mais le moteur BACS ne lit pas cette réponse
4. **q_cee** — "Oui" ne déclenche rien, "Non" non plus
5. **q_chauffage** — devrait impacter les benchmarks IPE mais ne le fait pas
6. **q_irve** — devrait activer le module flex/IRVE mais ne le fait pas

### Ce qui est faible — Conformité / Énergie
1. Le questionnaire ne filtre PAS les réglementations applicables à l'utilisateur
2. Un hôpital voit les mêmes questions qu'un bureau → incohérent
3. Pas de question sur la **puissance souscrite** (seuil BACS = 290 kW)
4. Pas de question sur le **type d'ERP** ou **surface > 1000 m²** (seuil Décret Tertiaire)
5. Pas de lien avec le patrimoine déjà renseigné (surface, type de site, vecteur énergie)

---

## 5. MINI AUDIT SÉVÈRE

| Critère | Note | Commentaire |
|---------|------|-------------|
| UX modal | 7/10 | Propre, skippable, mais sans feedback |
| Pertinence questions | 6/10 | Bonnes questions mais pas ciblées par profil |
| Impact usages | 1/10 | Zéro exploitation par le moteur usages |
| Impact conformité | 1/10 | Le moteur conformité ne lit pas les réponses |
| Impact recommandations | 3/10 | Seule la typologie impacte, pas les réponses individuelles |
| Impact achat | 0/10 | Aucun lien |
| Impact flex/IRVE | 0/10 | Aucun lien |
| Cohérence patrimoine | 2/10 | Pas de pré-remplissage depuis les données existantes |

**Verdict : 2.5/10 — Formulaire fantôme. Stocke des données, ne produit aucun effet.**

---

## 6. PROPOSITION V1.3 — NOUVELLE LOGIQUE PRODUIT

### A. Rôle exact dans PROMEOS

Le questionnaire doit être le **pont entre le déclaratif et le moteur** :
- Il capture ce que les données ne disent pas encore (intentions, équipements, obligations connues)
- Chaque réponse doit **activer, désactiver, ou paramétrer** un module
- L'utilisateur doit voir l'effet de sa réponse dans les 5 secondes (badge, score, recommandation)

### B. Quand il apparaît

1. **Onboarding** : après import du premier fichier (pas avant — l'utilisateur doit d'abord voir de la valeur)
2. **Patrimoine** : bouton "Compléter mon profil" dans la fiche site
3. **Cockpit** : relance si profil incomplet (card "Affinez votre profil" dans la watchlist)
4. **Jamais bloquant** — toujours skippable, relançable, versionnable

### C. Version améliorée — 6 questions

| # | ID | Question | Options | Ajouté/Modifié/Conservé | Pourquoi |
|---|-----|---------|---------|-------------------------|----------|
| 1 | q_typologie | Quel est votre secteur principal ? | Tertiaire privé / Collectivité / Industrie / Santé / Commerce / Copropriété | **Modifié** (était implicite via NAF) | Filtre toutes les réglementations applicables |
| 2 | q_surface_seuil | Vos bâtiments dépassent-ils 1 000 m² ? | Oui, tous / Oui, certains / Non / Je ne sais pas | **Ajouté** | Seuil Décret Tertiaire — filtre la conformité affichée |
| 3 | q_gtb | Disposez-vous d'une GTB ? | Oui, centralisée / Oui, partielle / Non / Je ne sais pas | **Conservé** | Impact BACS + source de données usages |
| 4 | q_chauffage | Mode de chauffage principal ? | Gaz naturel / Électrique (PAC) / Réseau chaleur / Mixte | **Conservé** | Impact benchmarks IPE + recommandations |
| 5 | q_cee | Avez-vous bénéficié de CEE ? | Oui / Non / Je ne sais pas | **Conservé** | Active recommandations CEE |
| 6 | q_irve | Bornes de recharge IRVE ? | Oui / En projet / Non | **Conservé** | Active module flex/IRVE |

**Retirés** :
- `q_operat` → peut être **déduit** du patrimoine (surface > 1000 m² + tertiaire = concerné)
- `q_bacs` → peut être **déduit** (puissance > 290 kW + tertiaire = concerné)
- `q_horaires` → reste disponible mais en **question secondaire** (pas dans le modal initial)

### D. Table de règles métier

| Question | Réponse | Impact produit | Impact métier | Modules impactés |
|----------|---------|---------------|---------------|-----------------|
| q_typologie = tertiaire_prive | → | Active Décret Tertiaire + BACS + OPERAT | Obligations réglementaires filtrées | Conformité, Cockpit KPI "Conformité" |
| q_typologie = industrie | → | Active ISO 50001 + audit 4 ans | Désactive DT si < 1000 m² | Conformité, Actions |
| q_typologie = collectivite | → | Active DT + schéma directeur | Priorise OPERAT | Conformité, Patrimoine |
| q_surface_seuil = oui | → | Confirme DT applicable | Seuil 1000 m² validé | Conformité, KPI Risque |
| q_surface_seuil = non | → | Désactive DT (pas concerné) | Allège le cockpit conformité | Cockpit, Conformité |
| q_gtb = oui_centralisee | → | Score BACS +20 pts, source "GTB" dispo pour usages | Upsell : connecteur GTB | Usages (data_source), BACS, Achat |
| q_gtb = non | → | Recommandation "Installer une GTB" high priority | Opportunity sizing | Actions, Recommandations |
| q_chauffage = gaz | → | Benchmark IPE chauffage ajusté (150-250 kWh/m²/an) | Risque prix gaz visible | Usages (IPE), Achat (contrat gaz) |
| q_chauffage = electrique | → | Benchmark IPE ajusté (50-120 kWh/m²/an) | Flex possible (effacement) | Usages, Flex |
| q_chauffage = reseau_chaleur | → | Pas de flex, IPE bas attendu | Peu de levier achat | Usages |
| q_cee = oui | → | Badge "CEE mobilisés" sur le profil | Valorisation acquise | Actions, Patrimoine |
| q_cee = non | → | Recommandation "Explorer les CEE" | Potentiel €€ | Recommandations, Achat |
| q_irve = oui | → | Active module IRVE/flex dans usages | Upsell : pilotage IRVE | Usages, Flex, Achat |
| q_irve = en_projet | → | Recommandation "Anticiper l'impact IRVE" | Sizing puissance | Actions, Achat |

### E. UX / Microcopy finale

**Titre modal** : "Personnalisez votre cockpit énergie"

**Sous-titre** : "6 questions rapides pour adapter PROMEOS à votre situation réelle."

**Questions** :

1. "Quel est le secteur principal de votre parc immobilier ?"
   - Tertiaire privé (bureaux, commerces)
   - Collectivité (bâtiments publics)
   - Industrie / logistique
   - Santé / médico-social
   - Copropriété / bailleur
   - Autre

2. "Vos bâtiments dépassent-ils 1 000 m² de surface ?"
   - Oui, la majorité
   - Oui, certains seulement
   - Non
   - Je ne suis pas sûr

3. "Disposez-vous d'une GTB (Gestion Technique du Bâtiment) ?"
   - Oui, centralisée
   - Oui, sur certains sites
   - Non
   - Je ne sais pas

4. "Quel est le mode de chauffage principal ?"
   - Gaz naturel
   - Électrique (PAC, convecteurs)
   - Réseau de chaleur urbain
   - Mixte / autre

5. "Avez-vous déjà bénéficié de CEE (Certificats d'Économie d'Énergie) ?"
   - Oui
   - Non
   - Je ne sais pas

6. "Disposez-vous de bornes de recharge électrique (IRVE) ?"
   - Oui, installées
   - En projet
   - Non

**Bouton secondaire** : "Plus tard"
**Bouton principal** : "Valider mon profil"
**Message confirmation** : "Profil mis à jour. Vos recommandations et obligations sont maintenant adaptées à votre situation."

### F. Hiérarchie des signaux (priorité d'impact)

1. **q_typologie** (critique) — filtre TOUT le reste (réglementations, benchmarks, recommandations)
2. **q_surface_seuil** (critique) — détermine si Décret Tertiaire s'applique ou non
3. **q_gtb** (fort) — impacte BACS + qualité des données usages + upsell
4. **q_chauffage** (fort) — impacte IPE + benchmarks + contrat énergie
5. **q_irve** (moyen) — active/désactive module flex
6. **q_cee** (moyen) — active/désactive recommandations CEE

### G. Quick Wins

**V1.3 immédiat** (cette semaine) :
1. Renommer le titre + sous-titre du modal
2. Ajouter `q_surface_seuil` (1 question, 0 impact backend lourd)
3. Afficher un message de confirmation visible après validation
4. Pré-remplir `q_typologie` depuis le patrimoine si disponible (NAF, type_site)
5. Filtrer les KPI cockpit conformité selon q_typologie (ne pas afficher DT à un industriel < 1000 m²)

**V1.4 ensuite** :
1. Connecter q_chauffage → benchmarks IPE dans `compute_baselines()`
2. Connecter q_gtb → data_source dans le plan de comptage
3. Connecter q_irve → module flex (endpoint + widget)
4. Ajouter relance cockpit si profil incomplet
5. Historiser les réponses (versioning pour audit trail)

### H. Risques / Erreurs à éviter

| Risque | Conséquence | Mitigation |
|--------|-------------|-----------|
| Questionnaire trop déclaratif | Réponses fausses, profil incorrect | Croiser avec données réelles (patrimoine, factures) |
| Réponses stockées mais inutiles | Utilisateur frustré ("j'ai répondu, et rien n'a changé") | Chaque réponse doit avoir un effet visible immédiat |
| Impact invisible | Pas de valeur perçue | Afficher "grâce à votre profil" sur les éléments personnalisés |
| Données non qualifiées | Faux positifs conformité | Distinguer "déclaré" vs "déduit" vs "confirmé" |
| Recommandations incohérentes | "Installez IRVE" alors que le site en a déjà | Vérifier les réponses IRVE avant de recommander |
| Sur-interrogation | 30 questions → abandon | Max 6 questions, skippable, relançable |

---

## 9. TOP 5 ACTIONS

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| 1 | Renommer titre/sous-titre modal + message confirmation | 0.5j | Front | S+1 |
| 2 | Ajouter q_surface_seuil + pré-remplir q_typologie depuis patrimoine | 1j | Back+Front | S+1 |
| 3 | Connecter q_typologie → filtrage KPI conformité cockpit | 1-2j | Back+Front | S+2 |
| 4 | Connecter q_chauffage → benchmarks IPE usages | 1j | Back | S+2 |
| 5 | Afficher "Profil mis à jour" + badge "Personnalisé" sur éléments adaptés | 0.5j | Front | S+2 |
