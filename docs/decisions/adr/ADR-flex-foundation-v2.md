# ADR — Flex Foundation V2

**Statut :** Accepté
**Date :** 2026-03-18
**Auteur :** Architecture PROMEOS

---

## Contexte

PROMEOS doit accueillir une brique flexibilité cohérente avec la chaîne existante (patrimoine → conformité → billing → purchase → actions). L'audit flex v1 contenait des simplifications réglementaires corrigées ici.

## Décision

### 1. FlexAsset comme objet pivot

Les assets pilotables sont modélisés comme `FlexAsset` rattachés à `Site` et optionnellement à `BacsCvcSystem`. Cela permet :
- Un inventaire par site/bâtiment
- Un lien direct BACS classe GTB → potentiel flex
- Une traçabilité source (déclaratif, inspection, sync BACS)

**Alternative rejetée :** Étendre directement BacsCvcSystem avec des champs flex. Rejeté car le périmètre flex dépasse le CVC (IRVE, PV, stockage, process).

### 2. Fenêtres tarifaires saisonnalisées (pas de hardcode HC)

Les fenêtres HC/HP ne sont JAMAIS hardcodées. Elles sont toujours lues depuis `TariffCalendar.ruleset_json` avec :
- Saisons explicites (hiver/été/mi-saison)
- Types de jour (weekday/weekend/holiday)
- Types de période distincts : `HC_NUIT`, `HC_SOLAIRE`, `HP`, `POINTE`
- Source officielle (CRE, distributeur)

**Rationale :** La réforme HC/HP 2025-2027 crée des fenêtres variables par distributeur, segment et calendrier de migration. Un hardcode serait faux pour une partie des clients.

### 3. APER = solarisation, pas autoconsommation

APER impose l'installation d'ombrières/PV. L'autoconsommation, l'ACC et le stockage sont des **opportunités** distinctes, pas des obligations.

### 4. CEE = éligibilité potentielle

Les CEE P6 sont un levier potentiel de financement, jamais garanti. Le TRI minimum est de 3 ans. Les volumes et la valorisation dépendent de l'opérateur CEE agréé.

### 5. NEBCO = structure, pas de valorisation Sprint 21

Le modèle NebcoSignal prépare la valorisation sans l'implémenter. Le seuil de participation n'est pas hardcodé (non confirmé CRE).

### 6. Pas de dispatch dans Sprint 21

Aucune logique de commande/pilotage réel. FlexAsset reste un inventaire. Le dispatch viendra dans un sprint ultérieur quand les données sont fiabilisées.

## Conséquences

- FlexAsset est le point d'entrée unique pour la flexibilité
- Le scoring flex_mini existant est enrichi progressivement, pas remplacé
- Les calculs tarifaires utilisent exclusivement TariffCalendar, jamais de constante
- La chaîne PROMEOS reste intacte : patrimoine → conformité → billing → purchase → actions
- La flex s'insère comme enrichissement des vues existantes, pas comme module isolé
