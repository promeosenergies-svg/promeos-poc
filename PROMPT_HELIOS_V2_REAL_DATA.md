# PROMPT_HELIOS_V2_REAL_DATA.md
# Sprint : Adosser HELIOS à des données réelles (PRM/PCE)
# Effort estimé : ~2h | Priorité : P1
# MCP plugins requis : Context7, code-review, simplify

---

## Objectif

Modifier le seed HELIOS pour que chaque site de démo soit **adossé à un vrai compteur**
issu du fichier fournisseur SME_FRANCE.xlsx, tout en gardant **100% de la façade démo intacte**
(noms de sites, anomalies, recommandations, courbes CDC synthétiques, scores compliance).

**Principe clé :** Le nom réel du client ne doit JAMAIS apparaître dans l'UI.
HELIOS reste "HELIOS" — seuls les identifiants techniques (PRM/PCE, SIRET, NAF) changent sous le capot.

---

## Phase 0 — Audit read-only (STOP GATE)

```bash
cd /path/to/promeos-poc
git status  # doit être clean
python -m pytest backend/tests/ -q --tb=short 2>&1 | tail -5
npx vitest run --reporter=verbose 2>&1 | tail -10
# Vérifier que tous les tests passent AVANT de toucher quoi que ce soit
```

Identifier les fichiers du seed HELIOS :
```bash
grep -rn "HELIOS\|helios\|Paris Bureaux\|Lyon Bureaux\|Marseille.*cole\|Nice.*tel\|Toulouse.*Entrep" backend/seeds/ backend/config/ --include="*.py" --include="*.yaml" --include="*.json" -l
```

**STOP GATE : Tests verts + fichiers seed identifiés → Go Phase 1**

---

## Phase 1 — Mapping table (constante de référence)

Créer ou modifier `backend/config/helios_real_mapping.py` :

```python
"""
HELIOS V2 — Real PRM/PCE mapping.
Each demo site is backed by a real meter from SME_FRANCE.xlsx.
The display_name shown in UI is ALWAYS the HELIOS facade name.
The real_* fields are NEVER exposed to the frontend.
"""

HELIOS_REAL_MAPPING = {
    "paris_bureaux": {
        # --- FAÇADE HELIOS (inchangé) ---
        "display_name": "Paris Bureaux",
        "display_city": "Paris",
        "display_address": "12 Avenue des Champs-Élysées",  # fictif, garder l'existant
        "helios_car_mwh": 350,
        "surface_m2": 3500,
        # --- DONNÉES RÉELLES (sous le capot) ---
        "real_prm": "30000710966640",
        "real_pdla": "30000710966640",
        "real_siret": "94519566700015",
        "real_siren": "945195667",
        "real_naf": "7010Z",
        "real_naf_label": "Activités des sièges sociaux",
        "real_address": "35 RUE DES JEUNEURS 2ETAGE",
        "real_city": "PARIS",
        "real_cp": "75002",
        "real_car_mwh": 312.357,
        "real_energy": "Electricité",
        "real_profil": None,
        "real_ntr": 2,
        # --- TURPE 7 / technique Enedis (ex contrat_test.xlsx) ---
        "real_pitd": "GD1057",
        "real_categorie": "C4",                    # Segment TURPE
        "real_tension": "BTSUP",                   # BTINF / BTSUP / HTA
        "real_fta": "BTSUPLU4",                    # Formule Tarifaire Acheminement
        "real_profil_distrib": "ENT1",             # Profil client Enedis
        "real_traitement": "MIXTE",                # MIXTE | INDEX | CDC
        "real_compteur_type": 2,                   # 2 = Linky/communicant
        "real_puissance_kva": None,
        "real_cee_eur_mwh": 0.0,
        "real_contrat_debut": "2026-01-01",
        "real_contrat_fin": "2026-12-31",
        "data_source": "sme_real",  # "synthetic" | "sme_real" | "dataconnect_live"
        "car_scale_factor": 350 / 312.357,  # 1.1205 — pour scaler les CDC réelles vers le CAR HELIOS
    },
    "lyon_bureaux": {
        "display_name": "Lyon Bureaux",
        "display_city": "Lyon",
        "display_address": "45 Rue de la République",
        "helios_car_mwh": 120,
        "surface_m2": 1200,
        "real_prm": "19427496304265",
        "real_pdla": "19427496304265",
        "real_siret": "87917746700013",
        "real_siren": "879177467",
        "real_naf": "6910Z",
        "real_naf_label": "Activités juridiques",
        "real_address": "LA MAISON BLANCHE, PARC D ACTIVITE",
        "real_city": "VAUGNERAY",
        "real_cp": "69670",
        "real_car_mwh": 51.761,
        "real_energy": "Electricité",
        "real_profil": None,
        "real_ntr": 1,
        # --- TURPE 7 / technique Enedis ---
        "real_pitd": "GD0136",
        "real_categorie": "C5",
        "real_tension": "BTINF",
        "real_fta": "BTINFCU4",
        "real_profil_distrib": "PRO6",
        "real_traitement": "INDEX",
        "real_compteur_type": 2,
        "real_puissance_kva": 36,                  # kVA souscrite
        "real_cee_eur_mwh": 4.30,
        "real_contrat_debut": "2025-03-01",
        "real_contrat_fin": "2026-12-31",
        "data_source": "sme_real",
        "car_scale_factor": 120 / 51.761,  # 2.318 — gap important, CDC sera scalée
    },
    "marseille_ecole": {
        "display_name": "Marseille École",
        "display_city": "Marseille",
        "display_address": "8 Boulevard Longchamp",
        "helios_car_mwh": 200,
        "surface_m2": 2800,
        "real_prm": "50043806664839",
        "real_pdla": "50043806664839",
        "real_siret": "77555892700023",
        "real_siren": "775558927",
        "real_naf": "8531Z",
        "real_naf_label": "Enseignement secondaire général",
        "real_address": "ECOLE SAINT BRUNO, 10 RUE PIERRE ROCHE",
        "real_city": "MARSEILLE",
        "real_cp": "13004",
        "real_car_mwh": 142.823,
        "real_energy": "Electricité",
        "real_profil": None,
        "real_ntr": 2,
        # --- TURPE 7 / technique Enedis ---
        "real_pitd": "GD0906",
        "real_categorie": "C4",
        "real_tension": "BTSUP",
        "real_fta": "BTSUPCU4",
        "real_profil_distrib": "ENT1",
        "real_traitement": "CDC",                  # ← Mode CDC = courbe de charge 30 min !
        "real_compteur_type": 2,
        "real_puissance_kva": None,
        "real_cee_eur_mwh": 4.03,
        "real_contrat_debut": "2026-01-01",
        "real_contrat_fin": "2027-12-31",
        "data_source": "sme_real",
        "car_scale_factor": 200 / 142.823,  # 1.400
    },
    "nice_hotel": {
        "display_name": "Nice Hôtel",
        "display_city": "Nice",
        "display_address": "23 Promenade des Anglais",
        "helios_car_mwh": 400,
        "surface_m2": 4000,
        "real_prm": "30002591014358",
        "real_pdla": "30002591014358",
        "real_siret": "45182974100029",
        "real_siren": "451829741",
        "real_naf": "5510Z",
        "real_naf_label": "Hôtels et hébergement similaire",
        "real_address": "4 Rue Montaigne",
        "real_city": "CANNES",  # façade garde "Nice"
        "real_cp": "06400",
        "real_car_mwh": 536.4,
        "real_energy": "Electricité",
        "real_profil": None,
        "real_ntr": 7,
        # --- TURPE 7 / technique Enedis ---
        "real_pitd": "GD0922",
        "real_categorie": "C4",
        "real_tension": "BTSUP",
        "real_fta": "BTSUPLU4",
        "real_profil_distrib": "ENT1",
        "real_traitement": "MIXTE",
        "real_compteur_type": 2,
        "real_puissance_kva": None,
        "real_cee_eur_mwh": 4.30,
        "real_contrat_debut": "2026-01-01",
        "real_contrat_fin": "2027-12-31",
        "data_source": "sme_real",
        "car_scale_factor": 400 / 536.4,  # 0.7458 — on réduit les CDC réelles
    },
    "toulouse_entrepot": {
        "display_name": "Toulouse Entrepôt",
        "display_city": "Toulouse",
        "display_address": "Zone Logistique de Sesquières",
        "helios_car_mwh": 500,
        "surface_m2": 6000,
        "real_prm": "50007182872595",
        "real_pdla": "50007182872595",
        "real_siret": "49203278400059",
        "real_siren": "492032784",
        "real_naf": "5210B",
        "real_naf_label": "Entreposage et stockage non frigorifique",
        "real_address": "Lieu-dit Le Carreau",
        "real_city": "LA VERPILLIERE",  # ⚠ dept 38, pas 31 — façade garde "Toulouse"
        "real_cp": "38290",
        "real_car_mwh": 214.15,
        "real_energy": "Electricité",
        "real_profil": None,
        "real_ntr": 2,
        # --- TURPE 7 / technique Enedis — HTA (haute tension) ! ---
        "real_pitd": "GD1089",
        "real_categorie": "C2",                    # ← C2 HTA = segment premium
        "real_tension": "HTA",                     # Haute Tension = vrai entrepôt logistique
        "real_fta": "HTACU5",
        "real_profil_distrib": "Non Profilé",      # HTA = télérelevé obligatoire, pas de profilage
        "real_traitement": "MIXTE",
        "real_compteur_type": 2,
        "real_puissance_kva": None,                # HTA exprimé en kW généralement
        "real_cee_eur_mwh": 0.0,
        "real_contrat_debut": "2026-01-01",
        "real_contrat_fin": "2029-12-31",          # Contrat long (4 ans)
        "data_source": "sme_real",
        "car_scale_factor": 500 / 214.15,  # 2.335 — gap important, CDC sera scalée
    },
}
```

Commit: `feat(seed-p1): Phase 1 — HELIOS real mapping table`

**STOP GATE : Fichier créé, importable, tests toujours verts → Go Phase 2**

---

## Phase 2 — Injection dans le seed existant

Modifier le seed HELIOS existant pour utiliser les `real_prm`/`real_pce` au lieu des PRM fictifs.

### 2.1 Identifier la structure actuelle

```bash
grep -n "prm\|pce\|pdl\|meter\|compteur" backend/seeds/seed_helios*.py | head -30
```

### 2.2 Remplacer les identifiants

Pour chaque site dans le seed :
- Remplacer le PRM/PCE fictif par `HELIOS_REAL_MAPPING[site_key]["real_prm"]` ou `real_pce`
- Remplacer le SIRET par `real_siret`
- **NE PAS TOUCHER** : `display_name`, `display_city`, `display_address`, surface, anomalies, recos

### 2.3 Ajouter le champ `data_source`

Dans le modèle `Site` ou `Meter` (selon la structure) :
```python
# Si le champ n'existe pas, l'ajouter via migration
data_source = Column(String, default="synthetic")  
# Valeurs : "synthetic" | "sme_real" | "dataconnect_live"
```

### 2.4 Garder les CDC synthétiques mais tracer le scale factor

```python
# Dans le seed, au moment de générer les CDC :
# Si data_source == "sme_real", stocker le car_scale_factor
# pour pouvoir transformer les CDC réelles quand DataConnect sera branché
```

Commit: `feat(seed-p2): Phase 2 — inject real PRM/PCE into HELIOS seed`

**STOP GATE : `python -m pytest` + `npx vitest run` → 0 failures → Go Phase 3**

---

## Phase 3 — Source guard : le nom réel ne fuit JAMAIS

### 3.1 Backend guard

Vérifier que les endpoints API ne renvoient JAMAIS les champs `real_*` au frontend :

```python
# Dans le serializer/schema Pydantic du site :
class SiteResponse(BaseModel):
    id: int
    display_name: str
    city: str  # ← display_city, JAMAIS real_city
    address: str  # ← display_address
    # ...
    # JAMAIS : real_address, real_city, real_siret, real_siren
```

### 3.2 Test source guard

```python
# backend/tests/test_helios_privacy.py

def test_real_data_never_in_api_response(client):
    """Les données réelles (nom client, adresse réelle) ne doivent JAMAIS
    apparaître dans les réponses API."""
    
    FORBIDDEN_IN_RESPONSE = [
        "94519566700015",   # SIRET Paris
        "87917746700013",   # SIRET Lyon
        "77555892700023",   # SIRET Marseille
        "45182974100029",   # SIRET Nice (Cannes)
        "49203278400059",   # SIRET Toulouse
        "35 RUE DES JEUNEURS",
        "LA MAISON BLANCHE",
        "ECOLE SAINT BRUNO",
        "4 Rue Montaigne",
        "Lieu-dit Le Carreau",
        "VAUGNERAY",
        "LA VERPILLIERE",
        "945195667",        # SIREN
        "879177467",
        "775558927",
        "451829741",
        "492032784",
    ]
    
    # Tester tous les endpoints qui renvoient des données de site
    for endpoint in ["/api/sites", "/api/sites/1", "/api/cockpit", "/api/patrimoine"]:
        response = client.get(endpoint)
        if response.status_code == 200:
            body = response.text
            for forbidden in FORBIDDEN_IN_RESPONSE:
                assert forbidden not in body, \
                    f"FUITE DONNÉES RÉELLES : '{forbidden}' trouvé dans {endpoint}"
```

### 3.3 Test frontend source guard

```javascript
// frontend/src/tests/helios-privacy.test.js
import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const FORBIDDEN = [
  '94519566700015', '87917746700013', '77555892700023',
  '45182974100029', '49203278400059',
  'RUE DES JEUNEURS', 'MAISON BLANCHE', 'SAINT BRUNO',
  'Rue Montaigne', 'Le Carreau',
  'VAUGNERAY', 'VERPILLIERE',
]

describe('HELIOS Privacy Guard', () => {
  it('real client data never hardcoded in frontend', () => {
    const srcDir = path.resolve(__dirname, '../../src')
    const files = getAllFiles(srcDir, ['.jsx', '.tsx', '.js', '.ts'])
    
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8')
      for (const term of FORBIDDEN) {
        expect(content).not.toContain(term)
      }
    }
  })
})

function getAllFiles(dir, exts) {
  // recursive file walker...
}
```

Commit: `test(seed-p3): Phase 3 — privacy source guard for real HELIOS data`

**STOP GATE : Tests privacy verts + tests existants verts → Go Phase 4**

---

## Phase 4 — Validation visuelle

```bash
# Relancer le seed
python backend/seeds/seed_helios.py

# Vérifier en base
sqlite3 backend/promeos.db "SELECT display_name, city, data_source FROM sites WHERE org_id = (SELECT id FROM organizations WHERE name = 'HELIOS')"
# Attendu : 5 lignes, display_name = noms HELIOS, data_source = 'sme_real'

# Vérifier que les PRM sont bien les vrais
sqlite3 backend/promeos.db "SELECT display_name, prm FROM meters WHERE site_id IN (SELECT id FROM sites WHERE org_id = (SELECT id FROM organizations WHERE name = 'HELIOS'))"
```

Commit: `chore(seed-p4): Phase 4 — HELIOS V2 seed validated`

**STOP GATE : `python -m pytest` + `npx vitest run` → 0 failures**

---

## Phase 5 — README / doc

Mettre à jour `docs/HELIOS_SEED.md` (ou créer) :

```markdown
## HELIOS V2 — Real Data Backing

Depuis V2, chaque site HELIOS est adossé à un vrai compteur :

| Façade           | PRM/PCE réel       | NAF   | CAR réel | Scale |
|------------------|--------------------|-------|----------|-------|
| Paris Bureaux    | 30000710966640     | 7010Z | 312 MWh  | 1.12  |
| Lyon Bureaux     | 19427496304265     | 6910Z | 52 MWh   | 2.32  |
| Marseille École  | 50043806664839     | 8531Z | 143 MWh  | 1.40  |
| Nice Hôtel       | 30002591014358     | 5510Z | 536 MWh  | 0.75  |
| Toulouse Entrepôt| 50007182872595     | 5210B | 214 MWh  | 2.34  |

### Principes
- `display_name` = façade HELIOS (JAMAIS le nom réel du client)
- `data_source` = "sme_real" (passera à "dataconnect_live" quand branché)
- `car_scale_factor` = ratio pour transformer les CDC réelles en CDC HELIOS
- Les anomalies et recommandations restent synthétiques (81 anomalies, 158 recos)
```

Commit: `docs(seed-p5): Phase 5 — HELIOS V2 documentation`

---

## Definition of Done

- [ ] `backend/config/helios_real_mapping.py` créé avec les 5 mappings complets
- [ ] Seed HELIOS utilise les vrais PRM/PCE (vérifiable en base)
- [ ] Champ `data_source = "sme_real"` sur les 5 sites
- [ ] Test privacy backend : aucun SIRET/adresse réelle dans les réponses API
- [ ] Test privacy frontend : aucune donnée réelle hardcodée dans le code source
- [ ] `display_name` HELIOS inchangé dans l'UI (vérification visuelle)
- [ ] Anomalies et recommandations existantes non impactées
- [ ] `python -m pytest` → 0 failures
- [ ] `npx vitest run` → 0 failures
- [ ] Doc mise à jour

---

## Données réelles de référence (copier-coller)

### Site 1 — Paris Bureaux
```
PRM:     30000710966640
SIRET:   94519566700015
SIREN:   945195667
NAF:     7010Z (Activités des sièges sociaux)
Adresse: 35 RUE DES JEUNEURS 2ETAGE, PARIS 75002
CAR:     312.357 MWh
Énergie: Électricité
NTR:     2
Profil:  —
```

### Site 2 — Lyon Bureaux
```
PRM:     19427496304265
SIRET:   87917746700013
SIREN:   879177467
NAF:     6910Z (Activités juridiques)
Adresse: LA MAISON BLANCHE, PARC D ACTIVITE, VAUGNERAY 69670
CAR:     51.761 MWh
Énergie: Électricité
NTR:     1
Profil:  —
```

### Site 3 — Marseille École
```
PRM:     50043806664839
SIRET:   77555892700023
SIREN:   775558927
NAF:     8531Z (Enseignement secondaire général)
Adresse: ECOLE SAINT BRUNO, 10 RUE PIERRE ROCHE, MARSEILLE 13004
CAR:     142.823 MWh
Énergie: Électricité
NTR:     2
Profil:  —
```

### Site 4 — Nice Hôtel
```
PRM:     30002591014358
SIRET:   45182974100029
SIREN:   451829741
NAF:     5510Z (Hôtels et hébergement similaire)
Adresse: 4 Rue Montaigne, CANNES 06400
CAR:     536.4 MWh
Énergie: Électricité ✅
NTR:     7
Profil:  —
⚠️ Façade garde "Nice" — le real_city est Cannes (06)
```

### Site 5 — Toulouse Entrepôt
```
PRM:     50007182872595
SIRET:   49203278400059
SIREN:   492032784
NAF:     5210B (Entreposage et stockage non frigorifique)
Adresse: Lieu-dit Le Carreau, LA VERPILLIERE 38290
CAR:     214.15 MWh
Énergie: Électricité
NTR:     2
Profil:  —
⚠️ Façade garde "Toulouse" — le real_city est La Verpillière (38)
```
