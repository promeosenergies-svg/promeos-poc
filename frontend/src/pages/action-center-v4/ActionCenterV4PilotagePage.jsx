import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import PageShell from '../../ui/PageShell';
import EmptyState from '../../ui/EmptyState';
import ErrorState from '../../ui/ErrorState';
import { useAuth } from '../../contexts/AuthContext';

import { usePilotageFilePrioritaire, useActionCenterV4Items } from '../../hooks/v4';
import { exportComexPdf } from '../../services/api/v4ActionCenter';
import { PILOTAGE_COPY, ROLE_LABELS_V4 } from './constants';
import { EditorialNarrativeBlock } from './components/narrative/EditorialNarrativeBlock';
import { ItemDetailDrawer } from './components/drawer/ItemDetailDrawer';
import { Masthead } from './components/narrative/Masthead';
import { NarrativeBar } from './components/narrative/NarrativeBar';
import { PilotageTabs } from './components/narrative/PilotageTabs';
import { PilotageViewToggle } from './components/narrative/PilotageViewToggle';
import { PriorityQueueCard } from './components/narrative/PriorityQueueCard';

/**
 * M2-5.10.D — Page Pilotage (`/action-center-v4/pilotage`) — vue Resp.
 * Énergie « ce matin » avec la file prioritaire (5 items P0/P1 actifs).
 *
 * Maquette source : `docs/maquettes/centre_action_v4/centre_action_v4_pilotage_
 * decisions_v031.html` §8.1. Scope MV3 réduit : masthead Sol + tabs internes
 * + section « File prioritaire » uniquement. Hors scope (BACKLOG_M3) :
 * narrative bar agrégée, escalation banner, quick filters, sections Jalons /
 * À surveiller / Clôturé récemment, view toggle Décisions/Journal (= .E),
 * SLA dates, vues Audit/Dense.
 *
 * Clic sur une card → ouvre le drawer détail (réutilise `ItemDetailDrawer`).
 * On consomme `useActionCenterV4Items` à zéro coût juste pour pouvoir
 * passer `refetch` à `onRefreshList` (parité avec la page Référentiel) —
 * sinon une transition lifecycle depuis le drawer ne rafraîchirait pas la
 * file (les hooks Pilotage et Items sont indépendants côté state).
 */
export function ActionCenterV4PilotagePage() {
  const [selectedItemId, setSelectedItemId] = useState(null);

  // M2-5.12 — persona + org du user connecté pour le Masthead enrichi
  // (maquette Sophie Marin 2026-05-22). useAuth est safe (l'app entière
  // est sous RequireAuth, donc user et role sont garantis non-null).
  const { user, org, role } = useAuth();
  const persona = useMemo(() => {
    if (!user) return null;
    const fullName = [user.prenom, user.nom].filter(Boolean).join(' ').trim();
    const roleLabel = ROLE_LABELS_V4[role] || role;
    const orgShort = org?.nom?.replace(/^Groupe\s+/i, '') || '';
    // « Sophie Marin · Resp. Énergie HELIOS »
    return [fullName, [roleLabel, orgShort].filter(Boolean).join(' ')].filter(Boolean).join(' · ');
  }, [user, role, org]);

  const { data, loading, error, refetch } = usePilotageFilePrioritaire({ limit: 5 });
  // Liste référentiel utilisée comme `onRefreshList` du drawer pour rester
  // cohérent avec la page liste (un succès transition refresh aussi la
  // liste globale même si l'utilisateur n'est pas dessus).
  const { refetch: refetchAll } = useActionCenterV4Items({ offset: 0, limit: 20 });

  const items = data?.items || [];
  const ready = !loading && !error;

  const handleOpenItem = useCallback((item) => {
    setSelectedItemId(item.id);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedItemId(null);
  }, []);

  // Succès transition / mutation → refetch file + référentiel (le drawer
  // gère son propre refetch item via useActionCenterV4Item).
  const handleRefreshFromDrawer = useCallback(() => {
    refetch();
    refetchAll();
  }, [refetch, refetchAll]);

  // M2-6.B.pdf — handler export PDF COMEX. Active le CTA disabled depuis
  // M2-5.12. Pattern download blob standard : fetch responseType=blob →
  // createObjectURL → click programmatique → cleanup URL. Filename extrait
  // du header `Content-Disposition` (exposé en CORS via main.py M2-6.B.pdf).
  const [isExportingComex, setIsExportingComex] = useState(false);
  const handleExportComex = useCallback(async () => {
    if (isExportingComex) return;
    setIsExportingComex(true);
    try {
      const response = await exportComexPdf();
      const cd =
        response.headers?.['content-disposition'] ||
        response.headers?.['Content-Disposition'] ||
        '';
      const filenameMatch = cd.match(/filename="?([^";]+)"?/i);
      const filename =
        filenameMatch?.[1] ||
        `promeos_comex_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.pdf`;

      // `response.data` est déjà un Blob (axios responseType: 'blob').
      const blob =
        response.data instanceof Blob
          ? response.data
          : new Blob([response.data], { type: 'application/pdf' });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      // Toast/notification non disponible MV3 — log console + alert simple.
      // M3+ : intégrer notification system (cf. AppShell toast pattern).
      console.error('[ExportCOMEX] Échec génération PDF :', err);
      // eslint-disable-next-line no-alert
      alert(
        'Erreur lors de la génération du PDF COMEX. ' +
          (err?.promeos?.message || err?.message || 'Voir console pour détail.')
      );
    } finally {
      setIsExportingComex(false);
    }
  }, [isExportingComex]);

  return (
    <PageShell
      editorialHeader={
        <Masthead
          subtitle={PILOTAGE_COPY.mastheadSubtitle}
          // M2-5.10.bis clôture (audit P0-2) : compteur contextuel « N actions
          // prioritaires » au lieu de simple « N items » (qui faisait croire
          // au total org alors qu'on visualise un sous-ensemble P0/P1).
          countLabel={
            items.length === 0
              ? null
              : items.length === 1
                ? '1 action prioritaire'
                : `${items.length} actions prioritaires`
          }
          // M2-5.12 — persona + heure live (maquette Sophie Marin).
          persona={persona}
          withLiveTime
        />
      }
    >
      <PilotageTabs />
      <PilotageViewToggle />

      {/* M2-5.12 — bloc éditorial narratif (eyebrow + phrase Fraunces + 3 CTAs).
          Données sourcées via useActionCenterV4Summary, réutilisé par
          NarrativeBar plus bas (React déduplique si stable).
          M2-6.B.pdf — onExportComex câblé (ACTIVE le CTA Exporter COMEX).
          Les 2 autres CTAs (Lancer le triage / Voir l'impact) restent disabled
          MV3 (Q24=A) — pas de handler fourni → bouton reste disabled. */}
      <EditorialNarrativeBlock
        orgName={org?.nom || 'Organisation'}
        sitesCount={5}
        onExportComex={handleExportComex}
        exportComexLoading={isExportingComex}
      />

      {/* M2-5.11.C — Synthèse 5 compteurs CFO posée au sommet du pilotage. */}
      <NarrativeBar />

      {/* Header section File prioritaire — maquette §8.1 lignes 870-876. */}
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <div>
          <h2
            className="text-[15px] font-semibold leading-tight"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-900)',
            }}
          >
            {PILOTAGE_COPY.fileSectionTitle}
            {items.length > 0 && (
              <span
                className="ml-2 font-mono text-[10px] font-normal"
                style={{ color: 'var(--sol-ink-500)' }}
              >
                {items.length}
              </span>
            )}
          </h2>
          <p
            className="mt-0.5 text-[12px] italic"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-500)',
            }}
          >
            {PILOTAGE_COPY.fileSectionSub}
          </p>
        </div>
      </div>

      {loading && (
        <div className="space-y-2" aria-busy="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-[110px] animate-pulse rounded-[8px] border"
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
              }}
            />
          ))}
        </div>
      )}

      {!loading && error && (
        <ErrorState
          title={PILOTAGE_COPY.errorTitle}
          message={error.message || ''}
          onRetry={refetch}
        />
      )}

      {ready && items.length === 0 && (
        <EmptyState
          variant="empty"
          title={PILOTAGE_COPY.emptyTitle}
          text={PILOTAGE_COPY.emptyText}
        />
      )}

      {ready && items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <PriorityQueueCard key={item.id} item={item} onOpenItem={handleOpenItem} />
          ))}
          {/* M2-5.10.bis clôture (audit CS P1-2) : pont vers le référentiel
              pour éviter le faux 2-backlogs (« Pilotage = 5 / Référentiel = N »
              sans lien). La constante `fileLinkToReferentiel` était définie
              mais non rendue. */}
          <div className="mt-3 text-right">
            <Link
              to="/action-center-v4"
              className="font-mono text-[10.5px] font-medium uppercase tracking-[0.08em] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
              style={{
                color: 'var(--sol-ink-700)',
                borderBottom: '1px dotted var(--sol-ink-400)',
                paddingBottom: '1px',
                textDecoration: 'none',
              }}
            >
              {PILOTAGE_COPY.fileLinkToReferentiel}
            </Link>
          </div>
        </div>
      )}

      <ItemDetailDrawer
        itemId={selectedItemId}
        open={selectedItemId !== null}
        onClose={handleCloseDrawer}
        onRefreshList={handleRefreshFromDrawer}
      />
    </PageShell>
  );
}
