/**
 * Benchmarks ADEME ODP 2024 — consommation médiane par usage (kWhEF/m²/an)
 * Source : ADEME ODP 2024, aligné sur backend/config/patrimoine_assumptions.py
 */
export const OID_BENCHMARKS = {
  bureau: 210,
  bureaux: 210,
  hotellerie: 280,
  hotel: 280,
  enseignement: 140,
  commerce: 330,
  magasin: 330,
  entrepot: 80,
  logistique: 80,
  industrie: 180,
  usine: 180,
  sante: 250,
  default: 210,
};

export function getBenchmark(usage) {
  if (!usage) return OID_BENCHMARKS.default;
  return OID_BENCHMARKS[usage.toLowerCase()] || OID_BENCHMARKS.default;
}

export function getIntensityRatio(kwh_m2, usage) {
  const bench = getBenchmark(usage);
  if (!bench || !kwh_m2) return null;
  return kwh_m2 / bench;
}
