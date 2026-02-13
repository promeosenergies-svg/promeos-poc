# BILLING CONCEPTS — PROMEOS Bill Intelligence

**Date**: 2026-02-13
**Source**: `app/bill_intelligence/domain.py` (BillingConcept enum + ConceptAllocation)

---

## 1. Taxonomie des concepts

Chaque ligne de facture energie est allouee a un **concept de facturation**.
L'allocation est deterministe (component_type → concept) avec fallback regex sur le libelle.

| Concept | Code | Description | ComponentTypes mappes |
|---------|------|-------------|----------------------|
| **Fourniture** | `fourniture` | Energie consommee (HP, HC, base, pointe, HPH/HCH/HPE/HCE) | conso_hp, conso_hc, conso_base, conso_pointe, conso_hph, conso_hch, conso_hpe, conso_hce, terme_variable |
| **Acheminement** | `acheminement` | Transport reseau (TURPE/ATRD) | turpe_fixe, turpe_puissance, turpe_energie |
| **Abonnement** | `abonnement` | Prime fixe / abonnement | abonnement, terme_fixe |
| **Taxes & Contributions** | `taxes` | Taxes reglementees | cta, accise, cee |
| **TVA** | `tva` | TVA reduite (5.5%) et normale (20%) | tva_reduite, tva_normale |
| **Capacite** | `capacite` | Depassements et penalites reseau | depassement_puissance, reactive |
| **Ajustement** | `ajustement` | Regularisations et corrections | prorata, regularisation, remise |
| **Penalite** | `penalite` | Penalites contractuelles | penalite |
| **Autre** | `autre` | Non classe | autre |

---

## 2. Logique d'allocation

### Priorite 1 : Mapping direct (confidence = 1.0)

Si `component_type` est connu (different de `autre`), le concept est mappe directement via `_COMPONENT_CONCEPT_MAP` dans `json_parser.py`.

### Priorite 2 : Regex sur libelle (confidence = 0.70-0.90)

Si `component_type == autre`, le moteur applique des regles regex sur le `label` :

| Pattern | Concept | Confidence |
|---------|---------|------------|
| `abonnement\|prime fixe\|souscri` | abonnement | 0.85 |
| `consommation\|energie\|kwh\|heure` | fourniture | 0.80 |
| `turpe\|acheminement\|soutirage` | acheminement | 0.85 |
| `accise\|cspe\|ticfe\|taxe\|cta` | taxes | 0.85 |
| `tva` | tva | 0.90 |
| `depassement\|reactive` | capacite | 0.80 |
| `regularis\|prorata\|remise` | ajustement | 0.75 |
| `penalite\|indemnit` | penalite | 0.80 |

### Priorite 3 : Fallback (confidence = 0.50)

Tout composant non reconnu reçoit `concept_id=autre`, `confidence=0.50`.

---

## 3. Modele de donnees

### Domain layer (dataclass)

```python
@dataclass
class ConceptAllocation:
    concept_id: str          # BillingConcept value
    confidence: float        # 0.0-1.0
    matched_rules: List[str] # ex: ["type:conso_hp"] ou ["label_regex:..."]
```

### Persistence layer (SQLAlchemy)

```
concept_allocations
  id                INTEGER PK
  invoice_line_id   FK -> energy_invoice_lines.id
  concept_id        VARCHAR(50) NOT NULL
  confidence        FLOAT NOT NULL DEFAULT 1.0
  matched_rules_json TEXT
  created_at        DATETIME
  updated_at        DATETIME
```

---

## 4. Usage dans le rapport

Le rapport HTML et JSON incluent :
- Colonne **Concept** et **Conf.** dans le tableau des composantes
- Section **Allocation par concept** : ventilation HT par concept
- Champ `concept_allocations` dans la reponse JSON de l'endpoint `/api/bill/audit/{id}`
