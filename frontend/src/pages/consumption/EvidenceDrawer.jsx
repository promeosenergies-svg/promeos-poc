/**
 * PROMEOS — EvidenceDrawer (Consumption Explorer)
 * Reusable drawer with 3 tabs: Preuve / Methode / Actions
 * Opened when user clicks a zone on Tunnel chart.
 * Uses shared Drawer component for accessibility (role=dialog, aria-modal, focus trap, ESC).
 */
import { useState } from 'react';
import { BarChart3, BookOpen, Zap } from 'lucide-react';
import { Badge, Button, TrustBadge } from '../../ui';
import Drawer from '../../ui/Drawer';

const TABS = [
  { key: 'evidence', label: 'Preuve', icon: BarChart3 },
  { key: 'method', label: 'Methode', icon: BookOpen },
  { key: 'actions', label: 'Actions', icon: Zap },
];

export default function EvidenceDrawer({ slot, tunnelData, onClose, onCreateAction }) {
  const [tab, setTab] = useState('evidence');

  if (!slot) return null;

  const { hour, dayType } = slot;
  const envelope = tunnelData?.envelope?.[dayType] || [];
  const point = envelope.find((s) => s.hour === hour) || {};
  const drawerTitle = `Analyse — ${hour}h (${dayType === 'weekday' ? 'Semaine' : 'Week-end'})`;

  return (
    <Drawer open={!!slot} onClose={onClose} title={drawerTitle}>
      <p className="text-xs text-gray-500 -mt-2 mb-3">
        {tunnelData?.readings_count?.toLocaleString('fr-FR')} releves • {tunnelData?.unit || 'kW'}
      </p>

      {/* Tabs */}
      <div className="flex border-b border-gray-100 -mx-6 px-6 mb-4">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition ${
                tab === t.key
                  ? 'text-blue-700 border-b-2 border-blue-500'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon size={14} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="space-y-4">
        {tab === 'evidence' && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">P10</p>
                <p className="text-lg font-bold text-gray-700">{point.p10 ?? '—'}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">P90</p>
                <p className="text-lg font-bold text-gray-700">{point.p90 ?? '—'}</p>
              </div>
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <p className="text-xs text-blue-600">Mediane (P50)</p>
                <p className="text-lg font-bold text-blue-700">{point.p50 ?? '—'}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-500">Echantillon</p>
                <p className="text-lg font-bold text-gray-700">{point.count ?? '—'}</p>
              </div>
            </div>
            <div className="bg-amber-50 rounded-lg p-3">
              <p className="text-xs font-medium text-amber-700">Bande normale</p>
              <p className="text-sm text-amber-800 mt-1">
                Entre {point.p10 ?? '—'} et {point.p90 ?? '—'} {tunnelData?.unit || 'kW'} —{' '}
                {point.count ?? 0} observations a cette heure.
              </p>
            </div>
          </>
        )}

        {tab === 'method' && (
          <div className="space-y-3">
            <div>
              <p className="text-xs font-semibold text-gray-600 uppercase mb-1">Methode</p>
              <p className="text-sm text-gray-700">
                Enveloppe quantile par creneau horaire. Les bandes P10-P90 definissent la plage de
                consommation "normale" basee sur {tunnelData?.days || 90} jours d'historique.
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-600 uppercase mb-1">Mode</p>
              <Badge status="info">
                {tunnelData?.mode === 'power' ? 'Puissance (kW)' : 'Energie (kWh)'}
              </Badge>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-600 uppercase mb-1">Confiance</p>
              <TrustBadge
                source={`${tunnelData?.sample_size || tunnelData?.readings_count || 0} points`}
                confidence={tunnelData?.confidence || 'low'}
              />
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-600 uppercase mb-1">Reference</p>
              <p className="text-sm text-gray-600">
                {tunnelData?.reference_band_method || 'percentile_hourly'}
              </p>
            </div>
          </div>
        )}

        {tab === 'actions' && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Si la consommation a {hour}h est regulierement hors bande, creez une action
              corrective.
            </p>
            <Button
              onClick={() =>
                onCreateAction?.({
                  sourceType: 'tunnel_anomaly',
                  hour,
                  dayType,
                  p10: point.p10,
                  p90: point.p90,
                  p50: point.p50,
                })
              }
              className="w-full"
            >
              <Zap size={14} className="mr-1.5" />
              Creer une action corrective
            </Button>
            <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-500 space-y-1">
              <p>Suggestions :</p>
              <ul className="list-disc list-inside space-y-0.5">
                <li>Vérifier la programmation CVC à {hour}h</li>
                <li>Comparer avec les horaires d'occupation</li>
                <li>Identifier les équipements actifs hors plage</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}
