---
name: promeos-iso50001-sme
description: >
  Expert ISO 50001 et Système de Management de l'Énergie.
  Structure SMÉ, audit obligatoire, CUSUM, indicateurs,
  certification, deadlines audit 11/10/2026 et SMÉ 11/10/2027.
version: 1.0.0
tags: [iso50001, sme, audit, certification, cusum, management]
---

# ISO 50001 & SMÉ — Expert PROMEOS

## 1. Contexte Réglementaire

### Loi n°2025-391 du 30 avril 2025 (DDADUE)
- **Audit énergétique** obligatoire si conso > 2.75 GWh/an
  (au niveau Organisation — personne morale)
- **SMÉ ISO 50001** obligatoire si conso > 23.6 GWh/an

### Deadlines (ATTENTION — deux dates différentes)
| Obligation | Seuil | Deadline |
|-----------|-------|----------|
| Audit énergétique | > 2.75 GWh/an | **11 octobre 2026** |
| SMÉ ISO 50001 | > 23.6 GWh/an | **11 octobre 2027** |

> **ERRATUM** : Le document initial indiquait 2026 pour les deux.
> En réalité la loi DDADUE accorde un an de plus pour la mise en
> place du SMÉ (2027). L'audit seul est exigé dès 2026.

- Périodicité audit : tous les 4 ans
- Évaluation au niveau Organisation entière, jamais par site seul

### Qui est concerné ?
Calcul à faire sur toute la consommation de la personne morale :
```python
# Dans PROMEOS : évaluation org-level
total_conso = sum(site.conso_annuelle for site in org.sites)
if total_conso > 2.75e6:  # kWh = 2.75 GWh
    trigger_audit = True       # Deadline : 11/10/2026
if total_conso > 23.6e6:  # kWh = 23.6 GWh
    trigger_sme = True         # Deadline : 11/10/2027
```

## 2. Structure ISO 50001:2018

### Les 10 clauses
| Clause | Titre | Contenu clé |
|--------|-------|-------------|
| 4 | Contexte | Parties prenantes, périmètre SMÉ |
| 5 | Leadership | Engagement direction, politique énergie |
| 6 | Planification | Revue énergétique, objectifs, USÉ |
| 7 | Support | Ressources, compétences, communication |
| 8 | Réalisation | Plans d'action, achat, conception |
| 9 | Évaluation | Mesure, audit interne, revue direction |
| 10 | Amélioration | Non-conformités, amélioration continue |

### Éléments clés à implémenter dans PROMEOS

#### Revue Énergétique (Clause 6.3)
- Analyse des usages significatifs d'énergie (USÉ)
- Identification des leviers d'amélioration
- Établissement des baselines

#### IÉEs (Indicateurs d'Efficacité Énergétique)
```
IÉE = Consommation réelle / Facteur pertinent
Ex: kWh/m², kWh/occupant, kWh/tonne produite
```

#### Plans d'Action (Clause 6.2)
- Objectifs SMART par USÉ
- Responsable, délai, ressources, méthode de vérification
- Traçabilité dans PROMEOS Action Center

## 3. CUSUM — Détection de Dérive

### Formule
```python
# Cumulative Sum Control Chart
baseline = calcul_baseline(conso_historique)  # Ex: régression sur 2 ans

def cusum(mesures, baseline, k=0.5, h=5):
    """
    k = valeur de référence (slack parameter)
    h = seuil de détection
    """
    S_pos, S_neg = 0, 0
    alertes = []
    for i, (mesuree, ref) in enumerate(zip(mesures, baseline)):
        ecart = mesuree - ref
        S_pos = max(0, S_pos + ecart - k)
        S_neg = max(0, S_neg - ecart - k)
        if S_pos > h or S_neg > h:
            alertes.append({"index": i, "type": "derive", "valeur": ecart})
            S_pos, S_neg = 0, 0  # Reset après alerte
    return alertes
```

### Interprétation PROMEOS
- S_pos croissant — surconsommation progressive (dérive positive)
- S_neg croissant — sous-consommation (panne capteur ou économies)
- Seuil h : calibrer à 2-3 semaines de dérive normale

## 4. Audit Énergétique Réglementaire

### Contenu obligatoire (arrêté du 24/11/2014 modifié)
1. Analyse des consommations par vecteur et usage
2. Description des bâtiments et installations
3. Identification des gisements d'économies
4. Analyse coûts/bénéfices des actions
5. Plan d'action priorisé avec ROI

### Auditeur qualifié
- Certification COFRAC ou équivalent
- Indépendance vis-à-vis du client
- Expérience secteur concerné

### Module Audit PROMEOS
- Pré-audit automatisé (données PROMEOS — rapport draft)
- Identification automatique des USÉs
- Calcul gisements par site et type d'action
- Export rapport PDF format réglementaire
- Traçabilité 4 ans

## 5. Certification ISO 50001

### Étapes
1. Diagnostic gap (PROMEOS génère automatiquement)
2. Mise en place SMÉ (6-12 mois)
3. Audit à blanc interne
4. Audit de certification (organisme accrédité)
5. Surveillance annuelle
6. Renouvellement tous les 3 ans

### Organismes certificateurs France
AFNOR Certification, Bureau Veritas, SGS, DNV, Intertek

### Valeur PROMEOS
- Préparer 80% du dossier SMÉ automatiquement
- Générer la revue énergétique depuis les données Enedis
- Tracker les actions et leur vérification
- Alerter avant les audits de surveillance

## 6. Intégration dans le Score Conformité

```python
# Source canonique poids : backend/regops/scoring.py + engine.py
# ─── Sans Audit/SMÉ (défaut) ───
SCORING_DEFAULT = {
    "DT":   0.45,
    "BACS": 0.30,
    "APER": 0.25,
}
# Source : regs.yaml → scoring_profile.json

# ─── Avec Audit/SMÉ (composite) ───
# Activé si conso org > 2.75 GWh
SCORING_WITH_AUDIT = {
    "DT":    0.39,
    "BACS":  0.28,
    "APER":  0.17,
    "AUDIT": 0.16,
}
# Source : engine.py → compliance_score_service (ligne ~120)
# Formule : composite = (raw_score × 0.84) + (audit_score × 0.16)
```
