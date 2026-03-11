# AUDIT TOTAL PROMEOS — 10 Mars 2026

**Quatuor d'experts** : Lead Product Auditor / UX-UI Principal / Functional QA / Senior Architect

---

## 1. Executive Summary

**Note globale : 62/100**

**Verdict** : PROMEOS est un produit ambitieux, fonctionnellement riche, avec une couverture metier impressionnante pour un cockpit B2B energie France. Mais il reste trop visiblement un POC enrichi pour convaincre un prospect exigeant, un DG, ou un investisseur sans preparation.

**Niveau de maturite reel** : Beta avancee / POC++

**Potentiel apres correction** : 78-82/100 (atteignable en 2-3 sprints cibles)

### 5 risques les plus graves
1. Page Status expose "PROMEOS POC | FastAPI + React + SQLite | 427 tests"
2. 266 actions / 1M EUR pour 5 sites — volumes de seed absurdes
3. Page OPERAT montre "DPE loi check", "DPE sans email", "Test EJE VR3"
4. Activation "5/5 briques actives" + banner "Donnees incompletes"
5. Onboarding 0/6 apres seed complet

### 5 forces reelles
1. Cockpit executif (Vue executive) — structure hierarchique claire, briefing contextualise
2. Explorateur de consommation — graphiques lisibles, KPI bar solide, filtres fonctionnels
3. Achat energie + Scenarios — meilleur module : simulation credible, 3 strategies, recommandation
4. Usages horaires (Heatmap 7x24) — visuel expert impressionnant
5. ScopeSwitcher + Breadcrumbs — navigation multi-scope propre

---

## 2. Note detaillee par dimension

| Dimension | Note /10 | Commentaire |
|-----------|----------|-------------|
| UX | 6.5 | Navigation structuree mais trop de pages, parcours confus Actions/Notifications/Diagnostic |
| UI | 7.0 | Design system Tailwind coherent, densite inegale (Cockpit surcharge vs pages vides) |
| Navigation | 6.0 | 12 pages cachees via Ctrl+K/URL, doublons Cockpit/Command Center/Dashboard |
| Scope / Gouvernance | 7.0 | ScopeSwitcher bien fait, scope non rappele sur certaines pages |
| KPI / Calcul | 5.5 | 266 actions pour 5 sites = absurde, risque financier 0 EUR vs cockpit |
| Facturation / Achat | 7.5 | Bill Intel riche, Achat excellent, seed trop agressif |
| Workflow / Actionability | 6.0 | "Creer une action" partout mais manque de guidage |
| Demo credibility | 4.5 | "PROMEOS POC" footer, noms test, volumes irrealistes, onboarding casse |
| Architecture visible | 5.0 | Status page technique exposee, "97 endpoints | 9 pages" |
| Wording / Microcopy | 6.5 | Bon effort FR, incoh. "Donnees incompletes"/"5/5 actives" |
| Responsive / Densite | 6.0 | Cockpit tres dense, pages Admin tres vides |
| Product Story | 7.0 | Promesse claire, execution diluee par trop de modules |

---

## 3. Top problemes critiques

| ID | Probleme | Zone | Pourquoi c'est grave | P | Effort | Type |
|----|----------|------|---------------------|---|--------|------|
| C1 | Footer Status "PROMEOS POC \| FastAPI + React + SQLite \| 427 tests" | Status | Prospect voit POC SQLite = 0 credibilite | P0 | XS | Technique visible |
| C2 | 266 actions / 1,047,422 EUR pour 5 sites | Actions | Irrealiste. Energy manager sait que 5 sites != 266 actions | P0 | S | Data / Demo |
| C3 | "DPE loi check", "DPE sans email", "Test EJE VR3" OPERAT | Tertiaire | Donnees de test visibles = amateur | P0 | S | Data / Demo |
| C4 | Activation "5/5 briques actives" + "Donnees incompletes" | Activation | Message contradictoire | P0 | S | UX / Logique |
| C5 | Onboarding 0/6 apres seed complet | Onboarding | Premier contact = "rien n'est fait" | P0 | M | Workflow |
| C6 | 3 pages cockpit/dashboard concurrentes | Navigation | Confusion, chiffres potentiellement differents | P1 | M | Navigation |
| C7 | Bill Intel : ~60 factures toutes en anomalie | Facturation | Si tout est anomalie, rien n'est anomalie | P1 | S | Data / Credibilite |
| C8 | Energy Copilot vide (0 propositions) | Copilot | Page visible, completement vide | P1 | S | Demo |
| C9 | Memobox : "0 items" / "457 items ingeres" contradictoire | KB | Compteurs incoherents | P1 | XS | Wording |
| C10 | Expert toggle Ctrl+K = no-op | Search | Feature annoncee non fonctionnelle | P1 | XS | Technique |
| C11 | Command Center "Risque 0 EUR" vs Cockpit non-zero | Dashboard | Chiffres contradictoires entre pages | P1 | S | KPI |
| C12 | Renouvellements : 2/5 sites ont des contrats | Achat | Patrimoine contrats incomplet | P2 | M | Data |
| C13 | Connectors : "stub" visible dans descriptions | Connectors | Technique visible | P2 | XS | Technique visible |
| C14 | Performance badge "10" sans explication | Sidebar | Badge sans contexte | P2 | XS | UX |
| C15 | Conformite 59/100 vs "0% conforme global" | Conformite | Scores incoherents | P2 | S | KPI |

---

## 4. Audit detaille par zone

### Cockpit (Vue executive)
- **Fonctionne** : Hierarchie claire, briefing, scores composites avec confiance
- **Faible** : Page tres longue (scroll infini), synthese KPI arrive tard
- **Trompeur** : "4 sites"/"100%"/"0 alertes" mini-KPI bas vs "9 alertes" plus haut
- **Prospect** : Densite — scrollera 3 ecrans, perdra le fil

### Patrimoine (Sites & Batiments)
- **Fonctionne** : Carte MapLibre interactive, heatmap, drawer site detaille
- **Faible** : Drawer montre "Risque: —", "OPERAT: —", "Anomalies: 0"
- **Manque** : Photo batiment, spark graph conso dans drawer

### Consommations (Explorateur)
- **Fonctionne** : Excellente page. KPI bar (522 MWh, 83k EUR, CO2). Graphique clair.
- **Force** : Fait "produit mature". Point fort demo.

### Consommations (Portefeuille)
- **Fonctionne** : Vue multi-sites avec totaux, classement par impact
- **Faible** : Colonnes "Derniere detection"/"Derniere anomalie" peu claires

### Facturation (Bill Intel)
- **Fonctionne** : Structure riche, drawer detaille, timeline mensuelle
- **Grave** : ~60 factures quasi-toutes en anomalie rouge/orange = "tout rouge"
- **Prospect** : "Si tout est anomalie, votre moteur est mal calibre"

### Achat energie
- **MEILLEUR MODULE** : 3 scenarios (Prix Fixe/Indexe/Spot), scoring 15/100, reco "Prix Fixe", "Recommande", "Accepte". CTA "Creer action" + "Exporter Note Decision.pdf"
- **Faible** : Hypotheses pas assez mises en avant

### Actions & Suivi
- **Fonctionne** : Table structuree, filtres statut/type/priorite
- **Grave** : 266 actions / 1M EUR pour 5 sites = irrealiste

### Conformite
- **Fonctionne** : Score 59/100, barre visuelle, piliers reglementaires
- **Incoherent** : 59 vs "0% conforme global". "1 non-conformite" vs "4 a qualifier"
- **Casse (OPERAT)** : Noms "DPE loi check", "Test EJE VR3" = test data

### Notifications/Alertes
- **Fonctionne** : Table propre, badges type/statut, KPI header
- **Faible** : Trop d'alertes (~25) pour 5 sites

### Admin (Utilisateurs)
- **Fonctionne** : Propre, clair
- **Faible** : 1 seul utilisateur. Montrer 3-4 users serait plus credible

### Onboarding (Demarrage)
- **Casse** : 0/6 apres seed. Auto-detection ne detecte rien. Premier contact rate.

### Status (Systeme)
- **CRITIQUE** : "PROMEOS POC | FastAPI + React + SQLite | 427 tests | 97 endpoints | 9 pages"
- "Endpoints API: -" = valeur manquante visible

### Command Palette (Ctrl+K)
- **Fonctionne** : Rapide, groupe par section, raccourcis clavier
- **Faible** : Expert toggle = no-op. Pages cachees accessibles

### Drawers / Modals
- **Fonctionne** : Drawer patrimoine propre, onglets Resume/Anomalies/Compteurs/Actions
- **Faible** : Beaucoup de "—" sans message fallback

---

## 5. Contradictions & pertes de confiance

| Type | Detail |
|------|--------|
| Chiffres contradictoires | Command Center "Risque 0 EUR" vs Cockpit non-zero. Conformite 59 vs "0% conforme" |
| Messages contradictoires | Activation "5/5 actives" + "Donnees incompletes" |
| Pages doublons | Cockpit / Dashboard 2min / Command Center |
| Labels instables | "Actions & Suivi" sidebar vs "Plan d'actions" header |
| Fallbacks visibles | "—" partout, Status "Endpoints API: -" |
| Seed data visible | "DPE loi check", "Test EJE VR3", "DPE sans email" |
| Debug/technique | "PROMEOS POC", "FastAPI + React + SQLite", "(stub)" |
| Calculs opaques | Score conformite 59/100 methode ?, Score comportement 99 quoi ? |
| Volumes absurdes | 266 actions, 60+ factures anomalie, 25 alertes pour 5 sites |

---

## 6. Audit customer journey

### Scenario 1 — Prospect / demo
- Cockpit : bon premier impact, briefing clair
- Scroll : perd le fil (trop long)
- Patrimoine : carte MapLibre impressionne
- Facturation : choc tout rouge
- Achat : excellent
- Verdict : "Prometteur mais trop de bruit"

### Scenario 2 — DG multi-sites
- ScopeSwitcher OK
- 266 actions, 1M EUR : "C'est quoi ces chiffres ?"
- Pas de page "Synthese decisionnelle" unique

### Scenario 3 — Energy manager
- Cherche site : Ctrl+K ou Patrimoine OK
- Diagnostic et Performance bons
- CTA action existe
- Scope rappele par ScopeSwitcher (pas toutes pages)

### Scenario 4 — Expert
- Mode Expert toggle fonctionne dans header
- Heatmap 7x24 impressionnante
- Expert toggle via Ctrl+K = no-op

### Scenario 5 — Admin
- 1 seul user = peu credible
- Permissions non visibles
- Status "PROMEOS POC | SQLite" = perte confiance

---

## 7. Audit chiffres / KPI

| Question | Reponse |
|----------|---------|
| Fiables ? | Conso MWh, EUR, CO2 dans l'explorateur |
| Opaques ? | Score conformite 59, Score comportement 99, Confiance badge |
| Contradictoires ? | Risque 0 EUR (Command Center) vs non-zero (Cockpit). 0% conforme vs 59 |
| Mal visibles ? | Petits chiffres Cockpit section basse |
| Sans contexte ? | 1.7M kWh/an sans benchmark secteur, 15/100 achat sans echelle |
| Suspects ? | 266 actions/5 sites, 60+ factures anomalie |

---

## 8. Audit demo / quasi-prod

### Fait encore POC
- "PROMEOS POC" footer, "FastAPI + React + SQLite"
- "(stub)" connecteurs
- Noms test OPERAT
- 0/6 onboarding apres seed
- 1 seul utilisateur
- Volumes absurdes
- "Endpoints API: -"

### Fait produit mature
- Explorateur consommation
- Module Achat + Scenarios
- Usages horaires Heatmap
- ScopeSwitcher
- Carte MapLibre patrimoine
- Timeline facturation

---

## 9. Recommandations

### P0 — Avant toute demo

| Action | Impact | Effort |
|--------|--------|--------|
| Footer Status "PROMEOS v1.0" | Credibilite | XS |
| Seed OPERAT noms realistes | Credibilite | S |
| Seed volumes 30-40 actions, 30% anomalies max | Credibilite | S |
| Activation banner coherent | Confiance | S |
| Onboarding auto-detect fonctionnel | Premier contact | M |

### P1 — Sprint suivant

| Action | Impact | Effort |
|--------|--------|--------|
| Masquer Command Center/Dashboard 2min | Navigation | M |
| Retirer "(stub)" connecteurs | Credibilite | XS |
| Fixer Expert toggle Command Palette | Fonctionnel | XS |
| Reduire alertes 8-10 pour 5 sites | Credibilite | S |
| Seed 3 users fictifs | Credibilite | S |
| Fixer "Endpoints API: -" Status | Qualite | XS |
| Energy Copilot seeder ou masquer | Credibilite | S |
| Memobox aligner compteurs | Coherence | XS |

### P2 — Ensuite

| Action | Impact | Effort |
|--------|--------|--------|
| Cockpit sections collapsibles | UX densite | M |
| Contrats pour tous sites | Couverture | M |
| Tooltips explication scores | Transparence | M |
| Remplacer "—" par "Non evalue" | Micro-UX | S |

---

## 10. Plan priorite

| # | Action | Impact | Effort | Pourquoi maintenant |
|---|--------|--------|--------|-------------------|
| 1 | Footer Status : "PROMEOS v1.0" | Critique | 10 min | 1 ligne, elimine le kill shot |
| 2 | Seed OPERAT noms realistes | Critique | 1h | Visible en 2 clics |
| 3 | Seed volumes 30-40 actions, 30% anomalies | Critique | 2h | Chiffres absurdes = perte prospect |
| 4 | Activation banner coherent | Majeur | 1h | Contradiction visible |
| 5 | Onboarding auto-detect | Majeur | 2h | Premier contact |
| 6 | Masquer Command Center / Dashboard 2min | Clarte | 30min | 3 dashboards = confusion |
| 7 | Retirer "(stub)" connecteurs | Credibilite | 10min | Texte technique visible |
| 8 | Energy Copilot seeder ou masquer | Credibilite | 1h | Page vide |
| 9 | Seed 3 users fictifs | Credibilite | 1h | 1 user = suspect |
| 10 | Seed contrats tous sites | Couverture | 2h | Renouvellements vide |

---

## 11. Verdict final

**PROMEOS est-il credible aujourd'hui ?** Non, pas en l'etat. Architecture credible, modules forts (Achat, Conso, Usages horaires), mais les fuites POC detruisent l'effet produit fini en 5 minutes.

**Ce qui empeche "top world"** : Trop de bruit, seed sans storytelling, pas de "moment wow" guide.

**Corriger AVANT toute feature** : Footer Status, seed quality, onboarding, pages doublons.

**Geler (deja bon)** : Explorateur conso, Achat, Usages horaires, ScopeSwitcher, MapLibre, Timeline.

**Ce qui fait peur en demo** : Status "PROMEOS POC | SQLite", 266 actions/5 sites, "Test EJE VR3", tout en anomalie Bill Intel, onboarding 0/6.

**Temps pour passer de 62 a 78/100** : ~12h de travail concentre sur les 10 actions du plan.
