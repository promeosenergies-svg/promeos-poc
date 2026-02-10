# KNOWLEDGE BASE STRUCTURE - PROMEOS POC
**Date**: 2026-02-09
**Purpose**: Organize all compliance, regulatory, and technical knowledge

---

## OVERVIEW

The PROMEOS Knowledge Base (KB) is a **structured repository** of:
- **Regulatory texts** (PDFs, laws, decrees)
- **Technical decisions** (ADRs - Architecture Decision Records)
- **Compliance proofs** (evidence templates, checklists)
- **AI prompts** (versioned prompt templates)
- **Regulations** (YAML configs + mappings)
- **Playbooks** (operational runbooks)

**Location**: `docs/kb/`

---

## DIRECTORY STRUCTURE

```
docs/kb/
├── README.md                    # KB index + navigation
├── sources/                     # 📚 Regulatory source documents
│   ├── tertiaire/
│   │   ├── decret_2019_771.pdf
│   │   ├── arrete_2021_0428.pdf
│   │   └── guide_operat_2023.pdf
│   ├── bacs/
│   │   ├── decret_2020_887.pdf
│   │   └── nf_en_iso_52120_2022.pdf
│   ├── aper/
│   │   ├── loi_2023_1322.pdf
│   │   └── arrete_aper_2024.pdf
│   ├── cee/
│   │   ├── arrete_p6_2022.pdf
│   │   └── catalogue_cee_2024.pdf
│   └── energy/
│       ├── arenh_decision_cre_2025.pdf
│       └── market_rules_epex_2024.pdf
├── decisions/                   # 🔍 Architecture Decision Records
│   ├── README.md
│   ├── 001_sqlite_vs_postgres.md
│   ├── 002_job_outbox_pattern.md
│   ├── 003_ai_never_modifies_status.md
│   ├── 004_yaml_driven_rules.md
│   ├── 005_stub_mode_for_ai.md
│   ├── 006_hash_based_caching.md
│   ├── 007_polymorphic_object_refs.md
│   └── 008_evidence_first_design.md
├── proofs/                      # ✅ Compliance evidence templates
│   ├── README.md
│   ├── tertiaire/
│   │   ├── attestation_operat_template.md
│   │   ├── checklist_declaration.md
│   │   └── example_attestation.pdf
│   ├── bacs/
│   │   ├── certificat_installation_template.md
│   │   ├── checklist_inspection.md
│   │   └── example_certificat.pdf
│   ├── aper/
│   │   ├── etude_faisabilite_template.md
│   │   └── checklist_ombriere.md
│   └── cee/
│       ├── audit_energetique_template.md
│       └── checklist_p6.md
├── prompts/                     # 🤖 AI prompt templates (versioned)
│   ├── README.md
│   ├── regops/
│   │   ├── explain_site_v1.md
│   │   ├── explain_site_v2.md (current)
│   │   ├── recommend_actions_v1.md
│   │   ├── data_quality_v1.md
│   │   ├── reg_change_impact_v1.md
│   │   └── exec_brief_v1.md
│   ├── bills/
│   │   ├── detect_anomaly_v1.md
│   │   └── suggest_tariff_v1.md
│   └── procurement/
│       ├── simulate_scenario_v1.md
│       └── hedge_strategy_v1.md
├── regulations/                 # 📋 YAML configs + mappings
│   ├── README.md
│   ├── regs.yaml                # Master config (copy from backend/regops/config/)
│   ├── naf_profiles.yaml
│   ├── location_profiles.yaml
│   ├── cee_p6_catalog.yaml
│   ├── mappings/
│   │   ├── naf_to_usage.csv     # NAF code → usage family mapping
│   │   ├── region_to_climate.csv # Region → climate zone
│   │   └── cee_to_actions.csv   # CEE code → action hints
│   └── changelog.md             # History of config changes
└── playbooks/                   # 📖 Operational runbooks
    ├── README.md
    ├── regops_audit.md          # How to run manual audit
    ├── connector_setup.md       # How to configure connectors
    ├── watcher_config.md        # How to add new watchers
    ├── ai_agent_add.md          # How to create new AI agent
    ├── incident_response.md     # How to handle compliance incidents
    └── data_quality_triage.md   # How to diagnose missing data
```

---

## CONVENTIONS

### 1. File Naming

- **PDFs**: `{regulation}_{doc_type}_{year}.pdf` (e.g., `decret_2019_771.pdf`)
- **ADRs**: `{number}_{short_title}.md` (e.g., `001_sqlite_vs_postgres.md`)
- **Prompts**: `{purpose}_v{version}.md` (e.g., `explain_site_v2.md`)
- **Templates**: `{doc_type}_template.md` (e.g., `attestation_operat_template.md`)
- **Mappings**: `{source}_to_{target}.csv` (e.g., `naf_to_usage.csv`)

### 2. Markdown Headers

All markdown files must start with YAML front matter:

```markdown
---
title: "ADR 003: AI Never Modifies Status"
date: 2026-01-15
status: ACCEPTED
author: PROMEOS Team
tags: [ai, compliance, hard-rule]
---

# ADR 003: AI Never Modifies Status

## Context
...
```

### 3. Versioning

- **Prompts**: Increment version on every change (v1, v2, v3...)
- **YAML configs**: Track in `changelog.md` with date + reason
- **ADRs**: Immutable once accepted (create new ADR to supersede)

### 4. Cross-References

Use relative links:

```markdown
See [ADR 002: Job Outbox Pattern](../decisions/002_job_outbox_pattern.md)
See [Tertiaire Decree](../sources/tertiaire/decret_2019_771.pdf)
See [Evidence Template](../proofs/bacs/certificat_installation_template.md)
```

---

## SOURCES (`docs/kb/sources/`)

### Purpose

Store **original regulatory documents** (PDFs, links).

### Structure

```
sources/
├── tertiaire/          # Décret Tertiaire / OPERAT
├── bacs/               # BACS / GTB
├── aper/               # APER (solar parking/roofs)
├── cee/                # CEE P6 (energy audit)
├── energy/             # ARENH, market rules, tariffs
└── misc/               # Other regulations (RE2020, CSRD, etc.)
```

### README Template (`sources/README.md`)

```markdown
# Regulatory Sources

## Tertiaire / OPERAT

- **Décret n°2019-771** (23/07/2019): Décret tertiaire, obligations de réduction
  - File: [decret_2019_771.pdf](tertiaire/decret_2019_771.pdf)
  - URL: https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000038812251

- **Arrêté OPERAT** (10/04/2021): Modalités de déclaration
  - File: [arrete_2021_0428.pdf](tertiaire/arrete_2021_0428.pdf)
  - URL: https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000043327711

## BACS

- **Décret n°2020-887** (22/07/2020): Obligation GTB
  - File: [decret_2020_887.pdf](bacs/decret_2020_887.pdf)
  - URL: https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000042156437
```

---

## DECISIONS (`docs/kb/decisions/`)

### Purpose

Document **architectural and technical decisions** (ADRs).

### ADR Template

```markdown
---
title: "ADR {number}: {Title}"
date: YYYY-MM-DD
status: PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED
author: {Name}
tags: [tag1, tag2]
supersedes: ADR {number} (if applicable)
---

# ADR {number}: {Title}

## Status

**{PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED}** on {date}

## Context

What is the issue we're facing? What constraints exist?

## Decision

What did we decide to do?

## Consequences

- **Positive**: What benefits does this bring?
- **Negative**: What tradeoffs or risks?
- **Neutral**: What else changes?

## Alternatives Considered

1. **Option 1**: Why rejected?
2. **Option 2**: Why rejected?

## References

- [Related ADR](./002_another_decision.md)
- [Documentation](../playbooks/some_playbook.md)
```

### Existing ADRs (To Create)

1. **ADR 001: SQLite vs PostgreSQL**
   - Decision: SQLite for dev, PostgreSQL for prod
   - Rationale: Simplicity vs concurrency

2. **ADR 002: Job Outbox Pattern**
   - Decision: Async jobs via outbox table (no SQLAlchemy events)
   - Rationale: Avoid recursion, explicit job queue

3. **ADR 003: AI Never Modifies Status**
   - Decision: AI agents create AiInsight, never update Site/RegAssessment status
   - Rationale: Trust deterministic rules, AI only suggests

4. **ADR 004: YAML-Driven Rules**
   - Decision: Externalize thresholds/deadlines to YAML (not hardcoded)
   - Rationale: Regulatory changes = config update, not code deploy

5. **ADR 005: Stub Mode for AI**
   - Decision: AI client returns mock responses if no API_KEY
   - Rationale: Allow testing without AI costs

6. **ADR 006: Hash-Based Caching**
   - Decision: Cache RegAssessment with deterministic_version + data_version hashes
   - Rationale: Invalidate cache only when rules or data change

7. **ADR 007: Polymorphic Object References**
   - Decision: Use (object_type, object_id) pattern (not separate FKs per type)
   - Rationale: Flexible, avoids table explosion

8. **ADR 008: Evidence-First Design**
   - Decision: All compliance assessments must reference source data (evidence, datapoints)
   - Rationale: Auditability, traceability

---

## PROOFS (`docs/kb/proofs/`)

### Purpose

Store **compliance evidence templates** and **checklists**.

### Structure

```
proofs/
├── tertiaire/
│   ├── attestation_operat_template.md  # Template for OPERAT attestation
│   ├── checklist_declaration.md        # Checklist before submitting
│   └── example_attestation.pdf         # Real example (anonymized)
├── bacs/
│   ├── certificat_installation_template.md
│   ├── checklist_inspection.md
│   └── example_certificat.pdf
├── aper/
│   ├── etude_faisabilite_template.md
│   └── checklist_ombriere.md
└── cee/
    ├── audit_energetique_template.md
    └── checklist_p6.md
```

### Template Format (`attestation_operat_template.md`)

```markdown
---
regulation: TERTIAIRE_OPERAT
doc_type: ATTESTATION
deadline: 2026-07-01
authority: ADEME via plateforme OPERAT
---

# Attestation d'affichage OPERAT

## Informations requises

### Site
- [ ] Nom du site
- [ ] Adresse complète
- [ ] Surface tertiaire assujettie (m²)
- [ ] Code INSEE commune

### Consommations
- [ ] Consommation année de référence (kWh)
- [ ] Année de référence choisie
- [ ] Consommation année N-1 (kWh)

### Objectifs
- [ ] Objectif 2030 (% réduction ou kWh/m²)
- [ ] Objectif 2040 (% réduction ou kWh/m²)
- [ ] Objectif 2050 (% réduction ou kWh/m²)

## Documents à joindre

1. Plan cadastral du site
2. Factures énergétiques (3 dernières années)
3. Justificatif d'activité (Kbis, bail)
4. Attestation de propriété/locataire

## Procédure de soumission

1. Créer un compte sur https://operat.ademe.fr
2. Renseigner les données du site
3. Télécharger les justificatifs
4. Valider et soumettre
5. Télécharger l'attestation générée
6. Afficher l'attestation à l'entrée du bâtiment (visible du public)

## Sanctions en cas de non-conformité

- Absence d'attestation: Amende jusqu'à 7500 EUR
- Déclaration erronée: Mise en demeure + amende

## Références

- [Décret 2019-771](../sources/tertiaire/decret_2019_771.pdf)
- [Guide OPERAT](../sources/tertiaire/guide_operat_2023.pdf)
- [Plateforme OPERAT](https://operat.ademe.fr)
```

---

## PROMPTS (`docs/kb/prompts/`)

### Purpose

Store **versioned AI prompt templates**.

### Structure

```
prompts/
├── README.md               # Prompt index + changelog
├── regops/
│   ├── explain_site_v1.md  # Version 1 (deprecated)
│   ├── explain_site_v2.md  # Version 2 (current)
│   └── ...
├── bills/
│   └── ...
└── procurement/
    └── ...
```

### Prompt Template Format

```markdown
---
version: v2
created: 2026-01-20
status: CURRENT
replaces: v1
model: claude-sonnet-4-5
max_tokens: 2000
temperature: 0.3
---

# RegOps Explainer: Site Compliance Brief (v2)

## System Prompt

```
You are a French regulatory compliance expert specializing in energy regulations (Décret Tertiaire, BACS, APER).

Your task: Explain a site's compliance status to a non-technical facility manager in 2-3 minutes of reading.

RULES:
- Use simple French (no legal jargon)
- Focus on actionable insights (what to do next)
- NEVER invent data (if unknown, say "données manquantes")
- ALWAYS cite source (regulation name + article)
- Use bullet points for clarity
```

## User Prompt Template

```
Site: {site_name} ({site_type}, {surface_m2} m²)

Données disponibles:
{data_summary}

Résultats d'évaluation RegOps:
{regops_findings}

Question: Rédige un résumé de la conformité réglementaire de ce site en 2-3 paragraphes. Quelles sont les 3 actions prioritaires?
```

## Variables

- `{site_name}`: str
- `{site_type}`: str (BUREAU, MAGASIN, etc.)
- `{surface_m2}`: float
- `{data_summary}`: str (JSON formatted)
- `{regops_findings}`: str (JSON formatted)

## Example Output

```
**Résumé de conformité pour Carrefour Paris 15e**

✅ **Décret Tertiaire**: Ce site de 2500m² est dans le champ d'application. Aucune déclaration OPERAT n'a encore été faite (données manquantes). Échéance critique : 30 sept 2026.

⚠️ **BACS**: La puissance CVC (350 kW) impose l'installation d'une GTB avant le 1er janv 2025. Aucun certificat d'installation n'est présent dans les preuves. Risque de non-conformité.

✅ **APER**: Parking extérieur de 8000m² → obligation ombrières solaires (échéance 1er juil 2026). Une étude de faisabilité est recommandée (6 mois de délai).

**Actions prioritaires**:
1. Collecter statut OPERAT + consommations annuelles (urgence: haute)
2. Planifier installation GTB (échéance: 11 mois)
3. Lancer étude ombrières solaires (échéance: 16 mois)

Sources: Décret 2019-771 (Tertiaire), Décret 2020-887 (BACS), Loi 2023-1322 (APER)
```

## Changelog

- **v2** (2026-01-20): Added APER regulation, improved action prioritization
- **v1** (2026-01-10): Initial version (Tertiaire + BACS only)
```

---

## REGULATIONS (`docs/kb/regulations/`)

### Purpose

Store **YAML configs** and **CSV mappings** used by RegOps engine.

### Structure

```
regulations/
├── README.md                   # Explain structure + changelog
├── regs.yaml                   # Master config (sync from backend/regops/config/)
├── naf_profiles.yaml
├── location_profiles.yaml
├── cee_p6_catalog.yaml
├── mappings/
│   ├── naf_to_usage.csv        # NAF → usage family
│   ├── region_to_climate.csv   # Region → H1/H2/H3
│   └── cee_to_actions.csv      # CEE code → hints
└── changelog.md                # History of changes
```

### Changelog Format (`changelog.md`)

```markdown
# Regulations Changelog

## 2026-02-09 - BACS threshold update

**Change**: Updated BACS low threshold from 70kW to 75kW (Décret 2026-123)

**Files**:
- `regs.yaml`: `bacs.thresholds.low_kw: 70 → 75`

**Impact**: ~5 sites move from CRITICAL to OUT_OF_SCOPE

**Reference**: [Décret 2026-123](../sources/bacs/decret_2026_123.pdf)

---

## 2026-01-15 - CEE P6 catalog update

**Change**: Added 3 new action codes (BAT-TH-180, BAT-EN-105, BAT-EN-106)

**Files**:
- `cee_p6_catalog.yaml`: Added entries

**Impact**: More granular CEE hints for insulation actions

**Reference**: [Arrêté CEE 2026](../sources/cee/arrete_cee_2026.pdf)
```

---

## PLAYBOOKS (`docs/kb/playbooks/`)

### Purpose

**Operational runbooks** for common tasks.

### Structure

```
playbooks/
├── README.md
├── regops_audit.md             # Manual compliance audit
├── connector_setup.md          # Configure external connectors
├── watcher_config.md           # Add new regulatory watcher
├── ai_agent_add.md             # Create custom AI agent
├── incident_response.md        # Handle compliance incidents
├── data_quality_triage.md      # Diagnose missing data
├── deployment.md               # Deploy new version
└── backup_restore.md           # Backup/restore DB
```

### Playbook Format (`regops_audit.md`)

```markdown
---
title: "Playbook: Manual RegOps Audit"
author: PROMEOS Team
last_updated: 2026-02-09
estimated_time: 2 hours (120 sites)
---

# Playbook: Manual RegOps Audit

## Purpose

Manually audit compliance status for all sites (when automated engine fails or needs validation).

## Prerequisites

- [ ] Access to PROMEOS backend (`backend/` directory)
- [ ] Python 3.14+ with venv activated
- [ ] Database access (`promeos.db`)
- [ ] Access to regulatory sources (`docs/kb/sources/`)

## Steps

### 1. Collect Site Data

```bash
cd backend
python -c "
from models import Site
from db import SessionLocal
db = SessionLocal()
sites = db.query(Site).all()
for s in sites:
    print(f'{s.id},{s.nom},{s.tertiaire_area_m2},{s.parking_area_m2}')
" > audit_sites.csv
```

### 2. Check Tertiaire Scope

For each site:
- ✅ tertiaire_area_m2 >= 1000 → IN_SCOPE
- ❌ tertiaire_area_m2 < 1000 → OUT_OF_SCOPE
- ⚠️ tertiaire_area_m2 IS NULL → UNKNOWN

**Reference**: [Décret 2019-771, Article 1](../sources/tertiaire/decret_2019_771.pdf#page=1)

### 3. Check OPERAT Status

For each IN_SCOPE site:
- ✅ operat_status = SUBMITTED → COMPLIANT (if < 1 year old)
- ⚠️ operat_status = IN_PROGRESS → AT_RISK
- ❌ operat_status = NOT_STARTED → NON_COMPLIANT
- ⚠️ operat_status IS NULL → UNKNOWN

**Deadline**: 2026-09-30 (declaration), 2026-07-01 (attestation)

### 4. Check BACS

For each site with batiments:
- Calculate max CVC power: `max(batiments.cvc_power_kw)`
- ✅ > 290 kW → CRITICAL (deadline 2025-01-01)
- ⚠️ 70-290 kW → MEDIUM (deadline 2030-01-01)
- ✅ < 70 kW → OUT_OF_SCOPE

**Reference**: [Décret 2020-887, Article 2](../sources/bacs/decret_2020_887.pdf#page=2)

### 5. Generate Report

```bash
python scripts/generate_audit_report.py --input audit_sites.csv --output audit_report.pdf
```

## Output

- CSV: `audit_sites.csv` (raw data)
- PDF: `audit_report.pdf` (formatted report with charts)

## Troubleshooting

### Issue: Missing tertiaire_area_m2 for many sites

**Solution**: Use proxy from surface_m2 (for BUREAU/MAGASIN, assume 100% tertiary)

```python
if site.type in [TypeSite.BUREAU, TypeSite.MAGASIN] and site.tertiaire_area_m2 is None:
    site.tertiaire_area_m2 = site.surface_m2
```

### Issue: No batiments for site

**Solution**: Cannot assess BACS → mark as UNKNOWN

## References

- [RegOps Ultimate Guide](../../regops_ultimate.md)
- [ADR 004: YAML-Driven Rules](../decisions/004_yaml_driven_rules.md)
- [API: GET /api/regops/site/{id}](../../audit/API_MAP.md)
```

---

## KB MAINTENANCE

### Weekly Tasks

1. **Update regulatory sources**: Check Legifrance RSS (via watchers)
2. **Review ADRs**: Any decisions from past week?
3. **Update prompts**: AI performance issues → new prompt version
4. **Sync YAML configs**: Backend changes → copy to KB

### Monthly Tasks

1. **Audit proofs**: Are templates up-to-date with latest regulations?
2. **Review playbooks**: Any new operational patterns?
3. **Cleanup**: Archive deprecated prompts/ADRs

### Quarterly Tasks

1. **Regulatory review**: Full audit of all sources (new laws?)
2. **KB index rebuild**: Update all READMEs
3. **Mappings update**: NAF codes, climate zones, CEE catalog

---

## SEARCH & DISCOVERY

### KB Index (`docs/kb/README.md`)

```markdown
# PROMEOS Knowledge Base

## Quick Links

- [Regulatory Sources](sources/README.md) - Original PDFs and links
- [Architectural Decisions](decisions/README.md) - ADRs
- [Evidence Templates](proofs/README.md) - Compliance checklists
- [AI Prompts](prompts/README.md) - Versioned prompts
- [Regulations Config](regulations/README.md) - YAML + mappings
- [Playbooks](playbooks/README.md) - Operational guides

## Search by Tag

### By Regulation
- [Tertiaire/OPERAT](sources/tertiaire/) - Décret 2019-771
- [BACS](sources/bacs/) - Décret 2020-887
- [APER](sources/aper/) - Loi 2023-1322
- [CEE P6](sources/cee/) - Arrêté P6

### By Topic
- [Compliance](proofs/) - Evidence templates
- [AI](prompts/) - Prompt templates
- [Architecture](decisions/) - ADRs
- [Operations](playbooks/) - Runbooks

## Recent Updates

- 2026-02-09: Added BACS threshold update (changelog)
- 2026-01-20: New AI prompt version (explain_site_v2)
- 2026-01-15: CEE P6 catalog update

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
```

### Search Script

```bash
#!/bin/bash
# kb_search.sh - Search KB by keyword

KEYWORD=$1
KB_DIR="docs/kb"

echo "Searching KB for: $KEYWORD"
echo ""

echo "=== Sources ==="
grep -r -i "$KEYWORD" $KB_DIR/sources/ | head -5

echo ""
echo "=== Decisions ==="
grep -r -i "$KEYWORD" $KB_DIR/decisions/ | head -5

echo ""
echo "=== Prompts ==="
grep -r -i "$KEYWORD" $KB_DIR/prompts/ | head -5
```

---

## INTEGRATION WITH CODE

### Backend References KB

```python
# backend/regops/engine.py
import os

KB_PATH = os.path.join(os.path.dirname(__file__), '../../docs/kb')

def _load_configs():
    """Load YAML configs from KB"""
    config_path = os.path.join(KB_PATH, 'regulations/regs.yaml')
    with open(config_path) as f:
        return yaml.safe_load(f)
```

### AI Agents Load Prompts from KB

```python
# backend/ai_layer/agents/regops_explainer.py
import os

PROMPT_PATH = os.path.join(os.path.dirname(__file__), '../../../docs/kb/prompts/regops')

def load_prompt(version="v2"):
    """Load versioned prompt template"""
    prompt_file = os.path.join(PROMPT_PATH, f'explain_site_{version}.md')
    with open(prompt_file) as f:
        content = f.read()
        # Parse YAML front matter + prompt body
        ...
```

---

## NEXT STEPS

1. **Immediate** (Tonight):
   - Create KB directory structure (5 min)
   - Create README files (15 min)
   - Copy regs.yaml to KB (2 min)

2. **Short Term** (This Week):
   - Write 8 ADRs (4 hours)
   - Create 4 evidence templates (2 hours)
   - Create 5 playbooks (3 hours)

3. **Medium Term** (This Month):
   - Collect regulatory PDFs (scan Legifrance) (4 hours)
   - Version all AI prompts (2 hours)
   - Create CSV mappings (NAF, regions) (2 hours)

---

**Status**: 🟢 **READY** - Structure defined, KB can be populated incrementally
**Priority**: Low (nice-to-have, not blocking)
**Reference**: See INVENTORY.md for current data/configs location
