/**
 * PROMEOS — MonitoringClimateScatter (Sprint P2.1).
 *
 * Composant autonome extrait de MonitoringPage (anciennement `ClimateScatter`
 * inline ligne 1321). Aucune modification visuelle volontaire — extraction
 * mécanique pour réduire la taille de MonitoringPage.
 *
 * Affiche le nuage de points consommation × température avec ligne de
 * régression + statistiques (pente, point d'équilibre, R², label) +
 * affichage du nombre d'outliers masqués via les bornes backend.
 *
 * Doctrine zéro calcul métier frontend :
 * - Bornes outliers fournies par backend (`climate.outlier_bounds`,
 *   livré par compute_quantiles SoT P0.S1c).
 * - `_filterOutliers` est un filtre d'affichage pur (pas de calcul
 *   statistique re-fait FE).
 *
 * Props :
 * - climate : objet retourné par `/api/monitoring/kpis.climate` —
 *   { scatter, fit_line, slope_kw_per_c, balance_point_c, r_squared,
 *     label, reason, outlier_bounds }
 */
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Thermometer } from 'lucide-react';
import { fmtNum } from '../../utils/format';

// Co-localisé : labels FR backend reason codes (vise erreurs métier
// remontées par /api/monitoring/kpis quand le scatter n'est pas
// calculable).
export const CLIMATE_REASONS = {
  no_meter: "Aucun compteur associé au snapshot. Relancez l'analyse.",
  no_weather: 'Données météo indisponibles pour la période.',
  meter_not_found: 'Compteur introuvable.',
  insufficient_readings: 'Moins de 10 jours de données — insuffisant pour la régression.',
  computation_error: 'Erreur de calcul. Vérifiez les données sources.',
};

export const CLIMATE_LABEL_FR = {
  heating_dominant: 'Chauffage majoritaire',
  cooling_dominant: 'Climatisation majoritaire',
  mixed: 'Mixte (chauffage + clim.)',
  flat: 'Insensible au climat',
  unknown: 'Non déterminé',
};

/**
 * Filtre d'affichage : applique les bornes `outlier_bounds` reçues du
 * backend pour ne pas écraser le scatter avec des outliers visuels.
 *
 * Si le backend ne fournit pas `outlier_bounds` (compat données legacy
 * ou erreur côté serveur), on retourne tous les points — pas de
 * fallback FE qui re-calculerait les quantiles (doctrine zéro calcul
 * métier — quantiles backend via compute_quantiles SoT P0.S1c).
 */
function _filterOutliers(points, outlierBounds) {
  if (!points || points.length < 5) return points;
  if (!outlierBounds || outlierBounds.lower == null || outlierBounds.upper == null) {
    return points;
  }
  const { lower, upper } = outlierBounds;
  return points.filter((p) => p.kwh >= lower && p.kwh <= upper);
}

export default function MonitoringClimateScatter({
  climate,
  testId = 'monitoring-climate-scatter',
}) {
  if (!climate || !climate.scatter || climate.scatter.length === 0) {
    const reason = climate?.reason;
    const msg = reason ? CLIMATE_REASONS[reason] || reason : 'Pas de données climatiques.';
    return (
      <div className="text-center py-12" data-testid={`${testId}-empty`}>
        <Thermometer size={28} className="mx-auto text-gray-200 mb-2" />
        <p className="text-sm text-gray-400">{msg}</p>
        {reason && <p className="text-xs text-gray-300 mt-1">code: {reason}</p>}
      </div>
    );
  }

  const filtered = _filterOutliers(climate.scatter, climate?.outlier_bounds);
  const removed = climate.scatter.length - filtered.length;

  return (
    <div data-testid={testId}>
      <ResponsiveContainer width="100%" height={250}>
        <ScatterChart margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="T"
            name="Température (°C)"
            unit=" °C"
            tick={{ fontSize: 11 }}
            type="number"
          />
          <YAxis
            dataKey="kwh"
            name="Conso. journalière"
            unit=" kWh/j"
            tick={{ fontSize: 11 }}
            type="number"
          />
          <RTooltip cursor={{ strokeDasharray: '3 3' }} />
          <Scatter data={filtered} fill="#0072B2" fillOpacity={0.55} r={3} name="Jours" />
          {climate.fit_line && climate.fit_line.length > 0 && (
            <Scatter
              data={climate.fit_line}
              fill="none"
              line={{ stroke: '#E69F00', strokeWidth: 2.5 }}
              shape={() => null}
              name="Régression"
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>
      <div
        className="flex items-center gap-4 mt-2 text-xs text-gray-500"
        data-testid={`${testId}-stats`}
      >
        {climate.slope_kw_per_c != null && (
          <span>Pente: {fmtNum(climate.slope_kw_per_c, 1)} (kWh/j)/°C</span>
        )}
        {climate.balance_point_c != null && (
          <span>Tb: {fmtNum(climate.balance_point_c, 1)} °C</span>
        )}
        {climate.r_squared != null && <span>R²: {fmtNum(climate.r_squared, 2)}</span>}
        {climate.label && <span>{CLIMATE_LABEL_FR[climate.label] || climate.label}</span>}
        {removed > 0 && (
          <span className="text-orange-400" data-testid={`${testId}-outliers-removed`}>
            {removed} outlier{removed > 1 ? 's' : ''} masqué{removed > 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  );
}
