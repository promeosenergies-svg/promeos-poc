/**
 * PROMEOS - Admin Roles Page
 * Shows system roles with permissions matrix.
 */
import { useState, useEffect } from 'react';
import { Shield, Check, X } from 'lucide-react';
import { getAdminRoles } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { PageShell, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
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
  pmo_acc: 'PMO / Acc.',
};

const ROLE_COLORS = {
  dg_owner: 'bg-purple-100 text-purple-700',
  dsi_admin: 'bg-red-100 text-red-700',
  daf: 'bg-blue-100 text-blue-700',
  acheteur: 'bg-green-100 text-green-700',
  resp_conformite: 'bg-yellow-100 text-yellow-700',
  energy_manager: 'bg-teal-100 text-teal-700',
  resp_immobilier: 'bg-orange-100 text-orange-700',
  resp_site: 'bg-pink-100 text-pink-700',
  prestataire: 'bg-gray-100 text-gray-700',
  auditeur: 'bg-indigo-100 text-indigo-700',
  pmo_acc: 'bg-cyan-100 text-cyan-700',
};

const PERM_LABELS = {
  view: 'Voir',
  edit: 'Modifier',
  admin: 'Admin',
  export: 'Export',
  sync: 'Sync',
  approve: 'Approuver',
};

function PermCell({ value }) {
  if (value === true) {
    return <Check size={16} className="text-green-600 mx-auto" />;
  }
  if (value === false) {
    return <X size={16} className="text-gray-300 mx-auto" />;
  }
  if (value === '__all__') {
    return (
      <span className="text-xs font-semibold text-green-700 bg-green-50 px-1.5 py-0.5 rounded">
        ALL
      </span>
    );
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <X size={16} className="text-gray-300 mx-auto" />;
    return (
      <div className="flex flex-wrap gap-0.5 justify-center">
        {value.map((m) => (
          <span key={m} className="text-[9px] bg-blue-50 text-blue-600 px-1 py-0.5 rounded">
            {m}
          </span>
        ))}
      </div>
    );
  }
  return <span className="text-gray-400">—</span>;
}

export default function AdminRolesPage() {
  const { hasPermission } = useAuth();
  const { toast } = useToast();
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAdminRoles()
      .then(setRoles)
      .catch(() => toast('Erreur lors du chargement des roles', 'error'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!hasPermission('admin')) {
    return (
      <PageShell icon={Shield} title="Rôles & Permissions">
        <EmptyState
          icon={Shield}
          title="Accès refusé"
          text="Vous n'avez pas les droits d'administration."
        />
      </PageShell>
    );
  }

  if (loading) {
    return (
      <PageShell icon={Shield} title="Rôles & Permissions" subtitle="Chargement...">
        <SkeletonCard />
      </PageShell>
    );
  }

  const permKeys = ['view', 'edit', 'admin', 'export', 'sync', 'approve'];

  return (
    <PageShell
      icon={Shield}
      title="Rôles & Permissions"
      subtitle="11 rôles système — lecture seule (non-modifiables)"
    >
      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-semibold text-gray-600 sticky left-0 bg-gray-50">
                Role
              </th>
              {permKeys.map((k) => (
                <th
                  key={k}
                  className="text-center px-3 py-3 font-semibold text-gray-600 min-w-[100px]"
                >
                  {PERM_LABELS[k]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.role} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 sticky left-0 bg-white">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${ROLE_COLORS[r.role] || 'bg-gray-100 text-gray-700'}`}
                  >
                    {ROLE_LABELS[r.role] || r.role}
                  </span>
                </td>
                {permKeys.map((k) => (
                  <td key={k} className="px-3 py-3 text-center">
                    <PermCell value={r.permissions[k]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-gray-400">
        Les rôles système sont fixes et ne peuvent pas être modifiés. Le périmètre d'accès (scope)
        est configuré par utilisateur via les Assignments.
      </p>
    </PageShell>
  );
}
