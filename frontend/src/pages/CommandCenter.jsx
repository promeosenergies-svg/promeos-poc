/**
 * PROMEOS - Command Center (/) V4
 * PageShell + KpiCard + Expert Mode + Progress + useToast
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ShieldCheck, BadgeEuro, AlertTriangle, ArrowRight, Scan, Clock,
  Zap, Upload, CheckCircle2, Database, FileText, RefreshCw,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, SkeletonCard, TrustBadge, PageShell, KpiCard, Progress } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { useToast } from '../ui/ToastProvider';
import { mockKpis, mockTodos, mockTopAnomalies } from '../mocks/kpis';
import { mockObligations } from '../mocks/obligations';
import { mockActions } from '../mocks/actions';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';

const PRIORITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };

function TodoItem({ item }) {
  const priorityColors = {
    critical: 'border-red-400 bg-red-50',
    high: 'border-orange-400 bg-orange-50',
    medium: 'border-yellow-400 bg-yellow-50',
  };
  return (
    <div className={`flex items-center gap-3 px-4 py-3 border-l-4 rounded-r-lg ${priorityColors[item.priorite] || 'border-gray-300 bg-gray-50'}`}>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{item.texte}</p>
        <p className="text-xs text-gray-500 mt-0.5">{item.site}</p>
      </div>
      <div className="flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
        <Clock size={12} />
        {item.echeance}
      </div>
    </div>
  );
}

function RecommendedActionCard({ action, index, onClick }) {
  const bgColors = ['bg-blue-50 border-blue-200', 'bg-amber-50 border-amber-200', 'bg-green-50 border-green-200'];
  const numColors = ['bg-blue-600', 'bg-amber-600', 'bg-green-600'];
  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer hover:shadow-sm transition ${bgColors[index] || bgColors[0]}`}
      onClick={onClick}
    >
      <div className={`w-6 h-6 rounded-full ${numColors[index] || numColors[0]} text-white flex items-center justify-center text-xs font-bold shrink-0`}>
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 truncate">{action.titre}</p>
        <p className="text-xs text-gray-600 mt-0.5">{action.source_label}</p>
        <div className="flex items-center gap-2 mt-2">
          {action.impact_eur > 0 && (
            <span className="text-xs font-medium text-red-700 bg-red-50 px-2 py-0.5 rounded">
              {action.impact_eur.toLocaleString()} EUR
            </span>
          )}
          <Badge status={action.priorite === 'critical' ? 'crit' : action.priorite === 'high' ? 'warn' : 'info'}>
            {action.priorite}
          </Badge>
        </div>
      </div>
      <ArrowRight size={16} className="text-gray-400 mt-1 shrink-0" />
    </div>
  );
}

export default function CommandCenter() {
  const navigate = useNavigate();
  const { org, scopedSites } = useScope();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setData({ kpis: mockKpis, todos: mockTodos, anomalies: mockTopAnomalies });
      setLoading(false);
    }, 300);
    return () => clearTimeout(t);
  }, []);

  const top3Actions = useMemo(() => {
    const fromObligations = mockObligations
      .filter(o => o.statut !== 'conforme')
      .map(o => ({
        id: `obl-${o.id}`,
        titre: `${o.regulation}: ${o.description}`,
        source_label: `Conformite — ${o.sites_concernes - o.sites_conformes} sites non conformes`,
        impact_eur: o.impact_eur,
        priorite: o.severity,
        route: '/conformite',
      }));

    const fromActions = mockActions
      .filter(a => a.statut !== 'done')
      .slice(0, 5)
      .map(a => ({
        id: `act-${a.id}`,
        titre: a.titre,
        source_label: `Plan d'action — ${a.site_nom}`,
        impact_eur: a.impact_eur,
        priorite: a.priorite,
        route: '/actions',
      }));

    return [...fromObligations, ...fromActions]
      .sort((a, b) => (PRIORITY_RANK[b.priorite] || 0) - (PRIORITY_RANK[a.priorite] || 0) || b.impact_eur - a.impact_eur)
      .slice(0, 3);
  }, []);

  const hasSites = scopedSites.length > 0;

  const handleSync = () => {
    toast('Synchronisation des donnees en cours...', 'info');
    setTimeout(() => toast('Donnees synchronisees', 'success'), 1500);
  };

  if (loading) {
    return (
      <PageShell icon={LayoutDashboard} title="Tableau de bord" subtitle="Chargement...">
        <div className="grid grid-cols-3 gap-4">
          <SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      </PageShell>
    );
  }

  const { kpis, todos, anomalies } = data;

  return (
    <PageShell
      icon={LayoutDashboard}
      title="Tableau de bord"
      subtitle={`Synthese 2 minutes : conformite, pertes, actions — ${org.nom} · ${scopedSites.length} sites`}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={() => navigate('/cockpit-2min')}>
            <FileText size={14} /> Briefing 2 min
          </Button>
          {isExpert && (
            <Button variant="secondary" size="sm" onClick={handleSync}>
              <RefreshCw size={14} /> Sync donnees
            </Button>
          )}
          {!hasSites ? (
            <Button onClick={() => navigate('/import')}>
              <Upload size={16} /> Importer mes sites
            </Button>
          ) : (
            <Button onClick={() => navigate('/conformite')}>
              <Scan size={16} /> Lancer un scan
            </Button>
          )}
        </>
      }
    >
      {/* 3 KPI cards */}
      <div className="grid grid-cols-3 gap-4">
        <KpiCard
          icon={ShieldCheck}
          title="Conformite"
          value={`${kpis.conformite.pct_conforme}%`}
          sub={`${kpis.conformite.conformes} conformes / ${kpis.conformite.total_sites}`}
          badge={kpis.conformite.label}
          badgeStatus={kpis.conformite.color}
          color="bg-blue-600"
        />
        <KpiCard
          icon={BadgeEuro}
          title="Risque financier"
          value={`${(kpis.risque_financier.total_eur / 1000).toFixed(0)}k EUR`}
          sub={`dont ${(kpis.risque_financier.pertes_conso_eur / 1000).toFixed(0)}k pertes conso`}
          badge={kpis.risque_financier.total_eur > 20000 ? 'Eleve' : 'Modere'}
          badgeStatus={kpis.risque_financier.total_eur > 20000 ? 'crit' : 'warn'}
          color="bg-red-600"
        />
        <KpiCard
          icon={AlertTriangle}
          title="Action prioritaire"
          value={kpis.action_prioritaire.texte}
          sub={`${kpis.action_prioritaire.nb_sites} sites concernes`}
          badge={kpis.action_prioritaire.priorite}
          badgeStatus={kpis.action_prioritaire.priorite === 'critical' ? 'crit' : 'warn'}
          color="bg-amber-600"
        />
      </div>

      {/* Data freshness + coverage */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-2.5 rounded-lg bg-green-50">
              <CheckCircle2 size={20} className="text-green-600" />
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-500 font-medium uppercase">Derniere mise a jour</p>
              <p className="text-sm font-semibold text-gray-900 mt-0.5">
                {new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}
              </p>
              <TrustBadge source="PROMEOS" period="temps reel" confidence="high" className="mt-1" />
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="p-2.5 rounded-lg bg-indigo-50">
              <Database size={20} className="text-indigo-600" />
            </div>
            <div className="flex-1">
              <p className="text-xs text-gray-500 font-medium uppercase">Couverture donnees</p>
              <Progress value={72} color="blue" size={isExpert ? 'md' : 'sm'} label={isExpert ? 'Sites avec compteurs actifs' : undefined} className="mt-2" />
              <p className="text-xs text-gray-400 mt-1">{scopedSites.length} sites dans le perimetre</p>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Top 3 recommended actions */}
      <Card>
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={18} className="text-blue-600" />
            <h3 className="font-semibold text-gray-800">Top 3 actions recommandees</h3>
          </div>
          <Button variant="ghost" size="sm" onClick={() => navigate('/actions')}>
            Voir toutes <ArrowRight size={14} />
          </Button>
        </div>
        <div className="p-4 grid grid-cols-3 gap-3">
          {top3Actions.map((a, i) => (
            <RecommendedActionCard key={a.id} action={a} index={i} onClick={() => navigate(a.route)} />
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-6">
        {/* A faire cette semaine */}
        <Card>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">A faire cette semaine</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/actions')}>
              Voir tout <ArrowRight size={14} />
            </Button>
          </div>
          <div className="p-3 space-y-2">
            {todos.map((t) => <TodoItem key={t.id} item={t} />)}
          </div>
        </Card>

        {/* Top anomalies */}
        <Card>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Top anomalies</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/diagnostic-conso')}>
              Voir tout <ArrowRight size={14} />
            </Button>
          </div>
          <Table>
            <Thead>
              <tr>
                <Th>Site</Th>
                <Th>Type</Th>
                <Th>Severite</Th>
                <Th className="text-right">Perte EUR</Th>
              </tr>
            </Thead>
            <Tbody>
              {anomalies.slice(0, 8).map((a) => (
                <Tr key={a.id} onClick={() => navigate(`/sites/${a.site_id}`)}>
                  <Td className="font-medium">{a.site_nom}</Td>
                  <Td>
                    <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">{a.type}</span>
                  </Td>
                  <Td><Badge status={a.severity === 'critical' ? 'crit' : a.severity === 'high' ? 'warn' : 'info'}>{a.severity}</Badge></Td>
                  <Td className="text-right text-red-600 font-medium">{a.perte_eur.toLocaleString()} EUR</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Card>
      </div>
    </PageShell>
  );
}
