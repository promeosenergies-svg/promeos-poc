/**
 * PROMEOS - Admin Audit Log Page (Sprint 12)
 * Timeline filtrable: action, user, resource + detail panel (before/after).
 */
import { useState, useEffect, useCallback } from 'react';
import {
  ClipboardList,
  ChevronLeft,
  ChevronRight,
  Filter,
  ChevronDown,
  ChevronUp,
  Search,
} from 'lucide-react';
import { getAuditLogs } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { PageShell, EmptyState } from '../ui';
import { useToast } from '../ui/ToastProvider';

const ACTION_COLORS = {
  login: 'bg-green-100 text-green-700',
  logout: 'bg-gray-100 text-gray-600',
  impersonate: 'bg-purple-100 text-purple-700',
  switch_org: 'bg-blue-100 text-blue-700',
  password_change: 'bg-yellow-100 text-yellow-700',
  create_user: 'bg-teal-100 text-teal-700',
  patch_user: 'bg-orange-100 text-orange-700',
  change_role: 'bg-red-100 text-red-700',
  set_scopes: 'bg-indigo-100 text-indigo-700',
  soft_delete_user: 'bg-red-100 text-red-700',
  edit: 'bg-blue-100 text-blue-700',
  test_action: 'bg-gray-100 text-gray-600',
  test_api: 'bg-gray-100 text-gray-600',
};

const ACTION_LABELS = {
  login: 'Connexion',
  logout: 'Deconnexion',
  impersonate: 'Impersonation',
  switch_org: 'Changement org.',
  password_change: 'Modif. mot de passe',
  create_user: 'Creation utilisateur',
  patch_user: 'Modification utilisateur',
  change_role: 'Changement role',
  set_scopes: 'Modification scopes',
  soft_delete_user: 'Desactivation',
};

function DetailPanel({ detail }) {
  if (!detail || (typeof detail === 'object' && Object.keys(detail).length === 0)) {
    return <span className="text-xs text-gray-300 italic">Aucun detail</span>;
  }

  const entries =
    typeof detail === 'string'
      ? (() => {
          try {
            return Object.entries(JSON.parse(detail));
          } catch {
            return [['raw', detail]];
          }
        })()
      : Object.entries(detail);

  return (
    <div className="bg-gray-50 rounded-lg p-3 mt-2 text-xs space-y-1.5">
      {entries.map(([key, val]) => (
        <div key={key} className="flex gap-2">
          <span className="font-mono text-gray-500 min-w-[100px]">{key}:</span>
          <span className="text-gray-700 break-all">
            {typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function AdminAuditLogPage() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [actionFilter, setActionFilter] = useState('');
  const [resourceFilter, setResourceFilter] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [searchText, setSearchText] = useState('');
  const limit = 20;

  const load = useCallback(() => {
    setLoading(true);
    const params = { limit, offset: page * limit };
    if (actionFilter) params.action = actionFilter;
    if (resourceFilter) params.resource_type = resourceFilter;

    getAuditLogs(params)
      .then((data) => {
        setEntries(data.entries || []);
        setTotal(data.total || 0);
      })
      .catch(() => toast("Erreur lors du chargement de l'audit log", 'error'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, actionFilter, resourceFilter]);

  useEffect(() => {
    load();
  }, [load]);

  if (!hasPermission('admin')) {
    return (
      <PageShell icon={ClipboardList} title="Audit Log">
        <EmptyState
          icon={ClipboardList}
          title="Acces refuse"
          text="Vous n'avez pas les droits d'administration."
        />
      </PageShell>
    );
  }

  const totalPages = Math.ceil(total / limit);

  const filtered = searchText
    ? entries.filter((e) =>
        `${e.action} ${e.user_name || ''} ${e.resource_type || ''} ${e.resource_id || ''}`
          .toLowerCase()
          .includes(searchText.toLowerCase())
      )
    : entries;

  return (
    <PageShell
      icon={ClipboardList}
      title="Audit Log"
      subtitle={`${total} événement${total !== 1 ? 's' : ''} tracés`}
    >
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Filter size={16} className="text-gray-400" />
        <select
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(0);
          }}
          className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="">Toutes les actions</option>
          <option value="login">Connexion</option>
          <option value="logout">Deconnexion</option>
          <option value="impersonate">Impersonation</option>
          <option value="switch_org">Switch Org</option>
          <option value="password_change">Modif. mot de passe</option>
          <option value="create_user">Creation utilisateur</option>
          <option value="patch_user">Modification utilisateur</option>
          <option value="change_role">Changement role</option>
          <option value="set_scopes">Modification scopes</option>
          <option value="soft_delete_user">Desactivation</option>
        </select>
        <select
          value={resourceFilter}
          onChange={(e) => {
            setResourceFilter(e.target.value);
            setPage(0);
          }}
          className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white"
        >
          <option value="">Tous les types</option>
          <option value="user">Utilisateur</option>
          <option value="organisation">Organisation</option>
          <option value="site">Site</option>
        </select>
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Filtrer localement..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="pl-8 pr-3 py-1.5 w-full border border-gray-200 rounded-lg text-xs"
          />
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        {loading ? (
          <div className="p-6 text-center text-gray-400">Chargement...</div>
        ) : filtered.length === 0 ? (
          <div className="p-6 text-center text-gray-400">
            {searchText || actionFilter || resourceFilter
              ? 'Aucun résultat pour ces filtres'
              : 'Aucun événement'}
          </div>
        ) : (
          filtered.map((e) => (
            <div key={e.id} className="hover:bg-gray-50/50 transition">
              <button
                onClick={() => setExpandedId(expandedId === e.id ? null : e.id)}
                className="w-full text-left px-4 py-3 flex items-start gap-4"
              >
                <div className="flex-shrink-0 mt-0.5">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${ACTION_COLORS[e.action] || 'bg-gray-100 text-gray-600'}`}
                  >
                    {ACTION_LABELS[e.action] || e.action}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700">
                    <span className="font-medium">{e.user_name || 'Systeme'}</span>
                    {e.resource_type && (
                      <span className="text-gray-400">
                        {' '}
                        sur <span className="font-mono text-gray-500">{e.resource_type}</span> #
                        {e.resource_id}
                      </span>
                    )}
                  </p>
                  {e.ip_address && (
                    <span className="text-[10px] text-gray-300 font-mono">{e.ip_address}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs text-gray-400">
                    {e.created_at
                      ? new Date(e.created_at).toLocaleString('fr-FR', {
                          dateStyle: 'short',
                          timeStyle: 'medium',
                        })
                      : ''}
                  </span>
                  {e.detail &&
                    (expandedId === e.id ? (
                      <ChevronUp size={14} className="text-gray-400" />
                    ) : (
                      <ChevronDown size={14} className="text-gray-300" />
                    ))}
                </div>
              </button>
              {expandedId === e.id && (
                <div className="px-4 pb-3">
                  <DetailPanel detail={e.detail} />
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
          >
            <ChevronLeft size={14} /> Precedent
          </button>
          <span className="text-sm text-gray-500">
            Page {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
          >
            Suivant <ChevronRight size={14} />
          </button>
        </div>
      )}
    </PageShell>
  );
}
