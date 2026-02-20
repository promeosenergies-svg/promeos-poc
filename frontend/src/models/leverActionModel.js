/**
 * PROMEOS — Lever → Action Mapping V34 (logique pure, aucun import React)
 *
 * Transforme un levier V33 en payload ActionCreate compatible avec POST /actions.
 * Genere un deep-link vers le Command Center si creation directe non souhaitee.
 *
 * Exports:
 *   buildActionPayload(lever)      → ActionCreate-compatible payload
 *   buildLeverDeepLink(lever)      → URL string pour navigation
 *   LEVER_ACTION_TEMPLATES         → templates FR par type de levier
 */

// ── Templates FR par type ────────────────────────────────────────────────────

export const LEVER_ACTION_TEMPLATES = {
  'lev-conf-nc': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      'Sites non conformes identifies dans le perimetre actif',
      'Risque financier reglementaire (Decret Tertiaire / BACS)',
      'Action corrective recommandee avant prochaine echeance',
    ],
    proof_expected: 'Attestation de mise en conformite ou plan de remediation',
    proof_owner: 'Responsable conformite site',
    due_days: 90,
    priority: 1,
  },
  'lev-conf-ar': {
    source_type: 'lever_engine',
    severity: 'medium',
    rationale: [
      'Sites a risque identifies — non-conformite probable',
      'Evaluation preventive recommandee',
      'Risque financier potentiel a quantifier',
    ],
    proof_expected: 'Rapport d\'evaluation conformite',
    proof_owner: 'Responsable energie',
    due_days: 120,
    priority: 2,
  },
  'lev-fact-anom': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      'Anomalies facture detectees par le moteur d\'audit',
      'Surcout identifie — recuperation possible',
      'Verification des ecarts prix, volumes et doublons',
    ],
    proof_expected: 'Factures corrigees ou avoir fournisseur',
    proof_owner: 'Responsable achat energie',
    due_days: 60,
    priority: 1,
  },
  'lev-fact-loss': {
    source_type: 'lever_engine',
    severity: 'medium',
    rationale: [
      'Surcout facture detecte sans detail anomalie',
      'Audit facture approfondi recommande',
      'Potentiel de recuperation a confirmer',
    ],
    proof_expected: 'Rapport d\'audit facture',
    proof_owner: 'Responsable achat energie',
    due_days: 90,
    priority: 2,
  },
  'lev-optim-ener': {
    source_type: 'lever_engine',
    severity: 'low',
    rationale: [
      'Potentiel d\'optimisation energetique identifie (heuristique V1)',
      'Analyse des sites energivores recommandee',
      'Objectif: reduire la facture totale de 1% minimum',
    ],
    proof_expected: 'Plan d\'optimisation energetique',
    proof_owner: 'Energy Manager',
    due_days: 180,
    priority: 3,
  },
};

// ── Fallback template ────────────────────────────────────────────────────────

const _FALLBACK = {
  source_type: 'lever_engine',
  severity: 'medium',
  rationale: ['Levier identifie par le moteur PROMEOS'],
  proof_expected: 'A qualifier',
  proof_owner: 'A qualifier',
  due_days: 90,
  priority: 3,
};

/**
 * Construit un payload compatible ActionCreate a partir d'un levier.
 *
 * @param {import('./leverEngineModel').Lever} lever
 * @returns {{ title: string, source_type: string, source_id: string, severity: string,
 *             rationale: string, estimated_gain_eur: number|null, due_date: string,
 *             priority: number, idempotency_key: string,
 *             _meta: { proof_expected: string, proof_owner: string } }}
 */
export function buildActionPayload(lever) {
  if (!lever || !lever.actionKey) return null;

  const tpl = LEVER_ACTION_TEMPLATES[lever.actionKey] || _FALLBACK;

  const dueDate = new Date();
  dueDate.setDate(dueDate.getDate() + (tpl.due_days || 90));
  const dueDateStr = dueDate.toISOString().slice(0, 10);

  return {
    title: lever.label,
    source_type: tpl.source_type,
    source_id: lever.actionKey,
    severity: tpl.severity,
    rationale: tpl.rationale.join('\n'),
    estimated_gain_eur: lever.impactEur,
    due_date: dueDateStr,
    priority: tpl.priority,
    idempotency_key: `lever-${lever.actionKey}`,
    _meta: {
      proof_expected: tpl.proof_expected,
      proof_owner: tpl.proof_owner,
    },
  };
}

/**
 * Construit un deep-link vers le Command Center avec pre-filtre levier.
 *
 * @param {import('./leverEngineModel').Lever} lever
 * @returns {string}
 */
export function buildLeverDeepLink(lever) {
  if (!lever || !lever.actionKey) return '/command-center';

  const params = new URLSearchParams({
    filter: 'leviers',
    type: lever.type,
    key: lever.actionKey,
  });

  if (lever.impactEur != null) {
    params.set('impact', String(lever.impactEur));
  }

  return `/command-center?${params.toString()}`;
}
