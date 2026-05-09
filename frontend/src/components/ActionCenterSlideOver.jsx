/**
 * PROMEOS — ActionCenterSlideOver V8 (Sprint Grammaire v1 Phase 2bis LEDGER)
 *
 * Inbox LEDGER quotidien. Vision Atlas/Briefing/Ledger : narration cardinale
 * "priorité → impact → action → suivi".
 *
 * Reconstruction LEGO (doctrine 2026-05-09) :
 *
 *   Briques CONSERVÉES (utiles, intactes) :
 *     - Drawer (a11y, focus trap, escape, body-lock)
 *     - useActionCenterData (polling 60s, multi-source issues+actions+notif+history)
 *     - EmptyState (états vides)
 *     - computeActionCenterBadge (export utilisé par AppShell cloche)
 *     - TabButton (structure 3 onglets, navigation claviers)
 *     - NotificationRow (onglet Alerts inchangé)
 *
 *   Briques TRANSFORMÉES :
 *     - Onglet Actions : ancienne liste ActionRow plate (anti-pattern §6.1) →
 *       Top 5 DecisionEvidenceCard rang/scope/severity/evidence[4]/cta
 *     - Onglet History : ActionRow compact préservé (vue rétrospective)
 *
 *   Briques NOUVELLES (primitifs Sol v1.1 grammar/) :
 *     - Mini-hero LEDGER (kicker mono "LEDGER · INBOX · TOP N PAR IMPACT")
 *     - SolPageFooter en bas du slide-over (Loi L6)
 *     - Term wrapping sur acronymes
 *
 *   Briques SUPPRIMÉES (anti-patterns §6.1 retirés) :
 *     - SlideOverRow / ActionRow utilisés pour Actions (remplacés par DEC)
 *     - PRIORITY_STYLES inline (priority encodé désormais dans severity DEC)
 *
 * Polling 60s tant que ouvert (inchangé).
 */
import { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, History, AlertTriangle, ChevronRight } from 'lucide-react';
import Drawer from '../ui/Drawer';
import EmptyState from '../ui/EmptyState';
import {
  getActionCenterActionsSummary,
  getActionCenterActions,
  getActionCenterIssues,
  getActionCenterNotifications,
} from '../services/api/actions';
import { DecisionEvidenceCard, SolPageFooter, Term } from './grammar';
// Phase 3.0 P2 — adaptateurs canoniques action→DEC (SoT cross-vues)
import {
  buildEvidenceFallback,
  priorityLabel as decPriorityLabel,
  toDecSeverity,
} from './grammar/decisionAdapters';
import { fmtEurShort } from '../utils/format';

// ── Configuration onglets ───────────────────────────────────────────────

const TABS = {
  actions: {
    label: 'Actions',
    icon: AlertTriangle,
    empty: 'Rien à signaler, profitez du calme',
  },
  alerts: { label: 'Alertes', icon: Bell, empty: 'Aucune alerte active' },
  history: { label: 'Historique', icon: History, empty: 'Aucun élément récent' },
};
const TAB_KEYS = Object.keys(TABS);

const SEVERITY_STYLES = {
  critical: 'text-red-600 bg-red-50',
  warning: 'text-amber-600 bg-amber-50',
  info: 'text-blue-600 bg-blue-50',
};

// Top N actions affichées en LEDGER inbox (cf. doctrine §5 limite cognitive)
const LEDGER_TOP_N = 5;

// ── Helpers data ────────────────────────────────────────────────────────

function arraysShallowEqual(a, b) {
  if (a === b) return true;
  if (!Array.isArray(a) || !Array.isArray(b)) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i]?.id !== b[i]?.id) return false;
  }
  return true;
}

function useActionCenterData(open, pollingMs = 60_000) {
  const [data, setData] = useState({
    actionsSummary: null,
    actionsList: [],
    notifications: [],
    history: [],
    loading: true,
    error: null,
  });

  const fetchAll = useCallback(async () => {
    try {
      const [summary, actionsRaw, issuesRaw, notifRaw, historyRaw] = await Promise.all([
        getActionCenterActionsSummary().catch(() => null),
        getActionCenterActions({ status: 'open,in_progress', limit: 20 }).catch(() => ({
          actions: [],
        })),
        // Doctrine §6.2 cohérence inter-surfaces : on fetch issues live
        // (anomalies auto-détectées) en plus des actions persistées. Sans ça
        // la cloche reste muette tant qu'aucune action n'est créée manuellement.
        getActionCenterIssues({ limit: 20 }).catch(() => ({ issues: [] })),
        getActionCenterNotifications({ unread_only: true }).catch(() => ({ notifications: [] })),
        getActionCenterActions({ status: 'resolved,dismissed', limit: 20 }).catch(() => ({
          actions: [],
        })),
      ]);
      const normalizedIssues = (issuesRaw?.issues || []).map((i) => ({
        id: i.issue_id,
        title: i.issue_label,
        priority: i.severity,
        site_name: i.site_name,
        domain: i.domain,
        estimated_impact_eur: i.estimated_impact_eur,
        __type: 'issue',
      }));
      // Tri par impact € décroissant — vision LEDGER "ordering par impact"
      const merged = [...normalizedIssues, ...(actionsRaw?.actions || [])].sort((a, b) => {
        const ia = a.estimated_impact_eur || a.estimated_loss_eur || 0;
        const ib = b.estimated_impact_eur || b.estimated_loss_eur || 0;
        return ib - ia;
      });
      const next = {
        actionsSummary: summary,
        actionsList: merged,
        notifications: notifRaw?.notifications || [],
        history: historyRaw?.actions || [],
        loading: false,
        error: null,
      };
      setData((prev) => {
        if (
          prev.actionsSummary === next.actionsSummary &&
          arraysShallowEqual(prev.actionsList, next.actionsList) &&
          arraysShallowEqual(prev.notifications, next.notifications) &&
          arraysShallowEqual(prev.history, next.history) &&
          prev.loading === false &&
          prev.error === null
        ) {
          return prev;
        }
        return next;
      });
    } catch (err) {
      setData((d) => ({ ...d, loading: false, error: err?.message || 'Erreur de chargement' }));
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    fetchAll();
    const interval = setInterval(fetchAll, pollingMs);
    return () => clearInterval(interval);
  }, [open, fetchAll, pollingMs]);

  return { ...data, refetch: fetchAll };
}

export function computeActionCenterBadge(summary, notifications) {
  const overdue = summary?.overdue_count || 0;
  const open = summary?.open_count || 0;
  const critical = (notifications || []).filter((n) => n.severity === 'critical').length;
  const warning = (notifications || []).filter((n) => n.severity === 'warning').length;
  const unread = (notifications || []).length;
  const total = open + unread;

  if (total === 0) return { count: null, color: 'gray' };
  const count = total > 99 ? '99+' : String(total);
  if (overdue > 0 || critical > 0) return { count, color: 'red' };
  if (warning > 0) return { count, color: 'amber' };
  return { count, color: 'gray' };
}

// ── Helpers LEDGER (mapping action → DecisionEvidenceCard) ──────────────

/**
 * Convertit une action/issue en payload DecisionEvidenceCard (doctrine §5.6).
 * 4 cellules garanties (contrat L9). Tonalité severity calme par défaut.
 */
function buildDecisionFromAction(action, rang) {
  const isIssue = action.__type === 'issue';
  const impactEur = action.estimated_impact_eur || action.estimated_loss_eur || 0;
  const category = (action.domain || (isIssue ? 'ANOMALIE' : 'ACTION')).toUpperCase();
  const scope = (action.site_name || 'PORTEFEUILLE').toUpperCase();

  // Phase 3.0 P2 (audit simplify) : utilisation des adaptateurs canoniques
  // grammar/decisionAdapters.js. Avant Phase 3.0, ce fichier réimplémentait
  // toDecSeverity localement avec une divergence : `medium → 'warning'` ici
  // mais `medium → 'neutral'` dans CockpitPilotage. SoT unique élimine ce bug.
  const dueDate = action.due_date
    ? new Date(action.due_date).toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit',
      })
    : null;

  // Surcharge minimale du fallback : on remplace la cellule CATÉGORIE par
  // une cellule TYPE plus spécifique au LEDGER (issue vs action manuelle).
  const fallback = buildEvidenceFallback({
    impactDisplay: impactEur > 0 ? fmtEurShort(impactEur) : null,
    category,
    priorityLabel: decPriorityLabel(action.priority),
    rang,
    dueDate,
    status: action.status || (isIssue ? 'À traiter' : 'Ouverte'),
  });
  // [IMPACT, CATÉGORIE→TYPE override, PRIORITÉ, ÉCHÉANCE/STATUT] pour LEDGER
  const evidence = [
    fallback[0],
    {
      label: 'TYPE',
      value: isIssue ? 'Anomalie auto' : 'Action manuelle',
      unit: '',
      helper: '',
    },
    fallback[2],
    fallback[3],
  ];

  const lead = isIssue
    ? `Anomalie auto-détectée sur ${action.site_name || 'le périmètre'}.${
        impactEur > 0 ? ` Impact estimé ${fmtEurShort(impactEur)}.` : ''
      } À arbitrer dans la file de pilotage.`
    : `Action en cours d'exécution.${impactEur > 0 ? ` Gain attendu ${fmtEurShort(impactEur)}.` : ''}`;

  const ctaHref = action.__type === 'issue' || !action.id ? '/anomalies' : `/actions/${action.id}`;

  return {
    rang,
    category,
    scope,
    severity: toDecSeverity(action.priority),
    titre: action.title || action.summary || 'Sans titre',
    lead,
    evidence,
    primaryCta: { label: "Voir l'action", href: ctaHref },
    methodologyRef: '/methodologie/anomalies',
  };
}

// ── UI primitifs locaux (conservés pour Alerts + History) ───────────────

function TabButton({ active, onClick, count, icon: Icon, label }) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm transition-all border-b-2 ${
        active
          ? 'border-blue-600 text-blue-700 font-medium bg-blue-50/30'
          : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
      }`}
    >
      {Icon && <Icon size={14} />}
      <span>{label}</span>
      {count > 0 && (
        <span
          className={`ml-1 px-1.5 py-0.5 text-[10px] rounded-full min-w-[18px] ${
            active ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-700'
          }`}
        >
          {count > 99 ? '99+' : count}
        </span>
      )}
    </button>
  );
}

function SlideOverRow({ accent, title, meta, subtitle, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2.5 hover:bg-slate-50 rounded-lg transition-all border border-transparent hover:border-slate-200 flex items-start gap-2 group"
    >
      {accent}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-800 truncate font-medium">{title}</p>
        {meta && <p className="text-xs mt-0.5">{meta}</p>}
        {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      <ChevronRight size={14} className="text-slate-300 group-hover:text-slate-500 mt-1 shrink-0" />
    </button>
  );
}

function NotificationRow({ notification, onClick }) {
  const sev = notification.severity || 'info';
  const sevClass = SEVERITY_STYLES[sev] || SEVERITY_STYLES.info;
  return (
    <SlideOverRow
      accent={
        <div
          className={`px-1.5 py-0.5 text-[10px] rounded ${sevClass} font-medium shrink-0 uppercase`}
        >
          {sev}
        </div>
      }
      title={notification.title || notification.message}
      subtitle={
        notification.created_at
          ? new Date(notification.created_at).toLocaleString('fr-FR', {
              dateStyle: 'short',
              timeStyle: 'short',
            })
          : null
      }
      onClick={onClick}
    />
  );
}

/** Vue compacte conservée pour onglet History (rétrospective non-LEDGER). */
function HistoryRow({ action, onClick }) {
  const tone =
    action.priority === 'critical' || action.priority === 'high'
      ? 'text-red-600'
      : action.priority === 'medium'
        ? 'text-amber-600'
        : 'text-slate-500';
  return (
    <SlideOverRow
      accent={<div className="mt-1 w-1.5 h-1.5 rounded-full bg-slate-400" />}
      title={action.title || action.summary}
      meta={
        action.due_date ? (
          <span className={tone}>
            Échéance : {new Date(action.due_date).toLocaleDateString('fr-FR')}
          </span>
        ) : null
      }
      subtitle={action.site_name}
      onClick={onClick}
    />
  );
}

// ── Composant racine ────────────────────────────────────────────────────

export default function ActionCenterSlideOver({ open, onClose, defaultTab = 'actions' }) {
  const safeDefault = useMemo(
    () => (TAB_KEYS.includes(defaultTab) ? defaultTab : 'actions'),
    [defaultTab]
  );
  const [tab, setTab] = useState(safeDefault);
  const navigate = useNavigate();
  const { actionsSummary, actionsList, notifications, history, loading, error } =
    useActionCenterData(open);

  useEffect(() => {
    if (open) setTab(safeDefault);
  }, [open, safeDefault]);

  const counts = useMemo(
    () => ({
      actions: actionsList.length,
      alerts: notifications.length,
      history: history.length,
    }),
    [actionsList, notifications, history]
  );

  const navigateAndClose = useCallback(
    (path) => {
      navigate(path);
      onClose();
    },
    [navigate, onClose]
  );

  const handleNotificationClick = useCallback(
    (notification) => navigateAndClose(notification.link || '/anomalies'),
    [navigateAndClose]
  );

  const handleHistoryClick = useCallback(
    (action) =>
      navigateAndClose(
        action.__type === 'issue' || !action.id ? '/anomalies' : `/actions/${action.id}`
      ),
    [navigateAndClose]
  );

  const renderActions = () => {
    if (actionsList.length === 0) {
      return <EmptyState variant="empty" title="Tout est en ordre" text={TABS.actions.empty} />;
    }
    const top = actionsList.slice(0, LEDGER_TOP_N);
    const remaining = actionsList.length - top.length;
    return (
      <div className="flex flex-col gap-3" data-testid="ledger-top-decisions">
        {top.map((a, i) => (
          <DecisionEvidenceCard key={a.id || i} {...buildDecisionFromAction(a, i + 1)} />
        ))}
        {remaining > 0 && (
          <p className="text-xs text-center text-slate-500 pt-1">
            + {remaining} autre{remaining > 1 ? 's' : ''} dans le centre d'action
          </p>
        )}
        {actionsSummary?.overdue_count > 0 && (
          <p className="text-xs text-red-600 px-1 pt-2 font-medium">
            {actionsSummary.overdue_count} action
            {actionsSummary.overdue_count > 1 ? 's' : ''} en retard
          </p>
        )}
      </div>
    );
  };

  const renderAlerts = () => {
    if (notifications.length === 0) {
      return <EmptyState variant="empty" title="Aucune alerte" text={TABS.alerts.empty} />;
    }
    return (
      <div className="flex flex-col gap-1">
        {notifications.map((n, i) => (
          <NotificationRow
            key={n.id || i}
            notification={n}
            onClick={() => handleNotificationClick(n)}
          />
        ))}
      </div>
    );
  };

  const renderHistory = () => {
    if (history.length === 0) {
      return <EmptyState variant="empty" title="Historique vide" text={TABS.history.empty} />;
    }
    return (
      <div className="flex flex-col gap-1">
        {history.slice(0, 20).map((a, i) => (
          <HistoryRow key={a.id || i} action={a} onClick={() => handleHistoryClick(a)} />
        ))}
      </div>
    );
  };

  const renderList = () => {
    if (loading) {
      return (
        <div className="flex flex-col gap-2 p-1">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-slate-100 rounded-lg animate-pulse" />
          ))}
        </div>
      );
    }
    if (error) {
      return (
        <div className="p-4 text-center">
          <p className="text-sm text-red-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 text-xs text-blue-600 hover:underline"
          >
            Recharger
          </button>
        </div>
      );
    }
    if (tab === 'actions') return renderActions();
    if (tab === 'alerts') return renderAlerts();
    return renderHistory();
  };

  // Mini-hero LEDGER : kicker mono + intent (doctrine §5)
  const ledgerKicker = useMemo(() => {
    if (tab === 'actions') {
      const total = actionsList.length;
      const top = Math.min(LEDGER_TOP_N, total);
      if (total === 0) return 'LEDGER · INBOX · AUCUNE ACTION OUVERTE';
      return `LEDGER · INBOX · TOP ${top} PAR IMPACT`;
    }
    if (tab === 'alerts') return 'LEDGER · ALERTES SYSTÈME';
    return 'LEDGER · HISTORIQUE 7 JOURS';
  }, [tab, actionsList.length]);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Centre d'actions"
      className="max-w-[440px]"
      noPadding
    >
      <div className="flex flex-col h-full">
        {/* Mini-hero LEDGER (kicker + intent) */}
        <div
          className="px-3 py-2 border-b border-slate-200 bg-white"
          data-testid="ledger-mini-hero"
        >
          <p className="font-mono uppercase tracking-[0.07em] text-[10.5px] text-slate-500">
            {ledgerKicker}
          </p>
          {tab === 'actions' && actionsList.length > 0 && (
            <p className="text-[12.5px] mt-1 text-slate-700 leading-snug">
              Priorité → Impact → Action → Suivi. Données <Term acronyme="EMS" /> +{' '}
              <Term acronyme="CRE" />.
            </p>
          )}
        </div>

        {/* Tabs nav */}
        <nav className="flex border-b border-slate-200 bg-white" role="tablist">
          {TAB_KEYS.map((key) => {
            const cfg = TABS[key];
            return (
              <TabButton
                key={key}
                active={tab === key}
                onClick={() => setTab(key)}
                count={key === 'history' ? undefined : counts[key]}
                icon={cfg.icon}
                label={cfg.label}
              />
            );
          })}
        </nav>

        {/* Liste */}
        <div className="flex-1 overflow-y-auto p-3">{renderList()}</div>

        {/* Footer Sol — SolPageFooter compact + lien CTA route complète */}
        <footer
          className="border-t border-slate-200 px-3 py-2 bg-slate-50/50"
          data-testid="ledger-footer"
        >
          <SolPageFooter
            source="ActionCenter + Anomalies + Bill-Intel"
            confidence="medium"
            updatedAt={new Date().toISOString()}
            methodologyUrl="/methodologie/anomalies"
            className="mt-0 pt-0 border-t-0"
          />
          <button
            onClick={() => navigateAndClose('/anomalies')}
            className="w-full text-center text-xs text-blue-600 hover:text-blue-700 hover:underline py-1.5 mt-1"
          >
            Ouvrir le centre d'action complet →
          </button>
        </footer>
      </div>
    </Drawer>
  );
}
