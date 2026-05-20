/**
 * M2-5.5 — Validation client d'un fichier evidence (defense in depth).
 *
 * Q1 : MIME type déclaré uniquement — pas de magic bytes côté client. Le
 * backend reste l'autorité (magic bytes + taille, cf. file_validation.py).
 */

export const ACCEPTED_MIME_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];

// Affichage UI (« PDF, JPG ou PNG ») — pas un contrôle.
export const ACCEPTED_MIME_LABELS = {
  'application/pdf': 'PDF',
  'image/jpeg': 'JPG',
  'image/png': 'PNG',
};

// Limite réelle backend = 10 Mo (MAX_EVIDENCE_SIZE_BYTES).
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
export const MAX_FILE_SIZE_LABEL = '10 Mo';

/**
 * Valide un fichier côté client (rapide, UX).
 * @param {File|null} file
 * @returns {string|null} message d'erreur FR, ou null si OK
 */
export function validateEvidenceFile(file) {
  if (!file) {
    return 'Veuillez sélectionner un fichier';
  }
  if (!ACCEPTED_MIME_TYPES.includes(file.type)) {
    return 'Format non accepté. Utilisez PDF, JPG ou PNG';
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `Le fichier dépasse ${MAX_FILE_SIZE_LABEL}`;
  }
  return null;
}
