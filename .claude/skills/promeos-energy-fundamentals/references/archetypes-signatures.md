# Archétypes et signatures de charge — Référence détaillée

Source: Deep research PROMEOS + ADEME/OID/Cerema

## Table des archétypes

| Archétype | kWh/m²/an | Usages dominants | Base load | Signature |
|---|---|---|---|---|
| BUREAU_STANDARD | 150-250 (moy: 180) | CVC 45-55%, Éclairage 20-25%, IT 15-20% | 10-15% nuit | Ramp-up matin, plateau jour, ramp-down soir |
| COMMERCE_ALIMENTAIRE | 400-800 (moy: 600) | Froid 35-45%, Éclairage 20-25%, CVC 15-20% | 40-50% (froid 24/7) | Stable hors horaires, pic ouverture |
| ENSEIGNEMENT | 80-130 | CVC 40-50%, Éclairage 25-30% | 5-10% | Creux vacances scolaires, relance matin |
| HOTEL_HEBERGEMENT | 180-280 | CVC 30-40%, ECS 20-25%, Cuisines 15% | 35-40% | 24/7, pic matin (ECS), pic soir |
| LOGISTIQUE_SEC | 30-70 | Éclairage 50-60%, Recharge engins 15-20% | 5-10% | Rectangulaire (horaires équipes) |
| SANTE_HOPITAL | 200-350 | CVC 35-40%, Équipements techniques 25-30% | 50-60% | 24/7, base très élevée, peu de variation |
| DATA_CENTER | 2000-5000 | IT 60-70%, Refroidissement 25-35% | 85-95% | Quasi-constant, corrélation T° sur cooling |
| RESTAURATION | 150-300 | Cuisson 30-40%, Froid 20-25%, Ventilation 20% | 15-20% | Pics midi et/ou soir, ventilation prolongée |

## Dérives courantes par archétype

| Archétype | Symptôme | Hypothèse | Data requise | Action | ICE |
|---|---|---|---|---|---|
| Bureaux | Base load nuit élevé | IT/serveurs, CVC en marche | CDC 30min + calendrier + T° | Réglage horaires CVC/éclairage | 8/10 |
| Bureaux | Éclairage > 30% en inoccupation | Temporisations, détecteurs HS | CDC + occupation | Recalibrer détecteurs | 7/10 |
| Commerce | Pic après fermeture | Vitrines, ventilation, portes | CDC + horaires | Règles fermeture auto | 7/10 |
| Enseignement | Chauffage actif vacances | Programmation défaillante | CDC + calendrier vacances + T° | Ajuster réduits/relances | 7/10 |
| Hôtel | ECS disproportionnée | Fuites, recirculation | CDC + T° ECS + occupation | Audit circuit ECS | 6/10 |
| Data center | Hausse été disproportionnée | Refroidissement inefficace | T° + PUE + IT load | Ajuster consignes, free-cooling | 6/10 |
| Logistique | Éclairage hors horaires | Pas de détection | CDC + horaires | Détecteurs + zonage | 7/10 |

## Profils de recharge IRVE

Profil non piloté: bosse 17h-21h (retour travail)
Profil smart charging: charge déplacée vers HC nocturnes (22h-6h)
Profil solaire: charge 11h-14h (HC méridiennes si disponible)
Gain smart charging vs non piloté: 20-40% économie sur la facture IRVE
