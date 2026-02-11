/**
 * PROMEOS - Site 360 (/sites/:siteId)
 * Header + badges + 3 mini KPIs + tabs (Resume, Conso, Factures, Conformite, Actions)
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, ShieldCheck, Zap, BadgeEuro, AlertTriangle,
  FileText, ListChecks, MapPin, Ruler,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, Tabs, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { getMockSite } from '../mocks/sites';

const STATUT_BADGE = {
  conforme: { status: 'ok', label: 'Conforme' },
  non_conforme: { status: 'crit', label: 'Non conforme' },
  a_risque: { status: 'warn', label: 'A risque' },
  a_evaluer: { status: 'neutral', label: 'A evaluer' },
};

const TABS = [
  { id: 'resume', label: 'Resume' },
  { id: 'conso', label: 'Consommation' },
  { id: 'factures', label: 'Factures' },
  { id: 'conformite', label: 'Conformite' },
  { id: 'actions', label: 'Actions' },
];

function MiniKpi({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-lg">
      <Icon size={18} className={color} />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm font-bold text-gray-800">{value}</p>
      </div>
    </div>
  );
}

function TabResume({ site }) {
  const mockAnomalies = [
    { id: 1, type: 'hors_horaires', severity: 'critical', message: `58% consommation hors horaires`, perte_eur: Math.round(site.risque_eur * 0.4) },
    { id: 2, type: 'base_load', severity: 'high', message: 'Talon eleve: 45% de la mediane', perte_eur: Math.round(site.risque_eur * 0.2) },
    { id: 3, type: 'derive', severity: 'medium', message: 'Derive +8% sur 30 jours', perte_eur: Math.round(site.risque_eur * 0.1) },
  ];

  return (
    <div className="grid grid-cols-2 gap-6 pt-6">
      {/* Left: KPIs + anomalies */}
      <div className="space-y-4">
        <Card>
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Indicateurs cles</h3>
          </div>
          <CardBody>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-gray-500">Conso annuelle</p>
                <p className="text-lg font-bold text-blue-700">{(site.conso_kwh_an / 1000).toFixed(0)} MWh</p>
              </div>
              <div className="p-3 bg-red-50 rounded-lg">
                <p className="text-xs text-gray-500">Risque financier</p>
                <p className="text-lg font-bold text-red-700">{site.risque_eur.toLocaleString()} EUR</p>
              </div>
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs text-gray-500">Anomalies</p>
                <p className="text-lg font-bold text-amber-700">{site.anomalies_count}</p>
              </div>
              <div className="p-3 bg-green-50 rounded-lg">
                <p className="text-xs text-gray-500">Compteurs</p>
                <p className="text-lg font-bold text-green-700">{site.nb_compteurs}</p>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Reco principale */}
        <Card className="border-l-4 border-l-blue-500">
          <CardBody>
            <p className="text-xs text-gray-500 uppercase font-semibold mb-1">Recommandation principale</p>
            <p className="text-sm text-gray-800 font-medium">
              {site.statut_conformite === 'non_conforme'
                ? 'Declarer vos consommations sur OPERAT avant le 30/09/2026'
                : site.statut_conformite === 'a_risque'
                  ? 'Planifier la mise en conformite BACS pour ce site'
                  : 'Maintenir la surveillance et optimiser la consommation'
              }
            </p>
            <Button size="sm" className="mt-3">Creer une action</Button>
          </CardBody>
        </Card>
      </div>

      {/* Right: anomalies list */}
      <Card>
        <div className="px-5 py-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800">Anomalies detectees</h3>
        </div>
        {site.anomalies_count === 0 ? (
          <EmptyState title="Aucune anomalie" text="Ce site ne presente aucune anomalie detectee." />
        ) : (
          <Table>
            <Thead>
              <tr><Th>Type</Th><Th>Severite</Th><Th>Message</Th><Th className="text-right">Perte</Th></tr>
            </Thead>
            <Tbody>
              {mockAnomalies.map((a) => (
                <Tr key={a.id}>
                  <Td><span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">{a.type}</span></Td>
                  <Td><Badge status={a.severity === 'critical' ? 'crit' : a.severity === 'high' ? 'warn' : 'info'}>{a.severity}</Badge></Td>
                  <Td className="text-sm">{a.message}</Td>
                  <Td className="text-right text-red-600 font-medium">{a.perte_eur.toLocaleString()} EUR</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}

function TabStub({ title, text }) {
  return (
    <div className="pt-6">
      <EmptyState
        title={title}
        text={text}
        ctaLabel="Bientot disponible"
      />
    </div>
  );
}

export default function Site360() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('resume');

  const site = getMockSite(id);

  if (!site) {
    return (
      <div className="px-6 py-6">
        <EmptyState
          title="Site introuvable"
          text={`Aucun site avec l'ID ${id}.`}
          ctaLabel="Retour au patrimoine"
          onCta={() => navigate('/patrimoine')}
        />
      </div>
    );
  }

  const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Back + Header */}
      <button
        onClick={() => navigate('/patrimoine')}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition"
      >
        <ArrowLeft size={16} /> Patrimoine
      </button>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-gray-900">{site.nom}</h2>
            <Badge status={badge.status}>{badge.label}</Badge>
            <span className="capitalize text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{site.usage}</span>
          </div>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
            <span className="flex items-center gap-1"><MapPin size={14} /> {site.adresse}, {site.code_postal} {site.ville}</span>
            <span className="flex items-center gap-1"><Ruler size={14} /> {site.surface_m2.toLocaleString()} m2</span>
          </div>
        </div>
        <Button variant="secondary" onClick={() => navigate(`/regops/${site.id}`)}>
          Evaluation RegOps
        </Button>
      </div>

      {/* 3 Mini KPIs */}
      <div className="flex gap-4">
        <MiniKpi icon={Zap} label="Conso annuelle" value={`${(site.conso_kwh_an / 1000).toFixed(0)} MWh`} color="text-blue-600" />
        <MiniKpi icon={BadgeEuro} label="Risque EUR" value={`${site.risque_eur.toLocaleString()} EUR`} color="text-red-600" />
        <MiniKpi icon={AlertTriangle} label="Anomalies" value={`${site.anomalies_count}`} color="text-amber-600" />
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />

      {/* Tab content */}
      {activeTab === 'resume' && <TabResume site={site} />}
      {activeTab === 'conso' && <TabStub title="Consommation" text="Courbes de charge, historique et benchmark a venir." />}
      {activeTab === 'factures' && <TabStub title="Factures" text="Analyse factures, shadow billing et optimisation tarifaire a venir." />}
      {activeTab === 'conformite' && <TabStub title="Conformite" text="Detail obligations reglementaires et echeances a venir." />}
      {activeTab === 'actions' && <TabStub title="Actions" text="Plan d'action et suivi des recommandations a venir." />}
    </div>
  );
}
