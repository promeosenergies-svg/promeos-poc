# SGE v25.6 — Webservices & Flux de données

Source: Enedis Homologation Session Type 1 SGE v25.6 C2C4, `docs/base_documentaire/enedis/` (46 fichiers, 32MB)

## Webservices disponibles

| Webservice | Segments | Données | Profondeur max |
|---|---|---|---|
| CommandeAccesDonneesMesures V1.0 | C1-C5, P1-P4 | CDC, index, Pmax, énergie quotidienne | 36 mois (index), 24 mois/7j (CDC) |
| ConsultationMesures V1.1 | C2-C5 | Historique conso par classe temporelle | 36 mois |
| CommandeCollectePublicationMesures V3.0 | C2-C4, P1-P3 | Publication récurrente index J+1 | Récurrent |
| CommandeHistoriqueDonneesMesuresFines V1.0 | C1-C4, P1-P3 | Historique courbes fines | 24 mois |
| CommandeArretServiceSouscritMesures V1 | Tous | Arrêt service souscrit | — |

## Limites par demande (CommandeHistoriqueDonneesMesuresFines)

| Type de données | Flux résultat | Max PRM par demande (JSON B2B) | Max PRM (CSV portail) |
|---|---|---|---|
| Courbe de charge | R63 | 1,500 | 100 |
| Index | R64 | 1,500 | 100 |
| Énergies quotidiennes | R65 | 10,000 | 1,000 |

## Flux publiés au fil de l'eau (sans demande)

| Flux | Segments | Contenu | Fréquence |
|---|---|---|---|
| R15 (C5) / R17 (C2-C4) | Tous | Relevés cycliques réels et estimés | Cyclique |
| R10/R10A | C2-C4 | CDC M-1 soutirage 10min | Mensuel |
| R50 | C5 Linky | CDC 30min | Récurrent |
| R4X | C1-C4 | CDC puissance active/réactive/tension | Récurrent |
| R151/R171/R172 | Tous | Index J+1 + données compteur | J+1 |
| IFJ (Infra-Journalier) | C1-C4 | CDC + tension + index + tarification dynamique | Infra-journalier |

## Prestations SGE courantes

| Code | Prestation | Canaux | Flux associé |
|---|---|---|---|
| F160 | Modification formule tarifaire acheminement | Portail + B2B | X12 |
| F175 | Modification comptage sans impact FTA | Portail | — |
| F190 | Enregistrements de puissance (optimisation tarifaire) | Portail | — |
| F300/P300 | Publication récurrente CDC | Portail + WS | R50 (C5) / R4X (C1-C4) |
| F305A/P305A | Publication récurrente index J+1 | Portail + WS | R151/R171/R172 |
| F330 | Relevé transitoire CDC par GSM | Portail | — |
| F360 | Relevé spécial | Portail | — |
| M023 | Historique CDC + index commandable | Portail + WS | Flux résultat |

## Homologation fournisseur (5 sessions)

1. Type 1: Présentation règles et processus SGE
2. Type 2: Prise en main portail distributeur
3. Type 3: Spécifications techniques échanges SI (API)
4. Type 4: Tests inter-opérabilité SI
5. Type 5: Tests étendus (recette complète)

## Règles d'accès aux données

- FT (Fournisseur Titulaire): accès direct aux flux récurrents
- FNT (Fournisseur Non Titulaire): accès soumis à accord client
- Tiers autorisé: accès via consentement explicite (RGPD)
- Compteurs SAPHIR, IC4Q, PME-PMI: compatibles transmission index quotidiens
- Données soutirage ET injection possibles sur même PRM (ACC)
