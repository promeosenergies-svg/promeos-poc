/**
 * PROMEOS - API Pilotage des usages.
 * Endpoints V1 innovation : Radar J+7, ROI Flex Ready®, Scoring portefeuille.
 * Ref : Baromètre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
 */
import { cachedGet } from './core';

export const getRadarPrixNegatifs = (horizonDays = 7) =>
  cachedGet('/pilotage/radar-prix-negatifs', { params: { horizon_days: horizonDays } }).then(
    (r) => r.data
  );

export const getRoiFlexReady = (siteId) =>
  cachedGet(`/pilotage/roi-flex-ready/${siteId}`).then((r) => r.data);

export const getPortefeuilleScoring = () =>
  cachedGet('/pilotage/portefeuille-scoring').then((r) => r.data);

export const getFlexReadySignals = (siteId) =>
  cachedGet(`/pilotage/flex-ready-signals/${siteId}`).then((r) => r.data);
