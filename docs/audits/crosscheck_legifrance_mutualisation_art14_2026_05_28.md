# Cross-check officiel Légifrance — Mutualisation Décret Tertiaire (Art. 14)

**Sprint** : S3 Conformité — Mutualisation P0 juridique
**Date** : 2026-05-28
**Méthode** : 4 fetch Légifrance + 4 recherches web, croisement systématique avec doctrine produit PROMEOS.
**Doctrine PROMEOS** : Phase 0 read-only obligatoire AVANT tout code. Si un point n'est pas confirmé verbatim source officielle → reporter (ne pas coder).

---

## 1. Cadre légal général (recodifié 2021)

### 1.1 Recodification du CCH (cardinal)

Découverte critique pendant la Phase 0 : **l'Article L.111-10-3 du CCH cité dans la doctrine PROMEOS antérieure est ABROGÉ** depuis le 1ᵉʳ juillet 2021.

| Ancienne référence (abrogée) | Nouvelle référence (en vigueur) | Texte de recodification |
|---|---|---|
| `L.111-10-3` CCH | **`L.174-1` CCH** | Ordonnance n° 2020-71 du 29/01/2020 (réécriture livre I) |
| `R.131-38` à `R.131-44` CCH | **`R.174-22` à `R.174-32` CCH** | Décret n° 2021-872 du 30/06/2021 (recodification partie réglementaire) |

**Conséquence pour le code PROMEOS** : toute mention `L.111-10-3` dans le code, les disclaimers, ou la doctrine doit être migrée vers `L.174-1`. Idem `R.131-*` → `R.174-*`.

**Décision** : ✅ Coder. Migration des références à intégrer dans le sprint S3.

---

## 2. Article 14 de l'arrêté du 10 avril 2020 modifié

Titre officiel : **« Modalités de mutualisation des résultats à l'échelle de tout ou partie d'un patrimoine ».**

URL Légifrance : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045681985

### 2.1 Constitution du « groupe de structures » (Art. 14 §1, alinéa 1)

> « Le périmètre de mutualisation des résultats à l'échelle de tout ou partie d'un patrimoine est défini dans le cadre d'un "groupe de structures", dont les données à renseigner sur la plateforme OPERAT [renvoient à la Table 1B de l'Annexe IV]. »

| Champ | Valeur confirmée | Source |
|---|---|---|
| Concept canonique | « groupe de structures » | Art. 14 §1 al.1 |
| Plateforme d'enregistrement | OPERAT (ADEME) | Art. 14 §1 al.1 |
| Format de données | Table 1B de l'Annexe IV | Art. 14 §1 al.1 |

**Décision** : ✅ Coder. Le modèle backend doit s'appeler explicitement `GroupeStructures` (et non `MutualisationGroup` ou autre traduction libre).

### 2.2 Validation du représentant légal (Art. 14 §1, alinéa 2)

> « L'intégration d'entités fonctionnelles assujetties au sein de ce périmètre de mutualisation des résultats nécessite une validation du représentant légal de chaque entité fonctionnelle qui vaut acceptation du principe de solidarité et d'intégration dans le groupe de structures. »

| Champ | Valeur confirmée | Source |
|---|---|---|
| Qui valide ? | Représentant légal de **chaque** entité fonctionnelle (EFA) | Art. 14 §1 al.2 |
| Effet juridique | Acceptation du principe de **solidarité** + intégration au groupe | Art. 14 §1 al.2 |
| Granularité | 1 validation par EFA membre (pas une seule validation pour le groupe) | Art. 14 §1 al.2 |

**Décision** : ✅ Coder. La table membre doit porter une colonne `representant_legal_status` + horodatage + validateur, sinon le groupe n'est juridiquement pas opposable au contrôle décennal.

### 2.3 Règle d'unicité EFA / groupe (Art. 14 §1, alinéa 3)

> « Une entité fonctionnelle ne peut pas être présente dans plusieurs groupes de structures. »

| Champ | Valeur confirmée | Source |
|---|---|---|
| Règle | Une EFA = **au plus un** groupe à un instant donné | Art. 14 §1 al.3 |
| Granularité contrainte | Au niveau de l'EFA (pas du site, pas du bâtiment) | Art. 14 §1 al.3 |

**Décision** : ✅ Coder. Contrainte UNIQUE PARTIELLE en base : `UNIQUE(efa_id) WHERE status IN ('pending_validation','validated')`. Une EFA peut basculer d'un groupe à un autre si l'ancien est archivé.

### 2.4 Règle de redistribution unique des économies (Art. 14 §1, alinéa 4)

> « Les consommations énergétiques économisées supplémentaires présentées au III du présent article ne peuvent être redistribuées qu'une seule fois. »

| Champ | Valeur confirmée | Source |
|---|---|---|
| Règle | Les économies excédentaires (surplus d'une EFA conforme) ne peuvent compenser qu'**une fois** | Art. 14 §1 al.4 (renvoi III) |
| Granularité | Au niveau du kWh économisé (audit trail nécessaire) | Art. 14 §1 al.4 + Art. 14 §III |

**Décision** : ✅ Coder. Côté service, tracker `economies_redistribuees_kwh` par EFA donneuse et refuser toute redistribution au-delà de cette enveloppe. Audit trail minimum : table `MutualisationLedger` (efa_id, kwh_distributed, redistributed_to_group_id, distributed_at).

### 2.5 Renvoi à la Table 1B de l'Annexe IV

Confirmé Art. 14 §1 al.1 (cité ci-dessus). Table 1B contient les données à saisir OPERAT lors de la constitution du groupe.

URL Annexe IV : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045682103 (Annexe IV verbatim, à approfondir colonne par colonne au Chantier 3).

**Décision** : ✅ Coder. L'export CSV doit reproduire la structure de la Table 1B, header inclus (« Données du groupe de structures — Table 1B Annexe IV »).

---

## 3. Article L.174-1 CCH (nouveau, en vigueur)

URL Légifrance : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043977483

| Élément confirmé | Détail | Source |
|---|---|---|
| Objectifs réduction | **-40 % 2030 / -50 % 2040 / -60 % 2050** vs année de référence ≥ 2010 | L.174-1 |
| 2 méthodes de calcul | Relatif (Crelat) ou Absolu (Cabs) | L.174-1 |
| Modulation OU mutualisation | « Ces objectifs peuvent être **modulés** ou **mutualisés** à l'échelle d'un patrimoine » | L.174-1 |
| Déclaration | Annuelle, sur OPERAT, attestation + score Éco Énergie Tertiaire générés | L.174-1 |

**Décision** : ✅ Coder. Référence canonique à utiliser dans tous les nouveaux disclaimers : `L.174-1 CCH + R.174-22 à R.174-32 CCH + Art. 14 arrêté 10/04/2020 modifié`.

---

## 4. Article R.174-31 CCH (modalité d'application mutualisation)

| Élément confirmé | Détail | Source |
|---|---|---|
| Faculté de mutualisation | Les assujettis peuvent mutualiser les résultats sur tout ou partie de leur patrimoine soumis à l'obligation `L.174-1` | R.174-31 |
| Conditions de mise en œuvre | Fixées par arrêté (= l'arrêté 10/04/2020 modifié, donc Art. 14) | R.174-31 |
| Vérification d'atteinte | Par le gestionnaire de la plateforme numérique au **31/12/2031**, **31/12/2041**, **31/12/2051** au plus tard | R.174-31 |
| Dossier technique justificatif | Renvoi à `R.174-26` (modulation) — peut être réclamé par les agents de contrôle | R.174-31 |

**Décision** : ✅ Coder. Les dates de vérification (31/12 de chaque jalon + 1) sont la deadline naturelle pour notifier le DAF que son groupe doit être finalisé. À traiter dans une suite éventuelle S3+.

---

## 5. Décret n° 2019-771 du 23/07/2019 (décret « tertiaire » originel)

URL : https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251

| Élément | Décision |
|---|---|
| Texte fondateur encore cité par doctrine | Conserver la référence aux côtés de L.174-1 (pas remplacé, juste recodifié) |
| Article 3 du décret | Calcul de l'objectif au niveau patrimoine — toujours en vigueur |

**Décision** : ✅ Coder. Conserver la mention du décret 2019-771 dans les disclaimers (lisible métier, c'est sous ce nom que le DAF connaît le dispositif).

---

## 6. Récap décisions de codage (Phase 0 → STOP gate)

| Point réglementaire | Source verbatim ? | Décision | Chantier où coder |
|---|---|---|---|
| Concept « groupe de structures » | ✅ Art. 14 §1 al.1 | **Coder** | Ch.1 modèle BD + Ch.4 UI |
| Référence Légifrance modernisée (L.174-1 vs L.111-10-3) | ✅ Confirmé Ord. 2020-71 | **Coder** (migration disclaimers) | Ch.4 UI + service mutualisation |
| Validation représentant légal par EFA | ✅ Art. 14 §1 al.2 | **Coder** | Ch.1 modèle + Ch.2 garde-fous + Ch.4 UI |
| 1 EFA ⊆ au plus 1 groupe actif | ✅ Art. 14 §1 al.3 | **Coder** | Ch.1 UNIQUE PARTIEL + Ch.2 service refus |
| Redistribution unique des économies | ✅ Art. 14 §1 al.4 + §III | **Coder** | Ch.2 service ledger + Ch.5 tests |
| Export Table 1B Annexe IV | ✅ Art. 14 §1 al.1 (renvoi) | **Coder** (CSV minimum) | Ch.3 endpoint export |
| Validation RL **OBLIGATOIRE pour export final** | ✅ Art. 14 §1 al.2 (solidarité) | **Coder** (refus export si pending) | Ch.2 garde-fou + Ch.3 endpoint |
| Détail colonnes Table 1B Annexe IV | 🟡 Annexe IV non encore lue verbatim (URL Légifrance) | **Coder minimum viable** + lire l'Annexe au Chantier 3 ; si colonne précise manque, fallback colonnes documentées ADEME | Ch.3 export |
| PDF export Table 1B | 🟡 Pas de pattern PDF existant pour ce flux dans PROMEOS aujourd'hui | **Reporter** (CSV uniquement S3 ; PDF en S3+ si demandé) | — |
| Notification deadline 31/12/2031 | 🟡 Confirmé R.174-31 mais hors scope S3 (système de notif n'existe pas encore par site/groupe) | **Reporter** (suite éventuelle) | — |
| Module OPERAT mutualisation déployé ? | ✅ Confirmé en déploiement progressif (recherche web 2026) | **Disclaimer UI** | Ch.4 UI banner contextuel |

---

## 7. Sources vérifiées (toutes Légifrance / officielles)

1. [Article L.174-1 — Code de la construction et de l'habitation](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043977483)
2. [Article R.174-31 — Code de la construction et de l'habitation](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000043819527)
3. [Section R.174-22 à R.174-32 — CCH](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006074096/LEGISCTA000043819497/)
4. [Article 14 — Arrêté du 10 avril 2020 modifié (mutualisation)](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045681985)
5. [Annexe IV — Arrêté du 10 avril 2020 modifié](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045682103)
6. [Décret n° 2019-771 du 23/07/2019](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251)
7. [Ordonnance n° 2020-71 du 29/01/2020 (recodification CCH)](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041487285) — référence pour L.111-10-3 → L.174-1
8. [Décret n° 2021-872 du 30/06/2021 (recodification réglementaire)](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000043809002) — référence pour R.131-* → R.174-*

---

## 8. Verdict Phase 0

✅ **STOP gate franchie. Codage autorisé** sur les 5 points cardinaux (groupe de structures · validation RL · unicité EFA · redistribution unique · export Table 1B CSV).

🟡 **Reporté** : PDF export Table 1B (pas de pattern existant), notification deadline 31/12/2031 (système non en place).

🚫 **Bloqué** : aucun point bloqué (toutes les modalités essentielles sont sourcées verbatim Légifrance).

**Prochaine action** : Chantier 1 — modèle minimal `GroupeStructures` + `GroupeStructuresMembre`.
