export const CONFIDENCE_LEVELS = { HIGH: 'high', MEDIUM: 'medium', LOW: 'low' };
export const DEFAULT_FRAMEWORKS_TOTAL = 3;

const HIGH_RATIO = 0.6;
const MEDIUM_RATIO = 0.3;

export function resolvePortfolioConfidence({ high_confidence_count, total_sites } = {}) {
  if (!total_sites || high_confidence_count == null) return null;
  const ratio = high_confidence_count / total_sites;
  if (ratio >= HIGH_RATIO) return CONFIDENCE_LEVELS.HIGH;
  if (ratio >= MEDIUM_RATIO) return CONFIDENCE_LEVELS.MEDIUM;
  return CONFIDENCE_LEVELS.LOW;
}
