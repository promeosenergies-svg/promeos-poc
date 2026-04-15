# SPRINT V1.4 — Questionnaire → Conformité : effet produit réel

**Date** : 2026-03-14
**Scope** : Connecter les réponses du questionnaire de segmentation à l'affichage conformité
**Prérequis** : V1.3 (questionnaire en place, badge "Adapté", segProfile déjà fetché)

---

## 1. RÉSUMÉ EXÉCUTIF

La V1.3 a amélioré l'UX du questionnaire mais le lien métier reste cosmétique : un badge "Adapté à votre profil" ne change rien à l'affichage. La V1.4 rend le questionnaire **utile** : les réponses modifient réellement la priorisation des obligations, l'affichage du Décret Tertiaire, et le tri des cartes sur la page Conformité. Simple, crédible, démontrable en démo.

---

## 2. FAITS

| # | Fait | Source |
|---|------|--------|
| F1 | `segProfile` est déjà fetché dans `ConformitePage.jsx` (L749, L816-819) | Code |
| F2 | `segProfile.answers` contient les réponses (dont `q_surface_seuil`) | API `getSegmentationProfile` |
| F3 | `sortedObligations` (L917-939) trie par overdue → statut, mais ignore le profil | Code |
| F4 | `sitesToObligations()` (L233) construit les obligations depuis les findings API | Code |
| F5 | `ObligationCard` (ObligationsTab.jsx L378) affiche : régulation, badges sévérité/statut, description | Code |
| F6 | Le Décret Tertiaire a le code `tertiaire_operat` dans les findings | `REG_CONFIG` + API |
| F7 | `q_surface_seuil` a 4 valeurs possibles : `oui_majorite`, `oui_certains`, `non`, `ne_sait_pas` | `segmentation_service.py` |
| F8 | `segProfile.typologie` et `segProfile.segment_label` existent (détecté ou déclaré) | Model `SegmentationProfile` |
| F9 | Le score conformité composite pondère : DT 45%, BACS 30%, APER 25% | `compliance_score_service.py` |

---

## 3. HYPOTHÈSES

| # | Hypothèse | Risque |
|---|-----------|--------|
| H1 | Un utilisateur qui répond "Non" à q_surface_seuil a probablement des bâtiments < 1000m² et le DT n'est pas sa priorité | Faible — logique produit crédible |
| H2 | On ne masque JAMAIS une obligation, on la déprioritise ou on l'étiquette "à confirmer" | Nul — prudence juridique |
| H3 | Le tri des obligations peut être enrichi sans casser les filtres/recherche existants | Faible — on enrichit `sortedObligations` |
| H4 | 3 statuts de fiabilité suffisent pour V1.4 : `détecté`, `déclaré`, `à_confirmer` | Faible — extensible plus tard |

---

## 4. DÉCISIONS

| # | Décision |
|---|----------|
| D1 | **Ne jamais masquer** une obligation — seulement la déprioritiser ou la taguer |
| D2 | Le Décret Tertiaire descend en bas de liste si `q_surface_seuil = "non"` |
| D3 | Le DT affiche un tag "À confirmer" si `q_surface_seuil = "ne_sait_pas"` |
| D4 | Le DT affiche un tag "Prioritaire selon votre profil" si `q_surface_seuil = "oui_*"` |
| D5 | Un micro-texte explicatif apparaît sous le score : "Affichage ajusté selon votre profil déclaré." |
| D6 | Les obligations reçoivent un tag "Pertinent pour votre profil" selon la typologie |
| D7 | Un badge de fiabilité source (détecté / déclaré / à confirmer) est affiché par obligation |

---

## 5. RÈGLES MÉTIER

### R1 — Décret Tertiaire × q_surface_seuil

| Réponse q_surface_seuil | Effet sur DT | Tag affiché | Ordre dans la liste |
|--------------------------|-------------|-------------|---------------------|
| `oui_majorite` | Applicable prioritaire | `Prioritaire` (vert) | En tête (boost +10) |
| `oui_certains` | Applicable | `Applicable potentiel` (bleu) | Position normale |
| `non` | Déprioritisé | `Non prioritaire — à confirmer` (gris) | En bas (pénalité -10) |
| `ne_sait_pas` | À qualifier | `À qualifier` (orange) | Position normale |
| _(pas de réponse)_ | Pas de changement | _(rien)_ | Position normale |

### R2 — Pertinence par typologie

| Typologie | Obligations pertinentes |
|-----------|------------------------|
| `TERTIAIRE_PRIVE`, `TERTIAIRE_PUBLIC`, `COLLECTIVITE`, `ENSEIGNEMENT`, `SANTE_MEDICO_SOCIAL`, `HOTELLERIE_RESTAURATION` | DT + BACS + APER |
| `INDUSTRIE` | BACS (si CVC > 290kW) — DT moins pertinent |
| `COMMERCE_RETAIL` | DT (si > 1000m²) + BACS |
| `COPROPRIETE_SYNDIC`, `BAILLEUR_SOCIAL` | DT peu pertinent, BACS peu pertinent |

Tag "Pertinent pour votre profil" affiché si la typologie correspond.

### R3 — Statuts de fiabilité

| Statut | Signification | Badge |
|--------|--------------|-------|
| `detected` | Calculé automatiquement depuis les données patrimoine (surface, CVC, etc.) | `Détecté` gris neutre |
| `declared` | L'utilisateur a répondu au questionnaire | `Déclaré` bleu |
| `to_confirm` | Données insuffisantes ou contradictoires | `À confirmer` orange |

Logique de résolution :
- Si `q_surface_seuil` a une réponse ≠ `ne_sait_pas` → `declared`
- Si le finding a `status = OK/NOK` basé sur des données patrimoine → `detected`
- Sinon → `to_confirm`

### R4 — Texte explicatif

Quand `segProfile?.has_profile && Object.keys(segProfile.answers || {}).length > 0` :
- Sous le score : "Certaines obligations sont adaptées selon votre profil déclaré."
- Sous chaque tag de profil : tooltip avec la raison (ex: "Surface > 1000 m² déclarée")

---

## 6. FICHIERS À MODIFIER

### Frontend (4 fichiers)

| Fichier | Modification |
|---------|-------------|
| `frontend/src/pages/ConformitePage.jsx` | Passer `segProfile` à `ObligationsTab` ; enrichir `sortedObligations` avec tri profil ; ajouter texte explicatif sous le score |
| `frontend/src/pages/conformite-tabs/ObligationsTab.jsx` | Recevoir `segProfile` en prop ; afficher tags "Prioritaire" / "Non prioritaire" / "Pertinent" / badge fiabilité sur `ObligationCard` |
| `frontend/src/models/complianceProfileRules.js` | **NOUVEAU** — Logique pure (pas de React) : `computeObligationProfileTags(obligations, segProfile)` retourne un Map<obligationId, {priorityBoost, tag, tagColor, reliabilityStatus, tooltip}> |
| `frontend/src/__tests__/v14_questionnaire_conformite.test.js` | **NOUVEAU** — Tests source-guard pour V1.4 |

### Backend (0 fichier)

Aucune modification backend nécessaire. `segProfile` est déjà exposé via `/api/segmentation/profile` et contient `answers`, `typologie`, `confidence_score`, `segment_label`.

---

## 7. PATCHES PROPOSÉS

### 7A — `complianceProfileRules.js` (nouveau fichier)

```javascript
/**
 * PROMEOS — V1.4 Compliance × Profile rules
 * Logique pure : calcule les tags et priorités des obligations
 * selon le profil de segmentation.
 */

const TERTIAIRE_TYPOLOGIES = [
  'tertiaire_prive', 'tertiaire_public', 'collectivite',
  'enseignement', 'sante_medico_social', 'hotellerie_restauration',
];

const DT_SURFACE_RULES = {
  oui_majorite:  { boost: 10,  tag: 'Prioritaire',                    color: 'green', reliability: 'declared' },
  oui_certains:  { boost: 0,   tag: 'Applicable potentiel',           color: 'blue',  reliability: 'declared' },
  non:           { boost: -10, tag: 'Non prioritaire — à confirmer',  color: 'gray',  reliability: 'declared' },
  ne_sait_pas:   { boost: 0,   tag: 'À qualifier',                    color: 'amber', reliability: 'to_confirm' },
};

export function computeObligationProfileTags(obligations, segProfile) {
  const result = new Map();
  if (!segProfile?.has_profile) return result;

  const answers = segProfile.answers || {};
  const typologie = (segProfile.typologie || '').toLowerCase();
  const surfaceAnswer = answers.q_surface_seuil;

  for (const obl of obligations) {
    const code = (obl.code || obl.id || '').toLowerCase();
    const entry = { priorityBoost: 0, tags: [], reliability: 'detected' };

    // R1 — Décret Tertiaire × q_surface_seuil
    if (code.includes('tertiaire') && surfaceAnswer && DT_SURFACE_RULES[surfaceAnswer]) {
      const rule = DT_SURFACE_RULES[surfaceAnswer];
      entry.priorityBoost = rule.boost;
      entry.tags.push({ label: rule.tag, color: rule.color, tooltip: `Surface > 1000 m² : ${surfaceAnswer.replace('_', ' ')}` });
      entry.reliability = rule.reliability;
    }

    // R2 — Pertinence par typologie
    if (typologie) {
      const isDtRelevant = code.includes('tertiaire') && TERTIAIRE_TYPOLOGIES.includes(typologie);
      const isBacsRelevant = code.includes('bacs') && !['copropriete_syndic', 'bailleur_social'].includes(typologie);
      const isAperRelevant = code.includes('aper');

      if (isDtRelevant || isBacsRelevant || isAperRelevant) {
        entry.tags.push({ label: 'Pertinent pour votre profil', color: 'blue', tooltip: `Typologie : ${segProfile.segment_label}` });
      }
    }

    // R3 — Fiabilité
    if (Object.keys(answers).length > 0) {
      entry.reliability = surfaceAnswer && surfaceAnswer !== 'ne_sait_pas' ? 'declared' : 'to_confirm';
    }

    if (entry.tags.length > 0 || entry.priorityBoost !== 0) {
      result.set(obl.id || obl.code, entry);
    }
  }

  return result;
}
```

### 7B — `ConformitePage.jsx` — Enrichir le tri et passer segProfile

Dans `sortedObligations` (L917-939), ajouter le boost de profil :

```javascript
// Import en tête
import { computeObligationProfileTags } from '../models/complianceProfileRules';

// Dans le useMemo sortedObligations :
const profileTags = useMemo(
  () => computeObligationProfileTags(obligations, segProfile),
  [obligations, segProfile]
);

const sortedObligations = useMemo(() => {
  let list = [...obligations];
  if (statusFilter) {
    list = list.filter((o) => o.statut === statusFilter);
  }
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase();
    list = list.filter(
      (o) =>
        o.regulation.toLowerCase().includes(q) ||
        o.description.toLowerCase().includes(q) ||
        o.code.toLowerCase().includes(q)
    );
  }
  list.sort((a, b) => {
    const aOver = isOverdue(a) ? 0 : 1;
    const bOver = isOverdue(b) ? 0 : 1;
    if (aOver !== bOver) return aOver - bOver;
    const order = { non_conforme: 0, a_risque: 1, conforme: 2 };
    const aBase = order[a.statut] ?? 9;
    const bBase = order[b.statut] ?? 9;
    // V1.4: profile boost
    const aBoost = profileTags.get(a.id || a.code)?.priorityBoost || 0;
    const bBoost = profileTags.get(b.id || b.code)?.priorityBoost || 0;
    return (aBase - aBoost) - (bBase - bBoost);
  });
  return list;
}, [obligations, statusFilter, searchQuery, profileTags]);
```

Passer à ObligationsTab :
```jsx
<ObligationsTab
  ...
  segProfile={segProfile}
  profileTags={profileTags}
/>
```

Texte explicatif sous le score :
```jsx
{segProfile?.has_profile && Object.keys(segProfile.answers || {}).length > 0 && (
  <>
    <p className="text-[10px] text-blue-600 font-medium mt-1" data-testid="profile-badge">
      Adapté à votre profil
    </p>
    <p className="text-[9px] text-gray-400 mt-0.5" data-testid="profile-explain">
      Certaines obligations sont adaptées selon votre profil déclaré.
    </p>
  </>
)}
```

### 7C — `ObligationsTab.jsx` — Afficher les tags sur ObligationCard

Dans `ObligationCard`, recevoir `profileEntry` en prop et afficher :

```jsx
{/* Après les badges existants (sévérité, statut, overdue) */}
{profileEntry?.tags?.map((tag, i) => (
  <span
    key={i}
    className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
      tag.color === 'green' ? 'bg-green-100 text-green-700' :
      tag.color === 'blue'  ? 'bg-blue-100 text-blue-700' :
      tag.color === 'amber' ? 'bg-amber-100 text-amber-700' :
                              'bg-gray-100 text-gray-500'
    }`}
    title={tag.tooltip}
  >
    {tag.label}
  </span>
))}
{profileEntry?.reliability && (
  <span
    className={`text-[9px] px-1.5 py-0.5 rounded ${
      profileEntry.reliability === 'declared'   ? 'bg-blue-50 text-blue-500' :
      profileEntry.reliability === 'detected'   ? 'bg-gray-50 text-gray-400' :
                                                  'bg-amber-50 text-amber-500'
    }`}
    title={
      profileEntry.reliability === 'declared'   ? 'Statut basé sur vos réponses' :
      profileEntry.reliability === 'detected'   ? 'Détecté automatiquement' :
                                                  'Données insuffisantes — à confirmer'
    }
  >
    {profileEntry.reliability === 'declared' ? 'Déclaré' :
     profileEntry.reliability === 'detected' ? 'Détecté' : 'À confirmer'}
  </span>
)}
```

---

## 8. CRITÈRES D'ACCEPTATION

| # | Critère | Méthode de vérification |
|---|---------|------------------------|
| CA1 | Si q_surface_seuil = "non", le Décret Tertiaire est en bas de la liste | Visuel : carte DT en dernier |
| CA2 | Si q_surface_seuil = "oui_majorite", le DT a un tag vert "Prioritaire" | Visuel : badge vert sur la carte |
| CA3 | Si q_surface_seuil = "ne_sait_pas", le DT a un tag orange "À qualifier" | Visuel : badge orange |
| CA4 | Le texte "Certaines obligations sont adaptées selon votre profil déclaré." est visible sous le score | Visuel + data-testid="profile-explain" |
| CA5 | Le badge "Pertinent pour votre profil" apparaît sur les obligations pertinentes pour la typologie | Visuel : badge bleu |
| CA6 | Le badge de fiabilité (Déclaré/Détecté/À confirmer) est visible | Visuel : mini-badge |
| CA7 | Sans profil (pas de réponses), aucun tag n'apparaît = comportement identique V1.3 | Visuel : page inchangée |
| CA8 | Les filtres (statut, recherche) fonctionnent toujours | Test manuel |
| CA9 | Le tri par urgence (overdue + statut) est préservé, le boost profil ne casse pas l'ordre logique | Test manuel |
| CA10 | Tous les tests existants passent | `npx vitest run` → ALL PASSED |

---

## 9. CAS DE TEST MANUELS

| # | Scénario | Étapes | Résultat attendu |
|---|----------|--------|------------------|
| T1 | DT prioritaire | 1. Répondre q_surface_seuil = "Oui, la majorité" 2. Aller sur /conformite | DT en tête avec badge vert "Prioritaire" |
| T2 | DT déprioritisé | 1. Répondre q_surface_seuil = "Non" 2. Aller sur /conformite | DT en bas avec badge gris "Non prioritaire — à confirmer" |
| T3 | DT à qualifier | 1. Répondre q_surface_seuil = "Je ne suis pas sûr" 2. Aller sur /conformite | DT avec badge orange "À qualifier" |
| T4 | Sans réponse | 1. Ne pas répondre au questionnaire 2. Aller sur /conformite | Aucun tag, affichage V1.3 identique |
| T5 | Texte explicatif | 1. Répondre au questionnaire 2. Aller sur /conformite | Texte "Certaines obligations sont adaptées..." visible sous le score |
| T6 | Pertinence typologie | 1. Profil détecté "Tertiaire Privé" 2. Aller sur /conformite | Badge "Pertinent pour votre profil" sur DT et BACS |
| T7 | Fiabilité déclaré | 1. Répondre q_surface_seuil 2. Vérifier la carte DT | Mini-badge "Déclaré" visible |
| T8 | Filtres préservés | 1. Avoir un profil 2. Filtrer par statut "Non conforme" | Filtrage fonctionne, tags visibles sur les résultats filtrés |
| T9 | Industrie | 1. Profil "Industrie" 2. Aller sur /conformite | DT n'a PAS le badge "Pertinent", BACS oui |

---

## 10. TOP 5 ACTIONS

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| 1 | Créer `complianceProfileRules.js` (logique pure, testable) | 0.5j | Front | J+1 |
| 2 | Modifier `ConformitePage.jsx` : passer segProfile + profileTags, enrichir tri, ajouter texte explicatif | 1j | Front | J+2 |
| 3 | Modifier `ObligationsTab.jsx` : afficher tags + badge fiabilité sur ObligationCard | 1j | Front | J+3 |
| 4 | Écrire tests source-guard V1.4 | 0.5j | Front | J+3 |
| 5 | Validation visuelle (audit Playwright) + ajustements UX | 0.5j | Front | J+4 |

**Total estimé : 3.5 jours**
**Complexité : Faible** — 100% frontend, pas de migration, pas de nouveau endpoint
**Risque : Très faible** — logique additionnelle sur un affichage existant, fallback = affichage V1.3

---

## 11. CE QUI N'EST PAS DANS LE SCOPE V1.4

- Pas de moteur réglementaire backend (les rules restent côté compliance_engine)
- Pas de filtrage dur (masquer des obligations) — uniquement du tri + tags
- Pas de tunnel de qualification complète
- Pas de nouveau endpoint API
- Pas de refonte de la page Conformité
