# PROMEOS - Audit Report PDF V1 (Sprint 10.1)

## Objectif

Rapport d'audit energetique multi-briques, telechargeable en 1 clic depuis le Plan d'action. PDF B2B pro, 3-8 pages, avec indice de confiance.

## Endpoints

| Methode | Path | Description |
|---------|------|-------------|
| GET | `/api/reports/audit.pdf?org_id=` | Telecharge le PDF |
| GET | `/api/reports/audit.json?org_id=` | Donnees structurees JSON |

## Sections du rapport

1. **Page de garde + Synthese executive** : KPI (risque EUR, gain potentiel, conformite %, actions ouvertes), indice de confiance (low/medium/high)
2. **Conformite reglementaire** : total findings OK/NOK/inconnus, top 5 non-conformites
3. **Diagnostics de consommation** : anomalies detectees, pertes EUR/an, top 5 insights
4. **Anomalies de facturation** : ecarts detectes, top 5 billing insights
5. **Achats energie** : strategie recommandee, scenarios evalues
6. **Plan d'action** : total actions, repartition par source, top 5 prioritaires

## Indice de confiance

Calcule a partir du volume de donnees :
- **High** : >= 5 compliance findings + >= 2 conso insights + >= 2 billing insights
- **Medium** : 2 des 3 criteres remplis
- **Low** : < 2 criteres remplis

## Architecture

```
backend/services/audit_report_service.py
  ├── build_audit_report_data(db, org_id) -> dict
  │     ├── _build_compliance_section()
  │     ├── _build_consumption_section()
  │     ├── _build_billing_section()
  │     ├── _build_purchase_section()
  │     └── _build_actions_section()
  └── render_audit_pdf(data) -> bytes (reportlab)

backend/routes/reports.py
  ├── GET /api/reports/audit.json
  └── GET /api/reports/audit.pdf
```

## Frontend

- Bouton "Rapport PDF" dans ActionsPage header (icone FileText)
- Fonction `downloadAuditPDF()` dans `api.js`
- Download via blob + object URL

## Dependance

- `reportlab==4.1.0` (ajoute dans requirements.txt)
- Compatible Python 3.14 (hex strings dans les font tags pour eviter ast.Str)

## Tests

16 tests dans `backend/tests/test_reports.py` :

| Classe | Tests | Description |
|--------|-------|-------------|
| TestAuditJSON | 6 | Structure JSON, sections, confidence, 400 on missing org |
| TestAuditPDF | 4 | PDF bytes, content-disposition, multi-page, 400 on missing org |
| TestBuildReportData | 6 | Service direct, render PDF, confidence levels |

## Fichiers modifies/crees

| Fichier | Action |
|---------|--------|
| `backend/requirements.txt` | +reportlab==4.1.0 |
| `backend/services/audit_report_service.py` | Cree |
| `backend/routes/reports.py` | Cree |
| `backend/routes/__init__.py` | +reports_router |
| `backend/main.py` | +reports_router |
| `backend/tests/test_reports.py` | Cree (16 tests) |
| `frontend/src/services/api.js` | +2 fonctions |
| `frontend/src/pages/ActionsPage.jsx` | +bouton PDF |
| `docs/audit_report_v1.md` | Cree |
