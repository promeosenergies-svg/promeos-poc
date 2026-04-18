/**
 * PROMEOS — Sol V1 Cockpit Page
 *
 * Route expérimentale `/cockpit/sol` pour tester l'UX Sol V1 sans toucher
 * au cockpit principal (PRODUCTION_CANDIDATE en V2 raw, cf DECISIONS_LOG UX-1).
 *
 * Cycle démonstratif dummy engine :
 *   1. Bouton "Sol, propose une action dummy" → POST /api/sol/propose
 *   2. SolHero affiche ActionPlan avec title_fr + summary_fr + métriques
 *   3. CTA "Voir ce que j'enverrai" → ouvre SolActionPreview drawer
 *   4. User valide → POST /api/sol/preview → POST /api/sol/confirm
 *   5. SolPendingBanner apparaît avec countdown live
 *   6. User peut annuler → POST /api/sol/cancel
 *   7. SolJournal affiche le trail d'audit en bas
 *   8. SolCartouche bas-droite indique l'état global
 *
 * Tout est wrappé dans `.sol-surface` pour activer les tokens slate + warm.
 */
import { useCallback, useEffect, useState } from 'react';
import {
  SolActionPreview,
  SolCartouche,
  SolHeadline,
  SolHero,
  SolJournal,
  SolPendingBanner,
} from '../sol';
import {
  SOL_INTENT_KINDS,
  cancelAction,
  confirmAction,
  listAuditTrail,
  listPendingActions,
  previewAction,
  proposeAction,
} from '../services/api/sol';

export default function SolCockpitPage() {
  // Flow state
  const [plan, setPlan] = useState(null);                    // ActionPlan (après propose)
  const [preview, setPreview] = useState(null);              // { plan, confirmation_token, expires_at }
  const [pending, setPending] = useState(null);              // { pending_action_id, cancellation_token, scheduled_for }
  const [auditItems, setAuditItems] = useState([]);
  const [confirming, setConfirming] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [error, setError] = useState(null);

  // Dérive l'état du cartouche bas-droite
  let cartoucheState = 'repos';
  let cartoucheMessage = '';
  if (pending) {
    cartoucheState = 'pending';
    cartoucheMessage = 'Envoi programmé — annulable';
  } else if (plan) {
    cartoucheState = 'proposing';
    cartoucheMessage = 'Une action prête à être prévisualisée';
  }

  const refreshAuditTrail = useCallback(async () => {
    try {
      const data = await listAuditTrail({ limit: 20 });
      setAuditItems(data.items || []);
    } catch (e) {
      // Pas bloquant — affiche trail vide si échec
      setAuditItems([]);
    }
  }, []);

  useEffect(() => {
    refreshAuditTrail();
  }, [refreshAuditTrail]);

  // Step 1 : propose via DummyEngine
  const handlePropose = useCallback(async () => {
    setError(null);
    try {
      const resp = await proposeAction(SOL_INTENT_KINDS.DUMMY_NOOP, { confidence: 0.94 });
      if (resp.type === 'refused') {
        setError(resp.refused.reason_fr);
        return;
      }
      setPlan(resp.plan);
      await refreshAuditTrail();
    } catch (e) {
      setError(e?.response?.data?.detail?.message_fr || 'Erreur technique Sol.');
    }
  }, [refreshAuditTrail]);

  // Step 2 : preview (ouvre drawer)
  const handleOpenPreview = useCallback(async () => {
    if (!plan) return;
    setError(null);
    try {
      const pv = await previewAction(plan.correlation_id, plan.intent, { confidence: plan.confidence });
      setPreview(pv);
      setDrawerOpen(true);
    } catch (e) {
      setError(e?.response?.data?.detail?.message_fr || 'Erreur technique Sol.');
    }
  }, [plan]);

  // Step 3 : confirm (schedule)
  const handleConfirm = useCallback(async () => {
    if (!plan || !preview) return;
    setConfirming(true);
    setError(null);
    try {
      const cf = await confirmAction(
        plan.correlation_id,
        preview.confirmation_token,
        plan.intent,
        { confidence: plan.confidence },
      );
      setPending(cf);
      setDrawerOpen(false);
      setPlan(null);
      setPreview(null);
      await refreshAuditTrail();
    } catch (e) {
      setError(e?.response?.data?.detail?.message_fr || 'Erreur confirmation Sol.');
    } finally {
      setConfirming(false);
    }
  }, [plan, preview, refreshAuditTrail]);

  // Step 4 : cancel
  const handleCancel = useCallback(async () => {
    if (!pending?.cancellation_token) return;
    setError(null);
    try {
      await cancelAction(pending.cancellation_token);
      setPending(null);
      await refreshAuditTrail();
    } catch (e) {
      setError(e?.response?.data?.detail?.message_fr || 'Erreur annulation Sol.');
    }
  }, [pending, refreshAuditTrail]);

  const handleDismiss = useCallback(() => {
    setPlan(null);
  }, []);

  return (
    <div
      className="sol-surface"
      style={{
        minHeight: '100vh',
        padding: '32px 48px 80px 48px',
      }}
    >
      {/* Header page */}
      <header
        style={{
          marginBottom: '28px',
          paddingBottom: '18px',
          borderBottom: '1px solid var(--sol-rule)',
        }}
      >
        <div
          style={{
            fontSize: '10.5px',
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            color: 'var(--sol-ink-500)',
            fontWeight: 600,
            marginBottom: '6px',
          }}
        >
          Sol V1 · cockpit expérimental
        </div>
        <h1
          style={{
            fontSize: '26px',
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            margin: 0,
            letterSpacing: '-0.025em',
            lineHeight: 1.1,
          }}
        >
          Bonjour — voici votre cockpit Sol.
        </h1>
      </header>

      {/* Headline Sol */}
      <SolHeadline
        text="Sol est votre cockpit agentique. Il propose, vous validez, il exécute — et tout reste dans le journal d'audit."
        subline="Cliquez sur « Propose une action dummy » pour tester le cycle complet. En Sprint 3+, les vrais engines remplaceront le dummy (contestation facture, rapport exécutif, plan DT, appel d'offres, déclaration OPERAT)."
      />

      {/* Pending banner si action schedulée */}
      {pending && (
        <div style={{ marginTop: '20px' }}>
          <SolPendingBanner
            title="Action dummy"
            scheduledFor={pending.scheduled_for}
            onCancel={handleCancel}
          />
        </div>
      )}

      {/* Sol Hero : action proposée */}
      {plan && !pending && (
        <SolHero
          title={plan.title_fr}
          summary={plan.summary_fr}
          metrics={[
            plan.estimated_value_eur != null
              ? {
                  label: 'à récupérer',
                  value: new Intl.NumberFormat('fr-FR', {
                    style: 'currency',
                    currency: 'EUR',
                    minimumFractionDigits: 0,
                  }).format(plan.estimated_value_eur),
                }
              : null,
            {
              label: 'confiance du calcul',
              value: `${Math.round((plan.confidence || 0) * 100)} %`,
            },
            plan.estimated_time_saved_minutes != null
              ? {
                  label: 'pour valider',
                  value: `${plan.estimated_time_saved_minutes} min`,
                }
              : null,
          ].filter(Boolean)}
          onPreview={handleOpenPreview}
          onDismiss={handleDismiss}
        />
      )}

      {/* CTA propose : s'il n'y a ni plan ni pending, afficher le bouton d'amorce */}
      {!plan && !pending && (
        <div style={{ marginTop: '20px', marginBottom: '28px' }}>
          <button
            type="button"
            onClick={handlePropose}
            style={{
              fontSize: '14px',
              fontWeight: 500,
              padding: '10px 18px',
              background: 'var(--sol-calme-fg)',
              color: '#FFFFFF',
              border: '1px solid transparent',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Sol, propose une action dummy
          </button>
        </div>
      )}

      {/* Error feedback */}
      {error && (
        <div
          role="alert"
          style={{
            background: 'var(--sol-refuse-bg)',
            color: 'var(--sol-refuse-fg)',
            padding: '10px 14px',
            borderRadius: '4px',
            fontSize: '13px',
            marginBottom: '20px',
          }}
        >
          {error}
        </div>
      )}

      {/* Journal d'audit */}
      <section style={{ marginTop: '36px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            marginBottom: '12px',
            paddingBottom: '8px',
            borderBottom: '1px solid var(--sol-rule)',
          }}
        >
          <h2
            style={{
              fontSize: '15px',
              fontWeight: 600,
              color: 'var(--sol-ink-900)',
              margin: 0,
              letterSpacing: '-0.005em',
            }}
          >
            Journal des actions Sol
          </h2>
          <span
            style={{
              fontFamily: 'ui-monospace, "JetBrains Mono", monospace',
              fontSize: '10.5px',
              color: 'var(--sol-ink-500)',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}
          >
            20 dernières entrées · append-only
          </span>
        </div>
        <SolJournal items={auditItems} />
      </section>

      {/* Drawer preview */}
      <SolActionPreview
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        plan={preview?.plan || null}
        onConfirm={handleConfirm}
        confirming={confirming}
      />

      {/* Cartouche bas-droite */}
      <SolCartouche state={cartoucheState} message={cartoucheMessage} />
    </div>
  );
}
