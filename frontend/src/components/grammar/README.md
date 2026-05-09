# grammar/ — 6 primitifs grammaire Sol v1.1

Namespace `frontend/src/components/grammar/` = contrats canoniques des 6 primitifs editoriaux PROMEOS.

Doctrine Sol §5 : chaque page Sol est composee d'assemblages de ces primitifs.

## Primitifs

### SolPageFooter (alias re-export)
Source · Confiance · Mis a jour — invariant de credibilite B2B.

```jsx
import { SolPageFooter } from 'components/grammar';
<SolPageFooter source="RegOps" confidence="high" updatedAt={ts} methodologyUrl="/methodologie" />
```

### SolHero (wrapper SolNarrative)
Kicker + titre + narrative 2-3 lignes + CTA optionnel.

```jsx
import { SolHero } from 'components/grammar';
<SolHero kicker="GROUPE HELIOS · 5 SITES" titre="Tableau de bord operationnel" narrative="..." kpis={[...]} cta={{ label: 'Voir details', href: '/conformite' }} />
```

### KPISol (wrapper KpiCard contrat KpiResult backend)
KPI avec tooltip metadata riche + badge statut.

```jsx
import { KPISol } from 'components/grammar';
<KPISol descriptor={{ kpi_id: 'compliance_score', label: 'Score conformite', value: 73, unit: '/100', source: 'RegOps', status: 'calculated', confidence: 'high' }} variant="hero" />
```

### Term (NOUVEAU — acronyme avec tooltip narratif)
Consomme le glossaire PROMEOS, 3 variants d'affichage.

```jsx
import { Term } from 'components/grammar';
<Term acronyme="BACS" variant="inline-tooltip" />
<Term acronyme="TURPE" variant="narrative" />
<Term acronyme="CTA" variant="short" />
```

### WeekCard (wrapper SolWeekCards single)
Carte typee parmi 4 variantes doctrinales.

```jsx
import { WeekCard } from 'components/grammar';
<WeekCard variant="a-faire" titre="Contester la facture mars" resume="Ecart 2,3 k€ detecte" impact={2300} echeance={7} cta={{ label: 'Voir', href: '/factures' }} />
```

### DecisionEvidenceCard (NOUVEAU — carte decision avec grille evidence)
Rang + category + scope + severity + lead + 4-8 cellules evidence sourcees.

```jsx
import { DecisionEvidenceCard } from 'components/grammar';
<DecisionEvidenceCard
  rang={1}
  category="CONFORMITE"
  scope="SIEGE PARIS"
  severity="warning"
  titre="Trajectoire DT a risque"
  lead="3 sites risquent une penalite OPERAT si aucune action avant septembre."
  evidence={[
    { label: 'Score actuel', value: 73, unit: '/100' },
    { label: 'Cible 2030', value: 60, unit: '/100' },
    { label: 'Ecart', value: '-13', unit: 'pts' },
    { label: 'Penalite potentielle', value: '26', unit: 'k€', helper: 'estimation RegOps' },
  ]}
  methodologyRef="/methodologie/dt"
  primaryCta={{ label: 'Planifier', href: '/actions' }}
/>
```

## Regles d'usage

- **Zero calcul metier** dans les primitifs — tout vient du backend via REST
- **Tonalite calme par defaut** — le rouge oriente, il ne colore pas
- **evidence** : 4-8 cellules strictement (validation runtime doctrine §5.6 L9)
- **Term** : tout acronyme metier doit etre wrappe (doctrine §6.4 "acronyme → recit")
