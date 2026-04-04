# 30 règles d'anomalie prêtes à implémenter

Source: Deep research PROMEOS (matrice décision/service)

## Règles de consommation

| # | Règle | Seuil défaut | Gravité | Archétypes |
|---|---|---|---|---|
| 1 | Base load nuit > X% de la moyenne jour | 25% bureaux, 50% data center | MEDIUM | Tous |
| 2 | Consommation week-end > X% de la semaine | 30% bureaux, 80% hôpital | MEDIUM | Bureaux, commerce |
| 3 | Conso vacances scolaires > X% période scolaire | 40% | HIGH | Enseignement |
| 4 | Pic après fermeture > X% pic ouvert | 20% | MEDIUM | Commerce, bureaux |
| 5 | Conso mois M > +15% vs M-12 (hors DJU) | 15% | HIGH | Tous |
| 6 | Conso nocturne croissante sur 3 mois | Tendance | LOW | Tous |
| 7 | Ratio HP/HC > 80% (potentiel report) | 80% | LOW | Bureaux, logistique |

## Règles de puissance

| # | Règle | Seuil | Gravité |
|---|---|---|---|
| 8 | Pmax atteinte > 90% puissance souscrite | 90% | HIGH |
| 9 | Pmax atteinte < 50% puissance souscrite (surdim) | 50% | MEDIUM |
| 10 | Dépassement puissance souscrite (CMDPS) | >100% | CRITICAL |
| 11 | tan φ > 0.4 (pénalité réactif) | 0.4 | HIGH |
| 12 | Facteur de charge < 0.2 | 0.2 | LOW |

## Règles thermiques (DJU)

| # | Règle | Seuil | Gravité |
|---|---|---|---|
| 13 | Chauffage actif quand T° ext > 18°C | 18°C | MEDIUM |
| 14 | Clim active quand T° ext < 22°C | 22°C | MEDIUM |
| 15 | Sensibilité thermique (pente a) dégradée vs N-1 | +10% | HIGH |
| 16 | Consigne chauffage > 21°C détectée | 21°C | LOW |
| 17 | Simultanéité chaud/froid | Détection CDC | HIGH |

## Règles billing

| # | Règle | Seuil | Gravité |
|---|---|---|---|
| 18 | Écart shadow billing > 2 €/MWh | 2 €/MWh | HIGH |
| 19 | Accise ≠ taux en vigueur | Exact match | HIGH |
| 20 | TURPE version incorrecte vs date facture | Date | HIGH |
| 21 | Puissance facturée ≠ Enedis | Exact match | HIGH |
| 22 | Doublon PRM + période | Exact match | CRITICAL |
| 23 | Régularisation > 50% facture précédente | 50% | MEDIUM |

## Règles conformité

| # | Règle | Seuil | Gravité |
|---|---|---|---|
| 24 | Trajectoire DT hors objectif > 10% | 10% | HIGH |
| 25 | Aucune preuve DT uploadée | 0 docs | MEDIUM |
| 26 | BACS non installé et deadline < 12 mois | Date | HIGH |
| 27 | APER non conforme et parking > 1500m² | Surface | MEDIUM |
| 28 | Audit énergétique non réalisé et deadline < 6 mois | Date | HIGH |

## Règles contrat

| # | Règle | Seuil | Gravité |
|---|---|---|---|
| 29 | Contrat expire dans < 6 mois | J-180 | HIGH |
| 30 | Indexation ARENH sur contrat post-2025 | R12 | CRITICAL |
