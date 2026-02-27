/**
 * PROMEOS — Consumption Context V0
 * Usages & Horaires → Profil conso & Anomalies comportementales.
 * 2 tabs: "Profil & Heatmap" | "Horaires & Anomalies"
 */
import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Activity, RefreshCw } from 'lucide-react';
import {
  getConsumptionContext,
  refreshConsumptionDiagnose,
} from '../services/api';
import { useScope } from '../contexts/ScopeContext';
import { PageShell, KpiCard, Tabs, Card, CardBody, EmptyState, Badge, Button } from '../ui';
import { useToast } from '../ui/ToastProvider';
import ProfileHeatmapTab from './consumption/ProfileHeatmapTab';
import HorairesAnomaliesTab from './consumption/HorairesAnomaliesTab';

const TABS = [
  { id: 'profile', label: 'Profil & Heatmap' },
  { id: 'horaires', label: 'Horaires & Anomalies' },
];

function scoreBadge(score) {
  if (score >= 80) return 'success';
  if (score >= 50) return 'warn';
  return 'crit';
}

export default function ConsumptionContextPage() {
  const { activeSite } = useScope();
  const siteId = activeSite?.id;
  const [sp, setSp] = useSearchParams();
  const tabParam = sp.get('tab') || 'profile';

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { toast } = useToast();

  const load = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    try {
      const ctx = await getConsumptionContext(siteId, 30);
      setData(ctx);
    } catch (err) {
      toast('Erreur chargement contexte consommation', 'error');
    } finally {
      setLoading(false);
    }
  }, [siteId, toast]);

  useEffect(() => { load(); }, [load]);

  const handleRefresh = async () => {
    if (!siteId) return;
    setRefreshing(true);
    try {
      await refreshConsumptionDiagnose(siteId, 30);
      await load();
      toast('Diagnostic recalculé', 'success');
    } catch {
      toast('Erreur recalcul', 'error');
    } finally {
      setRefreshing(false);
    }
  };

  const score = data?.anomalies?.behavior_score ?? null;
  const kpis = data?.anomalies?.kpis ?? {};
  const profileData = data?.profile ?? {};
  const activityData = data?.activity ?? {};
  const anomalyData = data?.anomalies ?? {};

  if (!siteId) {
    return (
      <PageShell icon={Activity} title="Usages & Horaires" subtitle="Profil conso · Anomalies comportementales">
        <EmptyState title="Aucun site sélectionné" message="Sélectionnez un site pour voir le contexte de consommation." />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={Activity}
      title="Usages & Horaires"
      subtitle="Profil conso · Anomalies comportementales"
      actions={
        <Button size="sm" variant="outline" onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
          Recalculer
        </Button>
      }
    >
      {/* KPI Row */}
      {score !== null && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <KpiCard
            label="Score Comportement"
            value={score}
            suffix="/100"
            badge={<Badge variant={scoreBadge(score)}>{score >= 80 ? 'Bon' : score >= 50 ? 'Moyen' : 'Mauvais'}</Badge>}
          />
          <KpiCard label="Hors horaires" value={`${kpis.offhours_pct ?? 0}%`} detail="Conso hors plages ouverture" />
          <KpiCard label="Talon" value={`${profileData.baseload_kw ?? 0} kW`} detail="Puissance minimale (Q10 nuit)" />
          <KpiCard label="Dérive" value={`${kpis.drift_pct ?? 0}%`} detail="Tendance sur la période" />
        </div>
      )}

      {/* Tabs */}
      <Tabs
        tabs={TABS}
        activeTab={tabParam}
        onChange={(t) => setSp({ tab: t }, { replace: true })}
      />

      <div className="mt-4">
        {loading ? (
          <Card><CardBody><div className="animate-pulse h-64 bg-gray-100 rounded" /></CardBody></Card>
        ) : tabParam === 'profile' ? (
          <ProfileHeatmapTab profile={profileData} loading={loading} />
        ) : (
          <HorairesAnomaliesTab
            activity={activityData}
            anomalies={anomalyData}
            siteId={siteId}
            loading={loading}
          />
        )}
      </div>
    </PageShell>
  );
}
