/**
 * PROMEOS - Site 360 (/sites/:siteId)
 * Header + badges + 3 mini KPIs + tabs (Resume, Conso, Factures, Conformite, Actions)
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, ShieldCheck, Zap, BadgeEuro, AlertTriangle,
  FileText, ListChecks, MapPin, Ruler,
  BookOpen, ChevronDown, ChevronUp, Clock, ExternalLink, ClipboardCheck,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, Tabs, EmptyState, TrustBadge } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { useScope } from '../contexts/ScopeContext';
import { applyKB } from '../services/api';
import { getStatusBadgeProps, SEV_BADGE } from '../lib/constants';
import IntakeWizard from '../components/IntakeWizard';
import BacsWizard from '../components/BacsWizard';
import SiteBillingMini from '../components/SiteBillingMini';

const _sb = (k) => { const { variant, label } = getStatusBadgeProps(k); return { status: variant, label }; };
const STATUT_BADGE = {
  conforme: _sb('conforme'),
  non_conforme: _sb('non_conforme'),
  a_risque: _sb('a_risque'),
  a_evaluer: _sb('a_evaluer'),
};

const TABS = [
  { id: 'resume', label: 'Résumé' },
  { id: 'conso', label: 'Consommation' },
  { id: 'factures', label: 'Factures' },
  { id: 'conformite', label: 'Conformité' },
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
    { id: 2, type: 'base_load', severity: 'high', message: 'Talon élevé : 45% de la médiane', perte_eur: Math.round(site.risque_eur * 0.2) },
    { id: 3, type: 'derive', severity: 'medium', message: 'Dérive +8% sur 30 jours', perte_eur: Math.round(site.risque_eur * 0.1) },
  ];

  return (
    <div className="grid grid-cols-2 gap-6 pt-6">
      {/* Left: KPIs + anomalies */}
      <div className="space-y-4">
        <Card>
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Indicateurs clés</h3>
          </div>
          <CardBody>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-gray-500">Conso annuelle</p>
                <p className="text-lg font-bold text-blue-700">{((site.conso_kwh_an || 0) / 1000).toFixed(0)} MWh</p>
              </div>
              <div className="p-3 bg-red-50 rounded-lg">
                <p className="text-xs text-gray-500">Risque financier</p>
                <p className="text-lg font-bold text-red-700">{(site.risque_eur || 0).toLocaleString()} €</p>
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
                ? 'Déclarer vos consommations sur OPERAT avant le 30/09/2026'
                : site.statut_conformite === 'a_risque'
                  ? 'Planifier la mise en conformité BACS pour ce site'
                  : 'Maintenir la surveillance et optimiser la consommation'
              }
            </p>
            <Button size="sm" className="mt-3">Créer une action</Button>
          </CardBody>
        </Card>
      </div>

      {/* Right: anomalies list */}
      <Card>
        <div className="px-5 py-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800">Anomalies détectées</h3>
        </div>
        {site.anomalies_count === 0 ? (
          <EmptyState title="Aucune anomalie" text="Ce site ne présente aucune anomalie détectée." />
        ) : (
          <Table>
            <Thead>
              <tr><Th>Type</Th><Th>Sévérité</Th><Th>Message</Th><Th className="text-right">Perte</Th></tr>
            </Thead>
            <Tbody>
              {mockAnomalies.map((a) => (
                <Tr key={a.id}>
                  <Td><span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">{a.type}</span></Td>
                  <Td><Badge status={SEV_BADGE[a.severity] || 'info'}>{a.severity}</Badge></Td>
                  <Td className="text-sm">{a.message}</Td>
                  <Td className="text-right text-red-600 font-medium">{(a.perte_eur || 0).toLocaleString()} €</Td>
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
        ctaLabel="Bientôt disponible"
      />
    </div>
  );
}

const KB_SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

function TabConformite({ site }) {
  const [kbResult, setKbResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    const estHvacKw = Math.round((site.surface_m2 || 0) * 0.1);
    const estParkingM2 = (site.surface_m2 || 0) >= 2000 ? Math.round(site.surface_m2 * 0.6) : 0;

    applyKB({
      site_context: {
        surface_m2: site.surface_m2 || 0,
        hvac_kw: estHvacKw,
        building_type: site.usage || 'bureau',
        parking_area_m2: estParkingM2,
        tertiaire_area_m2: site.surface_m2 || 0,
      },
      allow_drafts: true,
    })
      .then((data) => { setKbResult(data); setError(false); })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [site]);

  if (loading) {
    return (
      <div className="pt-6">
        <Card>
          <CardBody className="text-center py-8">
            <BookOpen size={28} className="text-blue-300 mx-auto mb-2 animate-pulse" />
            <p className="text-sm text-gray-400">Évaluation réglementaire en cours pour {site.nom}...</p>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (error || !kbResult) {
    return (
      <div className="pt-6">
        <EmptyState
          icon={ShieldCheck}
          title="Analyse indisponible"
          text="Impossible de contacter le moteur KB. Vérifiez que le backend est démarré."
        />
      </div>
    );
  }

  const items = kbResult.applicable_items || [];
  const missing = kbResult.missing_fields || [];
  const suggestions = kbResult.suggestions || [];
  const validated = items.filter(i => i.status === 'validated');
  const drafts = items.filter(i => i.status !== 'validated');

  return (
    <div className="pt-6 space-y-4">
      {/* Summary */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <BookOpen size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">
            {items.length} obligations applicables
          </h3>
        </div>
        {validated.length > 0 && <Badge status="ok">{validated.length} validees</Badge>}
        {drafts.length > 0 && <Badge status="neutral">{drafts.length} exploration</Badge>}
        <Link to="/kb" className="ml-auto text-xs text-blue-600 hover:underline flex items-center gap-1">
          <BookOpen size={12} /> Explorer la KB
        </Link>
      </div>

      {/* Validated items */}
      {validated.length > 0 && (
        <div className="space-y-2">
          {validated
            .sort((a, b) => (KB_SEV_ORDER[a.severity] ?? 9) - (KB_SEV_ORDER[b.severity] ?? 9))
            .map((item) => (
            <Card key={item.id} className="border-l-4 border-l-blue-400">
              <CardBody className="py-3">
                <div
                  className="flex items-start gap-3 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <Badge status={SEV_BADGE[item.severity] || 'neutral'}>{item.severity}</Badge>
                      <Badge status="ok">Valide</Badge>
                      {item.domain && (
                        <span className="text-xs font-medium px-2 py-0.5 rounded bg-red-50 text-red-700">{item.domain}</span>
                      )}
                    </div>
                    <h4 className="text-sm font-semibold text-gray-900">{item.title}</h4>
                    {expandedId !== item.id && item.summary && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.summary}</p>
                    )}
                    {item.why && expandedId !== item.id && (
                      <p className="text-xs text-blue-600 mt-1">{item.why}</p>
                    )}
                  </div>
                  <button className="p-1 text-gray-400 hover:text-gray-600 shrink-0">
                    {expandedId === item.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>

                {expandedId === item.id && (
                  <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                    {item.why && (
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <p className="text-xs font-semibold text-blue-600 uppercase mb-1">Pourquoi applicable</p>
                        <p className="text-sm text-gray-700">{item.why}</p>
                      </div>
                    )}
                    {item.logic?.then?.outputs && (
                      <div className="p-3 bg-amber-50 rounded-lg">
                        <p className="text-xs font-semibold text-amber-700 uppercase mb-1">Obligations</p>
                        {item.logic.then.outputs.map((o, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-amber-800 mt-1">
                            <span className={`w-2 h-2 rounded-full ${o.severity === 'critical' ? 'bg-red-500' : o.severity === 'high' ? 'bg-orange-500' : 'bg-blue-500'}`} />
                            <span className="font-medium">{o.label}</span>
                            {o.deadline && <span className="text-amber-600 flex items-center gap-1"><Clock size={11} /> {o.deadline}</span>}
                          </div>
                        ))}
                      </div>
                    )}
                    {item.sources && item.sources.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-500 mb-1">Sources</p>
                        {item.sources.map((src, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                            <ExternalLink size={12} />
                            <span>{src.label}{src.section ? ` - ${src.section}` : ''}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {item.tags && (
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(item.tags).map(([cat, values]) =>
                          Array.isArray(values) && values.map((v) => (
                            <span key={`${cat}-${v}`} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{cat}:{v}</span>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Draft items (exploration) */}
      {drafts.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-400 font-medium">Items en exploration (drafts)</p>
          {drafts.slice(0, 5).map((item) => (
            <Card key={item.id} className="border-l-4 border-l-gray-200 opacity-80">
              <CardBody className="py-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge status="neutral">draft</Badge>
                  {item.domain && (
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-50 text-gray-600">{item.domain}</span>
                  )}
                  <span className="text-sm text-gray-700">{item.title}</span>
                </div>
                {item.summary && (
                  <p className="text-xs text-gray-400 mt-1 line-clamp-1">{item.summary}</p>
                )}
              </CardBody>
            </Card>
          ))}
          {drafts.length > 5 && (
            <p className="text-xs text-gray-400 text-center">+{drafts.length - 5} autres items en exploration</p>
          )}
        </div>
      )}

      {/* Missing fields */}
      {missing.length > 0 && (
        <Card className="border-l-4 border-l-amber-300">
          <CardBody className="py-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={14} className="text-amber-500" />
              <p className="text-xs font-semibold text-amber-700">Données manquantes</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {missing.map((f) => (
                <span key={f} className="px-2 py-1 bg-amber-50 text-amber-700 rounded text-xs font-medium">{f}</span>
              ))}
            </div>
            {suggestions.length > 0 && (
              <p className="text-xs text-gray-500 mt-2">{suggestions.join(' ')}</p>
            )}
          </CardBody>
        </Card>
      )}

      <TrustBadge source="PROMEOS KB" period={`Analyse pour ${site.nom}`} confidence="high" />
    </div>
  );
}

export default function Site360() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { scopedSites, sitesLoading } = useScope();
  const [activeTab, setActiveTab] = useState('resume');
  const [showIntake, setShowIntake] = useState(false);
  const [showBacs, setShowBacs] = useState(false);

  const site = scopedSites.find(s => String(s.id) === String(id));

  if (sitesLoading) {
    return (
      <div className="px-6 py-6 space-y-4">
        <button
          onClick={() => navigate('/patrimoine')}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition"
        >
          <ArrowLeft size={16} /> Patrimoine
        </button>
        <div className="flex gap-4">
          <SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      </div>
    );
  }

  if (!site) {
    return (
      <div className="px-6 py-6">
        <EmptyState
          title="Site introuvable"
          text={`Aucun site avec l'identifiant ${id} dans votre périmètre.`}
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
            <span className="flex items-center gap-1"><Ruler size={14} /> {(site.surface_m2 || 0).toLocaleString()} m2</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setShowBacs(true)}>
            <ShieldCheck size={14} className="mr-1" />
            Évaluer BACS
          </Button>
          <Button variant="outline" onClick={() => setShowIntake(true)}>
            <ClipboardCheck size={14} className="mr-1" />
            Compléter les données
          </Button>
          <Button variant="secondary" onClick={() => navigate(`/regops/${site.id}`)}>
            Evaluation RegOps
          </Button>
        </div>
      </div>

      {/* 3 Mini KPIs */}
      <div className="flex gap-4">
        <MiniKpi icon={Zap} label="Conso annuelle" value={`${((site.conso_kwh_an || 0) / 1000).toFixed(0)} MWh`} color="text-blue-600" />
        <MiniKpi icon={BadgeEuro} label="Risque €" value={`${(site.risque_eur || 0).toLocaleString()} €`} color="text-red-600" />
        <MiniKpi icon={AlertTriangle} label="Anomalies" value={`${site.anomalies_count}`} color="text-amber-600" />
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />

      {/* Tab content */}
      {activeTab === 'resume' && <TabResume site={site} />}
      {activeTab === 'conso' && <TabStub title="Consommation" text="Courbes de charge, historique et benchmark à venir." />}
      {activeTab === 'factures' && <SiteBillingMini siteId={site.id} />}
      {activeTab === 'factures' && (
        <div className="flex justify-end mt-2">
          <button
            className="text-xs text-amber-600 hover:underline"
            onClick={() => navigate(`/billing?site_id=${site.id}`)}
          >
            Voir timeline complète
          </button>
        </div>
      )}
      {activeTab === 'conformite' && <TabConformite site={site} />}
      {activeTab === 'actions' && <TabStub title="Actions" text="Plan d'action et suivi des recommandations à venir." />}

      {/* BACS Wizard modal */}
      {showBacs && (
        <BacsWizard siteId={site.id} onClose={() => setShowBacs(false)} />
      )}

      {/* Smart Intake Wizard modal */}
      {showIntake && (
        <IntakeWizard siteId={site.id} onClose={() => setShowIntake(false)} />
      )}
    </div>
  );
}
