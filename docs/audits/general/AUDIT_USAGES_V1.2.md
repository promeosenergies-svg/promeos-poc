# CONTRE-AUDIT VISUEL V1.2 — Brique Usages Énergétiques

**Date** : 2026-03-13
**Auditeur** : Agent IA (Playwright headless + lecture visuelle)
**Périmètre** : Page `/usages` — 3 sites testés (Bureau Paris, Usine Toulouse, Hôtel Nice) + état vide
**Captures** : `artifacts/audits/captures/2026-03-13-18-52/V12-*.png`

---

## 1. SYNTHÈSE EXÉCUTIVE

| Métrique | Valeur |
|----------|--------|
| **Note globale** | **6.5 / 10** |
| **Verdict** | **GO AVEC RÉSERVES** |
| **Blocs fonctionnels** | 9 / 9 affichés |
| **Bugs bloquants** | 3 (coût %, IPE seed, doublons conformité) |
| **Crash découvert** | 1 (import ScopeContext → corrigé en live) |

**Ce que la brique sait faire maintenant** :
Afficher en une page les 9 blocs du parcours Usage : KPI header, Baseline & avant/après, UES/IPE, Plan de comptage, Dérives prioritaires, Impact conformité, Coût par usage, Impact facture & achat, Liens cross-briques. S'adapte au profil du site (bureau, usine, hôtel). État vide propre.

**Ce qui manque encore** :
Les données seed sont incohérentes (IPE à 1500 kWh/m²/an, coût > 100%, doublons conformité). Le lien sidebar est absent. L'export print n'est pas testable en headless.

**Phrase de synthèse** :
La brique Usage V1.2 passe de "fantôme" à "page réelle avec 9 blocs structurés". La crédibilité métier est là (baseline, IPE, conformité, facture). Les défauts restants sont des bugs de data — corrigeables en 1-2 jours.

---

## 2. FAITS — Confirmés visuellement

### A. Entrée /usages

| Aspect | Constat |
|--------|---------|
| **Visible** | Breadcrumb "PROMEOS > Usages", scope selector "Groupe HELIOS > Siege HELIOS Paris" |
| **Fonctionne** | Navigation OK, page accessible, breadcrumb cohérent |
| **Moyen** | Pas de lien "Usages" dans le sidebar gauche — l'utilisateur doit naviguer directement à `/usages` |
| **Crash corrigé** | Import `ScopeContext` inexistant → remplacé par `useScope()` |
| **Capture** | `V12-S1-02-viewport.png`, `V12-EMPTY-01.png` |

### B. Header / KPI

| Aspect | Constat |
|--------|---------|
| **Visible** | 6 KPIs en ligne : 1 823 186 kWh · 328 173 EUR · 100/100 Readiness · 3 sous-compteurs · 6 dérives · 29,2 c€/kWh |
| **Fonctionne** | Chiffres cohérents, badge "100/100 Prêt" en vert, bouton "Exporter / Imprimer" en haut à droite |
| **Bon** | Sous-titre "Usage > Dérives > Actions > Gain > Preuve > Conformité > Facture" — raconte l'histoire PROMEOS |
| **Moyen** | Readiness à 100/100 trop parfait pour un site de démo — réduit la crédibilité |
| **Capture** | `V12-S1-02-viewport.png` |

### C. Readiness

| Aspect | Constat |
|--------|---------|
| **Visible** | Badge "100/100 Prêt" intégré dans le header KPI, pas de bloc dédié |
| **Moyen** | Pas de détail visible des 4 dimensions (déclarés, couverture, qualité, profondeur). Un DG ne sait pas *pourquoi* c'est 100/100 |
| **Capture** | `V12-S1-02-viewport.png` |

### D. Plan de comptage

| Aspect | Constat |
|--------|---------|
| **Visible** | Arbre hiérarchique : Compteur principal → 3 sous-compteurs (CVC, Éclairage, IT) avec badges colorés par usage et "Mesuré" |
| **Fonctionne** | kWh par sous-compteur, % du total, "Écart négatif (anomalie)" signalé |
| **Bon** | Compteur gaz séparé visible (87 750 kWh) |
| **PROBLÈME** | Couverture sous-comptage à **240,8%** — aberrant. La somme des sous-compteurs dépasse le compteur principal. Signal d'erreur seed ou calcul |
| **Capture** | `V12-S1-04-scroll900.png` |

### E. UES / IPE

| Aspect | Constat |
|--------|---------|
| **Visible** | Tableau "Usages Énergétiques Significatifs (UES)" — 4 lignes avec kWh/an, Part %, IPE kWh/m²/an, Source, Dérive |
| **Fonctionne** | Footnote ISO 50001 visible, badges colorés UES |
| **PROBLÈME** | Les **IPE sont aberrants** : Chauffage IPE = ~1 519 kWh/m²/an (norme bureau : 100-200). Le seed injecte les kWh totaux du site au lieu de ventiler par pct_of_total |
| **Capture** | `V12-S1-02-viewport.png` |

### F. Baseline & Avant/Après

| Aspect | Constat |
|--------|---------|
| **Visible** | Tableau complet : Usage · Baseline kWh · Actuel kWh · Écart · IPE base · IPE actuel · Tendance · Source |
| **Fonctionne** | 4 usages avec baselines, tendances colorées (dégradation rouge, amélioration vert), badge "Mesuré" |
| **Bon** | Climatisation montre une amélioration (-1,4%) — crédible |
| **PROBLÈME** | kWh trop élevés (1 062 687 pour Chauffage baseline d'un bureau 3500 m²). Même cause que E : seed non ventilé |
| **Capture** | `V12-S1-02-viewport.png` |

### G. Impact conformité

| Aspect | Constat |
|--------|---------|
| **Visible** | Score BACS 52/100, Couverture BACS 0% (0/6 usages), tableau Usage/BACS/Décret Tertiaire/ISO 50001 |
| **Fonctionne** | "Manquant" orange, "Concerné" jaune, "UES" bleu — codes couleur lisibles |
| **Bon** | Encart orange "Principal risque : Usages thermiques sans couverture BACS" — actionnable |
| **Bon** | CTA "Voir la conformité détaillée →" présent |
| **PROBLÈME** | **Doublons** : Chauffage ×2, Climatisation ×2, Éclairage ×2, Ventilation ×2 (2 bâtiments × mêmes usages). Doit être dédupliqué par type |
| **Capture** | `V12-S1-05-scroll1800.png` |

### H. Coût par usage

| Aspect | Constat |
|--------|---------|
| **Visible** | Barres horizontales : IT & Bureautique 256 829 EUR (78,3%), Chauffage 251 450 EUR (76,6%), Éclairage 244 052 EUR (74,4%) |
| **PROBLÈME CRITIQUE** | **Les % dépassent 100 chacun.** 78% + 76% + 74% = 228%. Le calcul de ventilation pro-rata est cassé. Invendable en démo |
| **Capture** | `V12-S1-05-scroll1800.png` |

### I. Impact facture & achat

| Aspect | Constat |
|--------|---------|
| **Visible** | Prix référence 29,2 c€/kWh (badge "Facture"), alerte rouge "Aucun contrat actif", "Factures 12 mois : 137 802 EUR, 7 factures, 471 904 kWh" |
| **Fonctionne** | 3 CTA : "Voir les factures →", "Explorer le contrat →", "Scénarios d'achat →" |
| **Bon** | L'alerte contrat est pertinente et visuellement forte |
| **Capture** | `V12-S1-05-scroll1800.png` |

### J. Liens cross-briques

| Aspect | Constat |
|--------|---------|
| **Visible** | Barre de 5 boutons en bas : Diagnostic, Conformité, Factures, Actions, Patrimoine (avec icônes) |
| **Moyen** | Playwright ne détecte aucun `<a>` — probablement des `<button onClick>` ou `<div>`. Fonctionnels mais pas des liens HTML sémantiques |
| **Capture** | `V12-S1-06-scroll2700.png` |

### K. Export / Print

| Aspect | Constat |
|--------|---------|
| **Visible** | Bouton "Exporter / Imprimer" en haut à droite du header |
| **Non testé** | `window.print()` ne fonctionne pas en headless Playwright |
| **Capture** | `V12-S1-02-viewport.png` |

### L. Multi-sites

| Site | Profil | Résultat |
|------|--------|----------|
| Site 1 — Siege HELIOS Paris | Bureau | Page complète, 9 blocs, BACS 52/100 |
| Site 3 — Usine HELIOS Toulouse | Entrepôt | Page complète, Process/Ventilation, BACS 37/100 |
| Site 4 — Hôtel Helios Nice | Hôtel | Page complète, Cuisine & Buanderie/ECS, BACS 45/100 |

**Bon** : La page s'adapte au profil du site. Un hôtel montre ECS et Cuisine, une usine montre Process.
**Capture** : `V12-S4-01-fullpage.png`, `V12-S3-01-fullpage.png`

### M. État vide

| Aspect | Constat |
|--------|---------|
| **Visible** | "Sélectionnez un site pour afficher le tableau de bord des usages." |
| **Propre** | Pas de crash, pas de données fantômes. Message clair |
| **Capture** | `V12-EMPTY-01.png` |

---

## 3. HYPOTHÈSES — Fragilités restantes

### Encore trop V1
- Le **coût par usage** est cassé (% > 100) — invendable en démo ou en prod
- Les **IPE baseline** sont aberrants (1500 kWh/m²/an pour du chauffage bureau) — le seed injecte les kWh totaux du site, pas ventilés par pct_of_total de l'usage
- La **couverture sous-comptage à 240%** signale que la somme des sous-compteurs est fausse dans le seed
- Les **doublons conformité** (2x Chauffage, 2x Éclairage) montrent que la déduplication par type d'usage n'est pas faite

### Acceptable en démo mais pas en prod premium
- Readiness à 100/100 trop parfait — un site réel n'est jamais à 100
- Dérives toutes "MEDIUM" et identiques ("Consommation hors horaires") — pas de variété
- Lien "Usages" absent du sidebar (il faut naviguer directement à `/usages`)

### Ce qui pourrait gêner un DG
- Les chiffres de coût qui dépassent 100% détruisent la confiance
- Le IPE à 1500 kWh/m² est incompréhensible pour un non-expert
- Trop de lignes dupliquées dans la conformité

### Ce qui pourrait gêner un expert énergie
- Les données de baseline ne sont pas crédibles (kWh totaux site attribués à un seul usage)
- La couverture sous-comptage > 100% est un signal d'erreur
- Pas de benchmark sectoriel visible pour comparer les IPE

### Ce qui pourrait gêner un client multi-sites
- Pas de vue consolidée multi-sites (la page est site par site uniquement)
- Pas de comparaison inter-sites sur les usages

---

## 4. DÉCISIONS

### Statut global : **GO AVEC RÉSERVES**

### Prêt maintenant
- Structure de page (9 blocs, hiérarchie claire, histoire PROMEOS)
- Plan de comptage (arbre, badges, kWh)
- Conformité BACS/DT/ISO 50001 (tableau lisible, risque identifié)
- Impact facture & achat (prix ref, alerte contrat, CTA)
- Liens cross-briques (5 boutons, 3 CTA facture)
- Multi-sites (fonctionne sur 3 profils différents)
- État vide propre

### À corriger AVANT V1.3
1. **Coût par usage** : les % sont faux (dépassent 100%)
2. **IPE/Baseline seed** : ventiler le kWh annual par pct_of_total, pas le total brut
3. **Doublons conformité** : dédupliquer par type d'usage (pas par usage_id)
4. **Sidebar** : ajouter "Usages" dans le menu Énergie
5. **Couverture sous-comptage** : plafonner à 100% ou expliquer l'anomalie

### Peut attendre
- CTA en `<a>` au lieu de `<button>` (accessibilité)
- Variété des dérives (ajouter d'autres types dans le seed)
- Readiness trop parfait (ajuster le seed)
- Benchmark sectoriel dans les UES
- Vue consolidée multi-sites

---

## 5. TABLEAU FINAL

| Zone | Verdict | Grand public | Expert | Impact démo | Impact métier | Priorité |
|------|---------|-------------|--------|-------------|---------------|----------|
| A. Entrée /usages | OK | Clair | OK | Bon | Bon | — |
| B. Header / KPI | BON | 10s lisible | Complet | Fort | Fort | — |
| C. Readiness | MOYEN | Visible | Pas de détail | Moyen | Moyen | P2 |
| D. Plan comptage | BON | Arbre lisible | % couverture | Fort | Fort | P1 (fix 240%) |
| E. UES / IPE | MOYEN | Lisible | IPE faux | Fort | **BLOQUANT** | **P0** |
| F. Baseline | MOYEN | Tendances ok | kWh aberrants | Moyen | **BLOQUANT** | **P0** |
| G. Conformité | MOYEN | Lisible | Doublons | Fort | Fort | P1 |
| H. Coût / usage | **CASSÉ** | % > 100 | Invendable | **BLOQUANT** | **BLOQUANT** | **P0** |
| I. Facture / achat | BON | CTA clairs | Prix ref ok | Fort | Fort | — |
| J. Cross-briques | BON | Boutons ok | Navigation ok | Fort | Fort | P2 |
| K. Export / print | PRÉSENT | Bouton visible | Non testé | Moyen | Moyen | P2 |
| L. Multi-sites | BON | Adaptatif | 3 profils ok | Fort | Fort | — |
| M. État vide | BON | Message clair | Propre | Bon | Bon | — |

---

## 6. TOP 5 CORRECTIONS

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| 1 | **Fix coût par usage** : le % doit être relatif au total site, pas > 100 | 0.5j | Back | J+1 |
| 2 | **Fix baseline/IPE seed** : ventiler le kWh annual par pct_of_total, pas le total brut | 0.5j | Back/Seed | J+1 |
| 3 | **Dédupliquer conformité** : grouper par type d'usage (pas par usage_id) | 0.5j | Back | J+1 |
| 4 | **Ajouter "Usages" au sidebar** sous Énergie (NavRegistry visible) | 0.25j | Front | J+1 |
| 5 | **Plafonner couverture sous-comptage** à 100% ou afficher explication | 0.25j | Back | J+2 |

---

## 7. CAPTURES DE RÉFÉRENCE

| Fichier | Contenu |
|---------|---------|
| `V12-S1-01-fullpage.png` | Site 1 — Page complète |
| `V12-S1-02-viewport.png` | Site 1 — Header + Baseline + UES (above the fold) |
| `V12-S1-04-scroll900.png` | Site 1 — Plan de comptage + Dérives + début Conformité |
| `V12-S1-05-scroll1800.png` | Site 1 — Conformité + Coût + Facture & Achat |
| `V12-S1-06-scroll2700.png` | Site 1 — Liens cross-briques (bottom) |
| `V12-S3-01-fullpage.png` | Site 3 (Usine Toulouse) — Page complète |
| `V12-S4-01-fullpage.png` | Site 4 (Hôtel Nice) — Page complète |
| `V12-EMPTY-01.png` | État vide (pas de site sélectionné) |
