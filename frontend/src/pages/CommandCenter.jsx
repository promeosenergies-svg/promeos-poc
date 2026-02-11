/**
 * PROMEOS - Command Center (/)
 * 3 KPI cards + actions semaine + top anomalies
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, BadgeEuro, AlertTriangle, ArrowRight, Scan, Clock } from 'lucide-react';
import { Card, CardBody, Badge, Button, EmptyState, SkeletonCard } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { mockKpis, mockTodos, mockTopAnomalies } from '../mocks/kpis';

function KpiCard({ icon: Icon, title, value, sub, badge, badgeStatus, color }) {
  return (
    <Card>
      <CardBody className="flex items-start gap-4">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon size={22} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {sub && <p className="text-sm text-gray-500 mt-0.5">{sub}</p>}
        </div>
        {badge && <Badge status={badgeStatus}>{badge}</Badge>}
      </CardBody>
    </Card>
  );
}

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

export default function CommandCenter() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setData({ kpis: mockKpis, todos: mockTodos, anomalies: mockTopAnomalies });
      setLoading(false);
    }, 300);
    return () => clearTimeout(t);
  }, []);

  if (loading) {
    return (
      <div className="px-6 py-6">
        <div className="grid grid-cols-3 gap-4 mb-6">
          <SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      </div>
    );
  }

  const { kpis, todos, anomalies } = data;

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Command Center</h2>
          <p className="text-sm text-gray-500 mt-0.5">{kpis.conformite.total_sites} sites &middot; Derniere analyse: aujourd'hui</p>
        </div>
        <Button onClick={() => navigate('/compliance')}>
          <Scan size={16} />
          Lancer un scan
        </Button>
      </div>

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

      <div className="grid grid-cols-2 gap-6">
        {/* A faire cette semaine */}
        <Card>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">A faire cette semaine</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/action-plan')}>
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
    </div>
  );
}
