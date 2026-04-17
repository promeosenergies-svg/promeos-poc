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

// Vague 2 — Simulation décalage d'usages sur historique CDC + spot ENTSO-E.
// Différenciant démo : preuve chiffrée "voici ce que vous auriez gagné".
export const getNebcoSimulation = (siteId, periodDays = 30) =>
  cachedGet(`/pilotage/nebco-simulation/${siteId}`, {
    params: { period_days: periodDays },
  }).then((r) => r.data);
