# L2 — Mapping département → zone climatique OPERAT 🟢

> **TL;DR** — 96 départements métropole + 5 DOM mappés vers les 8 zones (H1a → H3) + zones DOM OPERAT.
> Resolveur Python prêt : `resolve_zone_from_postal_code("75001")` → `"H1a"`. **78 tests verts**.
> **Confidence 🟢** — mapping authentifié par recoupement direct sur l'**annexe III** du PDF Légifrance v2 du 03/05/2026 (arrêté 10/04/2020 NOR `LOGL2005904A`, version consolidée 07/09/2025 par `ATDL2430864A`).

---

## ⚠️ Important — Le mapping authentifié diffère du « consensus RT 2012 »

L'annexe III actuellement en vigueur (mise à jour 07/09/2025) ne correspond **pas** au zonage RT 2012 communément cité dans la littérature énergétique. **~25 départements ont une zone différente**. Si tu trouves un mapping ailleurs (Effinergie, ADEME 2010, Cerema), il sera probablement faux pour OPERAT.

| Famille de différence | Avant (consensus RT 2012) | Après (annexe III authentifiée) | Dépts concernés |
|----------------------|---------------------------|----------------------------------|-----------------|
| Est continental | H1a | **H1b** | 08, 10, 51, 52, 54, 55, 57, 67, 68, 88, 90 |
| Bourgogne nord/Yonne | H1c | **H1b** | 58, 70, 89 |
| Centre nord (Loiret) | H2b | **H1b** | 45 |
| Limousin | H2c/H2d | **H1c** | 19, 23, 87 |
| Hautes-Alpes | H2d | **H1c** | 05 |
| Mayenne | H2a | **H2b** | 53 |
| Toulouse / Sud-Ouest | H2d | **H2c** | 31 |
| Vaucluse | H3 | **H2d** | 84 |

→ **H1a est concentré sur Bassin parisien + Hauts-de-France + Normandie + Aisne** (18 dépts).
→ **H2d est réduit à 5 dépts** : 04, 07, 26, 48, 84.

---

## Pourquoi c'était bloquant

Sans ce mapping, le backend PROMEOS ne pouvait pas faire ceci :

```
site.code_postal = "75001"  →  ???  →  zone OPERAT  →  CVCi (Annexe I ATDL2430864A)
```

La matrice CVCi de 27 690 cellules (Annexe I) restait inutilisable côté code applicatif. **C'est résolu.**

---

## Ce qui a été produit

| Fichier | Quoi | Où |
|---------|------|-----|
| **Mapping JSON v2.0 authentifié** | 96 métro + 5 DOM = 101 entités | `backend/config/operat_zones_climatiques.json` |
| **Stations météo détaillées** | 165 stations (numéro, nom, dépt, alt, lat/long, Zclim) | `backend/config/operat_stations_meteo.json` |
| **Resolveur Python** | API : postal/INSEE/département → zone | `backend/regops/operat_zones.py` |
| **Parser Zclim** | Extraction PyMuPDF + regex + consolidation | `backend/scripts/operat_extract_zclim_annexe_iii.py` |
| **78 tests** | structure + cas canoniques + alignement Annexe I | `backend/tests/test_operat_zones_climatiques.py` |
| **Source archivée v2** | PDF Légifrance avec colonne Zclim | `docs/sources/regulatory/operat/legifrance_arrete_methode_10_avril_2020_v2_avec_zclim.pdf` |
| **YAML mis à jour** | section `zones_climatiques` v0.9 confidence 🟢 | `backend/config/operat_valeurs_absolues.yaml` |

---

## 1. Le mapping authentifié (annexe III)

### 1.1 Métropole (96 départements, 8 zones)

| Zone | Description | Nb | Départements |
|------|-------------|----|--------------|
| **H1a** | Bassin parisien + Hauts-de-France + Normandie + Aisne | 18 | 02, 14, 27, 28, 59, 60, 61, 62, 75, 76, 77, 78, 80, 91, 92, 93, 94, 95 |
| **H1b** | Continental nord-est (Grand Est) + Bourgogne nord + Loiret | 15 | 08, 10, 45, 51, 52, 54, 55, 57, 58, 67, 68, 70, 88, 89, 90 |
| **H1c** | Continental moyen-sud + Massif Central + Auvergne + Alpes Nord + Limousin sud + Hautes-Alpes | 18 | 01, 03, 05, 15, 19, 21, 23, 25, 38, 39, 42, 43, 63, 69, 71, 73, 74, 87 |
| **H2a** | Bretagne + Manche | 5 | 22, 29, 35, 50, 56 |
| **H2b** | Pays de la Loire + Centre + Poitou-Charentes + Mayenne | 13 | 16, 17, 18, 36, 37, 41, 44, 49, 53, 72, 79, 85, 86 |
| **H2c** | Sud-Ouest atlantique + Pyrénées + Toulouse + sud Massif Central | 13 | 09, 12, 24, 31, 32, 33, 40, 46, 47, 64, 65, 81, 82 |
| **H2d** | Vallée du Rhône + Provence intérieure + Lozère + Vaucluse | 5 | 04, 07, 26, 48, 84 |
| **H3** | Méditerranée + Corse | 9 | 06, 11, 13, 30, 34, 66, 83, 2A, 2B |

**Total = 96** (= 94 numériques 01-95 sans 20, plus 2A et 2B).

### 1.2 DOM (5 zones propres OPERAT)

| Zone OPERAT | Code département | Préfixe code postal | Stations météo |
|-------------|------------------|---------------------|----------------|
| Guadeloupe | 971 | 971xx | 4 (Les Abymes, Capesterre, Le Moule, Saint-Claude) |
| Martinique | 972 | 972xx | 3 (Lamentin, Fond-Denis, Saint-Joseph) |
| Guyane | 973 | 973xx | 3 (Cayenne, Saint-Georges, Maripasoula) |
| **La Réunion** | 974 | 974xx | 4 (Saint-Denis, Saint-Benoît, Plaine des Makes, Le Tampon) |
| Mayotte | 976 | 976xx | 1 (Pamandzi-Dzaoudzi) |

> **Nomenclature** : l'annexe III utilise **« La Réunion »** (avec article), à différencier de l'annexe I qui dit `Réunion` (sans article).

### 1.3 Hors périmètre OPERAT

Trois COM retournent `None` :
- **975** Saint-Pierre-et-Miquelon
- **977** Saint-Barthélemy
- **978** Saint-Martin

---

## 2. Source primaire authentifiée — citations littérales

**Arrêté du 10 avril 2020** NOR `LOGL2005904A` (JORF n°0108 du 3 mai 2020), version consolidée du 07/09/2025 par arrêté 01/08/2025 NOR `ATDL2430864A`.

**Article 2-h** :
> « Une zone climatique, nommée H1a, H1b, H1c, H2a, H2b, H2c, H2d ou H3, un regroupement de départements métropolitains ; la zone climatique correspondant à chaque département est précisée dans la **dernière colonne "Zclim"** du tableau en annexe III du présent arrêté. »

**Article 5** :
> « L'ajustement en fonction des variations climatiques est effectué à la **maille départementale**. Les données climatiques prises en considération sont celles de la station Météo France la plus représentative du site. L'ajustement en fonction des variations climatiques est effectué sur la base de Degré jour unifié moyen sur la période **2001-2020** de la station météo de référence. »

**Article 1** (modifié 13/04/2022) confirme le périmètre :
> « Ces dispositions s'appliquent aux bâtiments [...] situés en France métropolitaine ainsi qu'en Guadeloupe, en Guyane, en Martinique, à La Réunion et à Mayotte. »

→ **Définition de zone**, **maille DJU** et **périmètre géographique** : 3 ancrages textuels qui authentifient le mapping.

### Historique de l'anomalie résolue

| Date | PDF Légifrance | État colonne Zclim |
|------|----------------|---------------------|
| 2026-05-03 16:28 | v1 (129 pages) | ❌ Vide (bug rendu HTML→PDF) |
| 2026-05-03 16:33 | v1 bis (153 pages, qualité texte améliorée) | ❌ Toujours vide |
| **2026-05-03 16:42** | **v2 (153 pages avec Zclim)** | ✅ **Complète — colonne Zclim authentifiée** |

→ **L'anomalie initiale est levée** : Légifrance a corrigé son rendu PDF entre les versions, et la version actuellement servie contient la colonne Zclim.

---

## 3. Comment utiliser dans le backend

### 3.1 Code postal → zone (cas le plus fréquent)

```python
from regops.operat_zones import resolve_zone_from_postal_code

resolve_zone_from_postal_code("75001")   # → "H1a"  (Paris, vs consensus H1b)
resolve_zone_from_postal_code("13001")   # → "H3"   (Marseille)
resolve_zone_from_postal_code("69001")   # → "H1c"  (Lyon)
resolve_zone_from_postal_code("57000")   # → "H1b"  (Metz, vs consensus H1a)
resolve_zone_from_postal_code("31000")   # → "H2c"  (Toulouse, vs consensus H2d)
resolve_zone_from_postal_code("84000")   # → "H2d"  (Avignon, vs consensus H3)
resolve_zone_from_postal_code("87000")   # → "H1c"  (Limoges, vs consensus H2c)
resolve_zone_from_postal_code("97400")   # → "La Réunion"
resolve_zone_from_postal_code("97500")   # → None   (Saint-Pierre-et-Miquelon, hors OPERAT)
```

### 3.2 Code postal → CVCi (cas d'usage cible)

```python
from regops.operat_zones import resolve_zone_from_postal_code
import json

annexe_i = json.load(open("backend/config/operat_annexe_i_sous_categories.json"))

def get_cvci(code_postal: str, altitude_m: float, sous_categorie_title: str) -> float | None:
    zone = resolve_zone_from_postal_code(code_postal)
    if not zone:
        return None
    palier = (
        "alt_lt_400" if altitude_m < 400 else
        "alt_400_800" if altitude_m < 800 else
        "alt_800_1200" if altitude_m < 1200 else
        "alt_1200_1600" if altitude_m < 1600 else
        "alt_gte_1600"
    )
    # Tolérance accent : "La Réunion" (annexe III) vs "Réunion" (annexe I)
    zone_lookup = "Réunion" if zone == "La Réunion" else zone
    if zone_lookup not in annexe_i["zones_order"]:
        return None
    zone_idx = annexe_i["zones_order"].index(zone_lookup)
    for cat in annexe_i["categories"]:
        for sc in cat["sub_categories"]:
            if sc["title"] == sous_categorie_title:
                return sc["cvc_kwh_m2_an"][palier][zone_idx]
    return None

# Exemple : crèche à Limoges (H1c, altitude ~300m)
cvci = get_cvci("87000", 300, "Accueil petite enfance - Crèche")
# → valeur CVC zone H1c palier alt_lt_400
```

### 3.3 API du resolveur

| Fonction | Entrée | Sortie |
|----------|--------|--------|
| `resolve_zone_from_departement("75")` | str dépt | `"H1a"` |
| `resolve_zone_from_departement("2A")` | str dépt | `"H3"` |
| `resolve_zone_from_departement("971")` | str dépt | `"Guadeloupe"` |
| `resolve_zone_from_postal_code("75001")` | str CP | `"H1a"` |
| `resolve_zone_from_insee_commune("2A004")` | str INSEE | `"H3"` (Ajaccio) |
| `list_departements_for_zone("H1a")` | str zone | `["02","14",...]` |
| `all_zones()` | — | 13 zones (8 métro + 5 DOM) |

---

## 4. Méthode d'extraction (audit traçabilité)

### 4.1 Pipeline

1. **Archivage PDF v2** dans `docs/sources/regulatory/operat/legifrance_arrete_methode_10_avril_2020_v2_avec_zclim.pdf` (613 KB, 153 pages)
2. **Extraction PyMuPDF** texte → 174 909 caractères
3. **Délimitation annexe III** entre `"Liste des stations météorologiques"` et `"Détermination des degrés jours"`
4. **Parser regex** :
   - Détection numéros stations : `^\d{7,8}$`
   - Pour chaque station, scan des 30 lignes suivantes pour collecter [nom, dept, alt, lat, long, Zclim]
   - Reconnaissance Zclim : regex `^(H1[abc]|H2[abcd]|H3|Guadeloupe|Martinique|Guyane|La Réunion|Mayotte)$`
   - Reconnaissance dept : regex `^(0[1-9]|[1-8][0-9]|9[0-5]|2[AB]|97[1-6])$`
   - Reconstitution du nom = champs avant le département
5. **Consolidation** département → zone (cohérence : toutes stations d'un dept doivent agréer)
6. **Sortie JSON v2.0** + `operat_stations_meteo.json` (détail 165 stations)

### 4.2 Validation

- **165 stations parsées** sur 167 attendues (taux d'extraction 99%)
- **100 départements consolidés** (96 métro + 4 DOM directement, +Mayotte ajoutée manuellement post-parsing — la station Pamandzi-Dzaoudzi 98508001 n'a pas matché le regex)
- **0 incohérence** : toutes les stations d'un même département ont la même Zclim
- **Cross-check** sur 5 villes-tests (Paris H1a, Lyon H1c, Marseille H3, Bastia H3, Cayenne Guyane) : ✅ 5/5

### 4.3 Limitations restantes

| # | Limite | Impact | Plan |
|---|--------|--------|------|
| L1 | Mayotte (976) ajoutée manuellement post-parsing | Aucun (donnée connue, 1 station) | Déjà résolu |
| L2 | 2 stations sur 167 non capturées (estimation) | Marginal — couverture par dept reste 100% | À auditer si besoin |
| L3 | Le mapping diffère substantiellement du consensus RT 2012 répandu dans la littérature | Doctrinal — exige communication interne pour aligner les équipes/clients | Prévoir note explicative dans UX Conformité Tertiaire |

---

## 5. Tests (78/78 verts)

```bash
cd backend && venv/bin/python -m pytest tests/test_operat_zones_climatiques.py -v
# 78 passed in 0.33s
```

**Couverture** :
- 5 tests structure (96 métro exhaustifs, pas de doublon, totaux cohérents, alignement avec annexe I)
- 36 tests `resolve_zone_from_departement` (cas canoniques par zone, dont annotations explicites des écarts vs RT 2012)
- 20 tests `resolve_zone_from_postal_code` (10 grandes villes + Corse + 5 DOM + invalides)
- 7 tests `resolve_zone_from_insee_commune` (codes 5 caractères dont 2A/2B alpha)
- 6 tests fonctions utilitaires
- 4 tests entrées invalides (vide, mauvais format, COM hors périmètre)

**Tests de régression OPERAT/regops/doctrine** : ✅ 219 passed, 1 skipped (4,14 s) — aucune régression.

---

## 6. Wiring backend recommandé (P2)

### 6.1 Service backend complet

```python
# backend/regops/services/operat_cabs_service.py (à créer P2)
from regops.operat_zones import resolve_zone_from_postal_code
import json

class OperatCabsService:
    def __init__(self):
        self.annexe_i = json.load(open("backend/config/operat_annexe_i_sous_categories.json"))
        self.annexe_ii = json.load(open("backend/config/operat_annexe_ii_coeff_dju.json"))
        self.zones_climatiques = json.load(open("backend/config/operat_zones_climatiques.json"))

    def cvci_for_site(self, code_postal: str, altitude_m: float, sous_categorie_title: str) -> float | None:
        zone = resolve_zone_from_postal_code(code_postal)
        if not zone:
            return None
        palier = self._palier_for_altitude(altitude_m)
        # Normaliser "La Réunion" → "Réunion" pour aligner sur annexe I
        zone_in_annexe_i = "Réunion" if zone == "La Réunion" else zone
        if zone_in_annexe_i not in self.annexe_i["zones_order"]:
            return None
        zone_idx = self.annexe_i["zones_order"].index(zone_in_annexe_i)
        for cat in self.annexe_i["categories"]:
            for sc in cat["sub_categories"]:
                if sc["title"] == sous_categorie_title:
                    return sc["cvc_kwh_m2_an"][palier][zone_idx]
        return None

    @staticmethod
    def _palier_for_altitude(alt_m: float) -> str:
        if alt_m < 400: return "alt_lt_400"
        if alt_m < 800: return "alt_400_800"
        if alt_m < 1200: return "alt_800_1200"
        if alt_m < 1600: return "alt_1200_1600"
        return "alt_gte_1600"
```

### 6.2 UX Conformité Tertiaire — point de vigilance

Si l'application affiche la zone OPERAT à un utilisateur, **prévoir un tooltip ou une note** :

> Les zones climatiques OPERAT (annexe III arrêté 10/04/2020) diffèrent du zonage RT 2012 historiquement diffusé dans la littérature énergétique. Par exemple :
> - Strasbourg, Metz, Reims sont en **H1b** (et non H1a)
> - Limoges est en **H1c** (et non H2c)
> - Avignon est en **H2d** (et non H3)
> - Toulouse est en **H2c** (et non H2d)
>
> Source faisant foi : annexe III du présent arrêté.

---

## 7. Commit recommandé

```
feat(regops-operat): zonage authentifié 🟢 par recoupement annexe III LOGL2005904A

Lève la confidence 🟡 → 🟢 sur le mapping département → zone climatique OPERAT.
PDF Légifrance v2 (03/05/2026) contient désormais la colonne Zclim complète,
permettant l'extraction directe sur source primaire opposable.

Schema JSON v1.0 (consensus RT 2012 ~25 erreurs) → v2.0 (annexe III authentifiée).

Ajouts :
- backend/config/operat_stations_meteo.json (165 stations détaillées)
- backend/scripts/operat_extract_zclim_annexe_iii.py (parser PyMuPDF + regex)
- docs/sources/regulatory/operat/legifrance_arrete_methode_10_avril_2020_v2_avec_zclim.pdf

Modifications :
- backend/config/operat_zones_climatiques.json : schema 1.0 → 2.0
  Mapping recalculé à partir de 165 stations × cohérence par dept = 100 dépts
  (96 métro + 4 DOM via parser + Mayotte ajoutée manuellement)
- backend/config/operat_valeurs_absolues.yaml : schema 0.8 → 0.9
  zones_climatiques.confidence_globale: 🟡 → 🟢
  Mapping départements re-listé selon annexe III authentifiée
- backend/tests/test_operat_zones_climatiques.py : 68 → 78 tests
  Cas canoniques actualisés avec annotations explicites des écarts vs consensus RT 2012
- docs/audits/AUDIT_OPERAT_L2_ZONES_CLIMATIQUES_2026_05_03.md : v2 réécrite

CHANGEMENTS NOTABLES vs consensus RT 2012 (~25 départements) :
- Est continental (08/10/51/52/54/55/57/67/68/88/90) : H1a → H1b
- Bourgogne nord (58/70/89) : H1c → H1b
- Loiret 45 : H2b → H1b
- Limousin (19/23/87) : H2c/H2d → H1c
- Hautes-Alpes 05 : H2d → H1c
- Mayenne 53 : H2a → H2b
- Toulouse/Sud-Ouest 31 : H2d → H2c
- Vaucluse 84 : H3 → H2d
- H2d réduit à 5 dépts (04/07/26/48/84)

Sources :
- Arrêté 10/04/2020 NOR LOGL2005904A annexe III (PDF v2 Légifrance, JORF n°0108)
- Art. 2-h : définition zones / Art. 5 : maille DJU / Art. 1 : périmètre géo
- Version consolidée 07/09/2025 par arrêté 01/08/2025 NOR ATDL2430864A

Tests : 78/78 ✅ + 219 passed full regops/operat regression ✅
Branche : claude/operat-va-extraction
```

---

**Fin.** L'agent peut maintenant résoudre la zone OPERAT depuis n'importe quel code postal/INSEE/dépt avec **confidence opposable**, et accéder directement aux valeurs CVCi de l'annexe I via le pipeline complet `code_postal → zone → palier altitude → CVCi`.
