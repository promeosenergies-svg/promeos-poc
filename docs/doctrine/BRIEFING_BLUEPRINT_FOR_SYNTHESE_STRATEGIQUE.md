# PROMEOS — Brief de refonte Synthèse Stratégique

> **Document maître** pour Claude Code : duplique le pattern de la page
> **Briefing du Jour** sur la page **Synthèse Stratégique** en respectant la
> doctrine Sol v1.1, l'algorithme de priorisation v1.0 (ADR-022) et
> l'architecture data-driven cardinale.
>
> **Référence canonique** : commit `32916787` (branche `claude/refonte-sol2`).
> Ce brief est l'export consolidé de tout ce qui a été appris/produit
> pendant la refonte Briefing du Jour (16 commits F.8 → F.29 + doctrine).
>
> **Date** : 2026-05-13
> **Auteur** : session refonte Briefing (Amine + Claude)
> **Audience** : Claude Code chargé de produire la refonte Synthèse Stratégique

---

## 1. Vision et positionnement

### 1.1 PROMEOS — système de contrôle énergétique B2B

PROMEOS est la **tour de contrôle énergétique** du client B2B multi-sites. Pas
un hub Zapier, pas un fournisseur, pas un courtier, pas un agrégateur, pas une
PMO ACC, pas un EMS vertical.

**5 verbes cardinaux** : centraliser · fiabiliser · comparer · auditer · piloter.

**Wedge produit** : facture + conformité + consommation.

**Promesse finale** : *« Comprendre. Décider. Agir. Prouver. »*

### 1.2 Différentiants vs concurrence (Deepki, Energisme, Spacewell, Citron, Akajoule)

| Concurrent | Approche priorisation | Limite |
|---|---|---|
| Deepki | Tableau filtrable | Le client doit construire son tri |
| Energisme | Alertes par seuils | Pas de cross-domaine |
| Spacewell/Dexma | Score performance global | Score opaque non décomposable |
| Citron/iQspot | Tri par anomalie détectée | Réactif, pas prospectif |
| Akajoule, Enoptea | Liste plate des reco consultants | Pas de système, dépendant humain |
| **PROMEOS v1.0** | **G×I×D + Catégorie + Persona doctrinal** | **Différenciant : transparent, opposable, multi-audience** |

**Promesses cardinales** :
- *« Vous savez toujours pourquoi PROMEOS dit que c'est important »* → badge
  PriorityProof + modal méthodologie complète.
- *« Le même patrimoine, 3 audiences, 3 priorités »* → toggle persona qui
  recalcule le scoring backend.
- *« Aucun item n'est P1 par hasard »* → 3 axes sourcés + 3 overrides
  doctrinaux + audit trail.

### 1.3 Doctrine PROMEOS Sol v1.1 (référence socle)

- 12 principes
- 7 piliers
- 5 anti-patterns interdits (cf §6.5 doctrine)
- 8 tests doctrinaux (cf §7 doctrine)
- Loi L11 — Hub Page Grammar (cf §12)

Doctrine complète : `docs/vision/promeos_sol_doctrine.md`.

---

## 2. Personas et cible

### 2.1 Les 3 personas du toggle PriorityProof (ADR-022 §Personas)

| Persona | wG | wI | wD | Score max | Seuil P1 | Seuil P2 | Seuil P3 |
|---|---|---|---|---|---|---|---|
| **Responsable Énergie** | 3 | 2 | 2 | 35 | ≥25 | ≥18 | ≥12 |
| **DAF** | 2 | 3 | 2 | 35 | ≥22 | ≥16 | ≥10 |
| **DG / COMEX** | 2 | 3 | 3 | 40 | ≥24 | ≥17 | ≥11 |

**Justification** :
- Responsable Énergie porte la responsabilité légale → gravité prime (×3).
- DAF raisonne financier → impact prime (×3).
- DG/COMEX arbitre court vs long terme → impact + délai prime (×3 chacun).

### 2.2 Synthèse Stratégique — persona primaire

**DG / COMEX** est le persona primaire de la Synthèse Stratégique (vs
Responsable Énergie pour Briefing du Jour). Le toggle topbar suggère
DG-COMEX au mount mais laisse le choix utilisateur.

| Aspect | Briefing du Jour | Synthèse Stratégique |
|---|---|---|
| Persona primaire | Responsable Énergie | DG / COMEX |
| Fréquence | Quotidien (J-1) | Hebdomadaire / Mensuel |
| Granularité | Sites individuels | Portefeuilles + Groupe |
| Horizon | Court terme (≤ 90 jours) | Moyen-long terme (1-5 ans) |
| Question principale | « Qu'est-ce qui mérite mon attention aujourd'hui ? » | « Où va-t-on dans 2-5 ans ? » |
| Verbes (CTAs) | « voir, vérifier, programmer » | « arbitrer, simuler, comparer, contester » |
| Période défaut | `week` | `month` |

---

## 3. Système de couleurs (Sol design tokens)

### 3.1 Source unique : `frontend/src/ui/sol/tokens.css`

**Slate base — papier / canevas / panneau**
```css
--sol-bg-canvas: #f8f9fa;
--sol-bg-paper:  #ffffff;
--sol-bg-panel:  #f3f4f6;
```

**Ink scale — du clair au foncé**
```css
--sol-ink-50:  #fafaf7;
--sol-ink-100: #f1f5f9;
--sol-ink-200: #e2e8f0;
--sol-ink-300: #cbd5e1;
--sol-ink-400: #94a3b8;
--sol-ink-500: #64748b;
--sol-ink-700: #334155;
--sol-ink-900: #0f172a;
--sol-rule:    #e2e8f0;  /* alias bordures par défaut */
```

**Accents émotionnels warm — palette V2 « journal en terrasse »**

| Token | fg (texte) | bg (fond) | line (bordure) | Usage |
|---|---|---|---|---|
| **calme** | `#2f6b5e` (bleu-vert) | `#e3f0ed` | (calme-fg) | « tout va bien », primaire bouton |
| **succes** | `#2e6b4a` (vert forêt) | `#dfede3` | `#5a8a72` | « bonne nouvelle » |
| **attention** | `#8a5a14` (ambre WCAG AA) | `#f6ead2` | `#d4a85a` | « à regarder » |
| **afaire** | `#a04525` (orange corail WCAG AA) | `#f7e4d8` | `#d68a5e` | « à faire » |
| **refuse** | `#8b3a3a` (terre cuite) | `#f3dddb` | `#b85a5a` | « dérive », critique |
| **calme-fg-hover** | `#245047` (-10 % luminosité) | — | — | hover primaire |

**Plages tarifaires HP/HC**
```css
--sol-hph-fg: #b84545;  --sol-hph-bg: #fbe9e9;  /* HP signal fort */
--sol-hch-fg: #2e4a6b;  --sol-hch-bg: #e6edf5;  /* HC calme */
--sol-hpe-fg: #d08b3c;  --sol-hpe-bg: #fbf1e3;  /* HP été */
--sol-hce-fg: #6b8cae;  --sol-hce-bg: #e9eef4;  /* HC été */
```

**Premium night (variante Hero hub)**
```css
--sol-night-bg:      #072a44;             /* hero base */
--sol-night-bg-alt:  #0b3552;             /* gradient */
--sol-night-fg:      #ffffff;
--sol-night-line:    rgba(97, 183, 214, 0.22);
--sol-night-dot:     rgba(97, 183, 214, 0.55);
--sol-night-dot-hot: rgba(228, 173, 119, 0.85);
```

### 3.2 Règles d'usage couleurs

1. **Aucun hex hardcodé** dans JSX/CSS — toujours `var(--sol-*)` (anti-pattern doctrine §6.5).
2. **Classes Tailwind couleur** sont mappées automatiquement vers Sol via `frontend/src/index.css` (cascade CSS pure, zero touch JSX).
3. **WCAG AA** : tous les couples fg/bg respectent ratio ≥ 4.5:1 (testé Phase 1.3bis P0-E).
4. **Hover** = -10 % luminosité (calme-fg-hover pattern).
5. **`::selection` + scrollbar** : calme-bg / ink-300 cohérent.

---

## 4. Système typographique (Sol fonts)

### 4.1 3 fontes canoniques

```css
--sol-font-display: 'Fraunces', 'Tiempos', Georgia, serif;
--sol-font-body:    'DM Sans', system-ui, -apple-system, sans-serif;
--sol-font-mono:    'JetBrains Mono', ui-monospace, monospace;
```

### 4.2 Règles d'usage

| Usage | Fonte | Taille / Weight | OpenType |
|---|---|---|---|
| **Titre hero** (h1, .sol-page-title) | Fraunces | 32px / 500 | `opsz` 60 |
| **Titre hero italic-hook** | Fraunces italic | — / 400 | `opsz` 90 |
| **h2** (sections) | Fraunces | 22px / 600 | letter-spacing -0.02em |
| **h3** (sous-sections) | Fraunces | 17px / 600 | letter-spacing -0.015em |
| **h4-h6** | Fraunces | 15-13px / 600 | — |
| **Body courant** | DM Sans | 15px / 400 / line-height 1.5 | `ss01`, `cv11`, letter-spacing -0.005em |
| **text-sm** | DM Sans | 13px / line-height 1.45 | — |
| **text-xs** | DM Sans | 11.5px / line-height 1.45 | — |
| **Labels eyebrows / footScm / data-mono** | JetBrains Mono | 10-12px / 400-500 | letter-spacing 0.08em uppercase souvent |
| **Chiffres KPI** | JetBrains Mono `.sol-numeric` | 24-38px | `tnum`, `zero`, line-height 1 |
| **Form elements** | DM Sans | 15px hérité | tabular-nums sur input[type=number/date/time] |

### 4.3 Patterns canoniques (`.sol-*` classes)

- `.sol-page-kicker` — eyebrow mono uppercase 10px letter-spacing 0.14em
- `.sol-page-title` — Fraunces 32px Stripe Atlas pattern (avec `<em>` italic-hook)
- `.sol-page-subtitle` — DM Sans 13px ink-500
- `.sol-section-head` — DM Sans 15px / 600 ink-900
- `.sol-numeric` — JetBrains Mono tabular-nums leading-none
- `.max-w-sol-strip` (840px) / `.max-w-sol-hero` (920px)

---

## 5. Visuel et ergonomie (composition L11 Hub Page)

### 5.1 Loi L11 — Hub Page (doctrine §12)

Une page hub PROMEOS suit la grammaire stricte :

```
┌──────────────────────────────────────────────────────────────┐
│  HERO (SolHeroPremiumNight)                                  │
│   - eyebrow mono : "Briefing du jour · mardi 12 mai"         │
│   - title Fraunces (italic-hook éventuel)                    │
│   - sub narrative DM Sans                                     │
│   - meta footer : Qualité, Confiance, Période, Scope         │
│   - primary CTA droite                                        │
│   - fond bleu nuit + illustration filaire (-night-line)      │
├──────────────────────────────────────────────────────────────┤
│  KPI TRIPTYCH (HubPage.KpiTriptych) — exactement 3 KPIs       │
│   ├─ HubKpiCard {eyebrow, label, value, unit, delta, footScm}│
│   ├─ HubKpiCard                                              │
│   └─ HubKpiCard                                              │
├──────────────────────────────────────────────────────────────┤
│  CHART PAIR (HubPage.ChartPair) — exactement 2 charts         │
│   ├─ ChartFrame {question, answer, footScm}                  │
│   │   └─ ChartFrame{Bars|Line|TrajectoryLine|...}            │
│   └─ ChartFrame ...                                          │
├──────────────────────────────────────────────────────────────┤
│  HIGHLIGHTS (HubPage.Highlights) — 3 à 5 priorités           │
│   ├─ HubHighlight {tier, severity, category, scope, title,   │
│   │                 evidence, impact, invitation,             │
│   │                 priorityProof, onPriorityProofClick}     │
│   ├─ HubHighlight                                            │
│   └─ HubHighlight                                            │
├──────────────────────────────────────────────────────────────┤
│  FOOTER SCM (HubPageFooter)                                  │
│   - Sources, Confiance, MAJ timestamp, lien Méthodologie     │
└──────────────────────────────────────────────────────────────┘
```

**Cardinal** : aucune page hub ne doit dévier de cette structure.

### 5.2 Anti-patterns interdits (Loi L11)

| AP | Description | Interdit |
|---|---|---|
| **AP1** | KPI inline dans page (pas de HubKpiCard) | ❌ |
| **AP2** | Plus de 3 KPIs ou plus de 2 charts | ❌ |
| **AP3** | 4× même catégorie dans Top highlights | ❌ |
| **AP4** | Hardcode chiffre dans route (sans service) | ❌ |
| **AP5** | P1 sans evidence chiffrée + lien preuve | ❌ |
| **AP6** | Narration sur données pourries (qualité < 80 %) | ❌ |
| **AP7** | Référence sans audit trail | ❌ |
| **AP8** | Toggle persona mode Direction si data quality < 80 % | ❌ |

### 5.3 Ergonomie cardinale

- **Page max-width** 840-920px (hero) ou 1180px (cockpit grid 12 cols).
- **Padding hero** : 36px haut/bas, 28px gauche/droite.
- **Padding cards** : 14-18px standard, 20-24px pour KPI heroes.
- **Border radius** : 6px (cards/buttons), 8px (cards 2xl), 12-14px (modals).
- **Shadows** : 1-4px softer (rgba(15,23,42, 0.04-0.08)).
- **Spacing** : grid 16px gap par défaut, 8/12/24px secondaires.
- **Animations** : 180ms cubic-bezier(0.2, 0.6, 0.2, 1), reduced-motion respect.
- **Texture grain** : 2.5 % SVG noise sur body (métaphore éditoriale).
- **Stagger reveal** : 60ms par enfant au mount initial (Linear pattern).

---

## 6. Moteur de décision et arbitrage (doctrine v1.0)

### 6.1 Algorithme canonique de priorisation

Module : **`backend/regops/priority_scoring.py`**.

**Inputs** : `Finding` dataclass.
**Output** : `PriorityScore` dataclass `{ total, tier, persona, breakdown, overrides_applied }`.

### 6.2 Les 4 axes (G × I × D × C)

#### Axe Gravité (G ∈ [0, 5])

> *Que se passe-t-il si on ne fait rien ?*

| G | Sens | Exemples |
|---|---|---|
| 5 | Bloquant légal · sanction immédiate | Décret BACS non conforme passé 2027, OPERAT échue |
| 4 | Bloquant opérationnel · service dégradé | Connecteur EMS HS, API SGE échec, contrat expiré |
| 3 | Pénalité légale différée | DT 2030 trajectoire non tenable, audit ADEME futur |
| 2 | Perte économique récurrente | Anomalie facture, dérive baseload, sur-souscription |
| 1 | Inefficacité optimisable | Marge tarifaire, HP/HC sous-optimal |
| 0 | Information sans action | Veille marché, rapport informatif |

**Mapper Severity → G** :
```
CRITICAL → 5  (sanction immédiate)
HIGH     → 4  (bloquant opérationnel)
MEDIUM   → 3  (pénalité différée)
LOW      → 2  (perte récurrente)
```

#### Axe Impact (I ∈ [0, 5])

> *Combien ça pèse ?*

| I | Seuil €/an | Seuil MWh/an | Notation indicative |
|---|---|---|---|
| 5 | ≥ 100 k€ | ≥ 1 000 MWh/an | Action structurante |
| 4 | 50-100 k€ | 500-1 000 MWh/an | Action site mid-cap |
| 3 | 10-50 k€ | 100-500 MWh/an | Action ciblée |
| 2 | 1-10 k€ | 10-100 MWh/an | Quick-win |
| 1 | < 1 k€ | < 10 MWh/an | Maintenance / hygiène |
| 0 | Non monétisable | — | Informatif / veille |

**Conversion interne** : si I est en MWh/an, conversion à 130 €/MWh élec, 50 €/MWh gaz. Affichage UI suit la doctrine traçabilité monétaire (€ si réglementaire/contractuel/mesuré, MWh sinon).

#### Axe Délai (D ∈ [0, 5])

> *À quel point c'est urgent ?*

| D | Délai jusqu'à deadline | Sens |
|---|---|---|
| 5 | ≤ 30 jours (ou passé) | Imminence / sanction en cours |
| 4 | 30-90 jours | Court terme (trimestre courant) |
| 3 | 90-365 jours | Moyen terme (annuel) |
| 2 | 1-3 ans | Long terme (DT 2030 vu de 2026) |
| 1 | > 3 ans | Très long terme (DT 2040, 2050) |
| 0 | Pas d'échéance contraignante | Continu / optimisation |

#### Axe Catégorie (C — qualitative, pas une note)

5 valeurs : `PLATEFORME`, `ENERGIE`, `REGLEMENTAIRE`, `FINANCIER`, `STRATEGIQUE`.

Mapping vers Domain (rétro-compat) :
```
PLATFORM_HEALTH ↔ PLATEFORME
COMPLIANCE      ↔ REGLEMENTAIRE
FINANCIAL       ↔ FINANCIER
ENERGY          ↔ ENERGIE
OPTIMISATION    ↔ STRATEGIQUE
```

### 6.3 Formule de scoring + 3 personas

```python
score = G * wG + I * wI + D * wD

PERSONA_WEIGHTS = {
    RESPONSABLE_ENERGIE: (wG=3, wI=2, wD=2),  # max 35
    DAF:                 (wG=2, wI=3, wD=2),  # max 35
    DG_COMEX:            (wG=2, wI=3, wD=3),  # max 40
}
```

### 6.4 Les 3 overrides cardinaux

```python
# Override 1 — Gravité légale absolue
if g == 5:
    score = max(score, 25)
    # → garantit P1 même sans impact ni urgence

# Override 2 — Urgence absolue qualifiée
if d == 5 and g >= 3:
    score = max(score, 22)
    # → toute urgence imminente avec gravité monte en haut P2

# Override 3 — Plafond impact orphelin
if i == 5 and g == 0:
    score = min(score, 15)
    # → un gros impact sans gravité ne peut pas écraser un sujet réglementaire
```

### 6.5 Tiering persona-dependent

```
P1 si score ≥ seuil_P1[persona] — action critique sous 30 jours
P2 si score ≥ seuil_P2[persona] — alerte action sous 90 jours
P3 si score ≥ seuil_P3[persona] — veille / recommandation
sinon NONE — non affiché dans le briefing
```

### 6.6 HUB_CAT_ORDER — départage par hub

En cas d'égalité de score, ordre de catégorie selon le hub (départage déterministe) :

| Hub | Ordre catégorie |
|---|---|
| `COCKPIT_JOUR` | ENERGIE > PLATEFORME > REGLEMENTAIRE > FINANCIER > STRATEGIQUE |
| **`COCKPIT_STRATEGIQUE`** | **STRATEGIQUE > FINANCIER > REGLEMENTAIRE > ENERGIE > PLATEFORME** |
| `ENERGIE` | ENERGIE > PLATEFORME > REGLEMENTAIRE > FINANCIER > STRATEGIQUE |
| `CONFORMITE` | REGLEMENTAIRE > FINANCIER > ENERGIE > PLATEFORME > STRATEGIQUE |
| `FACTURES` | FINANCIER > REGLEMENTAIRE > ENERGIE > PLATEFORME > STRATEGIQUE |
| `ACHAT` | FINANCIER > STRATEGIQUE > ENERGIE > REGLEMENTAIRE > PLATEFORME |
| `PATRIMOINE` | PLATEFORME > REGLEMENTAIRE > ENERGIE > FINANCIER > STRATEGIQUE |

**Pour Synthèse Stratégique : utiliser `HubId.COCKPIT_STRATEGIQUE`** → STRATEGIQUE prime.

### 6.7 Top N + dédup (anti-pattern AP3)

```python
top_n(findings, n=3, persona, hub) :
    1. rank_findings → triés par (-score, cat_index(hub), -d, -i)
    2. dédup double : par category_label ET par site_id
    3. filter tier != NONE
    4. return top n
```

**Pour Synthèse Stratégique** : peut-être dédup par (category, portefeuille_id) plutôt que site_id, pour faire ressortir les enjeux portefeuille-level.

### 6.8 Audit trail (transparence)

Chaque highlight expose un `_audit` complet :

```json
{
  "score_total": 26,
  "score_breakdown": { "g": 4, "i": 4, "d": 3, "g_weighted": 12, "i_weighted": 8, "d_weighted": 6 },
  "persona": "responsable_energie",
  "overrides_applied": ["OV1_GRAVITE_LEGALE_ABSOLUE"],
  "doctrine_version": "priorisation_v1.0",
  "domain": "COMPLIANCE",
  "category": "REGLEMENTAIRE",
  "scope_level": "SITE",
  "sources": {
    "gravity": "Compliance score V2 adaptatif",
    "impact": "Estimation interne PROMEOS · 50 000 €/an",
    "delay": "Calendrier réglementaire · échéance 2026-12-31"
  },
  "axis_labels": {
    "gravity": "Bloquant opérationnel · service dégradé",
    "impact": "50-100 k€/an · action site mid-cap",
    "delay": "90-365 jours · moyen terme"
  }
}
```

---

## 7. Calculs métier — services SoT canoniques

### 7.1 Service consommation (`consumption_granularity_service.py`)

```python
get_org_daily_kwh(db, org_id, day) → float | None
get_org_daily_range_kwh(db, org_id, start, end) → list[{date, kwh, source}]
get_org_hourly_curve_kw(db, org_id, day) → list[{hour 0-23, kw}]
get_org_peak_kw(db, org_id, day) → {hour, kw} | None
get_org_subscribed_kw(db, org_id) → float | None  # Σ Meter.subscribed_power_kva
get_org_baseline_daily_kwh(db, org_id, today, lookback_days=28) → float | None
```

**Baseline DJU-adjusted V2** (F.26 + F.29 — utiliser pour Synthèse aussi) :

```python
get_org_baseline_daily_kwh_dju_adjusted(db, org_id, target_day, today)
  → {
    baseline_raw_kwh,
    baseline_adjusted_kwh,
    dju_target,           # 0-380, France COSTIC
    dju_baseline_avg,
    heating_load_ratio,   # 0.4 par défaut (bureaux tertiaire)
    method                # "dju_v2_simplified" | "flat"
  }

# Formule : baseline_adj = baseline_brute × (1 + 0.4 × (DJU_target/DJU_baseline - 1))
# Plafonné [0.6, 1.4] pour éviter les explosions extrêmes.
```

**Profil DJU mensuel France** (constante `_DJU_MONTHLY_FRANCE` à utiliser tel quel) :
```
janv 380 · fév 330 · mars 270 · avr 180 · mai 100 · juin 40
juill 10 · août 15 · sept 60 · oct 150 · nov 260 · déc 360
```

### 7.2 Service plages tarifaires (`tariff_periods_service.py`)

```python
get_active_hp_hc_zones(db, org_id, energy_type=ELEC) → {
  hc_hours: set[int],
  hp_hours: set[int],
  hc_zones: list[{from_h, to_h}],
  source: "contract" | "turpe_6_default",
  contract_id: int | None
}
```

**Source de vérité ordonnée** :
1. `EnergyContract.metadata_json['tariff_periods']['hc_zones']` si peuplé.
2. Fallback TURPE 6 : HC = 0h-7h + 22h-23h (tertiaire C5 standard).

### 7.3 Service highlights (`cockpit_highlights_service.py`)

```python
build_top_n_highlights(
    db, org_id, n=3, today=None,
    persona=Persona.RESPONSABLE_ENERGIE,    # défaut, à passer dg_comex pour Synthèse
    hub=HubId.COCKPIT_JOUR                   # à passer COCKPIT_STRATEGIQUE pour Synthèse
) → list[dict_highlight_payload]

count_total_signals(db, org_id, today, persona) → {p1, p2, p3, total}
```

### 7.4 Détecteurs (`highlights_detectors.py`)

```python
detect_compliance_findings(db, org_id) → list[Finding]
  # iter sites + compute_site_compliance_score → 1 Finding par framework < 50
detect_billing_findings(db, org_id, lookback_days=180) → list[Finding]
  # iter EnergyInvoice + bill_intelligence.detect_anomalies_for_invoice
  # dédup 1 max par site (severity max)
detect_ems_staleness_findings(db, org_id, today) → list[Finding]
  # max(MeterReading.timestamp) par site, severity selon âge
```

**Pour Synthèse Stratégique : créer en plus** :
```python
detect_strategic_findings(db, org_id) → list[Finding]
  # Capacité 2026 RTE, CBAM, ARENH/VNU, ETS2, audit ISO 50001 pluri-annuel
detect_economic_performance_findings(db, org_id) → list[Finding]
  # Coût €/MWh > P75 NAF, mix achat sub-optimal, CEE non valorisés
```

### 7.5 Règle d'or — ZÉRO calcul métier frontend

Le frontend est **affichage uniquement**. Tous les calculs (CO₂, scoring,
forecasting, baseline) côté backend, exposés via REST, consommés en
Context/hook (`useFilter`, `usePersona`).

---

## 8. Architecture backend (pattern à dupliquer)

### 8.1 Endpoint orchestrateur

```python
# backend/routes/cockpit.py — pattern à mirror dans cockpit_strategique.py

@router.get("/cockpit/strategique")  # POUR SYNTHÈSE
def get_cockpit_strategique(
    request: Request,
    period_type: str = "month",     # défaut month vs week pour briefing
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    persona: str = "dg_comex",      # défaut DG-COMEX vs Resp Énergie
    horizon_year: int = 2030,        # nouveau param — projection trajectoire
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    org_id = resolve_org_id(request, auth, db)
    period = {"type": period_type, ...}
    sites = _sites_for_org(db, org_id).all()
    scope_label = f"{len(sites)} sites"

    # Highlights computed UNE FOIS, threadés vers hero.
    highlights = _build_cockpit_strategique_highlights(db, org_id, persona_str=persona)

    return {
        "hero":       _build_cockpit_strategique_hero(db, org_id, period, scope_label, highlights, horizon_year),
        "kpis":       _build_cockpit_strategique_kpis(db, org_id, period, horizon_year),
        "charts":     _build_cockpit_strategique_charts(db, org_id, period, horizon_year),
        "highlights": highlights,
        "footer":     _build_cockpit_strategique_footer(db, org_id),
    }
```

### 8.2 Pattern fallback "données partielles"

Tout builder doit gérer le cas service retourne None :

```python
if value is not None:
    kpi = { "value": ..., "delta": {...}, "footScm": "Source X · ..." }
else:
    kpi = {
        "value": None, "delta": None,
        "helpTooltip": "Aucune donnée disponible.",
        "footScm": "Données partielles · Vérifier les connecteurs",
    }
```

### 8.3 Helper `_latest_data_day(db)` à dupliquer

```python
def _latest_data_day(db: Session) -> date | None:
    """Date du dernier MeterReading (J-1 réel pour la démo)."""
    last_ts = db.query(func.max(MeterReading.timestamp)).scalar()
    if last_ts is None: return None
    today_real = datetime.utcnow().date()
    candidate = last_ts.date()
    return today_real - timedelta(days=1) if candidate >= today_real else candidate
```

### 8.4 Pattern hero narratif depuis highlights

```python
def _generate_hero_narrative(highlights, scope_label) -> tuple[int, str]:
    """Génère (n_signals, sub_text) depuis Top N — préserve acronymes."""
    sentences = []
    for h in highlights:
        scope_text = h.get("scope") or "Site"
        city = scope_text.split()[-1]
        impact_value = h.get("impact", {}).get("value", "—")
        title = h.get("title", "")
        short_title = title.split("—")[0].strip()
        # Lowercase UNIQUEMENT la 1re lettre — préserve acronymes (EMS/BACS/CVC)
        if short_title:
            short_title = short_title[0].lower() + short_title[1:]
        if impact_value and impact_value != "—":
            sentences.append(f"{city} : {short_title} {impact_value}.")
        else:
            sentences.append(f"{city} : {short_title}.")
    sentences.append("Tout le reste est sous contrôle.")
    return (len(highlights), " ".join(sentences))
```

---

## 9. Architecture frontend (pattern à dupliquer)

### 9.1 Page (mirror `pages/CockpitJour.jsx` → `pages/CockpitStrategique.jsx`)

```jsx
import { useEffect, useMemo, useState } from 'react';
import {
  HubPage, SolHeroPremiumNight,
  ChartFrame, ChartFrameBars, ChartFrameLine,  // + nouveaux primitifs
  HubHighlight, HubPageFooter, HubKpiCard,
  HubSkeleton, HubError, AutoTerm,
} from '../components/grammar';
import PriorityProofModal from '../components/grammar/hub/PriorityProofModal';
import { useFilter } from '../contexts/FilterContext';
import { usePersona } from '../contexts/PersonaContext';
import { getCockpitStrategique } from '../services/api';   // NOUVEAU client
import { logger } from '../services/logger';

const TAG = 'CockpitStrategique';

export default function CockpitStrategique() {
  const { period } = useFilter();
  const { persona, setDataQualityPct } = usePersona();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [proofModalHighlight, setProofModalHighlight] = useState(null);

  // Fetch + reload sur changement persona ou period
  useEffect(() => { ... fetch avec { period, persona } ... }, [period, persona]);

  // Publie data quality vers PersonaContext (gating toggle DAF/DG)
  useEffect(() => {
    const q = payload?.hero?.meta?.quality;
    if (typeof q === 'number') setDataQualityPct(q);
  }, [payload, setDataQualityPct]);

  // useMemo enfants
  const kpiChildren = useMemo(...);
  const chartChildren = useMemo(...);
  const highlightChildren = useMemo(() =>
    highlights.slice(0, 5).map((h) => {
      const { id, title, evidence, _audit, tier, ...rest } = h;
      return (
        <HubHighlight
          key={id}
          {...rest}
          title={<AutoTerm text={title} />}
          evidence={<AutoTerm text={evidence} />}
          priorityProof={_audit ? {
            score_total: _audit.score_total,
            score_breakdown: _audit.score_breakdown,
            persona: _audit.persona,
            overrides_applied: _audit.overrides_applied,
            tier,
          } : undefined}
          onPriorityProofClick={_audit ? () => setProofModalHighlight(h) : undefined}
        />
      );
    }), [highlights]);

  // States loading/error gates
  if (loading && !payload) return <Skeleton />;
  if (error && !payload) return <HubError onRetry={retry} />;

  return (
    <div data-page="cockpit-strategique" data-doctrine="L11">
      <HubPage pillar="strategique">          {/* pillar key change vs briefing */}
        <SolHeroPremiumNight {...hero} primaryCta={...} />
        <HubPage.KpiTriptych>{kpiChildren}</HubPage.KpiTriptych>
        <HubPage.ChartPair>{chartChildren}</HubPage.ChartPair>
        <HubPage.Highlights title="Top arbitrages stratégiques" linkAll="/cockpit/decision">
          {highlightChildren}
        </HubPage.Highlights>
        <HubPageFooter {...footer} />
      </HubPage>
      {proofModalHighlight && (
        <PriorityProofModal
          highlight={proofModalHighlight}
          onClose={() => setProofModalHighlight(null)}
        />
      )}
    </div>
  );
}
```

### 9.2 Dispatcher polymorphique charts

```jsx
function renderChartInner(c) {
  if (c.type === 'bar_daily_7d')      return <ChartFrameBars ... />;     // si réutilisé
  if (c.type === 'line_24h_hp_hc')    return <ChartFrameLine ... />;     // si réutilisé
  if (c.type === 'trajectory_line')   return <ChartFrameTrajectoryLine ... />;  // NOUVEAU
  if (c.type === 'mix_horizontal')    return <ChartFrameMixHorizontal ... />;   // NOUVEAU
  return null;
}
```

### 9.3 API client (mirror `services/api/cockpit.js`)

```js
export const getCockpitStrategique = (filter = {}) => {
  const period = filter.period || {};
  const params = { period_type: period.type || 'month' };
  if (period.start) params.period_start = period.start;
  if (period.end) params.period_end = period.end;
  if (filter.persona) params.persona = filter.persona;
  if (filter.horizonYear) params.horizon_year = filter.horizonYear;
  return cachedGet('/cockpit/strategique', { params }).then((r) => r.data);
};
```

### 9.4 Grammar primitives — réutilisables 100 %

`frontend/src/components/grammar/hub/` :

| Primitif | Réutilisable Synthèse ? |
|---|---|
| `HubPage` + `KpiTriptych` / `ChartPair` / `Highlights` | ✅ as-is |
| `SolHeroPremiumNight` | ✅ as-is |
| `HubKpiCard` | ✅ as-is |
| `ChartFrame` (wrapper question/answer) | ✅ as-is |
| `ChartFrameBars` | ⚠️ adapter ou créer `ChartFrameTrajectoryLine` |
| `ChartFrameLine` | ⚠️ adapter |
| `HubHighlight` (avec PriorityProof inline) | ✅ as-is |
| `PriorityProofModal` | ✅ as-is |
| `HubPageFooter` | ✅ as-is |
| `HubSkeleton`, `HubError`, `AutoTerm` | ✅ as-is |

### 9.5 Contextes

```jsx
// frontend/src/contexts/PersonaContext.jsx — déjà existant, à réutiliser
const { persona, setPersona, dataQualityPct, setDataQualityPct } = usePersona();
```

**Pour Synthèse** : possibilité de banner "Mode DG-COMEX recommandé" au mount
si persona=responsable_energie (suggestion non bloquante).

---

## 10. Tests + source-guards (pattern à mirror)

### 10.1 Pytest

```
backend/tests/test_priority_scoring.py        (39 tests, partagé)
backend/tests/source_guards/test_strategique_no_hardcode.py   (à créer, mirror)
backend/tests/test_trajectory_service.py      (à créer)
backend/tests/test_economic_performance_service.py  (à créer)
```

### 10.2 Source-guards anti-hardcode (pattern)

```python
# backend/tests/source_guards/test_strategique_no_hardcode.py
def test_no_hardcoded_dt_trajectory_value(route_source: str):
    forbidden = ['"value": 73,', '"value": 47,']  # spécifique strat
    for p in forbidden:
        assert p not in route_source

def test_uses_trajectory_service(route_source: str):
    assert "trajectory_service" in route_source

def test_no_hardcoded_milestones_2030_2040(route_source: str):
    """milestones doivent venir du service, pas hardcoded."""
    assert "year=2030" not in route_source.replace(" ", "")
```

### 10.3 Vitest hub primitives (déjà existants)

```
frontend/src/components/grammar/hub/__tests__/  (72 tests, partagés, ne pas casser)
```

### 10.4 Snapshots Playwright

```
frontend/tests/visual/snapshots/synthese_after_*/  (à créer, mirror cockpit jour)
```

---

## 11. Doctrine de propagation visuelle (déjà appliquée)

### 11.1 CSS doctrine pure (`frontend/src/index.css`)

Toute page hérite automatiquement du body global qui pointe vers `--sol-*`.
Pas besoin de toucher au JSX si la page utilise les classes Tailwind standard.

**Mappings appliqués automatiquement** :
- gray/slate/neutral/zinc/stone 50-900 → ink scale Sol
- blue/indigo/sky/cyan → calme
- emerald/green/lime → succes
- amber/yellow → attention
- orange → afaire
- red → refuse
- purple/fuchsia/pink/rose → attention warm
- Form elements (button, input, select, textarea) → font Sol body
- Tables → font Sol + warm
- Scrollbar → slate moderne
- ::selection → calme

**Cardinal** : pour la Synthèse Stratégique, ne pas réintroduire de hex
hardcodé. Si besoin de custom, ajouter à `tokens.css`.

### 11.2 Grammar primitives respectent automatiquement la doctrine

Tous les composants `frontend/src/components/grammar/hub/*` sont déjà
conformes Sol. Réutiliser tels quels = conformité garantie.

---

## 12. Roadmap d'implémentation Synthèse Stratégique (15 étapes)

```
S.1   ADR-023 Synthèse Stratégique (matrice SoT par chiffre)               1 j/h
S.2   backend/services/strategique/trajectory_service.py                    2 j/h
S.3   backend/services/strategique/economic_performance_service.py          2 j/h
S.4   backend/services/strategique/benchmark_service.py                     2 j/h
S.5   backend/services/strategique/external_risk_service.py                 2 j/h
S.6   highlights_detectors.detect_strategic_findings (Capacité/CBAM/ARENH)  2 j/h
S.7   backend/routes/cockpit_strategique.py — endpoint + 5 builders         3 j/h
S.8   pytest test_trajectory + test_economic_performance + source_guards    2 j/h
S.9   frontend/src/components/grammar/hub/charts/ChartFrameTrajectoryLine   2 j/h
S.10  frontend/src/components/grammar/hub/charts/ChartFrameMixHorizontal    1 j/h
S.11  frontend/src/pages/CockpitStrategique.jsx (mirror CockpitJour)        2 j/h
S.12  services/api/cockpit.js — getCockpitStrategique                      0.5 j/h
S.13  App.jsx route /cockpit/strategique                                   0.5 j/h
S.14  Recapture Playwright synthese_after_S/                                1 j/h
S.15  Atomic commit S.x — feat(p3.5): synthèse stratégique data-driven      —
```

**Total ≈ 23-25 j/h** pour une page strat data-driven complète.

---

## 13. Différences cibles Synthèse vs Briefing

### 13.1 KPIs

| KPI | Briefing du Jour | Synthèse Stratégique |
|---|---|---|
| 1 | Conso mois courant (MWh, vs N-1) | **Trajectoire DT 2030 (%, vs cible idéale)** |
| 2 | Conso J-1 (MWh, vs baseline DJU) | **Coût moyen €/MWh (12m, vs benchmark NAF P50)** |
| 3 | Pic puissance hier (kW, vs souscrite) | **Reclaim potentiel (k€, anomalies billing 12m)** |

### 13.2 Charts

| Chart | Briefing du Jour | Synthèse Stratégique |
|---|---|---|
| 1 | Bar daily 7j (annotation worst day) | **Trajectory line 2020 → 2030 (milestones DT)** |
| 2 | Line 24h HP/HC (peak + threshold) | **Mix achat horizontal (fixe/indexé/spot, current vs optimal)** |

### 13.3 Hero narratif

- **Briefing** : « 3 signaux méritent votre attention sur le groupe HELIOS. »
  + « Lyon : EMS connector à vérifier. Toulouse : facture R27 à reclaim. »
- **Synthèse** : « Trajectoire DT 2030 tenable à 73 % · 4 leviers d'arbitrage. »
  + « Lyon dérive +28 % cible 2030 · Paris en avance · Marseille à confirmer. »

### 13.4 Highlights

- **Briefing** : 3 catégories différentes × 3 sites différents (dédup) — top
  scoring `responsable_energie`.
- **Synthèse** : 3-5 arbitrages stratégiques — top scoring `dg_comex`,
  hub=`COCKPIT_STRATEGIQUE` (STRATEGIQUE prime), dédup par (catégorie, portefeuille).

### 13.5 CTA Hero + Highlights

- **Briefing** : « Voir le centre d'action » + verbes (voir/vérifier/programmer)
- **Synthèse** : « Voir les arbitrages détaillés » + verbes (arbitrer/simuler/comparer/contester)

---

## 14. Référence canonique des fichiers

Pour copier le pattern :

```
backend/
├─ routes/cockpit.py                          (lignes 2029-2683 — 5 builders + endpoint)
├─ regops/priority_scoring.py                 (380 lignes — algo doctrine v1)
├─ services/cockpit_highlights_service.py     (240 lignes — agrégateur)
├─ services/highlights_detectors.py           (380 lignes — 3 détecteurs)
├─ services/consumption_granularity_service.py (360 lignes — daily/hourly/peak/baseline DJU)
└─ services/tariff_periods_service.py         (180 lignes — HP/HC dynamiques)

frontend/
├─ pages/CockpitJour.jsx                      (245 lignes — page complète)
├─ components/grammar/hub/HubHighlight.jsx    (340 lignes — avec PriorityProof inline)
├─ components/grammar/hub/PriorityProofModal.jsx (265 lignes — modal méthodologie)
├─ components/PersonaToggle.jsx               (85 lignes — toggle topbar conditional)
├─ contexts/PersonaContext.jsx                (75 lignes — toggle + dataQualityPct)
├─ services/api/cockpit.js                    (getCockpitJour ligne 136)
├─ ui/sol/tokens.css                          (300 lignes — design tokens canoniques)
└─ index.css                                  (750 lignes — Tailwind → Sol cascade)

docs/
├─ adr/ADR-022-cockpit-data-sources.md        (164 lignes — doctrine cockpit data sources)
├─ vision/promeos_sol_doctrine.md             (doctrine Sol v1.1 complète)
└─ doctrine/BRIEFING_BLUEPRINT_FOR_SYNTHESE_STRATEGIQUE.md  (CE FICHIER)
```

---

## 15. Règles non-négociables (résumé)

1. **Zéro hardcode chiffre** dans `routes/cockpit_strategique.py` — toujours via service.
2. **Zéro business logic frontend** — affichage uniquement, calculs backend.
3. **Source-guards pytest** obligatoires (mirror `test_cockpit_no_hardcode.py`).
4. **Audit trail `_audit`** sur chaque highlight (ADR-022 anti-AP5).
5. **PriorityProof badge + modal** sur chaque highlight (transparence).
6. **3 personas activables** (toggle existant à réutiliser).
7. **Plages tarifaires depuis contrat** si applicable, fallback TURPE 6.
8. **Baseline DJU-adjusted** pour toute comparaison saisonnière.
9. **HUB_CAT_ORDER** = `COCKPIT_STRATEGIQUE` pour départage.
10. **Loi L11** respectée : 1 hero + 3 KPIs + 2 charts + 3-5 highlights + 1 footer.
11. **Anti-pattern AP3** : dédup catégorie ET (site OU portefeuille) sur Top N.
12. **Anti-pattern AP6** : si `dataQualityPct < 80`, désactiver toggle DAF/DG.
13. **Anti-pattern AP4** : aucune valeur magique dans le JSX (toutes via API).
14. **Tokens Sol** uniquement (`var(--sol-*)`, jamais `#xxxxxx`).
15. **Doctrine version** tracée dans chaque `_audit.doctrine_version`.

---

## 16. Checklist DoD (Definition of Done) Synthèse Stratégique

```
DOCTRINE
[ ] ADR-023 rédigé et committé
[ ] Matrice SoT par chiffre Synthèse documentée
[ ] HUB_CAT_ORDER[COCKPIT_STRATEGIQUE] respecté

BACKEND
[ ] 4 nouveaux services strategique/ créés (trajectory, economic, benchmark, external_risk)
[ ] highlights_detectors étendu avec detect_strategic_findings
[ ] routes/cockpit_strategique.py — 5 builders + endpoint /api/cockpit/strategique
[ ] Endpoint accepte ?persona (default dg_comex) + ?horizon_year=2030
[ ] Fallback "données partielles" sur chaque KPI si service None
[ ] Helper _latest_data_day réutilisé OU dupliqué

TESTS
[ ] pytest test_trajectory_service ≥ 10 tests
[ ] pytest test_economic_performance_service ≥ 8 tests
[ ] pytest source_guards/test_strategique_no_hardcode ≥ 8 tests
[ ] Vitest 72/72 inchangés

FRONTEND
[ ] pages/CockpitStrategique.jsx (mirror CockpitJour.jsx)
[ ] services/api/cockpit.js — getCockpitStrategique()
[ ] App.jsx — route /cockpit/strategique enregistrée
[ ] Au moins 1 nouveau primitif chart (TrajectoryLine ou MixHorizontal)
[ ] Tous les highlights ont badge PriorityProof + modal cliquable

VISUEL
[ ] Recapture Playwright phase synthese
[ ] Toutes les couleurs via tokens Sol
[ ] Toutes les fontes via Fraunces/DM Sans/JetBrains Mono
[ ] Loi L11 respectée (composition 1 hero + 3 KPIs + 2 charts + N highlights + footer)
[ ] Toggle persona DG-COMEX par défaut testé
[ ] Modal méthodologie cliquable sur les 3 highlights

DEMO HELIOS
[ ] 3 KPIs affichent des valeurs cohérentes (trajectoire % + €/MWh + reclaim k€)
[ ] 2 charts data-driven (trajectoire 2020-2030 + mix achat actuel/optimal)
[ ] 3-5 highlights avec différentes catégories STRATEGIQUE/FINANCIER prioritaires
[ ] Hero narratif "Trajectoire DT 2030 tenable à X % · N leviers..."

DOCTRINE
[ ] Aucun hex hardcoded dans /pages/CockpitStrategique.jsx
[ ] Aucun calcul métier dans le JSX
[ ] Audit trail _audit sur chaque highlight
[ ] Doctrine version tracée
[ ] Source-guards anti-régression actifs
```

---

**FIN DU DOCUMENT.**

Ce brief est suffisant pour qu'un agent Claude Code reproduise le pattern
Briefing du Jour sur la page Synthèse Stratégique en respectant toute la
doctrine PROMEOS Sol v1.1 + algorithme priorisation v1.0 + design system
Sol + ergonomie L11.

Référence canonique : commit `32916787` (branche `claude/refonte-sol2`).
Pour vérifier le rendu cible : ouvrir `http://localhost:5175/cockpit/jour`
en environnement local (port 5175 = refonte-sol2).
