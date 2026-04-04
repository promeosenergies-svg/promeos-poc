# Cross-Skill Routing — Quand un skill doit pointer vers un autre

## Matrice de cross-routing

| Si tu travailles sur... | Et tu rencontres... | Lis aussi le skill... |
|---|---|---|
| promeos-billing | Périodes tarifaires HP/HC/HPH | promeos-energy-fundamentals |
| promeos-billing | Contrat fournisseur, resolve_pricing | energy-contracts-b2b |
| promeos-billing | Données CDC Enedis pour shadow billing | promeos-enedis |
| promeos-regulatory | Calcul kWh/m², DJU, correction climatique | promeos-energy-fundamentals |
| promeos-regulatory | Contrats V2 dans scoring compliance | promeos-architecture |
| promeos-enedis | Segments compteur vs type de site | promeos-seed |
| promeos-enedis | Impact sur shadow billing | promeos-billing |
| promeos-energy-market | Modèle de pricing dans contrat cadre | energy-contracts-b2b |
| promeos-energy-market | NEBCO / effacement | energy-flexibility-dr |
| energy-contracts-b2b | Simulation CDC → stratégie | promeos-energy-market |
| energy-contracts-b2b | Données PRM/PCE pour annexe site | promeos-enedis |
| energy-flexibility-dr | Potentiel HP→HC par archétype | promeos-energy-fundamentals |
| energy-flexibility-dr | BACS classe C pour pilotage | promeos-regulatory |
| energy-autoconsommation | APER obligations parking/toiture | promeos-regulatory |
| energy-autoconsommation | Dimensionnement vs profil site | promeos-seed |
| energy-france-veille | TURPE 7 détail grilles | promeos-billing (references/turpe7-grilles.md) |
| energy-france-veille | Impact sur scoring conformité | promeos-regulatory |
| promeos-seed | Archétypes de consommation | promeos-energy-fundamentals (references/archetypes-signatures.md) |

## Combinaisons fréquentes (>1 skill par tâche)

| Tâche | Skills combinés |
|---|---|
| Vérifier une facture EDF | billing + energy-fundamentals + enedis |
| Calculer le score conformité d'un site | regulatory + architecture + energy-fundamentals |
| Recommander un type de contrat | energy-market + contracts-b2b + energy-fundamentals |
| Implémenter le connecteur Enedis Sprint 1 | enedis + architecture |
| Optimiser HP/HC d'un site | energy-flexibility-dr + energy-fundamentals + billing |
| Évaluer le potentiel PV d'un parking | energy-autoconsommation + regulatory |
| Seeder un nouveau site démo | seed + energy-fundamentals |
| Mettre à jour les tarifs réglementaires | billing + energy-france-veille |
