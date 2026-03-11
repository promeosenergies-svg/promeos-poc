import { useState, useEffect } from 'react';
import { Users, Shield, Search, Eye, MapPin, Building2, ChevronUp, RefreshCw } from 'lucide-react';
import { getAdminUsers, getEffectiveAccess } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { PageShell, Button, EmptyState } from '../ui';
import { useToast } from '../ui/ToastProvider';

const ROLE_LABELS = {
  dg_owner: 'DG / Propriétaire',
  dsi_admin: 'DSI / Admin',
  daf: 'DAF',
  acheteur: 'Acheteur',
  resp_conformite: 'Resp. Conformité',
  energy_manager: 'Responsable Énergie',
  resp_immobilier: 'Resp. Immobilier',
  resp_site: 'Resp. Site',
  prestataire: 'Prestataire',
  auditeur: 'Auditeur',
  pmo_acc: 'PMO / ACC',
};

const ROLE_COLORS = {
  dg_owner: 'bg-purple-100 text-purple-700',
  dsi_admin: 'bg-blue-100 text-blue-700',
  daf: 'bg-green-100 text-green-700',
  acheteur: 'bg-orange-100 text-orange-700',
  resp_conformite: 'bg-red-100 text-red-700',
  energy_manager: 'bg-teal-100 text-teal-700',
  resp_immobilier: 'bg-amber-100 text-amber-700',
  resp_site: 'bg-cyan-100 text-cyan-700',
  prestataire: 'bg-gray-100 text-gray-700',
  auditeur: 'bg-indigo-100 text-indigo-700',
  pmo_acc: 'bg-pink-100 text-pink-700',
};

const SCOPE_LABELS = { org: 'Organisation', entite: 'Entité juridique', site: 'Site' };
const SCOPE_ICONS = { org: Building2, entite: Building2, site: MapPin };

function EffectiveAccessPanel({ userId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEffectiveAccess(userId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div className="p-4 text-sm text-gray-400">Chargement...</div>;
  if (!data)
    return <div className="p-4 text-sm text-red-500">Impossible de charger les accès.</div>;

  return (
    <div className="bg-blue-50/50 border-t border-blue-100 px-6 py-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-blue-800 flex items-center gap-1.5">
          <Eye size={14} /> Accès effectif
        </h4>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">
          Fermer
        </button>
      </div>

      {/* Scopes */}
      <div className="mb-3">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1">
          Scopes assignés
        </p>
        <div className="flex flex-wrap gap-1.5">
          {data.scopes?.length ? (
            data.scopes.map((s, i) => {
              const Icon = SCOPE_ICONS[s.level] || MapPin;
              return (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-blue-200 rounded-lg text-xs text-blue-700"
                >
                  <Icon size={12} />
                  {s.label}
                  {s.expires_at && (
                    <span className="text-orange-500 ml-1">
                      (exp: {new Date(s.expires_at).toLocaleDateString('fr-FR')})
                    </span>
                  )}
                </span>
              );
            })
          ) : (
            <span className="text-xs text-gray-400">Aucun scope</span>
          )}
        </div>
      </div>

      {/* Sites */}
      <div>
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1">
          Sites accessibles ({data.total_sites})
        </p>
        {data.sites?.length ? (
          <div className="flex flex-wrap gap-1">
            {data.sites.map((s) => (
              <span
                key={s.id}
                className="inline-block px-2 py-0.5 bg-white border border-gray-200 rounded text-[11px] text-gray-600"
              >
                {s.nom} <span className="text-gray-400">({s.type || '?'})</span>
              </span>
            ))}
          </div>
        ) : (
          <span className="text-xs text-red-400">Aucun site accessible</span>
        )}
      </div>

      {/* Permissions */}
      {data.permissions && (
        <div className="mt-3">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-1">
            Permissions
          </p>
          <div className="flex flex-wrap gap-1">
            {Object.entries(data.permissions).map(([k, v]) => {
              if (v === false || (Array.isArray(v) && v.length === 0)) return null;
              const label =
                v === true ? k : v === '__all__' ? `${k}: ALL` : `${k}: ${v.join(', ')}`;
              return (
                <span
                  key={k}
                  className="text-[10px] bg-green-50 text-green-700 px-1.5 py-0.5 rounded-full border border-green-200"
                >
                  {label}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedUser, setExpandedUser] = useState(null);
  const { hasPermission } = useAuth();
  const { toast } = useToast();

  const load = () => {
    setLoading(true);
    getAdminUsers()
      .then(setUsers)
      .catch(() => toast('Erreur lors du chargement des utilisateurs', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = users.filter((u) =>
    `${u.prenom} ${u.nom} ${u.email} ${u.role}`.toLowerCase().includes(search.toLowerCase())
  );

  if (!hasPermission('admin')) {
    return (
      <PageShell icon={Users} title="Utilisateurs">
        <EmptyState
          icon={Shield}
          title="Accès refusé"
          text="Vous n'avez pas les droits d'administration."
        />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={Users}
      title="Utilisateurs"
      subtitle={`${filtered.length} utilisateur${filtered.length > 1 ? 's' : ''} — Gestion des comptes, rôles et périmètres`}
      actions={
        <Button variant="secondary" onClick={load}>
          <RefreshCw size={14} className="mr-1.5" /> Actualiser
        </Button>
      }
    >
      {/* Admin summary */}
      {!loading && users.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Utilisateurs', value: users.length, color: 'text-blue-700 bg-blue-50' },
            {
              label: 'Rôles actifs',
              value: new Set(users.map((u) => u.role)).size,
              color: 'text-purple-700 bg-purple-50',
            },
            {
              label: 'Actifs ce mois',
              value: users.filter(
                (u) => u.last_login && new Date(u.last_login) > new Date(Date.now() - 30 * 86400000)
              ).length,
              color: 'text-green-700 bg-green-50',
            },
            {
              label: 'Sans connexion',
              value: users.filter((u) => !u.last_login).length,
              color: 'text-amber-700 bg-amber-50',
            },
          ].map((s) => (
            <div key={s.label} className={`rounded-lg px-4 py-3 ${s.color}`}>
              <p className="text-lg font-bold">{s.value}</p>
              <p className="text-xs opacity-80">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Search */}
      <div className="relative max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Rechercher par nom, email, rôle..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 pr-4 py-2 w-full border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
        />
      </div>

      {/* Users table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Utilisateur</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Role</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Scopes</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Statut</th>
              <th className="text-left px-4 py-3 font-medium text-gray-500">Dernière connexion</th>
              <th className="text-center px-4 py-3 font-medium text-gray-500">Accès</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  Chargement...
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  {search ? 'Aucun résultat pour cette recherche' : 'Aucun utilisateur'}
                </td>
              </tr>
            ) : (
              filtered.map((u) => (
                <tr key={u.id} className="group">
                  <td colSpan={7} className="p-0">
                    <div
                      className={`hover:bg-gray-50 transition ${expandedUser === u.id ? 'bg-blue-50/30' : ''}`}
                    >
                      <div className="flex items-center">
                        <div className="flex-1 grid grid-cols-7 items-center">
                          <div className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
                                {(u.prenom?.[0] || '').toUpperCase()}
                                {(u.nom?.[0] || '').toUpperCase()}
                              </div>
                              <span className="font-medium text-gray-900">
                                {u.prenom} {u.nom}
                              </span>
                            </div>
                          </div>
                          <div className="px-4 py-3 text-gray-600 truncate">{u.email}</div>
                          <div className="px-4 py-3">
                            <span
                              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ROLE_COLORS[u.role] || 'bg-gray-100 text-gray-700'}`}
                            >
                              {ROLE_LABELS[u.role] || u.role}
                            </span>
                          </div>
                          <div className="px-4 py-3 text-xs">
                            {u.scopes?.length ? (
                              u.scopes.map((s, i) => (
                                <span
                                  key={i}
                                  className="inline-flex items-center gap-0.5 bg-gray-100 rounded px-1.5 py-0.5 mr-1 text-gray-600"
                                >
                                  {s.label || `${SCOPE_LABELS[s.level] || s.level} #${s.id}`}
                                  {s.expires_at && <span className="text-orange-500">*</span>}
                                </span>
                              ))
                            ) : (
                              <span className="text-gray-300">-</span>
                            )}
                          </div>
                          <div className="px-4 py-3">
                            <span
                              className={`inline-flex items-center gap-1 text-xs font-medium ${u.actif ? 'text-green-600' : 'text-red-500'}`}
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${u.actif ? 'bg-green-500' : 'bg-red-400'}`}
                              />
                              {u.actif ? 'Actif' : 'Désactivé'}
                            </span>
                          </div>
                          <div className="px-4 py-3 text-xs text-gray-400">
                            {u.last_login
                              ? new Date(u.last_login).toLocaleDateString('fr-FR')
                              : 'Jamais'}
                          </div>
                          <div className="px-4 py-3 text-center">
                            <button
                              onClick={() => setExpandedUser(expandedUser === u.id ? null : u.id)}
                              className="p-1.5 rounded-lg hover:bg-blue-100 text-blue-600 transition"
                              title="Voir l'accès effectif"
                            >
                              {expandedUser === u.id ? <ChevronUp size={16} /> : <Eye size={16} />}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                    {expandedUser === u.id && (
                      <EffectiveAccessPanel userId={u.id} onClose={() => setExpandedUser(null)} />
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </PageShell>
  );
}
