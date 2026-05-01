# Audit qualité narrative HELIOS — 2026-05-01

> Sources : `samples/narrative_helios_daily_text.txt` (Marie 8h45 daily) +
> `samples/narrative_helios_comex_text.txt` (Jean-Marc CFO comex).
> Endpoint : `/api/pages/{page_key}/briefing?org_id=1&persona={daily|comex}`.

## Texte capturé — DAILY (Marie 8h45)

> Vous avez 3 sites en dérive sur 5, exposant 26.2 k€ de risque
> réglementaire. Score conformité 37/100 sur la trajectoire 2030
> obligatoire (Décret n°2019-771).

## Texte capturé — COMEX (Jean-Marc CFO)

> Exposition réglementaire cumulée : 26.2 k€ sur 3/5 sites en dérive de
> la trajectoire 2030. Score conformité 37/100 — écart significatif vs
> cible 2030 (Décret n°2019-771, jalons -40%/2030, -50%/2040, -60%/2050).
> Potentiel énergétique récupérable 1794 MWh/an sur 29 actions ouvertes
> (CEE BAT-TH-116, BAT-TH-104) — détail plan d'actions.

## Évaluation structurelle

### Longueur

| Persona | Mots | Phrases | Lisibilité estimée |
|---|---:|---:|---|
| daily (Marie) | ~30 | 2 | < 30 secondes |
| comex (Jean-Marc) | ~50 | 3 | ~ 45 secondes |

### Structure éditoriale

**Daily** :
- Phrase d'ouverture : "Vous avez 3 sites en dérive sur 5, exposant 26.2 k€ de risque réglementaire."
- Donne-t-elle le contexte global ? **PARTIEL** — donne le signal saillant (3/5 + 26 k€) mais pas le scope (Groupe HELIOS) ni le timing (semaine en cours)
- Hiérarchise-t-elle l'information ? **OUI** — exposition financière → score → référentiel
- Pousse-t-elle un signal saillant ? **OUI** — "3 sites en dérive sur 5" est saillant

**Comex** :
- Phrase d'ouverture : "Exposition réglementaire cumulée : 26.2 k€ sur 3/5 sites en dérive de la trajectoire 2030."
- Donne-t-elle le contexte global ? **PARTIEL** — pas de mention du nom org ni du timing
- Hiérarchise-t-elle l'information ? **OUI** — exposition → score + jalons → potentiel + actions
- Pousse-t-elle un signal saillant ? **OUI** — "écart significatif vs cible 2030" est explicite

### Vocabulaire

**Acronymes bruts présents** :
- Daily : `Décret n°2019-771` (référence numérique brute, OK car contextualisée par "trajectoire 2030 obligatoire")
- Comex : `Décret n°2019-771` + `CEE BAT-TH-116`, `BAT-TH-104`, `MWh/an`, `k€`

**Transformés via `acronym_to_narrative`** ?
- Vérification grep sur `narrative_generator.py` : oui, helper `transform_acronym` est importé depuis `doctrine.acronyms` mais utilisé sur les TITRES d'actions, PAS sur le corps narrative.
- Conclusion : **les acronymes du body narrative ne passent PAS par le transformer** — ils sont insérés en dur via les f-strings des builders.

**Vocabulaire institutionnel** :
- Daily : "trajectoire 2030", "score conformité", "risque réglementaire" — vocabulaire RegOps standard
- Comex : "Exposition réglementaire cumulée", "écart significatif vs cible 2030", "potentiel énergétique récupérable", "plan d'actions" — vocabulaire CFO/COMEX standard

### Push événementiel

**Mention "+X vs S-1" présente ?** **NON** dans la narrative principale.
- Vérification : `consumption.j_minus_1.delta_pct` et `weekly_deltas` sont
  exposés dans `_facts` et dans la card Décision (Phase 3.3) mais **PAS
  injectés dans la narrative comex**.
- La narrative n'a aucune référence temporelle relative
  ("cette semaine", "vs hier", "+3 k€ vs S-1").
- Granularité : 0 signal poussé.

**Bruit éventuel ("+0,2 k€ vs S-1")** : NON applicable car aucun signal poussé.

### Personnalisation

**Adaptée au persona connecté ?** **PARTIEL** :
- 2 versions distinctes (daily + comex) avec lexique différent (Marie =
  vouvoiement direct "Vous avez", Jean-Marc = formulation tierce-personne
  "Exposition cumulée")
- Daily est plus court et plus actionnable, Comex plus dense et plus
  référentiel
- MAIS : pas de mention du **nom du persona** ("Marie", "Jean-Marc") ni de
  son **rôle** ("DAF", "CFO"). Le tutoiement n'est pas non plus calé sur
  le rôle (Marie reçoit un "vous" formel).

**Adaptée à la typologie d'organisation ?** **NON** :
- Aucune variation lexicale selon le secteur (tertiaire bureau vs
  commerce vs ERP vs industrie). HELIOS est un mix tertiaire (bureau,
  hôtel, école, entrepôt) mais la narrative ne mentionne ni la diversité
  des typologies ni un contexte sectoriel.
- Vérification : pas de référence au champ `naf_code` dans le
  `narrative_generator.py` (à confirmer Phase 3.A).

**Variations selon contexte (urgence vs stable)** : **PARTIEL**
- Le ton est exclusivement "alarme retenue" (3/5 sites + écart
  significatif). Aucune narrative observée pour un cas "stable" ou
  "amélioration vs S-1".
- Vérification : champ `narrative_tone` est exposé dans le payload
  (cf `keys`), mais valeur observée non collectée — à creuser Phase 4.

### Doctrinalement

**Score / 10 selon doctrine §11.3** : **5/10** (estimation auditeur).

| Critère doctrine §11.3 | Note | Justification |
|---|---:|---|
| Remplace un dashboard (synthèse compréhensible 30s) | 7/10 | Fait son job sur signal + ordre de grandeur |
| Hiérarchise l'information critique | 8/10 | Signal saillant en 1ère phrase, référentiel en 2ème |
| Variation par typologie organisationnelle | 0/10 | Aucune variation NAF |
| Variation par persona (au-delà longueur) | 4/10 | 2 versions ok mais pas de mention nom/rôle |
| Push événementiel "+X vs S-1" | 0/10 | Absent |
| Acronymes glossés inline | 3/10 | Acronymes bruts présents dans le body |
| Tonalité contextuelle (urgence/stable/amélioration) | 2/10 | Toujours "alarme retenue" sur HELIOS |
| Sourçage réglementaire visible | 9/10 | Décret + jalons + CEE cités correctement |

**Verdict** : remplace-t-elle un dashboard ou est-elle juste un libellé décoratif ?

→ **REMPLACE PARTIELLEMENT** un dashboard. La narrative donne 80 % de la valeur
d'un coup d'œil dashboard pour le scope HELIOS, mais elle est **figée dans le
temps** (pas de push +X vs S-1, pas de variation contextuelle), **figée par
typologie** (pas de variation NAF), et **acronymes bruts** non transformés.

Cible doctrinale §11.3 (3 typologies × 6 déclencheurs hiérarchisés × push
événementiel + mention persona) : **non atteinte**. La narrative actuelle
est un MVP fonctionnel mais doctrinalement incomplet.

## Points de rupture vs cible

1. **Pas de variation par typologie organisationnelle** — pas de mapping
   NAF → typologie, pas de templates lexicaux par secteur.
2. **Pas de push événementiel "+X vs S-1"** — `weekly_deltas` exposé dans
   `_facts` mais non consommé par narrative_generator.
3. **Pas de mention persona** — la narrative diffère par longueur mais
   ne nomme pas le destinataire ni son rôle.
4. **Acronymes bruts dans le body** — `transform_acronym` n'est appliqué
   qu'aux titres d'actions, pas au corps narrative.
5. **Tonalité monotonique** — pas de bascule "alarme/stable/amélioration"
   selon le contexte saisonnier ou la dynamique.
6. **Pas de paramètre temporel `simulate_date`** — endpoint l'accepte
   silencieusement (HTTP 200) mais ignore. Pas de manière de tester la
   dynamique sans muter la DB.
