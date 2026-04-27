/**
 * usePageBriefing — Fetch briefing éditorial Sol §5 d'une page.
 *
 * Consomme l'endpoint `/api/pages/{page_key}/briefing` (ADR-001).
 * Retourne `{ narrative, kpis, weekCards, fallbackBody, provenance }`
 * prêts à brancher dans <SolNarrative>, <SolWeekCards>, <SolPageFooter>.
 *
 * MVP Sprint 1.1 : page_key='cockpit_daily'. Sprint 1.2+ étendra.
 *
 * Sprint 1.1bis P0-5 (audit CX) : re-fetch sur changement scope (org_id
 * + selectedSiteId). Sans ça, le briefing reste figé sur le scope initial
 * même quand l'utilisateur switche de site dans le ScopeContext.
 *
 * Sprint 1.5bis P0-7 (audit Quality) : fetch extrait dans un callback
 * réutilisable. Le retryCount pseudo-state qui forçait useEffect à se
 * relancer est supprimé — `refetch` appelle directement le callback.
 *
 * Doctrine §8.1 règle d'or : aucun calcul métier ici.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../services/api/core';
import { useScope } from '../contexts/ScopeContext';

export function usePageBriefing(pageKey, { persona = 'daily', archetype } = {}) {
  const { org, selectedSiteId } = useScope();
  const orgId = org?.id;
  const [briefing, setBriefing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const cancelTokenRef = useRef({ cancelled: false });

  const fetchBriefing = useCallback(() => {
    // Annule le fetch précédent (anti-race condition) avant de relancer.
    cancelTokenRef.current.cancelled = true;
    const token = { cancelled: false };
    cancelTokenRef.current = token;

    setLoading(true);
    setError(null);

    const params = new URLSearchParams({ persona });
    if (archetype) params.set('archetype', archetype);
    // Backend `resolve_org_id` lit le query org_id en priorité (cf
    // routes/pages_briefing.py). Re-fetch automatique sur switch scope.
    if (orgId) params.set('org_id', String(orgId));
    if (selectedSiteId) params.set('site_id', String(selectedSiteId));

    api
      .get(`/pages/${pageKey}/briefing?${params.toString()}`)
      .then((res) => {
        if (token.cancelled) return;
        // Convention API Sol §5 : { data: Narrative, provenance: {...} }
        const payload = res.data?.data || res.data;
        const provenance = res.data?.provenance || payload?.provenance || null;
        setBriefing({
          kicker: payload?.kicker,
          title: payload?.title,
          italicHook: payload?.italic_hook,
          narrative: payload?.narrative,
          narrativeTone: payload?.narrative_tone || 'neutral',
          kpis: payload?.kpis || [],
          weekCards: payload?.week_cards || [],
          fallbackBody: payload?.fallback_body,
          provenance,
        });
      })
      .catch((err) => {
        if (!token.cancelled) setError(err?.message || `Erreur briefing ${pageKey}`);
      })
      .finally(() => {
        if (!token.cancelled) setLoading(false);
      });
  }, [pageKey, persona, archetype, orgId, selectedSiteId]);

  useEffect(() => {
    fetchBriefing();
    return () => {
      cancelTokenRef.current.cancelled = true;
    };
  }, [fetchBriefing]);

  return { briefing, loading, error, refetch: fetchBriefing };
}
