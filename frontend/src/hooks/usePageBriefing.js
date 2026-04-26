/**
 * usePageBriefing — Fetch briefing éditorial Sol §5 d'une page.
 *
 * Consomme l'endpoint `/api/pages/{page_key}/briefing` (ADR-001).
 * Retourne `{ narrative, kpis, weekCards, fallbackBody, provenance }`
 * prêts à brancher dans <SolNarrative>, <SolWeekCards>, <SolPageFooter>.
 *
 * MVP Sprint 1.1 : page_key='cockpit_daily'. Sprint 1.2+ étendra.
 *
 * Doctrine §8.1 règle d'or : aucun calcul métier ici.
 */
import { useEffect, useRef, useState } from 'react';
import api from '../services/api/core';

export function usePageBriefing(pageKey, { persona = 'daily', archetype } = {}) {
  const [briefing, setBriefing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({ persona });
    if (archetype) params.set('archetype', archetype);

    api
      .get(`/pages/${pageKey}/briefing?${params.toString()}`)
      .then((res) => {
        if (cancelled) return;
        // Convention API Sol §5 : { data: Narrative, provenance: {...} }
        const payload = res.data?.data || res.data;
        const provenance = res.data?.provenance || payload?.provenance || null;
        setBriefing({
          kicker: payload?.kicker,
          title: payload?.title,
          italicHook: payload?.italic_hook,
          narrative: payload?.narrative,
          kpis: payload?.kpis || [],
          weekCards: payload?.week_cards || [],
          fallbackBody: payload?.fallback_body,
          provenance,
        });
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || `Erreur briefing ${pageKey}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, [pageKey, persona, archetype]);

  return { briefing, loading, error };
}
