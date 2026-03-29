/**
 * PROMEOS — TabActionsSite
 * Onglet Actions dans Site360 : liste des actions du site avec priorité/statut/impact
 * Remplace le TabStub "à venir"
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, Clock, AlertTriangle, XCircle, Plus, ArrowRight, Target } from 'lucide-react';
import { Card, CardBody, Badge, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { getActionsList } from '../services/api';
import { fmtEurFull } from '../utils/format';

const STATUS_CONFIG = {
  open: { label: 'Ouverte', variant: 'warning', icon: Clock },
  in_progress: { label: 'En cours', variant: 'info', icon: Target },
  done: { label: 'Terminée', variant: 'success', icon: CheckCircle },
  blocked: { label: 'Bloquée', variant: 'error', icon: XCircle },
  false_positive: { label: 'Faux positif', variant: 'neutral', icon: XCircle },
};

const PRIORITY_COLORS = {
  1: 'bg-red-100 text-red-800',
  2: 'bg-orange-100 text-orange-800',
  3: 'bg-amber-100 text-amber-800',
  4: 'bg-blue-100 text-blue-800',
  5: 'bg-gray-100 text-gray-600',
};

function getCountdown(dueDateStr) {
  if (!dueDateStr) return null;
  const due = new Date(dueDateStr);
  const now = new Date();
  const diffMs = due - now;
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  return diffDays;
}

function CountdownBadge({ dueDate }) {
  const days = getCountdown(dueDate);
  if (days === null) return null;

  let className = 'text-xs font-medium px-1.5 py-0.5 rounded';
  if (days < 0) className += ' bg-red-100 text-red-700';
  else if (days <= 7) className += ' bg-amber-100 text-amber-700';
  else if (days <= 30) className += ' bg-blue-100 text-blue-700';
  else className += ' bg-gray-100 text-gray-500';

  return <span className={className}>{days < 0 ? `J${days}` : `J-${days}`}</span>;
}

export default function TabActionsSite({ siteId }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [actions, setActions] = useState([]);

  useEffect(() => {
    if (!siteId) return;
    setStatus('loading');

    getActionsList({ site_id: siteId })
      .then((res) => {
        const list = Array.isArray(res) ? res : (res?.items ?? []);
        setActions(list);
        setStatus(list.length > 0 ? 'ready' : 'empty');
      })
      .catch(() => setStatus('error'));
  }, [siteId]);

  if (status === 'loading') {
    return (
      <div className="pt-6 space-y-3">
        <SkeletonCard lines={2} />
        <SkeletonCard lines={2} />
        <SkeletonCard lines={2} />
      </div>
    );
  }

  if (status === 'empty') {
    return (
      <div className="pt-6">
        <EmptyState
          title="Actions"
          text="Aucune action sur ce site. Créez-en une pour commencer."
          ctaLabel="Créer une action"
          onCtaClick={() => navigate(`/actions/new?site_id=${siteId}`)}
        />
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="pt-6">
        <EmptyState title="Actions" text="Erreur lors du chargement des actions." />
      </div>
    );
  }

  // Trier : in_progress d'abord, puis open, puis le reste, par priorité croissante
  const statusOrder = { in_progress: 0, open: 1, blocked: 2, done: 3, false_positive: 4 };
  const sorted = [...actions].sort((a, b) => {
    const sa = statusOrder[a.status] ?? 9;
    const sb = statusOrder[b.status] ?? 9;
    if (sa !== sb) return sa - sb;
    return (a.priority ?? 5) - (b.priority ?? 5);
  });

  // KPIs rapides
  const enCours = actions.filter((a) => a.status === 'in_progress').length;
  const ouvertes = actions.filter((a) => a.status === 'open').length;
  const totalGain = actions.reduce((s, a) => s + (a.estimated_gain_eur ?? 0), 0);

  return (
    <div className="pt-6 space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-3 gap-4">
        <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 rounded-lg">
          <Target size={18} className="text-blue-600" />
          <div>
            <p className="text-xs text-gray-500">En cours</p>
            <p className="text-sm font-bold text-gray-800">{enCours}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 px-4 py-3 bg-amber-50 rounded-lg">
          <Clock size={18} className="text-amber-600" />
          <div>
            <p className="text-xs text-gray-500">Ouvertes</p>
            <p className="text-sm font-bold text-gray-800">{ouvertes}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 px-4 py-3 bg-green-50 rounded-lg">
          <AlertTriangle size={18} className="text-green-600" />
          <div>
            <p className="text-xs text-gray-500">Gain estimé</p>
            <p className="text-sm font-bold text-gray-800">{fmtEurFull(totalGain)}</p>
          </div>
        </div>
      </div>

      {/* Liste des actions */}
      <Card>
        <CardBody className="divide-y divide-gray-100">
          {sorted.map((action) => {
            const cfg = STATUS_CONFIG[action.status] || STATUS_CONFIG.open;
            const StatusIcon = cfg.icon;
            return (
              <div
                key={action.id}
                className="flex items-center gap-3 py-3 first:pt-0 last:pb-0 cursor-pointer hover:bg-gray-50 -mx-4 px-4 rounded transition-colors"
                onClick={() => navigate(`/actions?highlight=${action.id}`)}
              >
                {/* Priorité */}
                <span
                  className={`flex-shrink-0 text-xs font-bold w-7 h-7 rounded-full flex items-center justify-center ${PRIORITY_COLORS[action.priority] ?? PRIORITY_COLORS[5]}`}
                >
                  P{action.priority ?? '?'}
                </span>

                {/* Contenu */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{action.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {action.source_type && (
                      <span className="text-xs text-gray-400 capitalize">{action.source_type}</span>
                    )}
                    {action.estimated_gain_eur > 0 && (
                      <span className="text-xs text-green-600 font-medium">
                        +{fmtEurFull(action.estimated_gain_eur)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Statut */}
                <Badge variant={cfg.variant} size="sm">
                  <StatusIcon size={12} className="mr-1" />
                  {cfg.label}
                </Badge>

                {/* Countdown */}
                <CountdownBadge dueDate={action.due_date} />
              </div>
            );
          })}
        </CardBody>
      </Card>

      {/* CTAs */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(`/actions/new?site_id=${siteId}`)}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-800"
        >
          <Plus size={14} />
          Créer une action
        </button>
        <button
          onClick={() => navigate('/actions')}
          className="inline-flex items-center gap-1 text-sm font-medium text-gray-500 hover:text-gray-700"
        >
          Voir le plan d&apos;actions complet
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
