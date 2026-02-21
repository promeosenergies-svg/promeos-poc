# V46 — OPERAT Actions Bridge

## FAITS

1. Le backend Actions existe depuis V4/V5 avec modele ActionItem riche (idempotency_key, source_type, severity, due_date, priority, site_id, category, etc.)
2. POST /api/actions supporte `idempotency_key` unique : si cle existante, retourne `{"status": "existing", ...}` sans duplication
3. POST /api/actions n'autorise que `source_type: "manual"` ou `"insight"` pour creation directe (pas "compliance")
4. Le frontend ActionsPage supporte filtres par type, statut, quickView, search, et group-by
5. Le leverActionModel.js a deja des templates tertiaire (lev-tertiaire-efa, lev-tertiaire-create-efa)
6. Les issues OPERAT V45 ont title_fr, proof_required, proof_links, severity
7. La dedup backend fonctionne via idempotency_key (UNIQUE constraint) — pas besoin de logique front supplementaire

## HYPOTHESES

1. `source_type: "insight"` est le meilleur fit pour les actions OPERAT (issues = insights de controles)
2. Les actions OPERAT doivent etre identifiables distinctement des autres "insight" actions → detection via `source_id.startsWith("operat:")`
3. La due_date est calculee de facon deterministe depuis la severite (critical: +14j, high: +30j, medium: +60j, low: +90j)
4. Pas de modification backend necessaire — le contrat API existant suffit

## DECISIONS

1. **Nouveau modele** `operatActionModel.js` : fonctions pures buildOperatActionKey, buildOperatActionPayload, buildOperatActionDeepLink
2. **Dedup** via `idempotency_key: operat-{efa_id}-{year}-{issue_code}` — 2 clics → 1 action
3. **Source type** : `insight` avec `source_id: operat:{efa_id}:{year}:{issue_code}`
4. **UI** : CTA "Créer une action" par issue sur EFA detail et Anomalies, toast feedback avec "Ouvrir le plan d'actions"
5. **Plan d'actions** : type "OPERAT" dans TYPE_BADGE et ACTION_TYPE_LABELS, filtre pre-rempli via `?source=operat`
6. **Mapping** : `insight` avec source_id `operat:*` → type frontend `operat` (distinct des autres insights)

## MAPPING ISSUE → ACTION

| Champ issue | Champ action | Transformation |
|---|---|---|
| title_fr ou code | title | `OPERAT — ${title_fr}` |
| severity | severity + priority | direct + SEVERITY_TO_PRIORITY |
| severity | due_date | +14j/+30j/+60j/+90j |
| message_fr + impact_fr + action_fr | rationale | 3 bullets FR |
| proof_required | notes | Preuve attendue: label (owner) |
| proof_links[0] | rationale link | Preuve Memobox: URL |
| efa.id | source_id | operat:{efa_id}:{year}:{code} |
| efa.site_id | site_id | direct |
