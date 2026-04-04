---
name: promeos-enedis
description: "Connecteurs données énergie France : Enedis SGE, DataConnect API v5, GRDF ADICT, Linky, Gazpar, flux R6X/F12/F15/C12, courbes de charge CDC 30min/10min, consentement RGPD, PRM/PDL/PCE, segments C1-C5, MDA/MDE, profils types, rate limits. Utiliser ce skill dès qu'il est question de données Enedis, GRDF, courbes de charge, DataConnect OAuth2, API Enedis, PRM, PDL, PCE, segments compteur, consentement, ou tout accès aux données de comptage France."
---

# PROMEOS Enedis & GRDF — Connecteurs

## Routing

| Contexte | Fichier |
|---|---|
| Webservices SGE, flux R4X/R6X, prestations F160/F300 | `references/sge-webservices.md` |
| Tout le reste (DataConnect, GRDF, consentement) | Ce SKILL.md suffit |

## Proactive triggers

- Token Enedis expiré (401) sans refresh → "Le token DataConnect est expiré. Vérifier le refresh automatique."
- PRM avec < 14 chiffres → "Format PRM invalide. Un PRM doit contenir exactement 14 chiffres."
- Consentement > 2.5 ans → "Consentement DataConnect proche de l'expiration (max 3 ans). Planifier le renouvellement."
- CDC avec trous > 24h → "Données manquantes dans la courbe de charge. Vérifier la connexion Enedis."

## Segments compteur — détail

| Segment | Tension | Puissance | Données | Résolution | Canal | Compteur |
|---|---|---|---|---|---|---|
| C1 | HTB | >10MW | CDC | 10min | SGE SOAP | Télérelevé |
| C2 | HTA | 250kW-10MW | CDC | 10min | SGE SOAP | Télérelevé |
| C3 | HTA | 36kVA-250kW | CDC | 10min | SGE SOAP | Télérelevé |
| C4 | BT | >36kVA | CDC | 10min | SGE SOAP | Télérelevé |
| C5 | BT | ≤36kVA | CDC Linky | 30min | DataConnect REST | Linky |

Accès tiers 10min sur 24 mois (CRE 2025-162). C1-C4 disponible historique jusqu'à 36 mois.

## DataConnect (C5 Linky) — détail

REST API v5, OAuth2 Authorization Code Flow.

### Endpoints disponibles

| Endpoint | Données | Résolution | Historique |
|---|---|---|---|
| daily_consumption | kWh/jour | Journalier | 36 mois |
| consumption_load_curve | W par pas | 30min | 24 mois |
| daily_production | kWh/jour | Journalier | 36 mois |
| production_load_curve | W par pas | 30min | 24 mois |
| consumption_max_power | kVA max | Journalier | 24 mois |
| identity | Titulaire | — | Actuel |
| contact_data | Adresse, contact | — | Actuel |
| contracts | Option tarifaire, puissance | — | Actuel |

### Cycle consentement (RGPD)

1. Redirect vers portail Enedis (URL paramétrable par environnement)
2. User consent sur Enedis.fr (affichage PRM + durée + périmètre)
3. Callback avec authorization code → échange tokens
4. Access token (1h) + refresh token (auto-renouvellement)
5. Durée consentement : **3 ans max** (renouvelable par le client)
6. Révocation possible à tout moment par le client sur Enedis.fr

### Rate limits & quotas

| Niveau | Limite | Action |
|---|---|---|
| Par token | 50 appels/min | Retry-after header |
| Par PRM | 5 appels/min | Queue côté PROMEOS |
| Global (application) | 1000 appels/heure | Circuit breaker |
| Données historiques | 1 appel = max 7 jours | Pagination requise |

### Gestion erreurs

| Code HTTP | Signification | Action PROMEOS |
|---|---|---|
| 401 | Token expiré | Refresh automatique |
| 403 | Consentement révoqué | Notification user + désactivation PRM |
| 404 | PRM inconnu | Vérification registre |
| 429 | Rate limit | Retry avec backoff exponentiel (1s, 2s, 4s, max 30s) |
| 500/503 | Erreur Enedis | Retry ×3 puis alerte monitoring |

## SGE (C1-C4) — détail

SOAP/XML, certificat X.509 client, infrastructure sécurisée.

### Services fonctionnels

| Service | Code | Contenu |
|---|---|---|
| SF1 | Consultation technique | Données contractuelles PRM, puissance, option |
| SF2 | Mesures | CDC 10min, index, courbes de charge |
| SF3 | Données en masse | Export bulk multi-PRM |

### Chiffrement mesures

AES-128-CBC. Clé de déchiffrement par PRM, fournie lors de l'habilitation.
⚠️ Données de mesure chiffrées au repos et en transit.

### Flux échangés

| Flux | Contenu | Format | Fréquence |
|---|---|---|---|
| R6X | Mesures CDC | JSON/XML | J+1 |
| F12 | Facturation acheminement | XML | Mensuel |
| F15 | Relevé résiduel TURPE 7 | XML | Mensuel |
| C12 | Facture client final | XML | Mensuel |
| X12 | Suivi affaire (switching) | XML | Événementiel |
| R151 | Données contractuelles | XML | Événementiel |

Documentation : `docs/base_documentaire/enedis/` (46 fichiers, 32MB).

## MDA/MDE (Marché de Données Agrégées)

Données agrégées par maille (commune, IRIS, département) sans consentement individuel.
Utile pour benchmark, analyse de portefeuille, prospection.
Accès via Open Data Enedis (data.enedis.fr) ou API spécifique (habilitation).

| Donnée | Granularité | Usage PROMEOS |
|---|---|---|
| Consommation par commune | Annuel, par secteur | Benchmark patrimoine |
| Profils types (P1-P6) | 30min, national | Estimation conso si pas de CDC |
| Taux Linky | Commune | Éligibilité DataConnect |

## Profils types Enedis (profilage)

Pour les sites sans CDC (non Linky, non télérelevé), Enedis utilise des profils types :

| Profil | Catégorie | Usage |
|---|---|---|
| RES1/RES2 | Résidentiel | Base / HP-HC |
| PRO1/PRO2 | Professionnel | Base / HP-HC |
| ENT1-ENT4 | Entreprise | Par tranche puissance |

PROMEOS utilise les profils pour l'estimation avant CDC réel disponible.

## GRDF ADICT — détail

REST API, OAuth2 Client Credentials + consentement explicite.
Consommation journalière gaz (Gazpar) + index.
PCE = 14 chiffres (Point de Comptage et d'Estimation).
Historique : 36 mois journalier.
Données : m³ (volume mesuré) → MWh PCS (conversion via coefficient thermique, fourni par GRDF).
⚠️ Coefficient thermique variable par zone et par mois (11.2-12.8 kWh/m³ selon composition gaz).

## Identifiants — validation

- **PRM/PDL** (électricité) = 14 chiffres, commence par 0 ou 1. Regex: `^[01]\d{13}$`
- **PCE** (gaz) = 14 chiffres. Regex: `^\d{14}$`
- Validation stricte côté backend. Jamais de PRM/PCE partiels en DB.

## Plan implémentation (3 sprints)

Sprint 1: `backend/enedis/` module + AES décrypteur + parsers SF2/SF3.
Sprint 2: DataConnect OAuth2 flow + consent lifecycle + UI consentement.
Sprint 3: Live API client + error catalog + R6X parsers + retry/circuit breaker.

## Règles non-négociables

- Consentement obligatoire avant tout accès (RGPD art.6)
- Tokens chiffrés en DB (Fernet ou AES-256), jamais en clair/logs
- PRM/PCE = 14 chiffres, validation stricte regex
- Horodatage UTC interne, Europe/Paris en affichage
- Données CDC = pas de cache >24h (fraîcheur)
- Logs d'accès API horodatés pour audit CNIL
- Retry avec backoff exponentiel, circuit breaker après 3 échecs consécutifs
