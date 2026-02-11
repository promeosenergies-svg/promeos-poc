# KB Runbook — Bill Intelligence

## 1. Ajouter un document dans la KB

### Via API
```bash
curl -X POST http://localhost:8000/api/kb/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "cre_turpe7_grilles_2026",
    "title": "Grilles tarifaires TURPE 7 - 2026",
    "file_path": "data/kb/raw/turpe7_grilles_2026.html",
    "source_org": "CRE",
    "doc_type": "grille",
    "published_date": "2025-12-15",
    "effective_from": "2026-01-01",
    "effective_to": "2026-12-31"
  }'
```

### Via script Python
```python
from app.kb.doc_ingest import ingest_document

result = ingest_document(
    doc_id="mon_doc",
    title="Mon document",
    file_path="data/kb/raw/mon_doc.html",
    source_org="CRE",
    doc_type="deliberation",
)
print(result)
```

### Via ingestion auto des snapshots referentiel
```bash
cd backend
python scripts/ingest_referential_to_kb.py
# OU via API:
curl -X POST http://localhost:8000/api/kb/ingest-referential
```

## 2. Rechercher dans la KB

### Recherche dans les chunks (citations)
```bash
curl -X POST http://localhost:8000/api/kb/search-docs \
  -H "Content-Type: application/json" \
  -d '{"q": "TURPE tarif acheminement", "limit": 5}'
```

### Recherche dans les items KB (archetypes, regles)
```bash
curl -X POST http://localhost:8000/api/kb/search \
  -H "Content-Type: application/json" \
  -d '{"q": "consommation bureau", "domain": "usages", "limit": 10}'
```

## 3. Creer une Citation

Les citations sont creees automatiquement lors de la creation de RuleCards,
ou peuvent etre creees manuellement via le code Python :

```python
from app.kb.citations import create_citation

cite = create_citation(
    doc_id="cre_turpe6_hta_bt_2025_02",
    doc_title="TURPE 6 HTA-BT",
    excerpt_text="La composante de gestion annuelle s'eleve a 145,92 EUR/an.",
    pointer_section="Section 3.1",
    pointer_article="Art. L.341-2",
    confidence="high",
)
```

## 4. Creer une RuleCard

### Via API
```bash
curl -X POST http://localhost:8000/api/kb/extract-rule \
  -H "Content-Type: application/json" \
  -d '{
    "rule_card_id": "RULE_TVA_TAUX",
    "name": "Taux TVA applicable",
    "scope": "both",
    "category": "vat",
    "intent": "Verifier le taux de TVA applique (5.5% abonnement, 20% conso elec)",
    "formula_or_check": "tva_rate IN (5.5, 20.0) selon composante",
    "inputs_needed": ["component.tva_rate", "component.component_type"],
    "citation_ids": ["cite_xxx_yyy"],
    "effective_from": "2024-01-01"
  }'
```

### Via Python
```python
from app.kb.citations import create_citation, create_rule_card

cite = create_citation(
    doc_id="bofip_tva",
    doc_title="TVA Energie BOFiP",
    excerpt_text="Taux reduit de 5,5% sur abonnement et CTA...",
)

card = create_rule_card(
    rule_card_id="RULE_TVA_TAUX",
    name="Taux TVA applicable",
    scope="both",
    category="vat",
    intent="Verifier taux TVA",
    formula_or_check="tva_rate IN (5.5, 20.0)",
    citation_ids=[cite["citation_id"]],
)
```

## 5. Lister les RuleCards et verifier P5

```bash
# Lister toutes les RuleCards
curl http://localhost:8000/api/kb/rule-cards

# Filtrer par scope
curl http://localhost:8000/api/kb/rule-cards?scope=elec

# Statistiques P5
curl http://localhost:8000/api/kb/rule-card-stats
# Reponse : { "p5_compliant": true/false, "rules_without_citations": 0 }
```

## 6. Verifier la coherence source-registry ↔ doc_id

Le fichier `docs/bill_intelligence/source-registry.md` liste les sources
normatives et leur `doc_id` KB. Verifier :

1. Chaque `doc_id` reference dans source-registry existe dans la KB :
   ```bash
   curl http://localhost:8000/api/kb/docs/{doc_id}
   ```

2. Chaque RuleCard normative a au moins 1 citation :
   ```bash
   curl http://localhost:8000/api/kb/rule-card-stats
   # rules_without_citations doit etre 0 pour les regles ACTIVE
   ```

## 7. Reindexer la KB

```bash
curl -X POST http://localhost:8000/api/kb/reindex
```

## 8. Formats de fichiers acceptes

| Format | Extension | Extraction |
|--------|-----------|------------|
| HTML | .html, .htm | HTML → Markdown (stdlib html.parser) |
| Texte | .txt | Passthrough |
| Markdown | .md | Passthrough |
| PDF | .pdf | NON SUPPORTE en V1 POC (TODO) |

## 9. Conventions doc_id

- Format : `{source}_{regulation}_{detail}_{date_hint}`
- Exemples : `cre_turpe6_hta_bt_2025_02`, `legifrance_cibs_accise_electricite`
- Caracteres : `[a-z0-9_]` uniquement
- Unique dans toute la KB
