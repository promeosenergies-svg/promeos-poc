/**
 * PROMEOS - Admin Assignments Page
 * Wizard Express: user → scope → role → recap effective permissions → confirm.
 * Matrix view: Users × Scopes → Roles.
 */
import { useState, useEffect } from 'react';
import {
  Users,
  Shield,
  Building2,
  MapPin,
  ChevronRight,
  Check,
  Search,
  RefreshCw,
} from 'lucide-react';
import { getAdminUsers, getAdminRoles, setAdminScopes, changeAdminRole } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { PageShell, Button, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { useToast } from '../ui/ToastProvider';

const ROLE_LABELS = {
  dg_owner: 'DG / Owner',
  dsi_admin: 'DSI / Admin',
  daf: 'DAF',
  acheteur: 'Acheteur',
  resp_conformite: 'Resp. Conformité',
  energy_manager: 'Energy Manager',
  resp_immobilier: 'Resp. Immobilier',
  resp_site: 'Resp. Site',
  prestataire: 'Prestataire',
  auditeur: 'Auditeur',
  pmo_acc: 'PMO / Acc.',
};

const SCOPE_LABELS = { org: 'Organisation', entite: 'Entite', site: 'Site' };

function WizardExpress({ users, roles, onDone }) {
  const { toast } = useToast();
  const [step, setStep] = useState(1);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedScopeLevel, setSelectedScopeLevel] = useState('org');
  const [selectedScopeId, setSelectedScopeId] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [saving, setSaving] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredUsers = users.filter((u) =>
    `${u.prenom} ${u.nom} ${u.email}`.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const effectivePerms = roles.find((r) => r.role === selectedRole)?.permissions;

  const handleConfirm = async () => {
    if (!selectedUser || !selectedRole) return;
    setSaving(true);
    try {
      // Update role
      await changeAdminRole(selectedUser.id, selectedRole);
      // Update scopes
      await setAdminScopes(selectedUser.id, [
        {
          level: selectedScopeLevel,
          id: parseInt(selectedScopeId) || 1,
        },
      ]);
      onDone();
    } catch (err) {
      toast('Erreur: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
        <Shield size={20} className="text-blue-600" />
        Wizard Express — Assigner un rôle
      </h2>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6 text-sm">
        {['Utilisateur', 'Périmètre', 'Rôle', 'Confirmer'].map((label, i) => (
          <div key={label} className="flex items-center gap-1">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
              ${step > i + 1 ? 'bg-green-100 text-green-700' : step === i + 1 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'}`}
            >
              {step > i + 1 ? <Check size={12} /> : i + 1}
            </div>
            <span className={step === i + 1 ? 'text-gray-800 font-medium' : 'text-gray-400'}>
              {label}
            </span>
            {i < 3 && <ChevronRight size={14} className="text-gray-300" />}
          </div>
        ))}
      </div>

      {/* Step 1: Select user */}
      {step === 1 && (
        <div>
          <div className="relative mb-3">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher un utilisateur..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 w-full border border-gray-200 rounded-lg text-sm"
            />
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {filteredUsers.map((u) => (
              <button
                key={u.id}
                onClick={() => {
                  setSelectedUser(u);
                  setStep(2);
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-blue-50 transition
                  ${selectedUser?.id === u.id ? 'bg-blue-50 border border-blue-200' : 'border border-transparent'}`}
              >
                <span className="font-medium">
                  {u.prenom} {u.nom}
                </span>
                <span className="text-gray-400 ml-2">{u.email}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: Select scope */}
      {step === 2 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">
            Périmètre d'accès pour{' '}
            <strong>
              {selectedUser?.prenom} {selectedUser?.nom}
            </strong>
          </p>
          <div className="flex gap-2">
            {['org', 'entite', 'site'].map((level) => (
              <button
                key={level}
                onClick={() => setSelectedScopeLevel(level)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm border transition
                  ${selectedScopeLevel === level ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}
              >
                {level === 'org' && <Building2 size={16} />}
                {level === 'entite' && <Building2 size={16} />}
                {level === 'site' && <MapPin size={16} />}
                {SCOPE_LABELS[level]}
              </button>
            ))}
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">
              ID du {SCOPE_LABELS[selectedScopeLevel]}
            </label>
            <input
              type="number"
              value={selectedScopeId}
              onChange={(e) => setSelectedScopeId(e.target.value)}
              placeholder="Ex: 1"
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm w-32"
            />
          </div>
          <button
            onClick={() => setStep(3)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm"
          >
            Suivant
          </button>
        </div>
      )}

      {/* Step 3: Select role */}
      {step === 3 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">
            Role pour{' '}
            <strong>
              {selectedUser?.prenom} {selectedUser?.nom}
            </strong>
          </p>
          <div className="grid grid-cols-2 gap-2">
            {roles.map((r) => (
              <button
                key={r.role}
                onClick={() => setSelectedRole(r.role)}
                className={`text-left px-3 py-2 rounded-lg text-sm border transition
                  ${selectedRole === r.role ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}`}
              >
                <span className="font-medium">{ROLE_LABELS[r.role] || r.role}</span>
              </button>
            ))}
          </div>
          <button
            onClick={() => setStep(4)}
            disabled={!selectedRole}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-40"
          >
            Suivant
          </button>
        </div>
      )}

      {/* Step 4: Recap + Confirm */}
      {step === 4 && (
        <div className="space-y-4">
          <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
            <div>
              <span className="text-gray-500">Utilisateur:</span>{' '}
              <strong>
                {selectedUser?.prenom} {selectedUser?.nom}
              </strong>{' '}
              ({selectedUser?.email})
            </div>
            <div>
              <span className="text-gray-500">Scope:</span>{' '}
              <strong>{SCOPE_LABELS[selectedScopeLevel]}</strong> #{selectedScopeId || '1'}
            </div>
            <div>
              <span className="text-gray-500">Role:</span>{' '}
              <strong>{ROLE_LABELS[selectedRole] || selectedRole}</strong>
            </div>
          </div>

          {effectivePerms && (
            <div>
              <p className="text-xs text-gray-500 font-semibold mb-2">Permissions effectives:</p>
              <div className="flex flex-wrap gap-1">
                {Object.entries(effectivePerms).map(([k, v]) => {
                  if (v === false || (Array.isArray(v) && v.length === 0)) return null;
                  const label =
                    v === true ? k : v === '__all__' ? `${k}: ALL` : `${k}: ${v.join(', ')}`;
                  return (
                    <span
                      key={k}
                      className="text-[10px] bg-green-50 text-green-700 px-1.5 py-0.5 rounded-full"
                    >
                      {label}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => setStep(1)}
              className="px-4 py-2 border border-gray-200 rounded-lg text-sm"
            >
              Annuler
            </button>
            <button
              onClick={handleConfirm}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50"
            >
              {saving ? 'Enregistrement...' : 'Confirmer'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MatrixView({ users, roles: _roles }) {
  const [search, setSearch] = useState('');

  const filtered = users.filter((u) =>
    `${u.prenom} ${u.nom} ${u.email}`.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-3">
        <h3 className="text-sm font-semibold text-gray-700">Matrice Users x Scopes x Roles</h3>
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Rechercher..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 w-full border border-gray-200 rounded-lg text-xs"
          />
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-2 font-semibold text-gray-600">Utilisateur</th>
              <th className="text-left px-3 py-2 font-semibold text-gray-600">Email</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-600">Role</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-600">Scopes</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-600">Statut</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-700">
                  {u.prenom} {u.nom}
                </td>
                <td className="px-3 py-2 text-gray-500">{u.email}</td>
                <td className="px-3 py-2 text-center">
                  <span className="inline-block px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded-full text-[10px] font-semibold">
                    {ROLE_LABELS[u.role] || u.role || '—'}
                  </span>
                </td>
                <td className="px-3 py-2 text-center">
                  {u.scopes && u.scopes.length > 0 ? (
                    <div className="flex flex-wrap gap-0.5 justify-center">
                      {u.scopes.map((s, i) => (
                        <span key={i} className="text-[9px] bg-gray-100 text-gray-600 px-1 rounded">
                          {s.level}#{s.id}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${u.actif ? 'bg-green-500' : 'bg-red-400'}`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function AdminAssignmentsPage() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('wizard');

  const load = () => {
    setLoading(true);
    Promise.all([getAdminUsers(), getAdminRoles()])
      .then(([u, r]) => {
        setUsers(u);
        setRoles(r);
      })
      .catch(() => toast('Erreur lors du chargement des données', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!hasPermission('admin')) {
    return (
      <PageShell icon={Users} title="Affectations">
        <EmptyState
          icon={Shield}
          title="Acces refuse"
          text="Vous n'avez pas les droits d'administration."
        />
      </PageShell>
    );
  }

  if (loading) {
    return (
      <PageShell icon={Users} title="Affectations" subtitle="Chargement...">
        <SkeletonCard />
        <SkeletonCard />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={Users}
      title="Affectations"
      subtitle={`${users.length} utilisateurs configures`}
      actions={
        <Button variant="secondary" onClick={load}>
          <RefreshCw size={14} className="mr-1.5" /> Actualiser
        </Button>
      }
    >
      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab('wizard')}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition
            ${tab === 'wizard' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
        >
          Wizard Express
        </button>
        <button
          onClick={() => setTab('matrix')}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition
            ${tab === 'matrix' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
        >
          Matrice
        </button>
      </div>

      {tab === 'wizard' && <WizardExpress users={users} roles={roles} onDone={load} />}
      {tab === 'matrix' && <MatrixView users={users} roles={roles} />}
    </PageShell>
  );
}
