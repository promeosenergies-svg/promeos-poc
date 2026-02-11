import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, AlertTriangle, Zap, ArrowRight, RefreshCw,
  CheckCircle, XCircle, Clock, Plus,
} from 'lucide-react';
import { getDashboard2min } from '../services/api';

const COLOR_MAP = {
  green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: CheckCircle },
  orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', icon: AlertTriangle },
  red: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: XCircle },
  gray: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-500', icon: Clock },
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: Clock },
};

function Cockpit2MinPage({ onUpgradeClick }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await getDashboard2min();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12 text-center">
        <RefreshCw size={24} className="animate-spin mx-auto text-blue-500 mb-3" />
        <p className="text-gray-500">Chargement du cockpit...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">{error}</div>
      </div>
    );
  }

  // No data yet — prompt to onboard
  if (!data?.has_data) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="text-center">
          <Shield size={48} className="mx-auto text-gray-300 mb-4" />
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Cockpit 2 minutes</h1>
          <p className="text-gray-500 mb-6">
            Creez votre organisation pour obtenir un diagnostic en 2 minutes.
          </p>
          <button
            onClick={onUpgradeClick}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
          >
            <Plus size={18} />
            Demarrer l'onboarding
          </button>
        </div>
        {/* Completude */}
        <div className="mt-8 max-w-sm mx-auto">
          <CompletudeBadge completude={data?.completude} />
        </div>
      </div>
    );
  }

  const conf = data.conformite_status;
  const colorConf = COLOR_MAP[conf?.color] || COLOR_MAP.gray;
  const ConfIcon = colorConf.icon;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Cockpit 2 minutes</h1>
          <p className="text-sm text-gray-500">{data.organisation?.nom} — {data.organisation?.type_client}</p>
        </div>
        <button onClick={fetchData} className="p-2 rounded hover:bg-gray-100 text-gray-400">
          <RefreshCw size={18} />
        </button>
      </div>

      {/* 3 blocks grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">

        {/* Block 1: Conformite */}
        <div className={`rounded-xl border-2 p-5 ${colorConf.bg} ${colorConf.border}`}>
          <div className="flex items-center gap-2 mb-3">
            <ConfIcon size={22} className={colorConf.text} />
            <h2 className="font-semibold text-gray-800">Conformite</h2>
          </div>
          <p className={`text-2xl font-bold mb-1 ${colorConf.text}`}>{conf?.label}</p>
          <div className="space-y-1 text-xs text-gray-600">
            <div className="flex justify-between">
              <span>Obligations</span>
              <span className="font-medium">{conf?.obligations_total}</span>
            </div>
            <div className="flex justify-between">
              <span>Conformes</span>
              <span className="font-medium text-green-600">{conf?.conformes}</span>
            </div>
            <div className="flex justify-between">
              <span>A risque</span>
              <span className="font-medium text-orange-600">{conf?.a_risque}</span>
            </div>
            <div className="flex justify-between">
              <span>Non conformes</span>
              <span className="font-medium text-red-600">{conf?.non_conformes}</span>
            </div>
          </div>
        </div>

        {/* Block 2: Pertes estimees */}
        <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={22} className="text-amber-600" />
            <h2 className="font-semibold text-gray-800">Risque financier</h2>
          </div>
          <p className="text-2xl font-bold text-amber-700 mb-1">
            {data.pertes_estimees_eur?.toLocaleString('fr-FR')} EUR
          </p>
          <p className="text-xs text-gray-500">
            Pertes estimees liees a la non-conformite reglementaire
          </p>
          <div className="mt-3 text-xs text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>Sites actifs</span>
              <span className="font-medium">{data.stats?.sites_actifs}</span>
            </div>
            <div className="flex justify-between">
              <span>Compteurs</span>
              <span className="font-medium">{data.stats?.total_compteurs}</span>
            </div>
          </div>
        </div>

        {/* Block 3: Action #1 */}
        <div className="rounded-xl border-2 border-blue-200 bg-blue-50 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={22} className="text-blue-600" />
            <h2 className="font-semibold text-gray-800">Action #1</h2>
          </div>
          {data.action_1 && (
            <>
              <p className="text-sm font-medium text-gray-800 mb-2">{data.action_1.texte}</p>
              <div className="flex items-center gap-2 mb-3">
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                  data.action_1.priorite === 'critical' ? 'bg-red-100 text-red-700' :
                  data.action_1.priorite === 'high' ? 'bg-orange-100 text-orange-700' :
                  data.action_1.priorite === 'info' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {data.action_1.priorite}
                </span>
                {data.action_1.nb_sites_concernes > 0 && (
                  <span className="text-xs text-gray-500">
                    {data.action_1.nb_sites_concernes} site(s) concerne(s)
                  </span>
                )}
              </div>
              {data.action_1.reglementation && (
                <p className="text-xs text-gray-400">
                  Reglementation : {data.action_1.reglementation.replace('_', ' ')}
                </p>
              )}
            </>
          )}
          <Link to="/action-plan"
            className="mt-3 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 font-medium">
            Voir le plan d'action <ArrowRight size={14} />
          </Link>
        </div>
      </div>

      {/* Completude bar */}
      <CompletudeBadge completude={data.completude} />

      {/* CTA if incomplete */}
      {data.completude?.pct < 100 && (
        <div className="mt-4 bg-white border rounded-lg p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">Completez votre patrimoine</p>
            <p className="text-xs text-gray-500">{data.completude?.message}</p>
          </div>
          <button onClick={onUpgradeClick}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition">
            Completer
          </button>
        </div>
      )}

      {/* Quick links */}
      <div className="mt-6 flex gap-3">
        <Link to="/cockpit"
          className="flex-1 text-center py-3 bg-white border rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition">
          Cockpit executif complet
        </Link>
        <Link to="/"
          className="flex-1 text-center py-3 bg-white border rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition">
          Dashboard sites
        </Link>
        <Link to="/import"
          className="flex-1 text-center py-3 bg-white border rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition">
          Importer des sites
        </Link>
      </div>
    </div>
  );
}


function CompletudeBadge({ completude }) {
  if (!completude) return null;
  const { pct, checks } = completude;
  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">Completude du patrimoine</span>
        <span className="text-sm font-bold text-blue-600">{pct}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div
          className={`h-2 rounded-full transition-all ${pct === 100 ? 'bg-green-500' : 'bg-blue-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex gap-4 text-xs">
        {Object.entries(checks).map(([key, done]) => (
          <div key={key} className="flex items-center gap-1">
            {done ? (
              <CheckCircle size={12} className="text-green-500" />
            ) : (
              <Clock size={12} className="text-gray-400" />
            )}
            <span className={done ? 'text-green-700' : 'text-gray-500'}>{key}</span>
          </div>
        ))}
      </div>
    </div>
  );
}


export default Cockpit2MinPage;
