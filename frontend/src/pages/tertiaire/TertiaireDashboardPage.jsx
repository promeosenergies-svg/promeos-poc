/**
 * PROMEOS V39 — Dashboard Tertiaire / OPERAT
 * Route: /conformite/tertiaire
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, AlertTriangle, CheckCircle2, FileText, Plus,
  Loader2, ArrowRight, ShieldAlert,
} from 'lucide-react';
import { PageShell, Card, CardBody, Button, Badge, KpiCard } from '../../ui';
import { getTertiaireDashboard, getTertiaireEfas } from '../../services/api';

const STATUS_LABELS = {
  active: 'Active',
  draft: 'Brouillon',
  closed: 'Fermée',
};

const STATUS_VARIANTS = {
  active: 'ok',
  draft: 'neutral',
  closed: 'neutral',
};

export default function TertiaireDashboardPage() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [efas, setEfas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getTertiaireDashboard().catch(() => null),
      getTertiaireEfas().catch(() => ({ efas: [] })),
    ]).then(([dash, efaData]) => {
      if (!cancelled) {
        setDashboard(dash);
        setEfas(efaData?.efas ?? []);
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <PageShell title="Décret tertiaire / OPERAT" subtitle="Chargement…">
        <div className="flex items-center justify-center gap-2 py-16 text-gray-400">
          <Loader2 size={20} className="animate-spin" />
          <span>Chargement…</span>
        </div>
      </PageShell>
    );
  }

  const kpis = dashboard || { total_efa: 0, active: 0, draft: 0, closed: 0, open_issues: 0, critical_issues: 0 };

  return (
    <PageShell
      title="Décret tertiaire / OPERAT"
      subtitle={`${kpis.total_efa} EFA enregistrée${kpis.total_efa > 1 ? 's' : ''}`}
    >
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="EFA actives"
          value={kpis.active}
          icon={Building2}
          accent="emerald"
        />
        <KpiCard
          label="EFA brouillon"
          value={kpis.draft}
          icon={FileText}
          accent="slate"
        />
        <KpiCard
          label="Anomalies ouvertes"
          value={kpis.open_issues}
          icon={AlertTriangle}
          accent={kpis.open_issues > 0 ? 'amber' : 'slate'}
          onClick={() => navigate('/conformite/tertiaire/anomalies')}
        />
        <KpiCard
          label="Issues critiques"
          value={kpis.critical_issues}
          icon={ShieldAlert}
          accent={kpis.critical_issues > 0 ? 'red' : 'slate'}
        />
      </div>

      {/* Actions rapides */}
      <div className="flex items-center gap-3 mt-6">
        <Button data-testid="btn-nouvelle-efa" onClick={() => navigate('/conformite/tertiaire/wizard')}>
          <Plus size={16} /> Nouvelle EFA
        </Button>
        <Button variant="secondary" onClick={() => navigate('/conformite/tertiaire/anomalies')}>
          Voir les anomalies <ArrowRight size={14} />
        </Button>
      </div>

      {/* Liste EFA */}
      <div className="mt-6 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Entités Fonctionnelles Assujetties
        </h3>
        {efas.length === 0 ? (
          <Card>
            <CardBody className="text-center py-8">
              <Building2 size={32} className="mx-auto text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">Aucune EFA enregistrée</p>
              <p className="text-xs text-gray-400 mt-1">
                Créez votre première EFA via l'assistant
              </p>
              <Button size="sm" className="mt-4" data-testid="btn-creer-efa-empty" onClick={() => navigate('/conformite/tertiaire/wizard')}>
                Créer une EFA
              </Button>
            </CardBody>
          </Card>
        ) : (
          <div className="space-y-2">
            {efas.map((efa) => (
              <button
                key={efa.id}
                onClick={() => navigate(`/conformite/tertiaire/efa/${efa.id}`)}
                className="w-full text-left rounded-lg border border-gray-200 bg-white p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <Building2 size={18} className="text-gray-400 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{efa.nom}</p>
                      <p className="text-xs text-gray-400">
                        {efa.role_assujetti ? `Rôle : ${efa.role_assujetti}` : ''}
                        {efa.reporting_start ? ` — Début : ${efa.reporting_start}` : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant={STATUS_VARIANTS[efa.statut] || 'neutral'} size="xs">
                      {STATUS_LABELS[efa.statut] || efa.statut}
                    </Badge>
                    <ArrowRight size={14} className="text-gray-400" />
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </PageShell>
  );
}
