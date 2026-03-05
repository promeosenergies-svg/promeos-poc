/**
 * PROMEOS — Lever → Action Mapping V34 (logique pure, aucun import React)
 *
 * Transforme un levier V33 en payload ActionCreate compatible avec POST /actions.
 * Génère un deep-link vers le Command Center si création directe non souhaitée.
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
      'Sites non conformes identifiés dans le périmètre actif',
      'Risque financier réglementaire (Décret Tertiaire / BACS)',
      'Action corrective recommandée avant prochaine échéance',
    ],
    proof_expected: 'Attestation de mise en conformité ou plan de remédiation',
    proof_owner: 'Responsable conformité site',
    due_days: 90,
    priority: 1,
  },
  'lev-conf-ar': {
    source_type: 'lever_engine',
    severity: 'medium',
    rationale: [
      'Sites à risque identifiés — non-conformité probable',
      'Évaluation préventive recommandée',
      'Risque financier potentiel à quantifier',
    ],
    proof_expected: "Rapport d'évaluation conformité",
    proof_owner: 'Responsable énergie',
    due_days: 120,
    priority: 2,
  },
  'lev-fact-anom': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      "Anomalies facture détectées par le moteur d'audit",
      'Surcoût identifié — récupération possible',
      'Vérification des écarts prix, volumes et doublons',
    ],
    proof_expected: 'Factures corrigées ou avoir fournisseur',
    proof_owner: 'Responsable achat énergie',
    due_days: 60,
    priority: 1,
  },
  'lev-fact-loss': {
    source_type: 'lever_engine',
    severity: 'medium',
    rationale: [
      'Surcoût facturé détecté sans détail anomalie',
      'Audit facture approfondi recommandé',
      'Potentiel de récupération à confirmer',
    ],
    proof_expected: "Rapport d'audit facture",
    proof_owner: 'Responsable achat énergie',
    due_days: 90,
    priority: 2,
  },
  'lev-optim-ener': {
    source_type: 'lever_engine',
    severity: 'low',
    rationale: [
      "Potentiel d'optimisation énergétique identifié (heuristique V1)",
      'Analyse des sites énergivores recommandée',
      'Objectif: réduire la facture totale de 1% minimum',
    ],
    proof_expected: "Plan d'optimisation énergétique",
    proof_owner: 'Energy Manager',
    due_days: 180,
    priority: 3,
  },
  // V36 — Achat d'énergie
  'lev-achat-renew': {
    source_type: 'lever_engine',
    severity: 'high',
    rationale: [
      'Contrats énergie arrivent à échéance dans les 90 prochains jours',
      'Risque de reconduction tacite à des conditions défavorables',
      'Négociation anticipée recommandée pour optimiser les conditions',
    ],
    proof_expected: 'Contrat de fourniture actuel / avenants / échéancier',
    proof_owner: 'Direction des achats ou responsable énergie',
    due_days: 30,
    priority: 1,
  },
  'lev-achat-data': {
    source_type: 'lever_engine',
    severity: 'medium',
    rationale: [
      'Sites identifiés sans information contractuelle dans le référentiel',
      "Impossible d'évaluer l'exposition ou les échéances sans ces données",
      'Prérequis pour activer le suivi renouvellement et les alertes',
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
      'Anomalies détectées sur les EFA (Entités Fonctionnelles Assujetties) au Décret tertiaire',
      'Données manquantes ou incohérences bloquant la déclaration OPERAT',
      'Correction prioritaire avant échéance de déclaration',
    ],
    proof_expected: 'Attestation OPERAT, dossier de modulation, ou justificatif de surface',
    proof_owner: 'Responsable conformité ou Energy Manager',
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
  // V37 — Activation données
  'lev-data-cover': {
    source_type: 'lever_engine',
    severity: 'low',
    rationale: [
      'Couverture données incomplète \u2014 certaines briques non activées',
      'Complétez les données manquantes pour débloquer les recommandations',
      'Chaque brique activée améliore la précision des analyses',
    ],
    proof_expected: 'Données importées (patrimoine, factures, contrats, consommations)',
    proof_owner: 'Gestionnaire de données ou Energy Manager',
    due_days: 60,
    priority: 3,
  },
};

// ── Fallback template ────────────────────────────────────────────────────────

const _FALLBACK = {
  source_type: 'lever_engine',
  severity: 'medium',
  rationale: ['Levier identifié par le moteur PROMEOS'],
  proof_expected: 'À qualifier',
  proof_owner: 'À qualifier',
  due_days: 90,
  priority: 3,
};

/**
 * Construit un payload compatible ActionCreate à partir d'un levier.
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
