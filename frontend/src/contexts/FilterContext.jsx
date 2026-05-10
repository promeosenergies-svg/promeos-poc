/**
 * PROMEOS — FilterContext (Sprint Grammaire v1.2 / Phase 3.4 V2 Hub Page L11)
 *
 * Contexte dédié aux **filtres temporels et de vue** des Hub Pages PROMEOS
 * (Briefing du jour, Énergie, Conformité, Bill-Intel, Achat, Patrimoine).
 *
 * **Distinct de ScopeContext** :
 *   - ScopeContext  → org / portefeuille / site (HIÉRARCHIE patrimoine)
 *   - FilterContext → période / vue / sort (DIMENSIONS d'analyse temporelle)
 *
 * Les deux contextes coexistent : `useScope()` + `useFilter()` consommés par
 * tout hook data de hub (`useCockpitJour`, `useEnergie`, etc.). Toute mutation
 * d'un des deux déclenche un re-fetch coherent de la page hub.
 *
 * Persisted localStorage `promeos_filters` — réhydratation au mount.
 *
 * Doctrine ref : `docs/vision/promeos_sol_doctrine.md` §12 (L11) + addendum
 * `sol_v1_1_addendum_hub_page.md` §11 (mécanisme filtres partagé).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'promeos_filters';

/**
 * @typedef {'day' | 'week' | 'month' | 'year' | 'custom'} PeriodType
 */

/**
 * @typedef {Object} FilterState
 * @property {Object} period          - Période d'analyse temporelle.
 * @property {PeriodType} period.type
 * @property {string} [period.start]  - ISO 8601 (custom uniquement).
 * @property {string} [period.end]    - ISO 8601 (custom uniquement).
 * @property {string} view            - Vue active ('briefing' | 'detail' | 'historique').
 * @property {string|null} sort       - Clé de tri active sur les highlights/tables.
 */

const DEFAULT_FILTER_STATE = Object.freeze({
  period: { type: 'week' },
  view: 'briefing',
  sort: null,
});

function loadFilters() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_FILTER_STATE;
    const parsed = JSON.parse(raw);
    return {
      period: parsed.period || DEFAULT_FILTER_STATE.period,
      view: parsed.view || DEFAULT_FILTER_STATE.view,
      sort: parsed.sort ?? null,
    };
  } catch {
    return DEFAULT_FILTER_STATE;
  }
}

function saveFilters(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* localStorage indisponible (mode incognito) — fallback silencieux */
  }
}

const FilterContext = createContext(null);

export function FilterProvider({ children }) {
  const [period, setPeriod] = useState(() => loadFilters().period);
  const [view, setView] = useState(() => loadFilters().view);
  const [sort, setSort] = useState(() => loadFilters().sort);

  useEffect(() => {
    saveFilters({ period, view, sort });
  }, [period, view, sort]);

  const setPeriodType = useCallback((type) => {
    setPeriod((p) => (p.type === type ? p : { ...p, type }));
  }, []);

  const setCustomPeriod = useCallback((start, end) => {
    setPeriod({ type: 'custom', start, end });
  }, []);

  const reset = useCallback(() => {
    setPeriod(DEFAULT_FILTER_STATE.period);
    setView(DEFAULT_FILTER_STATE.view);
    setSort(DEFAULT_FILTER_STATE.sort);
  }, []);

  const value = useMemo(
    () => ({
      period,
      view,
      sort,
      setPeriod,
      setPeriodType,
      setCustomPeriod,
      setView,
      setSort,
      reset,
    }),
    [period, view, sort, setPeriodType, setCustomPeriod, reset]
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

/**
 * Hook d'accès au FilterContext.
 * @returns {{
 *   period: { type: PeriodType, start?: string, end?: string },
 *   view: string,
 *   sort: string|null,
 *   setPeriod: (p: object) => void,
 *   setPeriodType: (t: PeriodType) => void,
 *   setCustomPeriod: (start: string, end: string) => void,
 *   setView: (v: string) => void,
 *   setSort: (s: string|null) => void,
 *   reset: () => void
 * }}
 */
export function useFilter() {
  const ctx = useContext(FilterContext);
  if (!ctx) {
    throw new Error('useFilter must be used inside <FilterProvider>');
  }
  return ctx;
}

export { FilterContext, DEFAULT_FILTER_STATE };
