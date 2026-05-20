import { fmtNum } from '../../../utils/format';

/**
 * M2-5.5 — Taille de fichier formatée en unités FR.
 *
 * Passe par le formateur central `fmtNum` (doctrine « formatters centralisés »
 * — aucun arrondi inline en composant, cf. source guard formatGuard).
 * Helper partagé par EvidenceItem (affichage liste) et EvidenceUploadModal
 * (aperçu du fichier sélectionné).
 *
 * @param {number|null|undefined} bytes
 * @returns {string} ex. « 850 o » / « 12 Ko » / « 2,4 Mo » / « — »
 */
export function formatFileSize(bytes) {
  if (bytes == null) return '—';
  if (bytes < 1024) return fmtNum(bytes, 0, 'o');
  if (bytes < 1024 * 1024) return fmtNum(bytes / 1024, 0, 'Ko');
  return fmtNum(bytes / (1024 * 1024), 1, 'Mo');
}
