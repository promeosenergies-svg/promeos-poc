/**
 * PROMEOS — TunnelPanel (extracted from ConsumptionExplorerPage)
 * P10-P90 envelope chart with day-type selector, kWh/kW toggle,
 * composable layers (TunnelLayer, SignatureLayer), and EvidenceDrawer.
 */
import { useState, useCallback, useEffect } from 'react';
import { Activity, RefreshCw } from 'lucide-react';
import { Card, CardBody, Button, EmptyState, TrustBadge } from '../../ui';
import { SkeletonCard } from '../../ui';
import { track } from '../../services/tracker';
import { getConsumptionTunnelV2 } from '../../services/api';
import ExplorerChart from './ExplorerChart';
import LayerToggle from './LayerToggle';
import TunnelLayer from './layers/TunnelLayer';
import SignatureLayer from './layers/SignatureLayer';
import EvidenceDrawer from './EvidenceDrawer';
import { CONFIDENCE_BADGE } from './constants';

export default function TunnelPanel({
  siteId,
  days,
  energyType,
  showSignature = false,
  toast,
  initialTunnel,
}) {
  const [tunnel, setTunnel] = useState(initialTunnel || null);
  const [loading, setLoading] = useState(false);
  const [dayType, setDayType] = useState('weekday');
  const [mode, setMode] = useState('energy');
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [showP10P90, setShowP10P90] = useState(true);
  const [showP25P75, setShowP25P75] = useState(true);

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const data = await getConsumptionTunnelV2(siteId, days, energyType, mode);
      setTunnel(data);
      track('tunnel_loaded', { site_id: siteId, days, energy_type: energyType, mode });
    } catch (e) {
      toast?.('Erreur chargement tunnel', 'error');
    } finally {
      setLoading(false);
    }
  }, [siteId, days, energyType, mode, toast]);

  // Only fetch if no initial data OR mode changed from default 'energy'
  useEffect(() => {
    if (mode !== 'energy' || !initialTunnel) load();
  }, [load, mode, initialTunnel]);

  if (loading) return <SkeletonCard rows={6} />;
  if (!tunnel || tunnel.readings_count === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="Aucune donnee de consommation"
        text="Importez des relevés ou générez des données démo pour voir l'enveloppe tunnel."
      />
    );
  }

  const conf = CONFIDENCE_BADGE[tunnel.confidence] || CONFIDENCE_BADGE.low;
  const envelope = tunnel.envelope?.[dayType] || [];
  const chartData = envelope.map((s) => ({
    hour: `${s.hour}h`,
    hourNum: s.hour,
    p10: s.p10,
    p25: s.p25,
    p50: s.p50,
    p75: s.p75,
    p90: s.p90,
  }));

  const handleChartClick = (data) => {
    if (data?.activePayload?.[0]?.payload) {
      const point = data.activePayload[0].payload;
      setSelectedSlot({ hour: point.hourNum, dayType });
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-800">Enveloppe de consommation</h3>
          <TrustBadge level={conf.variant} label={`Confiance ${conf.label}`} size="sm" />
        </div>
        <Button size="sm" variant="ghost" onClick={load}>
          <RefreshCw size={14} />
        </Button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Releves</p>
            <p className="text-xl font-bold text-gray-800">
              {tunnel.readings_count.toLocaleString()}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">% hors bande</p>
            <p
              className={`text-xl font-bold ${tunnel.outside_pct > 15 ? 'text-red-600' : tunnel.outside_pct > 5 ? 'text-amber-600' : 'text-green-600'}`}
            >
              {tunnel.outside_pct}%
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="py-3 px-4 text-center">
            <p className="text-xs text-gray-500">Hors bande (7j)</p>
            <p className="text-xl font-bold text-gray-800">
              {tunnel.outside_count}/{tunnel.total_evaluated}
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Mode toggle (kWh / kW) + Day type selector */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-2">
          <button
            className={`px-3 py-1 rounded-full text-sm font-medium transition ${dayType === 'weekday' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            onClick={() => setDayType('weekday')}
          >
            Semaine
          </button>
          <button
            className={`px-3 py-1 rounded-full text-sm font-medium transition ${dayType === 'weekend' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            onClick={() => setDayType('weekend')}
          >
            Week-end
          </button>
        </div>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setMode('energy')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition ${mode === 'energy' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
          >
            kWh
          </button>
          <button
            onClick={() => setMode('power')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition ${mode === 'power' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}
          >
            kW
          </button>
        </div>
      </div>

      {/* Tunnel chart + LayerToggle sidebar */}
      <Card>
        <CardBody>
          <div className="flex gap-4">
            <div className="flex-1 min-w-0">
              <ExplorerChart
                data={chartData}
                xKey="hour"
                valueKey="p50"
                mode="agrege"
                unit={mode === 'power' ? 'kw' : 'kwh'}
                height={300}
                onSlotClick={handleChartClick}
                summaryData={{
                  points: chartData.length,
                  series: 1,
                  meters: tunnel.meters_count,
                  source: tunnel.source,
                  quality: tunnel.readings_count
                    ? Math.round(Math.min(100, (tunnel.readings_count / 500) * 100))
                    : null,
                }}
              >
                <TunnelLayer visible={showP10P90} opacity={showP25P75 ? 0.2 : 0.3} />
                <SignatureLayer visible={showSignature} />
              </ExplorerChart>
              <p className="text-xs text-gray-400 mt-1 text-center">
                Cliquez sur un creneau pour ouvrir l'analyse detaillee
              </p>
            </div>
            <LayerToggle
              layers={{ tunnel: showP10P90, talon: showP25P75, signature: showSignature }}
              onToggle={(key) => {
                if (key === 'tunnel') setShowP10P90((v) => !v);
                if (key === 'talon') setShowP25P75((v) => !v);
              }}
            />
          </div>
        </CardBody>
      </Card>

      {/* Evidence drawer */}
      {selectedSlot && (
        <EvidenceDrawer
          slot={selectedSlot}
          tunnelData={tunnel}
          onClose={() => setSelectedSlot(null)}
          onCreateAction={(ctx) => {
            track('evidence_action', ctx);
            setSelectedSlot(null);
          }}
        />
      )}
    </div>
  );
}
