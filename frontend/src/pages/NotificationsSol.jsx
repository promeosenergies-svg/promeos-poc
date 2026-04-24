/**
 * PROMEOS — NotificationsSol (Sprint REFONTE-P6 S1 — Pilot Option A)
 *
 * Wrapper Sol autour de NotificationsPage (intact). Préserve les 50 features MAIN
 * selon la règle SUPERSET du Sprint P6 S1. Ajoute :
 *  - SolPageHeader (kicker + title Fraunces + narrative 5 briques)
 *  - 3 SolWeekCard "Cette semaine chez vous" (À regarder / Dérive détectée / Bonne nouvelle)
 *
 * NotificationsPage reste source de vérité data + UI (3 KPIs header, tabs triage,
 * sticky filter bar, table 20/page, drawer, bulk actions, ActionCenter bell intact).
 *
 * Phase 2 ultérieure : refonte complète Pattern B si ce wrapper est insuffisant.
 */

import React, { useEffect, useState } from 'react';
import {
  SolPageHeader,
  SolWeekCard,
} from '../ui/sol';
import NotificationsPage from './NotificationsPage';
import { getNotificationsList, getNotificationsSummary } from '../services/api/cockpit';
import { useScope } from '../contexts/ScopeContext';
import {
  buildNotificationsKicker,
  buildNotificationsNarrative,
  interpretWeek,
} from './notifications/sol_presenters';

/**
 * Hook local pour récupérer events + liveSummary pour le header + week cards.
 * NotificationsPage fait son propre fetch en interne — c'est volontairement
 * dupliqué (pattern wrapper non-invasif). En J3+ on extraira la data dans un
 * hook partagé `useNotificationsState()` pour éviter le double fetch.
 */
function useNotificationsHeaderData() {
  const { selectedSiteId, selectedOrgId } = useScope();
  const [events, setEvents] = useState([]);
  const [liveSummary, setLiveSummary] = useState(null);
  const [lastSync, setLastSync] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const params = {};
        if (selectedSiteId) params.site_id = selectedSiteId;
        if (selectedOrgId) params.org_id = selectedOrgId;

        const [list, summary] = await Promise.all([
          getNotificationsList(params),
          getNotificationsSummary(selectedOrgId, selectedSiteId),
        ]);
        if (cancelled) return;
        setEvents(Array.isArray(list) ? list : list?.events || []);
        setLiveSummary(summary || null);
        setLastSync(new Date());
      } catch (_err) {
        // silent — NotificationsPage gère son propre error state
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedSiteId, selectedOrgId]);

  return { events, liveSummary, lastSync };
}

export default function NotificationsSol() {
  const { events, liveSummary, lastSync } = useNotificationsHeaderData();
  const week = interpretWeek({ events });

  const kicker = buildNotificationsKicker({ liveSummary });
  const narrative = buildNotificationsNarrative({ events, lastSync });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Sol storytelling header */}
      <SolPageHeader
        kicker={kicker}
        title="Votre centre d'alertes"
        titleEm="— synthèse 5 briques"
        narrative={narrative}
      />

      {/* 3 SolWeekCard "Cette semaine chez vous" */}
      <section
        aria-label="Cette semaine chez vous"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 16,
        }}
      >
        <SolWeekCard {...week.aRegarder} />
        <SolWeekCard {...week.deriveDetectee} />
        <SolWeekCard {...week.bonneNouvelle} />
      </section>

      {/* NotificationsPage MAIN intact — 50 features préservées */}
      <NotificationsPage />
    </div>
  );
}
