# ADR-010 — TraceTooltip masquage R10 pour termes `pending_source_verification`

**Statut** : Accepté
**Date** : 2026-05-05
**Sprint** : C-4 Phase 4.2d audit follow-up
**Personnes impliquées** : Amine (founder), Claude architect-helios + regulatory-expert + bill-intelligence
**Tracking dette** : `D-Phase4-2d-Pending-Source-Verification-001`

---

## Contexte

Sprint C-4 Phase 4.2 a livré 9 termes YAML CAPACITE_RTE / VNU / CBAM. Audit multi-agents post-Phase 4.2 (regulatory-expert + code-reviewer + bill-intelligence convergents) a révélé :

1. **5 termes confidence LOW non vérifiables** : WebFetch bloqué allow-list pour Légifrance / CRE / services-rte.com. Seul EUR-Lex CBAM accessible (CBAM_OBLIGATION_DEADLINE + CBAM_REGLEMENT_REFERENCE = ✅ validés haute confiance).

2. **Sources potentiellement hallucinées** : Décret n°2026-55 (VNU) + CRE délibération 2026-52 (VNU seuils) référencés dans le code repo (`cost_simulator_2026.py` docstring) **mais NON retrouvés** par audit regulatory-expert sur le portail CRE public (confusion possible avec délibération 2026-70 minoration nucléaire, scope adjacent ≠).

3. **Risque cardinal R10** : différenciateur PROMEOS = traçabilité 100%. Exposer un `<TraceTooltip>` cliquable vers une URL nulle, ou citer une délibération CRE qui n'existe pas, **viole la promesse R10** et casse la crédibilité commerciale (anti-pattern PROMEOS Sol §6.4 "0 chiffre sans source").

5 termes affectés :

- `CAPACITE_RTE_OBLIGATION_DEADLINE` (medium confidence — Décret 2025-1441)
- `CAPACITE_RTE_TARIF_2026_EUR_PER_MW` (low — disambiguation 3.15 vs 3150 EUR/MW)
- `CAPACITE_RTE_COEFF_2026` (low — coefficient RTE non confirmé)
- `VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH` (low — CRE 2026-52 non retrouvée)
- `VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH` + `_HAUT_*` (low — CRE 2026-52 non retrouvée)

---

## Décision

### Schéma YAML — 2 champs ajoutés

```yaml
TERME_INCERTAIN:
  value: 3.15
  unit: "EUR/MW"
  domain: "tarifs"
  status: "pending_source_verification"  # ⚠️ NOUVEAU Phase 4.2d
  confidence: "low"                       # NOUVEAU : low | medium | high
  source: ...
  notes: "Vérification experte Sprint C-7 (référence dette)."
```

### Composant FE TraceTooltip — render conditionnel

```jsx
const isPendingVerification = trace.status === 'pending_source_verification';

// Au lieu du lien externe :
{isPendingVerification ? (
  <div className="text-amber-700 text-[11px] italic bg-amber-50 px-1.5 py-0.5 rounded">
    ⚠️ Source en cours de vérification (Sprint C-7+)
  </div>
) : (
  trace.source.url && (<a href={trace.source.url}>...</a>)
)}
```

**Comportement utilisateur** :
- Tooltip reste visible (transparence)
- Valeur + unit affichés normalement (le calcul utilise la valeur)
- Source label affiché normalement (transparence sur la référence revendiquée)
- **Aucun lien externe rendu** (évite redirection 404 ou source incorrecte)
- **Bannière warning ambre** signale que la source est en cours de vérification

### Doctrine cardinale "0 chiffre sans source affirmée"

PROMEOS ne ment jamais sur ses sources. Si la source légale revendiquée n'a pas été vérifiée par lecture officielle (Légifrance/CRE/EUR-Lex), elle est **explicitement marquée comme telle** dans l'UI. Le différenciateur R10 préserve sa crédibilité commerciale en assumant l'incertitude au lieu de la masquer.

### Critères d'utilisation

| Statut | Conditions | Comportement R10 TraceTooltip |
|---|---|---|
| (absent ou `verified`) | Source vérifiée Légifrance/CRE/EUR-Lex avec URL fonctionnelle | Lien externe cliquable normal (R10 plein) |
| `pending_source_verification` | Source revendiquée mais non vérifiable (allow-list / délib non retrouvée / disambiguation requise) | Bannière warning ambre, pas de lien |
| `verified_partial` (futur) | Référence légale confirmée mais URL deep-link manquante | Affiche legal_reference seul sans lien (à statuer Sprint C-7) |

---

## Conséquences

### Positives

- **Cohérence R10 préservée** : PROMEOS ne fabrique jamais de sources légales fantômes
- **Transparence utilisateur** : valeur utilisable mais incertitude assumée
- **Différenciateur commercial intact** : argument vs Deepki/Spacewell renforcé (PROMEOS audit ses propres sources)
- **Trajectoire vers verification 100%** : tag pending = backlog explicite Sprint C-7
- **Compatible doctrine PROMEOS Sol §6.4** "1 SoT par concept + 0 chiffre sans source"

### Négatives / Compromis

- **5 termes Phase 4.2 démarrent en LOW confidence** (pas idéal mais transparent)
- **Coût cognitif FE** : devs doivent connaître le schema status (mitigation : ADR-010 cité dans CONTRIBUTING.md + commentaire en haut de TraceTooltip)
- **Risque sur-utilisation** du tag pending si paresse (mitigation : règle Phase 0 sprint = tout terme YAML doit avoir status verified ou justification pending tracée dette)

### Source-guards anti-régression

- `test_yaml_pending_status_tracked_in_tracker` (Sprint C-7) : tout terme `pending_source_verification` doit avoir une dette tracker correspondante
- `test_tracetooltip_pending_renders_warning_banner` (FE Phase 4.2d ou Sprint C-5) : test rendu bannière

### Tests anti-régression Sprint C-4 P4.2d

- 1 test FE TraceTooltip rendu pending (bannière warning visible, pas de lien)
- 1 test FE TraceTooltip rendu verified (lien cliquable normal)
- 1 SG BE : terms en pending référencent une dette tracker

---

## Alternatives considérées

| Option | Pourquoi rejetée |
|---|---|
| **Masquer entièrement TraceTooltip** sur termes pending | Perd transparence — l'utilisateur ne sait pas que la valeur a été utilisée. Différenciateur R10 affaibli. |
| **Afficher lien quand même avec warning** | Lien null = redirection 404 = embarras utilisateur. Lien hallucination = mensonge sur source. Anti-pattern PROMEOS. |
| **Désactiver utilisation backend** des termes pending | Casse les calculs (cost_simulator_2026, billing_engine). Pour MVP, mieux vaut calculer avec valeur doctrinale + transparence vs ne pas calculer du tout. |
| **Demander confirmation explicite** utilisateur avant utilisation | Friction excessive, scope creep majeur. Pas de bénéfice vs bannière warning. |
| **Stocker hash de la dernière vérification source** | Overkill pour MVP. À considérer Sprint C-9+ si processus de vérification sources devient industrialisé. |

---

## Statut & validation

- **Acceptée** : 2026-05-05 (Sprint C-4 Phase 4.2d)
- **Implémentation** : Sprint C-4 Phase 4.2d (commit dédié, 5 termes taggés + TraceTooltip render conditionnel)
- **Vérification source experte** : Sprint C-7 polish (D-Phase4-2d-Pending-Source-Verification-001 + WebFetch-Allowlist-Review)

Closes (post-implémentation Phase 4.2d) : `D-Sprint-C3-7d-ADR-Routes-Namespace-001` non lié, mais cet ADR-010 prépare le terrain pour la doctrine cohérente "status = pending vs verified" qui s'appliquera à tous les termes YAML futurs (Sprint C-5+).
