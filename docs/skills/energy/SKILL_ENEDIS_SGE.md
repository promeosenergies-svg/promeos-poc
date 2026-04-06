---
name: promeos-enedis-sge
description: >
  Expert API Enedis SGE et DataConnect.
  Protocoles SOAP SF1/SF2/SF3, OAuth2 C5,
  formats XSD, flux données comptage C4/C2.
version: 2.0.0
tags: [enedis, sge, dataconnect, soap, oauth2, c4, c2, c5, comptage]
---

# Connecteur Enedis SGE -- Expert PROMEOS

## 1. Architecture Enedis -- 2 systèmes distincts

### SGE (Système de Gestion des Échanges) -- SOAP
- Protocole : SOAP XML / HTTPS
- Cible : clients C1-C4 (HTB, HTA, BT >36kVA, télérelevés 10min)
- Données : courbes de charge 10min, index, maxima, données contractuelles
- Auth : certificat + habilitation SGE (portail développeur Enedis)
- Specs : `docs/base_documentaire/enedis/` (18+ fichiers, PDFs + XSD)

### DataConnect -- OAuth2 REST
- Protocole : OAuth2 Authorization Code + REST JSON (API v5)
- Cible : clients C5 (BT <=36kVA, Linky, mesurés 30min)
- Données : courbes de charge 30min, index, données contractuelles
- Auth : OAuth2 client_id + client_secret (portail DataHub)
- Consentement client : obligatoire, durée max 3 ans renouvelable

## 2. Segments de comptage -- détail

| Segment | Tension | Puissance | Données | Résolution | Canal | Compteur |
|---------|---------|-----------|---------|-----------|-------|----------|
| C1 | HTB | >10MW | CDC | 10min | SGE SOAP | Télérelevé |
| C2 | HTA | 250kW-10MW | CDC | 10min | SGE SOAP | Télérelevé |
| C3 | HTA | 36kVA-250kW | CDC | 10min | SGE SOAP | Télérelevé |
| C4 | BT | >36kVA | CDC | 10min | SGE SOAP | Télérelevé |
| C5 | BT | <=36kVA | CDC Linky | 30min | DataConnect REST | Linky |

Accès tiers 10min sur 24 mois (CRE délib. 2025-162). C1-C4 historique jusqu'à 36 mois.

## 3. Flux SGE Prioritaires

### SF1 -- Recherche de point
```xml
<rechercherPoint>
  <criteres>
    <numSiret>SIRET</numSiret>
    <adresseInstallation>...</adresseInstallation>
  </criteres>
</rechercherPoint>
```

### SF2 -- Consultation des données contractuelles
- PRM, puissance souscrite, option tarifaire
- Périodes HP/HC, segment tarifaire

### SF3 -- Récupération des courbes de charge (CDC)
- C1-C4 : mesures 10min sur 36 mois max
- Format : XML avec timestamps UTC
- Déchiffrement : AES si données sensibles

## 4. DataConnect (C5 Linky) -- détail

REST API v5, OAuth2 Authorization Code Flow.

### Endpoints principaux
| Endpoint | Données | Résolution | Historique |
|----------|---------|-----------|-----------|
| /metering_data/consumption_load_curve | CDC consommation | 30min | 36 mois |
| /metering_data/daily_consumption | Conso quotidienne | Jour | 36 mois |
| /metering_data/consumption_max_power | Puissance max | Jour | 36 mois |
| /customers/identity | Identité titulaire | - | - |
| /customers/contact_data | Coordonnées | - | - |

### Rate limits DataConnect
- 50 requêtes / 10 secondes par application
- 200 requêtes / minute par PRM

## 5. Architecture Backend PROMEOS (à implémenter)

```
backend/
  enedis/
    __init__.py
    sge_client.py          # Client SOAP SF1/SF2/SF3
    dataconnect_client.py  # Client OAuth2 REST v5
    parsers/
      sf1_parser.py        # Recherche point -> PRM
      sf2_parser.py        # Données contractuelles
      sf3_parser.py        # CDC -> ConsumptionReading
    models/
      staging.py           # Tables staging avant bridge
    bridge.py              # Staging -> Meter unifié
```

## 6. Gestion des erreurs SGE (catalog R6X)

| Code | Description | Action |
|------|-------------|--------|
| R600 | Point inconnu | Vérifier PRM (14 chiffres exactement) |
| R601 | Données non disponibles | Retry J+1 |
| R602 | Période invalide | Vérifier dates (max 36 mois) |
| R605 | Habilitation insuffisante | Contacter Enedis portail développeur |
| R606 | Consentement absent/expiré | Renouveler via DataHub |

## 7. Règles PROMEOS pour ce module

- Toujours explorer `docs/base_documentaire/enedis/` avant de coder
- Staging tables avant insertion dans Meter (bridge.py)
- Idempotence : clé PRM + période de mesure
- Logs structurés sur chaque appel SGE (correlation_id)
- Consentements DataConnect : alerte renouvellement J-30 (max 3 ans)
- Format PRM : exactement 14 chiffres, validation stricte
