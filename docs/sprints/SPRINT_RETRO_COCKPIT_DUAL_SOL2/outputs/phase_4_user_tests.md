# Phase 4 — Test utilisateur réel — NON RÉALISÉ

## Statut

**Phase 4 (test utilisateur 30s avec panel CFO/DG/Energy Manager) n'a pas
été conduite formellement pendant ce sprint** (5 jours 26→30/04/2026 sur
branche `claude/refonte-sol2`).

## Raison

- Sprint dimensionné en **mode itératif court** (5 jours) avec 24 phases
  ré-arbitrées entre l'audit doctrine et la dette technique post-V120.
- Pas de panel utilisateur mobilisable sur cette fenêtre temporelle.
- Le sprint a privilégié la **construction de la doctrine exécutable**
  (constants, KPIs registry, briefings) et la **consolidation des
  source-guards** (passage 5 861 → 6 183 tests BE) plutôt que la
  validation panel terminale.

## Proxy effectué (audits 14 agents Claude Code)

À défaut de panel CFO/DG humain, **14 agents subagents Claude** ont
été convoqués en parallèle à chaque fin de phase pour simuler la
relecture multi-perspective :

- véracité (chiffres sourcés réglementaire/contrat)
- jargon (acronymes glossés vs bruts)
- navigation (routes legacy, redirects, scope switcher)
- personas Marc/Marie/Jean-Marc/Sophie/Antoine
- doctrine §11.3 conformité

Scores cumulés (audits Vague A à Phase 23) :
- véracité : **3,2 → 7,1** (+3,9)
- jargon : 4,83 → ~6,5-7 (statique)
- navigation : 5,4 → ~7,5 (estimé sans audit final)
- CX : 6,4 (Marie audit Vague A)
- Marie DAF : 5,5 → 7,8 estimé post-Phase 23

## Limitation reconnue

Ces scores sont **proxy IA**, pas validation terrain. Aucun verbatim
"En 30 secondes, dites-moi ce que vous avez compris" n'a été collecté
auprès d'un dirigeant ou energy manager humain.

## Plan de rattrapage proposé

À programmer sur Sprint suivant (S+1 mai 2026) :
- Session 1 — CFO Jean-Marc (profil DAF tertiaire mid-market)
- Session 2 — Energy Manager Marie (responsable conformité/RegOps)
- Session 3 — DG investisseur (préparé pour la démo intégrale juillet 2026)

Critères mesurables à chronométrer :
- Délai jusqu'à identification du risque réglementaire (cible ≤ 30s)
- Délai jusqu'à identification des 3 décisions à arbitrer (cible ≤ 60s)
- Verbatim post-démo (1 phrase libre)

## DoD §11.3 — statut

PARTIEL : la conformité doctrine §11.3 a été vérifiée par audits IA
(Phase 14, 15, 17, 19, 22, 23) mais pas par utilisateur final humain.
Le sprint a livré la **plateforme** Cockpit dual conforme doctrine ;
la **validation usage** reste en backlog post-sprint.
