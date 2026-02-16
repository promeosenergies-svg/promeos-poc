# PROMEOS — Importer Patrimoine (VNext)

Guide complet du pipeline d'import de patrimoine immobilier.

## Modes d'import

| Mode | Description | Cas d'usage |
|------|-------------|-------------|
| `express` | Upload CSV/Excel → activation directe | Premiere integration rapide |
| `import` | Upload → quality gate → corrections → activation | Import standard avec validation |
| `assiste` | Extraction depuis factures/IA → staging | Accompagnement assisté |
| `demo` | Donnees de demonstration pre-chargees | Evaluation / POC |

## Colonnes du template

Le template accepte 14 colonnes. Seule `nom` est obligatoire.

| Colonne | Label | Obligatoire | Exemple | Synonymes acceptes |
|---------|-------|:-----------:|---------|-------------------|
| `nom` | Nom du site | Oui | Mairie Principale | name, site_name, designation, libelle |
| `adresse` | Adresse | Non | 1 place de la Republique | address, addr, rue, street |
| `code_postal` | Code postal | Non | 75001 | cp, postal_code, zip, zipcode |
| `ville` | Ville | Non | Paris | city, commune, localite, town |
| `surface_m2` | Surface (m2) | Non | 1200 | surface, area, superficie, m2 |
| `type` | Type de site | Non | bureau | type_site, usage, categorie, activite |
| `naf_code` | Code NAF | Non | 84.11Z | naf, code_naf, ape, code_ape |
| `siren` | SIREN | Non | 443061841 | n_siren, num_siren |
| `siret` | SIRET | Non | 44306184100015 | n_siret, num_siret, siret_site |
| `energy_type` | Type energie | Non | elec | energie, energy, fluide, vecteur |
| `delivery_code` | Code PRM/PDL/PCE | Non | 12345678901234 | meter_id, prm, pdl, pce, point_livraison |
| `numero_serie` | N° serie compteur | Non | CPT-001 | serial, serial_number, num_compteur |
| `type_compteur` | Type compteur | Non | electricite | meter_type, compteur_type |
| `puissance_kw` | Puissance (kW) | Non | 36 | puissance, power, kva |

### Detection automatique

- **Delimiter** : auto-detecte (virgule `,`, point-virgule `;`, tabulation)
- **Encoding** : UTF-8, UTF-8 BOM, Latin-1 (auto-detecte)
- **Synonymes** : les noms de colonnes sont normalises (accents, espaces, casse) et mappes automatiquement
- **Regroupement** : les lignes avec le meme `nom` sont regroupees dans un seul site

## Endpoints API

### Template

| Methode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/patrimoine/import/template?format=xlsx` | Telecharger le template (xlsx par defaut, ou csv) |
| `GET` | `/api/patrimoine/import/template/columns` | Metadata des colonnes (label, required, synonymes) |

### Import

| Methode | URL | Description |
|---------|-----|-------------|
| `POST` | `/api/patrimoine/staging/import` | Upload CSV/Excel → staging pipeline |
| `POST` | `/api/patrimoine/staging/import-invoices` | Import depuis metadata factures |

**Import CSV — Exemple curl :**
```bash
curl -X POST http://localhost:8000/api/patrimoine/staging/import \
  -F "file=@patrimoine.csv" \
  -F "mode=import"
```

**Reponse :**
```json
{
  "batch_id": 42,
  "duplicate": false,
  "sites_count": 10,
  "compteurs_count": 15,
  "parse_errors": [],
  "mapping": {
    "mapping": {"PRM": "delivery_code", "CP": "code_postal"},
    "warnings": [{"header": "custom_col", "message": "Column 'custom_col' not recognized"}],
    "encoding": "utf-8",
    "delimiter": ";"
  }
}
```

### Quality Gate & Corrections

| Methode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/patrimoine/staging/{id}/summary` | Stats du batch (sites, compteurs, findings) |
| `GET` | `/api/patrimoine/staging/{id}/rows?page=1&page_size=50&q=&status=` | Sites + compteurs pagines |
| `GET` | `/api/patrimoine/staging/{id}/issues?severity=&resolved=` | Findings qualite filtres |
| `POST` | `/api/patrimoine/staging/{id}/validate` | Executer le quality gate |
| `PUT` | `/api/patrimoine/staging/{id}/fix` | Appliquer une correction |
| `PUT` | `/api/patrimoine/staging/{id}/fix/bulk` | Corrections en lot |
| `POST` | `/api/patrimoine/staging/{id}/autofix` | Auto-corrections sures |
| `DELETE` | `/api/patrimoine/staging/{id}` | Abandonner le batch |

### Activation & Resultats

| Methode | URL | Description |
|---------|-----|-------------|
| `POST` | `/api/patrimoine/staging/{id}/activate` | Activer → creer entites reelles |
| `GET` | `/api/patrimoine/staging/{id}/result` | Resultat post-activation |
| `GET` | `/api/patrimoine/staging/{id}/export/report.csv` | Export rapport CSV |

### Points de livraison

| Methode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/patrimoine/sites/{id}/delivery-points` | Liste des PRM/PCE actifs d'un site |

## Regles du Quality Gate

11 regles deterministes, classees par severite :

| Rule ID | Severite | Description |
|---------|----------|-------------|
| `dup_site_address` | BLOCKING | Sites avec meme adresse + code postal |
| `dup_meter` | BLOCKING | Compteurs avec meme numero de serie |
| `orphan_meter` | BLOCKING | Compteur sans site rattache |
| `incomplete_site` | WARNING | Site sans adresse |
| `missing_entity` | WARNING | Pas d'entite juridique dans le batch |
| `invalid_postal_code` | WARNING | Code postal invalide (pas 5 chiffres) |
| `invalid_siret` | WARNING | SIRET invalide (pas 14 chiffres) |
| `missing_meter_type` | INFO | Compteur sans type (elec/gaz) |
| `missing_surface` | INFO | Site sans surface |
| `suspicious_surface` | WARNING | Surface anormale (< 10 ou > 100 000 m2) |
| `missing_energy_type` | INFO | Type d'energie non renseigne |

### Auto-corrections (autofix)

L'endpoint `/autofix` applique 4 corrections automatiques sures :

1. **Trim whitespace** : espaces en debut/fin de tous les champs texte
2. **Pad code postal** : `1234` → `01234` (zero-fill 5 digits)
3. **Normaliser type compteur** : `Elec` → `electricite`, `Gaz` → `gaz`
4. **Skip compteurs vides** : compteur sans meter_id ET sans numero_serie → marque comme `skip`

## Pipeline complet

```
1. Telecharger template    GET  /import/template
2. Remplir le fichier      (Excel ou CSV)
3. Upload                  POST /staging/import
4. Consulter les donnees   GET  /staging/{id}/rows
5. Lancer quality gate     POST /staging/{id}/validate
6. Corriger (auto)         POST /staging/{id}/autofix
7. Corriger (manuel)       PUT  /staging/{id}/fix/bulk
8. Re-valider              POST /staging/{id}/validate
9. Activer                 POST /staging/{id}/activate
10. Consulter resultat     GET  /staging/{id}/result
11. Telecharger rapport    GET  /staging/{id}/export/report.csv
```

## DeliveryPoints (PRM/PCE)

A l'activation, chaque `meter_id` (ou `delivery_code`) cree automatiquement un `DeliveryPoint` :

- **PRM** (14 chiffres, electricite) → `DeliveryPoint(energy_type=elec)`
- **PCE** (14 chiffres, gaz) → `DeliveryPoint(energy_type=gaz)`
- Le `Compteur` est automatiquement lie au `DeliveryPoint` via `delivery_point_id`
- Deduplication : 2 compteurs avec le meme meter_id sur le meme site → 1 seul DeliveryPoint

## Troubleshooting

### "File already imported"
Le systeme detecte les doublons par hash SHA-256 du contenu. Si le meme fichier est re-uploade, le batch existant est retourne. Pour re-importer, modifiez le fichier ou abandonnez l'ancien batch.

### "Champ 'nom' manquant ou vide"
La colonne `nom` est la seule obligatoire. Verifiez que votre CSV contient bien une colonne `nom` (ou un synonyme : `name`, `site_name`, `designation`).

### Colonnes non reconnues
Les colonnes non reconnues sont ignorees avec un warning dans la reponse. Consultez le tableau des synonymes ci-dessus ou telechargez le template officiel.

### Erreurs de format
- **Surface** : accepte virgule ou point (`1200,5` → `1200.5`)
- **Puissance** : idem
- **SIRET** : espaces et tirets sont automatiquement supprimes
- **Code postal** : auto-pade a 5 chiffres

### Compteurs non crees
Un compteur n'est cree que s'il a au moins `numero_serie` ou `meter_id`. Les lignes avec les deux vides sont ignorees (ou marquees `skip` par autofix).
