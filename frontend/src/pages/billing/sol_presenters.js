/**
 * PROMEOS — BillingSol presenters (Sprint REFONTE-P6 S1 — pilot wrapper)
 *
 * Fonctions pures pour BillingSol wrapper. BillingPage reste propriétaire
 * de la data (periods, coverage, missing, compare chart, import CSV/PDF).
 */

import { NBSP } from '../cockpit/sol_presenters';

export { NBSP };

/**
 * Build kicker "PATRIMOINE · FACTURATION · 12 MOIS COUVERTS"
 */
export function buildBillingKicker({ summary } = {}) {
  const s = summary || {};
  const segments = ['PATRIMOINE', 'FACTURATION'];
  if (s.covered != null && s.months_total != null) {
    segments.push(`${s.covered}/${s.months_total} MOIS`);
  }
  if (s.missing > 0) segments.push(`${s.missing} MANQUANT${s.missing > 1 ? 'S' : ''}`);
  return segments.join(` ${NBSP}·${NBSP} `);
}

/**
 * Build narrative
 */
export function buildBillingNarrative({ summary, compareData } = {}) {
  const s = summary || {};
  const c = compareData || {};

  const total = s.months_total || 12;
  const covered = s.covered || 0;
  const coverage = total > 0 ? Math.round((covered / total) * 100) : 0;

  const parts = [];
  parts.push(`Couverture ${coverage}%`);
  if (s.range) parts.push(`période ${s.range.min} → ${s.range.max}`);
  if (s.missing > 0) parts.push(`${s.missing} à compléter`);

  const intro = parts.join(` ${NBSP}·${NBSP} `) + '.';
  const sources =
    'Moteur shadow v4.2 compare chaque facture aux barèmes TURPE 7, ATRD, accises, CTA et TVA en vigueur.';
  return `${intro} ${sources}`;
}

/**
 * interpretWeek — 3 cards sémantiques
 */
export function interpretWeek({ summary, missingPeriods = [], anomalies = [] } = {}) {
  const s = summary || {};
  const topMissing = missingPeriods[0];
  const topAnomaly = anomalies[0];

  const aRegarder = s.missing > 0 || topMissing
    ? {
        tagKind: 'afaire',
        tagLabel: 'À compléter',
        title: topMissing
          ? `${topMissing.site_name || 'Site'} — ${topMissing.month_key}`
          : `${s.missing} période${s.missing > 1 ? 's' : ''} manquante${s.missing > 1 ? 's' : ''}`,
        body: topMissing?.missing_reason
          ? topMissing.missing_reason
          : 'Import CSV/PDF pour compléter les données facture.',
        footerLeft: '',
        footerRight: 'importer →',
      }
    : {
        tagKind: 'calme',
        tagLabel: 'À compléter',
        title: 'Couverture totale',
        body: 'Toutes les périodes sont couvertes sur les 12 derniers mois.',
      };

  const deriveDetectee = topAnomaly
    ? {
        tagKind: 'attention',
        tagLabel: 'Dérive détectée',
        title: topAnomaly.title || 'Anomalie facturation',
        body: topAnomaly.detail || 'Écart shadow billing détecté',
        footerLeft: topAnomaly.estimated_loss
          ? `Impact ${formatFREurCompact(topAnomaly.estimated_loss)}`
          : '',
      }
    : {
        tagKind: 'calme',
        tagLabel: 'Dérive détectée',
        title: 'Aucune anomalie facturation',
        body: 'Les barèmes TURPE 7, accises et CTA sont conformes.',
      };

  const bonneNouvelle = {
    tagKind: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: `${s.covered || 0} mois sous contrôle`,
    body:
      s.covered > 0
        ? 'Analyses fiables sur la période couverte. Shadow billing actif.'
        : 'En attente d\'import des premières factures.',
  };

  return { aRegarder, deriveDetectee, bonneNouvelle };
}

function formatFREurCompact(v) {
  if (v == null || !Number.isFinite(v)) return '—';
  const abs = Math.abs(v);
  if (abs >= 1000) {
    return `${(v / 1000).toFixed(abs >= 10000 ? 0 : 1).replace('.', ',')}${NBSP}k€`;
  }
  return `${Math.round(v)}${NBSP}€`;
}
