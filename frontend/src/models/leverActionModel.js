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
    proof_expected: "Rapport d'evaluation conformite",
    proof_owner: 'Responsable energie',
    due_days: 120,
    priority: 2,
  },
  'lev-fact-anom': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      "Anomalies facture detectees par le moteur d'audit",
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
    proof_expected: "Rapport d'audit facture",
    proof_owner: 'Responsable achat energie',
    due_days: 90,
    priority: 2,
  },
  'lev-optim-ener': {
    source_type: 'lever_engine',
    severity: 'low',
    rationale: [
      "Potentiel d'optimisation energetique identifie (heuristique V1)",
      'Analyse des sites energivores recommandee',
      'Objectif: reduire la facture totale de 1% minimum',
    ],
    proof_expected: "Plan d'optimisation energetique",
    proof_owner: 'Energy Manager',
    due_days: 180,
    priority: 3,
  },
  // V36 — Achat d'energie
  'lev-achat-renew': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      'Contrats energie arrivent a echeance dans les 90 prochains jours',
      'Risque de reconduction tacite a des conditions defavorables',
      'Negociation anticipee recommandee pour optimiser les conditions',
    ],
    proof_expected: 'Contrat de fourniture actuel / avenants / echeancier',
    proof_owner: 'Direction des achats ou responsable energie',
    due_days: 30,
    priority: 1,
  },
  'lev-achat-data': {
    source_type: 'lever_engine',
    severity: 'medium',
    rationale: [
      'Sites identifies sans information contractuelle dans le referentiel',
      "Impossible d'evaluer l'exposition ou les echeances sans ces donnees",
      'Prerequis pour activer le suivi renouvellement et les alertes',
    ],
    proof_expected: 'Contrat ou attestation fournisseur par site',
    proof_owner: 'Direction des achats ou gestionnaire patrimoine',
    due_days: 60,
    priority: 2,
  },
  // V39 — Tertiaire / OPERAT
  'lev-tertiaire-efa': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      'Anomalies detectees sur les EFA (Entites Fonctionnelles Assujetties) au Decret tertiaire',
      'Donnees manquantes ou incoherences bloquant la declaration OPERAT',
      'Correction prioritaire avant echeance de declaration',
    ],
    proof_expected: 'Attestation OPERAT, dossier de modulation, ou justificatif de surface',
    proof_owner: 'Responsable conformite ou Energy Manager',
    due_days: 90,
    priority: 1,
  },
  // V42 — Tertiaire site signals
  'lev-tertiaire-create-efa': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      'Sites identifiés comme probablement assujettis au Décret tertiaire (surface >= 1000 m²)',
      'Aucune EFA existante pour ces sites',
      "Création d'une EFA recommandée avant la prochaine échéance OPERAT",
    ],
    proof_expected: 'Attestation OPERAT ou justificatif de surface tertiaire',
    proof_owner: 'Responsable conformité ou Energy Manager',
    due_days: 60,
    priority: 1,
  },
  'lev-tertiaire-complete-patrimoine': {
    source_type: 'lever_engine',
    severity: 'medium',
    rationale: [
      'Données patrimoniales incomplètes pour certains sites',
      "Impossible de qualifier l'assujettissement au Décret tertiaire sans surface renseignée",
      'Complétez les bâtiments et surfaces pour activer la qualification automatique',
    ],
    proof_expected: 'Données patrimoniales (surfaces, bâtiments)',
    proof_owner: 'Gestionnaire patrimoine',
    due_days: 90,
    priority: 2,
  },
  // V37 — Activation donnees
  'lev-data-cover': {
    source_type: 'lever_engine',
    severity: 'low',
    rationale: [
      'Couverture donnees incomplete \u2014 certaines briques non activees',
      'Completez les donnees manquantes pour debloquer les recommandations',
      'Chaque brique activee ameliore la precision des analyses',
    ],
    proof_expected: 'Donnees importees (patrimoine, factures, contrats, consommations)',
    proof_owner: 'Gestionnaire de donnees ou Energy Manager',
    due_days: 60,
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
 * Construit un deep-link vers la création d'action avec contexte levier.
 *
 * @param {import('./leverEngineModel').Lever} lever
 * @returns {string}
 */
export function buildLeverDeepLink(lever) {
  if (!lever || !lever.actionKey) return '/actions';

  const params = new URLSearchParams();
  params.set('type', lever.type || 'levier');
  params.set('source', 'lever_engine');
  params.set('ref_id', lever.actionKey);
  if (lever.label) params.set('titre', lever.label);

  return `/actions/new?${params.toString()}`;
}
