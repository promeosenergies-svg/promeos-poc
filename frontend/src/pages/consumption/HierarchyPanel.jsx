/**
 * PROMEOS — HierarchyPanel (EMS Tier 1)
 * Arbre hiérarchique Org → Portefeuille → Site → Meter
 * avec badges conformité, conso annuelle et qualité données.
 */
import { useState, useEffect, useCallback as _useCallback } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Building2,
  FolderOpen,
  MapPin,
  Gauge,
  Loader2,
} from 'lucide-react';
import { getEmsHierarchy } from '../../services/api/ems';
import { useScope } from '../../contexts/ScopeContext';
import DataQualityBadge from '../../components/DataQualityBadge';
import { Badge } from '../../ui';

function fmtKwh(val) {
  if (val == null) return '—';
  if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)} GWh`;
  if (val >= 1_000) return `${(val / 1_000).toFixed(0)} MWh`;
  return `${Math.round(val)} kWh`;
}

function ComplianceBadge({ status }) {
  if (!status) return null;
  const map = {
    conforme: { label: 'Conforme', variant: 'success' },
    en_cours: { label: 'En cours', variant: 'info' },
    a_risque: { label: 'À risque', variant: 'warn' },
    non_conforme: { label: 'Non conforme', variant: 'error' },
  };
  const cfg = map[status] || map.a_risque;
  return <Badge status={cfg.variant}>{cfg.label}</Badge>;
}

function TreeNode({ label, icon: Icon, level = 0, defaultOpen = false, children, onClick, extra }) {
  const [open, setOpen] = useState(defaultOpen);
  const hasChildren = !!children;
  const Chevron = open ? ChevronDown : ChevronRight;

  return (
    <div>
      <button
        onClick={() => {
          if (hasChildren) setOpen((o) => !o);
          if (onClick) onClick();
        }}
        className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50 rounded-lg transition group ${
          level === 0
            ? 'font-semibold text-gray-900'
            : level === 1
              ? 'font-medium text-gray-800'
              : 'text-gray-700'
        }`}
        style={{ paddingLeft: `${level * 16 + 12}px` }}
      >
        {hasChildren ? (
          <Chevron size={14} className="text-gray-400 shrink-0" />
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        <Icon size={15} className="text-gray-400 shrink-0" />
        <span className="truncate flex-1">{label}</span>
        {extra && <span className="flex items-center gap-2 shrink-0">{extra}</span>}
      </button>
      {open && children && <div>{children}</div>}
    </div>
  );
}

export default function HierarchyPanel({ onSiteSelect, onMeterSelect }) {
  const { orgId } = useScope();
  const [hierarchy, setHierarchy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getEmsHierarchy(orgId)
      .then((data) => {
        if (!cancelled) setHierarchy(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Erreur chargement hiérarchie');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={20} className="animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-gray-500">Chargement hiérarchie...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!hierarchy?.portefeuilles?.length) {
    return (
      <div className="text-center py-8">
        <Building2 size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">Aucun portefeuille trouvé pour cette organisation.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-1">
      <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
        <Building2 size={16} className="text-blue-600" />
        Hiérarchie — {hierarchy.org_name || 'Organisation'}
      </h3>

      {hierarchy.portefeuilles.map((pf) => (
        <TreeNode
          key={pf.id}
          label={pf.nom}
          icon={FolderOpen}
          level={0}
          defaultOpen={hierarchy.portefeuilles.length <= 3}
        >
          {pf.sites?.map((site) => (
            <TreeNode
              key={site.id}
              label={site.nom}
              icon={MapPin}
              level={1}
              onClick={() => onSiteSelect?.(site.id)}
              extra={
                <>
                  <ComplianceBadge status={site.compliance_status} />
                  <span className="text-xs text-gray-500">{fmtKwh(site.annual_kwh)}</span>
                  {site.dq_score != null && <DataQualityBadge score={site.dq_score} size="sm" />}
                </>
              }
            >
              {site.meters?.map((meter) => (
                <TreeNode
                  key={meter.id}
                  label={`${meter.name} (${meter.meter_ref})`}
                  icon={Gauge}
                  level={2}
                  onClick={() => onMeterSelect?.(meter.id)}
                  extra={<span className="text-xs text-gray-400">{meter.energy_vector}</span>}
                />
              ))}
            </TreeNode>
          ))}
        </TreeNode>
      ))}
    </div>
  );
}
