/**
 * PROMEOS — ActionCenterSlideOver V7
 *
 * Slide-over header avec 3 onglets (Actions humaines / Alertes système / Historique 7j).
 * Réutilise le composant Drawer du design system (a11y, focus trap, escape, body-lock).
 * Polling 60s tant que le panneau est ouvert.
 */
import { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Bell, History, ChevronRight } from 'lucide-react';
import Drawer from '../ui/Drawer';
import EmptyState from '../ui/EmptyState';
import {
  getActionCenterActionsSummary,
  getActionCenterActions,
  getActionCenterNotifications,
} from '../services/api/actions';

const TABS = {
  actions: { label: 'Actions', icon: AlertTriangle, empty: 'Rien à signaler, profitez du calme' },
  alerts: { label: 'Alertes', icon: Bell, empty: 'Aucune alerte active' },
  history: { label: 'Historique', icon: History, empty: 'Aucun élément récent' },
};
const TAB_KEYS = Object.keys(TABS);

const PRIORITY_STYLES = {
  critical: { text: 'text-red-600', bg: 'bg-red-500' },
  high: { text: 'text-red-600', bg: 'bg-red-500' },
  medium: { text: 'text-amber-600', bg: 'bg-amber-500' },
  low: { text: 'text-slate-500', bg: 'bg-slate-400' },
  default: { text: 'text-slate-500', bg: 'bg-slate-400' },
};

const SEVERITY_STYLES = {
  critical: 'text-red-600 bg-red-50',
  warning: 'text-amber-600 bg-amber-50',
  info: 'text-blue-600 bg-blue-50',
};

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
      const [summary, actionsRaw, notifRaw, historyRaw] = await Promise.all([
        getActionCenterActionsSummary().catch(() => null),
        getActionCenterActions({ status: 'open,in_progress', limit: 20 }).catch(() => ({
          actions: [],
        })),
        getActionCenterNotifications({ unread_only: true }).catch(() => ({ notifications: [] })),
        getActionCenterActions({ status: 'resolved,dismissed', limit: 20 }).catch(() => ({
          actions: [],
        })),
      ]);
      const next = {
        actionsSummary: summary,
        actionsList: actionsRaw?.actions || [],
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

/** Header badge computed from polling summary — { count: string|null, color: 'red'|'amber'|'gray' } */
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

/** Unified row used for actions, history and notifications. */
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

function ActionRow({ action, onClick }) {
  const style = PRIORITY_STYLES[action.priority] || PRIORITY_STYLES.default;
  return (
    <SlideOverRow
      accent={<div className={`mt-1 w-1.5 h-1.5 rounded-full ${style.bg}`} />}
      title={action.title || action.summary}
      meta={
        action.due_date ? (
          <span className={style.text}>
            Échéance : {new Date(action.due_date).toLocaleDateString('fr-FR')}
          </span>
        ) : null
      }
      subtitle={action.site_name}
      onClick={onClick}
    />
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

export default function ActionCenterSlideOver({ open, onClose, defaultTab = 'actions' }) {
  const safeDefault = TAB_KEYS.includes(defaultTab) ? defaultTab : 'actions';
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

  const handleActionClick = useCallback(
    (action) => navigateAndClose(action.id ? `/actions/${action.id}` : '/anomalies'),
    [navigateAndClose]
  );

  const handleNotificationClick = useCallback(
    (notification) => navigateAndClose(notification.link || '/anomalies'),
    [navigateAndClose]
  );

  const renderList = () => {
    if (loading) {
      return (
        <div className="flex flex-col gap-2 p-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-slate-100 rounded-lg animate-pulse" />
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

    const tabConfig = TABS[tab];
    if (tab === 'actions') {
      return actionsList.length === 0 ? (
        <EmptyState variant="empty" title="Tout est en ordre" text={tabConfig.empty} />
      ) : (
        <>
          <div className="flex flex-col gap-1">
            {actionsList.map((a, i) => (
              <ActionRow key={a.id || i} action={a} onClick={() => handleActionClick(a)} />
            ))}
          </div>
          {actionsSummary?.overdue_count > 0 && (
            <p className="text-xs text-red-600 px-3 pt-3 font-medium">
              {actionsSummary.overdue_count} action
              {actionsSummary.overdue_count > 1 ? 's' : ''} en retard
            </p>
          )}
        </>
      );
    }
    if (tab === 'alerts') {
      return notifications.length === 0 ? (
        <EmptyState variant="empty" title="Aucune alerte" text={tabConfig.empty} />
      ) : (
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
    }
    return history.length === 0 ? (
      <EmptyState variant="empty" title="Historique vide" text={tabConfig.empty} />
    ) : (
      <div className="flex flex-col gap-1">
        {history.slice(0, 20).map((a, i) => (
          <ActionRow key={a.id || i} action={a} onClick={() => handleActionClick(a)} />
        ))}
      </div>
    );
  };

  return (
    <Drawer open={open} onClose={onClose} title="Centre d'actions" className="max-w-[400px]">
      <div className="-mx-6 -my-4 flex flex-col h-full">
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
        <div className="flex-1 overflow-y-auto p-2">{renderList()}</div>
        <footer className="border-t border-slate-200 p-2 bg-slate-50/50">
          <button
            onClick={() => navigateAndClose('/anomalies')}
            className="w-full text-center text-xs text-blue-600 hover:text-blue-700 hover:underline py-1.5"
          >
            Voir tout l'historique →
          </button>
        </footer>
      </div>
    </Drawer>
  );
}
