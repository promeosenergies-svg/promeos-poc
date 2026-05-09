/**
 * grammar/decisionAdapters — Adaptateurs canoniques action/priority → DecisionEvidenceCard.
 *
 * Sprint Grammaire v1 Phase 3.0 (audit simplify 09/05).
 *
 * Avant Phase 3.0 : `toDecSeverity` et `buildEvidenceFallback` étaient
 * réimplémentés dans 2 fichiers consommateurs avec une divergence subtile :
 *   - ActionCenterSlideOver mappait `priority='medium'` → `severity='warning'`
 *   - CockpitPilotage mappait `urgency='medium'` → `severity='neutral'`
 * Bug silencieux : la même criticité backend produisait deux apparences
 * différentes selon l'écran. Cette dette doctrinale est éliminée par
 * cette SoT unique.
 *
 * Doctrine §5.6 Loi L9 : DecisionEvidenceCard requiert 4-8 cellules evidence.
 * Doctrine §6.4 (cohérence cross-écrans) : un même fait métier ne peut pas
 * être affiché de deux manières différentes selon l'écran.
 */

/**
 * Convertit un niveau de criticité backend (priority/urgency) en variant
 * severity DecisionEvidenceCard (doctrine §5.6).
 *
 * Convention canonique unique :
 *   critical → critical (rouge — décision vraiment critique)
 *   high     → warning  (ambré — attention requise)
 *   medium   → warning  (ambré — attention requise, pas neutre)
 *   low      → neutral  (calme — info)
 *   default  → neutral
 *
 * @param {string} level - 'critical' | 'high' | 'medium' | 'low'
 * @returns {'critical' | 'warning' | 'neutral'} severity
 */
export function toDecSeverity(level) {
  if (level === 'critical') return 'critical';
  if (level === 'high' || level === 'medium') return 'warning';
  return 'neutral';
}

/**
 * Construit 4 cellules evidence par défaut quand le backend ne fournit pas
 * un payload `evidence_cells` enrichi. Garantit le contrat L9 (4 minimum).
 *
 * @param {Object} input
 * @param {string|number} [input.impactDisplay] - valeur déjà formatée (ex "7,5 k€") ou null
 * @param {string} [input.category] - catégorie d'action
 * @param {string} [input.priorityLabel] - label de criticité ("Critique", "Haute", ...)
 * @param {string|number} [input.rang] - rang d'affichage P1/P2/P3
 * @param {string} [input.dueDate] - date échéance ISO ou format FR
 * @param {string} [input.status] - statut de l'action ("À traiter", "Ouverte", ...)
 * @param {string} [input.domain] - pilier PROMEOS (fallback si autres champs vides)
 * @returns {Array<{label, value, unit, helper}>} exactement 4 cellules
 */
export function buildEvidenceFallback(input = {}) {
  const cells = [];
  cells.push({
    label: 'IMPACT',
    value: input.impactDisplay || '—',
    unit: '',
    helper: input.impactDisplay ? 'estimation' : 'non chiffré',
  });
  cells.push({
    label: 'CATÉGORIE',
    value: input.category || '—',
    unit: '',
    helper: '',
  });
  cells.push({
    label: 'PRIORITÉ',
    value: input.priorityLabel || '—',
    unit: '',
    helper: input.rang != null ? `P${input.rang}` : '',
  });
  if (input.dueDate) {
    cells.push({
      label: 'ÉCHÉANCE',
      value: input.dueDate,
      unit: '',
      helper: '',
    });
  } else if (input.status) {
    cells.push({
      label: 'STATUT',
      value: input.status,
      unit: '',
      helper: 'à arbitrer',
    });
  } else {
    cells.push({
      label: 'DOMAINE',
      value: (input.domain || '—').toUpperCase(),
      unit: '',
      helper: 'pilier PROMEOS',
    });
  }
  return cells;
}

/**
 * Mapping label de criticité (utile pour l'affichage helper de cell PRIORITÉ).
 */
export function priorityLabel(level) {
  if (level === 'critical') return 'Critique';
  if (level === 'high') return 'Haute';
  if (level === 'medium') return 'Moyenne';
  if (level === 'low') return 'Basse';
  return '—';
}
