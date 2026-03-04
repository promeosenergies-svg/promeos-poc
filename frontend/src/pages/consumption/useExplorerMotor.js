/**
 * PROMEOS — useExplorerMotor
 * Central data engine for the Consumption Explorer.
 * Replaces scattered useState/useEffect across panels.
 *
 * Returns a unified state + data object consumed by the page and all panels.
 * Backward compatible: data.primary* helpers expose single-site slices for
 * existing TunnelPanel, TargetsPanel, HPHCPanel, GasPanel.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { MODES, UNITS, DEFAULT_LAYERS } from './types';
import {
  getConsumptionAvailability,
  getConsumptionTunnelV2,
  getTargetsProgressionV2,
  getConsumptionTargets,
  getHPHCBreakdownV2,
  getGasSummary,
  getGasWeatherNormalized,
} from '../../services/api';

/**
 * @param {object} opts
 * @param {string[]} opts.initialSiteIds  — initial site IDs to load
 * @param {string}   opts.initialEnergy   — 'electricity' | 'gas'
 * @param {number}   opts.initialDays     — period in days
 */
export default function useExplorerMotor({
  initialSiteIds = [],
  initialEnergy = 'electricity',
  initialDays = 90,
} = {}) {
  // ── Core filter state ──────────────────────────────────────────────────
  const [siteIds, setSiteIds] = useState(initialSiteIds);
  const [energyType, setEnergyType] = useState(initialEnergy);
  const [days, setDays] = useState(initialDays);
  const [mode, setMode] = useState(MODES.AGREGE);
  const [unit, setUnit] = useState(UNITS.KWH);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);

  // ── Data state (keyed by siteId) ───────────────────────────────────────
  const [availabilityBySite, setAvailabilityBySite] = useState({});
  const [tunnelBySite, setTunnelBySite] = useState({});
  const [targetsBySite, setTargetsBySite] = useState({});
  const [progressionBySite, setProgressionBySite] = useState({});
  const [hphcBySite, setHphcBySite] = useState({});
  const [gasBySite, setGasBySite] = useState({});
  const [weatherBySite, setWeatherBySite] = useState({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ── Last-write-wins guard ───────────────────────────────────────────────
  const requestIdRef = useRef(0);

  // ── Layer toggle ────────────────────────────────────────────────────────
  const toggleLayer = useCallback((layerKey) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  }, []);

  // ── Fetch all data for current siteIds ────────────────────────────────
  const fetchAll = useCallback(async () => {
    if (!siteIds.length) return;
    const reqId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const year = new Date().getFullYear();

      const results = await Promise.allSettled(
        siteIds.map(async (sid) => {
          const [avail, tunnel, progression, targets, hphc, gas, weather] =
            await Promise.allSettled([
              getConsumptionAvailability(sid, energyType),
              getConsumptionTunnelV2(sid, days, energyType, 'energy'),
              getTargetsProgressionV2(sid, energyType, year),
              getConsumptionTargets(sid, energyType, year),
              getHPHCBreakdownV2(sid, days),
              getGasSummary(sid, days),
              getGasWeatherNormalized(sid, days).catch(() => null),
            ]);
          return {
            siteId: sid,
            availability: avail.status === 'fulfilled' ? avail.value : null,
            tunnel: tunnel.status === 'fulfilled' ? tunnel.value : null,
            progression: progression.status === 'fulfilled' ? progression.value : null,
            targets: targets.status === 'fulfilled' ? targets.value : [],
            hphc: hphc.status === 'fulfilled' ? hphc.value : null,
            gas: gas.status === 'fulfilled' ? gas.value : null,
            weather: weather.status === 'fulfilled' ? weather.value : null,
          };
        })
      );

      // Last-write-wins: ignore stale results
      if (reqId !== requestIdRef.current) return;

      const newAvail = {};
      const newTunnel = {};
      const newTargets = {};
      const newProgression = {};
      const newHphc = {};
      const newGas = {};
      const newWeather = {};

      for (const r of results) {
        if (r.status !== 'fulfilled') continue;
        const { siteId, availability, tunnel, progression, targets, hphc, gas, weather } = r.value;
        newAvail[siteId] = availability;
        newTunnel[siteId] = tunnel;
        newProgression[siteId] = progression;
        newTargets[siteId] = targets;
        newHphc[siteId] = hphc;
        newGas[siteId] = gas;
        newWeather[siteId] = weather;
      }

      setAvailabilityBySite(newAvail);
      setTunnelBySite(newTunnel);
      setProgressionBySite(newProgression);
      setTargetsBySite(newTargets);
      setHphcBySite(newHphc);
      setGasBySite(newGas);
      setWeatherBySite(newWeather);
    } catch (e) {
      if (reqId === requestIdRef.current) setError(e.message || 'Erreur chargement');
    } finally {
      if (reqId === requestIdRef.current) setLoading(false);
    }
  }, [siteIds, energyType, days]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Derived: merged availability (union of all site data) ─────────────
  const mergedAvailability = useMemo(() => {
    const avails = Object.values(availabilityBySite).filter(Boolean);
    if (!avails.length) return null;
    const hasData = avails.some((a) => a.has_data);
    const allTypes = [...new Set(avails.flatMap((a) => a.energy_types || []))];
    const reasons = hasData ? [] : avails.flatMap((a) => a.reasons || []);
    const primary = avails[0];
    return {
      has_data: hasData,
      energy_types: allTypes,
      reasons,
      readings_count: avails.reduce((s, a) => s + (a.readings_count || 0), 0),
      first_ts: primary?.first_ts,
      last_ts: primary?.last_ts,
      site_nom: primary?.site_nom,
    };
  }, [availabilityBySite]);

  // ── Derived: active site IDs (those with data) ────────────────────────
  const activeSiteIds = useMemo(
    () => siteIds.filter((sid) => availabilityBySite[sid]?.has_data),
    [siteIds, availabilityBySite]
  );

  // ── Primary site helpers (backward compat for single-site panels) ─────
  const primarySiteId = siteIds[0] || null;

  return {
    // State (controlled by FilterBar / URL hook)
    state: { siteIds, energyType, days, mode, unit, layers },
    // Setters
    setSiteIds,
    setEnergyType,
    setDays,
    setMode,
    setUnit,
    toggleLayer,
    // Raw data maps
    data: {
      availabilityBySite,
      tunnelBySite,
      progressionBySite,
      targetsBySite,
      hphcBySite,
      gasBySite,
      weatherBySite,
    },
    // Derived
    mergedAvailability,
    activeSiteIds,
    // Primary site (single-site backward compat)
    primarySiteId,
    primaryAvailability: availabilityBySite[primarySiteId] || null,
    primaryTunnel: tunnelBySite[primarySiteId] || null,
    primaryProgression: progressionBySite[primarySiteId] || null,
    primaryTargets: targetsBySite[primarySiteId] || [],
    primaryHphc: hphcBySite[primarySiteId] || null,
    primaryGas: gasBySite[primarySiteId] || null,
    primaryWeather: weatherBySite[primarySiteId] || null,
    // Loading / refresh
    loading,
    error,
    refresh: fetchAll,
  };
}
