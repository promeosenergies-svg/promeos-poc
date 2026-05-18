/**
 * M2-5.3.B — Dérivation du status d'une evidence.
 *
 * Doctrine ADR-029 : pas d'enum `verification_status` côté backend — la
 * sémantique est portée par les timestamps `verified_at` / `expires_at`.
 *
 * @param {object|null} evidence
 * @param {string|null} [evidence.verified_at] - ISO date ou null
 * @param {string|null} [evidence.expires_at]  - ISO date ou null
 * @param {Date} [now] - injectable pour des tests déterministes
 * @returns {'pending' | 'verified' | 'expired'}
 */
export function deriveEvidenceStatus(evidence, now = new Date()) {
  if (!evidence || !evidence.verified_at) {
    return 'pending';
  }

  if (evidence.expires_at) {
    const expiry = new Date(evidence.expires_at);
    if (!Number.isNaN(expiry.getTime()) && expiry < now) {
      return 'expired';
    }
  }

  return 'verified';
}
